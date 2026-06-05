"""Europe PMC fetcher.

Endpoint:
- Search: GET https://www.ebi.ac.uk/europepmc/webservices/rest/search
          ?query=KEY&format=json&pageSize=N&resultType=core

Europe PMC is an open, key-free aggregator over PubMed/MEDLINE, PMC full text,
preprint servers, Agricola and patents. ``resultType=core`` returns the rich
record (abstract + author list + cited-by + full-text URLs) we need; the
cheaper ``lite`` result type omits abstracts, so we always ask for ``core``.

Year filtering is done in this fetcher (not via query syntax) for the same
reason as DBLP: Europe PMC's ``PUB_YEAR`` / ``FIRST_PDATE`` query operators have
subtle inclusivity rules across data sources, so a deterministic post-filter on
the parsed year is more predictable. We therefore over-fetch (``pageSize`` =
2× ``max_results``) and truncate after filtering.

Rate limit: Europe PMC asks callers to stay at or below ~10 requests/second.
We sit well under that at 5 req/s with a small burst.
"""

from __future__ import annotations

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
_SOURCE_NAME = "europepmc"
_SEARCH_ENDPOINT = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
_MAX_PAGE_SIZE = 1000


class EuropePmcFetcher(Fetcher):
    """Strategy implementation for Europe PMC."""

    config = FetcherConfig(
        name=_SOURCE_NAME,
        # 5 req/s with a 2-request burst — half of Europe PMC's stated 10 req/s
        # ceiling, with jitter to avoid synchronised bursts when several sources
        # run concurrently in the pipeline's asyncio.gather.
        rate_limit=RateLimit(requests_per_second=5.0, burst=2, jitter_seconds=0.2),
        requires_api_key=False,
        enabled_by_default=True,
    )

    async def search(self, query: Query) -> list[Paper]:
        params = self._build_search_params(query)
        data = await self._request(_SEARCH_ENDPOINT, params=params)
        results = (data.get("resultList") or {}).get("result") or []
        papers = [parse_result(item) for item in results]
        if query.year_from is not None or query.year_to is not None:
            papers = [
                p
                for p in papers
                if in_year_range(p.year, query.year_from, query.year_to)
            ]
        _LOG.info(
            "Europe PMC returned %d papers for query=%r (max=%d)",
            len(papers),
            query.keywords,
            query.max_results,
        )
        return papers[: query.max_results]

    def _build_search_params(self, query: Query) -> dict[str, str]:
        page_size = min(query.max_results * 2, _MAX_PAGE_SIZE)
        return {
            "query": query.keywords,
            "format": "json",
            "resultType": "core",
            "pageSize": str(page_size),
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
            raise RateLimitError(_SOURCE_NAME, "Europe PMC rate limit hit")
        if response.status_code >= 500:
            # Treat 5xx as transient throttling so the pipeline's exponential
            # backoff retries instead of failing the whole source.
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
