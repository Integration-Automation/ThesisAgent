"""Heuristic PDF metadata extractor."""

from __future__ import annotations

from thesisagents.intelligence.pdf_metadata import (
    ExtractedMetadata,
    extract_metadata,
)


def test_empty_text_returns_empty_metadata():
    assert extract_metadata("") == ExtractedMetadata()


def test_extracts_arxiv_id_from_header():
    text = (
        "Some Title\nFirst Author, Second Author\n"
        "arXiv:2401.08741v3 [cs.CL] 12 Jan 2024\n\nAbstract\nWe propose ..."
    )
    md = extract_metadata(text)
    assert md.arxiv_id == "2401.08741"


def test_extracts_arxiv_id_from_url():
    text = "See https://arxiv.org/abs/2504.20984v3 for the preprint."
    assert extract_metadata(text).arxiv_id == "2504.20984"


def test_extracts_doi():
    text = "Published in NDSS 2026. DOI: 10.14722/ndss.2026.123456."
    assert extract_metadata(text).doi == "10.14722/ndss.2026.123456"


def test_extracts_year_in_realistic_range():
    text = "Foo (2025) Some Title\nAuthor A, Author B"
    assert extract_metadata(text).year == 2025


def test_extracts_abstract_anchored_on_header():
    text = (
        "Some Paper Title\n"
        "Alice Smith, Bob Jones\n"
        "Some University\n\n"
        "Abstract\n"
        "We design a novel technique for X. It outperforms Y by Z%.\n\n"
        "1. Introduction\n"
        "Recent advances ..."
    )
    md = extract_metadata(text)
    assert md.abstract is not None
    assert md.abstract.startswith("We design")
    assert "Introduction" not in md.abstract
    assert "Recent advances" not in md.abstract


def test_extracts_abstract_with_chinese_header():
    text = (
        "論文標題\n"
        "張某, 李某\n\n"
        "摘要\n"
        "本文提出一個新方法。實驗結果顯示 X% 的提升。\n\n"
        "1. 介紹\n"
        "近年來 ..."
    )
    md = extract_metadata(text)
    assert md.abstract is not None
    assert md.abstract.startswith("本文提出一個新方法")


def test_extracts_title_and_authors():
    text = (
        "Adversarial Probes Against Large Language Models\n"
        "Alice Andersson, Bob Bertelsen, Carol Chen\n"
        "Department of Computer Science, Some University\n"
        "alice@example.edu\n\n"
        "Abstract\n"
        "We study ..."
    )
    md = extract_metadata(text)
    assert md.title == "Adversarial Probes Against Large Language Models"
    assert md.authors == ("Alice Andersson", "Bob Bertelsen", "Carol Chen")


def test_title_extraction_ignores_arxiv_boilerplate():
    text = (
        "arXiv:2401.08741v3 [cs.CL] 12 Jan 2024\n"
        "Adversarial Probes Against LLMs\n"
        "Alice Smith, Bob Jones\n"
        "MIT\n\n"
        "Abstract\nWe ..."
    )
    md = extract_metadata(text)
    assert md.title == "Adversarial Probes Against LLMs"


def test_too_short_title_is_rejected():
    text = "Hi\nAlice Smith, Bob Jones\n\nAbstract\nx"
    assert extract_metadata(text).title is None


def test_author_footnote_markers_stripped():
    text = (
        "Title of Paper\n"
        "Alice Smith*, Bob Jones†, Carol Chen‡\n"
        "Affiliation\n\n"
        "Abstract\nWe ..."
    )
    md = extract_metadata(text)
    assert md.authors == ("Alice Smith", "Bob Jones", "Carol Chen")


def test_authors_with_and_separator():
    text = (
        "A Good Paper\n"
        "Alice Smith and Bob Jones\n"
        "Department of CS\n\n"
        "Abstract\nWe ..."
    )
    md = extract_metadata(text)
    assert md.authors == ("Alice Smith", "Bob Jones")


def test_emails_terminate_author_block():
    text = (
        "Title Here\n"
        "Alice Smith, Bob Jones\n"
        "alice@example.com, bob@example.com\n\n"
        "Abstract\nWe ..."
    )
    md = extract_metadata(text)
    assert md.authors == ("Alice Smith", "Bob Jones")


def test_pathological_no_abstract_header_returns_none_abstract():
    text = "Just a title\nAlice Smith, Bob Jones\nSome content here."
    assert extract_metadata(text).abstract is None


def test_year_pattern_rejects_phone_numbers():
    """Phone numbers can have 4-digit substrings — make sure we don't pick e.g. 0123."""
    text = "Some Paper Title\nPhone: 0123-4567\nPublished 2024"
    assert extract_metadata(text).year == 2024


def test_flat_text_with_unicode_asterisk_footnotes():
    """Real PDFs (Li et al. NDSS 2026 layout): pypdf flattens to a single
    line, authors carry U+2217 ASTERISK OPERATOR footnotes, affiliation
    is "Northeastern University" + ``{...}@...`` email block."""
    text = (
        "ACE: A Security Architecture for LLM-Integrated App Systems "
        "Evan Li ∗, Tushin Mallick ∗, Evan Rose ∗, "
        "William Robertson, Alina Oprea, and Cristina Nita-Rotaru "
        "Northeastern University {li.evan1, mallick.tu, rose.ev}@northeastern.edu "
        "Abstract—LLM-integrated app systems extend ..."
    )
    md = extract_metadata(text)
    assert md.title == "ACE: A Security Architecture for LLM-Integrated App Systems"
    assert "Evan Li" in md.authors
    assert "Tushin Mallick" in md.authors
    assert "Cristina Nita-Rotaru" in md.authors
    assert all(not a.startswith("and ") for a in md.authors)


def test_flat_text_with_numeric_footnotes():
    """Wen et al. layout: ``Wen Cheng1, Ke Sun2, 3, ... Wei Wang1 1State Key Laboratory ...``"""
    text = (
        "Security Attacks on LLM-based Code Completion Tools "
        "Wen Cheng1, Ke Sun2, 3, Xinyu Zhang2, Wei Wang1 "
        "1State Key Laboratory for Novel Software Technology, Nanjing University "
        "Abstract The rapid development ..."
    )
    md = extract_metadata(text)
    assert md.title == "Security Attacks on LLM-based Code Completion Tools"
    assert "Wen Cheng" in md.authors
    assert "Ke Sun" in md.authors
    assert "Xinyu Zhang" in md.authors
    assert "Wei Wang" in md.authors
    # The "1State" affiliation footnote MUST NOT leak into an author name.
    assert all("State" not in a for a in md.authors)


def test_flat_text_strips_arxiv_preamble_from_title():
    """McClearn layout: arXiv stamp is prepended in pypdf output."""
    text = (
        "arXiv:2506.09580v1  [cs.CR]  11 Jun 2025 "
        "The Everyday Security of Living with Conflict "
        "Jessica McClearn Royal Holloway, University of London "
        "Abstract—When 'cyber' is used as a prefix ..."
    )
    md = extract_metadata(text)
    assert md.title is not None
    assert not md.title.lower().startswith("arxiv")
    assert "Everyday Security" in md.title
    assert md.arxiv_id == "2506.09580"
