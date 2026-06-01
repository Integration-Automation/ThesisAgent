"""PubMed fetcher via NCBI E-utilities.

esearch.fcgi → PMID list; efetch.fcgi → full XML records.
Rate limit: NCBI caps anonymous traffic at 3 req/s. An ``AUTOPAPERTOPPT_NCBI_API_KEY``
env var raises that to 10 req/s; we expose the env var but don't require it.
"""

from __future__ import annotations

import os

from autopapertoppt.core.exceptions import (
    ParseError,
    RateLimitError,
    SourceUnavailableError,
)
from autopapertoppt.core.models import Paper, Query
from autopapertoppt.fetchers.base import Fetcher, FetcherConfig
from autopapertoppt.fetchers.http import get_client
from autopapertoppt.fetchers.rate_limit import RateLimit
from autopapertoppt.utils.logging import get_logger

from .parser import parse_efetch

_LOG = get_logger(__name__)
_SOURCE_NAME = "pubmed"
_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_ESEARCH = f"{_BASE}/esearch.fcgi"
_EFETCH = f"{_BASE}/efetch.fcgi"
_API_KEY_ENV = "AUTOPAPERTOPPT_NCBI_API_KEY"
_TOOL_NAME = "autopapertoppt"


class PubMedFetcher(Fetcher):
    """Strategy implementation for PubMed."""

    config = FetcherConfig(
        name=_SOURCE_NAME,
        rate_limit=RateLimit(requests_per_second=3.0, burst=1, jitter_seconds=0.1),
        requires_api_key=False,
        enabled_by_default=True,
    )

    async def search(self, query: Query) -> list[Paper]:
        term = self._build_term(query)
        pmids = await self._esearch(term, retmax=query.max_results)
        if not pmids:
            _LOG.info("PubMed esearch returned 0 PMIDs for query=%r", query.keywords)
            return []
        papers = await self._efetch(pmids)
        _LOG.info(
            "PubMed returned %d papers for query=%r (max=%d)",
            len(papers),
            query.keywords,
            query.max_results,
        )
        return papers[: query.max_results]

    async def fetch_by_id(self, identifier: str) -> Paper:
        pmid = identifier.strip()
        if not pmid.isdigit():
            raise ParseError(_SOURCE_NAME, f"invalid PMID: {identifier!r}")
        papers = await self._efetch([pmid])
        if not papers:
            raise ParseError(_SOURCE_NAME, f"no PubMed entry for PMID {pmid}")
        return papers[0]

    @staticmethod
    def _build_term(query: Query) -> str:
        parts: list[str] = [query.keywords]
        if query.year_from is not None or query.year_to is not None:
            lo = query.year_from or 1800
            hi = query.year_to or 3000
            parts.append(f"({lo}:{hi}[dp])")
        return " AND ".join(parts)

    async def _esearch(self, term: str, *, retmax: int) -> list[str]:
        params = self._common_params() | {
            "db": "pubmed",
            "term": term,
            "retmax": str(retmax),
            "retmode": "json",
        }
        data = await self._request_json(_ESEARCH, params=params)
        return list(data.get("esearchresult", {}).get("idlist", []))

    async def _efetch(self, pmids: list[str]) -> list[Paper]:
        params = self._common_params() | {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract",
        }
        text = await self._request_text(_EFETCH, params=params)
        return parse_efetch(text)

    @staticmethod
    def _common_params() -> dict[str, str]:
        params: dict[str, str] = {"tool": _TOOL_NAME, "email": _contact_email()}
        api_key = os.environ.get(_API_KEY_ENV)
        if api_key:
            params["api_key"] = api_key
        return params

    async def _request_json(self, url: str, *, params: dict[str, str]) -> dict:
        text = await self._request_text(url, params=params)
        try:
            import json

            return json.loads(text)
        except ValueError as err:
            raise ParseError(_SOURCE_NAME, f"invalid JSON: {err}") from err

    async def _request_text(self, url: str, *, params: dict[str, str]) -> str:
        await self.bucket.acquire()
        client = await get_client(_SOURCE_NAME)
        try:
            response = await client.get(url, params=params)
        except Exception as err:
            raise SourceUnavailableError(
                _SOURCE_NAME, f"network error: {err}"
            ) from err
        if response.status_code == 429:
            raise RateLimitError(_SOURCE_NAME, "NCBI rate limit hit")
        if response.status_code >= 500:
            raise SourceUnavailableError(
                _SOURCE_NAME, f"server error {response.status_code}"
            )
        if response.status_code >= 400:
            raise ParseError(
                _SOURCE_NAME,
                f"client error {response.status_code}: {response.text[:256]}",
            )
        return response.text


def _contact_email() -> str:
    return os.environ.get("AUTOPAPERTOPPT_CONTACT_EMAIL", "autopapertoppt@example.invalid")
