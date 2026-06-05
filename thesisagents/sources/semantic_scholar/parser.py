"""Map Semantic Scholar Graph API JSON into normalised Paper records."""

from __future__ import annotations

from typing import Any

from thesisagents.core.models import Paper

_SOURCE = "semantic_scholar"

#: The fields we request from the Graph API.
GRAPH_FIELDS = (
    "paperId,title,authors.name,year,venue,abstract,"
    "externalIds,citationCount,openAccessPdf,url"
)


def parse_paper(record: dict[str, Any]) -> Paper:
    """Convert one Graph-API record into a Paper."""
    external = record.get("externalIds") or {}
    doi = external.get("DOI") or None
    arxiv_id = external.get("ArXiv") or None
    paper_id = record.get("paperId") or ""
    pdf_obj = record.get("openAccessPdf") or {}
    pdf_url = pdf_obj.get("url") if isinstance(pdf_obj, dict) else None
    url = (
        record.get("url")
        or (f"https://www.semanticscholar.org/paper/{paper_id}" if paper_id else "")
    )
    authors = tuple(
        author.get("name", "")
        for author in record.get("authors") or []
        if author.get("name")
    )
    return Paper(
        source=_SOURCE,
        source_id=paper_id,
        title=record.get("title") or "",
        authors=authors,
        year=record.get("year"),
        venue=record.get("venue") or None,
        abstract=record.get("abstract") or "",
        url=url,
        doi=doi,
        arxiv_id=arxiv_id,
        citation_count=record.get("citationCount"),
        pdf_url=pdf_url,
        raw=record,
    )
