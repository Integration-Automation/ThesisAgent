"""Scholar SERP fetching via WebRunner (real Chrome browser).

Why
---
Google's bot-detection flags httpx-style scrapes within a few requests
(captcha + 30-min cooldown, see ``scholar/fetcher.py``). Driving a real
Chrome session via Selenium with the
``--disable-blink-features=AutomationControlled`` flag survives
Google's standard detection heuristics — same idea Google's own
testing tools use.

``je_web_runner`` is a **default dependency** as of the current
release, so this backend is the default Scholar path on every install.
Users who don't have Chrome on PATH (or who set
``AUTOPAPERTOPPT_DISABLE_WEBRUNNER=1``) automatically fall through to
the httpx scrape path with no breakage.

Auto-detect rule: ``is_available()`` returns True iff
``je_web_runner`` imports cleanly AND ``AUTOPAPERTOPPT_DISABLE_WEBRUNNER``
is not set. Setting the env var forces the httpx path (useful for CI
runs where launching Chrome adds 5-10 s of overhead, or for containers
without a browser binary).

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
_PAGE_LOAD_WAIT_SECONDS = 3.0


def is_available() -> bool:
    """True when WebRunner is importable AND not explicitly disabled.

    Cached via Python's import system — repeated calls are cheap.
    """
    if os.environ.get(_DISABLE_ENV) == "1":
        return False
    try:
        import je_web_runner  # noqa: F401
    except ImportError:
        return False
    return True


async def fetch_serp_html(query: Query) -> str:
    """Drive a real Chrome via WebRunner to fetch the SERP HTML.

    Returns the raw page HTML for ``parse_serp`` to handle. Raises
    ``RuntimeError`` on Chrome boot failure or page-load failure; the
    caller wraps that into the plugin's standard error types.
    """
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
    """Boot Chrome, navigate, capture HTML, quit. Runs in a worker thread."""
    # Imports inside the function so the module imports cleanly even
    # when je_web_runner isn't installed — is_available() gates this
    # path before it ever runs.
    from je_web_runner import webdriver_wrapper_instance

    chrome_args = [
        "--disable-blink-features=AutomationControlled",
        "--lang=en-US",
        # Headless new mode passes more of Google's automation
        # detection than the legacy --headless flag.
        "--headless=new",
        # Reduce fingerprint surface.
        "--disable-gpu",
        "--no-sandbox",
        "--window-size=1280,720",
    ]
    try:
        webdriver_wrapper_instance.set_driver("chrome", options=chrome_args)
    except Exception as err:  # noqa: BLE001 — Selenium raises many types
        raise RuntimeError(f"WebRunner cannot start chrome: {err}") from err

    try:
        webdriver_wrapper_instance.to_url(url)
        # Page needs a beat to render results client-side. We don't use
        # a smart-wait helper here because the SERP layout has no single
        # stable readiness signal that survives captcha vs. real results.
        import time
        time.sleep(_PAGE_LOAD_WAIT_SECONDS)
        return webdriver_wrapper_instance.current_webdriver.page_source
    except Exception as err:  # noqa: BLE001 — best-effort
        raise RuntimeError(f"WebRunner page-load failed: {err}") from err
    finally:
        try:
            webdriver_wrapper_instance.quit()
        except Exception as err:  # noqa: BLE001  # nosec B110 — best-effort cleanup
            _LOG.debug("WebRunner cleanup failed: %s", err)
