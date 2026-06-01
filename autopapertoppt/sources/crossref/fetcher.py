"""Crossref (direct) fetcher.

Endpoints:
- Search: GET https://api.crossref.org/works?query=KEY&rows=N
- By DOI: GET https://api.crossref.org/works/{doi}

Distinct from the ``acm`` plugin: that one is scoped to ``member:320`` so
results are only ACM papers. This plugin runs an unscoped Crossref search and
returns DOIs from every publisher Crossref indexes — Nature, Springer, IEEE,
Elsevier, ACM, university presses. We rely on the top-tier venue whitelist
downstream to keep the noise down.

No API key required. Polite-pool: ``mailto=<email>`` from
``AUTOPAPERTOPPT_CONTACT_EMAIL``. Subscribers can attach
``AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN`` for higher rate-limit + fresher cache.

Rate limit: Crossref publishes ~50 req/s in the polite pool; we stay under 2.
"""

from __future__ import annotations

import os
from typing import Any

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

from .parser import parse_record

_LOG = get_logger(__name__)
_SOURCE_NAME = "crossref"
_WORKS_ENDPOINT = "https://api.crossref.org/works"
_WORK_ENDPOINT = "https://api.crossref.org/works/{doi}"
_PLUS_TOKEN_ENV = "AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN"  # noqa: S105  # nosec B105  # env var name, not a secret value
_CONTACT_ENV = "AUTOPAPERTOPPT_CONTACT_EMAIL"
_MAX_ROWS_PER_PAGE = 100


class CrossrefFetcher(Fetcher):
    """Strategy implementation for the Crossref REST API (unscoped)."""

    config = FetcherConfig(
        name=_SOURCE_NAME,
        rate_limit=RateLimit(requests_per_second=2.0, burst=2, jitter_seconds=0.1),
        requires_api_key=False,
        enabled_by_default=False,  # plugin: needs explicit --source crossref
    )

    async def search(self, query: Query) -> list[Paper]:
        params = self._build_search_params(query)
        data = await self._request_json(_WORKS_ENDPOINT, params=params)
        items = (data.get("message") or {}).get("items", [])
        papers = [parse_record(item) for item in items]
        _LOG.info(
            "Crossref returned %d papers for query=%r (max=%d)",
            len(papers),
            query.keywords,
            query.max_results,
        )
        return papers[: query.max_results]

    async def fetch_by_id(self, identifier: str) -> Paper:
        doi = identifier.strip()
        if not doi.startswith("10."):
            raise ParseError(_SOURCE_NAME, f"identifier is not a DOI: {identifier!r}")
        data = await self._request_json(_WORK_ENDPOINT.format(doi=doi))
        message = data.get("message")
        if not message:
            raise ParseError(_SOURCE_NAME, f"no Crossref message for DOI {doi}")
        return parse_record(message)

    def _build_search_params(self, query: Query) -> dict[str, str]:
        filters: list[str] = []
        if query.year_from is not None:
            filters.append(f"from-pub-date:{query.year_from}")
        if query.year_to is not None:
            filters.append(f"until-pub-date:{query.year_to}")
        params: dict[str, str] = {
            "query": query.keywords,
            "rows": str(min(query.max_results, _MAX_ROWS_PER_PAGE)),
        }
        if filters:
            params["filter"] = ",".join(filters)
        mailto = (os.environ.get(_CONTACT_ENV) or "").strip()
        if mailto:
            params["mailto"] = mailto
        return params

    async def _request_json(
        self, url: str, *, params: dict[str, str] | None = None
    ) -> dict[str, Any]:
        await self.bucket.acquire()
        client = await get_client(_SOURCE_NAME)
        headers: dict[str, str] = {}
        plus_token = (os.environ.get(_PLUS_TOKEN_ENV) or "").strip()
        if plus_token:
            headers["Crossref-Plus-API-Token"] = f"Bearer {plus_token}"
        try:
            response = await client.get(url, params=params or {}, headers=headers)
        except Exception as err:
            raise SourceUnavailableError(
                _SOURCE_NAME, f"network error: {err}"
            ) from err
        if response.status_code == 429:
            raise RateLimitError(_SOURCE_NAME, "Crossref rate limit hit")
        if response.status_code == 404:
            raise ParseError(_SOURCE_NAME, "DOI not found at Crossref")
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
