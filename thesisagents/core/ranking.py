"""Relevance + recency + citation ranking.

Each source returns a roughly relevance-sorted list, but de-duplication merges
those lists across sources and discards each source's local ordering. Without an
explicit relevance signal the merged list would sort purely by recency +
citation — which buries a highly-relevant older paper under a recent, more-cited,
*off-topic* one. (Concrete failure this prevents: a search for "transformer
attention" that surfaces a 100k-citation ResNet paper above an on-topic survey,
simply because ResNet is cited more.)

So each paper is scored on three axes and stable-sorted by the sum:

* **relevance** (dominant) — overlap between the query keywords and the paper's
  title (weighted heavily) + abstract (weighted lightly). Research starts from
  "is this on my topic?", so an on-topic paper should beat an off-topic one even
  when the off-topic one is older-and-more-cited.
* **recency** — exponential decay over paper age (~5-year scale).
* **citation** — ``log10`` of the citation count (diminishing returns), then
  damped by ``_CITATION_WEIGHT`` so a huge citation count is a strong tie-break
  but cannot by itself outrank an on-topic title.

``keywords`` is optional: callers that rank a single fetched paper (no query, e.g.
``run_single_paper``) pass ``None`` and keep the pre-relevance recency+citation
behaviour.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable

from thesisagents.core.models import Paper

_CURRENT_YEAR_FALLBACK = 2026

# Relevance weights. Title overlap dominates; abstract overlap is a softer
# secondary signal. Tuned together with _CITATION_WEIGHT so that a full
# title match (= _TITLE_WEIGHT) outranks even a ~100k-citation off-topic paper
# (citation term ≈ _CITATION_WEIGHT * log10(1e5) = 0.4 * 5 = 2.0 < 3.0).
_TITLE_WEIGHT = 3.0
_ABSTRACT_WEIGHT = 0.6
# Damping on the log10 citation term. Keeps "most-cited" a meaningful tie-break
# among similarly-relevant papers without letting it swamp the topic signal.
_CITATION_WEIGHT = 0.4
# Query/title tokens shorter than this are dropped as stop-word-ish noise
# ("a", "of", "is", "the"). 3 keeps useful short terms like "llm", "rag", "gan".
_MIN_TERM_LEN = 3

_WORD_RE = re.compile(r"[a-z0-9]+")


def rank(
    papers: Iterable[Paper],
    keywords: str | None = None,
    current_year: int | None = None,
) -> list[Paper]:
    """Stable sort by descending composite score (relevance + recency + citation).

    ``keywords`` is the raw query string; when given, papers whose title /
    abstract share terms with it rank higher. ``None`` disables the relevance
    axis (single-paper / query-less callers).
    """
    year_base = current_year or _CURRENT_YEAR_FALLBACK
    terms = _terms(keywords) if keywords else frozenset()
    return sorted(
        papers,
        key=lambda paper: _score(paper, year_base, terms),
        reverse=True,
    )


def _score(paper: Paper, current_year: int, terms: frozenset[str]) -> float:
    return (
        _relevance_score(paper, terms)
        + _recency_score(paper.year, current_year)
        + _citation_score(paper.citation_count)
    )


def _terms(text: str) -> frozenset[str]:
    """Lowercase alphanumeric tokens of length >= ``_MIN_TERM_LEN``."""
    return frozenset(w for w in _WORD_RE.findall(text.lower()) if len(w) >= _MIN_TERM_LEN)


def _relevance_score(paper: Paper, terms: frozenset[str]) -> float:
    """Fraction of query terms appearing in title / abstract, title-weighted.

    Range ``[0, _TITLE_WEIGHT + _ABSTRACT_WEIGHT]``. ``0.0`` when no query terms
    were supplied, so the score reduces to recency + citation.
    """
    if not terms:
        return 0.0
    title_hit = len(terms & _terms(paper.title)) / len(terms)
    abstract_hit = len(terms & _terms(paper.abstract)) / len(terms)
    return title_hit * _TITLE_WEIGHT + abstract_hit * _ABSTRACT_WEIGHT


def _recency_score(year: int | None, current_year: int) -> float:
    if year is None:
        return 0.0
    age = max(0, current_year - year)
    return math.exp(-age / 5.0)


def _citation_score(citations: int | None) -> float:
    if citations is None or citations <= 0:
        return 0.0
    return _CITATION_WEIGHT * math.log10(citations + 1.0)
