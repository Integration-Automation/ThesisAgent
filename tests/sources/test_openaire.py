"""OpenAIRE plugin tests against the recorded fixture."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from openaire.fetcher import OpenAireFetcher
from openaire.parser import parse_product

from autopapertoppt.core.exceptions import (
    ParseError,
    RateLimitError,
    SourceUnavailableError,
)
from autopapertoppt.core.models import Query
from autopapertoppt.fetchers import http as http_module

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "openaire"
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

    monkeypatch.setattr("openaire.fetcher.get_client", fake_get_client)


async def test_search_returns_papers(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await OpenAireFetcher().search(
        Query(keywords="LLM security", sources=("openaire",), max_results=10)
    )
    assert len(papers) == 2
    first = papers[0]
    assert first.source == "openaire"
    assert first.title.startswith("Detecting Prompt Injection")
    # OpenAIRE returns "Last, First"; parser normalises to "First Last".
    assert first.authors == ("Helena Garcia", "Ilya Ivanov")
    assert first.year == 2025
    assert first.venue == "Communications of the ACM"
    assert first.doi == "10.1145/3500000.3500001"
    # The OPEN instance has a .pdf URL — prefer it over the closed landing page.
    assert first.pdf_url == "https://arxiv.org/pdf/2503.01234.pdf"
    assert first.arxiv_id == "2503.01234"


async def test_search_year_filter_passes_to_api(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    await OpenAireFetcher().search(
        Query(
            keywords="x",
            sources=("openaire",),
            max_results=5,
            year_from=2025,
            year_to=2026,
        )
    )
    [request] = transport.requests
    assert request.url.params.get("fromPublicationDate") == "2025-01-01"
    assert request.url.params.get("toPublicationDate") == "2026-12-31"
    assert request.url.params.get("type") == "publication"
    assert request.url.params.get("sortBy") == "publicationDate DESC"


async def test_search_respects_max_results(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await OpenAireFetcher().search(
        Query(keywords="x", sources=("openaire",), max_results=1)
    )
    assert len(papers) == 1


async def test_search_raises_on_rate_limit(monkeypatch):
    transport = _CannedTransport(b"", status=429)
    _install(monkeypatch, transport)
    with pytest.raises(RateLimitError):
        await OpenAireFetcher().search(
            Query(keywords="x", sources=("openaire",), max_results=1)
        )


async def test_search_raises_on_server_error(monkeypatch):
    transport = _CannedTransport(b"oops", status=503)
    _install(monkeypatch, transport)
    with pytest.raises(SourceUnavailableError):
        await OpenAireFetcher().search(
            Query(keywords="x", sources=("openaire",), max_results=1)
        )


async def test_search_raises_on_bad_json(monkeypatch):
    transport = _CannedTransport(b"<html>", status=200)
    _install(monkeypatch, transport)
    with pytest.raises(ParseError):
        await OpenAireFetcher().search(
            Query(keywords="x", sources=("openaire",), max_results=1)
        )


# ---------------------------------------------------------------------------
# Pure-parser tests (no HTTP)
# ---------------------------------------------------------------------------


def test_parse_product_three_part_name_kept_as_is():
    """Names with multiple commas (suffixes) must not be mangled."""
    record = {
        "id": "x",
        "mainTitle": "T",
        "authors": [{"fullName": "Doe, John, Jr."}],
        "publicationDate": "2025",
    }
    assert parse_product(record).authors == ("Doe, John, Jr.",)


def test_parse_product_falls_back_to_doi_url():
    record = {
        "id": "x",
        "mainTitle": "T",
        "pids": [{"scheme": "doi", "value": "10.1/abc"}],
    }
    assert parse_product(record).url == "https://doi.org/10.1/abc"


def test_parse_product_pdf_url_priority():
    """OPEN .pdf wins over CLOSED landing wins over OPEN non-pdf."""
    record = {
        "id": "x",
        "mainTitle": "T",
        "instances": [
            {"accessRight": "CLOSED", "urls": ["https://closed.example/landing.pdf"]},
            {"accessRight": "OPEN", "urls": ["https://open.example/landing"]},
            {"accessRight": "OPEN", "urls": ["https://open.example/paper.pdf"]},
        ],
    }
    assert parse_product(record).pdf_url == "https://open.example/paper.pdf"


def test_parse_product_year_from_partial_date():
    record = {"id": "x", "mainTitle": "T", "publicationDate": "2025"}
    assert parse_product(record).year == 2025
