"""Source-neutral interface for citation links between papers.

Why an interface of its own: "what does this paper cite" and "who cites this
paper" are answered by some sources (Semantic Scholar, OpenAlex, Crossref) and
not by others, and each answers through a different endpoint with a different
identifier. Putting that behind one small interface keeps the snowball search
(``thesisagents/core/snowball.py``) free of any source's URL or JSON shape, the
same split ``Fetcher`` makes for keyword search.

A provider lives inside its source plugin (``thesisagents/sources/<name>/
citations.py``) and the plugin's ``__init__`` exposes it as
``citation_provider_class``, next to ``fetcher_class``.
"""

from __future__ import annotations

import importlib
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from thesisagents.core.exceptions import (
    CitationNotAvailableError,
    ConfigError,
    ParseError,
    RateLimitError,
    SourceUnavailableError,
)
from thesisagents.core.models import Paper
from thesisagents.fetchers.http import get_client
from thesisagents.fetchers.rate_limit import TokenBucket
from thesisagents.utils.logging import get_logger

_LOG = get_logger(__name__)

_HTTP_NOT_FOUND = 404
_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_SERVER_ERROR_FLOOR = 500
_HTTP_CLIENT_ERROR_FLOOR = 400
_ERROR_BODY_CHARS = 256


async def get_json(
    source: str,
    bucket: TokenBucket,
    url: str,
    *,
    params: Mapping[str, str] | None = None,
    headers: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """GET ``url`` for a citation lookup and return its JSON object.

    One request path for every citation provider, so the token bucket, the
    shared HTTPS-only client and the status mapping are not copied into each
    plugin. The mapping differs from the search fetchers' in one place, which
    is why they are not reused: here a 404 is ``CitationNotAvailableError``
    ("this provider does not know the paper, try the next one"), where a
    search fetcher reports it as a parse error.

    Raises ``RateLimitError`` on 429, ``SourceUnavailableError`` on a network
    failure or 5xx, ``ParseError`` on any other 4xx or a body that is not a
    JSON object.

    Example::

        data = await get_json(
            "openalex", self._bucket, "https://api.openalex.org/works",
            params={"filter": "cites:W2949676527", "per-page": "20"},
        )
    """
    await bucket.acquire()
    client = await get_client(source)
    try:
        response = await client.get(
            url, params=dict(params or {}), headers=dict(headers or {})
        )
    except Exception as err:
        raise SourceUnavailableError(source, f"network error: {err}") from err
    status = response.status_code
    if status == _HTTP_NOT_FOUND:
        raise CitationNotAvailableError(source, "paper not known to this provider")
    if status == _HTTP_TOO_MANY_REQUESTS:
        raise RateLimitError(source, "rate limit hit during a citation lookup")
    if status >= _HTTP_SERVER_ERROR_FLOOR:
        raise SourceUnavailableError(source, f"server error {status}")
    if status >= _HTTP_CLIENT_ERROR_FLOOR:
        raise ParseError(
            source, f"client error {status}: {response.text[:_ERROR_BODY_CHARS]}"
        )
    try:
        payload = response.json()
    except ValueError as err:
        raise ParseError(source, f"invalid JSON: {err}") from err
    if not isinstance(payload, dict):
        raise ParseError(source, "expected a JSON object")
    return payload


class CitationProvider(ABC):
    """Strategy every citation-capable source plugin implements.

    Both methods return normalised ``Paper`` records, at most ``limit`` of
    them. They raise ``CitationNotAvailableError`` when the provider has no
    answer for this paper (no identifier it understands, paper unknown to it,
    direction unsupported), and another ``FetchError`` when the provider
    itself is broken or rate limited. An empty list means "the provider knows
    the paper and it has none".

    Example::

        provider = load_citation_provider("openalex")
        cited = await provider.references(paper, limit=20)
        citing = await provider.cited_by(paper, limit=20)
    """

    #: The source name, as in ``Query.sources`` and ``Paper.source``.
    name: str

    @abstractmethod
    async def references(self, paper: Paper, limit: int) -> list[Paper]:
        """Papers that ``paper`` cites (backward snowballing)."""

    @abstractmethod
    async def cited_by(self, paper: Paper, limit: int) -> list[Paper]:
        """Papers that cite ``paper`` (forward snowballing)."""


def load_citation_provider(name: str) -> CitationProvider:
    """Load and instantiate the citation provider of source plugin ``name``.

    Raises ``ConfigError`` when the plugin does not exist or offers no
    citation provider, the same way ``load_fetcher`` reports an unusable
    source, so a caller can skip it and carry on with the others.

    Example: ``load_citation_provider("arxiv")`` raises ``ConfigError``
    because arXiv exposes no citation links.
    """
    try:
        module = importlib.import_module(f"thesisagents.sources.{name}")
    except ImportError as err:
        raise ConfigError(f"unknown or unavailable source plugin: {name}") from err
    provider_class = getattr(module, "citation_provider_class", None)
    if provider_class is None:
        raise ConfigError(f"source plugin '{name}' offers no citation provider")
    instance = provider_class()
    if not isinstance(instance, CitationProvider):
        raise ConfigError(
            f"source plugin '{name}' citation_provider_class did not produce "
            "a CitationProvider"
        )
    _LOG.debug("Loaded citation provider %s", name)
    return instance
