"""Shared raw-Selenium helpers for WebRunner-based source plugins.

Why not je_web_runner directly
------------------------------
``je_web_runner.webdriver_wrapper_instance`` is a module-level
singleton. When the pipeline runs sources concurrently
(``asyncio.gather`` fans out Scholar, IEEE, etc. simultaneously),
the Scholar backend and the IEEE backend both call
``set_driver(...)`` against the SAME singleton — they fight over it,
one Chrome becomes orphaned, the other's ``execute_async_script`` /
``page_source`` reads a window in the wrong state. The symptom is
silent: no exception, no log, just a hung Chrome window stuck on a
home page and an empty result set from the affected source.

This module sidesteps the singleton by spinning up a fresh
``selenium.webdriver.Chrome`` per call. Each WebRunner-backed search
owns its driver, never shares state, and quits cleanly when done.
"""

from __future__ import annotations

import os
import time
from typing import Any

from thesisagents.utils.logging import get_logger

_LOG = get_logger(__name__)

_DISABLE_ENV = "THESISAGENTS_DISABLE_WEBRUNNER"
_PROFILE_DIR_ENV = "THESISAGENTS_CHROME_PROFILE_DIR"

#: URL fragments and body markers that indicate the page is a captcha
#: / 'unusual traffic' interstitial instead of the expected content.
#: Combined Google + IEEE patterns; safe to grep both.
_CAPTCHA_URL_FRAGMENTS: tuple[str, ...] = (
    "/sorry/",
    "/captcha",
    "/recaptcha",
)
_CAPTCHA_BODY_MARKERS: tuple[str, ...] = (
    "Our systems have detected unusual traffic",
    'id="captcha-form"',
    "g-recaptcha",
    "Please show you're not a robot",
    "Please verify you're a human",
    "Verify you're not a robot",
    "Access blocked",
)


def is_available() -> bool:
    """True when ``selenium`` is importable AND ``THESISAGENTS_DISABLE_WEBRUNNER``
    is not set.
    """
    if os.environ.get(_DISABLE_ENV) == "1":
        return False
    try:
        import selenium  # noqa: F401
    except ImportError:
        return False
    return True


def make_driver(*, download_dir: str | None = None) -> Any:
    """Boot a fresh visible Chrome with anti-detection options.

    Returns a ``selenium.webdriver.Chrome`` instance the caller is
    responsible for closing (``.quit()``). When ``download_dir`` is
    provided, Chrome is configured to save PDFs straight to disk
    instead of opening the built-in viewer.
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=en-US")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,720")
    profile_dir = os.environ.get(_PROFILE_DIR_ENV, "").strip()
    if profile_dir:
        options.add_argument(f"--user-data-dir={profile_dir}")
    if download_dir:
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": False,
        }
        options.add_experimental_option("prefs", prefs)
    return webdriver.Chrome(options=options)


def is_captcha_page(driver: Any) -> bool:
    """True when the driver is currently on a captcha / blocked page."""
    try:
        current_url = driver.current_url or ""
        body = driver.page_source or ""
    except Exception:  # noqa: BLE001 — best-effort detection
        return False
    if any(fragment in current_url for fragment in _CAPTCHA_URL_FRAGMENTS):
        return True
    head = body[:8192]
    return any(marker in head for marker in _CAPTCHA_BODY_MARKERS)


def wait_for_captcha_solved(
    driver: Any,
    *,
    max_wait_seconds: float = 300.0,
    poll_interval: float = 2.0,
) -> bool:
    """Wait for the user to solve a captcha visible in the Chrome window.

    If the current page is NOT a captcha, returns True immediately.
    Otherwise polls every ``poll_interval`` seconds until either the
    captcha state clears (user solved it; URL changes back to the
    real page) or ``max_wait_seconds`` elapses.

    Returns True when the captcha cleared, False when the max wait
    elapsed without resolution. Never raises.
    """
    if not is_captcha_page(driver):
        return True
    try:
        starting_url = driver.current_url or ""
    except Exception:  # noqa: BLE001
        starting_url = ""
    _LOG.warning(
        "Captcha / 'unusual traffic' page detected at %s. Solve it in "
        "the visible Chrome window — waiting up to %.0fs.",
        starting_url, max_wait_seconds,
    )
    deadline = time.monotonic() + max_wait_seconds
    while time.monotonic() < deadline:
        time.sleep(poll_interval)
        if not is_captcha_page(driver):
            _LOG.info("Captcha cleared — continuing.")
            return True
    _LOG.warning("Captcha not solved within timeout; giving up on this source.")
    return False
