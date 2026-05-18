"""Post-dedup PDF resolver — fill missing pdf_url from open-access aggregators.

Why this exists
---------------
Most IEEE / ACM / Springer / Elsevier papers come back from their
respective source plugins with ``pdf_url=None`` because the publisher
sites are paywalled even when the paper itself is open access. The OA
copy almost always exists somewhere else — the author's institutional
repository, an arXiv preprint, ResearchGate, etc.

This module runs after dedup and tries four strategies in order for
every paper that still lacks a pdf_url:

1. **arXiv-ID direct**. If the paper carries ``arxiv_id`` (set by
   the openalex / pubmed / crossref / semantic_scholar parsers when
   the upstream identified an arXiv preprint), turn it into
   ``https://arxiv.org/pdf/{arxiv_id}.pdf`` directly. Zero network
   round-trip; highest precision; fastest.

2. **Unpaywall** (https://api.unpaywall.org/v2). Free, no API key,
   ~50M papers. Needs ``AUTOPAPERTOPPT_CONTACT_EMAIL`` for politeness
   (skipped silently when unset).

3. **Semantic Scholar OA index** (https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}).
   S2's ``openAccessPdf`` index is partially disjoint from Unpaywall;
   when one misses the other often hits. Free, no API key required
   (rate-limited to ~1 req/s anonymous; an
   ``AUTOPAPERTOPPT_S2_API_KEY`` raises that).

4. **CORE.ac.uk** (https://api.core.ac.uk/v3/search/works). Aggregator
   of 200M+ OA repository items — institutional repos, regional
   preprint servers, OA journals. Needs ``AUTOPAPERTOPPT_CORE_API_KEY``
   (free at https://core.ac.uk/services/api); skipped silently when
   unset.

5. **arXiv title search**. For papers without DOI / arxiv_id, search
   arXiv with the paper's title. Exact-match on the normalised title
   (alphanumeric + lowercase) so loosely-similar titles do not get
   adopted by accident.

Every lookup is best-effort: any failure logs at DEBUG and the
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
_S2_ENDPOINT = "https://api.semanticscholar.org/graph/v1/paper"
_S2_SOURCE = "semantic_scholar_oa"
_CORE_ENDPOINT = "https://api.core.ac.uk/v3/search/works"
_CORE_SOURCE = "core_ac_uk"
_LOOKUP_TIMEOUT_SECONDS = 10.0
_CONCURRENCY = 5

# One-shot warnings so we don't spam logs for every paper in a large run.
_email_warning_emitted = False
_core_warning_emitted = False


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


#: DOI-keyed OA lookup strategies, tried in order until one returns a URL.
_DOI_STRATEGIES = (
    ("Unpaywall", lambda doi: _query_unpaywall(doi)),
    ("S2 OA", lambda doi: _query_semantic_scholar(doi)),
    ("CORE", lambda doi: _query_core(doi)),
)


async def _resolve_one(paper: Paper, semaphore: asyncio.Semaphore) -> Paper:
    if paper.pdf_url:
        return paper
    async with semaphore:
        pdf = await _try_all_strategies(paper)
    if pdf:
        return dataclasses.replace(paper, pdf_url=pdf)
    return paper


async def _try_all_strategies(paper: Paper) -> str | None:
    """Run every OA strategy in priority order, returning the first hit."""
    key = paper.bibtex_key()
    # 1. arXiv-ID direct — no round-trip, highest precision.
    if paper.arxiv_id:
        pdf = _arxiv_id_to_pdf(paper.arxiv_id)
        if pdf:
            _LOG.debug("arxiv_id direct hit for %s: %s", key, pdf)
            return pdf
    # 2-4. DOI-keyed external aggregators.
    if paper.doi:
        for label, query in _DOI_STRATEGIES:
            pdf = await query(paper.doi)
            if pdf:
                _LOG.debug("%s hit for %s: %s", label, key, pdf)
                return pdf
    # 5. arXiv title search — last resort for DOI-less papers.
    pdf = await _query_arxiv_title(paper)
    if pdf:
        _LOG.debug("arXiv title hit for %s: %s", key, pdf)
        return pdf
    return None


def _arxiv_id_to_pdf(arxiv_id: str) -> str | None:
    """Derive the canonical arXiv PDF URL from an arXiv ID.

    Strips any trailing ``v<N>`` version suffix because arXiv resolves
    bare IDs to the latest version automatically.
    """
    cleaned = arxiv_id.strip()
    if not cleaned:
        return None
    # 1706.03762v2 → 1706.03762; cs.LG/0001001v1 → cs.LG/0001001
    if "v" in cleaned:
        base, _, tail = cleaned.rpartition("v")
        if tail.isdigit() and base:
            cleaned = base
    return f"https://arxiv.org/pdf/{cleaned}.pdf"


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


async def _query_semantic_scholar(doi: str) -> str | None:
    """Look up a DOI in Semantic Scholar's OA index."""
    client = await get_client(_S2_SOURCE)
    try:
        response = await asyncio.wait_for(
            client.get(
                f"{_S2_ENDPOINT}/DOI:{doi}",
                params={"fields": "openAccessPdf"},
            ),
            timeout=_LOOKUP_TIMEOUT_SECONDS,
        )
    except (TimeoutError, httpx.HTTPError, FetchError) as err:
        _LOG.debug("S2 OA lookup failed for %s: %s", doi, err)
        return None
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        _LOG.debug(
            "S2 returned %s for %s: %s",
            response.status_code, doi, response.text[:128],
        )
        return None
    try:
        data: dict[str, Any] = response.json()
    except ValueError:
        return None
    pdf_obj = data.get("openAccessPdf") or {}
    candidate = (pdf_obj.get("url") or "").strip() if isinstance(pdf_obj, dict) else ""
    if candidate.startswith("https://"):
        return candidate
    return None


async def _query_core(doi: str) -> str | None:
    """Look up a DOI on CORE.ac.uk for OA repository copies."""
    api_key = os.environ.get("AUTOPAPERTOPPT_CORE_API_KEY", "").strip()
    if not api_key:
        _warn_once_about_core()
        return None
    client = await get_client(_CORE_SOURCE)
    try:
        response = await asyncio.wait_for(
            client.get(
                _CORE_ENDPOINT,
                params={"q": f'doi:"{doi}"', "limit": "1"},
                headers={"Authorization": f"Bearer {api_key}"},
            ),
            timeout=_LOOKUP_TIMEOUT_SECONDS,
        )
    except (TimeoutError, httpx.HTTPError, FetchError) as err:
        _LOG.debug("CORE lookup failed for %s: %s", doi, err)
        return None
    if response.status_code != 200:
        _LOG.debug(
            "CORE returned %s for %s: %s",
            response.status_code, doi, response.text[:128],
        )
        return None
    try:
        data: dict[str, Any] = response.json()
    except ValueError:
        return None
    results = data.get("results") or []
    if not results:
        return None
    first = results[0]
    # CORE's `downloadUrl` is the direct PDF; fall back to `fullTextLinks`
    # otherwise.
    candidate = (first.get("downloadUrl") or "").strip()
    if candidate.startswith("https://"):
        return candidate
    for link in first.get("fullTextLinks") or []:
        url = (link.get("url") or "").strip() if isinstance(link, dict) else ""
        if url.startswith("https://"):
            return url
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
    """Log a single WARNING line when CONTACT_EMAIL is unset."""
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


def _warn_once_about_core() -> None:
    """Log a single WARNING line when CORE_API_KEY is unset.

    CORE is an optional layer on top of Unpaywall + S2 + arXiv; the
    warning is INFO-level rather than WARNING because most users
    will be fine without it.
    """
    global _core_warning_emitted  # noqa: PLW0603 — intentional one-shot flag
    if _core_warning_emitted:
        return
    _core_warning_emitted = True
    _LOG.info(
        "OA resolver: AUTOPAPERTOPPT_CORE_API_KEY is not set; CORE.ac.uk "
        "lookups (institutional / regional OA repos) will be skipped. "
        "Get a free key at https://core.ac.uk/services/api to enable."
    )
