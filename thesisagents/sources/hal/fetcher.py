"""HAL fetcher.

Endpoint:
- Search: GET https://api.archives-ouvertes.fr/search/
          ?q=KEY&wt=json&rows=N&fl=FIELDS

HAL is France's open archive (CS / maths / physics heavy), Solr-backed, no API
key. We must request the metadata fields explicitly via ``fl`` — the default
response carries only ``docid`` + ``label_s`` — so the field list lives next to
the parser's (see ``parser.FIELDS``).

Year filtering is a deterministic post-filter on ``producedDateY_i`` (consistent
with the other plugins) rather than a Solr ``fq`` clause, so we over-fetch 2×
``max_results`` and truncate afterwards.

Rate limit: HAL has no published per-second cap; we stay polite at ~2 req/s.
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

from .parser import FIELDS, in_year_range, parse_doc

_LOG = get_logger(__name__)
_SOURCE_NAME = "hal"
_SEARCH_ENDPOINT = "https://api.archives-ouvertes.fr/search/"
_MAX_ROWS = 1000


class HalFetcher(Fetcher):
    """Strategy implementation for HAL."""

    config = FetcherConfig(
        name=_SOURCE_NAME,
        rate_limit=RateLimit(requests_per_second=2.0, burst=1, jitter_seconds=0.3),
        requires_api_key=False,
        enabled_by_default=True,
    )

    async def search(self, query: Query) -> list[Paper]:
        params = self._build_search_params(query)
        data = await self._request(_SEARCH_ENDPOINT, params=params)
        docs = (data.get("response") or {}).get("docs") or []
        papers = [parse_doc(doc) for doc in docs]
        if query.year_from is not None or query.year_to is not None:
            papers = [
                p
                for p in papers
                if in_year_range(p.year, query.year_from, query.year_to)
            ]
        _LOG.info(
            "HAL returned %d papers for query=%r (max=%d)",
            len(papers),
            query.keywords,
            query.max_results,
        )
        return papers[: query.max_results]

    def _build_search_params(self, query: Query) -> dict[str, str]:
        rows = min(query.max_results * 2, _MAX_ROWS)
        return {
            "q": query.keywords,
            "wt": "json",
            "rows": str(rows),
            "fl": ",".join(FIELDS),
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
            raise RateLimitError(_SOURCE_NAME, "HAL rate limit hit")
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
