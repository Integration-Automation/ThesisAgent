"""Tests for core models (happy path, edge cases, round-trip)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from thesisagents.core.exceptions import ThesisAgentsError
from thesisagents.core.models import ExportOptions, FieldProvenance, Paper, Query


def test_paper_dedup_key_prefers_doi():
    paper = Paper(
        source="arxiv",
        source_id="1",
        title="T",
        authors=("A",),
        year=2024,
        venue=None,
        abstract="",
        url="https://example.com",
        doi="10.1/abc",
        arxiv_id="1234.56789",
    )
    assert paper.dedup_key() == "doi:10.1/abc"


def test_paper_dedup_key_falls_back_to_arxiv_then_hash():
    no_doi = Paper(
        source="arxiv", source_id="1", title="T", authors=("A",), year=2024,
        venue=None, abstract="", url="https://example.com",
        arxiv_id="1234.56789",
    )
    assert no_doi.dedup_key() == "arxiv:1234.56789"

    no_ids = Paper(
        source="x", source_id="1", title="Hello world", authors=("Alice",),
        year=2024, venue=None, abstract="", url="https://example.com",
    )
    key = no_ids.dedup_key()
    assert key.startswith("hash:")


def test_paper_bibtex_key_is_stable():
    paper = Paper(
        source="arxiv", source_id="1",
        title="Attention Is All You Need",
        authors=("Ashish Vaswani", "Noam Shazeer"),
        year=2017, venue=None, abstract="",
        url="https://arxiv.org/abs/1706.03762",
    )
    assert paper.bibtex_key() == "vaswani2017attention"


def test_paper_short_abstract_truncates():
    long_text = "word " * 1000
    paper = Paper(
        source="x", source_id="1", title="T", authors=(), year=None,
        venue=None, abstract=long_text, url="https://example.com",
    )
    short = paper.short_abstract()
    assert short.endswith("…")
    assert len(short) <= 1200


def test_paper_round_trip():
    paper = Paper(
        source="arxiv", source_id="1", title="T", authors=("Alice",),
        year=2024, venue="NeurIPS", abstract="abs", url="https://example.com",
        doi="10.1/a", arxiv_id="1234.5678", citation_count=10,
        pdf_url="https://example.com/p.pdf",
        provenance=(FieldProvenance("pdf_url", "openalex", "W1"),),
    )
    assert Paper.from_dict(paper.to_dict()) == paper


def test_query_rejects_empty_keywords():
    with pytest.raises(ValueError, match="keywords"):
        Query(keywords="   ", sources=("arxiv",))


def test_query_rejects_no_sources():
    with pytest.raises(ValueError, match="source"):
        Query(keywords="x", sources=())


def test_query_rejects_inverted_year_range():
    with pytest.raises(ValueError, match="year_from"):
        Query(keywords="x", sources=("arxiv",), year_from=2024, year_to=2020)


def test_query_rejects_out_of_range_max():
    with pytest.raises(ValueError, match="max_results"):
        Query(keywords="x", sources=("arxiv",), max_results=0)
    with pytest.raises(ValueError, match="max_results"):
        Query(keywords="x", sources=("arxiv",), max_results=10_000)


def test_export_options_rejects_empty_formats():
    with pytest.raises(ValueError, match="format"):
        ExportOptions(formats=(), out_dir=".")


def test_bibtex_key_survives_blank_author():
    """A blank author string must not IndexError.

    ``bibtex_key`` is called from the PDF downloader, the OA resolver and the
    per-paper deck emitter, so ``"".split()[-1]`` used to abort a whole run
    over one empty author cell (easy to produce from an MCP ``export`` payload
    or a scrape whose author field came back empty).
    """
    paper = Paper(
        source="s", source_id="1", title="On Widgets", authors=("",),
        year=2024, venue=None, abstract="", url="https://example.com",
    )
    assert paper.bibtex_key() == "anon2024widgets"
    whitespace = replace(paper, authors=("   ",))
    assert whitespace.bibtex_key() == "anon2024widgets"


def test_from_dict_names_the_missing_required_fields():
    """A malformed paper dict raises a named error, not a bare KeyError.

    The documented LLM-as-agent path hands hand-written dicts to the MCP
    ``export`` / ``download_pdfs`` tools; an omitted ``url`` used to surface as
    ``KeyError: 'url'`` with no hint about what to fix.
    """
    with pytest.raises(ThesisAgentsError, match="source_id, title, url"):
        Paper.from_dict({"source": "arxiv"})


def test_from_dict_tolerates_half_written_provenance():
    """Provenance is bookkeeping — a partial entry must not sink the paper."""
    paper = Paper.from_dict({
        "source": "arxiv", "source_id": "1", "title": "T", "url": "https://x",
        "provenance": [{"field": "pdf_url"}, "not-a-dict"],
    })
    assert paper.provenance == (FieldProvenance("pdf_url", "", ""),)


def test_clamp_max_results_keeps_synthetic_queries_legal():
    """Synthetic queries built purely to satisfy PaperCollection must not
    explode on a paper count outside the per-source page-size range."""
    assert Query.clamp_max_results(0) == 1
    assert Query.clamp_max_results(25) == 25
    assert Query.clamp_max_results(250) == 200
    # The clamped value is accepted by the Query validator.
    Query(keywords="x", sources=("arxiv",), max_results=Query.clamp_max_results(250))
