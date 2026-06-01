"""DBLP fetcher.

Endpoint:
- Search: GET https://dblp.org/search/publ/api?q=KEY&format=json&h=N

DBLP is the de-facto CS bibliography. No API key, no authentication. The
``publ`` endpoint returns publication metadata; we get the JSON variant via
``format=json``. Year filtering is not directly supported by the API — we
post-filter in the parser layer because DBLP's `year:YYYY` operator only
matches exact years and the operator's behaviour is undocumented for ranges.

Rate limit: DBLP has no published per-second cap but their ops page asks for
"reasonable" use; we stay under 2 req/s with a small burst.
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

from .parser import in_year_range, parse_hit

_LOG = get_logger(__name__)
_SOURCE_NAME = "dblp"
_SEARCH_ENDPOINT = "https://dblp.org/search/publ/api"
_MAX_HITS_PER_PAGE = 1000


class DblpFetcher(Fetcher):
    """Strategy implementation for DBLP."""

    config = FetcherConfig(
        name=_SOURCE_NAME,
        # DBLP rejects sustained traffic with transient 5xx from a single IP.
        # 1 req per 2s with jitter stays well below the threshold I've
        # observed in practice.
        rate_limit=RateLimit(requests_per_second=0.5, burst=1, jitter_seconds=0.3),
        requires_api_key=False,
        enabled_by_default=False,  # plugin: needs explicit --source dblp
    )

    async def search(self, query: Query) -> list[Paper]:
        params = self._build_search_params(query)
        data = await self._request(_SEARCH_ENDPOINT, params=params)
        hits = (
            (data.get("result") or {})
            .get("hits", {})
            .get("hit", [])
        )
        papers = [parse_hit(hit) for hit in hits]
        if query.year_from is not None or query.year_to is not None:
            papers = [
                p for p in papers
                if in_year_range(p.year, query.year_from, query.year_to)
            ]
        _LOG.info(
            "DBLP returned %d papers for query=%r (max=%d)",
            len(papers),
            query.keywords,
            query.max_results,
        )
        return papers[: query.max_results]

    def _build_search_params(self, query: Query) -> dict[str, str]:
        per_page = min(query.max_results * 2, _MAX_HITS_PER_PAGE)
        return {
            "q": query.keywords,
            "format": "json",
            "h": str(per_page),
        }

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
            raise RateLimitError(_SOURCE_NAME, "DBLP rate limit hit")
        if response.status_code >= 500:
            # DBLP's FAQ explicitly notes the search API returns transient
            # 5xx when the service is heavily loaded — treat 5xx as a soft
            # rate-limit so the pipeline's exponential-backoff retry kicks
            # in instead of failing the whole source.
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
