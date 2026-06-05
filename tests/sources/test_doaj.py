"""DOAJ plugin tests against the recorded `llm_security.json` fixture."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.sources._mock import MockTransport, install_mock
from thesisagents.core.exceptions import ParseError, RateLimitError
from thesisagents.core.models import Query
from thesisagents.sources.doaj.fetcher import DoajFetcher
from thesisagents.sources.doaj.parser import in_year_range, parse_result

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "doaj"
_FIXTURE_BYTES = (_FIXTURE_DIR / "llm_security.json").read_bytes()


def _install(monkeypatch, transport):
    install_mock(monkeypatch, "thesisagents.sources.doaj.fetcher", transport)


async def test_search_returns_papers(monkeypatch):
    transport = MockTransport(200, _FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await DoajFetcher().search(
        Query(keywords="LLM Security", sources=("doaj",), max_results=10)
    )
    assert len(papers) == 3
    first = papers[0]
    assert first.source == "doaj"
    assert first.title == "Open Defences Against Prompt Injection"
    assert first.authors == ("Andersson, Alice", "Bertelsen, Bob")
    assert first.year == 2025
    assert first.venue == "Journal of Open Security Research"
    assert first.doi == "10.5555/joa.2025.0001"
    assert first.url == "https://doaj.org/article/doaj0000001"
    assert first.pdf_url == "https://example.org/article/1.pdf"
    # DOAJ exposes no citation counts.
    assert first.citation_count is None


async def test_search_no_pdf_when_only_html_link(monkeypatch):
    transport = MockTransport(200, _FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await DoajFetcher().search(
        Query(keywords="LLM Security", sources=("doaj",), max_results=10)
    )
    assert papers[1].pdf_url is None


async def test_search_year_filter_drops_old_papers(monkeypatch):
    transport = MockTransport(200, _FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await DoajFetcher().search(
        Query(
            keywords="LLM Security",
            sources=("doaj",),
            max_results=10,
            year_from=2025,
        )
    )
    assert {p.year for p in papers} == {2025}
    assert len(papers) == 2


async def test_search_respects_max_results(monkeypatch):
    transport = MockTransport(200, _FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await DoajFetcher().search(
        Query(keywords="LLM Security", sources=("doaj",), max_results=1)
    )
    assert len(papers) == 1


async def test_search_encodes_query_in_path(monkeypatch):
    transport = MockTransport(200, _FIXTURE_BYTES)
    _install(monkeypatch, transport)
    await DoajFetcher().search(
        Query(keywords="a/b security", sources=("doaj",), max_results=5)
    )
    # The slash in the keyword must be percent-encoded into the path, not split.
    assert "a%2Fb" in str(transport.received_url)
    assert int(transport.received_url.params.get("pageSize") or "0") >= 5


async def test_search_raises_on_rate_limit(monkeypatch):
    transport = MockTransport(429, b"")
    _install(monkeypatch, transport)
    with pytest.raises(RateLimitError):
        await DoajFetcher().search(
            Query(keywords="x", sources=("doaj",), max_results=1)
        )


async def test_search_treats_5xx_as_rate_limit(monkeypatch):
    transport = MockTransport(502, b"oops")
    _install(monkeypatch, transport)
    with pytest.raises(RateLimitError):
        await DoajFetcher().search(
            Query(keywords="x", sources=("doaj",), max_results=1)
        )


async def test_search_raises_on_bad_json(monkeypatch):
    transport = MockTransport(200, b"<html>not json</html>")
    _install(monkeypatch, transport)
    with pytest.raises(ParseError):
        await DoajFetcher().search(
            Query(keywords="x", sources=("doaj",), max_results=1)
        )


# ---------------------------------------------------------------------------
# Pure-parser tests (no HTTP)
# ---------------------------------------------------------------------------


def test_parse_result_url_falls_back_to_doi_when_no_id():
    result = {
        "bibjson": {
            "title": "Paper",
            "identifier": [{"type": "doi", "id": "10.1/abc"}],
        }
    }
    assert parse_result(result).url == "https://doi.org/10.1/abc"


def test_parse_result_handles_missing_authors():
    result = {"id": "x", "bibjson": {"title": "Paper", "year": "2024"}}
    assert parse_result(result).authors == ()


def test_in_year_range_handles_none():
    assert in_year_range(2025, 2024, 2026) is True
    assert in_year_range(2023, 2024, 2026) is False
    assert in_year_range(None, 2024, 2026) is False
    assert in_year_range(None, None, None) is True
    assert in_year_range(2025, None, None) is True
