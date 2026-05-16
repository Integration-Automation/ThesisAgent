"""PubMed plugin tests against recorded fixtures."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from pubmed.fetcher import PubMedFetcher

from autopapertoppt.core.exceptions import ParseError
from autopapertoppt.core.models import Query
from autopapertoppt.fetchers import http as http_module

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "pubmed"
_ESEARCH_JSON = (_FIXTURE_DIR / "esearch.json").read_text(encoding="utf-8")
_EFETCH_XML = (_FIXTURE_DIR / "efetch.xml").read_text(encoding="utf-8")


class _RouterTransport(httpx.AsyncBaseTransport):
    """Route requests by endpoint path so esearch returns JSON, efetch returns XML."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def handle_async_request(self, request):
        path = request.url.path
        self.calls.append(path)
        if path.endswith("esearch.fcgi"):
            return httpx.Response(200, content=_ESEARCH_JSON.encode(), request=request)
        if path.endswith("efetch.fcgi"):
            return httpx.Response(200, content=_EFETCH_XML.encode(), request=request)
        return httpx.Response(404, content=b"unrouted", request=request)

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

    monkeypatch.setattr("pubmed.fetcher.get_client", fake_get_client)


async def test_search_full_pipeline(monkeypatch):
    transport = _RouterTransport()
    _install(monkeypatch, transport)
    papers = await PubMedFetcher().search(
        Query(keywords="crispr", sources=("pubmed",), max_results=5)
    )
    assert len(papers) == 2
    assert papers[0].source_id == "34567890"
    assert papers[0].title.startswith("A CRISPR screen")
    assert "BACKGROUND: CRISPR" in papers[0].abstract
    assert papers[0].year == 2022
    assert papers[0].doi == "10.1038/s41587-022-01234-5"
    assert papers[0].authors[0] == "Alice Doe"
    assert papers[1].authors == ("Human Cell Atlas Consortium",)
    assert papers[1].year == 2023  # parsed from MedlineDate
    assert any(c.endswith("esearch.fcgi") for c in transport.calls)
    assert any(c.endswith("efetch.fcgi") for c in transport.calls)


async def test_search_empty_pmids_skips_efetch(monkeypatch):
    empty_json = '{"esearchresult": {"idlist": []}}'

    class _OnlyEsearch(httpx.AsyncBaseTransport):
        def __init__(self):
            self.calls = []

        async def handle_async_request(self, request):
            self.calls.append(request.url.path)
            return httpx.Response(200, content=empty_json.encode(), request=request)

        async def aclose(self):
            return None

    t = _OnlyEsearch()
    _install(monkeypatch, t)
    papers = await PubMedFetcher().search(
        Query(keywords="nothing", sources=("pubmed",), max_results=5)
    )
    assert papers == []
    assert all("esearch" in c for c in t.calls)


async def test_fetch_by_id(monkeypatch):
    class _Fetcher(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            return httpx.Response(200, content=_EFETCH_XML.encode(), request=request)

        async def aclose(self):
            return None

    _install(monkeypatch, _Fetcher())
    paper = await PubMedFetcher().fetch_by_id("34567890")
    assert paper.title.startswith("A CRISPR screen")


async def test_fetch_by_id_non_digit_raises(monkeypatch):
    _install(monkeypatch, _RouterTransport())
    with pytest.raises(ParseError):
        await PubMedFetcher().fetch_by_id("not-a-pmid")
