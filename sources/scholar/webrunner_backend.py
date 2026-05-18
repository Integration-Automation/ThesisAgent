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
#: Chrome user-data directory to persist between runs. When set, the
#: session cookies from any prior login (Google account, captcha
#: clearance, etc.) survive across CLI invocations — a one-time
#: interactive login in this profile dramatically reduces captcha hits.
_PROFILE_DIR_ENV = "AUTOPAPERTOPPT_CHROME_PROFILE_DIR"
#: Set to ``0`` to disable headless mode (needed for the one-time
#: interactive login into Google when seeding the profile dir).
_HEADLESS_ENV = "AUTOPAPERTOPPT_CHROME_HEADLESS"
_PAGE_LOAD_WAIT_SECONDS = 3.0
#: When the headless flag is OFF (interactive login mode) we hold the
#: window open longer so the user has time to complete the Google
#: sign-in flow before the search returns.
_INTERACTIVE_WAIT_SECONDS = 60.0


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

    chrome_args, headless = _build_chrome_args()
    try:
        webdriver_wrapper_instance.set_driver("chrome", options=chrome_args)
    except Exception as err:  # noqa: BLE001 — Selenium raises many types
        raise RuntimeError(f"WebRunner cannot start chrome: {err}") from err

    try:
        webdriver_wrapper_instance.to_url(url)
        # Headless: tight wait, only need the SERP HTML. Non-headless
        # (interactive login mode): hold the window open so the user
        # has time to complete the Google sign-in flow.
        wait = _PAGE_LOAD_WAIT_SECONDS if headless else _INTERACTIVE_WAIT_SECONDS
        if not headless:
            _LOG.warning(
                "Chrome opened in interactive mode for %.0fs — sign into "
                "Google in the window now. Session cookies will persist "
                "in the profile dir for subsequent headless runs. You may "
                "close the window once logged in; an empty result set "
                "from this run is expected.",
                wait,
            )
        import time
        time.sleep(wait)
        # User closing the window during the wait makes page_source raise
        # or return None — treat that as "interactive seed succeeded,
        # nothing to scrape" and return an empty SERP shell. The cookie
        # store under --user-data-dir is already on disk.
        try:
            html = webdriver_wrapper_instance.current_webdriver.page_source
        except Exception as err:  # noqa: BLE001 — session may be gone
            _LOG.info("Scholar page_source unavailable (%s); returning empty SERP", err)
            return _EMPTY_SERP_HTML
        if html is None:
            _LOG.info(
                "Scholar page_source is None (user likely closed the "
                "interactive window); returning empty SERP",
            )
            return _EMPTY_SERP_HTML
        return html
    except Exception as err:  # noqa: BLE001 — best-effort
        raise RuntimeError(f"WebRunner page-load failed: {err}") from err
    finally:
        try:
            webdriver_wrapper_instance.quit()
        except Exception as err:  # noqa: BLE001  # nosec B110 — best-effort cleanup
            _LOG.debug("WebRunner cleanup failed: %s", err)


# Minimal HTML the SERP parser will treat as "valid but empty" — the
# wrapper div is what the parser checks before bailing out as a
# malformed page.
_EMPTY_SERP_HTML = (
    "<html><body><div id='gs_res_ccl'></div></body></html>"
)


def _build_chrome_args() -> tuple[list[str], bool]:
    """Return ``(chrome_args, is_headless)`` based on env-var overrides.

    Layered on top of the always-applied anti-detection flags:

    - ``AUTOPAPERTOPPT_CHROME_PROFILE_DIR=<path>``: pass
      ``--user-data-dir=<path>`` so cookies / login state persist.
    - ``AUTOPAPERTOPPT_CHROME_HEADLESS=0``: drop ``--headless=new`` so
      the user can interact with the Chrome window (required for the
      one-time Google sign-in that seeds the profile dir).
    """
    chrome_args = [
        "--disable-blink-features=AutomationControlled",
        "--lang=en-US",
        # Reduce fingerprint surface; safe in both headless and visible
        # modes.
        "--disable-gpu",
        "--no-sandbox",
        "--window-size=1280,720",
    ]
    headless = os.environ.get(_HEADLESS_ENV, "1") != "0"
    if headless:
        # Headless 'new' passes more of Google's automation detection
        # than legacy --headless.
        chrome_args.append("--headless=new")
    profile_dir = os.environ.get(_PROFILE_DIR_ENV, "").strip()
    if profile_dir:
        chrome_args.append(f"--user-data-dir={profile_dir}")
        _LOG.info("Chrome using persistent profile at %s", profile_dir)
    return chrome_args, headless
