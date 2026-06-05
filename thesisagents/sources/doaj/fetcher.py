"""DOAJ fetcher.

Endpoint:
- Search: GET https://doaj.org/api/search/articles/{query}?pageSize=N

DOAJ is the curated index of peer-reviewed open-access journal articles. No API
key, no authentication. Unusually, the search term goes in the URL **path**, not
a query parameter — so the keyword is percent-encoded into the path and only
``pageSize`` rides as a query parameter.

DOAJ has no documented year-range query operator, so (as with DBLP / Europe PMC)
year filtering is a deterministic post-filter on the parsed ``bibjson.year``; we
over-fetch 2× ``max_results`` and truncate afterwards.

Rate limit: DOAJ asks for no more than ~2 requests/second from a single client;
we stay at 2 req/s with a 1-request burst and jitter.
"""

from __future__ import annotations

from urllib.parse import quote

from thesisagents.core.exceptions import (
    ParseError,
    RateLimitError,
    SourceUnavailableError,
)
from thesisagents.core.models import Paper, Query
from thesisagents.fetchers.base import Fetcher, FetcherConfig
from thesisagents.fetchers.http import get_client
from thesisagents.fetchers.rate_limit import RateLimit
from thesisagents.utils.logging import get_logger

from .parser import in_year_range, parse_result

_LOG = get_logger(__name__)
_SOURCE_NAME = "doaj"
_SEARCH_BASE = "https://doaj.org/api/search/articles/"
_MAX_PAGE_SIZE = 100


class DoajFetcher(Fetcher):
    """Strategy implementation for DOAJ."""

    config = FetcherConfig(
        name=_SOURCE_NAME,
        rate_limit=RateLimit(requests_per_second=2.0, burst=1, jitter_seconds=0.3),
        requires_api_key=False,
        enabled_by_default=True,
    )

    async def search(self, query: Query) -> list[Paper]:
        # DOAJ takes the term in the path; safe="" so slashes/colons in the
        # keyword are encoded rather than splitting the path.
        url = f"{_SEARCH_BASE}{quote(query.keywords, safe='')}"
        params = self._build_search_params(query)
        data = await self._request(url, params=params)
        results = data.get("results") or []
        papers = [parse_result(item) for item in results]
        if query.year_from is not None or query.year_to is not None:
            papers = [
                p
                for p in papers
                if in_year_range(p.year, query.year_from, query.year_to)
            ]
        _LOG.info(
            "DOAJ returned %d papers for query=%r (max=%d)",
            len(papers),
            query.keywords,
            query.max_results,
        )
        return papers[: query.max_results]

    def _build_search_params(self, query: Query) -> dict[str, str]:
        page_size = min(query.max_results * 2, _MAX_PAGE_SIZE)
        return {"pageSize": str(page_size)}

    async def _request(self, url: str, *, params: dict[str, str]) -> dict:
        await self.bucket.acquire()
        client = await get_client(_SOURCE_NAME)
        try:
            response = await client.get(url, params=params)
        except Exception as err:
            raise SourceUnavailableError(
                _SOURCE_NAME, f"network error: {err}"
            ) from err
        if response.status_code == 429:
            raise RateLimitError(_SOURCE_NAME, "DOAJ rate limit hit")
        if response.status_code >= 500:
            raise RateLimitError(
                _SOURCE_NAME, f"transient server error {response.status_code}"
            )
        if response.status_code >= 400:
            raise ParseError(
                _SOURCE_NAME,
                f"client error {response.status_code}: {response.text[:256]}",
            )
        try:
            return response.json()
        except ValueError as err:
            raise ParseError(_SOURCE_NAME, f"invalid JSON: {err}") from err
