"""Tests for the identifier parser."""

from __future__ import annotations

import dataclasses

import pytest

from autopapertoppt.core.identifiers import (
    IdentifierKind,
    PaperIdentifier,
    parse_identifier,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2401.08741", "2401.08741"),
        ("2401.08741v2", "2401.08741"),
        ("arXiv:2401.08741", "2401.08741"),
        ("arxiv: 2401.08741v3", "2401.08741"),
        ("https://arxiv.org/abs/2401.08741", "2401.08741"),
        ("https://arxiv.org/abs/2401.08741v1", "2401.08741"),
        ("https://arxiv.org/pdf/2401.08741v1", "2401.08741"),
        ("https://arxiv.org/pdf/2401.08741v1.pdf", "2401.08741"),
        ("https://www.arxiv.org/abs/2401.08741", "2401.08741"),
        ("cs.LG/0001001", "cs.LG/0001001"),
    ],
)
def test_parse_arxiv_variants(raw: str, expected: str):
    parsed = parse_identifier(raw)
    assert parsed.kind is IdentifierKind.ARXIV
    assert parsed.value == expected
    assert parsed.preferred_source == "arxiv"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("10.1234/example.99999", "10.1234/example.99999"),
        ("doi:10.1234/example", "10.1234/example"),
        ("DOI: 10.1234/example", "10.1234/example"),
        ("https://doi.org/10.1234/example", "10.1234/example"),
        ("https://dx.doi.org/10.1234/example", "10.1234/example"),
    ],
)
def test_parse_doi_variants(raw: str, expected: str):
    parsed = parse_identifier(raw)
    assert parsed.kind is IdentifierKind.DOI
    assert parsed.value == expected


def test_doi_routes_to_semantic_scholar():
    assert parse_identifier("10.1234/example").preferred_source == "semantic_scholar"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("pmid:34567890", "34567890"),
        ("PMID: 12345678", "12345678"),
        ("34567890", "34567890"),
        ("https://pubmed.ncbi.nlm.nih.gov/12345678/", "12345678"),
        ("https://pubmed.ncbi.nlm.nih.gov/12345678", "12345678"),
    ],
)
def test_parse_pmid_variants(raw: str, expected: str):
    parsed = parse_identifier(raw)
    assert parsed.kind is IdentifierKind.PMID
    assert parsed.value == expected
    assert parsed.preferred_source == "pubmed"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://ieeexplore.ieee.org/document/10965643", "10965643"),
        ("https://ieeexplore.ieee.org/abstract/document/10965643", "10965643"),
        ("https://www.ieeexplore.ieee.org/document/10965643/", "10965643"),
        ("ieee:10965643", "10965643"),
    ],
)
def test_parse_ieee_variants(raw: str, expected: str):
    parsed = parse_identifier(raw)
    assert parsed.kind is IdentifierKind.IEEE
    assert parsed.value == expected
    assert parsed.preferred_source == "ieee"


def test_parse_rejects_empty():
    with pytest.raises(ValueError):
        parse_identifier("")
    with pytest.raises(ValueError):
        parse_identifier("   ")


def test_parse_rejects_garbage():
    with pytest.raises(ValueError, match="could not classify"):
        parse_identifier("not an identifier")


def test_paper_identifier_is_frozen():
    parsed = parse_identifier("2401.08741")
    with pytest.raises((AttributeError, TypeError, dataclasses.FrozenInstanceError)):
        parsed.value = "tampered"  # type: ignore[misc]
    assert isinstance(parsed, PaperIdentifier)
