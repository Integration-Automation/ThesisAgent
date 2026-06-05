"""Parse PubMed efetch XML into Paper records.

The PubMed efetch XML schema is `<PubmedArticleSet>` containing one or more
`<PubmedArticle>` entries. We pull out:
- MedlineCitation/PMID
- Article/ArticleTitle
- Article/Abstract/AbstractText (joined when split across <AbstractText> tags)
- AuthorList/Author (ForeName + LastName or CollectiveName)
- Journal/JournalIssue/PubDate/Year (or MedlineDate)
- Journal/Title
- ELocationID[ValidYN="Y"][EIdType="doi"]
"""

from __future__ import annotations

import re
from typing import Any

from defusedxml import ElementTree as ET  # noqa: N817  # ET is the canonical alias

from thesisagents.core.exceptions import ParseError
from thesisagents.core.models import Paper

_SOURCE = "pubmed"
_PUBMED_URL = "https://pubmed.ncbi.nlm.nih.gov/{pmid}/"


def parse_efetch(xml_text: str) -> list[Paper]:
    """Parse the XML payload returned by efetch into a list of papers."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as err:
        raise ParseError(_SOURCE, f"invalid PubMed XML: {err}") from err
    articles = root.findall("PubmedArticle")
    return [_parse_article(article) for article in articles]


def _parse_article(article: Any) -> Paper:
    pmid = _text(article.find("./MedlineCitation/PMID"))
    art = article.find("./MedlineCitation/Article")
    title = _normalise_whitespace(_inner_text(art.find("ArticleTitle"))) if art is not None else ""
    abstract = _collect_abstract(art) if art is not None else ""
    authors = _collect_authors(art) if art is not None else ()
    venue = _text(art.find("./Journal/Title")) if art is not None else ""
    year = _extract_year(art) if art is not None else None
    doi = _extract_doi(art) if art is not None else None
    return Paper(
        source=_SOURCE,
        source_id=pmid,
        title=title,
        authors=authors,
        year=year,
        venue=venue or None,
        abstract=abstract,
        url=_PUBMED_URL.format(pmid=pmid) if pmid else "",
        doi=doi,
    )


def _collect_abstract(article: Any) -> str:
    fragments: list[str] = []
    for piece in article.findall("./Abstract/AbstractText"):
        label = piece.attrib.get("Label")
        body = _inner_text(piece)
        fragments.append(f"{label}: {body}" if label else body)
    return _normalise_whitespace(" ".join(fragments))


def _collect_authors(article: Any) -> tuple[str, ...]:
    names: list[str] = []
    for author in article.findall("./AuthorList/Author"):
        collective = _text(author.find("CollectiveName"))
        if collective:
            names.append(collective)
            continue
        last = _text(author.find("LastName"))
        first = _text(author.find("ForeName"))
        if last and first:
            names.append(f"{first} {last}")
        elif last:
            names.append(last)
    return tuple(names)


def _extract_year(article: Any) -> int | None:
    pub_date = article.find("./Journal/JournalIssue/PubDate")
    if pub_date is None:
        return None
    year_text = _text(pub_date.find("Year"))
    if year_text and year_text.isdigit():
        return int(year_text)
    medline_date = _text(pub_date.find("MedlineDate"))
    match = re.search(r"\b(19|20)\d{2}\b", medline_date)
    if match:
        return int(match.group(0))
    return None


def _extract_doi(article: Any) -> str | None:
    for eid in article.findall("./ELocationID"):
        if eid.attrib.get("EIdType", "").lower() == "doi":
            value = _text(eid)
            if value:
                return value
    article_ids = article.findall("../PubmedData/ArticleIdList/ArticleId")
    for aid in article_ids:
        if aid.attrib.get("IdType", "").lower() == "doi":
            value = _text(aid)
            if value:
                return value
    return None


def _text(element: Any) -> str:
    if element is None or element.text is None:
        return ""
    return element.text.strip()


def _inner_text(element: Any) -> str:
    """Like _text but also concatenates child element text (PubMed wraps
    italics/sub/sup tags inside ArticleTitle / AbstractText)."""
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def _normalise_whitespace(value: str) -> str:
    return " ".join(value.split())
