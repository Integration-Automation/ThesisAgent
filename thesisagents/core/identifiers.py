"""Parse a single-paper identifier (arXiv ID, arXiv URL, DOI, PMID, IEEE
document URL) into a normalised form.

This module lives in core, not under any source plugin, because the CLI / API
needs to classify an identifier before deciding which source plugin can
resolve it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from thesisagents.core.constants import (
    SOURCE_ARXIV,
    SOURCE_IEEE,
    SOURCE_PUBMED,
    SOURCE_SEMANTIC_SCHOLAR,
)


class IdentifierKind(Enum):
    """Which kind of identifier the user gave us."""

    ARXIV = "arxiv"
    DOI = "doi"
    PMID = "pmid"
    IEEE = "ieee"


@dataclass(frozen=True, slots=True)
class PaperIdentifier:
    """A user-supplied paper reference, normalised for fetching."""

    kind: IdentifierKind
    value: str
    """The canonical identifier value (no scheme, no URL wrapping)."""

    @property
    def preferred_source(self) -> str:
        """The source plugin that can resolve this identifier on its own."""
        if self.kind is IdentifierKind.ARXIV:
            return SOURCE_ARXIV
        if self.kind is IdentifierKind.DOI:
            return SOURCE_SEMANTIC_SCHOLAR
        if self.kind is IdentifierKind.PMID:
            return SOURCE_PUBMED
        if self.kind is IdentifierKind.IEEE:
            return SOURCE_IEEE
        raise ValueError(f"no source plugin available yet for {self.kind.value}")


_ARXIV_NEW_RE = re.compile(r"^(\d{4}\.\d{4,5})(v\d+)?$")
_ARXIV_OLD_RE = re.compile(r"^([a-z\-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?$")
_ARXIV_URL_RE = re.compile(
    r"^https?://(?:www\.)?arxiv\.org/(?:abs|pdf)/([^?#\s]+?)(?:\.pdf)?/?$",
    re.IGNORECASE,
)
_ARXIV_PREFIX_RE = re.compile(r"^arxiv\s*:\s*", re.IGNORECASE)

_DOI_PREFIX_RE = re.compile(r"^doi\s*:\s*", re.IGNORECASE)
_DOI_URL_RE = re.compile(r"^https?://(?:dx\.)?doi\.org/(.+)$", re.IGNORECASE)
_DOI_PATTERN_RE = re.compile(r"^10\.\d{4,9}/\S+$")

_PMID_PREFIX_RE = re.compile(r"^pmid\s*:\s*", re.IGNORECASE)
_PMID_URL_RE = re.compile(
    r"^https?://(?:www\.)?(?:pubmed\.ncbi\.nlm\.nih\.gov|ncbi\.nlm\.nih\.gov/pubmed)/(\d+)/?",
    re.IGNORECASE,
)
_PMID_PATTERN_RE = re.compile(r"^\d{6,9}$")

_IEEE_URL_RE = re.compile(
    r"^https?://(?:www\.)?ieeexplore\.ieee\.org/(?:abstract/)?document/(\d+)/?",
    re.IGNORECASE,
)
_IEEE_PREFIX_RE = re.compile(r"^ieee\s*:\s*", re.IGNORECASE)


def parse_identifier(raw: str) -> PaperIdentifier:
    """Classify a raw user-supplied identifier string.

    Accepts:
      - arXiv: ``2401.08741``, ``2401.08741v2``, ``arXiv:2401.08741``,
               ``https://arxiv.org/abs/...``, ``cs.LG/0001001`` (legacy)
      - DOI:   ``10.1234/foo``, ``doi:10.1234/foo``, ``https://doi.org/10.1234/foo``
      - PMID:  ``pmid:12345678``, bare 6-9 digit numerics,
               ``https://pubmed.ncbi.nlm.nih.gov/12345678/``
      - IEEE:  ``https://ieeexplore.ieee.org/document/10965643``,
               ``ieee:10965643``
    """
    if raw is None or not raw.strip():
        raise ValueError("identifier cannot be empty")
    candidate = raw.strip()

    arxiv = _try_parse_arxiv(candidate)
    if arxiv is not None:
        return PaperIdentifier(IdentifierKind.ARXIV, arxiv)

    ieee = _try_parse_ieee(candidate)
    if ieee is not None:
        return PaperIdentifier(IdentifierKind.IEEE, ieee)

    pmid = _try_parse_pmid(candidate)
    if pmid is not None:
        return PaperIdentifier(IdentifierKind.PMID, pmid)

    doi = _try_parse_doi(candidate)
    if doi is not None:
        return PaperIdentifier(IdentifierKind.DOI, doi)

    raise ValueError(f"could not classify identifier: {raw!r}")


def _try_parse_arxiv(candidate: str) -> str | None:
    url_match = _ARXIV_URL_RE.match(candidate)
    if url_match:
        return _strip_version(url_match.group(1))
    bare = _ARXIV_PREFIX_RE.sub("", candidate)
    if _ARXIV_NEW_RE.match(bare) or _ARXIV_OLD_RE.match(bare):
        return _strip_version(bare)
    return None


def _try_parse_doi(candidate: str) -> str | None:
    url_match = _DOI_URL_RE.match(candidate)
    if url_match:
        doi = url_match.group(1)
        return doi if _DOI_PATTERN_RE.match(doi) else None
    bare = _DOI_PREFIX_RE.sub("", candidate)
    if _DOI_PATTERN_RE.match(bare):
        return bare
    return None


def _try_parse_pmid(candidate: str) -> str | None:
    url_match = _PMID_URL_RE.match(candidate)
    if url_match:
        return url_match.group(1)
    bare = _PMID_PREFIX_RE.sub("", candidate)
    if _PMID_PATTERN_RE.match(bare):
        return bare
    return None


def _try_parse_ieee(candidate: str) -> str | None:
    url_match = _IEEE_URL_RE.match(candidate)
    if url_match:
        return url_match.group(1)
    bare = _IEEE_PREFIX_RE.sub("", candidate)
    if bare.isdigit() and bare != candidate:
        return bare
    return None


def _strip_version(arxiv_id: str) -> str:
    return re.sub(r"v\d+$", "", arxiv_id)
