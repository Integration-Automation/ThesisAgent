"""CORE fetcher.

Endpoint:
- Search: GET https://api.core.ac.uk/v3/search/works?q=KEY&limit=N
          Authorization: Bearer <THESISAGENTS_CORE_API_KEY>

CORE is the largest open-access aggregator (250M+ works). The v3 API needs a
free key (https://core.ac.uk/services/api) passed as a Bearer token. The key is
read from ``THESISAGENTS_CORE_API_KEY`` — the SAME variable the OA resolver
already uses for PDF lookup, so a user who enabled CORE for PDF coverage gets
CORE search for free. Like Springer, the plugin loads but raises
:class:`ConfigError` at construction when no key is set, so the pipeline's
``load_fetcher`` silently skips it.

Year filtering is a deterministic post-filter on ``yearPublished`` (consistent
with the other plugins), so we over-fetch 2× ``max_results`` and truncate.

Rate limit: the free tier allows a few requests/second; we stay polite at
1 req/s with jitter.
"""

from __future__ import annotations

import os

from thesisagents.core.exceptions import (
    ConfigError,
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
_SOURCE_NAME = "core"
_API_KEY_ENV = "THESISAGENTS_CORE_API_KEY"  # noqa: S105  # nosec B105  # env var name, not a secret value
_SEARCH_ENDPOINT = "https://api.core.ac.uk/v3/search/works"
_MAX_LIMIT = 100


class CoreFetcher(Fetcher):
    """Strategy implementation for the CORE v3 API."""

    config = FetcherConfig(
        name=_SOURCE_NAME,
        rate_limit=RateLimit(requests_per_second=1.0, burst=1, jitter_seconds=0.3),
        requires_api_key=True,
        enabled_by_default=False,  # plugin: needs an API key
        opt_in_env_var=_API_KEY_ENV,
    )

    def __init__(self) -> None:
        super().__init__()
        # Fail at construction so load_fetcher catches the ConfigError and the
        # pipeline silently skips CORE when no key is set (same as Springer).
        self._api_key = (os.environ.get(_API_KEY_ENV) or "").strip() or None
        if self._api_key is None:
            raise ConfigError(
                f"CORE plugin requires {_API_KEY_ENV} "
                "— request a free key at https://core.ac.uk/services/api"
            )

    async def search(self, query: Query) -> list[Paper]:
        params = self._build_search_params(query)
        data = await self._request(_SEARCH_ENDPOINT, params=params)
        results = data.get("results") or []
        papers = [parse_result(item) for item in results]
        if query.year_from is not None or query.year_to is not None:
            papers = [
                p
                for p in papers
                if in_year_range(p.year, query.year_from, query.year_to)
            ]
        _LOG.info(
            "CORE returned %d papers for query=%r (max=%d)",
            len(papers),
            query.keywords,
            query.max_results,
        )
        return papers[: query.max_results]

    def _build_search_params(self, query: Query) -> dict[str, str]:
        limit = min(query.max_results * 2, _MAX_LIMIT)
        return {"q": query.keywords, "limit": str(limit)}

    async def _request(self, url: str, *, params: dict[str, str]) -> dict:
        await self.bucket.acquire()
        client = await get_client(_SOURCE_NAME)
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            response = await client.get(url, params=params, headers=headers)
        except Exception as err:
            raise SourceUnavailableError(
                _SOURCE_NAME, f"network error: {err}"
            ) from err
        if response.status_code == 401:
            raise ConfigError(
                f"CORE rejected the API key — check {_API_KEY_ENV}"
            )
        if response.status_code == 429:
            raise RateLimitError(_SOURCE_NAME, "CORE rate limit hit")
        if response.status_code >= 500:
            raise SourceUnavailableError(
                _SOURCE_NAME, f"server error {response.status_code}"
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
