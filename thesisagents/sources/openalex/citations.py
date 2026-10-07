"""OpenAlex citation links.

Endpoints:
- Resolve a DOI: GET https://api.openalex.org/works/doi:{doi}?select=id
- References:    GET /works?filter=cited_by:{work_id}  (works cited by it)
- Cited by:      GET /works?filter=cites:{work_id}     (works that cite it)

The two filters read backwards at first sight, so in OpenAlex's own words:
``cited_by:W1`` is "works where it's cited by W1" and ``cites:W1`` is "works
where it cites W1".

No API key. ``mailto`` from ``THESISAGENTS_CONTACT_EMAIL`` joins the polite
pool, as for search. Rate limit: the search fetcher's.
"""

from __future__ import annotations

from thesisagents.core.exceptions import CitationNotAvailableError
from thesisagents.core.identifiers import canonical_doi
from thesisagents.core.models import Paper
from thesisagents.fetchers.citations import CitationProvider, get_json
from thesisagents.fetchers.rate_limit import TokenBucket

from .fetcher import _SELECT_FIELDS, OpenAlexFetcher
from .parser import parse_work

_SOURCE_NAME = "openalex"
_WORKS_ENDPOINT = "https://api.openalex.org/works"
_WORK_ID_PREFIX = "W"
_MAX_PER_PAGE = 50
#: Order of the citing works. A well-known paper has thousands of them and
#: only ``limit`` are fetched, so some order has to choose. Most-cited first
#: is stable from run to run and brings the established follow-up work. It is
#: not a relevance judgement: the snowball scores every discovered paper
#: against the user's keywords afterwards.
_CITED_BY_SORT = "cited_by_count:desc"


class OpenAlexCitations(CitationProvider):
    """Citation links from the OpenAlex works index."""

    name = _SOURCE_NAME

    def __init__(self) -> None:
        self._bucket = TokenBucket(OpenAlexFetcher.config.rate_limit)

    async def references(self, paper: Paper, limit: int) -> list[Paper]:
        return await self._linked(paper, "cited_by", limit, sort=None)

    async def cited_by(self, paper: Paper, limit: int) -> list[Paper]:
        return await self._linked(paper, "cites", limit, sort=_CITED_BY_SORT)

    async def _linked(
        self, paper: Paper, relation: str, limit: int, *, sort: str | None
    ) -> list[Paper]:
        work_id = await self._work_id(paper)
        params = {
            "filter": f"{relation}:{work_id}",
            "per-page": str(min(limit, _MAX_PER_PAGE)),
            "select": _SELECT_FIELDS,
            **self._polite(),
        }
        if sort:
            params["sort"] = sort
        data = await get_json(_SOURCE_NAME, self._bucket, _WORKS_ENDPOINT, params=params)
        return [parse_work(record) for record in data.get("results") or []][:limit]

    async def _work_id(self, paper: Paper) -> str:
        """OpenAlex work ID of ``paper``: its own, or looked up by DOI.

        A paper with neither is not resolvable here. OpenAlex does not index
        arXiv's own DOIs reliably (``doi:10.48550/arxiv.1706.03762`` answers
        404), so an arXiv-only record is left to another provider.
        """
        if paper.source == _SOURCE_NAME and paper.source_id.upper().startswith(
            _WORK_ID_PREFIX
        ):
            return paper.source_id
        doi = canonical_doi(paper.doi)
        if doi is None:
            raise CitationNotAvailableError(
                _SOURCE_NAME, "paper has no DOI and is not an OpenAlex record"
            )
        data = await get_json(
            _SOURCE_NAME,
            self._bucket,
            f"{_WORKS_ENDPOINT}/doi:{doi}",
            params={"select": "id", **self._polite()},
        )
        work_id = str(data.get("id") or "").rsplit("/", 1)[-1]
        if not work_id:
            raise CitationNotAvailableError(_SOURCE_NAME, "no work ID in the answer")
        return work_id

    @staticmethod
    def _polite() -> dict[str, str]:
        mailto = OpenAlexFetcher._mailto()  # noqa: SLF001  # same plugin, one env lookup
        return {"mailto": mailto} if mailto else {}
