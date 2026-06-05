"""Async pipeline: fetch from N sources in parallel → dedup → rank → collection.

Also exposes ``run_single_paper`` for "fetch one paper by ID" workflows and
``enrich_collection`` which augments each paper with an LLM-generated
``PaperSummary`` built from its full PDF text.
"""

from __future__ import annotations

import asyncio
import dataclasses

from thesisagents.core.constants import (
    RATE_LIMIT_RETRY_ATTEMPTS,
    RATE_LIMIT_RETRY_BASE_SECONDS,
)
from thesisagents.core.dedup import dedupe
from thesisagents.core.exceptions import (
    ConfigError,
    FetchError,
    RateLimitError,
    ThesisAgentsError,
)
from thesisagents.core.identifiers import PaperIdentifier
from thesisagents.core.models import Paper, PaperCollection, Query
from thesisagents.core.oa_resolver import resolve_oa_pdfs
from thesisagents.core.ranking import rank
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
    """
    fetchers = [
        loaded
        for loaded in (_load_fetcher_safe(name) for name in query.sources)
        if loaded is not None
    ]
    per_source_query = query.with_max(query.max_results)
    results = await asyncio.gather(
        *(_safe_search(fetcher, per_source_query) for fetcher in fetchers),
        return_exceptions=False,
    )
    flat: list[Paper] = []
    for source_papers in results:
        flat.extend(source_papers)
    unique = dedupe(flat)
    ordered = rank(unique, keywords=query.keywords)
    if query.top_tier_only:
        before = len(ordered)
        ordered = [paper for paper in ordered if is_top_tier(paper)]
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
            paper
            for paper in ordered
            if paper.citation_count is None
            or paper.citation_count >= query.min_citations
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
            paper
            for paper in ordered
            if _in_year_range(paper.year, query.year_from, query.year_to)
        ]
        _LOG.info(
            "year filter [%s..%s] kept %d / %d papers (unknown years kept)",
            query.year_from or "", query.year_to or "", len(ordered), before,
        )
    collection = PaperCollection(
        query=query, papers=tuple(ordered[: query.max_results])
    )
    if resolve_oa:
        collection = await resolve_oa_pdfs(collection)
    return collection


def _load_fetcher_safe(name: str):
    try:
        return load_fetcher(name)
    except ConfigError as err:
        _LOG.warning("Source %s disabled: %s", name, err)
        return None


async def _safe_search(fetcher, query: Query) -> list[Paper]:
    """Run one source's search with retry-on-RateLimitError + backoff.

    A ``RateLimitError`` (HTTP 429 normalised by the source plugin) gets
    exponential backoff up to ``RATE_LIMIT_RETRY_ATTEMPTS`` total attempts.
    Other ``FetchError`` types short-circuit immediately because they
    indicate a misconfiguration or a parse failure that retrying won't fix.

    Other sources continue concurrently via ``asyncio.gather`` so a single
    slow source doesn't block the whole search.
    """
    source = fetcher.config.name
    for attempt in range(1, RATE_LIMIT_RETRY_ATTEMPTS + 1):
        try:
            return await fetcher.search(query)
        except RateLimitError as err:
            if attempt >= RATE_LIMIT_RETRY_ATTEMPTS:
                _LOG.warning(
                    "Source %s gave up after %d rate-limit retries: %s",
                    source, RATE_LIMIT_RETRY_ATTEMPTS, err,
                )
                return []
            wait = RATE_LIMIT_RETRY_BASE_SECONDS * (2 ** (attempt - 1))
            _LOG.info(
                "Source %s rate-limited; sleeping %.1fs before retry %d/%d",
                source, wait, attempt + 1, RATE_LIMIT_RETRY_ATTEMPTS,
            )
            await asyncio.sleep(wait)
        except FetchError as err:
            _LOG.warning("Source %s failed: %s", source, err)
            return []
    return []


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
    return PaperCollection(query=collection.query, papers=tuple(enriched_papers))


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
