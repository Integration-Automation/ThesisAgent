"""OpenAIRE Graph fetcher.

Endpoint:
- Search: GET https://api.openaire.eu/graph/v1/researchProducts
    ?search=KEY&pageSize=N&sortBy=publicationDate,desc

OpenAIRE is the EU-backed open scholarly graph. It harvests metadata from
thousands of repositories and publishers, so it's particularly strong for
finding OA mirrors of paywalled Nature / Springer / Elsevier articles.

No API key required. Rate limit: OpenAIRE's docs cite ~7200 requests/hour
(2/s) for anonymous users; we stay under 2 req/s with jitter.
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

from .parser import parse_product

_LOG = get_logger(__name__)
_SOURCE_NAME = "openaire"
_SEARCH_ENDPOINT = "https://api.openaire.eu/graph/v1/researchProducts"
_MAX_PAGE_SIZE = 100


class OpenAireFetcher(Fetcher):
    """Strategy implementation for the OpenAIRE Graph API."""

    config = FetcherConfig(
        name=_SOURCE_NAME,
        rate_limit=RateLimit(requests_per_second=2.0, burst=2, jitter_seconds=0.2),
        requires_api_key=False,
        enabled_by_default=False,  # plugin: needs explicit --source openaire
    )

    async def search(self, query: Query) -> list[Paper]:
        params = self._build_search_params(query)
        data = await self._request(_SEARCH_ENDPOINT, params=params)
        results = data.get("results") or []
        papers = [parse_product(record) for record in results]
        _LOG.info(
            "OpenAIRE returned %d papers for query=%r (max=%d)",
            len(papers),
            query.keywords,
            query.max_results,
        )
        return papers[: query.max_results]

    def _build_search_params(self, query: Query) -> dict[str, str]:
        page_size = min(query.max_results, _MAX_PAGE_SIZE)
        params: dict[str, str] = {
            "search": query.keywords,
            "pageSize": str(page_size),
            # OpenAIRE expects "<field> <ASC|DESC>" (space-separated). The
            # comma-separated form returns HTTP 400.
            "sortBy": "publicationDate DESC",
            # Articles only — exclude datasets, software, "other research products".
            "type": "publication",
        }
        if query.year_from is not None:
            params["fromPublicationDate"] = f"{query.year_from}-01-01"
        if query.year_to is not None:
            params["toPublicationDate"] = f"{query.year_to}-12-31"
        return params

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
            raise RateLimitError(_SOURCE_NAME, "OpenAIRE rate limit hit")
        if response.status_code >= 500:
            raise SourceUnavailableError(
                _SOURCE_NAME, f"server error {response.status_code}"
            )
        if response.status_code == 404:
            raise ParseError(_SOURCE_NAME, "endpoint not found")
        if response.status_code >= 400:
            raise ParseError(
                _SOURCE_NAME,
                f"client error {response.status_code}: {response.text[:256]}",
            )
        try:
            return response.json()
        except ValueError as err:
            raise ParseError(_SOURCE_NAME, f"invalid JSON: {err}") from err
