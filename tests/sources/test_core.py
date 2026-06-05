"""CORE plugin tests against the recorded `llm_security.json` fixture.

CORE is opt-in: the fetcher raises ConfigError at construction without a key, so
every test that constructs ``CoreFetcher`` sets ``THESISAGENTS_CORE_API_KEY``
first via the autouse fixture.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from thesisagents.core.exceptions import (
    ConfigError,
    ParseError,
    RateLimitError,
    SourceUnavailableError,
)
from thesisagents.core.models import Query
from thesisagents.fetchers import http as http_module
from thesisagents.sources.core.parser import in_year_range, parse_result

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "core"
_FIXTURE_BYTES = (_FIXTURE_DIR / "llm_security.json").read_bytes()
_KEY_ENV = "THESISAGENTS_CORE_API_KEY"


@pytest.fixture(autouse=True)
def _core_key(monkeypatch):
    monkeypatch.setenv(_KEY_ENV, "test-key")
    yield
    http_module._CLIENTS.clear()  # noqa: SLF001


def _make_fetcher():
    # Imported lazily so the env var (set by the autouse fixture) is present
    # before construction, which would otherwise raise ConfigError.
    from thesisagents.sources.core.fetcher import CoreFetcher

    return CoreFetcher()


class _CannedTransport(httpx.AsyncBaseTransport):
    def __init__(self, body: bytes, status: int = 200):
        self.body = body
        self.status = status
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request):
        self.requests.append(request)
        return httpx.Response(self.status, content=self.body, request=request)

    async def aclose(self):
        return None


def _install(monkeypatch, transport):
    http_module._CLIENTS.clear()  # noqa: SLF001

    async def fake_get_client(_source):
        return httpx.AsyncClient(transport=transport)

    monkeypatch.setattr("thesisagents.sources.core.fetcher.get_client", fake_get_client)


async def test_search_returns_papers(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await _make_fetcher().search(
        Query(keywords="LLM Security", sources=("core",), max_results=10)
    )
    assert len(papers) == 3
    first = papers[0]
    assert first.source == "core"
    assert first.title.startswith("Scalable Open-Access Retrieval")
    assert first.authors == ("Andersson, Alice", "Bertelsen, Bob")
    assert first.year == 2025
    assert first.venue == "Journal of Open Access"
    assert first.doi == "10.5555/core.2025.0001"
    assert first.url == "https://core.ac.uk/works/5000001"
    assert first.pdf_url == "https://core.ac.uk/download/5000001.pdf"


async def test_search_venue_falls_back_to_publisher(monkeypatch):
    """The second record has no journals[] — venue falls back to publisher,
    and an empty downloadUrl yields no pdf_url."""
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await _make_fetcher().search(
        Query(keywords="LLM Security", sources=("core",), max_results=10)
    )
    second = papers[1]
    assert second.venue == "Independent Press"
    assert second.pdf_url is None


async def test_search_sends_bearer_header(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    await _make_fetcher().search(
        Query(keywords="LLM Security", sources=("core",), max_results=5)
    )
    [request] = transport.requests
    assert request.headers.get("authorization") == "Bearer test-key"
    assert request.url.params.get("q") == "LLM Security"
    assert int(request.url.params.get("limit") or "0") >= 5


async def test_search_year_filter_drops_old_papers(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await _make_fetcher().search(
        Query(
            keywords="LLM Security",
            sources=("core",),
            max_results=10,
            year_from=2025,
        )
    )
    assert {p.year for p in papers} == {2025}
    assert len(papers) == 2


async def test_search_respects_max_results(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await _make_fetcher().search(
        Query(keywords="LLM Security", sources=("core",), max_results=1)
    )
    assert len(papers) == 1


async def test_missing_key_raises_config_error(monkeypatch):
    monkeypatch.delenv(_KEY_ENV, raising=False)
    from thesisagents.sources.core.fetcher import CoreFetcher

    with pytest.raises(ConfigError):
        CoreFetcher()


async def test_search_raises_on_bad_key(monkeypatch):
    transport = _CannedTransport(b"", status=401)
    _install(monkeypatch, transport)
    with pytest.raises(ConfigError):
        await _make_fetcher().search(
            Query(keywords="x", sources=("core",), max_results=1)
        )


async def test_search_raises_on_rate_limit(monkeypatch):
    transport = _CannedTransport(b"", status=429)
    _install(monkeypatch, transport)
    with pytest.raises(RateLimitError):
        await _make_fetcher().search(
            Query(keywords="x", sources=("core",), max_results=1)
        )


async def test_search_raises_on_server_error(monkeypatch):
    transport = _CannedTransport(b"oops", status=503)
    _install(monkeypatch, transport)
    with pytest.raises(SourceUnavailableError):
        await _make_fetcher().search(
            Query(keywords="x", sources=("core",), max_results=1)
        )


async def test_search_raises_on_bad_json(monkeypatch):
    transport = _CannedTransport(b"<html>not json</html>", status=200)
    _install(monkeypatch, transport)
    with pytest.raises(ParseError):
        await _make_fetcher().search(
            Query(keywords="x", sources=("core",), max_results=1)
        )


# ---------------------------------------------------------------------------
# Pure-parser tests (no HTTP, no key)
# ---------------------------------------------------------------------------


def test_parse_result_url_falls_back_to_doi():
    result = {"title": "Paper", "doi": "10.1/abc"}
    assert parse_result(result).url == "https://doi.org/10.1/abc"


def test_parse_result_handles_missing_authors():
    result = {"id": 1, "title": "Paper", "yearPublished": 2024}
    assert parse_result(result).authors == ()


def test_in_year_range_handles_none():
    assert in_year_range(2025, 2024, 2026) is True
    assert in_year_range(2023, 2024, 2026) is False
    assert in_year_range(None, 2024, 2026) is False
    assert in_year_range(None, None, None) is True
    assert in_year_range(2025, None, None) is True
