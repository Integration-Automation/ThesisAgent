"""Crossref (direct) plugin tests against the recorded fixture."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from crossref.fetcher import CrossrefFetcher
from crossref.parser import parse_record

from autopapertoppt.core.exceptions import (
    ParseError,
    RateLimitError,
    SourceUnavailableError,
)
from autopapertoppt.core.models import Query
from autopapertoppt.fetchers import http as http_module

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "crossref"
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

    monkeypatch.setattr("crossref.fetcher.get_client", fake_get_client)


async def test_search_returns_papers(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await CrossrefFetcher().search(
        Query(keywords="LLM security", sources=("crossref",), max_results=10)
    )
    assert len(papers) == 2
    first = papers[0]
    assert first.source == "crossref"
    assert first.title.startswith("Robustness Evaluation")
    assert first.authors == ("Dana Doe", "Eli Edwards")
    assert first.year == 2025
    assert first.venue == "Nature Machine Intelligence"
    assert first.doi == "10.1038/s41586-025-00001-x"
    assert "<jats:" not in (first.abstract or "")
    assert first.citation_count == 7
    # Direct PDF URL must be lifted from link[] (content-type application/pdf).
    assert first.pdf_url == "https://www.nature.com/articles/s41586-025-00001-x.pdf"


async def test_search_includes_year_filter(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    await CrossrefFetcher().search(
        Query(
            keywords="x",
            sources=("crossref",),
            max_results=5,
            year_from=2025,
            year_to=2026,
        )
    )
    [request] = transport.requests
    filter_param = request.url.params.get("filter") or ""
    assert "from-pub-date:2025" in filter_param
    assert "until-pub-date:2026" in filter_param


async def test_search_respects_max_results(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await CrossrefFetcher().search(
        Query(keywords="x", sources=("crossref",), max_results=1)
    )
    assert len(papers) == 1


async def test_search_attaches_mailto_when_env_set(monkeypatch):
    monkeypatch.setenv("AUTOPAPERTOPPT_CONTACT_EMAIL", "test@example.com")
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    await CrossrefFetcher().search(
        Query(keywords="x", sources=("crossref",), max_results=1)
    )
    [request] = transport.requests
    assert request.url.params.get("mailto") == "test@example.com"


async def test_search_attaches_plus_token_header(monkeypatch):
    monkeypatch.setenv("AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN", "secret-plus-token")
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    await CrossrefFetcher().search(
        Query(keywords="x", sources=("crossref",), max_results=1)
    )
    [request] = transport.requests
    assert request.headers.get("Crossref-Plus-API-Token") == "Bearer secret-plus-token"


async def test_search_raises_on_rate_limit(monkeypatch):
    transport = _CannedTransport(b"", status=429)
    _install(monkeypatch, transport)
    with pytest.raises(RateLimitError):
        await CrossrefFetcher().search(
            Query(keywords="x", sources=("crossref",), max_results=1)
        )


async def test_search_raises_on_server_error(monkeypatch):
    transport = _CannedTransport(b"oops", status=503)
    _install(monkeypatch, transport)
    with pytest.raises(SourceUnavailableError):
        await CrossrefFetcher().search(
            Query(keywords="x", sources=("crossref",), max_results=1)
        )


async def test_fetch_by_id_rejects_non_doi():
    with pytest.raises(ParseError):
        await CrossrefFetcher().fetch_by_id("not-a-doi")


# ---------------------------------------------------------------------------
# Pure-parser tests (no HTTP)
# ---------------------------------------------------------------------------


def test_parse_record_strips_html_abstract():
    record = {
        "DOI": "10.1/x",
        "title": ["Sample"],
        "abstract": "<jats:p>Hello <b>world</b>.</jats:p>",
        "issued": {"date-parts": [[2025]]},
    }
    paper = parse_record(record)
    assert paper.abstract == "Hello world."
    assert paper.doi == "10.1/x"
    assert paper.year == 2025


def test_parse_record_uses_published_print_first():
    record = {
        "DOI": "10.1/x",
        "title": ["Sample"],
        "published-print": {"date-parts": [[2024]]},
        "published-online": {"date-parts": [[2023]]},
        "issued": {"date-parts": [[2022]]},
    }
    assert parse_record(record).year == 2024


def test_parse_record_url_fallback_to_doi():
    record = {"DOI": "10.1/x", "title": ["Sample"]}
    assert parse_record(record).url == "https://doi.org/10.1/x"
