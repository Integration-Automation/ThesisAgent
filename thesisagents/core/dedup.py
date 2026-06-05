"""Hash-based de-duplication with field-merge across sources.

When two sources return the same paper (same DOI / arXiv ID / fuzzy
title-hash), the earlier source's record is the canonical one — its
``source``, ``source_id``, and ``url`` win so users searching with
``arxiv`` first keep the arXiv URL. But for *optional* fields that may
be missing on one source and present on another (``pdf_url``, ``doi``,
``arxiv_id``, ``venue``, ``citation_count``, ``abstract``), the merged
record takes the first non-empty value across all duplicates.

This matters for the PDF download flow: ACM/Crossref records don't
carry a ``pdf_url`` field but OpenAlex usually has the OA mirror under
``best_oa_location.pdf_url``. Pre-merge, a first-wins ACM record would
drop OpenAlex's PDF link and the downloader would skip the paper with
``no_pdf_url``. Post-merge, the ACM record keeps its canonical
metadata but inherits the OpenAlex PDF URL.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from thesisagents.core.models import Paper


def dedupe(papers: Iterable[Paper]) -> list[Paper]:
    """Collapse duplicate Papers, merging optional fields across sources.

    Iteration order matters: the first occurrence of each dedup-key is
    treated as the canonical record; later duplicates contribute only
    their non-empty optional fields. Callers concatenate sources in the
    user-supplied ``--source`` order so the canonical record reflects
    the user's source preference.
    """
    by_key: dict[str, Paper] = {}
    order: list[str] = []
    for paper in papers:
        key = paper.dedup_key()
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = paper
            order.append(key)
            continue
        by_key[key] = _merge(existing, paper)
    return [by_key[k] for k in order]


# Fields backfilled across duplicates. ``source`` / ``source_id`` / ``url`` /
# ``title`` are intentionally excluded — they stay with the canonical record
# so links and citation handling stay stable across runs.
_MERGEABLE_FIELDS: tuple[str, ...] = (
    "pdf_url", "doi", "arxiv_id", "venue", "citation_count",
    "year", "abstract", "authors", "summary",
)


def _is_missing(value: object) -> bool:
    """``None`` and empty strings/tuples count as missing for merge purposes."""
    if value is None:
        return True
    if isinstance(value, (str, tuple)):
        return len(value) == 0
    return False


def _merge(canonical: Paper, other: Paper) -> Paper:
    """Return a copy of ``canonical`` with optional fields backfilled from ``other``.

    Only fills fields where ``canonical`` is missing data — never
    overwrites a populated field. ``source`` / ``source_id`` / ``url`` /
    ``title`` / ``authors`` stay with the canonical record so links and
    citation handling stay stable.
    """
    updates: dict[str, object] = {}
    for name in _MERGEABLE_FIELDS:
        canonical_value = getattr(canonical, name)
        other_value = getattr(other, name)
        if _is_missing(canonical_value) and not _is_missing(other_value):
            updates[name] = other_value
    if not updates:
        return canonical
    return replace(canonical, **updates)
