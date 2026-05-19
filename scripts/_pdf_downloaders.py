"""Per-publisher PDF download helpers (shared by the LLM-driven scripts).

Each ``download_*`` helper runs against a Chrome driver the caller
already booted, so a batch script can solve a captcha / SSO once at
the start and burn through N papers in the same session instead of
booting Chrome per paper.

Common contract for each helper:

* Inputs: ``driver`` (already booted via ``webrunner_browser.make_driver``
  with ``download_dir`` configured), the per-paper identifier, ``out_dir``
  (where the resulting PDF should live).
* Behaviour: clear stale ``*.crdownload`` and any same-named PDF first,
  navigate to the landing URL, give the publisher a chance to either
  auto-download or expose a PDF link, wait on the download dir, validate
  ``%PDF-`` head + ``%%EOF`` tail, rename to the canonical ``<id>.pdf``.
* Return: the saved ``Path`` on success, ``None`` on failure (no PDF
  appeared, or the file was not a valid PDF — usually the publisher
  served an HTML "Sign in / Get access" gate to an unauthenticated
  visitor).

The helpers do NOT call ``driver.quit()`` — the caller owns the driver
lifecycle so a batch can reuse one Chrome across many papers.
"""

from __future__ import annotations

import contextlib
import re
import time
from pathlib import Path
from typing import Any

from autopapertoppt.fetchers import webrunner_browser

_DOWNLOAD_POLL_INTERVAL = 1.0
_DOWNLOAD_MAX_WAIT = 90.0
_DOC_RENDER_WAIT = 4.0
_STAMP_RENDER_WAIT = 6.0


def _clear_pending(out_dir: Path) -> None:
    """Remove stale .crdownload so a half-finished prior run doesn't trip the wait.

    Deliberately does NOT touch existing .pdf files — earlier papers in a batch
    already wrote their final PDFs here under canonical names; wiping them now
    would defeat the whole point of batching.
    """
    for old in out_dir.glob("*.crdownload"):
        with contextlib.suppress(OSError):
            old.unlink()


def _snapshot_pdfs(out_dir: Path) -> set[Path]:
    """Snapshot the existing .pdf set so we can later detect the new arrival."""
    return set(out_dir.glob("*.pdf"))


def _wait_for_new_pdf(
    out_dir: Path, baseline: set[Path], deadline: float,
) -> Path | None:
    """Block until a NEW .pdf lands (not in ``baseline``) and no .crdownload remains."""
    while time.monotonic() < deadline:
        pending = list(out_dir.glob("*.crdownload"))
        new_pdfs = [p for p in out_dir.glob("*.pdf") if p not in baseline]
        if new_pdfs and not pending:
            return new_pdfs[0]
        time.sleep(_DOWNLOAD_POLL_INTERVAL)
    return None


def _is_valid_pdf(path: Path) -> bool:
    """Magic-header + EOF check — rejects HTML masquerading as PDF."""
    try:
        data = path.read_bytes()
    except OSError:
        return False
    if len(data) < 32:
        return False
    if data[:4] != b"%PDF":
        return False
    return b"%%EOF" in data[-64:]


def _finalise(pdf: Path, canonical_name: str) -> Path | None:
    """Validate + rename. Returns the canonical path on success."""
    if not _is_valid_pdf(pdf):
        head = pdf.read_bytes()[:8] if pdf.exists() else b""
        size = pdf.stat().st_size if pdf.exists() else 0
        print(
            f"[fail] file {pdf.name} ({size} bytes) is not a valid PDF "
            f"(head={head!r}). Publisher likely served an HTML gate.",
            flush=True,
        )
        return None
    target = pdf.parent / canonical_name
    if pdf != target:
        if target.exists():
            target.unlink()
        pdf.rename(target)
    print(
        f"[ok]   {target.name} ({target.stat().st_size:,} bytes)",
        flush=True,
    )
    return target


# ---------------------------------------------------------------------------
# IEEE Xplore
# ---------------------------------------------------------------------------

_IEEE_DOC_URL = "https://ieeexplore.ieee.org/document/{arnumber}"
_IEEE_STAMP_URL = "https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={arnumber}"
_IEEE_ARNUMBER_RE = re.compile(r"/document/(\d+)")


def arnumber_from_url(url: str) -> str | None:
    """Pull the IEEE arnumber out of a `/document/<id>` URL."""
    if not url:
        return None
    m = _IEEE_ARNUMBER_RE.search(url)
    return m.group(1) if m else None


def download_ieee(
    driver: Any, arnumber: str, out_dir: Path,
) -> Path | None:
    """Drive Chrome to download an IEEE Xplore PDF by arnumber."""
    target = out_dir / f"{arnumber}.pdf"
    if target.exists() and _is_valid_pdf(target):
        print(f"[ieee] cached {target.name}", flush=True)
        return target
    _clear_pending(out_dir)
    baseline = _snapshot_pdfs(out_dir)

    doc_url = _IEEE_DOC_URL.format(arnumber=arnumber)
    print(f"[ieee] doc {doc_url}", flush=True)
    driver.get(doc_url)
    time.sleep(_DOC_RENDER_WAIT)
    webrunner_browser.wait_for_captcha_solved(driver, max_wait_seconds=300.0)

    stamp_url = _IEEE_STAMP_URL.format(arnumber=arnumber)
    print(f"[ieee] stamp {stamp_url}", flush=True)
    driver.get(stamp_url)
    time.sleep(_STAMP_RENDER_WAIT)
    webrunner_browser.wait_for_captcha_solved(driver, max_wait_seconds=300.0)

    deadline = time.monotonic() + _DOWNLOAD_MAX_WAIT
    pdf = _wait_for_new_pdf(out_dir, baseline, deadline)
    if pdf is None:
        # stamp.jsp serves an iframe wrapper; chase the iframe src.
        try:
            src = driver.execute_script(
                "const f=document.querySelector('frame,iframe');"
                "return f?f.src:null;"
            )
        except Exception:  # noqa: BLE001
            src = None
        if src and src.startswith("https://"):
            print(f"[ieee] iframe retry {src}", flush=True)
            driver.get(src)
            deadline = time.monotonic() + _DOWNLOAD_MAX_WAIT
            pdf = _wait_for_new_pdf(out_dir, baseline, deadline)

    if pdf is None:
        print("[ieee] no PDF appeared (paper may be early-access / withdrawn / no subscription access)", flush=True)
        return None
    return _finalise(pdf, f"{arnumber}.pdf")


# ---------------------------------------------------------------------------
# ACM Digital Library
# ---------------------------------------------------------------------------

_ACM_LANDING_URL = "https://dl.acm.org/doi/{doi}"
_ACM_PDF_URL = "https://dl.acm.org/doi/pdf/{doi}"


def _safe_doi_slug(doi: str) -> str:
    """Make a DOI safe for use as a filename stem."""
    return doi.replace("/", "_").replace(":", "_")


def download_acm(driver: Any, doi: str, out_dir: Path) -> Path | None:
    """Drive Chrome to download an ACM-hosted PDF by DOI."""
    canonical = f"{_safe_doi_slug(doi)}.pdf"
    target = out_dir / canonical
    if target.exists() and _is_valid_pdf(target):
        print(f"[acm]  cached {target.name}", flush=True)
        return target
    _clear_pending(out_dir)
    baseline = _snapshot_pdfs(out_dir)

    landing = _ACM_LANDING_URL.format(doi=doi)
    print(f"[acm]  landing {landing}", flush=True)
    driver.get(landing)
    time.sleep(_DOC_RENDER_WAIT)
    webrunner_browser.wait_for_captcha_solved(driver, max_wait_seconds=300.0)

    pdf_url = _ACM_PDF_URL.format(doi=doi)
    print(f"[acm]  pdf {pdf_url}", flush=True)
    driver.get(pdf_url)
    time.sleep(_STAMP_RENDER_WAIT)
    webrunner_browser.wait_for_captcha_solved(driver, max_wait_seconds=300.0)

    deadline = time.monotonic() + _DOWNLOAD_MAX_WAIT
    pdf = _wait_for_new_pdf(out_dir, baseline, deadline)
    if pdf is None:
        try:
            src = driver.execute_script(
                "const f=document.querySelector('frame,iframe');"
                "return f?f.src:null;"
            )
        except Exception:  # noqa: BLE001
            src = None
        if src and src.startswith("https://"):
            print(f"[acm]  iframe retry {src}", flush=True)
            driver.get(src)
            deadline = time.monotonic() + _DOWNLOAD_MAX_WAIT
            pdf = _wait_for_new_pdf(out_dir, baseline, deadline)

    if pdf is None:
        print("[acm]  no PDF appeared (likely paywall — institutional access required)", flush=True)
        return None
    return _finalise(pdf, canonical)


# ---------------------------------------------------------------------------
# SpringerLink
# ---------------------------------------------------------------------------

_SPRINGER_ARTICLE_URL = "https://link.springer.com/article/{doi}"
_SPRINGER_CHAPTER_URL = "https://link.springer.com/chapter/{doi}"
_SPRINGER_PDF_URL = "https://link.springer.com/content/pdf/{doi}.pdf"


def download_springer(driver: Any, doi: str, out_dir: Path) -> Path | None:
    """Drive Chrome to download a SpringerLink PDF by DOI.

    Springer hosts both journal articles (`/article/<doi>`) and book
    chapters (`/chapter/<doi>`); we try article first and fall through
    to chapter on a 404 / "page not found" body.
    """
    canonical = f"{_safe_doi_slug(doi)}.pdf"
    target = out_dir / canonical
    if target.exists() and _is_valid_pdf(target):
        print(f"[spr]  cached {target.name}", flush=True)
        return target
    _clear_pending(out_dir)
    baseline = _snapshot_pdfs(out_dir)

    article = _SPRINGER_ARTICLE_URL.format(doi=doi)
    print(f"[spr]  article {article}", flush=True)
    driver.get(article)
    time.sleep(_DOC_RENDER_WAIT)
    webrunner_browser.wait_for_captcha_solved(driver, max_wait_seconds=300.0)
    if "Page not found" in (driver.page_source or "")[:8192]:
        chapter = _SPRINGER_CHAPTER_URL.format(doi=doi)
        print(f"[spr]  not an article, retrying chapter {chapter}", flush=True)
        driver.get(chapter)
        time.sleep(_DOC_RENDER_WAIT)
        webrunner_browser.wait_for_captcha_solved(driver, max_wait_seconds=300.0)

    pdf_url = _SPRINGER_PDF_URL.format(doi=doi)
    print(f"[spr]  pdf {pdf_url}", flush=True)
    driver.get(pdf_url)
    time.sleep(_STAMP_RENDER_WAIT)
    webrunner_browser.wait_for_captcha_solved(driver, max_wait_seconds=300.0)

    deadline = time.monotonic() + _DOWNLOAD_MAX_WAIT
    pdf = _wait_for_new_pdf(out_dir, baseline, deadline)
    if pdf is None:
        print("[spr]  no PDF appeared (likely no institutional access)", flush=True)
        return None
    return _finalise(pdf, canonical)


# ---------------------------------------------------------------------------
# arXiv (open access, no VPN required)
# ---------------------------------------------------------------------------

_ARXIV_ID_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,6}(?:v\d+)?)")
_ARXIV_PDF_URL = "https://arxiv.org/pdf/{arxiv_id}.pdf"


def arxiv_id_from_url(url: str) -> str | None:
    """Pull the arXiv ID out of `arxiv.org/abs/<id>` or `arxiv.org/pdf/<id>`."""
    if not url:
        return None
    m = _ARXIV_ID_RE.search(url)
    return m.group(1) if m else None


def download_arxiv(driver: Any, arxiv_id: str, out_dir: Path) -> Path | None:
    """Drive Chrome to download an arXiv PDF. arXiv is open-access — no VPN.

    arXiv allows anonymous direct downloads of `/pdf/<id>.pdf`. We use the
    same visible-Chrome path as the paywalled publishers (rather than httpx)
    so the rest of the batch flow stays consistent — one driver, one log,
    same `*.crdownload` polling.
    """
    canonical = f"arxiv-{arxiv_id.replace('.', '_').replace('/', '_')}.pdf"
    target = out_dir / canonical
    if target.exists() and _is_valid_pdf(target):
        print(f"[arx]  cached {target.name}", flush=True)
        return target
    _clear_pending(out_dir)
    baseline = _snapshot_pdfs(out_dir)

    pdf_url = _ARXIV_PDF_URL.format(arxiv_id=arxiv_id)
    print(f"[arx]  pdf {pdf_url}", flush=True)
    driver.get(pdf_url)
    time.sleep(_STAMP_RENDER_WAIT)

    deadline = time.monotonic() + _DOWNLOAD_MAX_WAIT
    pdf = _wait_for_new_pdf(out_dir, baseline, deadline)
    if pdf is None:
        print(f"[arx]  no PDF appeared for {arxiv_id}", flush=True)
        return None
    return _finalise(pdf, canonical)


# ---------------------------------------------------------------------------
# ACL Anthology (open access, no VPN required)
# ---------------------------------------------------------------------------

_ACL_ID_RE = re.compile(r"aclanthology\.org/([^/?#]+?)(?:/|\.pdf)?$")
_ACL_PDF_URL = "https://aclanthology.org/{anthology_id}.pdf"


def acl_id_from_url(url: str) -> str | None:
    """Pull the ACL Anthology ID out of `aclanthology.org/<id>/`."""
    if not url:
        return None
    m = _ACL_ID_RE.search(url.rstrip("/") + "/")
    if m:
        ident = m.group(1)
        # Drop trailing `.pdf` / index suffix if matched.
        if ident.endswith(".pdf"):
            ident = ident[:-4]
        return ident
    return None


def download_aclanthology(driver: Any, anthology_id: str, out_dir: Path) -> Path | None:
    """Drive Chrome to download an ACL Anthology PDF. Open access, no VPN."""
    canonical = f"acl-{anthology_id.replace('.', '_').replace('/', '_')}.pdf"
    target = out_dir / canonical
    if target.exists() and _is_valid_pdf(target):
        print(f"[acl]  cached {target.name}", flush=True)
        return target
    _clear_pending(out_dir)
    baseline = _snapshot_pdfs(out_dir)

    pdf_url = _ACL_PDF_URL.format(anthology_id=anthology_id)
    print(f"[acl]  pdf {pdf_url}", flush=True)
    driver.get(pdf_url)
    time.sleep(_STAMP_RENDER_WAIT)

    deadline = time.monotonic() + _DOWNLOAD_MAX_WAIT
    pdf = _wait_for_new_pdf(out_dir, baseline, deadline)
    if pdf is None:
        print(f"[acl]  no PDF appeared for {anthology_id}", flush=True)
        return None
    return _finalise(pdf, canonical)


# ---------------------------------------------------------------------------
# NeurIPS / OpenReview proceedings (open access, no VPN required)
# ---------------------------------------------------------------------------

_NEURIPS_HASH_RE = re.compile(
    r"proceedings\.neurips\.cc/paper(?:_files)?/paper/(\d{4})/hash/([0-9a-f]+)-Abstract"
)


def neurips_paper_from_url(url: str) -> tuple[str, str] | None:
    """Return ``(year, hash)`` for a NeurIPS proceedings landing URL."""
    if not url:
        return None
    m = _NEURIPS_HASH_RE.search(url)
    return (m.group(1), m.group(2)) if m else None


def download_neurips(
    driver: Any, year: str, paper_hash: str, out_dir: Path,
) -> Path | None:
    """NeurIPS swaps ``hash/<id>-Abstract-Conference.html`` for
    ``file/<id>-Paper-Conference.pdf`` to expose the PDF directly."""
    canonical = f"neurips-{year}-{paper_hash[:12]}.pdf"
    target = out_dir / canonical
    if target.exists() and _is_valid_pdf(target):
        print(f"[nips] cached {target.name}", flush=True)
        return target
    _clear_pending(out_dir)
    baseline = _snapshot_pdfs(out_dir)

    pdf_url = (
        f"https://proceedings.neurips.cc/paper_files/paper/{year}/file/"
        f"{paper_hash}-Paper-Conference.pdf"
    )
    print(f"[nips] pdf {pdf_url}", flush=True)
    driver.get(pdf_url)
    time.sleep(_STAMP_RENDER_WAIT)

    deadline = time.monotonic() + _DOWNLOAD_MAX_WAIT
    pdf = _wait_for_new_pdf(out_dir, baseline, deadline)
    if pdf is None:
        print(f"[nips] no PDF appeared for {year}/{paper_hash[:12]}", flush=True)
        return None
    return _finalise(pdf, canonical)


_OPENREVIEW_ID_RE = re.compile(r"openreview\.net/(?:forum|pdf)\?id=([A-Za-z0-9]+)")


def openreview_id_from_url(url: str) -> str | None:
    """Pull the OpenReview paper ID out of `forum?id=…` or `pdf?id=…`."""
    if not url:
        return None
    m = _OPENREVIEW_ID_RE.search(url)
    return m.group(1) if m else None


def download_openreview(driver: Any, openreview_id: str, out_dir: Path) -> Path | None:
    """OpenReview exposes the PDF at `/pdf?id=<id>` directly. Open access."""
    canonical = f"openreview-{openreview_id}.pdf"
    target = out_dir / canonical
    if target.exists() and _is_valid_pdf(target):
        print(f"[orev] cached {target.name}", flush=True)
        return target
    _clear_pending(out_dir)
    baseline = _snapshot_pdfs(out_dir)

    pdf_url = f"https://openreview.net/pdf?id={openreview_id}"
    print(f"[orev] pdf {pdf_url}", flush=True)
    driver.get(pdf_url)
    time.sleep(_STAMP_RENDER_WAIT)

    deadline = time.monotonic() + _DOWNLOAD_MAX_WAIT
    pdf = _wait_for_new_pdf(out_dir, baseline, deadline)
    if pdf is None:
        print(f"[orev] no PDF appeared for {openreview_id}", flush=True)
        return None
    return _finalise(pdf, canonical)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_ACM_DOI_RE = re.compile(r"/doi/(?:abs/|pdf/)?(10\.\d{4,9}/[^\s?#]+)")
_SPRINGER_DOI_RE = re.compile(
    r"link\.springer\.com/(?:article|chapter|content/pdf)/(10\.\d{4,9}/[^\s?#]+?)(?:\.pdf)?(?:[?#]|$)"
)


def _acm_doi_from_url(url: str) -> str | None:
    """Pull a DOI out of any of ACM's URL flavours (`/doi/`, `/doi/abs/`, `/doi/pdf/`)."""
    m = _ACM_DOI_RE.search(url)
    return m.group(1) if m else None


def _springer_doi_from_url(url: str) -> str | None:
    """Pull a DOI out of a SpringerLink article/chapter URL."""
    m = _SPRINGER_DOI_RE.search(url)
    return m.group(1) if m else None


def _doi_prefix_to_publisher(doi: str) -> str | None:
    """Map a DOI prefix to a publisher when the URL host is opaque.

    Useful for openalex.org / semanticscholar.org / api.crossref.org URLs
    where the host doesn't tell us anything but the DOI does. Covers the
    high-volume prefixes — anything else returns None so we don't fake
    confidence in publishers we haven't written a downloader for.
    """
    prefix = doi.split("/", 1)[0]
    return {
        "10.1109": "ieee",        # IEEE journals + conferences (DOI -> arnumber not directly resolvable; needs search)
        "10.1145": "acm",
        "10.1007": "springer",    # bulk of Springer journals + LNCS
        "10.1038": "springer",    # Nature family (Springer-published)
    }.get(prefix)


def _dispatch_paywalled(host: str, url: str, clean_doi: str | None) -> tuple[str, ...] | None:
    """VPN-gated publishers — IEEE / ACM / Springer."""
    if "ieeexplore.ieee.org" in host:
        arn = arnumber_from_url(url)
        return ("ieee", arn) if arn else None
    if "dl.acm.org" in host:
        resolved = clean_doi or _acm_doi_from_url(url)
        return ("acm", resolved) if resolved else None
    if "link.springer.com" in host:
        resolved = clean_doi or _springer_doi_from_url(url)
        return ("springer", resolved) if resolved else None
    return None


def _dispatch_open_access(host: str, url: str) -> tuple[str, ...] | None:
    """Open-access hosts — arXiv, ACL Anthology, NeurIPS, OpenReview."""
    if "arxiv.org" in host:
        aid = arxiv_id_from_url(url)
        return ("arxiv", aid) if aid else None
    if "aclanthology.org" in host:
        aid = acl_id_from_url(url)
        return ("acl", aid) if aid else None
    if "proceedings.neurips.cc" in host:
        pair = neurips_paper_from_url(url)
        return ("neurips", pair[0], pair[1]) if pair else None
    if "openreview.net" in host:
        oid = openreview_id_from_url(url)
        return ("openreview", oid) if oid else None
    return None


def _dispatch_by_doi_prefix(clean_doi: str) -> tuple[str, ...] | None:
    """Opaque host (openalex / semanticscholar) — pivot to DOI prefix.

    IEEE DOIs (10.1109/...) don't yield an arnumber directly so we return
    None — the caller has to resolve via Crossref + IEEE search first.
    """
    publisher = _doi_prefix_to_publisher(clean_doi)
    if publisher in {"acm", "springer"}:
        return (publisher, clean_doi)
    return None


def dispatch_for_url(url: str, doi: str | None) -> tuple[str, ...] | None:
    """Pick the right downloader for a paper's landing URL.

    Returns ``(publisher, *identifier_parts)`` where publisher is one of
    ``"ieee" / "acm" / "springer" / "arxiv" / "acl" / "neurips" /
    "openreview"`` and the trailing tuple is whatever the matching
    ``download_<publisher>`` function expects (arnumber for IEEE, DOI
    for ACM / Springer, arXiv ID for arXiv, anthology ID for ACL,
    ``(year, hash)`` for NeurIPS, forum ID for OpenReview). Falls back
    to extracting the DOI from the URL when the caller-supplied ``doi``
    is empty. Returns ``None`` when the URL is not routable.
    """
    if not url:
        return None
    host = url.split("/", 3)[2].lower() if "://" in url else ""
    clean_doi = (doi or "").strip() or None

    paywalled = _dispatch_paywalled(host, url, clean_doi)
    if paywalled is not None:
        return paywalled
    open_access = _dispatch_open_access(host, url)
    if open_access is not None:
        return open_access
    if clean_doi:
        return _dispatch_by_doi_prefix(clean_doi)
    return None
