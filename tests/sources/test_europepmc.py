"""Europe PMC plugin tests against the recorded `llm_security.json` fixture."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.sources._mock import MockTransport, install_mock
from thesisagents.core.exceptions import ParseError, RateLimitError
from thesisagents.core.models import Query
from thesisagents.sources.europepmc.fetcher import EuropePmcFetcher
from thesisagents.sources.europepmc.parser import in_year_range, parse_result

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "europepmc"
_FIXTURE_BYTES = (_FIXTURE_DIR / "llm_security.json").read_bytes()


def _install(monkeypatch, transport):
    install_mock(monkeypatch, "thesisagents.sources.europepmc.fetcher", transport)


async def test_search_returns_papers(monkeypatch):
    transport = MockTransport(200, _FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await EuropePmcFetcher().search(
        Query(keywords="LLM Security", sources=("europepmc",), max_results=10)
    )
    assert len(papers) == 3
    first = papers[0]
    assert first.source == "europepmc"
    assert first.title.startswith("Adversarial Probes")
    assert first.title.endswith("Models")  # trailing dot stripped
    assert first.authors == ("Alice Andersson", "Bob Bertelsen")
    assert first.year == 2025
    assert first.venue == "IEEE Symposium on Security and Privacy"
    assert first.doi == "10.1109/SP.2025.0001"
    assert first.url == "https://europepmc.org/article/MED/40000001"
    assert first.pdf_url == "https://europepmc.org/articles/PMC1/pdf"
    assert first.citation_count == 12


async def test_search_uses_author_string_fallback(monkeypatch):
    """The second record has no structured authorList — fall back to the
    flat authorString and drop its trailing period."""
    transport = MockTransport(200, _FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await EuropePmcFetcher().search(
        Query(keywords="LLM Security", sources=("europepmc",), max_results=10)
    )
    second = papers[1]
    assert second.authors == ("Chen C",)
    assert second.pdf_url is None


async def test_search_year_filter_drops_old_papers(monkeypatch):
    transport = MockTransport(200, _FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await EuropePmcFetcher().search(
        Query(
            keywords="LLM Security",
            sources=("europepmc",),
            max_results=10,
            year_from=2025,
        )
    )
    assert {p.year for p in papers} == {2025}
    assert len(papers) == 2


async def test_search_respects_max_results(monkeypatch):
    transport = MockTransport(200, _FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await EuropePmcFetcher().search(
        Query(keywords="LLM Security", sources=("europepmc",), max_results=1)
    )
    assert len(papers) == 1


async def test_search_passes_query_params(monkeypatch):
    transport = MockTransport(200, _FIXTURE_BYTES)
    _install(monkeypatch, transport)
    await EuropePmcFetcher().search(
        Query(keywords="LLM Security", sources=("europepmc",), max_results=5)
    )
    assert transport.received_url.params.get("format") == "json"
    assert transport.received_url.params.get("resultType") == "core"
    assert transport.received_url.params.get("query") == "LLM Security"
    assert int(transport.received_url.params.get("pageSize") or "0") >= 5


async def test_search_raises_on_rate_limit(monkeypatch):
    transport = MockTransport(429, b"")
    _install(monkeypatch, transport)
    with pytest.raises(RateLimitError):
        await EuropePmcFetcher().search(
            Query(keywords="x", sources=("europepmc",), max_results=1)
        )


async def test_search_treats_5xx_as_rate_limit(monkeypatch):
    transport = MockTransport(503, b"oops")
    _install(monkeypatch, transport)
    with pytest.raises(RateLimitError):
        await EuropePmcFetcher().search(
            Query(keywords="x", sources=("europepmc",), max_results=1)
        )


async def test_search_raises_on_bad_json(monkeypatch):
    transport = MockTransport(200, b"<html>not json</html>")
    _install(monkeypatch, transport)
    with pytest.raises(ParseError):
        await EuropePmcFetcher().search(
            Query(keywords="x", sources=("europepmc",), max_results=1)
        )


# ---------------------------------------------------------------------------
# Pure-parser tests (no HTTP)
# ---------------------------------------------------------------------------


def test_parse_result_prefers_structured_authors():
    result = {
        "id": "1",
        "source": "MED",
        "title": "Paper.",
        "authorString": "Smith J.",
        "authorList": {"author": [{"fullName": "Jane Smith"}]},
        "pubYear": "2024",
    }
    assert parse_result(result).authors == ("Jane Smith",)


def test_parse_result_pdf_selection_ignores_html():
    result = {
        "id": "1",
        "source": "MED",
        "title": "Paper",
        "fullTextUrlList": {
            "fullTextUrl": [
                {"documentStyle": "html", "url": "https://example.org/html"},
                {"documentStyle": "pdf", "url": "https://example.org/paper.pdf"},
            ]
        },
    }
    assert parse_result(result).pdf_url == "https://example.org/paper.pdf"


def test_parse_result_url_falls_back_to_doi():
    result = {"title": "Paper", "doi": "10.1/abc"}
    assert parse_result(result).url == "https://doi.org/10.1/abc"


def test_in_year_range_handles_none():
    assert in_year_range(2025, 2024, 2026) is True
    assert in_year_range(2023, 2024, 2026) is False
    assert in_year_range(2027, 2024, 2026) is False
    assert in_year_range(None, 2024, 2026) is False
    assert in_year_range(None, None, None) is True
    assert in_year_range(2025, None, None) is True
