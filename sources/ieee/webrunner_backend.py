"""IEEE Xplore search via WebRunner (real visible Chrome browser).

Why
---
IEEE Xplore's ``/rest/search`` endpoint blocks httpx-style POSTs even
with browser-shaped headers — they fingerprint the TLS handshake +
JavaScript engine to require a real Chrome instance. Driving a real
Chrome that hits the same endpoint with ``fetch()`` from inside the
``ieeexplore.ieee.org`` origin survives that detection.

Flow:
1. Boot visible Chrome with anti-detection flags.
2. Navigate to ``https://ieeexplore.ieee.org/Xplore/home.jsp`` so the
   page sets the session cookies the REST endpoint requires.
3. ``execute_async_script`` a ``fetch('/rest/search', {method:'POST',
   body: ...})`` so the request runs inside the real-browser context
   (right cookies, right Origin, right fingerprint).
4. Parse the returned JSON with the existing :func:`parse_search_record`.

Document-by-id flow:
1. Same Chrome boot.
2. Navigate directly to ``https://ieeexplore.ieee.org/document/<arnumber>``
3. Return ``page_source`` for the existing HTML parser.

``je_web_runner`` is a default dependency; this backend is the default
IEEE scrape path. Set ``AUTOPAPERTOPPT_DISABLE_WEBRUNNER=1`` to fall
back to the httpx scrape (which will likely 403).
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from autopapertoppt.utils.logging import get_logger

_LOG = get_logger(__name__)

_HOME_URL = "https://ieeexplore.ieee.org/Xplore/home.jsp"
_SEARCH_REST = "https://ieeexplore.ieee.org/rest/search"
_DOCUMENT_URL = "https://ieeexplore.ieee.org/document/{arnumber}"
_DISABLE_ENV = "AUTOPAPERTOPPT_DISABLE_WEBRUNNER"
_PROFILE_DIR_ENV = "AUTOPAPERTOPPT_CHROME_PROFILE_DIR"
_PAGE_LOAD_WAIT_SECONDS = 4.0
_SCRIPT_TIMEOUT_SECONDS = 30


def is_available() -> bool:
    """True when WebRunner is importable AND not explicitly disabled."""
    if os.environ.get(_DISABLE_ENV) == "1":
        return False
    try:
        import je_web_runner  # noqa: F401
    except ImportError:
        return False
    return True


async def fetch_search_json(body: dict[str, Any]) -> dict[str, Any]:
    """POST ``/rest/search`` from inside the IEEE origin via real Chrome."""
    return await asyncio.to_thread(_search_via_chrome_sync, body)


async def fetch_document_html(arnumber: str) -> str:
    """Navigate to ``/document/<arnumber>`` via real Chrome, return HTML."""
    url = _DOCUMENT_URL.format(arnumber=arnumber)
    return await asyncio.to_thread(_document_via_chrome_sync, url)


def _search_via_chrome_sync(body: dict[str, Any]) -> dict[str, Any]:
    """Boot Chrome → land on IEEE home → JS-fetch POST → return JSON."""
    from je_web_runner import webdriver_wrapper_instance

    chrome_args = _build_chrome_args()
    try:
        webdriver_wrapper_instance.set_driver("chrome", options=chrome_args)
    except Exception as err:  # noqa: BLE001
        raise RuntimeError(f"WebRunner cannot start chrome: {err}") from err

    driver = webdriver_wrapper_instance.current_webdriver
    try:
        webdriver_wrapper_instance.to_url(_HOME_URL)
        # Brief wait for cookies / JS setup; if user manually closes the
        # window during this we let the next step blow up cleanly.
        import time
        time.sleep(_PAGE_LOAD_WAIT_SECONDS)
        driver.set_script_timeout(_SCRIPT_TIMEOUT_SECONDS)
        result = driver.execute_async_script(
            _FETCH_REST_JS,
            _SEARCH_REST,
            json.dumps(body),
        )
        if not isinstance(result, dict):
            raise RuntimeError(f"IEEE fetch returned non-dict: {result!r}")
        if "_error" in result:
            raise RuntimeError(f"IEEE fetch JS failed: {result['_error']}")
        return result
    except Exception as err:  # noqa: BLE001
        raise RuntimeError(f"WebRunner IEEE search failed: {err}") from err
    finally:
        try:
            webdriver_wrapper_instance.quit()
        except Exception as err:  # noqa: BLE001  # nosec B110 — cleanup
            _LOG.debug("WebRunner cleanup failed: %s", err)


def _document_via_chrome_sync(url: str) -> str:
    from je_web_runner import webdriver_wrapper_instance

    chrome_args = _build_chrome_args()
    try:
        webdriver_wrapper_instance.set_driver("chrome", options=chrome_args)
    except Exception as err:  # noqa: BLE001
        raise RuntimeError(f"WebRunner cannot start chrome: {err}") from err

    try:
        webdriver_wrapper_instance.to_url(url)
        import time
        time.sleep(_PAGE_LOAD_WAIT_SECONDS)
        try:
            html = webdriver_wrapper_instance.current_webdriver.page_source
        except Exception as err:  # noqa: BLE001
            raise RuntimeError(f"IEEE document page_source failed: {err}") from err
        if not html:
            raise RuntimeError("IEEE document page_source is empty")
        return html
    finally:
        try:
            webdriver_wrapper_instance.quit()
        except Exception as err:  # noqa: BLE001  # nosec B110 — cleanup
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
    return chrome_args


# JavaScript executed inside the IEEE origin to POST /rest/search with
# the right cookies + Origin header. Returns the JSON via async
# callback; on failure returns an object with ``_error`` set so the
# Python side can surface a meaningful message.
_FETCH_REST_JS = """
const url = arguments[0];
const bodyJson = arguments[1];
const callback = arguments[arguments.length - 1];
fetch(url, {
    method: 'POST',
    credentials: 'include',
    headers: {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'Origin': 'https://ieeexplore.ieee.org',
        'Referer': 'https://ieeexplore.ieee.org/search/searchresult.jsp',
    },
    body: bodyJson,
}).then(r => {
    if (!r.ok) {
        return callback({_error: 'HTTP ' + r.status});
    }
    return r.json().then(data => callback(data));
}).catch(err => callback({_error: String(err)}));
"""
