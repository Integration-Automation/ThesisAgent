"""``rank_with_scores``: the same order as ``rank``, with the reason attached."""

from __future__ import annotations

import json
import math

import pytest

from thesisagents.core import ranking
from thesisagents.core.models import Paper
from thesisagents.core.ranking import (
    RankingPolicy,
    rank,
    rank_with_scores,
    title_terms,
)

_YEAR = 2026


def _paper(
    sid: str, title: str, abstract: str = "", year: int | None = 2024,
    citations: int | None = None,
) -> Paper:
    return Paper(
        source="arxiv", source_id=sid, title=title, authors=("Ada Author",),
        year=year, venue=None, abstract=abstract,
        url=f"https://example.org/{sid}", citation_count=citations,
    )


_CORPUS = (
    _paper("rag", "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
           "We study retrieval augmented generation.", 2020, 5000),
    _paper("llm", "Large Language Models: A Survey", "A survey of LLMs.", 2024, 300),
    _paper("resnet", "Deep Residual Learning for Image Recognition", "ResNet.", 2015, 150000),
    _paper("viterbi", "A Viterbi Decoder Code Generator", "generation of decoders", 2009, 2),
    _paper("scatter", "Generation of Augmented Datasets by Retrieval", "", 2023, 40),
    _paper("noyear", "Transformers", "attention attention attention", None, None),
    _paper("cjk", "注意力機制於影像辨識之應用", "本文探討注意力機制。", 2022, 12),
    _paper("tie-a", "Graph Neural Networks", "", 2021, 10),
    _paper("tie-b", "Graph Neural Networks", "", 2021, 10),
)
_QUERIES = (
    None, "", "retrieval augmented generation", "llm", "large language model",
    "transformer attention", "注意力機制", "graph neural network gnn", "a of the",
    "image recognition residual", "generation",
)


def _legacy_total(paper: Paper, keywords: str | None) -> float:
    """The scoring formula as it stood before ``rank_with_scores`` existed."""
    terms = frozenset(ranking._ordered_tokens(keywords)) if keywords else frozenset()  # noqa: SLF001
    bigrams = ranking._bigrams(keywords) if keywords else frozenset()  # noqa: SLF001
    relevance = 0.0
    if terms:
        title_hit = len(terms & ranking._term_set(paper.title)) / len(terms)  # noqa: SLF001
        abstract_hit = len(terms & ranking._term_set(paper.abstract)) / len(terms)  # noqa: SLF001
        relevance = title_hit * 3.0 + abstract_hit * 0.6
        if bigrams:
            matched = len(bigrams & ranking._bigrams(paper.title))  # noqa: SLF001
            relevance += 1.0 * (matched / len(bigrams))
    recency = 0.0 if paper.year is None else math.exp(-max(0, _YEAR - paper.year) / 5.0)
    citation = 0.0
    if paper.citation_count is not None and paper.citation_count > 0:
        citation = 0.4 * math.log10(paper.citation_count + 1.0)
    return relevance + recency + citation


# ---------------------------------------------------------------------------
# Same order as before
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("keywords", _QUERIES)
def test_order_and_totals_match_the_original_formula(keywords):
    legacy = sorted(_CORPUS, key=lambda p: _legacy_total(p, keywords), reverse=True)

    ranked = rank_with_scores(_CORPUS, keywords, current_year=_YEAR)

    assert [e.paper.source_id for e in ranked] == [p.source_id for p in legacy]
    for entry in ranked:
        assert entry.score.total == _legacy_total(entry.paper, keywords)  # bit-identical


@pytest.mark.parametrize("keywords", _QUERIES)
def test_rank_returns_the_papers_of_rank_with_scores(keywords):
    plain = rank(_CORPUS, keywords, current_year=_YEAR)
    scored = rank_with_scores(_CORPUS, keywords, current_year=_YEAR)

    assert plain == [entry.paper for entry in scored]


def test_equal_scores_keep_their_input_order():
    ranked = rank_with_scores(_CORPUS, "graph neural network", current_year=_YEAR)
    ties = [e.paper.source_id for e in ranked if e.paper.source_id.startswith("tie-")]

    assert ties == ["tie-a", "tie-b"]


def test_ranks_run_from_one_without_gaps():
    ranked = rank_with_scores(_CORPUS, "generation", current_year=_YEAR)

    assert [entry.rank for entry in ranked] == list(range(1, len(_CORPUS) + 1))


def test_an_empty_input_ranks_to_nothing():
    assert rank_with_scores([], "anything", current_year=_YEAR) == []


# ---------------------------------------------------------------------------
# The breakdown
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("keywords", _QUERIES)
def test_total_is_the_sum_of_the_three_axes(keywords):
    for entry in rank_with_scores(_CORPUS, keywords, current_year=_YEAR):
        score = entry.score
        assert score.total == score.relevance + score.recency + score.citation


def test_relevance_dominates_an_off_topic_high_citation_paper():
    ranked = rank_with_scores(
        _CORPUS, "retrieval augmented generation", current_year=_YEAR
    )
    by_id = {entry.paper.source_id: entry for entry in ranked}

    assert by_id["rag"].rank < by_id["resnet"].rank
    assert by_id["resnet"].score.citation > by_id["rag"].score.citation  # more cited
    assert by_id["resnet"].score.relevance == 0.0
    assert by_id["resnet"].score.matched_terms == ()
    assert "no query term appears in the title or abstract" in by_id["resnet"].score.reasons


def test_a_phrase_match_explains_its_bonus():
    ranked = rank_with_scores(
        _CORPUS, "retrieval augmented generation", current_year=_YEAR
    )
    by_id = {entry.paper.source_id: entry.score for entry in ranked}
    adjacent, scattered = by_id["rag"], by_id["scatter"]

    assert adjacent.matched_phrases == ("retrieval augment", "augment generation")
    assert (
        'query words adjacent in the title ("retrieval augment", '
        '"augment generation"): +1.00' in adjacent.reasons
    )
    # Same three words in the title, in another order: no phrase, no bonus.
    assert scattered.matched_terms == adjacent.matched_terms
    assert scattered.matched_phrases == ()
    assert not any("adjacent" in reason for reason in scattered.reasons)
    title_points = 3.0
    assert scattered.relevance == pytest.approx(title_points)
    assert adjacent.relevance == pytest.approx(title_points + 0.6 + 1.0)


def test_an_acronym_query_names_the_long_form_it_matched():
    ranked = rank_with_scores(_CORPUS, "llm", current_year=_YEAR)
    score = next(e.score for e in ranked if e.paper.source_id == "llm")

    assert score.matched_terms == ("llm",)
    assert '"llm" matched through its long form "large language model"' in score.reasons


def test_a_long_form_query_names_the_acronym_it_matched():
    paper = _paper("acro", "LLM Agents for Code Review")

    score = rank_with_scores([paper], "language", current_year=_YEAR)[0].score

    assert score.matched_terms == ("language",)
    assert '"language" matched through the acronym "llm"' in score.reasons


def test_a_literal_match_carries_no_synonym_note():
    paper = _paper("lit", "Large Language Models and LLM Agents")

    score = rank_with_scores([paper], "llm", current_year=_YEAR)[0].score

    assert not any("matched through" in reason for reason in score.reasons)


def test_matched_terms_follow_query_order_in_stemmed_form():
    paper = _paper("order", "Generation with Transformers", "retrieval of documents")

    score = rank_with_scores(
        [paper], "transformers retrieval generation missing", current_year=_YEAR
    )[0].score

    assert score.matched_terms == ("transformer", "retrieval", "generation")
    assert "title matches 2 of 4 query terms (transformer, generation): +1.50" in score.reasons
    assert "abstract matches 1 of 4 query terms (retrieval): +0.15" in score.reasons


def test_a_repeated_query_word_counts_once():
    paper = _paper("rep", "Attention")

    score = rank_with_scores([paper], "attention attention", current_year=_YEAR)[0].score

    assert score.matched_terms == ("attention",)
    assert "title matches 1 of 1 query terms (attention): +3.00" in score.reasons


def test_cjk_query_terms_are_reported_as_bigrams():
    ranked = rank_with_scores(_CORPUS, "注意力機制", current_year=_YEAR)
    score = next(e.score for e in ranked if e.paper.source_id == "cjk")

    assert score.matched_terms == ("注意", "意力", "力機", "機制")
    assert score.relevance_ratio == pytest.approx(1.0)


def test_recency_and_citation_reasons_state_the_facts():
    known = rank_with_scores([_CORPUS[0]], "x", current_year=_YEAR)[0].score
    unknown = rank_with_scores(
        [_paper("u", "Untitled", year=None, citations=None)], "x", current_year=_YEAR
    )[0].score

    assert "published 2020: recency +0.30" in known.reasons
    assert "5,000 citations: +1.48" in known.reasons
    assert "publication year unknown: recency +0.00" in unknown.reasons
    assert "citation count unknown: citations +0.00" in unknown.reasons
    assert unknown.recency == 0.0
    assert unknown.citation == 0.0


# ---------------------------------------------------------------------------
# relevance_ratio
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("keywords", [None, "", "   ", "a of"])
def test_no_usable_query_means_no_relevance_ratio(keywords):
    score = rank_with_scores([_CORPUS[0]], keywords, current_year=_YEAR)[0].score

    assert score.relevance_ratio is None
    assert score.relevance == 0.0
    assert score.matched_terms == ()
    assert "no query: ranked by recency and citations only" in score.reasons


@pytest.mark.parametrize("keywords", [q for q in _QUERIES if q and q != "a of the"])
def test_relevance_ratio_stays_between_zero_and_one(keywords):
    for entry in rank_with_scores(_CORPUS, keywords, current_year=_YEAR):
        assert 0.0 <= entry.score.relevance_ratio <= 1.0


def test_a_full_match_scores_a_ratio_of_one():
    paper = _paper("full", "Transformer Attention", "transformer attention in depth")

    score = rank_with_scores([paper], "transformer attention", current_year=_YEAR)[0].score

    assert score.relevance_ratio == pytest.approx(1.0)
    assert score.relevance == pytest.approx(3.0 + 0.6 + 1.0)


def test_a_one_word_query_has_no_phrase_in_its_best_score():
    paper = _paper("one", "Transformers", "about transformers")

    score = rank_with_scores([paper], "transformer", current_year=_YEAR)[0].score

    assert score.relevance == pytest.approx(3.6)
    assert score.relevance_ratio == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


def test_a_policy_without_citations_changes_the_order():
    old_cited = _paper("old", "Unrelated Classic", year=2025, citations=100000)
    new_uncited = _paper("new", "Unrelated Fresh", year=2026, citations=0)

    default = rank_with_scores([old_cited, new_uncited], None, current_year=_YEAR)
    no_citations = rank_with_scores(
        [old_cited, new_uncited], None, RankingPolicy(citation_weight=0.0),
        current_year=_YEAR,
    )

    assert [e.paper.source_id for e in default] == ["old", "new"]
    assert [e.paper.source_id for e in no_citations] == ["new", "old"]
    assert no_citations[1].score.citation == 0.0


def test_policy_weights_scale_the_axes():
    paper = _paper("w", "Transformer Attention", "transformer attention")
    policy = RankingPolicy(title_weight=1.0, abstract_weight=2.0, phrase_weight=0.5)

    score = rank_with_scores(
        [paper], "transformer attention", policy, current_year=_YEAR
    )[0].score

    assert score.relevance == pytest.approx(3.5)
    assert score.relevance_ratio == pytest.approx(1.0)
    assert policy.max_relevance(has_phrases=True) == pytest.approx(3.5)
    assert policy.max_relevance(has_phrases=False) == pytest.approx(3.0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"title_weight": -1.0}, {"abstract_weight": -0.1}, {"phrase_weight": -1.0},
        {"citation_weight": -0.4}, {"recency_scale_years": 0.0},
        {"recency_scale_years": -5.0},
    ],
)
def test_a_nonsensical_policy_is_rejected(kwargs):
    with pytest.raises(ValueError):
        RankingPolicy(**kwargs)


def test_an_all_zero_relevance_policy_gives_a_zero_ratio_not_a_crash():
    policy = RankingPolicy(title_weight=0.0, abstract_weight=0.0, phrase_weight=0.0)

    score = rank_with_scores(
        [_CORPUS[0]], "retrieval", policy, current_year=_YEAR
    )[0].score

    assert score.relevance_ratio == 0.0


# ---------------------------------------------------------------------------
# Serialisation + helpers
# ---------------------------------------------------------------------------


def test_score_serialises_to_json_with_rounded_numbers():
    score = rank_with_scores(
        _CORPUS, "retrieval augmented generation", current_year=_YEAR
    )[0].score

    payload = score.to_dict()

    assert json.loads(json.dumps(payload)) == payload
    assert set(payload) == {
        "total", "relevance", "recency", "citation", "relevance_ratio",
        "matched_terms", "matched_phrases", "reasons",
    }
    assert payload["total"] == round(score.total, 4)
    assert payload["matched_terms"] == ["retrieval", "augment", "generation"]


def test_a_score_without_a_query_serialises_a_null_ratio():
    score = rank_with_scores([_CORPUS[0]], None, current_year=_YEAR)[0].score

    assert score.to_dict()["relevance_ratio"] is None


def test_title_terms_are_stemmed_and_unexpanded():
    assert title_terms("Transformers for Vision") == frozenset(
        {"transformer", "for", "vision"}
    )
    assert "large" not in title_terms("LLM Agents")  # no synonym expansion
    assert title_terms("") == frozenset()
    assert title_terms("...") == frozenset()


def test_current_year_defaults_to_now():
    from datetime import UTC, datetime

    paper = _paper("now", "Fresh", year=datetime.now(UTC).year)

    assert rank_with_scores([paper], None)[0].score.recency == 1.0
