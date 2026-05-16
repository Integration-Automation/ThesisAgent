"""Simple relevance + recency + citation ranking.

The signal is intentionally lightweight — sources already return roughly
relevance-sorted lists. We just stable-merge them and tie-break with recency
and citation count.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from autopapertoppt.core.models import Paper

_CURRENT_YEAR_FALLBACK = 2026


def rank(papers: Iterable[Paper], current_year: int | None = None) -> list[Paper]:
    """Stable sort by descending composite score."""
    year_base = current_year or _CURRENT_YEAR_FALLBACK
    return sorted(
        papers,
        key=lambda paper: _score(paper, year_base),
        reverse=True,
    )


def _score(paper: Paper, current_year: int) -> float:
    recency = _recency_score(paper.year, current_year)
    citation = _citation_score(paper.citation_count)
    return recency + citation


def _recency_score(year: int | None, current_year: int) -> float:
    if year is None:
        return 0.0
    age = max(0, current_year - year)
    return math.exp(-age / 5.0)


def _citation_score(citations: int | None) -> float:
    if citations is None or citations <= 0:
        return 0.0
    return math.log10(citations + 1.0)
