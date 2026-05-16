"""Parse a Google Scholar SERP HTML page into Paper records.

Scholar's HTML is brittle — class names rotate occasionally. We treat any
``div.gs_r.gs_or.gs_scl`` as one result block and pull title / link / authors
/ venue / year / snippet best-effort. Records that can't be parsed are
skipped rather than failing the whole search.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from autopapertoppt.core.exceptions import ParseError, SourceUnavailableError
from autopapertoppt.core.models import Paper

_SOURCE = "scholar"
_CAPTCHA_HINTS = ("our systems have detected unusual traffic", "/sorry/index")


def parse_serp(html_text: str) -> list[Paper]:
    """Parse a Scholar SERP HTML page into a list of Paper records."""
    lowered = html_text.lower()
    if any(hint in lowered for hint in _CAPTCHA_HINTS):
        raise SourceUnavailableError(
            _SOURCE,
            "Google Scholar served a captcha / sorry page. Back off and retry later.",
        )
    soup = BeautifulSoup(html_text, "lxml")
    blocks = soup.select("div.gs_r.gs_or.gs_scl")
    if not blocks:
        # An empty SERP is legitimate; truly malformed HTML lacks even the wrapper.
        wrapper = soup.find("div", id="gs_res_ccl")
        if wrapper is None:
            raise ParseError(_SOURCE, "Scholar HTML does not match the expected layout")
        return []
    papers: list[Paper] = []
    for block in blocks:
        paper = _parse_one(block)
        if paper is not None:
            papers.append(paper)
    return papers


def _parse_one(block) -> Paper | None:
    title_node = block.select_one("h3.gs_rt a") or block.select_one("h3.gs_rt")
    if title_node is None:
        return None
    title = " ".join(title_node.get_text(" ", strip=True).split())
    url = (title_node.get("href") or "").strip() if title_node.name == "a" else ""
    meta_node = block.select_one(".gs_a")
    authors, year, venue = _parse_meta(meta_node.get_text(" ", strip=True) if meta_node else "")
    snippet_node = block.select_one(".gs_rs")
    abstract = (
        " ".join(snippet_node.get_text(" ", strip=True).split())
        if snippet_node
        else ""
    )
    citation_count = _parse_citation_count(block)
    source_id = _data_cid(block) or url or title
    return Paper(
        source=_SOURCE,
        source_id=source_id,
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        abstract=abstract,
        url=url,
        citation_count=citation_count,
    )


_META_SPLIT_RE = re.compile(r"\s+-\s+")
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _parse_meta(meta_text: str) -> tuple[tuple[str, ...], int | None, str | None]:
    """Scholar's `gs_a` div looks like:

        A Vaswani, N Shazeer, N Parmar - Advances in neural information ..., 2017 - papers.nips.cc

    Authors are comma-separated; year is the first 19xx/20xx in the middle
    segment; venue is what's left after stripping authors / year / publisher.
    """
    if not meta_text:
        return (), None, None
    parts = _META_SPLIT_RE.split(meta_text)
    author_part = parts[0] if parts else ""
    middle = parts[1] if len(parts) > 1 else ""
    authors = tuple(name.strip() for name in author_part.split(",") if name.strip())
    year_match = _YEAR_RE.search(middle)
    year = int(year_match.group(0)) if year_match else None
    venue = middle
    if year_match:
        venue = (venue[: year_match.start()] + venue[year_match.end():]).strip(" ,")
    venue = venue.rstrip(",").strip() or None
    return authors, year, venue


_CITATION_RE = re.compile(r"Cited by\s+(\d+)", re.IGNORECASE)


def _parse_citation_count(block) -> int | None:
    for link in block.select("a"):
        text = link.get_text(" ", strip=True)
        match = _CITATION_RE.match(text)
        if match:
            return int(match.group(1))
    return None


def _data_cid(block) -> str:
    return (block.get("data-cid") or "").strip()
