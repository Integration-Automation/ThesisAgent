"""Convert one Crossref ``message`` record into a Paper.

Crossref returns HTML-tagged abstracts (``<jats:p>...</jats:p>``); we strip
the tags so downstream exporters get plain text.
"""

from __future__ import annotations

import re
from typing import Any

from autopapertoppt.core.models import Paper

_SOURCE = "acm"
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_ACM_PUBLISHER_HINTS = ("ACM", "Association for Computing Machinery")


def parse_record(record: dict[str, Any], *, source: str = _SOURCE) -> Paper:
    """Map one Crossref message item to a Paper."""
    title = _first_string(record.get("title")) or ""
    authors = tuple(_author_name(a) for a in record.get("author") or [] if _author_name(a))
    year = _extract_year(record)
    abstract = _strip_html(record.get("abstract") or "")
    doi = record.get("DOI") or None
    url = record.get("URL") or (f"https://doi.org/{doi}" if doi else "")
    venue = (
        _first_string(record.get("container-title"))
        or record.get("publisher")
        or None
    )
    citation_count = record.get("is-referenced-by-count")
    pdf_url = _pick_pdf_link(record.get("link") or [])
    return Paper(
        source=source,
        source_id=doi or "",
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        abstract=abstract,
        url=url,
        doi=doi,
        citation_count=citation_count,
        pdf_url=pdf_url,
        raw=record,
    )


def _pick_pdf_link(links: list[dict[str, Any]]) -> str | None:
    """Pull a direct PDF URL from Crossref's ``link[]`` array.

    Crossref lets publishers (including ACM and IEEE) list multiple
    syndication URLs per work. We prefer entries with
    ``content-type == 'application/pdf'`` — when present those point at
    the publisher-served PDF (often paywalled, but worth trying with the
    downloader's browser-style headers).
    """
    for entry in links:
        if not isinstance(entry, dict):
            continue
        ctype = (entry.get("content-type") or "").lower()
        url_value = (entry.get("URL") or "").strip()
        if ctype == "application/pdf" and url_value:
            return url_value
    return None


def is_acm_record(record: dict[str, Any]) -> bool:
    """Belt-and-braces filter — Crossref's `filter=member:320` should already
    keep ACM-only, but a tiny number of bibliographic entries slip through with
    different publishers, so we double-check by publisher string."""
    publisher = (record.get("publisher") or "").strip()
    if not publisher:
        return True
    return any(hint.lower() in publisher.lower() for hint in _ACM_PUBLISHER_HINTS)


def _first_string(value: Any) -> str | None:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item.strip()
        return None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _author_name(author: dict[str, Any]) -> str:
    given = (author.get("given") or "").strip()
    family = (author.get("family") or "").strip()
    if given and family:
        return f"{given} {family}"
    return family or given or (author.get("name") or "").strip()


def _extract_year(record: dict[str, Any]) -> int | None:
    for key in ("published-print", "published-online", "issued", "created"):
        date_parts = (record.get(key) or {}).get("date-parts") or []
        if date_parts and date_parts[0]:
            year = date_parts[0][0]
            if isinstance(year, int):
                return year
    return None


def _strip_html(value: str) -> str:
    stripped = _HTML_TAG_RE.sub("", value).strip()
    return " ".join(stripped.split())
