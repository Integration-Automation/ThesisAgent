"""Tests for dedup and ranking."""

from __future__ import annotations

import pytest

from thesisagents.core.dedup import dedupe
from thesisagents.core.models import Paper
from thesisagents.core.ranking import rank


def _paper(**overrides) -> Paper:
    base = {
        "source": "arxiv", "source_id": "x", "title": "T", "authors": (),
        "year": 2024, "venue": None, "abstract": "", "url": "https://e.com",
    }
    base.update(overrides)
    return Paper(**base)


def test_dedupe_keeps_first_by_doi():
    a = _paper(source_id="1", doi="10.1/a", title="First")
    b = _paper(source_id="2", doi="10.1/a", title="Second")
    out = dedupe([a, b])
    assert out == [a]


def test_dedupe_keeps_distinct():
    a = _paper(source_id="1", arxiv_id="aa")
    b = _paper(source_id="2", arxiv_id="bb")
    assert len(dedupe([a, b])) == 2


def test_dedupe_merges_pdf_url_from_later_source():
    """ACM returns the paper first with no pdf_url; OpenAlex follows with an
    OA mirror. Canonical record stays ACM but inherits the OpenAlex pdf_url."""
    acm = _paper(
        source="acm", source_id="acm-1", doi="10.1145/x",
        pdf_url=None, url="https://dl.acm.org/doi/10.1145/x",
    )
    openalex = _paper(
        source="openalex", source_id="W1", doi="10.1145/x",
        pdf_url="https://author.example.com/preprint.pdf",
        url="https://openalex.org/W1",
    )
    out = dedupe([acm, openalex])
    assert len(out) == 1
    assert out[0].source == "acm"  # canonical (first) source preserved
    assert out[0].url == "https://dl.acm.org/doi/10.1145/x"  # canonical URL
    assert out[0].pdf_url == "https://author.example.com/preprint.pdf"  # merged


def test_dedupe_does_not_overwrite_populated_fields():
    """Canonical fields must NEVER be replaced by a later duplicate's values."""
    canonical = _paper(
        doi="10.1/a", pdf_url="https://canonical.example/p.pdf", venue="NeurIPS",
        citation_count=100, abstract="canonical abstract",
    )
    other = _paper(
        doi="10.1/a", pdf_url="https://other.example/p.pdf", venue="Other",
        citation_count=999, abstract="other abstract",
    )
    out = dedupe([canonical, other])
    assert len(out) == 1
    assert out[0].pdf_url == "https://canonical.example/p.pdf"
    assert out[0].venue == "NeurIPS"
    assert out[0].citation_count == 100
    assert out[0].abstract == "canonical abstract"


def test_dedupe_merges_multiple_optional_fields():
    canonical = _paper(
        doi="10.1/a", title="Same",
        venue=None, citation_count=None, abstract="", year=None,
    )
    other = _paper(
        doi="10.1/a", title="Same",
        venue="ICML", citation_count=42, abstract="filled in", year=2024,
    )
    out = dedupe([canonical, other])
    assert out[0].venue == "ICML"
    assert out[0].citation_count == 42
    assert out[0].abstract == "filled in"
    assert out[0].year == 2024


def test_dedupe_collapses_title_punctuation_and_case():
    """Same paper from two sources differing only by trailing period / case
    collapses to one record (no DOI / arXiv ID to key on)."""
    a = _paper(source_id="1", title="Attention Is All You Need",
               authors=("Vaswani",), year=2017)
    b = _paper(source_id="2", title="Attention is all you need.",
               authors=("Vaswani",), year=2017)
    assert len(dedupe([a, b])) == 1


def test_dedupe_collapses_arxiv_versions():
    """Two arXiv versions of the same paper (v1, v2) are one paper."""
    v1 = _paper(source_id="1", arxiv_id="2401.00001v1")
    v2 = _paper(source_id="2", arxiv_id="2401.00001v2")
    assert len(dedupe([v1, v2])) == 1


def test_dedupe_collapses_author_name_formats():
    """Same DOI-less paper whose first author arrives in three different name
    formats across sources collapses to one record (surname canonicalisation)."""
    a = _paper(source_id="1", title="On Method X",
               authors=("Ashish Vaswani",), year=2020)
    b = _paper(source_id="2", title="On Method X",
               authors=("Vaswani, Ashish",), year=2020)
    c = _paper(source_id="3", title="On Method X",
               authors=("A. Vaswani",), year=2020)
    assert len(dedupe([a, b, c])) == 1


def test_dedupe_distinguishes_different_surnames():
    """Different first-author surnames (same title/year) stay distinct — the
    surname canonicalisation must not over-merge."""
    a = _paper(source_id="1", title="Common Title", authors=("Alice Smith",), year=2020)
    b = _paper(source_id="2", title="Common Title", authors=("Bob Jones",), year=2020)
    assert len(dedupe([a, b])) == 2


def test_rank_prefers_recent_papers():
    old = _paper(source_id="old", year=2010)
    new = _paper(source_id="new", year=2024)
    ordered = rank([old, new], current_year=2025)
    assert ordered[0].source_id == "new"


def test_rank_uses_citation_count_as_tie_breaker():
    a = _paper(source_id="a", year=2024, citation_count=5)
    b = _paper(source_id="b", year=2024, citation_count=500)
    ordered = rank([a, b], current_year=2025)
    assert ordered[0].source_id == "b"


def test_rank_handles_missing_year():
    a = _paper(source_id="a", year=None)
    b = _paper(source_id="b", year=2024)
    ordered = rank([a, b], current_year=2025)
    assert ordered[0].source_id == "b"


def test_rank_relevance_outranks_off_topic_high_citation():
    """An on-topic paper beats an off-topic, far-more-cited one — relevance is
    the dominant signal (the failure this whole feature prevents)."""
    on_topic = _paper(
        source_id="on", title="A Survey of Transformer Attention",
        year=2024, citation_count=10,
    )
    off_topic = _paper(
        source_id="off", title="Deep Residual Learning for Image Recognition",
        year=2024, citation_count=100_000,
    )
    ordered = rank(
        [off_topic, on_topic], keywords="transformer attention", current_year=2025
    )
    assert ordered[0].source_id == "on"


def test_rank_title_match_outranks_abstract_match():
    """A query term in the title weighs more than the same term in the abstract."""
    title_match = _paper(
        source_id="title", title="Transformer Attention Models",
        abstract="", year=2024,
    )
    abstract_match = _paper(
        source_id="abs", title="A New Method",
        abstract="we study transformer attention", year=2024,
    )
    ordered = rank(
        [abstract_match, title_match],
        keywords="transformer attention", current_year=2025,
    )
    assert ordered[0].source_id == "title"


def test_rank_without_keywords_ignores_relevance():
    """No keywords -> relevance axis off; back-compat recency+citation only."""
    on_topic_but_old = _paper(
        source_id="on", title="transformer attention", year=2010, citation_count=1,
    )
    recent_unrelated = _paper(
        source_id="recent", title="unrelated topic", year=2024, citation_count=1,
    )
    ordered = rank([on_topic_but_old, recent_unrelated], current_year=2025)
    assert ordered[0].source_id == "recent"  # recency wins; title text ignored


def test_rank_short_query_terms_are_dropped():
    """Stop-word-ish terms (<3 chars) don't create spurious matches."""
    # "a"/"of" must not match; only "llm" (3 chars) counts.
    hit = _paper(source_id="hit", title="On LLM agents", year=2024)
    miss = _paper(source_id="miss", title="A study of birds", year=2024)
    ordered = rank([miss, hit], keywords="a llm of", current_year=2025)
    assert ordered[0].source_id == "hit"


def test_rank_stemming_matches_plural():
    """A singular query term matches a plural/inflected title — same concept.

    Without stemming, "transformer" would miss "Transformers" entirely and the
    on-topic paper would sort below an unrelated one on recency/citation alone.
    """
    hit = _paper(source_id="hit", title="Transformers in Vision", year=2024)
    miss = _paper(source_id="miss", title="Graph Theory Basics", year=2024)
    ordered = rank([miss, hit], keywords="transformer", current_year=2025)
    assert ordered[0].source_id == "hit"


def test_rank_phrase_adjacency_bonus():
    """Two titles share all query words, but the one where they appear ADJACENT
    (a real phrase) ranks above the one where they are scattered."""
    phrase = _paper(
        source_id="phrase", title="Retrieval-Augmented Generation", year=2024,
    )
    scattered = _paper(
        source_id="scattered", title="Generation Augmented by Retrieval", year=2024,
    )
    ordered = rank(
        [scattered, phrase],
        keywords="retrieval augmented generation", current_year=2025,
    )
    assert ordered[0].source_id == "phrase"


def test_rank_synonym_acronym_expands():
    """A query for an acronym matches a title that only writes the long form."""
    hit = _paper(
        source_id="hit", title="A Survey of Large Language Models", year=2024,
    )
    miss = _paper(source_id="miss", title="Image Segmentation Methods", year=2024)
    ordered = rank([miss, hit], keywords="llm", current_year=2025)
    assert ordered[0].source_id == "hit"


def test_rank_synonym_does_not_overmatch_shared_word():
    """A lone shared word ("language") must NOT inject an unrelated acronym:
    a query for "nlp" must not match a pure "language model" title."""
    lang_only = _paper(
        source_id="lang", title="Sign Language Recognition", year=2024,
    )
    nlp_paper = _paper(
        source_id="nlp", title="Natural Language Processing Advances", year=2024,
    )
    ordered = rank([lang_only, nlp_paper], keywords="nlp", current_year=2025)
    assert ordered[0].source_id == "nlp"


def test_rank_cjk_query_has_relevance():
    """A Chinese-keyword search gets a real relevance signal (CJK bigrams), so an
    on-topic Chinese title beats an off-topic one rather than tying on recency."""
    hit = _paper(source_id="hit", title="視覺注意力機制研究", year=2024)
    miss = _paper(source_id="miss", title="區塊鏈技術概論", year=2024)
    ordered = rank([miss, hit], keywords="注意力機制", current_year=2025)
    assert ordered[0].source_id == "hit"


def test_rank_stemming_does_not_overstrip():
    """The min-stem-length guard keeps short words intact: "ring" must stay
    "ring" (not collapse to "r"), so it still matches a "Ring ..." title and
    "Rendering" correctly stems to "render" without colliding."""
    hit = _paper(source_id="hit", title="Ring Signatures", year=2024)
    miss = _paper(source_id="miss", title="Rendering Pipelines", year=2024)
    ordered = rank([miss, hit], keywords="ring", current_year=2025)
    assert ordered[0].source_id == "hit"


# --- Golden-query regression set -------------------------------------------
# A realistic candidate pool ranked end-to-end (relevance + recency + citation
# together), so a future change to the weights / stemmer / synonyms that quietly
# degrades real-world ranking is caught — not just the isolated-axis unit tests
# above. The invariant each case pins: the on-topic paper takes the #1 slot even
# though the pool contains a 180k-citation OFF-topic paper (resnet) — i.e.
# relevance still dominates raw citation count. (Below #1, the off-topic paper
# may legitimately fill a slot on a query where only one paper is on-topic; that
# is correct recency+citation behaviour, so the test pins #1, not the whole top
# 3.) The gaps are wide enough to survive small weight retunes; if one breaks,
# the ranking changed materially and the expectation should be re-justified.
def _golden_pool() -> list[Paper]:
    return [
        _paper(source_id="attn", title="Attention Is All You Need",
               year=2017, citation_count=90000),
        _paper(source_id="xformer_survey", title="A Survey of Transformer Architectures",
               year=2024, citation_count=120),
        _paper(source_id="resnet", title="Deep Residual Learning for Image Recognition",
               year=2016, citation_count=180000),
        _paper(source_id="rag",
               title="Retrieval-Augmented Generation for Knowledge-Intensive NLP",
               year=2020, citation_count=5000),
        _paper(source_id="gpt3", title="Large Language Models are Few-Shot Learners",
               year=2020, citation_count=30000),
        _paper(source_id="gnn", title="Graph Neural Networks: A Comprehensive Review",
               year=2021, citation_count=800),
    ]


@pytest.mark.parametrize(
    ("query", "expected_top"),
    [
        # Plural/inflected title match (stemming): "transformer" -> "Transformer".
        ("transformer", "xformer_survey"),
        # Exact multi-word phrase wins on adjacency + full overlap.
        ("retrieval augmented generation", "rag"),
        # Acronym synonym: "llm" surfaces the long-form "Large Language Models".
        ("llm", "gpt3"),
        # Plural in title ("Networks") + phrase; on-topic beats the 180k-cite resnet.
        ("graph neural network", "gnn"),
    ],
)
def test_rank_golden_queries(query, expected_top):
    ordered = rank(_golden_pool(), keywords=query, current_year=2026)
    top_ids = [p.source_id for p in ordered]
    assert top_ids[0] == expected_top, f"{query!r} -> {top_ids[:3]}"
    # Relevance dominance: the on-topic paper outranks the 180k-citation
    # off-topic paper, even with a ~400x citation disadvantage in some cases.
    assert top_ids.index(expected_top) < top_ids.index("resnet"), (
        f"off-topic resnet outranked {expected_top!r} for {query!r}: {top_ids}"
    )
