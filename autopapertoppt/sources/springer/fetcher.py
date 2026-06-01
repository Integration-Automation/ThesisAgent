"""Springer Nature fetcher.

Endpoint:
- Meta v2 JSON: GET https://api.springernature.com/meta/v2/json
    ?q=KEY&p=N&s=START&api_key=KEY

Requires a free API key from https://dev.springernature.com/. The key is
read from ``AUTOPAPERTOPPT_SPRINGER_API_KEY``. The plugin loads but the
``search`` call raises :class:`ConfigError` when no key is set so callers
get a clear error rather than a silent failure.

Coverage: Nature, Scientific Reports, Lecture Notes in Computer Science, all
Springer subscription journals. The ``meta`` endpoint returns abstracts +
authors + the canonical landing URL. PDFs are NOT included — even OA
Springer articles redirect through their HTML page first; ``best_oa_location``
from OpenAlex is the usual route to the bytes.

Rate limit: 5000 requests/day / 300 per 5 min (75/min ~ 1.25/s). We stay
under 1 req/s to leave headroom.
"""

from __future__ import annotations

import os

from autopapertoppt.core.exceptions import (
    ConfigError,
    ParseError,
    RateLimitError,
    SourceUnavailableError,
)
from autopapertoppt.core.models import Paper, Query
from autopapertoppt.fetchers.base import Fetcher, FetcherConfig
from autopapertoppt.fetchers.http import get_client
from autopapertoppt.fetchers.rate_limit import RateLimit
from autopapertoppt.utils.logging import get_logger

from .parser import parse_record

_LOG = get_logger(__name__)
_SOURCE_NAME = "springer"
_API_KEY_ENV = "AUTOPAPERTOPPT_SPRINGER_API_KEY"  # noqa: S105  # nosec B105  # env var name, not a secret value
_SEARCH_ENDPOINT = "https://api.springernature.com/meta/v2/json"
_MAX_PAGE_SIZE = 50


class SpringerFetcher(Fetcher):
    """Strategy implementation for the Springer Meta API."""

    config = FetcherConfig(
        name=_SOURCE_NAME,
        rate_limit=RateLimit(requests_per_second=1.0, burst=1, jitter_seconds=0.2),
        requires_api_key=True,
        enabled_by_default=False,  # plugin: needs explicit --source springer + API key
        opt_in_env_var=_API_KEY_ENV,
    )

    def __init__(self) -> None:
        super().__init__()
        # Fail at construction time so the pipeline's load_fetcher catches
        # the ConfigError and silently skips Springer when no key is set —
        # the same pattern the IEEE plugin uses.
        self._api_key = (os.environ.get(_API_KEY_ENV) or "").strip() or None
        if self._api_key is None:
            raise ConfigError(
                f"Springer plugin requires {_API_KEY_ENV} "
                "— request a free key at https://dev.springernature.com/"
            )

    async def search(self, query: Query) -> list[Paper]:
        params = self._build_search_params(query, self._api_key)
        data = await self._request(_SEARCH_ENDPOINT, params=params)
        records = data.get("records") or []
        papers = [parse_record(record) for record in records]
        _LOG.info(
            "Springer returned %d papers for query=%r (max=%d)",
            len(papers),
            query.keywords,
            query.max_results,
        )
        return papers[: query.max_results]

    def _build_search_params(self, query: Query, api_key: str) -> dict[str, str]:
        per_page = min(query.max_results, _MAX_PAGE_SIZE)
        q_parts: list[str] = [query.keywords]
        if query.year_from is not None and query.year_to is not None:
            q_parts.append(
                f"datefrom:{query.year_from}-01-01 dateto:{query.year_to}-12-31"
            )
        elif query.year_from is not None:
            q_parts.append(f"datefrom:{query.year_from}-01-01")
        elif query.year_to is not None:
            q_parts.append(f"dateto:{query.year_to}-12-31")
        return {
            "q": " ".join(q_parts),
            "p": str(per_page),
            "s": "1",
            "api_key": api_key,
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
        if response.status_code == 401:
            raise ConfigError(
                f"Springer rejected the API key — check {_API_KEY_ENV}"
            )
        if response.status_code == 429:
            raise RateLimitError(_SOURCE_NAME, "Springer rate limit hit")
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
