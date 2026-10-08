"""Crossref reference lists.

Endpoints:
- A work:      GET https://api.crossref.org/works/{doi}  -> ``message.reference``
- Several DOIs: GET /works?filter=doi:A,doi:B,...&rows=N

Backward direction only. Crossref does not list the works citing a DOI
without Cited-by membership, so ``cited_by`` reports that it is not available
and the snowball asks another provider.

What a reference list really contains: most entries are an unstructured
citation string or a bare DOI, and few carry a title. In the response recorded
for the tests (``10.1145/3292500.3330701``), 7 of 29 references have a DOI and
1 has an ``article-title``. So this provider takes the DOIs, fetches their
records in one further request, and returns those. References without a DOI
are not returned: there is nothing to identify them by.

Rate limit, ``mailto`` and the Plus token are the search fetcher's.
"""

from __future__ import annotations

import os
from urllib.parse import quote

from thesisagents.core.exceptions import CitationNotAvailableError
from thesisagents.core.identifiers import canonical_doi
from thesisagents.core.models import Paper
from thesisagents.fetchers.citations import CitationProvider, get_json
from thesisagents.fetchers.rate_limit import TokenBucket

from .fetcher import CrossrefFetcher
from .parser import parse_record

_SOURCE_NAME = "crossref"
_WORKS_ENDPOINT = "https://api.crossref.org/works"
_PLUS_TOKEN_ENV = "THESISAGENTS_CROSSREF_PLUS_TOKEN"  # noqa: S105  # nosec B105  # env var name, not a secret value
_CONTACT_ENV = "THESISAGENTS_CONTACT_EMAIL"
#: DOIs looked up in one filtered request. Keeps the URL well under any
#: server limit (50 DOIs are about 2 kB) and one request per seed paper.
_MAX_DOIS_PER_REQUEST = 50


class CrossrefCitations(CitationProvider):
    """Reference lists from the Crossref REST API (no citing works)."""

    name = _SOURCE_NAME

    def __init__(self) -> None:
        self._bucket = TokenBucket(CrossrefFetcher.config.rate_limit)

    async def references(self, paper: Paper, limit: int) -> list[Paper]:
        doi = canonical_doi(paper.doi)
        if doi is None:
            raise CitationNotAvailableError(
                _SOURCE_NAME, "Crossref looks a paper up by DOI and this one has none"
            )
        work = await self._get(f"{_WORKS_ENDPOINT}/{quote(doi, safe='/')}")
        dois = _reference_dois((work.get("message") or {}).get("reference") or [])
        dois = dois[: min(limit, _MAX_DOIS_PER_REQUEST)]
        if not dois:
            return []
        found = await self._get(
            _WORKS_ENDPOINT,
            params={
                "filter": ",".join(f"doi:{item}" for item in dois),
                "rows": str(len(dois)),
            },
        )
        by_doi: dict[str, Paper] = {}
        for item in (found.get("message") or {}).get("items") or []:
            key = canonical_doi(item.get("DOI"))
            if key:
                by_doi[key] = parse_record(item)
        # Crossref answers in its own order. Return the reference list's.
        return [by_doi[item] for item in dois if item in by_doi]

    async def cited_by(self, paper: Paper, limit: int) -> list[Paper]:
        _ = paper, limit
        raise CitationNotAvailableError(
            _SOURCE_NAME, "Crossref lists a work's references, not the works citing it"
        )

    async def _get(self, url: str, *, params: dict[str, str] | None = None) -> dict:
        query = dict(params or {})
        mailto = (os.environ.get(_CONTACT_ENV) or "").strip()
        if mailto:
            query["mailto"] = mailto
        headers: dict[str, str] = {}
        plus_token = (os.environ.get(_PLUS_TOKEN_ENV) or "").strip()
        if plus_token:
            headers["Crossref-Plus-API-Token"] = f"Bearer {plus_token}"
        return await get_json(
            _SOURCE_NAME, self._bucket, url, params=query, headers=headers
        )


def _reference_dois(references: list[dict]) -> list[str]:
    """Canonical DOIs of a Crossref reference list, in order, without repeats.

    Example: ``[{"DOI": "10.1/A"}, {"unstructured": "..."}, {"DOI": "10.1/a"}]``
    gives ``["10.1/a"]``.
    """
    seen: dict[str, None] = {}
    for reference in references:
        if not isinstance(reference, dict):
            continue
        doi = canonical_doi(reference.get("DOI"))
        if doi:
            seen.setdefault(doi, None)
    return list(seen)
