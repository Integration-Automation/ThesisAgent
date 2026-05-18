"""Scholar SERP fetching via WebRunner (real visible Chrome browser).

Why
---
Google's bot-detection flags httpx-style scrapes within a few requests
(captcha + 30-min cooldown, see ``scholar/fetcher.py``). Driving a
real visible Chrome session via Selenium with the
``--disable-blink-features=AutomationControlled`` flag survives
Google's standard detection heuristics. Headless mode is intentionally
NOT supported because Google's detection is more aggressive against
headless signatures.

``je_web_runner`` is a default dependency, so this backend is the
default Scholar path on every install. Set
``AUTOPAPERTOPPT_DISABLE_WEBRUNNER=1`` to fall back to the httpx
scrape path (useful for CI / Docker without a Chrome binary, or when
you'd rather skip the visible Chrome window popping up).

The actual Selenium calls run inside ``asyncio.to_thread`` so the
async pipeline isn't blocked while Chrome boots.
"""

from __future__ import annotations

import asyncio
import os
from urllib.parse import urlencode

from autopapertoppt.core.models import Query
from autopapertoppt.utils.logging import get_logger

_LOG = get_logger(__name__)
_SEARCH_URL_BASE = "https://scholar.google.com/scholar"
_DISABLE_ENV = "AUTOPAPERTOPPT_DISABLE_WEBRUNNER"
#: Chrome user-data directory to persist between runs. When set the
#: session cookies (captcha clearance, any consent acks) survive
#: across CLI invocations.
_PROFILE_DIR_ENV = "AUTOPAPERTOPPT_CHROME_PROFILE_DIR"
#: Page-load wait per Chrome navigation. Generous so the user has a
#: chance to interact (close consent banner, solve captcha) when the
#: window pops up.
_PAGE_LOAD_WAIT_SECONDS = 15.0

# Minimal HTML the SERP parser treats as "valid but empty" — the
# wrapper div is what the parser checks before bailing out as malformed.
_EMPTY_SERP_HTML = "<html><body><div id='gs_res_ccl'></div></body></html>"


def is_available() -> bool:
    """True when WebRunner is importable AND not explicitly disabled."""
    if os.environ.get(_DISABLE_ENV) == "1":
        return False
    try:
        import je_web_runner  # noqa: F401
    except ImportError:
        return False
    return True


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
    """Boot a visible Chrome, navigate, capture HTML, quit."""
    from je_web_runner import webdriver_wrapper_instance

    chrome_args = _build_chrome_args()
    try:
        webdriver_wrapper_instance.set_driver("chrome", options=chrome_args)
    except Exception as err:  # noqa: BLE001
        raise RuntimeError(f"WebRunner cannot start chrome: {err}") from err

    try:
        webdriver_wrapper_instance.to_url(url)
        _LOG.info(
            "Chrome opened (visible) for %.0fs — close the window early "
            "if the page is ready, otherwise it will close itself.",
            _PAGE_LOAD_WAIT_SECONDS,
        )
        import time
        time.sleep(_PAGE_LOAD_WAIT_SECONDS)
        try:
            html = webdriver_wrapper_instance.current_webdriver.page_source
        except Exception as err:  # noqa: BLE001
            _LOG.info(
                "Scholar page_source unavailable (%s); returning empty SERP",
                err,
            )
            return _EMPTY_SERP_HTML
        if html is None:
            _LOG.info(
                "Scholar page_source is None (window likely closed); "
                "returning empty SERP",
            )
            return _EMPTY_SERP_HTML
        return html
    except Exception as err:  # noqa: BLE001
        raise RuntimeError(f"WebRunner page-load failed: {err}") from err
    finally:
        try:
            webdriver_wrapper_instance.quit()
        except Exception as err:  # noqa: BLE001  # nosec B110 — best-effort cleanup
            _LOG.debug("WebRunner cleanup failed: %s", err)


def _build_chrome_args() -> list[str]:
    """Build the Chrome CLI flag list. Always visible (no headless)."""
    chrome_args = [
        "--disable-blink-features=AutomationControlled",
        "--lang=en-US",
        "--disable-gpu",
        "--no-sandbox",
        "--window-size=1280,720",
    ]
    profile_dir = os.environ.get(_PROFILE_DIR_ENV, "").strip()
    if profile_dir:
        chrome_args.append(f"--user-data-dir={profile_dir}")
        _LOG.info("Chrome using persistent profile at %s", profile_dir)
    return chrome_args
