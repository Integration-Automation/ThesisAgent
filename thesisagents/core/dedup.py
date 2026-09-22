"""Multi-key de-duplication with field-merge across sources.

When two sources return the same paper, the earlier source's record is the
canonical one — its ``source``, ``source_id``, and ``url`` win so users
searching with ``arxiv`` first keep the arXiv URL. But for *optional* fields
that may be missing on one source and present on another (``pdf_url``,
``doi``, ``arxiv_id``, ``venue``, ``citation_count``, ``abstract``), the
merged record takes the first non-empty value across all duplicates.

This matters for the PDF download flow: ACM/Crossref records don't
carry a ``pdf_url`` field but OpenAlex usually has the OA mirror under
``best_oa_location.pdf_url``. Pre-merge, a first-wins ACM record would
drop OpenAlex's PDF link and the downloader would skip the paper with
``no_pdf_url``. Post-merge, the ACM record keeps its canonical
metadata but inherits the OpenAlex PDF URL.

Why matching is on ALL identity keys, not one
---------------------------------------------
Every paper carries up to three identities — DOI, arXiv ID, fuzzy title hash
— and each source populates a different subset. Matching only on the
*strongest* key each record happens to have (``Paper.dedup_key()``) meant a
DOI-less ACM record keyed on ``hash:…`` and the same paper's OpenAlex record
keyed on ``doi:10.1145/x`` never compared at all: both shipped, the user saw
the paper twice, and the ACM record never inherited OpenAlex's PDF URL — the
exact failure the field-merge above exists to prevent. Grouping on
:meth:`Paper.identity_keys` fixes that: papers sharing ANY key are one paper,
and a record that arrives later can transitively join two earlier groups (an
arXiv record and a publisher record joined by a third that carries both IDs).

The one restraint is :func:`_identifiers_conflict`: two records that BOTH
carry a DOI, and disagree about it, are never merged on the strength of a
fuzzy title match alone. Same title + same first author + same year with two
different DOIs is how a workshop paper and its extended journal version look,
and merging those would silently drop one from the results.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from thesisagents.core.models import FieldProvenance, Paper, _canon_title

#: Prefix of the fuzzy (title + author + year) identity key. Links made on it
#: are the ones the conflict guard polices — DOI / arXiv keys are exact.
_FUZZY_PREFIX = "hash:"


def dedupe(papers: Iterable[Paper]) -> list[Paper]:
    """Collapse duplicate Papers, merging optional fields across sources.

    Iteration order matters: the first occurrence of a paper is treated as the
    canonical record; later duplicates contribute only their non-empty optional
    fields. Callers concatenate sources in the user-supplied ``--source`` order
    so the canonical record reflects the user's source preference.

    Example: ``dedupe([acm_no_doi, openalex_with_doi, crossref_same_doi])``
    returns one paper — sourced ``acm``, carrying OpenAlex's ``pdf_url`` and
    the DOI both later records supplied.
    """
    slots: list[Paper | None] = []      # None once absorbed into an earlier slot
    index: dict[str, int] = {}          # identity key -> slot position
    for paper in papers:
        keys = paper.identity_keys()
        matches = _matching_slots(slots, index, paper, keys)
        if not matches:
            slots.append(paper)
            position = len(slots) - 1
        else:
            position = min(matches)
            for absorbed in sorted(matches - {position}):
                slots[position] = _merge(slots[position], slots[absorbed])
                slots[absorbed] = None
                _repoint(index, absorbed, position)
            slots[position] = _merge(slots[position], paper)
        # ``setdefault``: a key already claimed by a DIFFERENT slot was rejected
        # by the conflict guard, so it must stay with the slot that owns it.
        for key in keys:
            index.setdefault(key, position)
    return [paper for paper in slots if paper is not None]


def _matching_slots(
    slots: list[Paper | None],
    index: dict[str, int],
    paper: Paper,
    keys: tuple[str, ...],
) -> set[int]:
    """Slots ``paper`` belongs to: every one sharing an identity key with it."""
    matches: set[int] = set()
    for key in keys:
        position = index.get(key)
        if position is None:
            continue
        occupant = slots[position]
        if occupant is None:
            continue
        if key.startswith(_FUZZY_PREFIX) and not _fuzzy_link_allowed(occupant, paper):
            continue
        matches.add(position)
    return matches


def _fuzzy_link_allowed(existing: Paper, candidate: Paper) -> bool:
    """Whether a title-hash match alone may merge these two records.

    Blocked in two cases:

    * **Conflicting strong identifiers.** Both carry a DOI (or both an arXiv
      ID) and they disagree — see the module docstring's workshop-vs-journal
      example. The exact-key path still merges them if a DOI does match.
    * **An empty canonical title.** ``_canon_title`` strips every
      non-alphanumeric character, so a paper titled ``"..."`` — or one whose
      title the source left blank — hashes identically to every other such
      paper. Without this check the fuzzy key becomes a magnet that collapses
      unrelated title-less records into one.
    """
    if not _canon_title(existing.title) or not _canon_title(candidate.title):
        return False
    return not _identifiers_conflict(existing, candidate)


def _identifiers_conflict(a: Paper, b: Paper) -> bool:
    """True when both papers name the same identifier type but disagree on it."""
    for left, right in ((a.doi_key(), b.doi_key()), (a.arxiv_key(), b.arxiv_key())):
        if left is not None and right is not None and left != right:
            return True
    return False


def _repoint(index: dict[str, int], absorbed: int, target: int) -> None:
    """Redirect every key pointing at an absorbed slot to the surviving one."""
    for key, position in index.items():
        if position == absorbed:
            index[key] = target


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
    added_provenance: list[FieldProvenance] = []
    for name in _MERGEABLE_FIELDS:
        canonical_value = getattr(canonical, name)
        other_value = getattr(other, name)
        if _is_missing(canonical_value) and not _is_missing(other_value):
            updates[name] = other_value
            added_provenance.append(
                FieldProvenance(
                    field=name,
                    source=other.source,
                    source_id=other.source_id,
                )
            )
    if not updates:
        return canonical
    updates["provenance"] = canonical.provenance + tuple(added_provenance)
    return replace(canonical, **updates)
