"""Parse OpenAIRE Graph `researchProducts` records into ``Paper`` instances.

OpenAIRE's value over OpenAlex is its strong coverage of European OA
repositories and pre-print servers. We pick the first ``instances[].urls[]``
entry as the canonical landing URL, and look for a PDF URL among the
instances with ``accessRight`` of ``OPEN`` or with a ``.pdf`` suffix.
"""

from __future__ import annotations

import re
from typing import Any

from autopapertoppt.core.models import Paper

_SOURCE = "openaire"
_ARXIV_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/([\w.\-/]+)", re.IGNORECASE)


def parse_product(record: dict[str, Any]) -> Paper:
    """Map one ``results[]`` entry to a ``Paper``."""
    title = (record.get("mainTitle") or record.get("title") or "").strip()
    authors = tuple(_authors(record.get("authors") or []))
    year = _year(record.get("publicationDate") or "")
    venue = _venue(record)
    abstract = _abstract(record.get("descriptions") or [])
    doi = _doi(record.get("pids") or [])
    arxiv_id = _arxiv_id(record)
    url = _landing_url(record.get("instances") or [])
    if not url and doi:
        url = f"https://doi.org/{doi}"
    pdf_url = _pdf_url(record.get("instances") or [])
    source_id = (record.get("id") or doi or url or "").strip()
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
        pdf_url=pdf_url,
        raw=record,
    )


def _authors(entries: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = (entry.get("fullName") or entry.get("name") or "").strip()
        if name:
            # OpenAIRE stores "Last, First"; normalise to "First Last"
            # only when there's exactly one comma so we don't mangle
            # cases like "Last, First, Middle".
            if name.count(",") == 1:
                family, given = (part.strip() for part in name.split(","))
                if family and given:
                    name = f"{given} {family}"
            names.append(name)
    return names


def _year(publication_date: str) -> int | None:
    if not publication_date:
        return None
    head = publication_date.strip()[:4]
    try:
        return int(head)
    except ValueError:
        return None


def _venue(record: dict[str, Any]) -> str | None:
    container = (record.get("container") or {})
    name = (container.get("name") or "").strip()
    if name:
        return name
    journal = (record.get("journal") or {})
    name = (journal.get("name") or "").strip()
    return name or None


def _abstract(descriptions: list[dict[str, Any]]) -> str:
    for entry in descriptions:
        if isinstance(entry, dict):
            value = (entry.get("value") or "").strip()
            if value:
                return value
        elif isinstance(entry, str) and entry.strip():
            return entry.strip()
    return ""


def _doi(pids: list[dict[str, Any]]) -> str | None:
    for entry in pids:
        if not isinstance(entry, dict):
            continue
        scheme = (entry.get("scheme") or "").lower()
        value = (entry.get("value") or "").strip()
        if scheme == "doi" and value:
            return value
    return None


def _arxiv_id(record: dict[str, Any]) -> str | None:
    for entry in record.get("pids") or []:
        if isinstance(entry, dict):
            scheme = (entry.get("scheme") or "").lower()
            value = (entry.get("value") or "").strip()
            if scheme == "arxiv" and value:
                return value
    for instance in record.get("instances") or []:
        for url in (instance or {}).get("urls") or []:
            match = _ARXIV_RE.search(url or "")
            if match:
                return match.group(1)
    return None


def _landing_url(instances: list[dict[str, Any]]) -> str:
    for instance in instances:
        for url in (instance or {}).get("urls") or []:
            if url:
                return url
    return ""


def _pdf_url(instances: list[dict[str, Any]]) -> str | None:
    open_pdf: str | None = None
    any_pdf: str | None = None
    for instance in instances:
        access = (instance.get("accessRight") or "").upper()
        for url in instance.get("urls") or []:
            if not url:
                continue
            if url.lower().endswith(".pdf"):
                if access == "OPEN":
                    return url
                any_pdf = any_pdf or url
            elif access == "OPEN":
                open_pdf = open_pdf or url
    return any_pdf or open_pdf
