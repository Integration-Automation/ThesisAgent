"""OpenAlex plugin tests against the recorded `llm_security.json` fixture."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from openalex.fetcher import OpenAlexFetcher
from openalex.parser import _reconstruct_abstract, parse_work

from autopapertoppt.core.models import Query
from autopapertoppt.fetchers import http as http_module

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "openalex"
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
def _reset_clients():
    yield
    http_module._CLIENTS.clear()  # noqa: SLF001


def _install(monkeypatch, transport):
    http_module._CLIENTS.clear()  # noqa: SLF001

    async def fake_get_client(_source):
        return httpx.AsyncClient(transport=transport)

    monkeypatch.setattr("openalex.fetcher.get_client", fake_get_client)


async def test_search_returns_papers(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await OpenAlexFetcher().search(
        Query(
            keywords="LLM Security",
            sources=("openalex",),
            max_results=10,
            year_from=2025,
        )
    )
    assert len(papers) == 5
    first = papers[0]
    assert first.source == "openalex"
    assert first.title
    assert first.year == 2025
    assert first.authors
    # Open-access papers should carry a pdf_url.
    oa_with_pdf = [p for p in papers if p.pdf_url]
    assert len(oa_with_pdf) >= 1


async def test_search_includes_year_filter(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    await OpenAlexFetcher().search(
        Query(
            keywords="LLM Security",
            sources=("openalex",),
            max_results=5,
            year_from=2025,
            year_to=2026,
        )
    )
    [request] = transport.requests
    filter_param = request.url.params.get("filter") or ""
    assert "from_publication_date:2025-01-01" in filter_param
    assert "to_publication_date:2026-12-31" in filter_param


async def test_search_respects_max_results(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await OpenAlexFetcher().search(
        Query(
            keywords="LLM Security",
            sources=("openalex",),
            max_results=2,
        )
    )
    assert len(papers) == 2


async def test_search_attaches_mailto_when_env_set(monkeypatch):
    monkeypatch.setenv("AUTOPAPERTOPPT_CONTACT_EMAIL", "test@example.com")
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    await OpenAlexFetcher().search(
        Query(keywords="x", sources=("openalex",), max_results=1)
    )
    [request] = transport.requests
    assert request.url.params.get("mailto") == "test@example.com"


async def test_search_omits_mailto_when_env_unset(monkeypatch):
    monkeypatch.delenv("AUTOPAPERTOPPT_CONTACT_EMAIL", raising=False)
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    await OpenAlexFetcher().search(
        Query(keywords="x", sources=("openalex",), max_results=1)
    )
    [request] = transport.requests
    assert request.url.params.get("mailto") is None


# ---------------------------------------------------------------------------
# Pure-parser tests (no HTTP)
# ---------------------------------------------------------------------------


def test_reconstruct_abstract():
    inverted = {"hello": [0, 2], "world": [1]}
    assert _reconstruct_abstract(inverted) == "hello world hello"


def test_reconstruct_abstract_empty():
    assert _reconstruct_abstract({}) == ""


def test_parser_prefers_best_oa_pdf_url():
    record = {
        "id": "https://openalex.org/W1",
        "title": "X",
        "publication_year": 2025,
        "authorships": [{"author": {"display_name": "A"}}],
        "best_oa_location": {"pdf_url": "https://example.com/best.pdf"},
        "primary_location": {"pdf_url": "https://example.com/primary.pdf"},
        "open_access": {"oa_url": "https://example.com/landing"},
    }
    assert parse_work(record).pdf_url == "https://example.com/best.pdf"


def test_parser_falls_back_to_primary_pdf_url():
    record = {
        "id": "https://openalex.org/W1",
        "title": "X",
        "publication_year": 2025,
        "primary_location": {"pdf_url": "https://example.com/primary.pdf"},
        "open_access": {"oa_url": "https://example.com/landing"},
    }
    assert parse_work(record).pdf_url == "https://example.com/primary.pdf"


def test_parser_falls_back_to_oa_url():
    record = {
        "id": "https://openalex.org/W1",
        "title": "X",
        "publication_year": 2025,
        "open_access": {"oa_url": "https://example.com/landing"},
    }
    assert parse_work(record).pdf_url == "https://example.com/landing"


def test_parser_no_pdf_when_no_oa():
    record = {
        "id": "https://openalex.org/W1",
        "title": "X",
        "publication_year": 2025,
        "open_access": {"is_oa": False},
    }
    assert parse_work(record).pdf_url is None


def test_parser_strips_doi_prefix():
    record = {
        "id": "https://openalex.org/W1",
        "doi": "https://doi.org/10.1234/abc",
        "title": "X",
        "publication_year": 2025,
    }
    assert parse_work(record).doi == "10.1234/abc"


def test_parser_extracts_arxiv_id_from_ids():
    record = {
        "id": "https://openalex.org/W1",
        "title": "X",
        "publication_year": 2025,
        "ids": {"arxiv": "https://arxiv.org/abs/2401.08741"},
    }
    assert parse_work(record).arxiv_id == "2401.08741"


def test_parser_venue_from_primary_source():
    record = {
        "id": "https://openalex.org/W1",
        "title": "X",
        "publication_year": 2025,
        "primary_location": {"source": {"display_name": "NeurIPS"}},
    }
    assert parse_work(record).venue == "NeurIPS"
