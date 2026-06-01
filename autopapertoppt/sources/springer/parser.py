"""Parse Springer Meta v2 records into ``Paper`` instances.

The meta JSON puts authors under ``creators[].creator`` as "Last, First"
strings, the title under ``title``, the abstract under ``abstract`` (HTML
allowed), the venue under ``publicationName``, the date under
``publicationDate`` (YYYY-MM-DD), and the DOI under ``doi``. URLs sit under
``url[]`` as ``{value, format, platform}``; we pick the HTML landing page.
"""

from __future__ import annotations

import re
from typing import Any

from autopapertoppt.core.models import Paper

_SOURCE = "springer"
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def parse_record(record: dict[str, Any]) -> Paper:
    """Map one ``records[]`` entry to a ``Paper``."""
    title = (record.get("title") or "").strip()
    authors = tuple(_authors(record.get("creators") or []))
    year = _year(record.get("publicationDate") or "")
    venue = (record.get("publicationName") or "").strip() or None
    abstract = _strip_html(record.get("abstract") or "")
    doi = (record.get("doi") or "").strip() or None
    url = _landing_url(record.get("url") or [], doi)
    source_id = (record.get("identifier") or doi or url or "").strip()
    citation_count = _to_int(record.get("citation_count"))
    return Paper(
        source=_SOURCE,
        source_id=source_id,
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        abstract=abstract,
        url=url,
        doi=doi,
        citation_count=citation_count,
        raw=record,
    )


def _authors(creators: list[Any]) -> list[str]:
    names: list[str] = []
    for entry in creators:
        if isinstance(entry, dict):
            raw = (entry.get("creator") or entry.get("name") or "").strip()
        else:
            raw = str(entry).strip()
        if not raw:
            continue
        if raw.count(",") == 1:
            family, given = (part.strip() for part in raw.split(","))
            if family and given:
                raw = f"{given} {family}"
        names.append(raw)
    return names


def _year(publication_date: str) -> int | None:
    head = publication_date.strip()[:4]
    if not head:
        return None
    try:
        return int(head)
    except ValueError:
        return None


def _landing_url(urls: list[dict[str, Any]], doi: str | None) -> str:
    html_url = ""
    fallback_url = ""
    for entry in urls:
        if not isinstance(entry, dict):
            continue
        fmt = (entry.get("format") or "").lower()
        value = (entry.get("value") or "").strip()
        if not value:
            continue
        if fmt == "html" and not html_url:
            html_url = value
        elif not fallback_url:
            fallback_url = value
    chosen = html_url or fallback_url
    if chosen:
        return chosen
    return f"https://doi.org/{doi}" if doi else ""


def _strip_html(value: str) -> str:
    stripped = _HTML_TAG_RE.sub("", value).strip()
    return " ".join(stripped.split())


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
