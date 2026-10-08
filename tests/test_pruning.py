"""``recommend_pruning``: advice on which results to keep, review or drop."""

from __future__ import annotations

import json

import pytest

from thesisagents.core.diagnostics import PruningAction
from thesisagents.core.models import Paper
from thesisagents.core.pruning import PruningPolicy, recommend_pruning
from thesisagents.core.ranking import rank_with_scores

_YEAR = 2026
_QUERY = "transformer attention"


def _paper(
    sid: str, title: str, abstract: str = "", year: int | None = 2024,
    citations: int | None = None, doi: str | None = None,
) -> Paper:
    return Paper(
        source="arxiv", source_id=sid, title=title, authors=("Ada Author",),
        year=year, venue=None, abstract=abstract,
        url=f"https://example.org/{sid}", citation_count=citations, doi=doi,
    )


def _advise(papers, keywords=_QUERY, policy=None):
    ranked = rank_with_scores(papers, keywords, current_year=_YEAR)
    advice = recommend_pruning(ranked, policy)
    return {ranked[i].paper.source_id: advice[i] for i in range(len(ranked))}


# ---------------------------------------------------------------------------
# Roadmap cases
# ---------------------------------------------------------------------------


def test_low_score_papers_get_review_or_prune():
    advice = _advise(
        [
            _paper("on", "Transformer Attention Explained", "transformer attention"),
            _paper("abstract-only", "Sequence Models", "transformer attention inside"),
            _paper("off", "A Viterbi Decoder Code Generator", "decoding codes"),
        ]
    )

    assert advice["on"].action is PruningAction.KEEP
    assert advice["abstract-only"].action is PruningAction.REVIEW
    assert advice["abstract-only"].threshold == "review_below_relevance=0.30"
    assert advice["off"].action is PruningAction.PRUNE
    assert advice["off"].threshold == "prune_below_relevance=0.10"
    assert advice["off"].reasons == (
        "relevance is 0% of the best this query allows, below the prune threshold 10%",
    )


def test_a_top_ranked_paper_is_not_pruned_for_low_citations():
    """A new, on-topic paper has no citations yet. That alone must never
    produce a recommendation."""
    advice = _advise(
        [
            _paper("fresh", "Transformer Attention at Scale", citations=0, year=2026),
            _paper("unknown", "Transformer Attention Revisited", citations=None),
            _paper("old-uncited", "Transformer Attention Notes", citations=0, year=2001),
        ]
    )

    for key in ("fresh", "unknown", "old-uncited"):
        assert advice[key].action is PruningAction.KEEP, key
        assert advice[key].threshold == ""
        assert not any("cited" in reason for reason in advice[key].reasons)


def test_recommendations_are_stable_for_identical_inputs():
    papers = [
        _paper("a", "Transformer Attention Explained"),
        _paper("b", "Transformer Attention Explained Again"),
        _paper("c", "Sequence Models", "transformer attention"),
        _paper("d", "Cooking With Gas", year=2001, citations=1),
    ]

    first = _advise(papers)
    second = _advise(papers)
    reversed_twice = _advise(list(reversed(list(reversed(papers)))))

    assert first == second == reversed_twice


# ---------------------------------------------------------------------------
# Rule 2: weak on every axis
# ---------------------------------------------------------------------------


def test_a_review_paper_that_is_old_and_uncited_becomes_prune():
    advice = _advise(
        [_paper("weak", "Sequence Models", "transformer attention", year=2010, citations=2)]
    )["weak"]

    assert advice.action is PruningAction.PRUNE
    assert advice.threshold == "weak_on_all_axes(weak_recency=0.15, weak_citations=5)"
    assert advice.reasons[-1] == (
        "also old (published 2010) and weakly cited (2 citations), "
        "so no axis argues for keeping it"
    )


@pytest.mark.parametrize(
    ("year", "citations"),
    [
        (2010, 500),    # old but well cited
        (2025, 2),      # uncited but recent
        (None, 2),      # year unknown: not the same as old
        (2010, None),   # citation count unknown: not the same as uncited
        (None, None),
    ],
)
def test_one_strong_or_unknown_axis_keeps_it_at_review(year, citations):
    advice = _advise(
        [_paper("p", "Sequence Models", "transformer attention", year=year, citations=citations)]
    )["p"]

    assert advice.action is PruningAction.REVIEW
    assert advice.threshold == "review_below_relevance=0.30"


def test_the_recency_boundary_is_ten_years():
    abstract = "transformer attention"
    nine = _paper("nine", "Sequence Models", abstract, year=_YEAR - 9, citations=0)
    ten = _paper("ten", "Sequence Models Two", abstract, year=_YEAR - 10, citations=0)

    advice = _advise([nine, ten])

    assert advice["nine"].action is PruningAction.REVIEW
    assert advice["ten"].action is PruningAction.PRUNE


def test_the_citation_boundary_is_the_policy_value():
    four = _paper("four", "Sequence Models", "transformer attention", year=2005, citations=4)
    five = _paper("five", "Sequence Models Two", "transformer attention", year=2005, citations=5)

    advice = _advise([four, five])

    assert advice["four"].action is PruningAction.PRUNE
    assert advice["five"].action is PruningAction.REVIEW


# ---------------------------------------------------------------------------
# Rule 3: redundancy
# ---------------------------------------------------------------------------


def test_a_near_duplicate_title_is_flagged_against_the_higher_ranked_paper():
    """Dedup keeps a workshop paper and its journal version apart because
    their DOIs differ. This is where the overlap is reported."""
    journal = _paper(
        "journal", "Transformer Attention for Long Documents", year=2025,
        citations=90, doi="10.1000/journal",
    )
    workshop = _paper(
        "workshop", "Transformer Attention for Long Documents", year=2024,
        citations=3, doi="10.1000/workshop",
    )

    advice = _advise([workshop, journal])

    assert advice["journal"].action is PruningAction.KEEP
    assert advice["workshop"].action is PruningAction.REVIEW
    assert advice["workshop"].threshold == "redundant_title_overlap=0.85"
    assert advice["workshop"].reasons[-1] == (
        'title shares 100% of its terms with higher-ranked #1 '
        '"Transformer Attention for Long Documents"'
    )


def test_titles_below_the_overlap_bar_are_not_redundant():
    advice = _advise(
        [
            _paper("a", "Transformer Attention for Long Documents", year=2025),
            _paper("b", "Transformer Attention for Protein Folding", year=2024),
        ]
    )

    assert advice["b"].action is PruningAction.KEEP
    assert not any("shares" in reason for reason in advice["b"].reasons)


def test_the_overlap_bar_is_inclusive_and_configurable():
    # 6 shared terms of 7 in the union: an overlap of 6/7, about 0.857.
    papers = [
        _paper("a", "Transformer Attention for Long Legal Documents", year=2025),
        _paper("b", "Transformer Attention for Long Legal Documents Revisited", year=2024),
    ]

    assert _advise(papers)["b"].action is PruningAction.REVIEW
    strict = PruningPolicy(redundant_title_overlap=0.9)
    assert _advise(papers, policy=strict)["b"].action is PruningAction.KEEP
    exact = PruningPolicy(redundant_title_overlap=6 / 7)
    assert _advise(papers, policy=exact)["b"].action is PruningAction.REVIEW


def test_a_long_title_is_shortened_in_the_reason():
    long_title = "Transformer Attention " + "for Very Long Documents " * 6
    advice = _advise(
        [
            _paper("a", long_title, year=2025),
            _paper("b", long_title, year=2024),
        ]
    )["b"]

    quoted = advice.reasons[-1].split("#1 ", 1)[1]
    assert quoted.endswith('…"')
    assert len(quoted) == 62  # 60 characters and the two quote marks


def test_title_less_papers_are_never_called_redundant():
    advice = _advise(
        [_paper("a", "...", "transformer attention"), _paper("b", "", "transformer attention")]
    )

    assert not any("shares" in reason for a in advice.values() for reason in a.reasons)


def test_a_review_paper_that_is_also_redundant_keeps_its_first_threshold():
    advice = _advise(
        [
            _paper("a", "Sequence Models in Practice", "transformer attention", year=2025),
            _paper("b", "Sequence Models in Practice", "transformer attention", year=2024),
        ]
    )["b"]

    assert advice.action is PruningAction.REVIEW
    assert advice.threshold == "review_below_relevance=0.30"
    assert len(advice.reasons) == 2
    assert "shares 100% of its terms" in advice.reasons[1]


def test_a_pruned_paper_gets_no_redundancy_note():
    advice = _advise(
        [
            _paper("a", "Cooking With Gas", year=2025),
            _paper("b", "Cooking With Gas", year=2024),
        ]
    )

    assert advice["a"].action is advice["b"].action is PruningAction.PRUNE
    assert len(advice["b"].reasons) == 1


# ---------------------------------------------------------------------------
# No query, shape, policy
# ---------------------------------------------------------------------------


def test_without_a_query_everything_is_kept():
    papers = [_paper("a", "Anything"), _paper("b", "Something Else", year=1990, citations=0)]

    for advice in _advise(papers, keywords=None).values():
        assert advice.action is PruningAction.KEEP
        assert advice.reasons == ("no query: relevance was not assessed",)
        assert advice.threshold == ""


def test_one_recommendation_per_paper_in_rank_order():
    papers = [_paper(str(i), f"Transformer Attention Part {i}", year=2020 + i) for i in range(5)]
    ranked = rank_with_scores(papers, _QUERY, current_year=_YEAR)

    advice = recommend_pruning(ranked)

    assert [a.rank for a in advice] == [1, 2, 3, 4, 5]
    assert [a.paper_key for a in advice] == [e.paper.dedup_key() for e in ranked]


def test_an_empty_ranking_gives_no_recommendations():
    assert recommend_pruning([]) == ()


def test_thresholds_follow_the_policy():
    paper = _paper("p", "Attention", "transformer attention")  # half the title
    lenient = PruningPolicy(review_below_relevance=0.2)
    strict = PruningPolicy(prune_below_relevance=0.5, review_below_relevance=0.6)

    assert _advise([paper])["p"].action is PruningAction.KEEP
    assert _advise([paper], policy=lenient)["p"].action is PruningAction.KEEP
    pruned = _advise([paper], policy=strict)["p"]
    assert pruned.action is PruningAction.PRUNE
    assert pruned.threshold == "prune_below_relevance=0.50"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"prune_below_relevance": 0.5, "review_below_relevance": 0.4},
        {"prune_below_relevance": -0.1},
        {"review_below_relevance": 1.5},
        {"redundant_title_overlap": 0.0},
        {"redundant_title_overlap": 1.1},
        {"weak_recency": -0.1},
        {"weak_citations": -1},
    ],
)
def test_a_nonsensical_policy_is_rejected(kwargs):
    with pytest.raises(ValueError):
        PruningPolicy(**kwargs)


def test_a_recommendation_serialises_to_json():
    advice = _advise([_paper("p", "Sequence Models", "transformer attention")])["p"]

    payload = advice.to_dict()

    assert json.loads(json.dumps(payload)) == payload
    assert payload["action"] == "review"
    assert payload["threshold"] == "review_below_relevance=0.30"
    assert payload["rank"] == 1
