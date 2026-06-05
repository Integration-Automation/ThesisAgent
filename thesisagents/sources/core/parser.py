"""Parse CORE ``v3/search/works`` JSON results into ``Paper`` instances.

CORE (https://core.ac.uk) is the world's largest aggregator of open-access
research papers (250M+ works), harvesting institutional and subject repositories
worldwide. The v3 API returns a ``results[]`` list where each work carries a
title, an author list (``[{"name": …}]``), the publication year, a DOI, an
abstract, and — crucially — a direct ``downloadUrl`` to the open-access PDF.

CORE does not expose per-paper citation counts in the search response, so
``citation_count`` stays ``None``.
"""

from __future__ import annotations

from typing import Any

from thesisagents.core.models import Paper

_SOURCE = "core"


def parse_result(result: dict[str, Any]) -> Paper:
    """Map one entry from ``results[]`` to a ``Paper``."""
    title = (result.get("title") or "").strip()
    authors = tuple(_authors(result.get("authors")))
    year = _to_int(result.get("yearPublished"))
    venue = _venue(result)
    doi = (result.get("doi") or "").strip() or None
    abstract = (result.get("abstract") or "").strip()
    work_id = result.get("id")
    url = _work_url(work_id, doi)
    pdf_url = (result.get("downloadUrl") or "").strip() or None
    source_id = str(work_id or doi or url).strip()
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
        raw=result,
    )


def in_year_range(year: int | None, year_from: int | None, year_to: int | None) -> bool:
    """Return True if `year` is within [year_from, year_to] (None bounds = open).

    Undated records are dropped only when a bound is set, matching the other
    post-filtering plugins.
    """
    if year is None:
        return year_from is None and year_to is None
    if year_from is not None and year < year_from:
        return False
    return not (year_to is not None and year > year_to)


def _authors(author_block: Any) -> list[str]:
    if not isinstance(author_block, list):
        return []
    names = [
        (item.get("name") or "").strip()
        for item in author_block
        if isinstance(item, dict)
    ]
    return [n for n in names if n]


def _venue(result: dict[str, Any]) -> str | None:
    journals = result.get("journals")
    if isinstance(journals, list):
        for journal in journals:
            if isinstance(journal, dict):
                title = (journal.get("title") or "").strip()
                if title:
                    return title
    publisher = (result.get("publisher") or "").strip()
    return publisher or None


def _work_url(work_id: Any, doi: str | None) -> str:
    if work_id:
        return f"https://core.ac.uk/works/{work_id}"
    return f"https://doi.org/{doi}" if doi else ""


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
