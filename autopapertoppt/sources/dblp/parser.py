"""Parse DBLP `publ/api` JSON hits into `Paper` instances.

DBLP returns very compact bibliographic data — no abstracts and no citation
counts. We populate the `Paper` with what's available and leave the rest as
the model defaults; downstream rank-by-citation falls back gracefully when
the count is missing.
"""

from __future__ import annotations

from typing import Any

from autopapertoppt.core.models import Paper

_SOURCE = "dblp"


def parse_hit(hit: dict[str, Any]) -> Paper:
    """Map one entry from ``result.hits.hit[].info`` to a ``Paper``."""
    info = hit.get("info") or {}
    title = (info.get("title") or "").strip().rstrip(".")
    authors = tuple(_authors(info.get("authors") or {}))
    year = _to_int(info.get("year"))
    venue = (info.get("venue") or "").strip() or None
    doi = (info.get("doi") or "").strip() or None
    url = (info.get("ee") or info.get("url") or "").strip()
    if not url and doi:
        url = f"https://doi.org/{doi}"
    source_id = (hit.get("@id") or info.get("key") or doi or url).strip()
    return Paper(
        source=_SOURCE,
        source_id=source_id,
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        abstract="",
        url=url,
        doi=doi,
        raw=hit,
    )


def in_year_range(year: int | None, year_from: int | None, year_to: int | None) -> bool:
    """Return True if `year` is within [year_from, year_to] (None = open)."""
    if year is None:
        return False
    if year_from is not None and year < year_from:
        return False
    return not (year_to is not None and year > year_to)


def _authors(authors_block: dict[str, Any]) -> list[str]:
    raw = authors_block.get("author")
    if raw is None:
        return []
    items = raw if isinstance(raw, list) else [raw]
    names: list[str] = []
    for item in items:
        text = (
            (item.get("text") or "").strip()
            if isinstance(item, dict)
            else str(item).strip()
        )
        if text:
            names.append(text)
    return names


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
