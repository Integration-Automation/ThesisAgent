"""Tests for query normalisation."""

from __future__ import annotations

import pytest

from autopapertoppt.core.query import normalize_query


def test_normalize_strips_whitespace_and_collapses():
    assert normalize_query("  diffusion   models  ") == "diffusion models"


def test_normalize_strips_control_chars():
    raw = "hello\x00world\x1f!"
    assert normalize_query(raw) == "hello world !"


def test_normalize_rejects_empty():
    with pytest.raises(ValueError):
        normalize_query("")
    with pytest.raises(ValueError):
        normalize_query("   ")


def test_normalize_caps_length():
    raw = "x " * 1000
    out = normalize_query(raw)
    assert len(out) <= 256


def test_normalize_nfc():
    raw = "café"
    assert normalize_query(raw) == "café"
