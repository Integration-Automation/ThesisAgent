"""Fetch a paper's PDF over HTTPS-only and extract its text.

We reuse the shared per-source HTTPS-only client so the same rate limiter
and TLS guardrails apply. Output is plain text, joined per page, capped at
``MAX_PDF_CHARS`` so a malicious 1000-page PDF cannot blow out the LLM
context window.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from autopapertoppt.core.exceptions import FetchError, ParseError, SourceUnavailableError
from autopapertoppt.fetchers.http import get_client
from autopapertoppt.utils.logging import get_logger

_LOG = get_logger(__name__)

MAX_PDF_BYTES: int = 20_000_000   # 20 MB hard cap on the downloaded file
MAX_PDF_PAGES: int = 60           # truncate at 60 pages — far past every paper we'd care about
MAX_PDF_CHARS: int = 80_000       # keep the extracted text below this many chars


@dataclass(frozen=True, slots=True)
class ExtractedPdf:
    """Result of a successful fetch + extract."""

    url: str
    page_count: int
    chars: int
    text: str


async def fetch_and_extract(pdf_url: str, source: str = "intelligence") -> ExtractedPdf:
    """Download ``pdf_url`` and return its concatenated text.

    Raises ``FetchError`` subclasses on network / status problems and
    ``ParseError`` when the bytes don't decode as a PDF.
    """
    if not pdf_url:
        raise ParseError(source, "no pdf_url supplied")
    client = await get_client(source)
    try:
        response = await client.get(pdf_url, headers={"Accept": "application/pdf"})
    except Exception as err:
        raise SourceUnavailableError(source, f"network error: {err}") from err
    if response.status_code == 429:
        raise FetchError(source, "PDF host rate-limited the request")
    if response.status_code >= 500:
        raise SourceUnavailableError(source, f"server error {response.status_code}")
    if response.status_code >= 400:
        raise ParseError(
            source, f"PDF host returned {response.status_code}"
        )
    body = response.content
    if len(body) > MAX_PDF_BYTES:
        raise ParseError(
            source,
            f"PDF exceeds {MAX_PDF_BYTES:,} byte cap ({len(body):,} bytes)",
        )
    content_type = response.headers.get("content-type", "").lower()
    if "pdf" not in content_type and not body.startswith(b"%PDF"):
        raise ParseError(source, f"response is not a PDF (content-type={content_type!r})")
    text, page_count = _extract_text(body, source)
    if len(text) > MAX_PDF_CHARS:
        text = text[:MAX_PDF_CHARS]
    _LOG.info(
        "PDF extracted: url=%s pages=%d chars=%d", pdf_url, page_count, len(text)
    )
    return ExtractedPdf(url=pdf_url, page_count=page_count, chars=len(text), text=text)


def _extract_text(body: bytes, source: str) -> tuple[str, int]:
    try:
        from pypdf import PdfReader  # imported lazily so the dep is truly optional
    except ImportError as err:
        raise ParseError(
            source,
            "pypdf is not installed; run `pip install autopapertoppt[intelligence]`",
        ) from err
    try:
        reader = PdfReader(io.BytesIO(body))
    except Exception as err:
        raise ParseError(source, f"pypdf could not open the file: {err}") from err
    chunks: list[str] = []
    pages = list(reader.pages)[:MAX_PDF_PAGES]
    for page in pages:
        try:
            text = page.extract_text() or ""
        except Exception as err:    # noqa: BLE001  # pypdf raises various sub-exceptions
            _LOG.debug("pypdf failed on a page: %s", err)
            continue
        if text.strip():
            chunks.append(text)
    if not chunks:
        raise ParseError(source, "pypdf extracted zero text from the PDF")
    joined = "\n\n".join(chunks)
    return _normalise(joined), len(pages)


def _normalise(text: str) -> str:
    """Collapse runs of whitespace and stray PDF line-wrap artefacts."""
    # rejoin hard-wrapped lines: "exam-\nple" → "example"
    text = text.replace("-\n", "")
    # collapse single newlines inside paragraphs to spaces; keep blank lines
    out_lines: list[str] = []
    current: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped:
            current.append(stripped)
        else:
            if current:
                out_lines.append(" ".join(current))
                current = []
    if current:
        out_lines.append(" ".join(current))
    return "\n\n".join(out_lines)
