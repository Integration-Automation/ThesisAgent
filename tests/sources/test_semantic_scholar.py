"""Semantic Scholar plugin tests against recorded JSON fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.sources._mock import MockTransport, install_mock
from thesisagents.core.exceptions import ParseError, RateLimitError, SourceUnavailableError
from thesisagents.core.models import Query
from thesisagents.sources.semantic_scholar.fetcher import SemanticScholarFetcher

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "semantic_scholar"


def _fixture(name: str) -> str:
    return (_FIXTURE_DIR / name).read_text(encoding="utf-8")


async def test_search_returns_papers(monkeypatch):
    transport = MockTransport(200, _fixture("search.json"))
    install_mock(monkeypatch, "thesisagents.sources.semantic_scholar.fetcher", transport)
    papers = await SemanticScholarFetcher().search(
        Query(keywords="attention", sources=("semantic_scholar",), max_results=10)
    )
    assert len(papers) == 2
    assert papers[0].title == "Attention Is All You Need"
    assert papers[0].doi == "10.48550/arXiv.1706.03762"
    assert papers[0].arxiv_id == "1706.03762"
    assert papers[0].pdf_url == "https://arxiv.org/pdf/1706.03762"
    assert "query=attention" in str(transport.received_url)


async def test_search_passes_year_filter(monkeypatch):
    transport = MockTransport(200, '{"data": []}')
    install_mock(monkeypatch, "thesisagents.sources.semantic_scholar.fetcher", transport)
    await SemanticScholarFetcher().search(
        Query(
            keywords="x",
            sources=("semantic_scholar",),
            max_results=5,
            year_from=2020,
            year_to=2024,
        )
    )
    assert "year=2020-2024" in str(transport.received_url)


async def test_fetch_by_id_doi(monkeypatch):
    transport = MockTransport(200, _fixture("single.json"))
    install_mock(monkeypatch, "thesisagents.sources.semantic_scholar.fetcher", transport)
    paper = await SemanticScholarFetcher().fetch_by_id("10.48550/arXiv.1706.03762")
    assert paper.title == "Attention Is All You Need"
    assert "DOI:10.48550" in str(transport.received_url)


async def test_fetch_by_id_arxiv(monkeypatch):
    transport = MockTransport(200, _fixture("single.json"))
    install_mock(monkeypatch, "thesisagents.sources.semantic_scholar.fetcher", transport)
    await SemanticScholarFetcher().fetch_by_id("1706.03762")
    assert "ARXIV:1706.03762" in str(transport.received_url)


async def test_fetch_by_id_404_raises(monkeypatch):
    transport = MockTransport(404, '{"error":"not found"}')
    install_mock(monkeypatch, "thesisagents.sources.semantic_scholar.fetcher", transport)
    with pytest.raises(ParseError):
        await SemanticScholarFetcher().fetch_by_id("10.0/missing")


async def test_search_429_raises_rate_limit(monkeypatch):
    transport = MockTransport(429, "too many")
    install_mock(monkeypatch, "thesisagents.sources.semantic_scholar.fetcher", transport)
    with pytest.raises(RateLimitError):
        await SemanticScholarFetcher().search(
            Query(keywords="x", sources=("semantic_scholar",), max_results=1)
        )


async def test_search_5xx_raises_unavailable(monkeypatch):
    transport = MockTransport(503, "down")
    install_mock(monkeypatch, "thesisagents.sources.semantic_scholar.fetcher", transport)
    with pytest.raises(SourceUnavailableError):
        await SemanticScholarFetcher().search(
            Query(keywords="x", sources=("semantic_scholar",), max_results=1)
        )


async def test_api_key_sent_when_env_set(monkeypatch):
    monkeypatch.setenv("THESISAGENTS_S2_API_KEY", "secret-test-key")
    transport = MockTransport(200, '{"data": []}')
    install_mock(monkeypatch, "thesisagents.sources.semantic_scholar.fetcher", transport)

    # Patch the client to capture the headers we send.
    captured: dict[str, str] = {}
    original = transport.handle_async_request

    async def capturing(request):
        for key, value in request.headers.items():
            captured[key.lower()] = value
        return await original(request)

    transport.handle_async_request = capturing  # type: ignore[method-assign]
    await SemanticScholarFetcher().search(
        Query(keywords="x", sources=("semantic_scholar",), max_results=1)
    )
    assert captured.get("x-api-key") == "secret-test-key"
