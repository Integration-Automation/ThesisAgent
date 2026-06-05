"""Parse HAL ``search`` Solr JSON docs into ``Paper`` instances.

HAL (Hyper Articles en Ligne, https://hal.science) is France's national open
archive — strong in CS, mathematics and physics, with full-text PDFs for most
deposits. Its API is a thin Solr wrapper: each hit in ``response.docs[]`` is a
flat field bag where most fields are **arrays** even when single-valued
(``title_s``, ``abstract_s``, ``authFullName_s``). The parser therefore unwraps
array-or-scalar fields defensively via :func:`_first`.

HAL does not expose citation counts, so ``citation_count`` stays ``None``.
"""

from __future__ import annotations

from typing import Any

from thesisagents.core.models import Paper

_SOURCE = "hal"

# The Solr fields we request via ``fl`` — must stay in sync with the fetcher's
# field list so a doc always carries what the parser reads.
FIELDS: tuple[str, ...] = (
    "docid",
    "title_s",
    "authFullName_s",
    "producedDateY_i",
    "journalTitle_s",
    "doiId_s",
    "abstract_s",
    "uri_s",
    "fileMain_s",
)


def parse_doc(doc: dict[str, Any]) -> Paper:
    """Map one entry from ``response.docs[]`` to a ``Paper``."""
    title = (_first(doc.get("title_s")) or "").strip()
    authors = tuple(
        name.strip()
        for name in (doc.get("authFullName_s") or [])
        if isinstance(name, str) and name.strip()
    )
    year = _to_int(doc.get("producedDateY_i"))
    venue = (_first(doc.get("journalTitle_s")) or "").strip() or None
    doi = (_first(doc.get("doiId_s")) or "").strip() or None
    abstract = (_first(doc.get("abstract_s")) or "").strip()
    url = (_first(doc.get("uri_s")) or "").strip()
    pdf_url = (_first(doc.get("fileMain_s")) or "").strip() or None
    if not url and doi:
        url = f"https://doi.org/{doi}"
    source_id = str(doc.get("docid") or doi or url).strip()
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
        pdf_url=pdf_url,
        raw=doc,
    )


def in_year_range(year: int | None, year_from: int | None, year_to: int | None) -> bool:
    """Return True if `year` is within [year_from, year_to] (None bounds = open).

    Undated records are dropped only when a bound is set, matching the other
    post-filtering plugins so a year filter never silently keeps year-less docs.
    """
    if year is None:
        return year_from is None and year_to is None
    if year_from is not None and year < year_from:
        return False
    return not (year_to is not None and year > year_to)


def _first(value: Any) -> Any:
    """Return the first element of a Solr array field, or the value itself."""
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _to_int(value: Any) -> int | None:
    value = _first(value)
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
