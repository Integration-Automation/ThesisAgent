"""Google Scholar fetcher (opt-in HTML scraping).

Requires ``AUTOPAPERTOPPT_ENABLE_SCHOLAR_SCRAPING=1``. Paces requests at
~1 every 10 seconds with jitter (matching what real humans browse at) and
surfaces the captcha / sorry page as a SourceUnavailableError.

``fetch_by_id`` is intentionally unsupported — Scholar has no stable native
identifier we can deep-link; the search-results page is the only public
surface.
"""

from __future__ import annotations

import os

from autopapertoppt.core.exceptions import (
    ConfigError,
    ParseError,
    SourceUnavailableError,
)
from autopapertoppt.core.models import Paper, Query
from autopapertoppt.fetchers.base import Fetcher, FetcherConfig
from autopapertoppt.fetchers.http import get_client
from autopapertoppt.fetchers.rate_limit import RateLimit
from autopapertoppt.utils.logging import get_logger
from scholar.parser import parse_serp

_LOG = get_logger(__name__)
_SOURCE_NAME = "scholar"
_SEARCH_URL = "https://scholar.google.com/scholar"
_OPT_OUT_ENV = "AUTOPAPERTOPPT_DISABLE_SCHOLAR_SCRAPING"


class ScholarFetcher(Fetcher):
    """Strategy implementation for Google Scholar."""

    config = FetcherConfig(
        name=_SOURCE_NAME,
        rate_limit=RateLimit(requests_per_second=1 / 10, burst=1, jitter_seconds=2.5),
        requires_api_key=False,
        enabled_by_default=True,
        opt_out_env_var=_OPT_OUT_ENV,
    )

    def __init__(self) -> None:
        super().__init__()
        # Scholar is default-on; flip off via AUTOPAPERTOPPT_DISABLE_SCHOLAR_SCRAPING=1.
        # Google's ToS forbids automated access — heavy use risks captcha
        # / IP blocks. We default-on for coverage; users who prefer not
        # to take the risk can opt out.
        if os.environ.get(_OPT_OUT_ENV) == "1":
            raise ConfigError(
                f"Scholar plugin disabled via {_OPT_OUT_ENV}=1"
            )

    async def search(self, query: Query) -> list[Paper]:
        params = self._build_params(query)
        html_text = await self._get_text(_SEARCH_URL, params=params)
        papers = parse_serp(html_text)
        _LOG.info(
            "Scholar returned %d papers for query=%r (max=%d)",
            len(papers),
            query.keywords,
            query.max_results,
        )
        return papers[: query.max_results]

    async def fetch_by_id(self, identifier: str) -> Paper:
        raise ParseError(
            _SOURCE_NAME,
            "Google Scholar exposes no stable native identifier; use a different source",
        )

    @staticmethod
    def _build_params(query: Query) -> dict[str, str]:
        params: dict[str, str] = {
            "q": query.keywords,
            "hl": "en",
            "num": str(min(query.max_results, 20)),
        }
        if query.year_from is not None:
            params["as_ylo"] = str(query.year_from)
        if query.year_to is not None:
            params["as_yhi"] = str(query.year_to)
        return params

    async def _get_text(self, url: str, *, params: dict[str, str]) -> str:
        await self.bucket.acquire()
        client = await get_client(_SOURCE_NAME)
        headers = {
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            response = await client.get(url, params=params, headers=headers)
        except Exception as err:
            raise SourceUnavailableError(
                _SOURCE_NAME, f"network error: {err}"
            ) from err
        if response.status_code == 429:
            raise SourceUnavailableError(_SOURCE_NAME, "Scholar served HTTP 429")
        if response.status_code in (403, 503):
            raise SourceUnavailableError(
                _SOURCE_NAME,
                f"Scholar blocked the request ({response.status_code}); "
                "back off and try later.",
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
