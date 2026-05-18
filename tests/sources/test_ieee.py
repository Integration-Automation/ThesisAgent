"""IEEE plugin tests."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from autopapertoppt.core.exceptions import ConfigError, ParseError, SourceUnavailableError
from autopapertoppt.core.models import Query
from tests.sources._mock import MockTransport, install_mock

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "ieee"


def _fixture(name: str) -> str:
    return (_FIXTURE_DIR / name).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _isolate_ieee_env(monkeypatch):
    """IEEE is now default-on; make sure no DISABLE flag leaks. Also
    force WebRunner off so the existing tests that monkeypatch the
    httpx transport stay valid — the few tests that specifically want
    to exercise the WebRunner path opt in by setting is_available."""
    monkeypatch.delenv("AUTOPAPERTOPPT_DISABLE_IEEE_SCRAPING", raising=False)
    monkeypatch.setenv("AUTOPAPERTOPPT_DISABLE_WEBRUNNER", "1")


def _new_fetcher():
    from ieee.fetcher import IeeeFetcher

    return IeeeFetcher()


async def test_opt_out_disables_plugin(monkeypatch):
    """AUTOPAPERTOPPT_DISABLE_IEEE_SCRAPING=1 raises ConfigError so the
    pipeline silently skips IEEE for users who explicitly opted out."""
    monkeypatch.setenv("AUTOPAPERTOPPT_DISABLE_IEEE_SCRAPING", "1")
    from ieee.fetcher import IeeeFetcher

    with pytest.raises(ConfigError):
        IeeeFetcher()


async def test_search_parses_rest_response(monkeypatch):
    transport = MockTransport(200, _fixture("search.json"))
    install_mock(monkeypatch, "ieee.fetcher", transport)
    papers = await _new_fetcher().search(
        Query(keywords="robotics", sources=("ieee",), max_results=10)
    )
    assert len(papers) == 2
    assert papers[0].source_id == "10965643"
    assert "Securing LLM Workloads" in papers[0].title
    assert papers[0].year == 2025
    assert papers[0].doi == "10.1109/ACCESS.2025.3561235"
    assert papers[0].pdf_url and papers[0].pdf_url.startswith("https://ieeexplore.ieee.org/")
    # HTML <mark> tag was stripped from title 2
    assert papers[1].title == "Another paper on robotics"
    assert transport.received_method == "POST"


async def test_fetch_by_id_metadata_blob(monkeypatch):
    transport = MockTransport(200, _fixture("document.html"))
    install_mock(monkeypatch, "ieee.fetcher", transport)
    paper = await _new_fetcher().fetch_by_id("10965643")
    assert paper.source_id == "10965643"
    assert paper.year == 2025
    assert paper.doi == "10.1109/ACCESS.2025.3561235"
    assert "IoRT" in paper.abstract
    assert paper.authors == ("Hassan Karim", "Deepti Gupta", "Sai Sitharaman")


async def test_fetch_by_id_non_digit_raises(monkeypatch):
    transport = MockTransport(200, "")
    install_mock(monkeypatch, "ieee.fetcher", transport)
    with pytest.raises(ParseError):
        await _new_fetcher().fetch_by_id("not-arnumber")


async def test_fetch_blocked_response_surfaces_unavailable(monkeypatch):
    transport = MockTransport(418, "I'm a teapot")
    install_mock(monkeypatch, "ieee.fetcher", transport)
    with pytest.raises(SourceUnavailableError):
        await _new_fetcher().fetch_by_id("10965643")


async def test_search_blocked_surfaces_unavailable(monkeypatch):
    transport = MockTransport(403, "forbidden")
    install_mock(monkeypatch, "ieee.fetcher", transport)
    with pytest.raises(SourceUnavailableError):
        await _new_fetcher().search(
            Query(keywords="x", sources=("ieee",), max_results=1)
        )


async def test_search_sends_referer_and_origin(monkeypatch):
    captured: dict[str, str] = {}

    class _CaptureTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            for k, v in request.headers.items():
                captured[k.lower()] = v
            return httpx.Response(
                200, content=b'{"records": []}', request=request
            )

        async def aclose(self):
            return None

    install_mock(monkeypatch, "ieee.fetcher", _CaptureTransport())
    await _new_fetcher().search(
        Query(keywords="x", sources=("ieee",), max_results=1)
    )
    assert "ieeexplore.ieee.org" in captured.get("referer", "")
    assert captured.get("origin") == "https://ieeexplore.ieee.org"


# ---------------------------------------------------------------------------
# Official API path — AUTOPAPERTOPPT_IEEE_API_KEY
# ---------------------------------------------------------------------------


async def test_api_key_takes_official_path(monkeypatch):
    """When the API key is set the plugin uses the official Xplore API."""
    monkeypatch.setenv("AUTOPAPERTOPPT_IEEE_API_KEY", "test-key")
    from ieee.fetcher import IeeeFetcher

    IeeeFetcher()  # must not raise


async def test_api_search_uses_api_endpoint_and_key(monkeypatch):
    monkeypatch.setenv("AUTOPAPERTOPPT_IEEE_API_KEY", "test-key")
    transport = MockTransport(200, _fixture("api_search.json"))
    install_mock(monkeypatch, "ieee.fetcher", transport)
    papers = await _new_fetcher().search(
        Query(
            keywords="LLM security",
            sources=("ieee",),
            max_results=10,
            year_from=2025,
            year_to=2026,
        )
    )
    assert transport.received_method == "GET"
    assert transport.received_url is not None
    assert "ieeexploreapi.ieee.org" in str(transport.received_url)
    assert transport.received_url.params.get("apikey") == "test-key"
    assert transport.received_url.params.get("querytext") == "LLM security"
    assert transport.received_url.params.get("start_year") == "2025"
    assert transport.received_url.params.get("end_year") == "2026"
    # Fixture has 2 articles
    assert len(papers) == 2
    first = papers[0]
    assert first.source_id == "10965643"
    assert first.title == "Securing LLM Workloads at Edge"
    assert first.year == 2025
    assert first.doi == "10.1109/ACCESS.2025.3561235"
    assert first.pdf_url and "stamp.jsp" in first.pdf_url
    # Author parsing covers full_name / first+last / preferred_name variants
    assert first.authors == ("Hassan Karim", "Deepti Gupta", "Sai Sitharaman")
    # Citation count from citing_paper_count
    assert first.citation_count == 4
    # Second paper has pdf_url=null → None
    assert papers[1].pdf_url is None


async def test_api_fetch_by_id_uses_article_number_param(monkeypatch):
    monkeypatch.setenv("AUTOPAPERTOPPT_IEEE_API_KEY", "test-key")
    transport = MockTransport(200, _fixture("api_search.json"))
    install_mock(monkeypatch, "ieee.fetcher", transport)
    paper = await _new_fetcher().fetch_by_id("10965643")
    assert transport.received_url is not None
    assert transport.received_url.params.get("article_number") == "10965643"
    assert paper.source_id == "10965643"


async def test_api_mode_no_api_key_falls_back_to_scrape(monkeypatch):
    """Without the API key the existing scraping path is used (default-on)."""
    monkeypatch.delenv("AUTOPAPERTOPPT_IEEE_API_KEY", raising=False)
    transport = MockTransport(200, _fixture("search.json"))
    install_mock(monkeypatch, "ieee.fetcher", transport)
    await _new_fetcher().search(
        Query(keywords="x", sources=("ieee",), max_results=1)
    )
    # Scraping POSTs to /rest/search, not the API endpoint
    assert transport.received_method == "POST"
    assert "ieeexploreapi.ieee.org" not in str(transport.received_url)


async def test_webrunner_search_used_when_available(monkeypatch):
    """When WebRunner is enabled, _scrape_search routes through it
    instead of the httpx POST."""
    from ieee import webrunner_backend

    monkeypatch.setattr(webrunner_backend, "is_available", lambda: True)

    captured: dict[str, object] = {}

    async def fake_fetch(body):
        captured["body"] = body
        return {"records": [], "totalRecords": 0}

    monkeypatch.setattr(webrunner_backend, "fetch_search_json", fake_fetch)
    papers = await _new_fetcher().search(
        Query(keywords="webrunner test", sources=("ieee",), max_results=5)
    )
    assert papers == []
    assert captured["body"]["queryText"] == "webrunner test"


async def test_webrunner_search_failure_falls_back_to_httpx(monkeypatch):
    """RuntimeError from the WebRunner backend triggers the httpx fallback."""
    from ieee import webrunner_backend

    monkeypatch.setattr(webrunner_backend, "is_available", lambda: True)

    async def explode(_body):
        raise RuntimeError("Chrome did not start")

    monkeypatch.setattr(webrunner_backend, "fetch_search_json", explode)

    transport = MockTransport(200, _fixture("search.json"))
    install_mock(monkeypatch, "ieee.fetcher", transport)
    papers = await _new_fetcher().search(
        Query(keywords="x", sources=("ieee",), max_results=10)
    )
    # httpx fallback worked → got the fixture's records.
    assert len(papers) > 0
