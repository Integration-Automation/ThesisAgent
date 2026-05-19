"""Async pipeline: fetch from N sources in parallel → dedup → rank → collection.

Also exposes ``run_single_paper`` for "fetch one paper by ID" workflows and
``enrich_collection`` which augments each paper with an LLM-generated
``PaperSummary`` built from its full PDF text.
"""

from __future__ import annotations

import asyncio
import dataclasses

from autopapertoppt.core.constants import (
    RATE_LIMIT_RETRY_ATTEMPTS,
    RATE_LIMIT_RETRY_BASE_SECONDS,
)
from autopapertoppt.core.dedup import dedupe
from autopapertoppt.core.exceptions import (
    AutoPaperToPPTError,
    ConfigError,
    FetchError,
    RateLimitError,
)
from autopapertoppt.core.identifiers import PaperIdentifier
from autopapertoppt.core.models import Paper, PaperCollection, Query
from autopapertoppt.core.oa_resolver import resolve_oa_pdfs
from autopapertoppt.core.ranking import rank
from autopapertoppt.core.top_venues import is_top_tier
from autopapertoppt.fetchers.base import load_fetcher
from autopapertoppt.utils.logging import get_logger

_LOG = get_logger(__name__)


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
    ordered = rank(unique)
    if query.top_tier_only:
        before = len(ordered)
        ordered = [paper for paper in ordered if is_top_tier(paper)]
        _LOG.info(
            "top-tier filter kept %d / %d papers", len(ordered), before
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
) -> PaperCollection:
    """Download each paper's PDF, summarise it with an LLM, attach the result.

    Papers without a ``pdf_url`` or whose PDF can't be fetched / parsed pass
    through unchanged — the exporter then falls back to the abstract-based
    deck. Each enrichment runs in its own asyncio task so total wall-clock
    is roughly ``max(per-paper time)`` rather than the sum.
    """
    enriched_papers = await asyncio.gather(
        *(_enrich_one(paper, language=language, model=model) for paper in collection.papers)
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
        from autopapertoppt.intelligence.pdf import fetch_and_extract
        from autopapertoppt.intelligence.summarise import summarise_paper
    except ImportError as err:
        raise ConfigError(
            "intelligence extras not installed; "
            "run `pip install autopapertoppt[intelligence]`"
        ) from err
    try:
        pdf = await fetch_and_extract(paper.pdf_url, source=paper.source)
    except (FetchError, AutoPaperToPPTError) as err:
        _LOG.warning("PDF fetch failed for %s: %s", paper.bibtex_key(), err)
        return paper
    try:
        summary = await asyncio.to_thread(
            summarise_paper, paper, pdf, language=language, model=model
        )
    except (AutoPaperToPPTError, Exception) as err:  # noqa: BLE001  # API client raises various types
        _LOG.warning("summarisation failed for %s: %s", paper.bibtex_key(), err)
        return paper
    if summary.is_empty():
        return paper
    return dataclasses.replace(paper, summary=summary)
