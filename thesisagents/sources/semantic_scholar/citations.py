"""Semantic Scholar citation links.

Endpoints (Graph API):
- References: GET /graph/v1/paper/{id}/references  -> rows of ``citedPaper``
- Cited by:   GET /graph/v1/paper/{id}/citations   -> rows of ``citingPaper``

``{id}`` is a Semantic Scholar paper ID, ``DOI:10.x/y`` or ``ARXIV:2401.x``.
Rate limit and API key (``THESISAGENTS_S2_API_KEY``) are the search fetcher's.
"""

from __future__ import annotations

import os
import re

from thesisagents.core.exceptions import CitationNotAvailableError
from thesisagents.core.identifiers import canonical_doi
from thesisagents.core.models import Paper
from thesisagents.fetchers.citations import CitationProvider, get_json
from thesisagents.fetchers.rate_limit import TokenBucket

from .fetcher import SemanticScholarFetcher
from .parser import parse_paper

_SOURCE_NAME = "semantic_scholar"
_PAPER_ENDPOINT = "https://api.semanticscholar.org/graph/v1/paper"
_API_KEY_ENV = "THESISAGENTS_S2_API_KEY"
#: The fields of the linked paper. The same set the search asks for, with one
#: difference: these two endpoints reject the dotted ``authors.name`` the
#: search endpoint accepts (HTTP 400 "Unrecognized or unsupported fields:
#: [authors.name]"). Plain ``authors`` returns the names as well.
_CITATION_FIELDS = (
    "paperId,title,authors,year,venue,abstract,"
    "externalIds,citationCount,openAccessPdf,url"
)
_MAX_LIMIT = 100
_VERSION_SUFFIX_RE = re.compile(r"v\d+$")


class SemanticScholarCitations(CitationProvider):
    """Citation links from the Semantic Scholar Graph API."""

    name = _SOURCE_NAME

    def __init__(self) -> None:
        self._bucket = TokenBucket(SemanticScholarFetcher.config.rate_limit)

    async def references(self, paper: Paper, limit: int) -> list[Paper]:
        return await self._linked(paper, "references", "citedPaper", limit)

    async def cited_by(self, paper: Paper, limit: int) -> list[Paper]:
        return await self._linked(paper, "citations", "citingPaper", limit)

    async def _linked(
        self, paper: Paper, edge: str, record_key: str, limit: int
    ) -> list[Paper]:
        headers: dict[str, str] = {}
        api_key = os.environ.get(_API_KEY_ENV)
        if api_key:
            headers["x-api-key"] = api_key
        data = await get_json(
            _SOURCE_NAME,
            self._bucket,
            f"{_PAPER_ENDPOINT}/{_paper_ref(paper)}/{edge}",
            params={"fields": _CITATION_FIELDS, "limit": str(min(limit, _MAX_LIMIT))},
            headers=headers,
        )
        papers: list[Paper] = []
        for row in data.get("data") or []:
            record = (row or {}).get(record_key) or {}
            # A reference Semantic Scholar could not resolve is listed as a
            # stub with no paperId and no title. It cannot be scored or
            # identified, so it is left out.
            if record.get("title"):
                papers.append(parse_paper(record))
        return papers[:limit]


def _paper_ref(paper: Paper) -> str:
    """The identifier Semantic Scholar accepts for ``paper``.

    Its own paper ID when the record came from Semantic Scholar, else the DOI,
    else the arXiv ID without a version suffix.

    Example: a Crossref record with ``doi="10.1145/3292500.3330701"`` becomes
    ``"DOI:10.1145/3292500.3330701"``.
    """
    if paper.source == _SOURCE_NAME and paper.source_id:
        return paper.source_id
    doi = canonical_doi(paper.doi)
    if doi:
        return f"DOI:{doi}"
    if paper.arxiv_id and paper.arxiv_id.strip():
        return f"ARXIV:{_VERSION_SUFFIX_RE.sub('', paper.arxiv_id.strip())}"
    raise CitationNotAvailableError(
        _SOURCE_NAME, "paper has no DOI, arXiv ID or Semantic Scholar ID"
    )
