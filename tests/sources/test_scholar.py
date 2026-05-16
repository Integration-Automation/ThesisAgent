"""Google Scholar plugin tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from autopapertoppt.core.exceptions import (
    ConfigError,
    ParseError,
    SourceUnavailableError,
)
from autopapertoppt.core.models import Query
from tests.sources._mock import MockTransport, install_mock

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "scholar"


def _fixture(name: str) -> str:
    return (_FIXTURE_DIR / name).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _enable_scholar(monkeypatch):
    monkeypatch.setenv("AUTOPAPERTOPPT_ENABLE_SCHOLAR_SCRAPING", "1")


def _new_fetcher():
    from scholar.fetcher import ScholarFetcher

    return ScholarFetcher()


async def test_opt_in_required(monkeypatch):
    monkeypatch.delenv("AUTOPAPERTOPPT_ENABLE_SCHOLAR_SCRAPING", raising=False)
    from scholar.fetcher import ScholarFetcher

    with pytest.raises(ConfigError):
        ScholarFetcher()


async def test_search_parses_serp(monkeypatch):
    transport = MockTransport(200, _fixture("serp.html"))
    install_mock(monkeypatch, "scholar.fetcher", transport)
    papers = await _new_fetcher().search(
        Query(keywords="attention", sources=("scholar",), max_results=10)
    )
    assert len(papers) == 2
    assert papers[0].title == "Attention Is All You Need"
    assert papers[0].url == "https://arxiv.org/abs/1706.03762"
    assert papers[0].year == 2017
    assert papers[0].citation_count == 100000
    assert papers[0].authors == ("A Vaswani", "N Shazeer", "N Parmar")


async def test_search_captcha_raises_unavailable(monkeypatch):
    transport = MockTransport(200, _fixture("captcha.html"))
    install_mock(monkeypatch, "scholar.fetcher", transport)
    with pytest.raises(SourceUnavailableError):
        await _new_fetcher().search(
            Query(keywords="x", sources=("scholar",), max_results=1)
        )


async def test_fetch_by_id_unsupported(monkeypatch):
    transport = MockTransport(200, "")
    install_mock(monkeypatch, "scholar.fetcher", transport)
    with pytest.raises(ParseError):
        await _new_fetcher().fetch_by_id("anything")


async def test_search_403_surfaces_unavailable(monkeypatch):
    transport = MockTransport(403, "Forbidden")
    install_mock(monkeypatch, "scholar.fetcher", transport)
    with pytest.raises(SourceUnavailableError):
        await _new_fetcher().search(
            Query(keywords="x", sources=("scholar",), max_results=1)
        )
