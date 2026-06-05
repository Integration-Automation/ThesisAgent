"""ACM Digital Library via the Crossref REST API.

Crossref's free public API
(`https://api.crossref.org/works`) indexes every ACM DOI. Filtering by
``member:320`` restricts results to the Association for Computing Machinery.
Year filters are supported via ``filter=from-pub-date:YYYY,until-pub-date:YYYY``.

Rate-limit etiquette: Crossref is friendly when you set a polite
``mailto`` query parameter (their "polite pool"), giving 50 req/s. Without
mailto, ~5 req/s. We default to a single contact env var so the polite pool
applies automatically when set.
"""

from __future__ import annotations

import os
from typing import Any

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

from .parser import is_acm_record, parse_record

_LOG = get_logger(__name__)
_SOURCE_NAME = "acm"
_WORKS_ENDPOINT = "https://api.crossref.org/works"
_WORK_ENDPOINT = "https://api.crossref.org/works/{doi}"
_ACM_MEMBER = "320"
_PLUS_TOKEN_ENV = "THESISAGENTS_CROSSREF_PLUS_TOKEN"  # noqa: S105  # nosec B105  # env var name, not a secret value


class AcmFetcher(Fetcher):
    """Strategy implementation for ACM Digital Library via Crossref."""

    config = FetcherConfig(
        name=_SOURCE_NAME,
        rate_limit=RateLimit(requests_per_second=2.0, burst=2, jitter_seconds=0.1),
        requires_api_key=False,
        enabled_by_default=False,  # plugin: needs explicit --source acm
    )

    async def search(self, query: Query) -> list[Paper]:
        params = self._build_search_params(query)
        data = await self._request_json(_WORKS_ENDPOINT, params=params)
        items = data.get("message", {}).get("items", [])
        papers = [
            parse_record(item, source=_SOURCE_NAME)
            for item in items
            if is_acm_record(item)
        ]
        _LOG.info(
            "ACM/Crossref returned %d papers for query=%r (max=%d)",
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
        return parse_record(message, source=_SOURCE_NAME)

    def _build_search_params(self, query: Query) -> dict[str, str]:
        filters: list[str] = [f"member:{_ACM_MEMBER}"]
        if query.year_from is not None:
            filters.append(f"from-pub-date:{query.year_from}")
        if query.year_to is not None:
            filters.append(f"until-pub-date:{query.year_to}")
        params: dict[str, str] = {
            "query": query.keywords,
            "rows": str(min(query.max_results, 100)),
            "filter": ",".join(filters),
        }
        mailto = os.environ.get("THESISAGENTS_CONTACT_EMAIL")
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
            # Crossref Plus subscribers get higher rate limits and fresher
            # cache. The token sits in a dedicated header, not a query param,
            # so it never lands in upstream access logs.
            headers["Crossref-Plus-API-Token"] = f"Bearer {plus_token}"
        try:
            response = await client.get(
                url, params=params or {}, headers=headers
            )
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
