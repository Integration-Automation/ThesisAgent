"""HAL plugin tests against the recorded `llm_security.json` fixture."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.sources._mock import MockTransport, install_mock
from thesisagents.core.exceptions import ParseError, RateLimitError
from thesisagents.core.models import Query
from thesisagents.sources.hal.fetcher import HalFetcher
from thesisagents.sources.hal.parser import in_year_range, parse_doc

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "hal"
_FIXTURE_BYTES = (_FIXTURE_DIR / "llm_security.json").read_bytes()


def _install(monkeypatch, transport):
    install_mock(monkeypatch, "thesisagents.sources.hal.fetcher", transport)


async def test_search_returns_papers(monkeypatch):
    transport = MockTransport(200, _FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await HalFetcher().search(
        Query(keywords="LLM Security", sources=("hal",), max_results=10)
    )
    assert len(papers) == 3
    first = papers[0]
    assert first.source == "hal"
    assert first.title == "Formal Verification of LLM Guardrails"
    assert first.authors == ("Alice Andersson", "Bob Bertelsen")
    assert first.year == 2025
    assert first.venue == "Journal of Formal Methods"
    assert first.doi == "10.1234/hal.2025.0001"
    assert first.url == "https://hal.science/hal-4000001"
    assert first.pdf_url == "https://hal.science/hal-4000001/document"


async def test_search_handles_missing_optional_fields(monkeypatch):
    """The second doc has no journal, doi or PDF — those become None."""
    transport = MockTransport(200, _FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await HalFetcher().search(
        Query(keywords="LLM Security", sources=("hal",), max_results=10)
    )
    second = papers[1]
    assert second.venue is None
    assert second.doi is None
    assert second.pdf_url is None


async def test_search_year_filter_drops_old_papers(monkeypatch):
    transport = MockTransport(200, _FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await HalFetcher().search(
        Query(
            keywords="LLM Security",
            sources=("hal",),
            max_results=10,
            year_from=2025,
        )
    )
    assert {p.year for p in papers} == {2025}
    assert len(papers) == 2


async def test_search_respects_max_results(monkeypatch):
    transport = MockTransport(200, _FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await HalFetcher().search(
        Query(keywords="LLM Security", sources=("hal",), max_results=1)
    )
    assert len(papers) == 1


async def test_search_requests_metadata_fields(monkeypatch):
    transport = MockTransport(200, _FIXTURE_BYTES)
    _install(monkeypatch, transport)
    await HalFetcher().search(
        Query(keywords="LLM Security", sources=("hal",), max_results=5)
    )
    assert transport.received_url.params.get("wt") == "json"
    assert transport.received_url.params.get("q") == "LLM Security"
    # Field list must be requested or HAL returns only docid + label_s.
    fl = transport.received_url.params.get("fl") or ""
    assert "title_s" in fl
    assert "authFullName_s" in fl
    assert int(transport.received_url.params.get("rows") or "0") >= 5


async def test_search_raises_on_rate_limit(monkeypatch):
    transport = MockTransport(429, b"")
    _install(monkeypatch, transport)
    with pytest.raises(RateLimitError):
        await HalFetcher().search(
            Query(keywords="x", sources=("hal",), max_results=1)
        )


async def test_search_treats_5xx_as_rate_limit(monkeypatch):
    transport = MockTransport(503, b"oops")
    _install(monkeypatch, transport)
    with pytest.raises(RateLimitError):
        await HalFetcher().search(
            Query(keywords="x", sources=("hal",), max_results=1)
        )


async def test_search_raises_on_bad_json(monkeypatch):
    transport = MockTransport(200, b"<html>not json</html>")
    _install(monkeypatch, transport)
    with pytest.raises(ParseError):
        await HalFetcher().search(
            Query(keywords="x", sources=("hal",), max_results=1)
        )


# ---------------------------------------------------------------------------
# Pure-parser tests (no HTTP)
# ---------------------------------------------------------------------------


def test_parse_doc_unwraps_array_fields():
    doc = {
        "docid": "1",
        "title_s": ["Solo Title"],
        "authFullName_s": ["Lone Wolf"],
        "producedDateY_i": 2024,
        "abstract_s": ["Body"],
        "uri_s": "https://hal.science/hal-1",
    }
    paper = parse_doc(doc)
    assert paper.title == "Solo Title"
    assert paper.authors == ("Lone Wolf",)
    assert paper.abstract == "Body"


def test_parse_doc_falls_back_to_doi_url():
    doc = {"docid": "1", "title_s": ["T"], "doiId_s": "10.1/abc"}
    assert parse_doc(doc).url == "https://doi.org/10.1/abc"


def test_in_year_range_handles_none():
    assert in_year_range(2025, 2024, 2026) is True
    assert in_year_range(2023, 2024, 2026) is False
    assert in_year_range(None, 2024, 2026) is False
    assert in_year_range(None, None, None) is True
    assert in_year_range(2025, None, None) is True
