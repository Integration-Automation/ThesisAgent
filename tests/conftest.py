"""Shared fixtures + sys.path injection so source plugins import like packages."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SOURCES = _ROOT / "sources"


def _ensure_sources_on_path() -> None:
    sources_dir = str(_SOURCES)
    if sources_dir not in sys.path:
        sys.path.insert(0, sources_dir)


_ensure_sources_on_path()


@pytest.fixture()
def sample_papers():
    from autopapertoppt.core.models import Paper

    return [
        Paper(
            source="arxiv",
            source_id="2401.00001v1",
            title="Sample Paper on Attention",
            authors=("Alice Anderson", "Bob Brown"),
            year=2024,
            venue=None,
            abstract="A short abstract about attention mechanisms.",
            url="https://arxiv.org/abs/2401.00001v1",
            arxiv_id="2401.00001",
            pdf_url="https://arxiv.org/pdf/2401.00001v1",
        ),
        Paper(
            source="arxiv",
            source_id="2305.99999v2",
            title="Second Paper with Special & Chars",
            authors=("Carol Chen",),
            year=2023,
            venue="NeurIPS 2023",
            abstract="Second abstract. Includes math like $x^2$ and curly {braces}.",
            url="https://arxiv.org/abs/2305.99999v2",
            doi="10.1234/example.99999",
            arxiv_id="2305.99999",
        ),
    ]


@pytest.fixture()
def arxiv_fixture_path():
    return Path(__file__).resolve().parent / "fixtures" / "arxiv" / "attention.xml"
