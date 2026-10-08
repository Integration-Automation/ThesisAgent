"""Async pipeline: fetch from N sources in parallel → dedup → rank → collection.

Also exposes ``run_single_paper`` for "fetch one paper by ID" workflows and
``enrich_collection`` which augments each paper with an LLM-generated
``PaperSummary`` built from its full PDF text.
"""

from __future__ import annotations

import asyncio
import dataclasses
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any

from thesisagents.core.constants import (
    RATE_LIMIT_RETRY_ATTEMPTS,
    RATE_LIMIT_RETRY_BASE_SECONDS,
)
from thesisagents.core.dedup import dedupe
from thesisagents.core.diagnostics import (
    PaperScore,
    SearchDiagnostics,
    SourceStat,
    SourceStatus,
)
from thesisagents.core.exceptions import (
    ConfigError,
    FetchError,
    RateLimitError,
    ThesisAgentsError,
)
from thesisagents.core.identifiers import PaperIdentifier
from thesisagents.core.models import Paper, PaperCollection, Query
from thesisagents.core.oa_resolver import resolve_oa_pdfs
from thesisagents.core.pruning import recommend_pruning
from thesisagents.core.ranking import RankedPaper, rank_with_scores
from thesisagents.core.top_venues import is_top_tier
from thesisagents.fetchers.base import load_fetcher
from thesisagents.utils.logging import get_logger

_LOG = get_logger(__name__)

# Cap on simultaneous per-paper enrichment tasks. Each task fetches a PDF over
# HTTPS and then calls the Anthropic API; without a cap a 25-paper search would
# fire 25 concurrent API calls (an easy 429 from Anthropic) plus 25 concurrent
# PDF downloads. 4 keeps throughput high while staying under typical API limits.
_ENRICH_CONCURRENCY = 4


async def run_search(
    query: Query, *, resolve_oa: bool = True
) -> PaperCollection:
    """Run `query` across its sources concurrently and produce a collection.

    Source plugins that fail to load (e.g. an opt-in plugin whose env var
    is unset) are skipped with a warning so the rest of the mix still runs.

    ``resolve_oa`` (default True) runs the OA PDF resolver after dedup +
    rank + top-tier filter so papers whose source returned no ``pdf_url``
    (typical for IEEE / ACM / Springer / Elsevier) get a chance to pick
    up an open-access mirror from Unpaywall or an arXiv preprint.
    Pass ``False`` from tests or CLI flags that want raw source output.

    The returned collection carries ``diagnostics``: what each source
    contributed (``source_stats``), the score behind each paper's position and
    the advisory pruning recommendations.
    """
    outcomes = await _fetch_all(query)
    flat = [paper for outcome in outcomes for paper in outcome.papers]
    unique = dedupe(flat)
    ranked = rank_with_scores(unique, keywords=query.keywords)
    kept = _apply_query_filters(ranked, query)[: query.max_results]
    stats = _source_stats(outcomes, unique, requested=query.max_results)
    collection = PaperCollection(
        query=query,
        papers=tuple(entry.paper for entry in kept),
        diagnostics=_diagnose(kept, stats),
    )
    if resolve_oa:
        collection = await resolve_oa_pdfs(collection)
    return collection


@dataclass(frozen=True, slots=True)
class _SourceOutcome:
    """What one source produced for one query, before any merging.

    Kept per source (the results used to be flattened at once) so the search
    can report who returned what. ``status`` and ``detail`` say why
    ``papers`` is empty when it is empty for a reason other than "no match".
    """

    source: str
    papers: tuple[Paper, ...] = ()
    status: SourceStatus = SourceStatus.OK
    detail: str = ""


async def _fetch_all(query: Query) -> list[_SourceOutcome]:
    """Search every source of ``query`` concurrently, one outcome per source.

    The outcomes come back in the order the sources were named, including the
    sources that could not be loaded (``disabled``), so the report lists every
    source the user asked for and not only the ones that ran.

    Failure containment is unchanged: a source that cannot be loaded or that
    raises contributes an empty outcome and never stops the others.
    """
    per_source_query = query.with_max(query.max_results)
    outcomes: dict[int, _SourceOutcome] = {}
    running: list[tuple[int, Coroutine[Any, Any, _SourceOutcome]]] = []
    for index, name in enumerate(query.sources):
        try:
            fetcher = load_fetcher(name)
        except ConfigError as err:
            _LOG.warning("Source %s disabled: %s", name, err)
            outcomes[index] = _SourceOutcome(
                name, status=SourceStatus.DISABLED, detail=str(err)
            )
            continue
        running.append((index, _safe_search(fetcher, per_source_query, name)))
    finished = await asyncio.gather(*(search for _, search in running))
    for (index, _), outcome in zip(running, finished, strict=True):
        outcomes[index] = outcome
    return [outcomes[index] for index in range(len(query.sources))]


def _source_stats(
    outcomes: list[_SourceOutcome], unique: list[Paper], *, requested: int
) -> tuple[SourceStat, ...]:
    """Count, per source, what it returned and what it is credited with.

    A de-duplicated paper keeps the ``source`` / ``source_id`` of its first
    occurrence (see ``dedup.merge_papers``), so it is credited to the first source
    whose results contain that pair. Every unique paper is credited exactly
    once, which makes the ``after_dedup`` values add up to ``len(unique)``.

    Example: arXiv returns 3 records and OpenAlex returns 3, two of which are
    the same papers as arXiv's. With arXiv named first the stats read
    ``arxiv: returned 3, after_dedup 3`` and ``openalex: returned 3,
    after_dedup 1``.
    """
    owner: dict[tuple[str, str], int] = {}
    for index, outcome in enumerate(outcomes):
        for paper in outcome.papers:
            owner.setdefault((paper.source, paper.source_id), index)
    credited = [0] * len(outcomes)
    for paper in unique:
        index = owner.get((paper.source, paper.source_id))
        if index is not None:
            credited[index] += 1
    return tuple(
        SourceStat(
            source=outcome.source,
            requested=requested,
            returned=len(outcome.papers),
            after_dedup=credited[index],
            status=outcome.status,
            detail=outcome.detail,
        )
        for index, outcome in enumerate(outcomes)
    )


def _apply_query_filters(
    ranked: list[RankedPaper], query: Query
) -> list[RankedPaper]:
    """Apply every ``Query`` filter, for all sources, after ranking.

    Filters live here and not in the source plugins so that they hold for
    every source (see ``compliance-auditor`` "Query semantics are enforced in
    core"). They run on the ranked entries, so each surviving paper keeps the
    score that explains its position.
    """
    ordered = ranked
    if query.top_tier_only:
        before = len(ordered)
        ordered = [entry for entry in ordered if is_top_tier(entry.paper)]
        _LOG.info(
            "top-tier filter kept %d / %d papers", len(ordered), before
        )
    if query.min_citations is not None:
        # Apply min_citations across EVERY source here, not just the one source
        # (semantic_scholar) that supports it as an API parameter. Papers whose
        # source doesn't report a citation count (citation_count is None — e.g.
        # dblp / doaj / hal / arxiv) are KEPT: an unknown count must not be
        # treated as zero and silently dropped.
        before = len(ordered)
        ordered = [
            entry
            for entry in ordered
            if entry.paper.citation_count is None
            or entry.paper.citation_count >= query.min_citations
        ]
        _LOG.info(
            "min-citations(>=%d) filter kept %d / %d papers (unknown counts kept)",
            query.min_citations, len(ordered), before,
        )
    if query.year_from is not None or query.year_to is not None:
        # Pipeline-level year guard. Most source plugins already filter by year,
        # but scrape sources (scholar / ieee) do it loosely, so enforce the
        # range once here for ALL sources. Papers with an unknown year are KEPT
        # (uncertainty must not silently drop a possibly-in-range paper).
        before = len(ordered)
        ordered = [
            entry
            for entry in ordered
            if _in_year_range(entry.paper.year, query.year_from, query.year_to)
        ]
        _LOG.info(
            "year filter [%s..%s] kept %d / %d papers (unknown years kept)",
            query.year_from or "", query.year_to or "", len(ordered), before,
        )
    return ordered


def _diagnose(
    kept: list[RankedPaper], source_stats: tuple[SourceStat, ...] = ()
) -> SearchDiagnostics:
    """Record why each surviving paper ranks where it does, and the advice.

    ``kept`` is the ranked list after the filters and the ``max_results`` cut,
    so positions are renumbered 1..n to match the collection the caller sees
    (a filter may have removed the papers that held ranks 2 and 3).

    The pruning recommendations are advice. Every paper in ``kept`` stays in
    the collection, whatever the advice says.

    ``source_stats`` is stored as given. It describes the sources before the
    filters, so it is not recomputed from ``kept``.
    """
    final = [
        dataclasses.replace(entry, rank=position)
        for position, entry in enumerate(kept, start=1)
    ]
    scores = tuple(
        PaperScore(paper_key=entry.paper.dedup_key(), rank=entry.rank, score=entry.score)
        for entry in final
    )
    return SearchDiagnostics(
        scores=scores,
        pruning=recommend_pruning(final),
        source_stats=source_stats,
    )


async def _safe_search(fetcher, query: Query, source: str) -> _SourceOutcome:
    """Run one source's search with retry-on-RateLimitError + backoff.

    ``source`` is the name the query asked for. Every return is a
    ``_SourceOutcome`` so the caller can report, per source, how many records
    came back and why a source came back empty.

    A ``RateLimitError`` (HTTP 429 normalised by the source plugin) gets
    exponential backoff up to ``RATE_LIMIT_RETRY_ATTEMPTS`` total attempts.
    Other ``FetchError`` types short-circuit immediately because they
    indicate a misconfiguration or a parse failure that retrying won't fix.

    Other sources continue concurrently via ``asyncio.gather`` so a single
    slow source doesn't block the whole search.

    The final ``except Exception`` is the containment boundary that makes the
    paragraph above true. Source plugins normalise the failures they *expect*
    into ``FetchError``, but an upstream schema change reaches the parser as a
    plain ``KeyError`` / ``TypeError`` / ``AttributeError``, and
    ``asyncio.gather`` propagates the first such exception — discarding the
    results every other source already returned. One publisher renaming a JSON
    field must degrade to "that source returned nothing", not to "the search
    crashed". ``asyncio.CancelledError`` is deliberately NOT caught (it is a
    ``BaseException`` in 3.8+, so ``except Exception`` already lets a real
    cancellation through).

    Anti-pattern this replaces::

        except FetchError:      # only the expected shapes
            return []
        # KeyError from parse_work(...) escapes -> whole search dies

    Example: with sources ``("openalex", "arxiv")`` where OpenAlex's parser
    raises ``KeyError``, the search now returns the arXiv papers and logs
    ``Source openalex raised an unexpected error``.
    """
    for attempt in range(1, RATE_LIMIT_RETRY_ATTEMPTS + 1):
        try:
            return _SourceOutcome(source, papers=tuple(await fetcher.search(query)))
        except RateLimitError as err:
            if attempt >= RATE_LIMIT_RETRY_ATTEMPTS:
                _LOG.warning(
                    "Source %s gave up after %d rate-limit retries: %s",
                    source, RATE_LIMIT_RETRY_ATTEMPTS, err,
                )
                return _SourceOutcome(
                    source,
                    status=SourceStatus.RATE_LIMITED,
                    detail=(
                        f"gave up after {RATE_LIMIT_RETRY_ATTEMPTS} "
                        f"rate-limit retries: {err}"
                    ),
                )
            wait = RATE_LIMIT_RETRY_BASE_SECONDS * (2 ** (attempt - 1))
            _LOG.info(
                "Source %s rate-limited; sleeping %.1fs before retry %d/%d",
                source, wait, attempt + 1, RATE_LIMIT_RETRY_ATTEMPTS,
            )
            await asyncio.sleep(wait)
        except FetchError as err:
            _LOG.warning("Source %s failed: %s", source, err)
            return _SourceOutcome(source, status=SourceStatus.FAILED, detail=str(err))
        except Exception as err:  # noqa: BLE001 — containment boundary, see docstring
            _LOG.warning(
                "Source %s raised an unexpected error (%s: %s); "
                "skipping it and keeping the other sources' results",
                source, type(err).__name__, err,
            )
            return _SourceOutcome(
                source,
                status=SourceStatus.FAILED,
                detail=f"{type(err).__name__}: {err}",
            )
    return _SourceOutcome(source, status=SourceStatus.FAILED, detail="no attempt made")


def _in_year_range(
    year: int | None, year_from: int | None, year_to: int | None
) -> bool:
    """True if ``year`` is within ``[year_from, year_to]`` (None bound = open).

    Unlike the per-source ``in_year_range`` helpers (which drop year-less
    records), this pipeline guard KEEPS a paper whose year is unknown — at this
    stage the source already chose to return it, so an unknown year is treated
    as "possibly in range" rather than silently filtered out.
    """
    if year is None:
        return True
    if year_from is not None and year < year_from:
        return False
    return not (year_to is not None and year > year_to)


async def run_single_paper(identifier: PaperIdentifier) -> PaperCollection:
    """Fetch exactly one paper by its identifier and wrap it in a collection.

    The returned PaperCollection has a synthetic Query whose `keywords` is the
    raw identifier value, so exporters can render a sensible title/filename
    without special-casing single-paper mode.
    """
    source = identifier.preferred_source
    fetcher = load_fetcher(source)
    paper = await fetcher.fetch_by_id(identifier.value)
    synthetic_query = Query(
        keywords=identifier.value,
        sources=(source,),
        max_results=1,
    )
    return PaperCollection(query=synthetic_query, papers=(paper,))


async def enrich_collection(
    collection: PaperCollection,
    *,
    language: str = "en",
    model: str | None = None,
    concurrency: int = _ENRICH_CONCURRENCY,
) -> PaperCollection:
    """Download each paper's PDF, summarise it with an LLM, attach the result.

    Papers without a ``pdf_url`` or whose PDF can't be fetched / parsed pass
    through unchanged — the exporter then falls back to the abstract-based
    deck. Enrichments run concurrently but a semaphore caps how many run at
    once (``concurrency``, default ``_ENRICH_CONCURRENCY``) so a large
    collection doesn't fire one Anthropic API call + one PDF download per paper
    all at once and trip the API's rate limit. Total wall-clock is roughly
    ``ceil(n / concurrency) * per-paper time``.

    Example: ``enrich_collection(coll, concurrency=2)`` processes at most two
    papers in flight at a time.
    """
    sem = asyncio.Semaphore(max(1, concurrency))

    async def _bounded(paper: Paper) -> Paper:
        async with sem:
            return await _enrich_one(paper, language=language, model=model)

    enriched_papers = await asyncio.gather(
        *(_bounded(paper) for paper in collection.papers)
    )
    # ``replace`` keeps ``diagnostics``: a summary changes neither a paper's
    # identity key nor the score that ranked it.
    return dataclasses.replace(collection, papers=tuple(enriched_papers))


async def _enrich_one(
    paper: Paper, *, language: str, model: str | None
) -> Paper:
    if not paper.pdf_url:
        _LOG.info(
            "skip enrichment for %s (%s): no pdf_url", paper.bibtex_key(), paper.source
        )
        return paper
    try:
        from thesisagents.intelligence.pdf import fetch_and_extract
        from thesisagents.intelligence.summarise import summarise_paper
    except ImportError as err:
        raise ConfigError(
            "intelligence extras not installed; "
            "run `pip install thesisagents[intelligence]`"
        ) from err
    try:
        pdf = await fetch_and_extract(paper.pdf_url, source=paper.source)
    except (FetchError, ThesisAgentsError) as err:
        _LOG.warning("PDF fetch failed for %s: %s", paper.bibtex_key(), err)
        return paper
    try:
        summary = await asyncio.to_thread(
            summarise_paper, paper, pdf, language=language, model=model
        )
    except Exception as err:  # noqa: BLE001  # anthropic client raises various, incl. ThesisAgentsError
        _LOG.warning("summarisation failed for %s: %s", paper.bibtex_key(), err)
        return paper
    if summary.is_empty():
        return paper
    return dataclasses.replace(paper, summary=summary)
