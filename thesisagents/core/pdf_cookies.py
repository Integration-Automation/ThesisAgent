"""Optional cookie jar for PDF downloads.

Some publishers (IEEE, ACM, Elsevier, Springer) return 403 to anonymous
requests for paywalled PDFs even when OpenAlex hands us a direct URL.
Users with institutional access can opt-in by exporting their browser
cookies to a Netscape-format ``cookies.txt`` file and pointing the env
var ``THESISAGENTS_PDF_COOKIES_FILE`` at it.

* **Off by default.** No file → no cookies attached → unchanged behaviour.
* **User responsibility.** Using session cookies to fetch paywalled PDFs
  may violate the publisher's terms of service. The startup warning makes
  the activation visible; the user accepts the risk by setting the env var.
* **Scope.** Cookies are only attached to PDF download requests, never to
  search-API calls.
"""

from __future__ import annotations

import os
from http.cookiejar import Cookie, MozillaCookieJar
from pathlib import Path
from urllib.parse import urlparse

from thesisagents.utils.logging import get_logger

_LOG = get_logger(__name__)
_ENV_VAR = "THESISAGENTS_PDF_COOKIES_FILE"

_jar: MozillaCookieJar | None = None
_load_attempted: bool = False
_load_warned: bool = False


def _load_jar() -> MozillaCookieJar | None:
    """Lazily parse the cookies file. Returns None when the env var is unset
    or the file can't be read; logs an explanation in both cases."""
    global _jar, _load_attempted, _load_warned
    if _load_attempted:
        return _jar
    _load_attempted = True
    path_str = (os.environ.get(_ENV_VAR) or "").strip()
    if not path_str:
        return None
    path = Path(path_str).expanduser()
    if not path.is_file():
        _LOG.warning(
            "%s set to %s but file does not exist; cookies disabled.",
            _ENV_VAR, path,
        )
        return None
    jar = MozillaCookieJar(str(path))
    try:
        # ignore_discard / ignore_expires keep session-scoped cookies that
        # the user's browser exported as expiring at unix-epoch zero, which
        # are exactly the auth cookies we need for paywalled hosts.
        jar.load(ignore_discard=True, ignore_expires=True)
    except Exception as err:  # noqa: BLE001  # MozillaCookieJar raises various types
        _LOG.warning(
            "could not parse cookies file %s: %s; cookies disabled.",
            path, err,
        )
        return None
    if not _load_warned:
        _LOG.warning(
            "PDF cookies loaded from %s (%d entries). The cookies will be "
            "attached to PDF download requests for matching hosts; you are "
            "responsible for compliance with each publisher's terms of "
            "service.",
            path, len(list(jar)),
        )
        _load_warned = True
    _jar = jar
    return jar


def cookies_for_url(url: str) -> dict[str, str]:
    """Return a ``{name: value}`` mapping of cookies whose domain matches
    ``url``. Empty dict when cookies are disabled or the host has no
    matching cookies in the jar."""
    jar = _load_jar()
    if jar is None or not url:
        return {}
    host = urlparse(url).hostname or ""
    if not host:
        return {}
    matched: dict[str, str] = {}
    for cookie in jar:
        if _domain_matches(host, cookie):
            matched[cookie.name] = cookie.value or ""
    return matched


def _domain_matches(host: str, cookie: Cookie) -> bool:
    """Apply standard cookie-domain matching rules.

    A cookie with domain ``.example.com`` matches ``host == example.com``
    and any subdomain. A cookie with domain ``example.com`` (no leading
    dot, host-only) matches only the exact host.
    """
    cookie_domain = (cookie.domain or "").lower()
    host = host.lower()
    if not cookie_domain:
        return False
    if cookie_domain.startswith("."):
        bare = cookie_domain[1:]
        return host == bare or host.endswith(cookie_domain)
    return host == cookie_domain


def _reset_for_tests() -> None:
    """Test-only hook so each test starts with a fresh load state."""
    global _jar, _load_attempted, _load_warned
    _jar = None
    _load_attempted = False
    _load_warned = False
