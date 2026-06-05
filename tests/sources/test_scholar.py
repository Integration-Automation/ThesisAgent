"""Google Scholar plugin tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.sources._mock import MockTransport, install_mock
from thesisagents.core.exceptions import (
    ConfigError,
    ParseError,
    SourceUnavailableError,
)
from thesisagents.core.models import Query

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "scholar"


def _fixture(name: str) -> str:
    return (_FIXTURE_DIR / name).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _isolate_scholar_env(monkeypatch):
    """Scholar is now default-on; make sure no DISABLE flag leaks from
    the host env. Also force WebRunner off by default so tests that
    install a MockTransport on the httpx client exercise that path —
    tests that specifically want the WebRunner path opt in by setting
    is_available themselves.

    Also reset the process-level captcha cooldown between tests so a
    previous test's lockout doesn't bleed into the next.
    """
    monkeypatch.delenv("THESISAGENTS_DISABLE_SCHOLAR_SCRAPING", raising=False)
    monkeypatch.setenv("THESISAGENTS_DISABLE_WEBRUNNER", "1")
    import thesisagents.sources.scholar.fetcher as scholar_mod
    scholar_mod._captcha_locked_until = 0.0  # noqa: SLF001
    yield
    scholar_mod._captcha_locked_until = 0.0  # noqa: SLF001


def _new_fetcher():
    from thesisagents.sources.scholar.fetcher import ScholarFetcher

    return ScholarFetcher()


async def test_opt_out_disables_plugin(monkeypatch):
    """THESISAGENTS_DISABLE_SCHOLAR_SCRAPING=1 raises ConfigError so the
    pipeline silently skips Scholar for users who explicitly opted out."""
    monkeypatch.setenv("THESISAGENTS_DISABLE_SCHOLAR_SCRAPING", "1")
    from thesisagents.sources.scholar.fetcher import ScholarFetcher

    with pytest.raises(ConfigError):
        ScholarFetcher()


def test_captcha_detection_matches_known_markers():
    from thesisagents.sources.scholar.fetcher import _is_captcha_response

    # /sorry/ URL is the canonical lockout endpoint.
    assert _is_captcha_response(
        "https://www.google.com/sorry/index?continue=...", ""
    ) is True
    # Body markers also trigger.
    assert _is_captcha_response(
        "https://scholar.google.com/scholar?q=x",
        "<html><body>Our systems have detected unusual traffic...</body></html>",
    ) is True
    assert _is_captcha_response(
        "https://scholar.google.com/scholar?q=x",
        '<form id="captcha-form">',
    ) is True
    # Real SERP HTML does not.
    assert _is_captcha_response(
        "https://scholar.google.com/scholar?q=attention",
        "<html><div class='gs_r'>...</div></html>",
    ) is False


async def test_captcha_cooldown_engages_after_captcha_response(monkeypatch):
    """After one captcha hit, subsequent calls raise immediately."""
    import thesisagents.sources.scholar.fetcher as scholar_mod
    from thesisagents.core.exceptions import SourceUnavailableError

    # Reset the process-level flag in case a prior test set it.
    scholar_mod._captcha_locked_until = 0.0

    class CaptchaResponse:
        url = "https://www.google.com/sorry/index"
        status_code = 200
        text = ""

    class CaptchaClient:
        async def get(self, *_args, **_kwargs):
            return CaptchaResponse()

    async def fake_get_client(_name):
        return CaptchaClient()

    monkeypatch.setattr(scholar_mod, "get_client", fake_get_client)
    fetcher = _new_fetcher()

    with pytest.raises(SourceUnavailableError, match="captcha"):
        await fetcher.search(
            Query(keywords="x", sources=("scholar",), max_results=1)
        )
    # Cooldown is now set. A second call should raise immediately
    # WITHOUT issuing an HTTP request.
    assert scholar_mod._captcha_locked_until > 0
    with pytest.raises(SourceUnavailableError, match="cooldown"):
        await fetcher.search(
            Query(keywords="y", sources=("scholar",), max_results=1)
        )
    # Reset so other tests aren't affected.
    scholar_mod._captcha_locked_until = 0.0


async def test_search_parses_serp(monkeypatch):
    transport = MockTransport(200, _fixture("serp.html"))
    install_mock(monkeypatch, "thesisagents.sources.scholar.fetcher", transport)
    papers = await _new_fetcher().search(
        Query(keywords="attention", sources=("scholar",), max_results=10)
    )
    assert len(papers) == 2
    assert papers[0].title == "Attention Is All You Need"
    assert papers[0].url == "https://arxiv.org/abs/1706.03762"
    assert papers[0].year == 2017
    assert papers[0].citation_count == 100000
    assert papers[0].authors == ("A Vaswani", "N Shazeer", "N Parmar")


async def test_search_captcha_raises_unavailable(monkeypatch):
    transport = MockTransport(200, _fixture("captcha.html"))
    install_mock(monkeypatch, "thesisagents.sources.scholar.fetcher", transport)
    with pytest.raises(SourceUnavailableError):
        await _new_fetcher().search(
            Query(keywords="x", sources=("scholar",), max_results=1)
        )


async def test_fetch_by_id_unsupported(monkeypatch):
    transport = MockTransport(200, "")
    install_mock(monkeypatch, "thesisagents.sources.scholar.fetcher", transport)
    with pytest.raises(ParseError):
        await _new_fetcher().fetch_by_id("anything")


async def test_search_403_surfaces_unavailable(monkeypatch):
    transport = MockTransport(403, "Forbidden")
    install_mock(monkeypatch, "thesisagents.sources.scholar.fetcher", transport)
    with pytest.raises(SourceUnavailableError):
        await _new_fetcher().search(
            Query(keywords="x", sources=("scholar",), max_results=1)
        )


async def test_webrunner_backend_used_when_available(monkeypatch):
    """When je_web_runner is importable, search() uses the real-browser
    backend instead of httpx."""
    from thesisagents.sources.scholar import webrunner_backend

    monkeypatch.setattr(webrunner_backend, "is_available", lambda: True)

    captured: dict[str, object] = {}

    async def fake_fetch(query):
        captured["query"] = query
        return _fixture("serp.html")

    monkeypatch.setattr(webrunner_backend, "fetch_serp_html", fake_fetch)
    papers = await _new_fetcher().search(
        Query(keywords="attention", sources=("scholar",), max_results=10)
    )
    assert captured["query"].keywords == "attention"
    assert papers and papers[0].title == "Attention Is All You Need"


async def test_webrunner_failure_falls_back_to_httpx(monkeypatch):
    """If WebRunner crashes (Chrome unavailable etc.), the httpx path runs."""
    from thesisagents.sources.scholar import webrunner_backend

    monkeypatch.setattr(webrunner_backend, "is_available", lambda: True)

    async def explode(_query):
        raise RuntimeError("Chrome did not start")

    monkeypatch.setattr(webrunner_backend, "fetch_serp_html", explode)

    transport = MockTransport(200, _fixture("serp.html"))
    install_mock(monkeypatch, "thesisagents.sources.scholar.fetcher", transport)
    papers = await _new_fetcher().search(
        Query(keywords="attention", sources=("scholar",), max_results=1)
    )
    # httpx fallback succeeded.
    assert papers and papers[0].title


def test_webrunner_is_available_respects_disable_env(monkeypatch):
    """THESISAGENTS_DISABLE_WEBRUNNER=1 forces the httpx path even
    when je_web_runner is installed."""
    from thesisagents.sources.scholar import webrunner_backend

    monkeypatch.setenv("THESISAGENTS_DISABLE_WEBRUNNER", "1")
    assert webrunner_backend.is_available() is False


def test_chrome_args_always_visible_no_profile(monkeypatch):
    """Always-visible policy: no --headless flag ever, profile only when set."""
    from thesisagents.sources.scholar import webrunner_backend

    monkeypatch.delenv("THESISAGENTS_CHROME_PROFILE_DIR", raising=False)
    args = webrunner_backend._build_chrome_args()  # noqa: SLF001
    assert "--headless=new" not in args
    assert not any(a.startswith("--headless") for a in args)
    assert "--disable-blink-features=AutomationControlled" in args
    assert not any(a.startswith("--user-data-dir=") for a in args)


def test_chrome_args_with_profile_dir_passes_user_data_dir(monkeypatch):
    from thesisagents.sources.scholar import webrunner_backend

    monkeypatch.setenv("THESISAGENTS_CHROME_PROFILE_DIR", "D:/scholar-profile")
    args = webrunner_backend._build_chrome_args()  # noqa: SLF001
    assert "--user-data-dir=D:/scholar-profile" in args
    # Still no headless flag — visible is mandatory.
    assert not any(a.startswith("--headless") for a in args)
