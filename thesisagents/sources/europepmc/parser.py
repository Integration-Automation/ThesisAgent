"""Parse Europe PMC ``rest/search`` JSON results into ``Paper`` instances.

Europe PMC (https://europepmc.org) indexes PubMed/MEDLINE, PMC full text,
Agricola, preprint servers and patents. With ``resultType=core`` each hit in
``resultList.result[]`` carries title, an author list, journal/year metadata, a
DOI, an abstract, a cited-by count and (for open-access records) full-text URLs
— enough to populate every ``Paper`` field including ``pdf_url``.

The author list has two representations and we prefer the structured one:
``authorList.author[].fullName`` gives clean "First Last" names, whereas the
flat ``authorString`` ("Smith J, Doe A.") is an abbreviated fallback used only
when the structured list is absent.
"""

from __future__ import annotations

from typing import Any

from thesisagents.core.models import Paper

_SOURCE = "europepmc"


def parse_result(result: dict[str, Any]) -> Paper:
    """Map one entry from ``resultList.result[]`` to a ``Paper``."""
    title = (result.get("title") or "").strip().rstrip(".")
    authors = tuple(_authors(result))
    year = _to_int(result.get("pubYear")) or _to_int(
        (result.get("journalInfo") or {}).get("yearOfPublication")
    )
    venue = _venue(result)
    doi = (result.get("doi") or "").strip() or None
    abstract = (result.get("abstractText") or "").strip()
    citation_count = _to_int(result.get("citedByCount"))
    url = _article_url(result, doi)
    pdf_url = _pdf_url(result)
    source_id = (
        result.get("id")
        or result.get("pmid")
        or result.get("pmcid")
        or doi
        or url
    )
    return Paper(
        source=_SOURCE,
        source_id=str(source_id).strip(),
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        abstract=abstract,
        url=url,
        doi=doi,
        citation_count=citation_count,
        pdf_url=pdf_url,
        raw=result,
    )


def in_year_range(year: int | None, year_from: int | None, year_to: int | None) -> bool:
    """Return True if `year` is within [year_from, year_to] (None bounds = open).

    A paper with an unknown year is dropped when any bound is set — the same
    conservative behaviour the DBLP plugin uses, so a year filter never silently
    keeps undated records.
    """
    if year is None:
        return year_from is None and year_to is None
    if year_from is not None and year < year_from:
        return False
    return not (year_to is not None and year > year_to)


def _authors(result: dict[str, Any]) -> list[str]:
    author_block = (result.get("authorList") or {}).get("author")
    if isinstance(author_block, list):
        names = [
            (item.get("fullName") or "").strip()
            for item in author_block
            if isinstance(item, dict)
        ]
        names = [n for n in names if n]
        if names:
            return names
    # Fallback: the flat "Smith J, Doe A." string.
    flat = (result.get("authorString") or "").strip().rstrip(".")
    if not flat:
        return []
    return [part.strip() for part in flat.split(",") if part.strip()]


def _venue(result: dict[str, Any]) -> str | None:
    journal = (result.get("journalInfo") or {}).get("journal") or {}
    title = (journal.get("title") or "").strip()
    return title or None


def _article_url(result: dict[str, Any], doi: str | None) -> str:
    """Canonical Europe PMC article URL, falling back to a DOI resolver."""
    source = (result.get("source") or "").strip()
    ident = (result.get("id") or "").strip()
    if source and ident:
        return f"https://europepmc.org/article/{source}/{ident}"
    if doi:
        return f"https://doi.org/{doi}"
    return ""


def _pdf_url(result: dict[str, Any]) -> str | None:
    """First open-access PDF URL, if Europe PMC lists one."""
    urls = (result.get("fullTextUrlList") or {}).get("fullTextUrl") or []
    pdfs = [
        (entry.get("url") or "").strip()
        for entry in urls
        if isinstance(entry, dict) and entry.get("documentStyle") == "pdf"
    ]
    pdfs = [u for u in pdfs if u]
    return pdfs[0] if pdfs else None


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
