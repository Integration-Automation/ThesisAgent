"""Bounded snowball search over an in-memory citation graph.

``GraphProvider`` answers from a dict, so every test states its whole graph
and no request leaves the process.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from thesisagents.core.diagnostics import PaperRelation, RelationKind
from thesisagents.core.exceptions import (
    CitationNotAvailableError,
    RateLimitError,
    SourceUnavailableError,
)
from thesisagents.core.models import Paper
from thesisagents.core.snowball import Direction, SnowballResult, snowball
from thesisagents.fetchers.citations import CitationProvider

_YEAR = 2026


def _paper(key: str, title: str, *, doi: str | None = None, **overrides) -> Paper:
    fields = {
        "source": "test", "source_id": key, "title": title,
        "authors": ("Ada Author",), "year": 2024, "venue": None, "abstract": "",
        "url": f"https://example.org/{key}",
        "doi": doi if doi is not None else f"10.1000/{key}",
    }
    fields.update(overrides)
    return Paper(**fields)


class GraphProvider(CitationProvider):
    """Answer from ``{(seed_source_id, "references" | "cited_by"): [papers]}``.

    ``fail_with`` makes every call raise that exception instead. ``calls``
    records ``(source_id, direction, limit)`` for each call.
    """

    def __init__(self, name: str = "graph", graph=None, *, fail_with=None, delay=0.0):
        self.name = name
        self._graph = graph or {}
        self._fail_with = fail_with
        self._delay = delay
        self.calls: list[tuple[str, str, int]] = []
        self.in_flight = 0
        self.peak = 0

    async def _answer(self, paper: Paper, direction: str, limit: int) -> list[Paper]:
        self.calls.append((paper.source_id, direction, limit))
        self.in_flight += 1
        self.peak = max(self.peak, self.in_flight)
        try:
            if self._delay:
                await asyncio.sleep(self._delay)
            if self._fail_with is not None:
                raise self._fail_with
            return list(self._graph.get((paper.source_id, direction), []))
        finally:
            self.in_flight -= 1

    async def references(self, paper: Paper, limit: int) -> list[Paper]:
        return await self._answer(paper, "references", limit)

    async def cited_by(self, paper: Paper, limit: int) -> list[Paper]:
        return await self._answer(paper, "cited_by", limit)


SEED = _paper("seed", "Graph Neural Networks for Molecules")
REF_1 = _paper("ref1", "Neural Message Passing for Quantum Chemistry")
REF_2 = _paper("ref2", "Spectral Networks on Graphs")
CITING_1 = _paper("cit1", "Graph Neural Networks at Scale")
CITING_2 = _paper("cit2", "A Survey of Graph Neural Networks")


def _ids(result: SnowballResult) -> list[str]:
    return [entry.paper.source_id for entry in result.discovered]


# ---------------------------------------------------------------------------
# Roadmap cases
# ---------------------------------------------------------------------------


async def test_forward_expansion_returns_citing_papers():
    provider = GraphProvider(graph={("seed", "cited_by"): [CITING_1, CITING_2]})

    result = await snowball([SEED], direction="cited_by", providers=[provider])

    assert _ids(result) == ["cit1", "cit2"]
    assert {call[1] for call in provider.calls} == {"cited_by"}
    for entry in result.discovered:
        assert entry.found_by.relation is RelationKind.CITED_BY
        assert entry.found_by.source_key == SEED.dedup_key()
        assert entry.found_by.citing_key == entry.paper.dedup_key()
        assert entry.found_by.cited_key == SEED.dedup_key()


async def test_backward_expansion_returns_references():
    provider = GraphProvider(graph={("seed", "references"): [REF_1, REF_2]})

    result = await snowball([SEED], direction=Direction.REFERENCES, providers=[provider])

    assert _ids(result) == ["ref1", "ref2"]
    assert {call[1] for call in provider.calls} == {"references"}
    relation = result.discovered[0].found_by
    assert relation.relation is RelationKind.REFERENCES
    assert relation.citing_key == SEED.dedup_key()       # the seed cites it
    assert relation.cited_key == REF_1.dedup_key()


async def test_both_directions_respect_depth():
    deep = _paper("deep", "Laplacian Eigenmaps")
    graph = {
        ("seed", "references"): [REF_1],
        ("seed", "cited_by"): [CITING_1],
        ("ref1", "references"): [deep],
        ("deep", "references"): [_paper("deeper", "Never Reached At Depth Two")],
    }

    shallow = await snowball([SEED], depth=1, providers=[GraphProvider(graph=graph)])
    two = await snowball([SEED], depth=2, providers=[GraphProvider(graph=graph)])

    assert _ids(shallow) == ["ref1", "cit1"]
    assert _ids(two) == ["ref1", "cit1", "deep"]
    depths = {entry.paper.source_id: entry.found_by.depth for entry in two.discovered}
    assert depths == {"ref1": 1, "cit1": 1, "deep": 2}
    assert two.discovered[2].found_by.source_key == REF_1.dedup_key()


async def test_both_directions_respect_the_caps():
    many = [_paper(f"r{i}", f"Reference Number {i}") for i in range(30)]
    provider = GraphProvider(
        graph={("seed", "references"): many, ("seed", "cited_by"): many[:5]}
    )

    result = await snowball([SEED], max_per_seed=10, max_total=12, providers=[provider])

    assert all(limit == 10 for _key, _direction, limit in provider.calls)
    # 10 taken from the references, then 5 citing papers that are among them.
    assert len(result.discovered) == 10
    assert result.truncated is False

    capped = await snowball([SEED], max_per_seed=30, max_total=12, providers=[provider])
    assert len(capped.discovered) == 12
    assert capped.truncated is True


async def test_duplicate_paths_collapse_to_one_paper():
    """Reached from two seeds, and from the second under another record of
    the same DOI, it is still one discovered paper."""
    other_seed = _paper("seed2", "Graph Attention Networks")
    same_paper_other_record = _paper(
        "ref1-from-another-index", "Neural message passing for quantum chemistry.",
        doi="10.1000/REF1",
    )
    provider = GraphProvider(
        graph={
            ("seed", "references"): [REF_1],
            ("seed2", "references"): [same_paper_other_record],
        }
    )

    result = await snowball(
        [SEED, other_seed], direction="references", providers=[provider]
    )

    assert _ids(result) == ["ref1"]
    targets = [relation.target_key for relation in result.relations]
    assert targets == [REF_1.dedup_key(), REF_1.dedup_key()]  # two links, one paper
    assert {relation.source_key for relation in result.relations} == {
        SEED.dedup_key(), other_seed.dedup_key()
    }


async def test_provenance_records_the_first_and_shortest_path():
    """``far`` is one step from seed2 and two steps from seed via ref1. The
    one-step path is recorded, whichever order the lookups finish in."""
    seed2 = _paper("seed2", "Graph Attention Networks")
    far = _paper("far", "Semi-Supervised Classification with Graph Convolutions")
    graph = {
        ("seed", "references"): [REF_1],
        ("ref1", "references"): [far],
        ("seed2", "references"): [far],
    }

    result = await snowball(
        [SEED, seed2], direction="references", depth=2,
        providers=[GraphProvider("openalex", graph)],
    )

    found = {entry.paper.source_id: entry.found_by for entry in result.discovered}
    assert found["far"] == PaperRelation(
        source_key=seed2.dedup_key(), target_key=far.dedup_key(),
        relation=RelationKind.REFERENCES, provider="openalex", depth=1,
    )
    # The longer path is still in the graph, just not the recorded provenance.
    assert PaperRelation(
        REF_1.dedup_key(), far.dedup_key(), RelationKind.REFERENCES, "openalex", 2
    ) in result.relations


async def test_a_provider_failure_does_not_abort_the_expansion():
    broken = GraphProvider("broken", fail_with=SourceUnavailableError("broken", "HTTP 503"))
    working = GraphProvider("working", {("seed", "references"): [REF_1]})

    result = await snowball(
        [SEED], direction="references", providers=[broken, working]
    )

    assert _ids(result) == ["ref1"]
    assert result.discovered[0].found_by.provider == "working"
    assert result.errors == (
        f"broken references lookup failed for {SEED.dedup_key()}: [broken] HTTP 503",
    )


# ---------------------------------------------------------------------------
# Provider fallback
# ---------------------------------------------------------------------------


async def test_the_first_provider_with_papers_answers_and_the_rest_are_not_asked():
    first = GraphProvider("first", {("seed", "references"): [REF_1]})
    second = GraphProvider("second", {("seed", "references"): [REF_2]})

    result = await snowball([SEED], direction="references", providers=[first, second])

    assert _ids(result) == ["ref1"]
    assert second.calls == []


async def test_an_empty_answer_falls_through_to_the_next_provider():
    empty = GraphProvider("empty")
    second = GraphProvider("second", {("seed", "references"): [REF_2]})

    result = await snowball([SEED], direction="references", providers=[empty, second])

    assert _ids(result) == ["ref2"]
    assert result.discovered[0].found_by.provider == "second"
    assert result.errors == ()


async def test_not_available_is_skipped_without_being_reported():
    """Crossref has no citing works. That is expected, not an error."""
    unavailable = GraphProvider(
        "crossref", fail_with=CitationNotAvailableError("crossref", "no citing works")
    )
    second = GraphProvider("second", {("seed", "cited_by"): [CITING_1]})

    result = await snowball([SEED], direction="cited_by", providers=[unavailable, second])

    assert _ids(result) == ["cit1"]
    assert result.errors == ()


@pytest.mark.parametrize(
    "failure",
    [RateLimitError("s2", "429"), KeyError("citedPaper"), RuntimeError("boom")],
)
async def test_any_provider_exception_is_contained_and_reported(failure):
    broken = GraphProvider("s2", fail_with=failure)

    result = await snowball([SEED], direction="references", providers=[broken])

    assert result.discovered == ()
    assert len(result.errors) == 1
    assert result.errors[0].startswith("s2 references lookup failed for ")


async def test_no_providers_means_nothing_found_and_no_crash():
    result = await snowball([SEED], providers=[])

    assert result.discovered == ()
    assert result.seeds == (SEED,)


# ---------------------------------------------------------------------------
# Identity, cycles, seeds
# ---------------------------------------------------------------------------


async def test_a_seed_is_never_listed_as_discovered_but_its_link_is_kept():
    seed2 = _paper("seed2", "Graph Attention Networks")
    provider = GraphProvider(graph={("seed", "cited_by"): [seed2, CITING_1]})

    result = await snowball([SEED, seed2], direction="cited_by", providers=[provider])

    assert _ids(result) == ["cit1"]
    assert PaperRelation(
        SEED.dedup_key(), seed2.dedup_key(), RelationKind.CITED_BY, "graph", 1
    ) in result.relations


async def test_a_citation_cycle_does_not_loop():
    graph = {
        ("seed", "references"): [REF_1],
        ("ref1", "references"): [SEED, REF_2],
        ("ref2", "references"): [REF_1, SEED],
    }
    provider = GraphProvider(graph=graph)

    result = await snowball([SEED], direction="references", depth=3, providers=[provider])

    assert _ids(result) == ["ref1", "ref2"]
    assert [call[0] for call in provider.calls] == ["seed", "ref1", "ref2"]  # each once


async def test_a_paper_does_not_link_to_itself():
    provider = GraphProvider(graph={("seed", "references"): [SEED, REF_1]})

    result = await snowball([SEED], direction="references", providers=[provider])

    assert _ids(result) == ["ref1"]
    assert all(r.source_key != r.target_key for r in result.relations)


async def test_duplicate_seeds_are_expanded_once():
    provider = GraphProvider(graph={("seed", "references"): [REF_1]})

    result = await snowball([SEED, SEED], direction="references", providers=[provider])

    assert result.seeds == (SEED,)
    assert len(provider.calls) == 1


async def test_a_second_record_backfills_the_discovered_paper():
    bare = _paper("ref1", "Neural Message Passing for Quantum Chemistry")
    with_pdf = _paper(
        "ref1-oa", "Neural Message Passing for Quantum Chemistry",
        doi="10.1000/ref1", pdf_url="https://example.org/ref1.pdf", venue="ICML",
    )
    provider = GraphProvider(
        graph={("seed", "references"): [bare], ("seed", "cited_by"): [with_pdf]}
    )

    result = await snowball([SEED], providers=[provider])

    assert _ids(result) == ["ref1"]                      # canonical record kept
    assert result.discovered[0].paper.pdf_url == "https://example.org/ref1.pdf"
    assert result.discovered[0].paper.venue == "ICML"


async def test_a_title_less_record_is_dropped():
    provider = GraphProvider(
        graph={("seed", "references"): [_paper("blank", "   "), REF_1]}
    )

    result = await snowball([SEED], direction="references", providers=[provider])

    assert _ids(result) == ["ref1"]


async def test_no_seeds_means_no_requests():
    provider = GraphProvider()

    result = await snowball([], providers=[provider])

    assert result == SnowballResult()
    assert provider.calls == []


# ---------------------------------------------------------------------------
# Relevance
# ---------------------------------------------------------------------------


async def test_discovered_papers_are_scored_and_ordered_by_the_search_ranker():
    off_topic = _paper("off", "Cooking With Gas", citation_count=9000)
    provider = GraphProvider(
        graph={("seed", "references"): [off_topic, REF_2, CITING_1]}
    )

    result = await snowball(
        [SEED], direction="references", keywords="graph neural networks",
        providers=[provider], current_year=_YEAR,
    )

    # Found first, ranked last: 9,000 citations do not make it on topic.
    assert _ids(result) == ["cit1", "ref2", "off"]
    scores = {entry.paper.source_id: entry.score for entry in result.discovered}
    assert scores["cit1"].matched_terms == ("graph", "neural", "network")
    assert scores["off"].relevance == 0.0
    assert scores["off"].citation > scores["cit1"].citation
    assert scores["off"].total < scores["ref2"].total


async def test_without_keywords_papers_keep_discovery_order_and_have_no_score():
    provider = GraphProvider(
        graph={("seed", "references"): [REF_2, REF_1], ("seed", "cited_by"): [CITING_1]}
    )

    result = await snowball([SEED], providers=[provider])

    assert _ids(result) == ["ref2", "ref1", "cit1"]
    assert all(entry.score is None for entry in result.discovered)


async def test_min_relevance_drops_papers_and_does_not_expand_them():
    off_topic = _paper("off", "Cooking With Gas")
    graph = {
        ("seed", "references"): [off_topic, CITING_1],
        ("off", "references"): [_paper("via-off", "Graph Neural Networks Found Via Off Topic")],
    }
    provider = GraphProvider(graph=graph)

    result = await snowball(
        [SEED], direction="references", depth=2, keywords="graph neural networks",
        min_relevance=0.3, providers=[provider], current_year=_YEAR,
    )

    assert _ids(result) == ["cit1"]
    assert "off" not in [call[0] for call in provider.calls]
    assert all("off" not in relation.target_key for relation in result.relations)


async def test_dropped_papers_do_not_use_up_the_total_cap():
    noise = [_paper(f"n{i}", f"Cooking With Gas Volume {i}") for i in range(5)]
    provider = GraphProvider(graph={("seed", "references"): [*noise, CITING_1]})

    result = await snowball(
        [SEED], direction="references", keywords="graph neural networks",
        min_relevance=0.3, max_total=1, providers=[provider], current_year=_YEAR,
    )

    assert _ids(result) == ["cit1"]
    assert result.truncated is False


# ---------------------------------------------------------------------------
# Bounds and validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"depth": 0}, r"depth must be in \[1, 3\]"),
        ({"depth": 4}, r"depth must be in \[1, 3\]"),
        ({"direction": "sideways"}, "direction must be one of: references, cited_by, both"),
        ({"max_per_seed": 0}, r"max_per_seed must be in \[1, 100\]"),
        ({"max_per_seed": 101}, r"max_per_seed must be in \[1, 100\]"),
        ({"max_total": 0}, r"max_total must be in \[1, 1000\]"),
        ({"max_total": 1001}, r"max_total must be in \[1, 1000\]"),
        ({"min_relevance": 0.5}, "min_relevance needs keywords"),
        ({"min_relevance": 0.5, "keywords": "   "}, "min_relevance needs keywords"),
        ({"min_relevance": 1.5, "keywords": "x"}, r"min_relevance must be in \[0, 1\]"),
        ({"min_relevance": -0.1, "keywords": "x"}, r"min_relevance must be in \[0, 1\]"),
    ],
)
async def test_a_bound_outside_its_range_is_rejected_before_any_request(kwargs, message):
    provider = GraphProvider(graph={("seed", "references"): [REF_1]})

    with pytest.raises(ValueError, match=message):
        await snowball([SEED], providers=[provider], **kwargs)

    assert provider.calls == []


async def test_depth_defaults_to_one():
    graph = {("seed", "references"): [REF_1], ("ref1", "references"): [REF_2]}

    result = await snowball([SEED], direction="references", providers=[GraphProvider(graph=graph)])

    assert _ids(result) == ["ref1"]


async def test_the_search_stops_expanding_once_the_cap_is_hit():
    graph = {
        ("seed", "references"): [REF_1, REF_2],
        ("ref1", "references"): [_paper("deep", "Never Asked For")],
    }
    provider = GraphProvider(graph=graph)

    result = await snowball(
        [SEED], direction="references", depth=3, max_total=1, providers=[provider]
    )

    assert _ids(result) == ["ref1"]
    assert result.truncated is True
    assert [call[0] for call in provider.calls] == ["seed"]


async def test_lookups_run_concurrently_but_bounded():
    seeds = [_paper(f"s{i}", f"Seed Paper Number {i}") for i in range(12)]
    provider = GraphProvider(delay=0.01)

    await snowball(seeds, direction="both", providers=[provider])

    assert len(provider.calls) == 24
    assert 1 < provider.peak <= 4


async def test_the_same_inputs_give_the_same_result():
    graph = {
        ("seed", "references"): [REF_1, REF_2],
        ("seed", "cited_by"): [CITING_1, CITING_2, REF_1],
        ("ref1", "cited_by"): [CITING_2],
    }

    runs = [
        await snowball(
            [SEED], depth=2, keywords="graph neural networks",
            providers=[GraphProvider(graph=graph, delay=0.001)], current_year=_YEAR,
        )
        for _ in range(3)
    ]

    assert runs[0] == runs[1] == runs[2]


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------


async def test_result_serialises_to_json():
    provider = GraphProvider(graph={("seed", "references"): [REF_1]})

    result = await snowball(
        [SEED], direction="references", keywords="neural", providers=[provider],
        current_year=_YEAR,
    )
    payload = result.to_dict()

    assert json.loads(json.dumps(payload)) == payload
    assert payload["seed_count"] == 1
    assert payload["discovered_count"] == 1
    assert payload["truncated"] is False
    assert payload["discovered"][0]["paper"]["title"] == REF_1.title
    assert payload["discovered"][0]["found_by"] == {
        "source_key": SEED.dedup_key(), "target_key": REF_1.dedup_key(),
        "relation": "references", "provider": "graph", "depth": 1,
    }
    assert payload["discovered"][0]["score"]["matched_terms"] == ["neural"]
    assert payload["relations"] == [payload["discovered"][0]["found_by"]]
    assert result.papers == (REF_1,)


async def test_default_providers_are_loaded_when_none_are_given(monkeypatch):
    from thesisagents.core import snowball as snowball_module
    from thesisagents.core.exceptions import ConfigError

    loaded: list[str] = []

    def fake_load(name: str):
        loaded.append(name)
        if name == "semantic_scholar":
            raise ConfigError("not installed")
        return GraphProvider(name, {("seed", "references"): [REF_1]})

    monkeypatch.setattr(snowball_module, "load_citation_provider", fake_load)

    result = await snowball([SEED], direction="references")

    assert loaded == ["openalex", "semantic_scholar", "crossref"]
    assert result.discovered[0].found_by.provider == "openalex"
