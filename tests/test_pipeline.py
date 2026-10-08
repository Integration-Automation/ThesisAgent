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

from thesisagents.core import pipeline as pipeline_module
from thesisagents.core.exceptions import ConfigError, FetchError, RateLimitError
from thesisagents.core.models import Paper, Query
from thesisagents.fetchers.base import Fetcher, FetcherConfig
from thesisagents.fetchers.rate_limit import RateLimit


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


async def test_run_search_tolerates_unexpected_source_exception(monkeypatch):
    """A non-FetchError escaping a plugin must not sink the whole search.

    Source plugins normalise the failures they anticipate into ``FetchError``,
    but an upstream schema change surfaces in the parser as a plain
    ``KeyError`` / ``AttributeError``. Because ``asyncio.gather`` propagates the
    first exception, such a bug used to discard the results every other source
    had already returned — a whole multi-minute search lost to one publisher
    renaming a JSON field.
    """
    rate = RateLimit(requests_per_second=100, burst=10, jitter_seconds=0)

    class _Exploding(Fetcher):
        def __init__(self) -> None:
            self.config = FetcherConfig(name="openalex", rate_limit=rate)
            super().__init__()

        async def search(self, query):  # noqa: ARG002 (mirror real signature)
            raise KeyError("best_oa_location")

    pool = {
        "arxiv": _make_fetcher("arxiv", [_paper("arxiv", "1", "survivor")]),
        "openalex": _Exploding(),
    }
    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda name: pool[name])
    query = Query(keywords="x", sources=("arxiv", "openalex"), max_results=5)
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
    from thesisagents.core.constants import DEFAULT_SOURCES

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
    from thesisagents.core.constants import RATE_LIMIT_RETRY_ATTEMPTS

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


async def test_run_search_min_citations_filters_all_sources(monkeypatch):
    """min_citations is enforced in the pipeline for every source (not only
    semantic_scholar). Papers with an unknown (None) citation count are kept."""
    def _cited(source_id, count):
        return Paper(
            source="arxiv", source_id=source_id, title=source_id, authors=(),
            year=2024, venue=None, abstract="",
            url=f"https://example.com/{source_id}", citation_count=count,
        )

    high = _cited("high", 100)
    low = _cited("low", 5)
    unknown = _cited("unknown", None)
    pool = {"arxiv": _make_fetcher("arxiv", [high, low, unknown])}
    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda name: pool[name])
    query = Query(
        keywords="x", sources=("arxiv",), max_results=10, min_citations=50
    )
    collection = await pipeline_module.run_search(query, resolve_oa=False)
    ids = {p.source_id for p in collection.papers}
    assert "high" in ids          # 100 >= 50
    assert "unknown" in ids        # unknown count kept, not dropped
    assert "low" not in ids        # 5 < 50 filtered out


async def test_run_search_year_range_pipeline_guard(monkeypatch):
    """The pipeline enforces the year range even when a source returns
    out-of-range papers (scrape sources filter loosely); unknown years kept."""
    def _yr(sid, year):
        return Paper(
            source="arxiv", source_id=sid, title=sid, authors=(), year=year,
            venue=None, abstract="", url=f"https://example.com/{sid}",
        )

    in_range = _yr("in", 2022)
    too_old = _yr("old", 2010)
    too_new = _yr("new", 2025)
    unknown = _yr("unk", None)
    pool = {"arxiv": _make_fetcher("arxiv", [in_range, too_old, too_new, unknown])}
    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda name: pool[name])
    query = Query(
        keywords="x", sources=("arxiv",), max_results=10,
        year_from=2020, year_to=2024,
    )
    collection = await pipeline_module.run_search(query, resolve_oa=False)
    ids = {p.source_id for p in collection.papers}
    assert ids == {"in", "unk"}  # in-range + unknown kept; old/new dropped


async def test_enrich_collection_caps_concurrency(monkeypatch):
    """A semaphore bounds how many per-paper enrichments run at once, so a big
    collection doesn't fire one Anthropic call + one PDF download per paper."""
    import asyncio

    from thesisagents.core.models import PaperCollection

    # dict (not nonlocal ints) so the counter mutation is visible to static
    # analysers that don't trace the monkeypatched async call path.
    counters = {"active": 0, "peak": 0}

    async def fake_enrich_one(paper, *, language, model):
        counters["active"] += 1
        counters["peak"] = max(counters["peak"], counters["active"])
        await asyncio.sleep(0.01)
        counters["active"] -= 1
        return paper

    monkeypatch.setattr(pipeline_module, "_enrich_one", fake_enrich_one)
    papers = tuple(_paper("arxiv", str(i), f"t{i}") for i in range(8))
    collection = PaperCollection(
        query=Query(keywords="x", sources=("arxiv",), max_results=8),
        papers=papers,
    )
    out = await pipeline_module.enrich_collection(collection, concurrency=3)
    assert len(out.papers) == 8
    assert 1 <= counters["peak"] <= 3  # never more than the cap in flight at once


# ---------------------------------------------------------------------------
# Diagnostics: the score behind each position + advisory pruning
# ---------------------------------------------------------------------------


def _scored_paper(sid: str, title: str, *, year: int = 2025, citations=None, venue=None):
    return Paper(
        source="arxiv", source_id=sid, title=title, authors=("Ada Author",),
        year=year, venue=venue, abstract="", url=f"https://example.com/{sid}",
        citation_count=citations,
    )


async def test_run_search_attaches_a_score_and_advice_per_paper(monkeypatch):
    on_topic = _scored_paper("on", "Transformer Attention Explained")
    off_topic = _scored_paper("off", "Cooking With Gas")
    pool = {"arxiv": _make_fetcher("arxiv", [off_topic, on_topic])}
    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda name: pool[name])
    query = Query(keywords="transformer attention", sources=("arxiv",), max_results=10)

    collection = await pipeline_module.run_search(query, resolve_oa=False)

    diagnostics = collection.diagnostics
    assert [p.source_id for p in collection.papers] == ["on", "off"]
    assert [s.paper_key for s in diagnostics.scores] == [
        p.dedup_key() for p in collection.papers
    ]
    assert [s.rank for s in diagnostics.scores] == [1, 2]
    assert diagnostics.scores[0].score.matched_terms == ("transformer", "attention")
    assert [a.action.value for a in diagnostics.pruning] == ["keep", "prune"]


async def test_pruning_advice_never_removes_a_paper(monkeypatch):
    """Advisory by design: a paper recommended for pruning is still returned."""
    papers = [_scored_paper(str(i), f"Cooking With Gas Volume {i}") for i in range(4)]
    pool = {"arxiv": _make_fetcher("arxiv", papers)}
    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda name: pool[name])
    query = Query(keywords="transformer attention", sources=("arxiv",), max_results=10)

    collection = await pipeline_module.run_search(query, resolve_oa=False)

    assert len(collection.papers) == 4
    assert {a.action.value for a in collection.diagnostics.pruning} == {"prune"}


async def test_diagnostic_ranks_are_renumbered_after_filters_and_the_cut(monkeypatch):
    """A filter can remove the papers that held ranks 1 and 2. The recorded
    ranks must match the positions in the collection the caller receives."""
    papers = [
        _scored_paper("a", "Transformer Attention One", citations=1),
        _scored_paper("b", "Transformer Attention Two", citations=2),
        _scored_paper("c", "Transformer Attention Three", citations=300),
        _scored_paper("d", "Transformer Attention Four", citations=400),
        _scored_paper("e", "Transformer Attention Five", citations=500),
    ]
    pool = {"arxiv": _make_fetcher("arxiv", papers)}
    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda name: pool[name])
    query = Query(
        keywords="transformer attention", sources=("arxiv",), max_results=2,
        min_citations=100,
    )

    collection = await pipeline_module.run_search(query, resolve_oa=False)

    assert [p.source_id for p in collection.papers] == ["e", "d"]
    assert [s.rank for s in collection.diagnostics.scores] == [1, 2]
    assert [a.rank for a in collection.diagnostics.pruning] == [1, 2]
    assert len(collection.diagnostics.scores) == len(collection.papers)


async def test_diagnostics_survive_oa_resolution_and_enrichment(monkeypatch):
    """Both stages rebuild the collection. The explanation must come along,
    and still find its paper after ``pdf_url`` / ``summary`` were filled in."""
    import dataclasses

    paper = _scored_paper("p", "Transformer Attention Explained")
    pool = {"arxiv": _make_fetcher("arxiv", [paper])}
    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda name: pool[name])

    async def fake_enrich_one(paper, *, language, model):
        return dataclasses.replace(paper, pdf_url="https://example.com/p.pdf")

    monkeypatch.setattr(pipeline_module, "_enrich_one", fake_enrich_one)
    query = Query(keywords="transformer attention", sources=("arxiv",), max_results=5)

    searched = await pipeline_module.run_search(query)  # resolve_oa=True, network refused
    enriched = await pipeline_module.enrich_collection(searched)

    assert searched.diagnostics is not None
    assert enriched.diagnostics is searched.diagnostics
    key = enriched.papers[0].dedup_key()
    assert enriched.diagnostics.score_for(key) is not None
    assert enriched.diagnostics.recommendation_for(key).action.value == "keep"


async def test_an_empty_search_still_carries_empty_diagnostics(monkeypatch):
    pool = {"arxiv": _make_fetcher("arxiv", [])}
    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda name: pool[name])
    query = Query(keywords="x", sources=("arxiv",), max_results=5)

    collection = await pipeline_module.run_search(query, resolve_oa=False)

    assert collection.papers == ()
    assert collection.diagnostics.scores == ()
    assert collection.diagnostics.pruning == ()


def test_collection_equality_ignores_diagnostics():
    """Two collections holding the same papers are the same result, however
    they were explained. Tests and callers compare collections freely."""
    from thesisagents.core.diagnostics import SearchDiagnostics
    from thesisagents.core.models import PaperCollection

    query = Query(keywords="x", sources=("arxiv",), max_results=5)
    papers = (_scored_paper("p", "Title"),)

    plain = PaperCollection(query=query, papers=papers)
    explained = PaperCollection(query=query, papers=papers, diagnostics=SearchDiagnostics())

    assert plain.diagnostics is None
    assert plain == explained


def test_collection_report_joins_scores_to_papers():
    from thesisagents.core.diagnostics import collection_report
    from thesisagents.core.models import PaperCollection
    from thesisagents.core.ranking import rank_with_scores

    papers = [
        _scored_paper("on", "Transformer Attention Explained"),
        _scored_paper("off", "Cooking With Gas"),
    ]
    ranked = rank_with_scores(papers, "transformer attention", current_year=2026)
    query = Query(keywords="transformer attention", sources=("arxiv",), max_results=5)
    collection = PaperCollection(
        query=query,
        papers=tuple(e.paper for e in ranked),
        diagnostics=pipeline_module._diagnose(ranked),  # noqa: SLF001
    )

    report = collection_report(collection)

    assert report["keywords"] == "transformer attention"
    assert report["advisory"] is True
    assert report["summary"] == {"keep": 1, "review": 0, "prune": 1}
    first, second = report["papers"]
    assert first["rank"] == 1
    assert first["bibtex_key"] == papers[0].bibtex_key()
    assert first["paper_key"] == papers[0].dedup_key()
    assert first["score"]["matched_terms"] == ["transformer", "attention"]
    assert first["recommendation"] == {
        "action": "keep", "threshold": "",
        "reasons": ["relevance is 87% of the best this query allows"],
    }
    assert second["recommendation"]["action"] == "prune"
    assert second["recommendation"]["threshold"] == "prune_below_relevance=0.10"


def test_collection_report_lists_papers_that_have_no_score():
    from thesisagents.core.diagnostics import collection_report
    from thesisagents.core.models import PaperCollection

    query = Query(keywords="x", sources=("arxiv",), max_results=5)
    collection = PaperCollection(query=query, papers=(_scored_paper("p", "Title"),))

    report = collection_report(collection)

    assert report["summary"] == {"keep": 0, "review": 0, "prune": 0}
    assert report["papers"][0]["score"] is None
    assert report["papers"][0]["recommendation"] is None
    assert report["papers"][0]["title"] == "Title"


# ---------------------------------------------------------------------------
# Per-source statistics
# ---------------------------------------------------------------------------


def _stats(collection) -> dict[str, dict]:
    return {stat.source: stat.to_dict() for stat in collection.diagnostics.source_stats}


async def test_one_source_reports_what_it_returned(monkeypatch):
    papers = [_scored_paper(str(i), f"Distinct Title Number {i}") for i in range(4)]
    pool = {"arxiv": _make_fetcher("arxiv", papers)}
    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda name: pool[name])
    query = Query(keywords="x", sources=("arxiv",), max_results=25)

    collection = await pipeline_module.run_search(query, resolve_oa=False)

    assert _stats(collection) == {
        "arxiv": {
            "source": "arxiv", "requested": 25, "returned": 4, "after_dedup": 4,
            "status": "ok", "detail": "",
        }
    }


async def test_a_failed_source_reports_zero_and_a_failure_status(monkeypatch):
    pool = {
        "arxiv": _make_fetcher("arxiv", [_paper("arxiv", "1", "survivor")]),
        "pubmed": _make_fetcher("pubmed", fail=True),
    }
    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda name: pool[name])
    query = Query(keywords="x", sources=("arxiv", "pubmed"), max_results=5)

    collection = await pipeline_module.run_search(query, resolve_oa=False)

    stats = _stats(collection)
    assert stats["pubmed"]["status"] == "failed"
    assert stats["pubmed"]["returned"] == 0
    assert stats["pubmed"]["after_dedup"] == 0
    assert stats["pubmed"]["detail"] == "[pubmed] boom"
    assert stats["arxiv"]["status"] == "ok"
    assert stats["arxiv"]["returned"] == 1
    assert len(collection.papers) == 1  # the failure did not stop the search


async def test_an_unexpected_exception_is_reported_with_its_type(monkeypatch):
    rate = RateLimit(requests_per_second=100, burst=10, jitter_seconds=0)

    class _Exploding(Fetcher):
        def __init__(self) -> None:
            self.config = FetcherConfig(name="openalex", rate_limit=rate)
            super().__init__()

        async def search(self, query):  # noqa: ARG002 (mirror real signature)
            raise KeyError("best_oa_location")

    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda _name: _Exploding())
    query = Query(keywords="x", sources=("openalex",), max_results=5)

    collection = await pipeline_module.run_search(query, resolve_oa=False)

    stat = _stats(collection)["openalex"]
    assert stat["status"] == "failed"
    assert stat["detail"] == "KeyError: 'best_oa_location'"


async def test_a_disabled_source_is_listed_with_the_reason(monkeypatch):
    def fake_load(name: str):
        if name == "springer":
            raise ConfigError("THESISAGENTS_SPRINGER_API_KEY is not set")
        return _make_fetcher(name, [_paper(name, "1", "from arxiv")])

    monkeypatch.setattr(pipeline_module, "load_fetcher", fake_load)
    query = Query(keywords="x", sources=("springer", "arxiv"), max_results=10)

    collection = await pipeline_module.run_search(query, resolve_oa=False)

    stats = collection.diagnostics.source_stats
    assert [stat.source for stat in stats] == ["springer", "arxiv"]  # query order
    assert stats[0].status.value == "disabled"
    assert stats[0].detail == "THESISAGENTS_SPRINGER_API_KEY is not set"
    assert stats[0].requested == 10
    assert stats[0].returned == 0
    assert stats[1].returned == 1


async def test_a_rate_limited_source_is_reported_as_such(monkeypatch):
    from thesisagents.core.constants import RATE_LIMIT_RETRY_ATTEMPTS

    flaky = _make_flaky_fetcher(
        "semantic_scholar", [_paper("semantic_scholar", "1", "x")],
        fail_first_n=RATE_LIMIT_RETRY_ATTEMPTS + 5,
    )
    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda _name: flaky)
    query = Query(keywords="x", sources=("semantic_scholar",), max_results=5)

    collection = await pipeline_module.run_search(query, resolve_oa=False)

    stat = _stats(collection)["semantic_scholar"]
    assert stat["status"] == "rate_limited"
    assert stat["returned"] == 0
    assert f"gave up after {RATE_LIMIT_RETRY_ATTEMPTS} rate-limit retries" in stat["detail"]


async def test_a_source_that_recovers_from_rate_limiting_is_ok(monkeypatch):
    flaky = _make_flaky_fetcher("arxiv", [_paper("arxiv", "1", "x")], fail_first_n=2)
    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda _name: flaky)
    query = Query(keywords="x", sources=("arxiv",), max_results=5)

    collection = await pipeline_module.run_search(query, resolve_oa=False)

    assert _stats(collection)["arxiv"]["status"] == "ok"
    assert _stats(collection)["arxiv"]["returned"] == 1


async def test_sources_keep_independent_counts(monkeypatch):
    pool = {
        "arxiv": _make_fetcher(
            "arxiv", [_scored_paper(f"a{i}", f"Arxiv Only Paper {i}") for i in range(3)]
        ),
        "pubmed": _make_fetcher(
            "pubmed",
            [
                Paper(
                    source="pubmed", source_id=f"p{i}", title=f"Pubmed Only Paper {i}",
                    authors=("Bo Author",), year=2025, venue=None, abstract="",
                    url=f"https://example.com/p{i}",
                )
                for i in range(5)
            ],
        ),
        "dblp": _make_fetcher("dblp", []),
    }
    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda name: pool[name])
    query = Query(keywords="x", sources=("arxiv", "pubmed", "dblp"), max_results=50)

    collection = await pipeline_module.run_search(query, resolve_oa=False)

    stats = _stats(collection)
    assert (stats["arxiv"]["returned"], stats["arxiv"]["after_dedup"]) == (3, 3)
    assert (stats["pubmed"]["returned"], stats["pubmed"]["after_dedup"]) == (5, 5)
    assert stats["dblp"] == {
        "source": "dblp", "requested": 50, "returned": 0, "after_dedup": 0,
        "status": "ok", "detail": "",   # an empty answer is still an answer
    }


async def test_dedup_count_is_lower_than_returned_when_records_overlap(monkeypatch):
    """The paper both sources return is credited to the first source named."""

    def _doi_paper(source: str, sid: str, title: str, doi: str) -> Paper:
        return Paper(
            source=source, source_id=sid, title=title, authors=("Ada Author",),
            year=2025, venue=None, abstract="", url=f"https://example.com/{sid}",
            doi=doi,
        )

    pool = {
        "arxiv": _make_fetcher(
            "arxiv",
            [
                _doi_paper("arxiv", "a1", "Shared One", "10.1000/one"),
                _doi_paper("arxiv", "a2", "Shared Two", "10.1000/two"),
                _doi_paper("arxiv", "a3", "Arxiv Only", "10.1000/three"),
            ],
        ),
        "openalex": _make_fetcher(
            "openalex",
            [
                _doi_paper("openalex", "o1", "Shared One", "10.1000/one"),
                _doi_paper("openalex", "o2", "Shared Two", "10.1000/two"),
                _doi_paper("openalex", "o3", "Openalex Only", "10.1000/four"),
            ],
        ),
    }
    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda name: pool[name])
    query = Query(keywords="x", sources=("arxiv", "openalex"), max_results=50)

    collection = await pipeline_module.run_search(query, resolve_oa=False)

    stats = _stats(collection)
    assert (stats["arxiv"]["returned"], stats["arxiv"]["after_dedup"]) == (3, 3)
    assert (stats["openalex"]["returned"], stats["openalex"]["after_dedup"]) == (3, 1)
    assert stats["openalex"]["after_dedup"] < stats["openalex"]["returned"]
    credited = sum(stat["after_dedup"] for stat in stats.values())
    assert credited == len(collection.papers) == 4


async def test_a_sources_own_duplicates_collapse_too(monkeypatch):
    twin = _scored_paper("same", "Printed Twice By One Source")
    pool = {"arxiv": _make_fetcher("arxiv", [twin, twin, _scored_paper("x", "Another")])}
    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda name: pool[name])
    query = Query(keywords="x", sources=("arxiv",), max_results=50)

    collection = await pipeline_module.run_search(query, resolve_oa=False)

    assert _stats(collection)["arxiv"]["returned"] == 3
    assert _stats(collection)["arxiv"]["after_dedup"] == 2


async def test_source_counts_describe_the_sources_not_the_filtered_result(monkeypatch):
    """Filters and the final cut run after the counts are taken."""
    papers = [
        _scored_paper(str(i), f"Distinct Paper {i}", citations=i * 10) for i in range(6)
    ]
    pool = {"arxiv": _make_fetcher("arxiv", papers)}
    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda name: pool[name])
    query = Query(
        keywords="x", sources=("arxiv",), max_results=2, min_citations=30
    )

    collection = await pipeline_module.run_search(query, resolve_oa=False)

    assert len(collection.papers) == 2
    stat = _stats(collection)["arxiv"]
    assert (stat["requested"], stat["returned"], stat["after_dedup"]) == (2, 6, 6)


async def test_the_papers_are_the_same_with_or_without_the_stats(monkeypatch):
    """Keeping per-source outcomes must not change what the search returns."""
    from thesisagents.core.dedup import dedupe
    from thesisagents.core.ranking import rank

    arxiv = [_scored_paper(f"a{i}", f"Transformer Attention {i}") for i in range(3)]
    openalex = [_scored_paper(f"a{i}", f"Transformer Attention {i}") for i in (1, 2)]
    openalex.append(_scored_paper("o9", "Cooking With Gas"))
    pool = {"arxiv": _make_fetcher("arxiv", arxiv), "openalex": _make_fetcher("openalex", openalex)}
    monkeypatch.setattr(pipeline_module, "load_fetcher", lambda name: pool[name])
    query = Query(
        keywords="transformer attention", sources=("arxiv", "openalex"), max_results=50
    )

    collection = await pipeline_module.run_search(query, resolve_oa=False)

    expected = rank(dedupe([*arxiv, *openalex]), keywords="transformer attention")
    assert list(collection.papers) == expected


def test_source_stat_serialises_to_json():
    import json

    from thesisagents.core.diagnostics import SourceStat, SourceStatus

    stat = SourceStat(
        "ieee", requested=25, returned=0, after_dedup=0,
        status=SourceStatus.FAILED, detail="[ieee] blocked",
    )

    assert json.loads(json.dumps(stat.to_dict())) == {
        "source": "ieee", "requested": 25, "returned": 0, "after_dedup": 0,
        "status": "failed", "detail": "[ieee] blocked",
    }
