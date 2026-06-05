"""Parse Crossref `/works` message items into `Paper` instances.

Crossref returns HTML-tagged abstracts (``<jats:p>...</jats:p>``); we strip
the tags so downstream exporters get plain text. The shape is identical to
what the ACM plugin's parser handles — we re-implement here rather than
import from the ACM plugin so the two plugins stay independent (failure
isolation: a Crossref-direct schema tweak must not break ``--source acm``).
"""

from __future__ import annotations

import re
from typing import Any

from thesisagents.core.models import Paper

_SOURCE = "crossref"
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def parse_record(record: dict[str, Any]) -> Paper:
    """Map one Crossref message item to a ``Paper``."""
    title = _first_string(record.get("title")) or ""
    authors = tuple(
        _author_name(a) for a in record.get("author") or [] if _author_name(a)
    )
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
        source=_SOURCE,
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

    Each entry has ``URL`` + ``content-type``; we only take entries that
    advertise ``application/pdf`` so we don't fall back on landing-page
    HTML that the downloader would reject as ``not_pdf``.
    """
    for entry in links:
        if not isinstance(entry, dict):
            continue
        ctype = (entry.get("content-type") or "").lower()
        url_value = (entry.get("URL") or "").strip()
        if ctype == "application/pdf" and url_value:
            return url_value
    return None


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
