"""IEEE Xplore search via WebRunner (real visible Chrome browser).

Uses the shared ``webrunner_browser`` helper which avoids the
``je_web_runner`` singleton (would race against the Scholar backend
when sources fan out in parallel via ``asyncio.gather``).

Flow per search:
1. Boot a fresh visible Chrome.
2. Navigate to ``https://ieeexplore.ieee.org/Xplore/home.jsp`` so the
   page sets the session cookies the REST endpoint requires.
3. If IEEE serves a 'verify you're human' / 'access blocked' page,
   wait up to 5 minutes for the user to clear it.
4. ``execute_async_script`` runs ``fetch('/rest/search', POST, body)``
   inside the IEEE origin so the request carries the right cookies,
   ``Origin`` header, and JS-engine fingerprint.
5. Parse the returned JSON with the existing :func:`parse_search_record`.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any

from thesisagents.fetchers import webrunner_browser
from thesisagents.utils.logging import get_logger

_LOG = get_logger(__name__)

_HOME_URL = "https://ieeexplore.ieee.org/Xplore/home.jsp"
_SEARCH_REST = "https://ieeexplore.ieee.org/rest/search"
_DOCUMENT_URL = "https://ieeexplore.ieee.org/document/{arnumber}"
_INITIAL_RENDER_WAIT_SECONDS = 4.0
_SCRIPT_TIMEOUT_SECONDS = 30
_CAPTCHA_MAX_WAIT_SECONDS = 300.0
_DOCUMENT_RENDER_WAIT_SECONDS = 4.0


def is_available() -> bool:
    """Re-exported from the shared browser helper."""
    return webrunner_browser.is_available()


async def fetch_search_json(body: dict[str, Any]) -> dict[str, Any]:
    """POST ``/rest/search`` from inside the IEEE origin via real Chrome."""
    return await asyncio.to_thread(_search_via_chrome_sync, body)


async def fetch_document_html(arnumber: str) -> str:
    """Navigate to ``/document/<arnumber>`` via real Chrome, return HTML."""
    url = _DOCUMENT_URL.format(arnumber=arnumber)
    return await asyncio.to_thread(_document_via_chrome_sync, url)


def _search_via_chrome_sync(body: dict[str, Any]) -> dict[str, Any]:
    """Boot Chrome → land on IEEE home → JS-fetch POST → return JSON."""
    try:
        driver = webrunner_browser.make_driver()
    except Exception as err:  # noqa: BLE001
        raise RuntimeError(f"WebRunner cannot start chrome: {err}") from err

    try:
        driver.get(_HOME_URL)
        import time
        time.sleep(_INITIAL_RENDER_WAIT_SECONDS)
        # Some IEEE regions serve a 'verify you're human' page on first
        # visit; wait for the user to clear it before issuing the fetch.
        webrunner_browser.wait_for_captcha_solved(
            driver, max_wait_seconds=_CAPTCHA_MAX_WAIT_SECONDS,
        )
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
        _LOG.info(
            "IEEE WebRunner fetch returned %d records",
            len(result.get("records") or []),
        )
        return result
    except Exception as err:  # noqa: BLE001
        raise RuntimeError(f"WebRunner IEEE search failed: {err}") from err
    finally:
        with contextlib.suppress(Exception):
            driver.quit()


def _document_via_chrome_sync(url: str) -> str:
    try:
        driver = webrunner_browser.make_driver()
    except Exception as err:  # noqa: BLE001
        raise RuntimeError(f"WebRunner cannot start chrome: {err}") from err

    try:
        driver.get(url)
        import time
        time.sleep(_DOCUMENT_RENDER_WAIT_SECONDS)
        webrunner_browser.wait_for_captcha_solved(
            driver, max_wait_seconds=_CAPTCHA_MAX_WAIT_SECONDS,
        )
        try:
            html = driver.page_source
        except Exception as err:  # noqa: BLE001
            raise RuntimeError(f"IEEE document page_source failed: {err}") from err
        if not html:
            raise RuntimeError("IEEE document page_source is empty")
        return html
    finally:
        with contextlib.suppress(Exception):
            driver.quit()


# JS executed inside the IEEE origin to POST /rest/search with the
# right cookies + Origin header. Returns the JSON via async callback;
# on failure returns an object with ``_error`` set so the Python side
# surfaces a meaningful error.
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
