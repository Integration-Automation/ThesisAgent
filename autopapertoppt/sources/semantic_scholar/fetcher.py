"""Semantic Scholar Graph API fetcher.

Endpoints:
- Search:      GET /graph/v1/paper/search
- Single paper: GET /graph/v1/paper/{id}  (id can be `DOI:10.x`, `ARXIV:2401.x`,
                                           a paperId, etc.)
Public access is rate-limited to ~1 req/sec by Semantic Scholar; an API key
(``AUTOPAPERTOPPT_S2_API_KEY``) raises that.
"""

from __future__ import annotations

import os

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

from .parser import GRAPH_FIELDS, parse_paper

_LOG = get_logger(__name__)
_SOURCE_NAME = "semantic_scholar"
_SEARCH_ENDPOINT = "https://api.semanticscholar.org/graph/v1/paper/search"
_PAPER_ENDPOINT = "https://api.semanticscholar.org/graph/v1/paper/{id}"
_API_KEY_ENV = "AUTOPAPERTOPPT_S2_API_KEY"


class SemanticScholarFetcher(Fetcher):
    """Strategy implementation for Semantic Scholar."""

    config = FetcherConfig(
        name=_SOURCE_NAME,
        rate_limit=RateLimit(requests_per_second=1.0, burst=1, jitter_seconds=0.3),
        requires_api_key=False,
        enabled_by_default=True,
    )

    async def search(self, query: Query) -> list[Paper]:
        params: dict[str, str] = {
            "query": query.keywords,
            "limit": str(min(query.max_results, 100)),
            "fields": GRAPH_FIELDS,
        }
        if query.year_from is not None or query.year_to is not None:
            params["year"] = self._year_filter(query.year_from, query.year_to)
        if query.min_citations is not None:
            params["minCitationCount"] = str(query.min_citations)
        data = await self._request(_SEARCH_ENDPOINT, params=params)
        records = data.get("data") or []
        papers = [parse_paper(r) for r in records]
        _LOG.info(
            "Semantic Scholar returned %d papers for query=%r (max=%d)",
            len(papers),
            query.keywords,
            query.max_results,
        )
        return papers[: query.max_results]

    async def fetch_by_id(self, identifier: str) -> Paper:
        normalised = self._normalise_id(identifier)
        url = _PAPER_ENDPOINT.format(id=normalised)
        data = await self._request(url, params={"fields": GRAPH_FIELDS})
        return parse_paper(data)

    @staticmethod
    def _year_filter(year_from: int | None, year_to: int | None) -> str:
        lo = str(year_from) if year_from is not None else ""
        hi = str(year_to) if year_to is not None else ""
        return f"{lo}-{hi}"

    @staticmethod
    def _normalise_id(identifier: str) -> str:
        """Accept DOI / arXiv / raw paperId and produce the Graph-API form."""
        raw = identifier.strip()
        upper = raw.upper()
        if upper.startswith(("DOI:", "ARXIV:", "URL:", "PMID:", "MAG:", "CORPUS:")):
            return raw
        if raw.startswith("10."):
            return f"DOI:{raw}"
        if any(ch.isdigit() for ch in raw) and "." in raw and "/" not in raw:
            return f"ARXIV:{raw}"
        return raw

    async def _request(self, url: str, *, params: dict[str, str]) -> dict:
        await self.bucket.acquire()
        client = await get_client(_SOURCE_NAME)
        headers: dict[str, str] = {}
        api_key = os.environ.get(_API_KEY_ENV)
        if api_key:
            headers["x-api-key"] = api_key
        try:
            response = await client.get(url, params=params, headers=headers)
        except Exception as err:
            raise SourceUnavailableError(
                _SOURCE_NAME, f"network error: {err}"
            ) from err
        if response.status_code == 429:
            raise RateLimitError(_SOURCE_NAME, "Semantic Scholar rate limit hit")
        if response.status_code >= 500:
            raise SourceUnavailableError(
                _SOURCE_NAME, f"server error {response.status_code}"
            )
        if response.status_code == 404:
            raise ParseError(_SOURCE_NAME, "paper not found")
        if response.status_code >= 400:
            raise ParseError(
                _SOURCE_NAME,
                f"client error {response.status_code}: {response.text[:256]}",
            )
        try:
            return response.json()
        except ValueError as err:
            raise ParseError(_SOURCE_NAME, f"invalid JSON: {err}") from err
