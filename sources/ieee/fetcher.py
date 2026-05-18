"""IEEE Xplore fetcher.

Two paths, selected at runtime:

* **Official API** — when ``AUTOPAPERTOPPT_IEEE_API_KEY`` is set, the plugin
  calls ``https://ieeexploreapi.ieee.org/api/v1/search/articles`` with the
  key attached. This path is fully sanctioned, returns ``pdf_url`` for
  documents inside the key's subscription scope, and does not need the
  scraping opt-in flag.
* **Scraping fallback** — when no API key is available the plugin falls back
  to the public website's ``/rest/search`` endpoint, guarded by
  ``AUTOPAPERTOPPT_ENABLE_IEEE_SCRAPING=1``. IEEE Xplore terms restrict
  bulk automated scraping; this path paces requests, requires the env-var
  opt-in, and surfaces clear errors when the upstream blocks.

Single-paper lookup also takes the API key when present (via the document
endpoint ``/api/v1/search/document/<arnumber>``); otherwise it falls back
to scraping the ``xplGlobal.document.metadata`` JavaScript blob from the
public document page.
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
from ieee.parser import parse_api_record, parse_metadata_blob, parse_search_record

_LOG = get_logger(__name__)
_SOURCE_NAME = "ieee"
_SEARCH_URL = "https://ieeexplore.ieee.org/rest/search"
_DOCUMENT_URL = "https://ieeexplore.ieee.org/document/{arnumber}"
_API_SEARCH_URL = "https://ieeexploreapi.ieee.org/api/v1/search/articles"
_OPT_OUT_ENV = "AUTOPAPERTOPPT_DISABLE_IEEE_SCRAPING"
_API_KEY_ENV = "AUTOPAPERTOPPT_IEEE_API_KEY"
_REFERER = "https://ieeexplore.ieee.org/search/searchresult.jsp"


class IeeeFetcher(Fetcher):
    """Strategy implementation for IEEE Xplore."""

    config = FetcherConfig(
        name=_SOURCE_NAME,
        rate_limit=RateLimit(requests_per_second=0.5, burst=1, jitter_seconds=0.4),
        requires_api_key=False,
        enabled_by_default=True,
        opt_out_env_var=_OPT_OUT_ENV,
    )

    def __init__(self) -> None:
        super().__init__()
        self._api_key = (os.environ.get(_API_KEY_ENV) or "").strip() or None
        # IEEE is default-on; flip off via AUTOPAPERTOPPT_DISABLE_IEEE_SCRAPING=1.
        # Subscribers should set AUTOPAPERTOPPT_IEEE_API_KEY for the official
        # API path (better metadata + pdf_url for subscription papers); without
        # the key the plugin falls back to the scrape path.
        if os.environ.get(_OPT_OUT_ENV) == "1":
            raise ConfigError(
                f"IEEE plugin disabled via {_OPT_OUT_ENV}=1"
            )

    async def search(self, query: Query) -> list[Paper]:
        if self._api_key:
            return await self._api_search(query)
        body = self._build_search_body(query)
        data = await self._post_json(_SEARCH_URL, body=body)
        records = data.get("records") or []
        papers = [parse_search_record(r) for r in records]
        _LOG.info(
            "IEEE (scrape) returned %d papers for query=%r (max=%d)",
            len(papers),
            query.keywords,
            query.max_results,
        )
        return papers[: query.max_results]

    async def fetch_by_id(self, identifier: str) -> Paper:
        arnumber = identifier.strip()
        if not arnumber.isdigit():
            raise ParseError(_SOURCE_NAME, f"invalid IEEE arnumber: {identifier!r}")
        if self._api_key:
            return await self._api_fetch_by_id(arnumber)
        url = _DOCUMENT_URL.format(arnumber=arnumber)
        html_text = await self._get_text(url)
        paper = parse_metadata_blob(html_text)
        _LOG.info("IEEE resolved arnumber=%s (scrape)", arnumber)
        return paper

    async def _api_search(self, query: Query) -> list[Paper]:
        params = self._build_api_params(query)
        data = await self._get_json(_API_SEARCH_URL, params=params)
        records = data.get("articles") or []
        papers = [parse_api_record(record) for record in records]
        _LOG.info(
            "IEEE (api) returned %d papers for query=%r (max=%d)",
            len(papers),
            query.keywords,
            query.max_results,
        )
        return papers[: query.max_results]

    async def _api_fetch_by_id(self, arnumber: str) -> Paper:
        params = {
            "apikey": self._api_key,
            "article_number": arnumber,
            "max_records": "1",
            "format": "json",
        }
        data = await self._get_json(_API_SEARCH_URL, params=params)
        records = data.get("articles") or []
        if not records:
            raise ParseError(
                _SOURCE_NAME, f"no IEEE article found for arnumber {arnumber}"
            )
        paper = parse_api_record(records[0])
        _LOG.info("IEEE resolved arnumber=%s (api)", arnumber)
        return paper

    def _build_api_params(self, query: Query) -> dict[str, str]:
        params: dict[str, str] = {
            "apikey": self._api_key or "",
            "querytext": query.keywords,
            "max_records": str(min(query.max_results, 200)),
            "start_record": "1",
            "format": "json",
            "sort_field": "article_number",
            "sort_order": "desc",
        }
        if query.year_from is not None:
            params["start_year"] = str(query.year_from)
        if query.year_to is not None:
            params["end_year"] = str(query.year_to)
        return params

    @staticmethod
    def _build_search_body(query: Query) -> dict[str, object]:
        body: dict[str, object] = {
            "queryText": query.keywords,
            "highlight": False,
            "returnFacets": ["ALL"],
            "returnType": "SEARCH",
            "matchPubs": True,
            "pageNumber": 1,
            "rowsPerPage": min(query.max_results, 100),
        }
        if query.year_from is not None:
            body["rangeYearFrom"] = query.year_from
        if query.year_to is not None:
            body["rangeYearTo"] = query.year_to
        return body

    async def _get_json(self, url: str, *, params: dict[str, str]) -> dict:
        await self.bucket.acquire()
        client = await get_client(_SOURCE_NAME)
        headers = {"Accept": "application/json"}
        try:
            response = await client.get(url, params=params, headers=headers)
        except Exception as err:
            raise SourceUnavailableError(
                _SOURCE_NAME, f"network error: {err}"
            ) from err
        return self._decode_json(response)

    async def _post_json(self, url: str, *, body: dict[str, object]) -> dict:
        await self.bucket.acquire()
        client = await get_client(_SOURCE_NAME)
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://ieeexplore.ieee.org",
            "Referer": _REFERER,
        }
        try:
            response = await client.post(url, json=body, headers=headers)
        except Exception as err:
            raise SourceUnavailableError(
                _SOURCE_NAME, f"network error: {err}"
            ) from err
        return self._decode_json(response)

    async def _get_text(self, url: str) -> str:
        await self.bucket.acquire()
        client = await get_client(_SOURCE_NAME)
        headers = {"Accept": "text/html,application/xhtml+xml"}
        try:
            response = await client.get(url, headers=headers)
        except Exception as err:
            raise SourceUnavailableError(
                _SOURCE_NAME, f"network error: {err}"
            ) from err
        if response.status_code == 429:
            raise RateLimitError(_SOURCE_NAME, "IEEE rate-limited the document fetch")
        if response.status_code in (418, 403):
            raise SourceUnavailableError(
                _SOURCE_NAME,
                f"IEEE blocked the request ({response.status_code}). "
                "Try again later or run from a different network.",
            )
        if response.status_code >= 500:
            raise SourceUnavailableError(
                _SOURCE_NAME, f"server error {response.status_code}"
            )
        if response.status_code >= 400:
            raise ParseError(
                _SOURCE_NAME,
                f"client error {response.status_code}: {response.text[:256]}",
            )
        return response.text

    @staticmethod
    def _decode_json(response) -> dict:
        if response.status_code == 429:
            raise RateLimitError(_SOURCE_NAME, "IEEE rate-limited the search")
        if response.status_code in (418, 403):
            raise SourceUnavailableError(
                _SOURCE_NAME, f"IEEE blocked the request ({response.status_code})"
            )
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
