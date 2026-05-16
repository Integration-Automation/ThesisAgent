"""Tests for the search pipeline.

The high-leverage behaviour we want to lock in:

* sources whose plugin raises ``ConfigError`` at load time (e.g. an opt-in
  scraper without its env var) must be skipped without sinking the rest of
  the mix;
* a single source's ``FetchError`` does not poison sibling sources;
* a source's ``RateLimitError`` triggers retry-with-backoff before
  short-circuiting;
* the resulting collection still goes through dedup + rank + max truncation.
"""

from __future__ import annotations

import pytest

from autopapertoppt.core import pipeline as pipeline_module
from autopapertoppt.core.exceptions import ConfigError, FetchError, RateLimitError
from autopapertoppt.core.models import Paper, Query
from autopapertoppt.fetchers.base import Fetcher, FetcherConfig
from autopapertoppt.fetchers.rate_limit import RateLimit


@pytest.fixture(autouse=True)
def _fast_backoff(monkeypatch):
    """Replace asyncio.sleep inside the pipeline with a no-op so retry tests
    don't actually wait 5+10+20 seconds. Other tests are unaffected because
    they don't trip RateLimitError."""

    async def _instant(_seconds):
        return None

    monkeypatch.setattr(pipeline_module.asyncio, "sleep", _instant)


def _make_fetcher(name: str, papers: list[Paper] | None = None, *, fail: bool = False):
    rate = RateLimit(requests_per_second=100, burst=10, jitter_seconds=0)
    config = FetcherConfig(name=name, rate_limit=rate)
    delivered = papers or []

    class _Fake(Fetcher):
        def __init__(self) -> None:
            self.config = config
            super().__init__()

        async def search(self, query):  # noqa: ARG002 (mirror real signature)
            if fail:
                raise FetchError(name, "boom")
            return list(delivered)

    return _Fake()


def _make_flaky_fetcher(name: str, papers: list[Paper], *, fail_first_n: int):
    """Build a fetcher that raises RateLimitError for the first N calls and
    then returns ``papers``. Lets us drive the retry-with-backoff branch."""
    rate = RateLimit(requests_per_second=100, burst=10, jitter_seconds=0)
    config = FetcherConfig(name=name, rate_limit=rate)
    state = {"calls": 0}

    class _Flaky(Fetcher):
        def __init__(self) -> None:
            self.config = config
            super().__init__()

        async def search(self, query):  # noqa: ARG002
            state["calls"] += 1
            if state["calls"] <= fail_first_n:
                raise RateLimitError(name, "slow down")
            return list(papers)

    fetcher = _Flaky()
    fetcher.call_state = state
    return fetcher


def _paper(source: str, source_id: str, title: str) -> Paper:
    return Paper(
        source=source,
        source_id=source_id,
        title=title,
        authors=("Alice Author",),
        year=2025,
        venue=None,
        abstract="abstract",
        url=f"https://example.com/{source_id}",
    )


async def test_run_search_skips_disabled_source(monkeypatch):
    """A plugin that raises ConfigError at construction is skipped silently."""
    p_arxiv = _paper("arxiv", "1", "from arxiv")

    def fake_load(name: str):
        if name == "ieee":
            raise ConfigError("IEEE scraping disabled")
        return _make_fetcher(name, [p_arxiv])

    monkeypatch.setattr(pipeline_module, "load_fetcher", fake_load)
    query = Query(
        keywords="x",
        sources=("arxiv", "ieee"),
        max_results=10,
    )
    collection = await pipeline_module.run_search(query)
    assert len(collection.papers) == 1
    assert collection.papers[0].source == "arxiv"


async def test_run_search_tolerates_per_source_fetch_error(monkeypatch):
    """One source's FetchError must not kill the others."""
    good = _make_fetcher("arxiv", [_paper("arxiv", "1", "good")])
    bad = _make_fetcher("pubmed", fail=True)
    pool = {"arxiv": good, "pubmed": bad}
    monkeypatch.setattr(
        pipeline_module, "load_fetcher", lambda name: pool[name]
    )
    query = Query(keywords="x", sources=("arxiv", "pubmed"), max_results=5)
    collection = await pipeline_module.run_search(query)
    assert {p.source for p in collection.papers} == {"arxiv"}


async def test_run_search_merges_and_dedupes(monkeypatch):
    """Same paper coming from two sources should appear once."""
    dup_arxiv = Paper(
        source="arxiv",
        source_id="1",
        title="Same",
        authors=("Alice",),
        year=2025,
        venue=None,
        abstract="",
        url="https://example.com/a",
        doi="10.1234/same",
    )
    dup_pubmed = Paper(
        source="pubmed",
        source_id="2",
        title="Same",
        authors=("Alice",),
        year=2025,
        venue=None,
        abstract="",
        url="https://example.com/b",
        doi="10.1234/same",
    )
    pool = {
        "arxiv": _make_fetcher("arxiv", [dup_arxiv]),
        "pubmed": _make_fetcher("pubmed", [dup_pubmed]),
    }
    monkeypatch.setattr(
        pipeline_module, "load_fetcher", lambda name: pool[name]
    )
    query = Query(keywords="x", sources=("arxiv", "pubmed"), max_results=5)
    collection = await pipeline_module.run_search(query)
    assert len(collection.papers) == 1


def test_default_sources_constant_includes_arxiv_and_ieee():
    """Default mix advertises the breadth users now expect from a search."""
    from autopapertoppt.core.constants import DEFAULT_SOURCES

    assert "arxiv" in DEFAULT_SOURCES
    assert "ieee" in DEFAULT_SOURCES
    # At least one of the open-API fallbacks so a default install still works
    # when opt-in scrapers are off.
    assert {"semantic_scholar", "pubmed"} & set(DEFAULT_SOURCES)


async def test_run_search_top_tier_only_filters_results(monkeypatch):
    """top_tier_only=True drops papers whose venue isn't on the whitelist."""
    top_tier = Paper(
        source="openalex", source_id="t",
        title="Top paper", authors=("Top Author",), year=2025,
        venue="NeurIPS 2025", abstract="", url="https://example.com/t",
    )
    low_tier = Paper(
        source="openalex", source_id="l",
        title="Low paper", authors=("Low Author",), year=2025,
        venue="Some Random Conference", abstract="", url="https://example.com/l",
    )
    arxiv_pre = Paper(
        source="arxiv", source_id="a",
        title="Preprint", authors=("Preprint Author",), year=2025,
        venue=None, abstract="", url="https://arxiv.org/abs/2401.00001",
    )
    pool = {"openalex": _make_fetcher("openalex", [top_tier, low_tier]),
            "arxiv": _make_fetcher("arxiv", [arxiv_pre])}
    monkeypatch.setattr(
        pipeline_module, "load_fetcher", lambda name: pool[name]
    )
    query = Query(
        keywords="x",
        sources=("openalex", "arxiv"),
        max_results=10,
        top_tier_only=True,
    )
    collection = await pipeline_module.run_search(query)
    titles = {p.title for p in collection.papers}
    assert "Top paper" in titles
    assert "Preprint" in titles
    assert "Low paper" not in titles


async def test_rate_limit_retries_then_succeeds(monkeypatch):
    """First two attempts hit RateLimitError; third succeeds and papers flow."""
    paper = _paper("arxiv", "1", "from arxiv")
    flaky = _make_flaky_fetcher("arxiv", [paper], fail_first_n=2)
    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda _name: flaky)
    query = Query(keywords="x", sources=("arxiv",), max_results=5)
    collection = await pipeline_module.run_search(query)
    assert flaky.call_state["calls"] == 3
    assert len(collection.papers) == 1
    assert collection.papers[0].title == "from arxiv"


async def test_rate_limit_gives_up_after_max_attempts(monkeypatch):
    """If every retry hits RateLimitError, source is reported empty."""
    from autopapertoppt.core.constants import RATE_LIMIT_RETRY_ATTEMPTS

    flaky = _make_flaky_fetcher(
        "arxiv", [_paper("arxiv", "1", "x")],
        fail_first_n=RATE_LIMIT_RETRY_ATTEMPTS + 5,
    )
    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda _name: flaky)
    query = Query(keywords="x", sources=("arxiv",), max_results=5)
    collection = await pipeline_module.run_search(query)
    assert flaky.call_state["calls"] == RATE_LIMIT_RETRY_ATTEMPTS
    assert collection.papers == ()


async def test_non_rate_limit_fetch_error_does_not_retry(monkeypatch):
    """A non-rate-limit FetchError still short-circuits immediately."""
    state = {"calls": 0}

    rate = RateLimit(requests_per_second=100, burst=10, jitter_seconds=0)
    config = FetcherConfig(name="arxiv", rate_limit=rate)

    class _BadParse(Fetcher):
        def __init__(self):
            self.config = config
            super().__init__()

        async def search(self, _query):
            state["calls"] += 1
            raise FetchError("arxiv", "broken parse")

    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda _name: _BadParse())
    query = Query(keywords="x", sources=("arxiv",), max_results=5)
    collection = await pipeline_module.run_search(query)
    assert state["calls"] == 1
    assert collection.papers == ()


async def test_run_search_top_tier_only_default_false(monkeypatch):
    """Library callers see the historical no-filter behaviour by default."""
    low_tier = Paper(
        source="openalex", source_id="l",
        title="Low paper", authors=("Low Author",), year=2025,
        venue="Some Random Conference", abstract="", url="https://example.com/l",
    )
    pool = {"openalex": _make_fetcher("openalex", [low_tier])}
    monkeypatch.setattr(
        pipeline_module, "load_fetcher", lambda name: pool[name]
    )
    query = Query(keywords="x", sources=("openalex",), max_results=5)
    collection = await pipeline_module.run_search(query)
    assert len(collection.papers) == 1
    assert collection.papers[0].title == "Low paper"
