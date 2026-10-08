"""Advice on which search results to keep, look at again, or drop.

Why this exists: a keyword search returns off-topic papers by construction. A
"Claude code" query once returned a Viterbi-decoder paper because both contain
"code". Removing such papers was a manual step with no help from the tool, and
the ranking scores that could have pointed at them were discarded.

:func:`recommend_pruning` reads the scores :func:`ranking.rank_with_scores`
kept and labels each paper ``keep``, ``review`` or ``prune``, naming the rule
and the threshold behind every label.

**Advice only.** Nothing here removes a paper. The pipeline attaches the
recommendations to the collection and a person (or an agent) decides. A hard
pruning mode can be added later, once these rules have been observed on real
searches.

The rules, in the order they are applied to each paper:

1. **Low relevance.** ``relevance_ratio`` (relevance as a fraction of the best
   the query allows) below ``prune_below_relevance`` is ``prune``, below
   ``review_below_relevance`` is ``review``.
2. **Weak on every axis.** A ``review`` paper that is also old and weakly cited
   becomes ``prune``: nothing argues for it.
3. **Redundant.** A paper whose title shares almost all of its terms with a
   higher-ranked paper is ``review``. De-duplication keeps a workshop paper and
   its journal version apart on purpose (their DOIs differ), and this is where
   the user is told the two overlap.

What never triggers a recommendation: a low citation count on its own. A new,
on-topic paper has no citations yet, and dropping it for that would discard
exactly the work a literature review most needs. Likewise an unknown year or
an unknown citation count is not treated as weak: the source did not say.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from thesisagents.core.diagnostics import PruningAction, PruningRecommendation
from thesisagents.core.ranking import RankedPaper, title_terms


@dataclass(frozen=True, slots=True)
class PruningPolicy:
    """Thresholds behind :func:`recommend_pruning`.

    ``prune_below_relevance`` / ``review_below_relevance`` are fractions of the
    best relevance the query allows. With the default ranking weights and a
    two-word query, 0.10 is "at most part of the query in the abstract and
    nothing in the title", and 0.30 is "less than half the query in the title".

    ``weak_recency`` is a recency score (``exp(-age / 5)``). 0.15 falls between
    nine years (0.165) and ten (0.135), so a paper ten or more years old counts
    as old. ``weak_citations`` is a citation count: fewer than this is weak.

    ``redundant_title_overlap`` is the Jaccard overlap of two titles' term
    sets: shared terms divided by all terms.

    Example: ``PruningPolicy(review_below_relevance=0.5)`` flags more papers
    for review, for a narrow topic where a partial title match is not enough.
    """

    prune_below_relevance: float = 0.10
    review_below_relevance: float = 0.30
    weak_recency: float = 0.15
    weak_citations: int = 5
    redundant_title_overlap: float = 0.85

    def __post_init__(self) -> None:
        if not 0.0 <= self.prune_below_relevance <= self.review_below_relevance <= 1.0:
            raise ValueError(
                "need 0 <= prune_below_relevance <= review_below_relevance <= 1"
            )
        if not 0.0 < self.redundant_title_overlap <= 1.0:
            raise ValueError("redundant_title_overlap must be in (0, 1]")
        if self.weak_recency < 0 or self.weak_citations < 0:
            raise ValueError("weak_recency and weak_citations must be >= 0")


DEFAULT_PRUNING_POLICY = PruningPolicy()

#: A reason line names the paper it overlaps with. Longer titles are cut here
#: so one recommendation stays one readable line.
_TITLE_QUOTE_CHARS = 60


def _quote_title(title: str) -> str:
    flat = " ".join(title.split())
    if len(flat) > _TITLE_QUOTE_CHARS:
        flat = flat[: _TITLE_QUOTE_CHARS - 1].rstrip() + "…"
    return f'"{flat}"'


def recommend_pruning(
    ranked: Sequence[RankedPaper], policy: PruningPolicy | None = None
) -> tuple[PruningRecommendation, ...]:
    """One recommendation per ranked paper, in rank order.

    Deterministic: the same ranked list and policy always give the same
    recommendations, because every rule reads only the scores and the paper
    fields already in ``ranked``.

    Example::

        ranked = rank_with_scores(papers, "transformer attention")
        for advice in recommend_pruning(ranked):
            if advice.action is not PruningAction.KEEP:
                print(advice.rank, advice.action, advice.threshold, advice.reasons)
    """
    chosen = policy if policy is not None else DEFAULT_PRUNING_POLICY
    recommendations: list[PruningRecommendation] = []
    seen: list[tuple[RankedPaper, frozenset[str]]] = []
    for entry in ranked:
        terms = title_terms(entry.paper.title)
        action, threshold, reasons = _judge_relevance(entry, chosen)
        if action is not PruningAction.PRUNE:
            overlap = _most_similar_earlier(terms, seen, chosen)
            if overlap is not None:
                earlier, share = overlap
                reasons.append(
                    f"title shares {share:.0%} of its terms with higher-ranked "
                    f"#{earlier.rank} {_quote_title(earlier.paper.title)}"
                )
                if action is PruningAction.KEEP:
                    action = PruningAction.REVIEW
                    threshold = (
                        f"redundant_title_overlap={chosen.redundant_title_overlap:.2f}"
                    )
        recommendations.append(
            PruningRecommendation(
                paper_key=entry.paper.dedup_key(),
                rank=entry.rank,
                action=action,
                reasons=tuple(reasons),
                threshold=threshold,
            )
        )
        seen.append((entry, terms))
    return tuple(recommendations)


def _judge_relevance(
    entry: RankedPaper, policy: PruningPolicy
) -> tuple[PruningAction, str, list[str]]:
    """Rules 1 and 2: low relevance, then weak on every axis."""
    ratio = entry.score.relevance_ratio
    if ratio is None:
        return (
            PruningAction.KEEP, "",
            ["no query: relevance was not assessed"],
        )
    if ratio < policy.prune_below_relevance:
        return (
            PruningAction.PRUNE,
            f"prune_below_relevance={policy.prune_below_relevance:.2f}",
            [
                f"relevance is {ratio:.0%} of the best this query allows, "
                f"below the prune threshold {policy.prune_below_relevance:.0%}"
            ],
        )
    if ratio >= policy.review_below_relevance:
        return (
            PruningAction.KEEP, "",
            [f"relevance is {ratio:.0%} of the best this query allows"],
        )
    reasons = [
        f"relevance is {ratio:.0%} of the best this query allows, "
        f"below the review threshold {policy.review_below_relevance:.0%}"
    ]
    weakness = _weak_on_other_axes(entry, policy)
    if weakness is None:
        return (
            PruningAction.REVIEW,
            f"review_below_relevance={policy.review_below_relevance:.2f}",
            reasons,
        )
    reasons.append(weakness)
    return (
        PruningAction.PRUNE,
        f"weak_on_all_axes(weak_recency={policy.weak_recency:.2f}, "
        f"weak_citations={policy.weak_citations})",
        reasons,
    )


def _weak_on_other_axes(entry: RankedPaper, policy: PruningPolicy) -> str | None:
    """A sentence when the paper is both old and weakly cited, else ``None``.

    Both facts must be known. A missing year or a missing citation count means
    the source did not report it, which is not the same as "old" or "uncited".
    """
    paper = entry.paper
    if paper.year is None or paper.citation_count is None:
        return None
    old = entry.score.recency < policy.weak_recency
    uncited = paper.citation_count < policy.weak_citations
    if not (old and uncited):
        return None
    return (
        f"also old (published {paper.year}) and weakly cited "
        f"({paper.citation_count} citations), so no axis argues for keeping it"
    )


def _most_similar_earlier(
    terms: frozenset[str],
    seen: Sequence[tuple[RankedPaper, frozenset[str]]],
    policy: PruningPolicy,
) -> tuple[RankedPaper, float] | None:
    """The higher-ranked paper whose title overlaps most, if it passes the bar.

    Ties go to the higher-ranked paper, so the result does not depend on set
    iteration order.
    """
    if not terms:
        return None
    best: tuple[RankedPaper, float] | None = None
    for earlier, earlier_terms in seen:
        if not earlier_terms:
            continue
        share = len(terms & earlier_terms) / len(terms | earlier_terms)
        if share >= policy.redundant_title_overlap and (
            best is None or share > best[1]
        ):
            best = (earlier, share)
    return best
