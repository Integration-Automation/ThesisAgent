"""Post-dedup PDF resolver — fill missing pdf_url from open-access aggregators.

Why this exists
---------------
Most IEEE / ACM / Springer / Elsevier papers come back from their
respective source plugins with ``pdf_url=None`` because the publisher
sites are paywalled even when the paper itself is open access. The OA
copy almost always exists somewhere else — the author's institutional
repository, an arXiv preprint, ResearchGate, etc. — and Unpaywall
indexes ~50M of them keyed by DOI.

This module runs after dedup and tries two strategies in order for
every paper that still lacks a pdf_url:

1. **Unpaywall** (https://unpaywall.org/products/api). Free, no API
   key required, but needs an email in the query string per their
   politeness contract. Pulled from ``AUTOPAPERTOPPT_CONTACT_EMAIL``
   (same env var Crossref / OpenAlex use); skipped silently when
   unset, with a one-time WARNING log so the user knows what they're
   missing.

2. **arXiv title search**. For papers without a DOI (or where
   Unpaywall returned no hit), search arXiv with the paper's title
   and accept the first result whose normalised title matches
   exactly. Covers the many CS papers that have an arXiv preprint
   but reach the pipeline via OpenAlex / Crossref / DBLP without
   the arXiv ID populated.

Both lookups are best-effort: any failure logs at DEBUG and the
paper passes through unchanged. The resolver never raises.
"""

from __future__ import annotations

import asyncio
import dataclasses
import os
from typing import Any

import httpx

from autopapertoppt.core.exceptions import FetchError
from autopapertoppt.core.models import Paper, PaperCollection, Query
from autopapertoppt.fetchers.http import get_client
from autopapertoppt.utils.logging import get_logger

_LOG = get_logger(__name__)

_UNPAYWALL_ENDPOINT = "https://api.unpaywall.org/v2"
_UNPAYWALL_SOURCE = "unpaywall"
_LOOKUP_TIMEOUT_SECONDS = 10.0
_CONCURRENCY = 5

# One-shot warning so we don't spam logs for every paper in a large run.
_email_warning_emitted = False


async def resolve_oa_pdfs(collection: PaperCollection) -> PaperCollection:
    """Try to fill ``pdf_url`` for every paper currently missing one.

    Returns a new ``PaperCollection`` with the same query and same
    paper count. Papers that already have ``pdf_url`` pass through
    unchanged.
    """
    missing = sum(1 for p in collection.papers if not p.pdf_url)
    if missing == 0:
        return collection

    _LOG.info(
        "OA resolver: looking up %d / %d papers without pdf_url",
        missing,
        len(collection.papers),
    )

    semaphore = asyncio.Semaphore(_CONCURRENCY)
    resolved = await asyncio.gather(
        *(_resolve_one(paper, semaphore) for paper in collection.papers)
    )
    found = sum(
        1
        for old, new in zip(collection.papers, resolved, strict=True)
        if not old.pdf_url and new.pdf_url
    )
    if found:
        _LOG.info(
            "OA resolver: filled %d / %d missing pdf_url (Unpaywall + arXiv)",
            found,
            missing,
        )
    return PaperCollection(query=collection.query, papers=tuple(resolved))


async def _resolve_one(paper: Paper, semaphore: asyncio.Semaphore) -> Paper:
    if paper.pdf_url:
        return paper
    async with semaphore:
        # 1. Unpaywall by DOI — fastest path, highest precision.
        if paper.doi:
            pdf = await _query_unpaywall(paper.doi)
            if pdf:
                _LOG.debug("Unpaywall hit for %s: %s", paper.bibtex_key(), pdf)
                return dataclasses.replace(paper, pdf_url=pdf)
        # 2. arXiv title search — covers DOI-less papers + DOIs missed
        # by Unpaywall.
        pdf = await _query_arxiv_title(paper)
        if pdf:
            _LOG.debug("arXiv title hit for %s: %s", paper.bibtex_key(), pdf)
            return dataclasses.replace(paper, pdf_url=pdf)
    return paper


async def _query_unpaywall(doi: str) -> str | None:
    """Look up a DOI in Unpaywall; return the best OA PDF URL or None."""
    email = os.environ.get("AUTOPAPERTOPPT_CONTACT_EMAIL", "").strip()
    if not email:
        _warn_once_about_email()
        return None
    client = await get_client(_UNPAYWALL_SOURCE)
    try:
        response = await asyncio.wait_for(
            client.get(
                f"{_UNPAYWALL_ENDPOINT}/{doi}",
                params={"email": email},
            ),
            timeout=_LOOKUP_TIMEOUT_SECONDS,
        )
    except (TimeoutError, httpx.HTTPError, FetchError) as err:
        _LOG.debug("Unpaywall lookup failed for %s: %s", doi, err)
        return None
    if response.status_code == 404:
        return None  # not indexed
    if response.status_code != 200:
        _LOG.debug(
            "Unpaywall returned %s for %s: %s",
            response.status_code, doi, response.text[:128],
        )
        return None
    try:
        data: dict[str, Any] = response.json()
    except ValueError:
        return None
    best_oa = data.get("best_oa_location") or {}
    candidate = (best_oa.get("url_for_pdf") or "").strip()
    if candidate.startswith("https://"):
        return candidate
    return None


async def _query_arxiv_title(paper: Paper) -> str | None:
    """Search arXiv by title; return the matching paper's PDF URL or None.

    Match is exact on the normalised title (alphanumeric + lowercase)
    so a "transformer" paper doesn't accidentally claim someone else's
    "transformer architecture for X" preprint.
    """
    if not paper.title:
        return None
    # Skip the round-trip if the paper is already from arXiv — its
    # plugin would have populated pdf_url at parse time if a PDF
    # existed.
    if paper.source == "arxiv":
        return None
    try:
        from autopapertoppt.fetchers.base import load_fetcher
    except ImportError:
        return None
    try:
        fetcher = load_fetcher("arxiv")
    except Exception:  # noqa: BLE001 — load failures must not break the resolver
        return None

    # arXiv's API supports field-restricted queries; ti:"<title>" looks
    # only at the title field. Pull the top 3 in case the first is a
    # later version of a different paper with similar words.
    query = Query(
        keywords=f'ti:"{paper.title}"',
        sources=("arxiv",),
        max_results=3,
    )
    try:
        results = await fetcher.search(query)
    except Exception as err:  # noqa: BLE001 — best-effort
        _LOG.debug("arXiv title search failed for %r: %s", paper.title, err)
        return None

    target = _normalise_title(paper.title)
    for candidate in results:
        if (
            _normalise_title(candidate.title) == target
            and candidate.pdf_url
            and candidate.pdf_url.startswith("https://")
        ):
            return candidate.pdf_url
    return None


def _normalise_title(text: str) -> str:
    """Lowercase + drop non-alphanumeric for fuzzy title comparison."""
    return "".join(c.lower() for c in text if c.isalnum())


def _warn_once_about_email() -> None:
    """Log a single WARNING line when CONTACT_EMAIL is unset.

    Module-global flag rather than logging-stdlib filter because we
    want the warning per-process, not per-logger-handler, and the
    fewer moving parts the better.
    """
    global _email_warning_emitted  # noqa: PLW0603 — intentional one-shot flag
    if _email_warning_emitted:
        return
    _email_warning_emitted = True
    _LOG.warning(
        "OA resolver: AUTOPAPERTOPPT_CONTACT_EMAIL is not set; "
        "Unpaywall lookups (the biggest PDF coverage win for IEEE / "
        "ACM / Springer / Elsevier papers) will be skipped. Set the "
        "env var to your email to enable them."
    )
