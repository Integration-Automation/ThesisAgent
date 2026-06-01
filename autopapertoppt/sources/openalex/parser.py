"""Parse OpenAlex /works JSON records into ``Paper`` instances.

OpenAlex's open-access metadata is the reason this source matters: a paper
that is paywalled on the publisher's site (IEEE, ACM, Elsevier) often has a
freely hosted mirror that OpenAlex tracks under ``best_oa_location.pdf_url``
or ``primary_location.pdf_url``. We prefer those direct PDFs over the
landing-page ``open_access.oa_url`` so the downstream PDF downloader can
verify the bytes with the ``%PDF`` magic check.
"""

from __future__ import annotations

import re
from typing import Any

from autopapertoppt.core.models import Paper

_SOURCE = "openalex"
_DOI_PREFIX = "https://doi.org/"
_OPENALEX_PREFIX = "https://openalex.org/"


def parse_work(record: dict[str, Any]) -> Paper:
    """Map one entry from ``/works`` to a ``Paper``."""
    title = (record.get("title") or record.get("display_name") or "").strip()
    authors = tuple(_authors(record.get("authorships") or []))
    year = _to_int(record.get("publication_year"))
    venue = _venue(record)
    abstract = _reconstruct_abstract(record.get("abstract_inverted_index") or {})
    doi = _strip_prefix(record.get("doi"), _DOI_PREFIX)
    arxiv_id = _extract_arxiv_id(record)
    citation_count = _to_int(record.get("cited_by_count"))
    source_id = _strip_prefix(record.get("id") or "", _OPENALEX_PREFIX) or (
        doi or arxiv_id or ""
    )
    url = record.get("id") or (f"{_DOI_PREFIX}{doi}" if doi else "")
    pdf_url = _pick_pdf_url(record)
    return Paper(
        source=_SOURCE,
        source_id=source_id,
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        abstract=abstract,
        url=url,
        doi=doi,
        arxiv_id=arxiv_id,
        citation_count=citation_count,
        pdf_url=pdf_url,
        raw=record,
    )


def _authors(authorships: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for entry in authorships:
        author = entry.get("author") or {}
        name = (author.get("display_name") or "").strip()
        if name:
            names.append(name)
    return names


def _venue(record: dict[str, Any]) -> str | None:
    """Pull a venue name from ``primary_location.source.display_name``.

    ``host_venue`` used to be the canonical field but OpenAlex removed it
    from the schema in late 2024; ``primary_location.source`` is now the
    blessed path. Falls back to ``None`` if neither is populated.
    """
    primary = record.get("primary_location") or {}
    src = (primary.get("source") or {})
    name = (src.get("display_name") or "").strip()
    return name or None


def _pick_pdf_url(record: dict[str, Any]) -> str | None:
    """Pick the most directly-downloadable PDF URL.

    Order of preference:
    1. ``best_oa_location.pdf_url`` — OpenAlex's curated best OA mirror
    2. ``primary_location.pdf_url`` — primary host (may be publisher OA)
    3. ``open_access.oa_url`` — landing page, only as a last resort
    """
    for location_key in ("best_oa_location", "primary_location"):
        loc = record.get(location_key) or {}
        candidate = (loc.get("pdf_url") or "").strip()
        if candidate:
            return candidate
    oa = record.get("open_access") or {}
    fallback = (oa.get("oa_url") or "").strip()
    return fallback or None


def _reconstruct_abstract(inverted_index: dict[str, list[int]]) -> str:
    """OpenAlex stores abstracts as ``{word: [positions...]}``; invert it.

    Why this exists: copyright-free papers can still ship via OpenAlex with
    the abstract scrambled into a positional inverted index so the original
    contiguous text isn't trivially redistributable. Reconstructing the
    sequence is straightforward and produces a normal sentence flow.
    """
    if not inverted_index:
        return ""
    by_position: dict[int, str] = {}
    for word, positions in inverted_index.items():
        if not isinstance(positions, list):
            continue
        for pos in positions:
            if isinstance(pos, int) and pos >= 0:
                by_position[pos] = word
    if not by_position:
        return ""
    ordered = (by_position[i] for i in sorted(by_position))
    return " ".join(ordered)


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _strip_prefix(value: str | None, prefix: str) -> str | None:
    if not value:
        return None
    return value[len(prefix):] if value.startswith(prefix) else value


_ARXIV_RE = re.compile(r"arxiv\.org/abs/([\w.\-/]+)", re.IGNORECASE)


def _extract_arxiv_id(record: dict[str, Any]) -> str | None:
    """Pull an arXiv ID out of `ids.arxiv` (full URL) or any matching `locations[*]`."""
    ids = record.get("ids") or {}
    arxiv_url = ids.get("arxiv") or ""
    match = _ARXIV_RE.search(arxiv_url) if arxiv_url else None
    if match:
        return match.group(1)
    locations = record.get("locations") or []
    for loc in locations:
        landing = (loc or {}).get("landing_page_url") or ""
        match = _ARXIV_RE.search(landing)
        if match:
            return match.group(1)
    return None
