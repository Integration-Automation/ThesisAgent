"""arXiv fetcher.

Source: https://export.arxiv.org/api/query
Format: Atom feed (XML), parsed via defusedxml.
Rate limit: arXiv asks for ~1 request per 3 seconds in their robots /
            API guide; we err on the side of caution.
No API key required.
"""

from __future__ import annotations

from autopapertoppt.core.exceptions import (
    ParseError,
    RateLimitError,
    SourceUnavailableError,
)
from autopapertoppt.core.models import Paper, Query
from autopapertoppt.fetchers.base import Fetcher, FetcherConfig
from autopapertoppt.fetchers.http import get_client
from autopapertoppt.fetchers.rate_limit import RateLimit
from autopapertoppt.utils.logging import get_logger

from .parser import parse_atom_feed

_LOG = get_logger(__name__)
_ENDPOINT = "https://export.arxiv.org/api/query"
_SOURCE_NAME = "arxiv"


class ArxivFetcher(Fetcher):
    """Strategy implementation for arXiv."""

    config = FetcherConfig(
        name=_SOURCE_NAME,
        rate_limit=RateLimit(requests_per_second=1 / 3, burst=1, jitter_seconds=0.5),
        requires_api_key=False,
        enabled_by_default=True,
    )

    async def search(self, query: Query) -> list[Paper]:
        params = self._build_params(query)
        text = await self._request(params)
        papers = parse_atom_feed(text)
        if query.year_from is not None or query.year_to is not None:
            papers = [
                paper
                for paper in papers
                if _year_in_range(paper.year, query.year_from, query.year_to)
            ]
        _LOG.info(
            "arXiv returned %d papers for query=%r (max=%d)",
            len(papers),
            query.keywords,
            query.max_results,
        )
        return papers[: query.max_results]

    async def fetch_by_id(self, identifier: str) -> Paper:
        text = await self._request({"id_list": identifier, "max_results": "1"})
        papers = parse_atom_feed(text)
        if not papers:
            raise ParseError(
                _SOURCE_NAME, f"no entry returned for arXiv id {identifier!r}"
            )
        _LOG.info("arXiv resolved id %s", identifier)
        return papers[0]

    async def _request(self, params: dict[str, str]) -> str:
        await self.bucket.acquire()
        client = await get_client(_SOURCE_NAME)
        try:
            response = await client.get(_ENDPOINT, params=params)
        except Exception as err:
            raise SourceUnavailableError(_SOURCE_NAME, f"network error: {err}") from err
        if response.status_code == 429:
            # Route 429 through RateLimitError so the pipeline's retry-with-
            # backoff path picks it up. Other 4xx codes stay as ParseError.
            raise RateLimitError(_SOURCE_NAME, "arXiv rate limit hit")
        if response.status_code >= 500:
            raise SourceUnavailableError(
                _SOURCE_NAME, f"server error {response.status_code}"
            )
        if response.status_code >= 400:
            raise ParseError(
                _SOURCE_NAME,
                f"client error {response.status_code}: {response.text[:256]}",
            )
        return response.text

    @staticmethod
    def _build_params(query: Query) -> dict[str, str]:
        return {
            "search_query": f"all:{query.keywords}",
            "start": "0",
            "max_results": str(query.max_results),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }


def _year_in_range(
    year: int | None, year_from: int | None, year_to: int | None
) -> bool:
    if year is None:
        return False
    if year_from is not None and year < year_from:
        return False
    return not (year_to is not None and year > year_to)
