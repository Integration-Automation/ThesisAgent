"""DBLP plugin tests against the recorded `llm_security.json` fixture."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from dblp.fetcher import DblpFetcher
from dblp.parser import in_year_range, parse_hit

from autopapertoppt.core.exceptions import ParseError, RateLimitError
from autopapertoppt.core.models import Query
from autopapertoppt.fetchers import http as http_module

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "dblp"
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

    monkeypatch.setattr("dblp.fetcher.get_client", fake_get_client)


async def test_search_returns_papers(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await DblpFetcher().search(
        Query(keywords="LLM Security", sources=("dblp",), max_results=10)
    )
    assert len(papers) == 3
    first = papers[0]
    assert first.source == "dblp"
    assert first.title.startswith("Adversarial Probes")
    assert first.title.endswith("Models")  # trailing dot stripped
    assert first.authors == ("Alice Andersson", "Bob Bertelsen")
    assert first.year == 2025
    assert first.venue == "IEEE Symposium on Security and Privacy"
    assert first.doi == "10.1109/SP.2025.0001"
    assert first.url == "https://doi.org/10.1109/SP.2025.0001"


async def test_search_year_filter_drops_old_papers(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await DblpFetcher().search(
        Query(
            keywords="LLM Security",
            sources=("dblp",),
            max_results=10,
            year_from=2025,
        )
    )
    # The 2018 entry must be filtered out.
    assert {p.year for p in papers} == {2025}
    assert len(papers) == 2


async def test_search_respects_max_results(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await DblpFetcher().search(
        Query(keywords="LLM Security", sources=("dblp",), max_results=1)
    )
    assert len(papers) == 1


async def test_search_passes_query_params(monkeypatch):
    transport = _CannedTransport(_FIXTURE_BYTES)
    _install(monkeypatch, transport)
    await DblpFetcher().search(
        Query(keywords="LLM Security", sources=("dblp",), max_results=5)
    )
    [request] = transport.requests
    assert request.url.params.get("format") == "json"
    assert request.url.params.get("q") == "LLM Security"
    assert int(request.url.params.get("h") or "0") >= 5


async def test_search_raises_on_rate_limit(monkeypatch):
    transport = _CannedTransport(b"", status=429)
    _install(monkeypatch, transport)
    with pytest.raises(RateLimitError):
        await DblpFetcher().search(
            Query(keywords="x", sources=("dblp",), max_results=1)
        )


async def test_search_treats_5xx_as_rate_limit(monkeypatch):
    """DBLP's FAQ notes 5xx is transient throttling — pipeline retry covers it."""
    transport = _CannedTransport(b"oops", status=503)
    _install(monkeypatch, transport)
    with pytest.raises(RateLimitError):
        await DblpFetcher().search(
            Query(keywords="x", sources=("dblp",), max_results=1)
        )


async def test_search_raises_on_bad_json(monkeypatch):
    transport = _CannedTransport(b"<html>not json</html>", status=200)
    _install(monkeypatch, transport)
    with pytest.raises(ParseError):
        await DblpFetcher().search(
            Query(keywords="x", sources=("dblp",), max_results=1)
        )


# ---------------------------------------------------------------------------
# Pure-parser tests (no HTTP)
# ---------------------------------------------------------------------------


def test_parse_hit_single_author_object():
    """DBLP returns a dict (not list) when there is exactly one author."""
    hit = {
        "@id": "x",
        "info": {
            "authors": {"author": {"text": "Lone Wolf"}},
            "title": "Solo Paper.",
            "year": "2024",
        },
    }
    assert parse_hit(hit).authors == ("Lone Wolf",)


def test_parse_hit_strips_trailing_period():
    hit = {"@id": "x", "info": {"title": "Trailing dot.", "year": "2024"}}
    assert parse_hit(hit).title == "Trailing dot"


def test_parse_hit_falls_back_to_doi_url_when_ee_missing():
    hit = {
        "@id": "x",
        "info": {"title": "Paper", "year": "2024", "doi": "10.1/abc"},
    }
    assert parse_hit(hit).url == "https://doi.org/10.1/abc"


def test_in_year_range_handles_none():
    assert in_year_range(2025, 2024, 2026) is True
    assert in_year_range(2023, 2024, 2026) is False
    assert in_year_range(2027, 2024, 2026) is False
    assert in_year_range(None, 2024, 2026) is False
    assert in_year_range(2025, None, None) is True
