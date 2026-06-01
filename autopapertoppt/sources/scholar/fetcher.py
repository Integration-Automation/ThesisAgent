"""Google Scholar fetcher (default-on HTML scraping).

Default-on; opt out with ``AUTOPAPERTOPPT_DISABLE_SCHOLAR_SCRAPING=1``.
Paces requests at ~1 every 10 seconds with jitter and **detects
Google's captcha / 'unusual traffic' interstitial**, surfacing it as a
SourceUnavailableError plus a process-level cooldown so subsequent
searches in the same run skip Scholar instantly instead of burning the
rate-limit budget.

``fetch_by_id`` is intentionally unsupported — Scholar has no stable
native identifier we can deep-link; the search-results page is the only
public surface.
"""

from __future__ import annotations

import os
import time

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

#: Substrings that indicate Google served a captcha / 'unusual traffic'
#: page instead of the search results. The /sorry/ URL is Google's
#: bot-interstitial endpoint; the others cover the in-page form text.
_CAPTCHA_MARKERS: tuple[str, ...] = (
    "/sorry/",
    "Our systems have detected unusual traffic",
    'id="captcha-form"',
    "Please show you're not a robot",
    "g-recaptcha",
)

#: Process-level cooldown. Once Google serves a captcha, retrying for
#: the next 30 minutes is pointless and will only deepen the IP block.
#: Stored as the timestamp (epoch seconds) until which Scholar refuses
#: to even try. 0 means "no cooldown".
_CAPTCHA_COOLDOWN_SECONDS = 30 * 60
_captcha_locked_until: float = 0.0


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
        html_text = await self._fetch_serp(query)
        papers = parse_serp(html_text)
        _LOG.info(
            "Scholar returned %d papers for query=%r (max=%d)",
            len(papers),
            query.keywords,
            query.max_results,
        )
        return papers[: query.max_results]

    async def _fetch_serp(self, query: Query) -> str:
        """Pick the WebRunner (real browser) path when available, fall
        back to the httpx scrape path otherwise.

        WebRunner survives Google's standard bot-detection because it
        drives a real Chrome with the auto-control flag disabled; the
        httpx path gets captcha'd within a few requests. We prefer
        WebRunner whenever ``je_web_runner`` is importable and
        ``AUTOPAPERTOPPT_DISABLE_WEBRUNNER`` is not set.
        """
        from scholar import webrunner_backend

        if webrunner_backend.is_available():
            try:
                return await webrunner_backend.fetch_serp_html(query)
            except RuntimeError as err:
                _LOG.warning(
                    "WebRunner backend failed (%s); falling back to httpx", err,
                )
        params = self._build_params(query)
        return await self._get_text(_SEARCH_URL, params=params)

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
        _raise_if_cooldown_active()
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
        # Google may serve the captcha as HTTP 200 with an HTML form, so
        # the body check must come before the status-code-only checks.
        if _is_captcha_response(str(response.url), response.text):
            _engage_captcha_cooldown()
            raise SourceUnavailableError(
                _SOURCE_NAME,
                "Scholar served a captcha / 'unusual traffic' page. "
                f"Pausing Scholar for {_CAPTCHA_COOLDOWN_SECONDS // 60} "
                "minutes. To avoid this: rotate IP (VPN), set "
                "AUTOPAPERTOPPT_DISABLE_SCHOLAR_SCRAPING=1 to skip the "
                "plugin, or wait it out.",
            )
        if response.status_code == 429:
            _engage_captcha_cooldown()
            raise SourceUnavailableError(_SOURCE_NAME, "Scholar served HTTP 429")
        if response.status_code in (403, 503):
            _engage_captcha_cooldown()
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


def _is_captcha_response(url: str, body: str) -> bool:
    """Detect Google's bot-check interstitial in either the URL or body.

    Body check is bounded to the first 8 KB — captcha pages are tiny so
    the markers always sit at the top, and we avoid scanning megabytes
    of legitimate HTML on real result pages.
    """
    if "/sorry/" in url:
        return True
    head = body[:8_192]
    return any(marker in head for marker in _CAPTCHA_MARKERS)


def _engage_captcha_cooldown() -> None:
    global _captcha_locked_until  # noqa: PLW0603 — intentional process flag
    _captcha_locked_until = time.monotonic() + _CAPTCHA_COOLDOWN_SECONDS
    _LOG.warning(
        "Scholar captcha lockout engaged for %ds. Subsequent Scholar "
        "requests in this process will raise SourceUnavailableError "
        "immediately until the cooldown expires.",
        _CAPTCHA_COOLDOWN_SECONDS,
    )


def _raise_if_cooldown_active() -> None:
    if _captcha_locked_until and time.monotonic() < _captcha_locked_until:
        remaining = int(_captcha_locked_until - time.monotonic())
        raise SourceUnavailableError(
            _SOURCE_NAME,
            f"Scholar in cooldown for {remaining}s after a captcha hit.",
        )
