"""OpenAlex fetcher.

Endpoints:
- Search:        GET https://api.openalex.org/works?search=…
- Single work:   GET https://api.openalex.org/works/{id}
                 where {id} may be ``doi:10.x/y``, ``arxiv:2401.x``, or the
                 raw OpenAlex work id (``W123``).

No API key required. Polite-pool: include ``mailto=<email>`` as a query
param when ``THESISAGENTS_CONTACT_EMAIL`` is set — this lifts the request
into a separately rate-limited pool with better stability.

Rate limit: OpenAlex publishes 10 req/s, 100k/day. We stay under 5 req/s.
"""

from __future__ import annotations

import os

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

from .parser import parse_work

_LOG = get_logger(__name__)
_SOURCE_NAME = "openalex"
_SEARCH_ENDPOINT = "https://api.openalex.org/works"
_WORK_ENDPOINT = "https://api.openalex.org/works/{id}"
_CONTACT_ENV = "THESISAGENTS_CONTACT_EMAIL"

#: Restrict the JSON to the fields the parser actually reads — keeps the
#: response small and shields us from upstream schema noise.
_SELECT_FIELDS: str = ",".join(
    (
        "id",
        "doi",
        "title",
        "display_name",
        "publication_year",
        "authorships",
        "primary_location",
        "best_oa_location",
        "open_access",
        "abstract_inverted_index",
        "cited_by_count",
        "ids",
        "locations",
    )
)


class OpenAlexFetcher(Fetcher):
    """Strategy implementation for OpenAlex."""

    config = FetcherConfig(
        name=_SOURCE_NAME,
        rate_limit=RateLimit(requests_per_second=5.0, burst=2, jitter_seconds=0.2),
        requires_api_key=False,
        enabled_by_default=True,
    )

    async def search(self, query: Query) -> list[Paper]:
        params = self._build_search_params(query)
        data = await self._request(_SEARCH_ENDPOINT, params=params)
        records = data.get("results") or []
        papers = [parse_work(record) for record in records]
        _LOG.info(
            "OpenAlex returned %d papers for query=%r (max=%d)",
            len(papers),
            query.keywords,
            query.max_results,
        )
        return papers[: query.max_results]

    async def fetch_by_id(self, identifier: str) -> Paper:
        normalised = self._normalise_id(identifier)
        url = _WORK_ENDPOINT.format(id=normalised)
        params = {"select": _SELECT_FIELDS}
        mailto = self._mailto()
        if mailto:
            params["mailto"] = mailto
        data = await self._request(url, params=params)
        return parse_work(data)

    def _build_search_params(self, query: Query) -> dict[str, str]:
        per_page = min(query.max_results, 50)
        params: dict[str, str] = {
            "search": query.keywords,
            "per-page": str(per_page),
            "select": _SELECT_FIELDS,
            "sort": "relevance_score:desc",
        }
        year_filter = self._year_filter(query.year_from, query.year_to)
        if year_filter:
            params["filter"] = year_filter
        mailto = self._mailto()
        if mailto:
            params["mailto"] = mailto
        return params

    @staticmethod
    def _year_filter(year_from: int | None, year_to: int | None) -> str | None:
        bits: list[str] = []
        if year_from is not None:
            bits.append(f"from_publication_date:{year_from}-01-01")
        if year_to is not None:
            bits.append(f"to_publication_date:{year_to}-12-31")
        return ",".join(bits) if bits else None

    @staticmethod
    def _mailto() -> str | None:
        raw = (os.environ.get(_CONTACT_ENV) or "").strip()
        return raw or None

    @staticmethod
    def _normalise_id(identifier: str) -> str:
        raw = identifier.strip()
        lower = raw.lower()
        if lower.startswith(("doi:", "arxiv:", "pmid:", "w")):
            return raw
        if raw.startswith("10."):
            return f"doi:{raw}"
        return raw

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
            raise RateLimitError(_SOURCE_NAME, "OpenAlex rate limit hit")
        if response.status_code >= 500:
            raise SourceUnavailableError(
                _SOURCE_NAME, f"server error {response.status_code}"
            )
        if response.status_code == 404:
            raise ParseError(_SOURCE_NAME, "work not found")
        if response.status_code >= 400:
            raise ParseError(
                _SOURCE_NAME,
                f"client error {response.status_code}: {response.text[:256]}",
            )
        try:
            return response.json()
        except ValueError as err:
            raise ParseError(_SOURCE_NAME, f"invalid JSON: {err}") from err
