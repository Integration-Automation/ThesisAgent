"""Bounded snowball search: grow a set of papers along its citation links.

Starting from seed papers, *backward* snowballing collects the papers they
cite (their references) and *forward* snowballing collects the papers that
cite them. It finds the work a keyword search misses because the authors used
other words.

A citation graph has no natural end, so every dimension here is capped:

* **depth** (default 1, at most ``SNOWBALL_MAX_DEPTH``): how many steps from a
  seed. Depth 2 also expands the papers found at depth 1.
* **max_per_seed**: papers taken from one lookup (one paper, one direction).
* **max_total**: papers discovered in all. Reaching it stops the search and
  sets ``truncated``.
* a paper is expanded at most once, so a cycle cannot loop.

Other rules the design follows:

* **One identity model.** A found paper is matched against the seeds and
  everything found so far with ``IdentityIndex``, the same DOI / arXiv ID /
  title-hash matching as ``dedupe``. Reached along two paths, it is one paper.
* **Provenance.** Each discovered paper keeps the first path that reached it
  (``found_by``: which paper, which direction, which provider, which depth).
  Levels are expanded in order, so the first path is also a shortest one.
  Every link seen is kept in ``relations`` for a citation graph.
* **Relevance is scored, never assumed.** With ``keywords`` each discovered
  paper is scored by the search's own ranker. Being cited often, or citing a
  seed, is not treated as evidence that a paper is on topic.
* **A broken provider does not stop the search.** Its error is recorded in
  ``errors`` and the next provider is asked.
"""

from __future__ import annotations

import asyncio
import dataclasses
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from thesisagents.core.constants import (
    DEFAULT_CITATION_PROVIDERS,
    SNOWBALL_DEFAULT_DEPTH,
    SNOWBALL_DEFAULT_MAX_PER_SEED,
    SNOWBALL_DEFAULT_MAX_TOTAL,
    SNOWBALL_MAX_DEPTH,
    SNOWBALL_MAX_PER_SEED,
    SNOWBALL_MAX_TOTAL,
)
from thesisagents.core.dedup import IdentityIndex
from thesisagents.core.diagnostics import (
    PaperRelation,
    PaperScore,
    RelationKind,
    RelevanceScore,
    SearchDiagnostics,
)
from thesisagents.core.exceptions import CitationNotAvailableError, ConfigError
from thesisagents.core.models import Paper, PaperCollection
from thesisagents.core.pruning import recommend_pruning
from thesisagents.core.ranking import RankedPaper, rank_with_scores
from thesisagents.fetchers.citations import CitationProvider, load_citation_provider
from thesisagents.utils.logging import get_logger

_LOG = get_logger(__name__)

#: Lookups in flight at once. Each provider also has its own token bucket.
#: This cap keeps a frontier of fifty papers from opening fifty connections.
_LOOKUP_CONCURRENCY = 4


class Direction(StrEnum):
    """Which way to follow citation links."""

    REFERENCES = "references"   # backward: what the seeds cite
    CITED_BY = "cited_by"       # forward: what cites the seeds
    BOTH = "both"


_KINDS: dict[Direction, tuple[RelationKind, ...]] = {
    Direction.REFERENCES: (RelationKind.REFERENCES,),
    Direction.CITED_BY: (RelationKind.CITED_BY,),
    Direction.BOTH: (RelationKind.REFERENCES, RelationKind.CITED_BY),
}


@dataclass(frozen=True, slots=True)
class DiscoveredPaper:
    """A paper the snowball found, with why it is here.

    ``found_by`` is the first path that reached it. ``score`` is its ranking
    score against the snowball's ``keywords``, ``None`` when none were given.
    """

    paper: Paper
    found_by: PaperRelation
    score: RelevanceScore | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "paper": self.paper.to_dict(),
            "found_by": self.found_by.to_dict(),
            "score": self.score.to_dict() if self.score else None,
        }


@dataclass(frozen=True, slots=True)
class SnowballResult:
    """Outcome of one :func:`snowball` call.

    ``discovered`` holds the new papers only, never a seed. With keywords they
    are ordered best score first, otherwise in the order they were found.
    ``relations`` holds every citation link seen, including links between two
    seeds and links to a paper that was already known. ``truncated`` is True
    when ``max_total`` stopped the search with papers left unseen.
    """

    seeds: tuple[Paper, ...] = ()
    discovered: tuple[DiscoveredPaper, ...] = ()
    relations: tuple[PaperRelation, ...] = ()
    errors: tuple[str, ...] = ()
    truncated: bool = False

    @property
    def papers(self) -> tuple[Paper, ...]:
        """The discovered papers, without their provenance."""
        return tuple(entry.paper for entry in self.discovered)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed_count": len(self.seeds),
            "discovered_count": len(self.discovered),
            "discovered": [entry.to_dict() for entry in self.discovered],
            "relations": [relation.to_dict() for relation in self.relations],
            "errors": list(self.errors),
            "truncated": self.truncated,
        }


@dataclass(frozen=True, slots=True)
class _Settings:
    kinds: tuple[RelationKind, ...]
    depth: int
    max_per_seed: int
    max_total: int
    keywords: str | None
    min_relevance: float | None
    current_year: int | None


@dataclass(frozen=True, slots=True)
class _Edge:
    """A link between two index slots, as first reported."""

    source: int
    target: int
    kind: RelationKind
    provider: str
    depth: int


async def snowball(  # noqa: PLR0913 — the bounds are the public contract of the search
    seeds: Sequence[Paper],
    *,
    direction: Direction | str = Direction.BOTH,
    depth: int = SNOWBALL_DEFAULT_DEPTH,
    max_per_seed: int = SNOWBALL_DEFAULT_MAX_PER_SEED,
    min_relevance: float | None = None,
    keywords: str | None = None,
    max_total: int = SNOWBALL_DEFAULT_MAX_TOTAL,
    providers: Sequence[CitationProvider] | None = None,
    known: Sequence[Paper] = (),
    current_year: int | None = None,
) -> SnowballResult:
    """Expand ``seeds`` along their citation links, within fixed bounds.

    ``known`` lists papers the caller already holds besides the seeds, for
    example the rest of a search result when only its top five are used as
    seeds. They are not expanded, and a link that leads to one of them is
    recorded without the paper being reported as discovered.

    ``direction`` is ``"references"``, ``"cited_by"`` or ``"both"``.
    ``keywords`` turns on scoring of every discovered paper with the search
    ranker. ``min_relevance`` (0 to 1, needs ``keywords``) then drops papers
    whose relevance is below that fraction of the best the keywords allow. A
    dropped paper is neither returned nor expanded further.

    ``providers`` defaults to ``DEFAULT_CITATION_PROVIDERS``. For each paper
    and direction they are asked in order until one returns papers.

    Raises ``ValueError`` for a bound outside its range, before any request.

    Example::

        result = await snowball(
            collection.papers[:5], direction="both", keywords="graph neural network",
            min_relevance=0.3,
        )
        for found in result.discovered:
            via = found.found_by
            print(found.paper.title, "<-", via.relation, "of", via.source_key)
    """
    settings = _validated(
        direction, depth, max_per_seed, max_total, keywords, min_relevance, current_year
    )
    chosen = list(providers) if providers is not None else _default_providers()
    expansion = _Expansion(seeds, known, settings, chosen)
    frontier = expansion.seed_slots
    for level in range(1, settings.depth + 1):
        if not frontier or expansion.truncated:
            break
        frontier = await expansion.expand(frontier, level)
    return expansion.result()


def _validated(
    direction: Direction | str,
    depth: int,
    max_per_seed: int,
    max_total: int,
    keywords: str | None,
    min_relevance: float | None,
    current_year: int | None,
) -> _Settings:
    try:
        chosen = Direction(direction)
    except ValueError as err:
        options = ", ".join(item.value for item in Direction)
        raise ValueError(f"direction must be one of: {options}") from err
    if not 1 <= depth <= SNOWBALL_MAX_DEPTH:
        raise ValueError(f"depth must be in [1, {SNOWBALL_MAX_DEPTH}]")
    if not 1 <= max_per_seed <= SNOWBALL_MAX_PER_SEED:
        raise ValueError(f"max_per_seed must be in [1, {SNOWBALL_MAX_PER_SEED}]")
    if not 1 <= max_total <= SNOWBALL_MAX_TOTAL:
        raise ValueError(f"max_total must be in [1, {SNOWBALL_MAX_TOTAL}]")
    cleaned = (keywords or "").strip() or None
    if min_relevance is not None:
        if not 0.0 <= min_relevance <= 1.0:
            raise ValueError("min_relevance must be in [0, 1]")
        if cleaned is None:
            raise ValueError("min_relevance needs keywords to score against")
    return _Settings(
        kinds=_KINDS[chosen],
        depth=depth,
        max_per_seed=max_per_seed,
        max_total=max_total,
        keywords=cleaned,
        min_relevance=min_relevance,
        current_year=current_year,
    )


def _default_providers() -> list[CitationProvider]:
    """The default providers that can be loaded, in their configured order."""
    loaded: list[CitationProvider] = []
    for name in DEFAULT_CITATION_PROVIDERS:
        try:
            loaded.append(load_citation_provider(name))
        except ConfigError as err:
            _LOG.warning("Citation provider %s unavailable: %s", name, err)
    return loaded


class _Expansion:
    """The state of one snowball run.

    Papers are tracked by ``IdentityIndex`` slot and not by key, because a
    paper's key can change while the search runs: a record first seen without
    a DOI gains one when a later record of the same paper is merged into it.
    Keys are read once, in :meth:`result`.
    """

    def __init__(
        self,
        seeds: Sequence[Paper],
        known: Sequence[Paper],
        settings: _Settings,
        providers: list[CitationProvider],
    ) -> None:
        self._settings = settings
        self._providers = providers
        self._index = IdentityIndex()
        self.seed_slots: list[int] = []
        for seed in seeds:
            slot, is_new = self._index.add(seed)
            if is_new:
                self.seed_slots.append(slot)
        # Held but not expanded: a paper the caller already has is never a
        # discovery, however it is reached.
        self._held_slots: list[int] = list(self.seed_slots)
        for paper in known:
            slot, _is_new = self._index.add(paper)
            self._held_slots.append(slot)
        self._discovered: list[int] = []
        self._first_path: dict[int, _Edge] = {}
        self._edges: dict[tuple[int, int, RelationKind], _Edge] = {}
        self._errors: list[str] = []
        self.truncated = False

    async def expand(self, frontier: list[int], level: int) -> list[int]:
        """Look up every paper of ``frontier`` and return the newly found slots."""
        gate = asyncio.Semaphore(_LOOKUP_CONCURRENCY)
        lookups = [
            (slot, kind) for slot in frontier for kind in self._settings.kinds
        ]

        async def bounded(slot: int, kind: RelationKind) -> tuple[str, list[Paper]]:
            async with gate:
                return await self._lookup(self._index.get(slot), kind)

        answers = await asyncio.gather(
            *(bounded(slot, kind) for slot, kind in lookups)
        )
        # Integrate in lookup order, not completion order, so the same inputs
        # always give the same discovery order and the same first paths.
        found: list[int] = []
        for (slot, kind), (provider, papers) in zip(lookups, answers, strict=True):
            for candidate in papers:
                new_slot = self._admit(candidate, slot, kind, provider, level)
                if new_slot is not None:
                    found.append(new_slot)
        return found

    async def _lookup(self, paper: Paper, kind: RelationKind) -> tuple[str, list[Paper]]:
        """Ask the providers in order until one returns papers."""
        limit = self._settings.max_per_seed
        for provider in self._providers:
            ask = (
                provider.references
                if kind is RelationKind.REFERENCES
                else provider.cited_by
            )
            try:
                papers = await ask(paper, limit)
            except CitationNotAvailableError as err:
                _LOG.debug("%s has no %s for %s: %s", provider.name, kind.value,
                           paper.dedup_key(), err)
                continue
            except Exception as err:  # noqa: BLE001 — containment: one provider must not end the search
                self._errors.append(
                    f"{provider.name} {kind.value} lookup failed for "
                    f"{paper.dedup_key()}: {err}"
                )
                continue
            if papers:
                return provider.name, list(papers[:limit])
        return "", []

    def _admit(
        self, candidate: Paper, source: int, kind: RelationKind, provider: str, level: int
    ) -> int | None:
        """Record ``candidate`` and its link. Return its slot when it is new."""
        if not candidate.title.strip():
            return None  # nothing to score it by, and no title to identify it by
        if self._below_relevance(candidate):
            return None
        known = self._index.find(candidate)
        if known is None and len(self._discovered) >= self._settings.max_total:
            self.truncated = True
            return None
        slot, is_new = self._index.add(candidate)
        origin = self._index.resolve(source)
        if origin != slot:
            edge = _Edge(origin, slot, kind, provider, level)
            self._edges.setdefault((origin, slot, kind), edge)
            if is_new:
                self._first_path[slot] = edge
        if not is_new:
            return None
        self._discovered.append(slot)
        return slot

    def _score(self, paper: Paper) -> RelevanceScore | None:
        if self._settings.keywords is None:
            return None
        ranked = rank_with_scores(
            [paper], self._settings.keywords, current_year=self._settings.current_year
        )
        return ranked[0].score

    def _below_relevance(self, paper: Paper) -> bool:
        threshold = self._settings.min_relevance
        if threshold is None:
            return False
        score = self._score(paper)
        return score is None or (score.relevance_ratio or 0.0) < threshold

    def _relation(self, edge: _Edge) -> PaperRelation:
        return PaperRelation(
            source_key=self._index.get(edge.source).dedup_key(),
            target_key=self._index.get(edge.target).dedup_key(),
            relation=edge.kind,
            provider=edge.provider,
            depth=edge.depth,
        )

    def result(self) -> SnowballResult:
        seed_set = {self._index.resolve(slot) for slot in self.seed_slots}
        held = {self._index.resolve(slot) for slot in self._held_slots}
        entries: list[DiscoveredPaper] = []
        emitted: set[int] = set()
        for slot in self._discovered:
            current = self._index.resolve(slot)
            # A later merge can fold a discovered paper into a held paper or
            # into another discovered one. Either way it is listed once, or not.
            if current in held or current in emitted:
                continue
            emitted.add(current)
            paper = self._index.get(current)
            entries.append(
                DiscoveredPaper(
                    paper=paper,
                    found_by=self._relation(self._first_path[slot]),
                    score=self._score(paper),
                )
            )
        if self._settings.keywords is not None:
            entries.sort(key=lambda entry: entry.score.total, reverse=True)
        relations: dict[tuple[str, str, RelationKind], PaperRelation] = {}
        for edge in self._edges.values():
            relation = self._relation(edge)
            if relation.source_key != relation.target_key:
                key = (relation.source_key, relation.target_key, relation.relation)
                relations.setdefault(key, relation)
        return SnowballResult(
            seeds=tuple(self._index.get(slot) for slot in sorted(seed_set)),
            discovered=tuple(entries),
            relations=tuple(relations.values()),
            errors=tuple(self._errors),
            truncated=self.truncated,
        )


def expand_collection(
    collection: PaperCollection, result: SnowballResult
) -> PaperCollection:
    """Return ``collection`` with the discovered papers appended.

    The boundary this guards: a snowball result is a separate object, and the
    rest of the program (PDF download, the identifier preflight, the
    exporters, the diagnostics printout) works on one ``PaperCollection``.
    This is the one place the two are joined, so the discovered papers reach
    every later stage and their provenance is not lost on the way.

    The search results keep their positions and the discovered papers follow
    in the result's order. ``diagnostics`` gains the citation links
    (``relations``) and, when the snowball scored the papers, a score and an
    advisory pruning recommendation for each discovered paper, ranked after
    the search results.

    Call :func:`snowball` with ``known=collection.papers`` first. That is what
    keeps a paper already in the collection from being discovered again.

    Example::

        result = await snowball(collection.papers[:5], known=collection.papers,
                                keywords=collection.query.keywords)
        collection = expand_collection(collection, result)
    """
    base = collection.diagnostics or SearchDiagnostics()
    offset = len(collection.papers)
    ranked = [
        RankedPaper(paper=entry.paper, score=entry.score, rank=offset + position)
        for position, entry in enumerate(result.discovered, start=1)
        if entry.score is not None
    ]
    scores = tuple(
        PaperScore(paper_key=entry.paper.dedup_key(), rank=entry.rank, score=entry.score)
        for entry in ranked
    )
    diagnostics = dataclasses.replace(
        base,
        scores=base.scores + scores,
        pruning=base.pruning + recommend_pruning(ranked),
        relations=base.relations + result.relations,
    )
    return dataclasses.replace(
        collection,
        papers=collection.papers + result.papers,
        diagnostics=diagnostics,
    )
