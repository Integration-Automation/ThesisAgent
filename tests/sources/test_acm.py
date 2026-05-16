"""ACM/Crossref plugin tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from acm.fetcher import AcmFetcher

from autopapertoppt.core.exceptions import ParseError
from autopapertoppt.core.models import Query
from tests.sources._mock import MockTransport, install_mock

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "acm"


def _fixture(name: str) -> str:
    return (_FIXTURE_DIR / name).read_text(encoding="utf-8")


async def test_search_filters_to_acm(monkeypatch):
    transport = MockTransport(200, _fixture("crossref_search.json"))
    install_mock(monkeypatch, "acm.fetcher", transport)
    papers = await AcmFetcher().search(
        Query(keywords="inclusive AI", sources=("acm",), max_results=10)
    )
    # 3 records in fixture, but the Springer one is filtered out
    assert len(papers) == 2
    titles = [p.title for p in papers]
    assert "Designing Conversational AI for Older Adults" in titles
    assert "A Framework for Inclusive AI" in titles
    assert "Non-ACM record that slipped through filter" not in titles
    # Verify abstracts had jats:p tags stripped
    assert papers[0].abstract == "We design a conversational agent for older adults."
    assert papers[0].year == 2021
    assert papers[0].doi == "10.1145/3411764.3445005"
    assert papers[0].citation_count == 87
    # Direct PDF URL from Crossref's link[] (content-type application/pdf).
    assert (
        papers[0].pdf_url
        == "https://dl.acm.org/doi/pdf/10.1145/3411764.3445005"
    )
    # The second record has no link[] → pdf_url stays None.
    assert papers[1].pdf_url is None
    assert "member%3A320" in str(transport.received_url)


async def test_search_passes_year_filter(monkeypatch):
    transport = MockTransport(200, '{"message": {"items": []}}')
    install_mock(monkeypatch, "acm.fetcher", transport)
    await AcmFetcher().search(
        Query(
            keywords="x",
            sources=("acm",),
            max_results=5,
            year_from=2020,
            year_to=2024,
        )
    )
    url = str(transport.received_url)
    assert "from-pub-date%3A2020" in url
    assert "until-pub-date%3A2024" in url


async def test_fetch_by_doi(monkeypatch):
    transport = MockTransport(200, _fixture("crossref_single.json"))
    install_mock(monkeypatch, "acm.fetcher", transport)
    paper = await AcmFetcher().fetch_by_id("10.1145/3411764.3445005")
    assert paper.title == "Designing Conversational AI for Older Adults"
    assert paper.year == 2021
    assert paper.authors == ("Alice Anderson", "Bob Brown")


async def test_fetch_non_doi_raises(monkeypatch):
    transport = MockTransport(200, "{}")
    install_mock(monkeypatch, "acm.fetcher", transport)
    with pytest.raises(ParseError):
        await AcmFetcher().fetch_by_id("not-a-doi")


async def test_fetch_404_raises(monkeypatch):
    transport = MockTransport(404, "missing")
    install_mock(monkeypatch, "acm.fetcher", transport)
    with pytest.raises(ParseError):
        await AcmFetcher().fetch_by_id("10.1/missing")


async def test_mailto_sent_when_env_set(monkeypatch):
    monkeypatch.setenv("AUTOPAPERTOPPT_CONTACT_EMAIL", "polite@example.org")
    transport = MockTransport(200, '{"message": {"items": []}}')
    install_mock(monkeypatch, "acm.fetcher", transport)
    await AcmFetcher().search(
        Query(keywords="x", sources=("acm",), max_results=1)
    )
    assert "mailto=polite%40example.org" in str(transport.received_url)


async def test_crossref_plus_token_attached_when_env_set(monkeypatch):
    """``AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN`` must turn into a
    ``Crossref-Plus-API-Token: Bearer …`` header on every request."""
    import httpx

    monkeypatch.setenv("AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN", "plus-secret")
    captured: dict[str, str] = {}

    class _CaptureTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            for k, v in request.headers.items():
                captured[k.lower()] = v
            return httpx.Response(
                200, content=b'{"message": {"items": []}}', request=request
            )

        async def aclose(self):
            return None

    install_mock(monkeypatch, "acm.fetcher", _CaptureTransport())
    await AcmFetcher().search(
        Query(keywords="x", sources=("acm",), max_results=1)
    )
    assert captured.get("crossref-plus-api-token") == "Bearer plus-secret"


async def test_crossref_plus_token_absent_when_env_unset(monkeypatch):
    import httpx

    monkeypatch.delenv("AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN", raising=False)
    captured: dict[str, str] = {}

    class _CaptureTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            for k, v in request.headers.items():
                captured[k.lower()] = v
            return httpx.Response(
                200, content=b'{"message": {"items": []}}', request=request
            )

        async def aclose(self):
            return None

    install_mock(monkeypatch, "acm.fetcher", _CaptureTransport())
    await AcmFetcher().search(
        Query(keywords="x", sources=("acm",), max_results=1)
    )
    assert "crossref-plus-api-token" not in captured
