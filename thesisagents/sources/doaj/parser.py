"""Parse DOAJ ``search/articles`` JSON results into ``Paper`` instances.

DOAJ (Directory of Open Access Journals, https://doaj.org) indexes peer-reviewed
open-access journal articles. Every record nests its bibliographic data under a
``bibjson`` object: title, an author list, the journal, identifiers (DOI / ISSN)
and full-text links. DOAJ does not expose citation counts, so ``citation_count``
stays ``None`` and downstream rank-by-citation falls back gracefully.

Because every DOAJ article is by definition open access, the ``link`` list almost
always carries a fulltext URL — we surface a PDF link as ``pdf_url`` when the
content type advertises PDF, which lets the per-paper PDF download stage proceed
without a paywall hop.
"""

from __future__ import annotations

from typing import Any

from thesisagents.core.models import Paper

_SOURCE = "doaj"


def parse_result(result: dict[str, Any]) -> Paper:
    """Map one entry from ``results[]`` to a ``Paper``."""
    bib = result.get("bibjson") or {}
    title = (bib.get("title") or "").strip()
    authors = tuple(_authors(bib.get("author")))
    year = _to_int(bib.get("year"))
    venue = ((bib.get("journal") or {}).get("title") or "").strip() or None
    doi = _doi(bib.get("identifier"))
    abstract = (bib.get("abstract") or "").strip()
    article_id = (result.get("id") or "").strip()
    url = _article_url(article_id, bib.get("link"), doi)
    pdf_url = _pdf_url(bib.get("link"))
    source_id = (article_id or doi or url).strip()
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

    Undated records are dropped only when a bound is set, matching the DBLP /
    Europe PMC plugins so a year filter never silently keeps year-less papers.
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


def _doi(identifiers: Any) -> str | None:
    if not isinstance(identifiers, list):
        return None
    for ident in identifiers:
        if isinstance(ident, dict) and ident.get("type") == "doi":
            value = (ident.get("id") or "").strip()
            if value:
                return value
    return None


def _article_url(article_id: str, links: Any, doi: str | None) -> str:
    """Canonical DOAJ article URL, falling back to fulltext link then DOI."""
    if article_id:
        return f"https://doaj.org/article/{article_id}"
    fulltext = _first_link(links, lambda link: link.get("type") == "fulltext")
    if fulltext:
        return fulltext
    return f"https://doi.org/{doi}" if doi else ""


def _pdf_url(links: Any) -> str | None:
    """First fulltext link that advertises a PDF content type."""
    return _first_link(
        links,
        lambda link: "pdf" in (link.get("content_type") or "").lower(),
    )


def _first_link(links: Any, predicate) -> str | None:
    if not isinstance(links, list):
        return None
    for link in links:
        if isinstance(link, dict) and predicate(link):
            url = (link.get("url") or "").strip()
            if url:
                return url
    return None


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
