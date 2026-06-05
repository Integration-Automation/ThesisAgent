"""Tests for dedup and ranking."""

from __future__ import annotations

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
