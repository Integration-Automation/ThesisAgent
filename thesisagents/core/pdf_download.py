"""Download paper PDFs alongside the exported artefacts.

Reuses the shared per-source HTTPS-only client so the same rate-limit token
bucket, TLS guardrails, and User-Agent rules apply as for search traffic.
Failures (missing pdf_url, network errors, wrong content-type) are logged
and skipped — the rest of the export workflow is unaffected.

Every PDF request also sends browser-style headers (real Mozilla
User-Agent, ``Accept``, ``Accept-Language``, and a ``Referer`` derived
from the paper's landing-page URL) because many publishers return 403 to
the project's default API-style UA. When the env var
``THESISAGENTS_PDF_COOKIES_FILE`` points at a Netscape ``cookies.txt``
file, matching cookies are attached on top.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse

from thesisagents.core.models import Paper, PaperCollection
from thesisagents.core.pdf_cookies import cookies_for_url
from thesisagents.fetchers.http import get_client
from thesisagents.utils.logging import get_logger
from thesisagents.utils.path_safety import ensure_export_dir, safe_filename

_LOG = get_logger(__name__)

_PDF_SUBDIR: str = "pdfs"
_MAX_PDF_BYTES: int = 50_000_000
_MAX_FILENAME_LENGTH: int = 80

#: Cap on simultaneously-downloading PDFs. Each per-source client already has
#: its own token bucket, but several sources can hand back PDF URLs on the SAME
#: publisher CDN (dl.acm.org, link.springer.com, …) under different source
#: clients — bypassing any single bucket. A global cap keeps that burst from
#: looking like a scrape and risking an IP block. 4 keeps the stage brisk.
_DOWNLOAD_CONCURRENCY: int = 4

#: Real browser User-Agent — many publisher CDNs (Elsevier, IEEE Xplore,
#: Springer) return 403 to non-browser UAs even for open-access PDFs.
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


@dataclass(frozen=True, slots=True)
class PdfDownloadResult:
    """Outcome of one download attempt."""

    paper_key: str
    path: Path | None
    skipped_reason: str | None


async def download_pdfs(
    collection: PaperCollection,
    out_dir: str | Path,
    *,
    concurrency: int = _DOWNLOAD_CONCURRENCY,
) -> list[PdfDownloadResult]:
    """Download every paper's PDF into ``{out_dir}/pdfs/``.

    Returns a result per paper so callers can summarise failures. Papers
    without a ``pdf_url`` are skipped with reason ``no_pdf_url``. A semaphore
    caps how many downloads run at once (``concurrency``, default
    ``_DOWNLOAD_CONCURRENCY``) so a large collection doesn't hammer a single
    publisher CDN with one request per paper simultaneously.
    """
    root = ensure_export_dir(out_dir)
    pdf_dir = ensure_export_dir(root / _PDF_SUBDIR)
    sem = asyncio.Semaphore(max(1, concurrency))

    async def _bounded(paper: Paper) -> PdfDownloadResult:
        async with sem:
            return await _download_one(paper, pdf_dir)

    results = await asyncio.gather(
        *(_bounded(paper) for paper in collection.papers)
    )
    return list(results)


async def _download_one(paper: Paper, pdf_dir: Path) -> PdfDownloadResult:
    key = paper.bibtex_key()
    if not paper.pdf_url:
        _LOG.info("skip pdf for %s: no pdf_url", key)
        return PdfDownloadResult(paper_key=key, path=None, skipped_reason="no_pdf_url")
    target = pdf_dir / f"{safe_filename(key)[:_MAX_FILENAME_LENGTH]}.pdf"
    if target.exists() and target.stat().st_size > 0:
        _LOG.info("pdf already on disk for %s: %s", key, target)
        return PdfDownloadResult(paper_key=key, path=target, skipped_reason=None)
    # For paywalled publisher CDNs (IEEE, ACM, Springer, Elsevier, ...)
    # httpx-style requests reliably 403. Route those through WebRunner
    # (real visible Chrome) so the session cookie / TLS handshake / JS
    # fingerprint match what the publisher expects.
    from thesisagents.fetchers import webrunner_pdf

    if webrunner_pdf.is_available() and webrunner_pdf.should_use_webrunner(paper.pdf_url):
        _LOG.info("pdf via WebRunner for %s: %s", key, paper.pdf_url)
        ok = await webrunner_pdf.download_via_browser(paper.pdf_url, target)
        if ok:
            return PdfDownloadResult(paper_key=key, path=target, skipped_reason=None)
        _LOG.info(
            "pdf WebRunner failed for %s; falling back to httpx", key,
        )
    return await _fetch_and_validate(paper, target, key)


async def _fetch_and_validate(
    paper: Paper, target: Path, key: str
) -> PdfDownloadResult:
    """Fetch ``paper.pdf_url`` and persist the PDF bytes.

    Handles the three soft failure modes: HTTP 4xx/5xx, oversized body,
    HTML-instead-of-PDF. The last is recoverable when the HTML carries
    a ``<meta name="citation_pdf_url">`` tag (Google Scholar's
    metadata convention, populated by most publisher landing pages and
    every OJS / DSpace / EPrints install) — we extract the tag, follow
    it once, and re-validate.
    """
    client = await get_client(paper.source)
    fetched = await _request_pdf(client, paper, paper.pdf_url)
    if isinstance(fetched, PdfDownloadResult):
        # _request_pdf carries the failure reason but doesn't know the key.
        return PdfDownloadResult(
            paper_key=key, path=fetched.path, skipped_reason=fetched.skipped_reason
        )
    body, content_type = fetched
    if not _looks_like_pdf(body, content_type):
        retry_url = _extract_citation_pdf_url(body, base_url=paper.pdf_url)
        if retry_url and retry_url != paper.pdf_url:
            _LOG.info(
                "pdf %s returned HTML; retrying via <meta name=\"citation_pdf_url\"> %s",
                key, retry_url,
            )
            fetched = await _request_pdf(client, paper, retry_url)
            if isinstance(fetched, PdfDownloadResult):
                return PdfDownloadResult(
                    paper_key=key, path=None, skipped_reason="citation_pdf_url_fail",
                )
            body, content_type = fetched
        if not _looks_like_pdf(body, content_type):
            _LOG.warning(
                "pdf wrong content-type for %s: %r", key, content_type or "<empty>"
            )
            return PdfDownloadResult(
                paper_key=key, path=None, skipped_reason="not_pdf"
            )
    target.write_bytes(body)
    _LOG.info("pdf saved %s (%d bytes) for %s", target, len(body), key)
    return PdfDownloadResult(paper_key=key, path=target, skipped_reason=None)


async def _request_pdf(client, paper: Paper, url: str):
    """Run one HTTP GET with browser-style headers and Cookie injection.

    Returns ``(body, content_type)`` on a 2xx response that fits the
    size cap, or a :class:`PdfDownloadResult` with the failure reason
    already populated.
    """
    headers = _browser_headers(paper)
    cookies = cookies_for_url(url)
    if cookies:
        # Pass cookies through the ``Cookie:`` header directly; httpx's
        # per-request ``cookies=`` arg is deprecated, and our cookies are
        # opaque-strings-from-a-file, never managed across requests.
        headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    try:
        response = await client.get(url, headers=headers)
    except Exception as err:  # noqa: BLE001  # network errors come in many shapes
        _LOG.warning("pdf network error for %s: %s", url, err)
        return PdfDownloadResult(
            paper_key="", path=None, skipped_reason="network_error"
        )
    if response.status_code >= 400:
        _LOG.warning("pdf http %s for %s", response.status_code, url)
        return PdfDownloadResult(
            paper_key="", path=None,
            skipped_reason=f"http_{response.status_code}",
        )
    body = response.content
    if len(body) > _MAX_PDF_BYTES:
        _LOG.warning("pdf too large for %s (%d bytes)", url, len(body))
        return PdfDownloadResult(
            paper_key="", path=None, skipped_reason="too_large"
        )
    content_type = response.headers.get("content-type", "").lower()
    return body, content_type


def _looks_like_pdf(body: bytes, content_type: str) -> bool:
    if "pdf" in content_type:
        return True
    return body.startswith(b"%PDF")


_CITATION_PDF_URL_RE = re.compile(
    rb'<meta\s+[^>]*?name=["\']citation_pdf_url["\'][^>]*?content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_CITATION_PDF_URL_REV_RE = re.compile(
    rb'<meta\s+[^>]*?content=["\']([^"\']+)["\'][^>]*?name=["\']citation_pdf_url["\']',
    re.IGNORECASE,
)


def _extract_citation_pdf_url(body: bytes, *, base_url: str) -> str | None:
    """Parse ``<meta name="citation_pdf_url" content="...">`` out of HTML.

    The tag is the Google Scholar metadata convention every publisher
    landing page implements; the URL points at the canonical PDF for
    that paper. We accept either attribute order. Relative URLs are
    resolved against ``base_url`` so we don't issue an unparseable GET.
    """
    if not body:
        return None
    head = body[:32_768]  # the tag always sits in the document <head>
    match = _CITATION_PDF_URL_RE.search(head) or _CITATION_PDF_URL_REV_RE.search(head)
    if not match:
        return None
    candidate = match.group(1).decode("utf-8", errors="replace").strip()
    if not candidate:
        return None
    return urljoin(base_url, candidate)


def _browser_headers(paper: Paper) -> dict[str, str]:
    """Per-request headers that make us look like a browser to publisher
    CDNs. ``Referer`` is the paper's landing page (when its host matches
    the PDF host) so the request looks like a click-through from the
    article page; that closes the most common 403 case."""
    headers: dict[str, str] = {
        "User-Agent": _BROWSER_UA,
        "Accept": "application/pdf,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    referer = _referer_for(paper)
    if referer:
        headers["Referer"] = referer
    return headers


def _referer_for(paper: Paper) -> str | None:
    """Use ``paper.url`` as Referer when its host matches the PDF's host —
    a cross-host Referer would itself trip anti-bot rules."""
    if not paper.url or not paper.pdf_url:
        return None
    landing_host = urlparse(paper.url).hostname or ""
    pdf_host = urlparse(paper.pdf_url).hostname or ""
    if landing_host and pdf_host and landing_host == pdf_host:
        return paper.url
    return None
