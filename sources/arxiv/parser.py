"""Parse the arXiv Atom feed into normalised Paper records.

Atom XML namespaces:
- atom:   http://www.w3.org/2005/Atom
- arxiv:  http://arxiv.org/schemas/atom
"""

from __future__ import annotations

import re
from typing import Any

from defusedxml import ElementTree as ET  # noqa: N817  # ET is the canonical alias for ElementTree

from autopapertoppt.core.exceptions import ParseError
from autopapertoppt.core.models import Paper

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}
_SOURCE = "arxiv"
_ARXIV_ID_RE = re.compile(r"arxiv\.org/abs/([^/?#]+)")
_VERSION_SUFFIX_RE = re.compile(r"v\d+$")


def parse_atom_feed(xml_text: str) -> list[Paper]:
    """Parse the Atom XML response from arXiv's API into Paper records."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as err:
        raise ParseError(_SOURCE, f"invalid Atom XML: {err}") from err
    entries = root.findall("atom:entry", _NS)
    return [_parse_entry(entry) for entry in entries]


def _parse_entry(entry: Any) -> Paper:
    arxiv_id_raw = _text(entry.find("atom:id", _NS))
    arxiv_id = _extract_arxiv_id(arxiv_id_raw)
    title = _normalise_whitespace(_text(entry.find("atom:title", _NS)))
    summary = _normalise_whitespace(_text(entry.find("atom:summary", _NS)))
    published = _text(entry.find("atom:published", _NS))
    year = _extract_year(published)
    authors = _extract_authors(entry)
    doi = _text(entry.find("arxiv:doi", _NS)) or None
    journal_ref = _text(entry.find("arxiv:journal_ref", _NS)) or None
    pdf_url = _extract_pdf_link(entry)
    abs_url = _extract_abs_link(entry) or arxiv_id_raw
    return Paper(
        source=_SOURCE,
        source_id=arxiv_id or arxiv_id_raw,
        title=title,
        authors=authors,
        year=year,
        venue=journal_ref,
        abstract=summary,
        url=abs_url,
        doi=doi,
        arxiv_id=_strip_version(arxiv_id) if arxiv_id else None,
        pdf_url=pdf_url,
    )


def _text(element: Any) -> str:
    if element is None or element.text is None:
        return ""
    return element.text


def _normalise_whitespace(value: str) -> str:
    return " ".join(value.split())


def _extract_arxiv_id(raw: str) -> str:
    match = _ARXIV_ID_RE.search(raw)
    if match:
        return match.group(1)
    return raw.strip()


def _strip_version(arxiv_id: str) -> str:
    return _VERSION_SUFFIX_RE.sub("", arxiv_id)


def _extract_year(published: str) -> int | None:
    if len(published) >= 4 and published[:4].isdigit():
        return int(published[:4])
    return None


def _extract_authors(entry: Any) -> tuple[str, ...]:
    names: list[str] = []
    for author in entry.findall("atom:author", _NS):
        name_el = author.find("atom:name", _NS)
        name = _text(name_el).strip()
        if name:
            names.append(name)
    return tuple(names)


def _extract_pdf_link(entry: Any) -> str | None:
    for link in entry.findall("atom:link", _NS):
        if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
            href = link.attrib.get("href")
            if href:
                return href
    return None


def _extract_abs_link(entry: Any) -> str | None:
    for link in entry.findall("atom:link", _NS):
        rel = link.attrib.get("rel")
        if rel == "alternate":
            href = link.attrib.get("href")
            if href:
                return href
    return None
