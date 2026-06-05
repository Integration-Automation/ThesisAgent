"""Tests for core models (happy path, edge cases, round-trip)."""

from __future__ import annotations

import pytest

from thesisagents.core.models import ExportOptions, Paper, Query


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
