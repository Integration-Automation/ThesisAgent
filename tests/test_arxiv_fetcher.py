"""ArxivFetcher against a mocked HTTP transport — no live network."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from thesisagents.core.exceptions import (
    ParseError,
    RateLimitError,
    SourceUnavailableError,
)
from thesisagents.core.models import Query
from thesisagents.fetchers import http as http_module
from thesisagents.sources.arxiv.fetcher import ArxivFetcher


@pytest.fixture()
def fixture_xml(arxiv_fixture_path: Path) -> str:
    return arxiv_fixture_path.read_text(encoding="utf-8")


class _MockTransport(httpx.AsyncBaseTransport):
    def __init__(self, status: int, body: str) -> None:
        self._status = status
        self._body = body
        self.received_url: httpx.URL | None = None

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.received_url = request.url
        return httpx.Response(
            self._status,
            content=self._body.encode("utf-8"),
            request=request,
        )

    async def aclose(self):
        return None


@pytest.fixture(autouse=True)
def _reset_clients():
    yield
    http_module._CLIENTS.clear()


async def _install_mock(monkeypatch, transport: _MockTransport) -> None:
    async def fake_get_client(source: str) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=transport, base_url="https://export.arxiv.org")

    monkeypatch.setattr(
        "thesisagents.sources.arxiv.fetcher.get_client",
        fake_get_client,
    )


async def test_arxiv_fetcher_returns_papers(monkeypatch, fixture_xml):
    transport = _MockTransport(200, fixture_xml)
    await _install_mock(monkeypatch, transport)
    fetcher = ArxivFetcher()
    query = Query(keywords="attention", sources=("arxiv",), max_results=10)
    papers = await fetcher.search(query)
    assert len(papers) == 2
    assert papers[0].arxiv_id == "1706.03762"
    assert transport.received_url is not None
    assert "search_query=all%3Aattention" in str(transport.received_url)


async def test_arxiv_fetcher_filters_year_range(monkeypatch, fixture_xml):
    transport = _MockTransport(200, fixture_xml)
    await _install_mock(monkeypatch, transport)
    fetcher = ArxivFetcher()
    query = Query(
        keywords="attention", sources=("arxiv",), max_results=10,
        year_from=2020, year_to=2024,
    )
    papers = await fetcher.search(query)
    assert len(papers) == 1
    assert papers[0].arxiv_id == "2401.04088"


async def test_arxiv_fetcher_500_raises_unavailable(monkeypatch):
    transport = _MockTransport(503, "service down")
    await _install_mock(monkeypatch, transport)
    fetcher = ArxivFetcher()
    query = Query(keywords="x", sources=("arxiv",), max_results=5)
    with pytest.raises(SourceUnavailableError):
        await fetcher.search(query)


async def test_arxiv_fetcher_400_raises_parse_error(monkeypatch):
    transport = _MockTransport(400, "bad query")
    await _install_mock(monkeypatch, transport)
    fetcher = ArxivFetcher()
    query = Query(keywords="x", sources=("arxiv",), max_results=5)
    with pytest.raises(ParseError):
        await fetcher.search(query)


async def test_arxiv_fetcher_429_raises_rate_limit_error(monkeypatch):
    """arxiv 429 must route through RateLimitError so the pipeline's
    retry-with-backoff path picks it up instead of giving up immediately."""
    transport = _MockTransport(429, "Rate exceeded")
    await _install_mock(monkeypatch, transport)
    fetcher = ArxivFetcher()
    query = Query(keywords="x", sources=("arxiv",), max_results=5)
    with pytest.raises(RateLimitError):
        await fetcher.search(query)


async def test_arxiv_fetch_by_id_returns_paper(monkeypatch, arxiv_fixture_path):
    single_xml = (
        arxiv_fixture_path.parent / "single.xml"
    ).read_text(encoding="utf-8")
    transport = _MockTransport(200, single_xml)
    await _install_mock(monkeypatch, transport)
    fetcher = ArxivFetcher()
    paper = await fetcher.fetch_by_id("1706.03762")
    assert paper.arxiv_id == "1706.03762"
    assert paper.title == "Attention Is All You Need"
    assert paper.authors[0] == "Ashish Vaswani"
    assert "id_list=1706.03762" in str(transport.received_url)


async def test_arxiv_fetch_by_id_empty_raises(monkeypatch):
    empty_feed = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
    )
    transport = _MockTransport(200, empty_feed)
    await _install_mock(monkeypatch, transport)
    fetcher = ArxivFetcher()
    with pytest.raises(ParseError):
        await fetcher.fetch_by_id("9999.99999")
