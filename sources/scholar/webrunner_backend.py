"""Scholar SERP fetching via WebRunner (real visible Chrome browser).

Uses the shared helper at ``autopapertoppt.fetchers.webrunner_browser``
which bypasses ``je_web_runner``'s module-level singleton (it crashes
when multiple WebRunner sources fan out in parallel) by spinning a
fresh ``selenium.webdriver.Chrome`` per call.

When Google serves a captcha / 'unusual traffic' page, the backend
waits up to 5 minutes for the user to solve it in the visible Chrome
window. After the user clicks through, the SERP loads naturally and
we grab ``page_source`` once it's no longer a captcha page.
"""

from __future__ import annotations

import asyncio
import contextlib
from urllib.parse import urlencode

from autopapertoppt.core.models import Query
from autopapertoppt.fetchers import webrunner_browser
from autopapertoppt.utils.logging import get_logger

_LOG = get_logger(__name__)
_SEARCH_URL_BASE = "https://scholar.google.com/scholar"
_INITIAL_RENDER_WAIT_SECONDS = 4.0
_CAPTCHA_MAX_WAIT_SECONDS = 300.0

_EMPTY_SERP_HTML = "<html><body><div id='gs_res_ccl'></div></body></html>"


def is_available() -> bool:
    """Re-exported from the shared browser helper."""
    return webrunner_browser.is_available()


async def fetch_serp_html(query: Query) -> str:
    """Drive a real Chrome via WebRunner to fetch the SERP HTML."""
    url = _build_url(query)
    _LOG.info("Scholar via WebRunner: %s", url)
    return await asyncio.to_thread(_drive_chrome_sync, url)


def _build_url(query: Query) -> str:
    params: dict[str, str] = {
        "q": query.keywords,
        "hl": "en",
        "num": str(min(query.max_results, 20)),
    }
    if query.year_from is not None:
        params["as_ylo"] = str(query.year_from)
    if query.year_to is not None:
        params["as_yhi"] = str(query.year_to)
    return f"{_SEARCH_URL_BASE}?{urlencode(params)}"


def _drive_chrome_sync(url: str) -> str:
    """Boot a fresh Chrome, navigate, wait for any captcha to clear,
    capture HTML, quit. Runs in a worker thread (Selenium is sync).
    """
    try:
        driver = webrunner_browser.make_driver()
    except Exception as err:  # noqa: BLE001 — Selenium raises many types
        raise RuntimeError(f"WebRunner cannot start chrome: {err}") from err

    try:
        driver.get(url)
        import time
        time.sleep(_INITIAL_RENDER_WAIT_SECONDS)
        # If Google served a captcha / 'unusual traffic' page, wait for
        # the user to solve it manually before reading page_source.
        webrunner_browser.wait_for_captcha_solved(
            driver, max_wait_seconds=_CAPTCHA_MAX_WAIT_SECONDS,
        )
        try:
            html = driver.page_source
        except Exception as err:  # noqa: BLE001 — session may be gone
            _LOG.info(
                "Scholar page_source unavailable (%s); returning empty SERP",
                err,
            )
            return _EMPTY_SERP_HTML
        if not html:
            _LOG.info(
                "Scholar page_source is empty (window likely closed); "
                "returning empty SERP",
            )
            return _EMPTY_SERP_HTML
        return html
    except Exception as err:  # noqa: BLE001
        raise RuntimeError(f"WebRunner page-load failed: {err}") from err
    finally:
        with contextlib.suppress(Exception):
            driver.quit()


# Backward-compat alias for tests that monkeypatch _build_chrome_args.
def _build_chrome_args() -> list[str]:
    """Return the Chrome args list (used by tests; the actual driver
    is built by ``webrunner_browser.make_driver``)."""
    args = [
        "--disable-blink-features=AutomationControlled",
        "--lang=en-US",
        "--disable-gpu",
        "--no-sandbox",
        "--window-size=1280,720",
    ]
    import os
    profile_dir = os.environ.get(
        "AUTOPAPERTOPPT_CHROME_PROFILE_DIR", ""
    ).strip()
    if profile_dir:
        args.append(f"--user-data-dir={profile_dir}")
    return args
