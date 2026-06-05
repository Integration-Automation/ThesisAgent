"""Parse a recorded arXiv Atom feed and assert the normalised Paper output."""

from __future__ import annotations

from thesisagents.sources.arxiv.parser import parse_atom_feed


def test_parse_recorded_attention_feed(arxiv_fixture_path):
    xml_text = arxiv_fixture_path.read_text(encoding="utf-8")
    papers = parse_atom_feed(xml_text)
    assert len(papers) == 2

    first = papers[0]
    assert first.title == "Attention Is All You Need"
    assert first.year == 2017
    assert first.arxiv_id == "1706.03762"
    assert first.authors[0] == "Ashish Vaswani"
    assert first.pdf_url == "http://arxiv.org/pdf/1706.03762v5"
    assert first.url.endswith("1706.03762v5")
    assert first.source == "arxiv"
    assert first.doi is None

    second = papers[1]
    assert second.arxiv_id == "2401.04088"
    assert second.year == 2024
    assert second.venue == "Example Journal of ML"
    assert second.doi == "10.1234/example.04088"


def test_parse_empty_feed():
    empty = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
    )
    assert parse_atom_feed(empty) == []


def test_parse_invalid_xml_raises():
    import pytest

    from thesisagents.core.exceptions import ParseError

    with pytest.raises(ParseError):
        parse_atom_feed("<not><valid>")
