"""PDF download via WebRunner (real visible Chrome browser).

Why
---
Publisher PDF CDNs (IEEE Xplore, ACM Digital Library, Springer, Elsevier,
Wiley, Taylor & Francis, etc.) return 403 to httpx-style requests even
with browser headers + Referer + cookies. They fingerprint the TLS
handshake and the JavaScript engine to require a real Chrome.

This module routes PDF downloads for paywalled publisher domains
through a real visible Chrome instance configured to save PDFs
directly to disk (instead of opening the built-in PDF viewer). The
profile dir env var the rest of WebRunner uses is honoured here too,
so institutional auth cookies surface paywalled subscription PDFs
the same as they would in a normal browser session.

The actual Selenium calls run inside ``asyncio.to_thread`` so the
download doesn't block the pipeline's event loop while Chrome boots
+ waits for the file to appear (5-30s per PDF).
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

from autopapertoppt.utils.logging import get_logger

_LOG = get_logger(__name__)

_DISABLE_ENV = "AUTOPAPERTOPPT_DISABLE_WEBRUNNER"
_PROFILE_DIR_ENV = "AUTOPAPERTOPPT_CHROME_PROFILE_DIR"
#: Per-PDF wall-clock cap. Generous to handle 50-page Elsevier PDFs on
#: slow connections; Chrome boot + page-load is usually the bigger
#: fraction of this budget.
_DOWNLOAD_TIMEOUT_SECONDS = 60.0
_DOWNLOAD_POLL_INTERVAL = 0.5

#: Publisher CDN hosts where httpx-style PDF GETs reliably 403.
#: Anything resolved on these hosts is routed through WebRunner.
#: Subdomain matching: `endswith` on the hostname so
#: e.g. ``onlinelibrary.wiley.com`` matches the broader ``wiley.com``
#: entry.
_PAYWALLED_SUFFIXES: tuple[str, ...] = (
    "ieeexplore.ieee.org",
    "ieee.org",
    "dl.acm.org",
    "acm.org",
    "link.springer.com",
    "springer.com",
    "sciencedirect.com",
    "elsevier.com",
    "onlinelibrary.wiley.com",
    "wiley.com",
    "tandfonline.com",
    "academic.oup.com",
    "oup.com",
    "nature.com",
    "science.org",
    "asme.org",
    "asce.org",
    "ascelibrary.org",
)


def is_available() -> bool:
    """True when je_web_runner is importable AND not explicitly disabled."""
    if os.environ.get(_DISABLE_ENV) == "1":
        return False
    try:
        import selenium  # noqa: F401
    except ImportError:
        return False
    return True


def should_use_webrunner(url: str) -> bool:
    """True when the URL's host is a known paywalled publisher CDN."""
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    return any(host.endswith(suffix) for suffix in _PAYWALLED_SUFFIXES)


async def download_via_browser(url: str, target: Path) -> bool:
    """Drive Chrome to download a PDF, copy it to ``target``.

    Returns True on success (target file written and ≥ 4 bytes starting
    with ``%PDF``), False on any failure. Never raises — callers fall
    back to the httpx path on False.
    """
    return await asyncio.to_thread(_download_sync, url, target)


def _download_sync(url: str, target: Path) -> bool:
    """Boot Chrome → navigate to PDF URL → wait for file → copy to target."""
    from autopapertoppt.fetchers import webrunner_browser

    tmpdir = Path(tempfile.mkdtemp(prefix="autopapertoppt_pdf_"))
    try:
        try:
            driver = webrunner_browser.make_driver(download_dir=str(tmpdir))
        except Exception as err:  # noqa: BLE001 — Selenium raises many types
            _LOG.warning("WebRunner PDF: cannot start Chrome: %s", err)
            return False
        try:
            return _navigate_and_collect(driver, url, tmpdir, target)
        finally:
            with contextlib.suppress(Exception):
                driver.quit()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _navigate_and_collect(driver, url: str, tmpdir: Path, target: Path) -> bool:
    """Navigate to ``url``, poll ``tmpdir`` for a finished PDF, copy to target."""
    try:
        driver.get(url)
    except Exception as err:  # noqa: BLE001
        _LOG.warning("WebRunner PDF: navigation failed for %s: %s", url, err)
        return False

    deadline = time.monotonic() + _DOWNLOAD_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        partials = list(tmpdir.glob("*.crdownload"))
        completed = [p for p in tmpdir.iterdir() if p.suffix.lower() == ".pdf"]
        if completed and not partials:
            return _persist_downloaded_pdf(completed[0], target)
        time.sleep(_DOWNLOAD_POLL_INTERVAL)
    _LOG.warning("WebRunner PDF: timed out waiting for %s", url)
    return False


def _persist_downloaded_pdf(source: Path, target: Path) -> bool:
    """Validate the magic bytes, copy to ``target``, return success."""
    try:
        head = source.read_bytes()[:4]
    except OSError as err:
        _LOG.warning("WebRunner PDF: cannot read %s: %s", source, err)
        return False
    if not head.startswith(b"%PDF"):
        _LOG.warning("WebRunner PDF: %s is not a PDF (head=%r)", source, head)
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(source), str(target))
    except OSError as err:
        _LOG.warning(
            "WebRunner PDF: cannot move %s -> %s: %s", source, target, err,
        )
        return False
    return True
