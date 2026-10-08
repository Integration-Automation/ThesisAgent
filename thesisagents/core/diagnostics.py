"""Records that explain a search result: why a paper ranks where it does.

Kept free of imports from the rest of the package so that ``models.py`` can
attach a :class:`SearchDiagnostics` to ``PaperCollection`` while ``ranking.py``
and ``pruning.py`` (which import ``models``) fill it in, with no import cycle.

Why these exist: ``rank()`` used to return only the sorted papers. The three
numbers that decided the order were thrown away, so a user who asked "why is
this off-topic paper third?" had no answer short of re-deriving the score by
hand. A :class:`RelevanceScore` keeps the breakdown and says, in words, what
matched.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # models.py imports this module, so the import is type-only
    from thesisagents.core.models import PaperCollection

_SCORE_DIGITS = 4


@dataclass(frozen=True, slots=True)
class RelevanceScore:
    """How one paper's ranking score is made up.

    ``total == relevance + recency + citation``, the three axes described in
    ``ranking.py``. The rest explains the ``relevance`` part:

    * ``matched_terms``: query terms found in the title or abstract, in query
      order, in their stemmed form (``"transformers"`` is ``"transformer"``).
    * ``matched_phrases``: adjacent query word pairs that are also adjacent in
      the title, as ``"retrieval augmented"``.
    * ``reasons``: one plain sentence per contribution, ready to show a user.
    * ``relevance_ratio``: ``relevance`` as a fraction of the best relevance
      this query allows (every term in title and abstract, every phrase
      adjacent), ``0.0`` to ``1.0``. ``None`` when the ranking had no query,
      because there was nothing to be relevant to.

    Example: for the query ``"llm"`` and a paper titled "Large Language
    Models: A Survey", ``matched_terms == ("llm",)`` and ``reasons`` holds
    ``'"llm" matched through its long form "large language model"'``.
    """

    total: float
    relevance: float
    recency: float
    citation: float
    matched_terms: tuple[str, ...] = ()
    matched_phrases: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    relevance_ratio: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": round(self.total, _SCORE_DIGITS),
            "relevance": round(self.relevance, _SCORE_DIGITS),
            "recency": round(self.recency, _SCORE_DIGITS),
            "citation": round(self.citation, _SCORE_DIGITS),
            "relevance_ratio": (
                None
                if self.relevance_ratio is None
                else round(self.relevance_ratio, _SCORE_DIGITS)
            ),
            "matched_terms": list(self.matched_terms),
            "matched_phrases": list(self.matched_phrases),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True, slots=True)
class PaperScore:
    """A :class:`RelevanceScore` tied to one paper of a collection.

    ``paper_key`` is ``Paper.dedup_key()`` and ``rank`` is the paper's 1-based
    position in the collection. Keyed, not holding the ``Paper`` itself, so the
    entry stays valid when a later stage replaces the paper object (the OA
    resolver fills ``pdf_url``, enrichment attaches a summary).
    """

    paper_key: str
    rank: int
    score: RelevanceScore

    def to_dict(self) -> dict[str, Any]:
        return {"paper_key": self.paper_key, "rank": self.rank, **self.score.to_dict()}


class PruningAction(StrEnum):
    """What to do with a search result. Advice only: nothing is removed."""

    KEEP = "keep"
    REVIEW = "review"
    PRUNE = "prune"


@dataclass(frozen=True, slots=True)
class PruningRecommendation:
    """Advice for one paper, with the rule that produced it.

    ``threshold`` names the policy setting that triggered a ``review`` /
    ``prune`` (``"prune_below_relevance=0.10"``), so the advice can be traced
    and the setting tuned. It is empty for ``keep``.
    """

    paper_key: str
    rank: int
    action: PruningAction
    reasons: tuple[str, ...] = ()
    threshold: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "paper_key": self.paper_key,
            "rank": self.rank,
            "action": self.action.value,
            "threshold": self.threshold,
            "reasons": list(self.reasons),
        }


class SourceStatus(StrEnum):
    """How one source fared for one query.

    ``ok`` covers a source that answered with nothing: an empty answer is an
    answer. The other three mean the source contributed no papers and say why.
    """

    OK = "ok"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class SourceStat:
    """What one source contributed to one search.

    Why it exists: a failing source returns nothing and never breaks the
    others, by design. That made a search that silently lost half its sources
    look the same as one that found nothing there. These counts make the
    difference visible.

    * ``requested``: the per-source result cap of the query (``--max``).
    * ``returned``: records the source sent back, before de-duplication.
    * ``after_dedup``: how many of the de-duplicated papers are credited to
      this source. A paper several sources returned is credited to the first
      of them in the query's source order, so the values of all sources add up
      to the number of unique papers. ``returned - after_dedup`` is therefore
      how many of this source's records duplicated an earlier source's (or its
      own).
    * ``status`` / ``detail``: see :class:`SourceStatus`. ``detail`` carries
      the error text for anything but ``ok``.

    Both counts are taken before the query's filters (year range, minimum
    citations, top-tier venues) and before the final ``max_results`` cut, so
    they describe the sources, not the filtered result.

    Example: ``SourceStat("arxiv", requested=25, returned=23, after_dedup=19,
    status=SourceStatus.OK)`` means four of arXiv's 23 records were also
    returned by a source listed before it.
    """

    source: str
    requested: int
    returned: int
    after_dedup: int
    status: SourceStatus = SourceStatus.OK
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "requested": self.requested,
            "returned": self.returned,
            "after_dedup": self.after_dedup,
            "status": self.status.value,
            "detail": self.detail,
        }


class RelationKind(StrEnum):
    """How a paper found by snowballing relates to the paper it was found from."""

    #: The found paper is in the reference list of the paper expanded.
    REFERENCES = "references"
    #: The found paper cites the paper expanded.
    CITED_BY = "cited_by"


@dataclass(frozen=True, slots=True)
class PaperRelation:
    """One citation link found by a snowball search, with its provenance.

    ``source_key`` is the paper that was expanded and ``target_key`` the paper
    found from it, both as ``Paper.dedup_key()``. Read together with
    ``relation`` it says which way the citation runs: for ``references`` the
    source cites the target, for ``cited_by`` the target cites the source.
    ``citing_key`` / ``cited_key`` give that direction without the reader
    having to work it out.

    ``provider`` is the source that reported the link and ``depth`` how many
    steps from a seed it was found (1 = straight from a seed). Together with
    ``source_key`` this is the answer to "why is this paper here?".

    Kept outside ``Paper`` on purpose: a paper can be reached along many
    paths, and a list of them does not belong in the bibliographic record.

    Example: ``PaperRelation("doi:10.1/seed", "doi:10.1/found",
    RelationKind.CITED_BY, "openalex", 1)`` reads "10.1/found cites
    10.1/seed, reported by OpenAlex, found directly from a seed".
    """

    source_key: str
    target_key: str
    relation: RelationKind
    provider: str
    depth: int

    @property
    def citing_key(self) -> str:
        """The paper that cites."""
        if self.relation is RelationKind.REFERENCES:
            return self.source_key
        return self.target_key

    @property
    def cited_key(self) -> str:
        """The paper that is cited."""
        if self.relation is RelationKind.REFERENCES:
            return self.target_key
        return self.source_key

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_key": self.source_key,
            "target_key": self.target_key,
            "relation": self.relation.value,
            "provider": self.provider,
            "depth": self.depth,
        }


@dataclass(frozen=True, slots=True)
class SearchDiagnostics:
    """Everything a search can say about itself beyond the papers.

    Attached to ``PaperCollection.diagnostics`` by ``run_search``. Optional
    everywhere: a collection built by hand (the MCP ``export`` tool, a regen
    script, ``--pdf`` mode) has none, and every consumer must accept ``None``.
    """

    scores: tuple[PaperScore, ...] = ()
    pruning: tuple[PruningRecommendation, ...] = ()
    source_stats: tuple[SourceStat, ...] = ()
    #: Citation links found when the search was expanded by snowballing.
    #: Empty for a plain search.
    relations: tuple[PaperRelation, ...] = ()

    def score_for(self, paper_key: str) -> RelevanceScore | None:
        """The score recorded for ``paper_key``, or ``None``."""
        for entry in self.scores:
            if entry.paper_key == paper_key:
                return entry.score
        return None

    def recommendation_for(self, paper_key: str) -> PruningRecommendation | None:
        """The pruning advice recorded for ``paper_key``, or ``None``."""
        for entry in self.pruning:
            if entry.paper_key == paper_key:
                return entry
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "scores": [entry.to_dict() for entry in self.scores],
            "pruning": [entry.to_dict() for entry in self.pruning],
            "source_stats": [entry.to_dict() for entry in self.source_stats],
            "relations": [entry.to_dict() for entry in self.relations],
        }


def source_stats_payload(collection: PaperCollection) -> list[dict[str, Any]]:
    """The per-source counts of ``collection`` as JSON-ready dicts.

    An empty list for a collection without diagnostics, so a caller can put
    the result in a response unconditionally.

    Example: ``[{"source": "arxiv", "requested": 25, "returned": 23,
    "after_dedup": 19, "status": "ok", "detail": ""}]``.
    """
    diagnostics = collection.diagnostics
    if diagnostics is None:
        return []
    return [stat.to_dict() for stat in diagnostics.source_stats]


def collection_report(collection: PaperCollection) -> dict[str, Any]:
    """Scores and pruning advice joined to the papers, one entry per paper.

    The boundary this guards: the diagnostics are stored by ``paper_key`` so
    they survive later pipeline stages, but a reader wants them next to the
    paper they describe. This is the one place that join is made, so the CLI's
    ``diagnostics.json`` and the MCP ``search`` response cannot drift apart.

    Each entry carries the ``bibtex_key`` as well, because that is how the
    PDFs and per-paper decks on disk are named: an agent that follows a
    ``prune`` recommendation needs it to find ``pdfs/<bibtex_key>.pdf``.

    A paper with no recorded score (a collection built by hand) is listed with
    ``"score": None`` and ``"recommendation": None``, never left out.

    Example entry::

        {"rank": 3, "paper_key": "doi:10.1/x", "bibtex_key": "lee2023graph",
         "title": "...", "score": {"total": 2.41, "reasons": [...], ...},
         "recommendation": {"action": "review",
                            "threshold": "review_below_relevance=0.30",
                            "reasons": [...]}}
    """
    diagnostics = collection.diagnostics
    entries: list[dict[str, Any]] = []
    summary = dict.fromkeys((action.value for action in PruningAction), 0)
    for position, paper in enumerate(collection.papers, start=1):
        key = paper.dedup_key()
        score = diagnostics.score_for(key) if diagnostics else None
        advice = diagnostics.recommendation_for(key) if diagnostics else None
        if advice is not None:
            summary[advice.action.value] += 1
        entries.append(
            {
                "rank": position,
                "paper_key": key,
                "bibtex_key": paper.bibtex_key(),
                "title": paper.title,
                "score": score.to_dict() if score else None,
                "recommendation": (
                    {
                        "action": advice.action.value,
                        "threshold": advice.threshold,
                        "reasons": list(advice.reasons),
                    }
                    if advice
                    else None
                ),
            }
        )
    return {
        "keywords": collection.query.keywords,
        "advisory": True,
        "summary": summary,
        "source_stats": source_stats_payload(collection),
        # Citation links found by a snowball expansion, empty for a plain search.
        "relations": [
            relation.to_dict()
            for relation in (diagnostics.relations if diagnostics else ())
        ],
        "papers": entries,
    }
