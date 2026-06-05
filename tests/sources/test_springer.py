"""Springer Nature plugin tests against the recorded fixture."""

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
from thesisagents.sources.springer.fetcher import SpringerFetcher
from thesisagents.sources.springer.parser import parse_record

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "springer"
_FIXTURE_BYTES = (_FIXTURE_DIR / "llm_security.json").read_bytes()


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


@pytest.fixture(autouse=True)
def _reset_clients_and_key(monkeypatch):
    monkeypatch.setenv("THESISAGENTS_SPRINGER_API_KEY", "test-key")
    yield
    http_module._CLIENTS.clear()  # noqa: SLF001


def _install(monkeypatch, transport):
    http_module._CLIENTS.clear()  # noqa: SLF001

    async def fake_get_client(_source):
        return httpx.AsyncClient(transport=transport)

    monkeypatch.setattr("thesisagents.sources.springer.fetcher.get_client", fake_get_client)


async def test_search_returns_papers(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await SpringerFetcher().search(
        Query(keywords="LLM security", sources=("springer",), max_results=10)
    )
    assert len(papers) == 2
    first = papers[0]
    assert first.source == "springer"
    assert first.title.startswith("Adversarial Robustness")
    assert first.authors == ("Kavya Kumar", "Lewis Lin")
    assert first.year == 2025
    assert first.venue == "Nature"
    assert first.doi == "10.1038/s41586-025-09999-3"
    assert first.url.startswith("https://link.springer.com/")
    assert "<i>" not in (first.abstract or "")
    assert first.citation_count == 4


async def test_search_passes_api_key_query_param(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    await SpringerFetcher().search(
        Query(keywords="x", sources=("springer",), max_results=1)
    )
    [request] = transport.requests
    assert request.url.params.get("api_key") == "test-key"


async def test_search_appends_year_filter_to_query(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    await SpringerFetcher().search(
        Query(
            keywords="x",
            sources=("springer",),
            max_results=1,
            year_from=2025,
            year_to=2026,
        )
    )
    [request] = transport.requests
    q = request.url.params.get("q") or ""
    assert "datefrom:2025-01-01" in q
    assert "dateto:2026-12-31" in q


async def test_search_respects_max_results(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await SpringerFetcher().search(
        Query(keywords="x", sources=("springer",), max_results=1)
    )
    assert len(papers) == 1


def test_construction_without_api_key_raises_config_error(monkeypatch):
    """ConfigError must fire at construction so load_fetcher_safe skips us."""
    monkeypatch.delenv("THESISAGENTS_SPRINGER_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        SpringerFetcher()


async def test_search_raises_config_error_on_401(monkeypatch):
    transport = _CannedTransport(b"unauthorized", status=401)
    _install(monkeypatch, transport)
    with pytest.raises(ConfigError):
        await SpringerFetcher().search(
            Query(keywords="x", sources=("springer",), max_results=1)
        )


async def test_search_raises_on_rate_limit(monkeypatch):
    transport = _CannedTransport(b"", status=429)
    _install(monkeypatch, transport)
    with pytest.raises(RateLimitError):
        await SpringerFetcher().search(
            Query(keywords="x", sources=("springer",), max_results=1)
        )


async def test_search_raises_on_server_error(monkeypatch):
    transport = _CannedTransport(b"oops", status=503)
    _install(monkeypatch, transport)
    with pytest.raises(SourceUnavailableError):
        await SpringerFetcher().search(
            Query(keywords="x", sources=("springer",), max_results=1)
        )


async def test_search_raises_on_bad_json(monkeypatch):
    transport = _CannedTransport(b"<html>", status=200)
    _install(monkeypatch, transport)
    with pytest.raises(ParseError):
        await SpringerFetcher().search(
            Query(keywords="x", sources=("springer",), max_results=1)
        )


# ---------------------------------------------------------------------------
# Pure-parser tests (no HTTP)
# ---------------------------------------------------------------------------


def test_parse_record_prefers_html_url():
    record = {
        "identifier": "doi:10.1/x",
        "title": "T",
        "doi": "10.1/x",
        "publicationDate": "2025-01-01",
        "url": [
            {"value": "https://example/doi", "format": "", "platform": "doi"},
            {"value": "https://example/html", "format": "html", "platform": "web"},
        ],
    }
    assert parse_record(record).url == "https://example/html"


def test_parse_record_falls_back_to_doi():
    record = {
        "identifier": "doi:10.1/x",
        "title": "T",
        "doi": "10.1/x",
        "publicationDate": "2025-01-01",
        "url": [],
    }
    assert parse_record(record).url == "https://doi.org/10.1/x"


def test_parse_record_year_from_partial_date():
    record = {"identifier": "x", "title": "T", "publicationDate": "2025"}
    assert parse_record(record).year == 2025
