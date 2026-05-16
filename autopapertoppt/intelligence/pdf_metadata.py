"""Heuristic metadata extraction from a paper's page-1 text.

Pure-Python, no LLM, no network. Operates on whatever ``pypdf`` already
gave us. Goals:

* fill in the four fields a user is most likely to leave blank on
  ``--pdf``: ``title``, ``authors``, ``year``, ``abstract``;
* surface obvious identifiers (``arxiv_id``, ``doi``) so the deck links
  back to the canonical source;
* never raise — when a regex misses, the field comes back as ``None``
  and the caller falls back to whatever the user did pass.

Heuristics, not parsers. Modern academic PDFs follow predictable layout
conventions (title at top, authors next, "Abstract" header before the
body) so a tiny rule set covers the long tail; weirder cases stay
overridable through the existing CLI flags.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_ARXIV_RE = re.compile(
    r"arXiv\s*:\s*(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE
)
# Strip the full "arXiv:NNNN.NNNNNvN [category] DD MMM YYYY" preamble that
# arXiv stamps into the top of every preprint — when present, it would
# otherwise become part of the extracted title.
_ARXIV_PREAMBLE_RE = re.compile(
    r"^\s*arXiv\s*:\s*\d{4}\.\d{4,5}(?:v\d+)?"
    r"(?:\s*\[[\w\-./]+\])?"
    r"(?:\s+\d{1,2}\s+\w{3,9}\s+\d{4})?"
    r"\s*",
    re.IGNORECASE,
)
_ARXIV_URL_RE = re.compile(
    r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE
)
_DOI_RE = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(19[89]\d|20\d{2})\b")
# The em-dash / hyphen / colon / period after "Abstract" is the IEEE / ACM
# inline-abstract anchor — when the PDF extractor flattens the layout to
# one long line, this is the only reliable signal of where the abstract
# starts. The bare "Abstract" form (no separator) only matches when it
# sits on its own line so figure captions like "Abstract Apps" don't
# fire.
_ABSTRACT_INLINE_RE = re.compile(
    r"(?:^|\s)(?:Abstract|ABSTRACT|摘要|要旨|Resumen|Résumé|Zusammenfassung)"
    r"\s*[—\-:.]\s*",
)
_ABSTRACT_BLOCK_RE = re.compile(
    r"(?:^|\n)\s*(?:Abstract|ABSTRACT|摘要|要旨|Resumen|Résumé|Zusammenfassung)\s*\n",
)
_ABSTRACT_END_RE = re.compile(
    r"(?:"
    r"(?:^|\n|\s)1\s*[.)]\s*Introduction"
    r"|(?:^|\n|\s)I\.?\s*Introduction"
    r"|(?:^|\n)\s*Introduction\s*\n"
    r"|(?:^|\n|\s)Keywords?\s*[:.—\-]"
    r"|(?:^|\n|\s)Index\s+Terms"
    r"|(?:^|\n|\s)CCS\s+Concepts"
    r"|(?:^|\n|\s)Categories\s+and\s+Subject\s+Descriptors"
    r")",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"\S+@\S+\.\S+")
_AUTHOR_SEPARATOR_RE = re.compile(r",\s*|\s+and\s+|;\s*", re.IGNORECASE)

# Lines that page-1 boilerplate uses — never the title, never an author.
_BOILERPLATE_PREFIXES = (
    "arxiv:", "doi:", "https://", "http://", "preprint",
    "submitted", "accepted", "published", "to appear",
    "permission", "copyright", "all rights reserved",
    "ieee", "acm", "springer", "elsevier",
    "the author", "this work",
)

#: Authors lines almost never contain these — used as anti-signals.
_NON_AUTHOR_TOKENS = (
    "department", "university", "institute", "laboratory", "school of",
    "abstract", "introduction", "keywords", "@",
    "research group", "corporation", "inc.", "ltd.",
)

_MAX_TITLE_LINES = 3
_MIN_TITLE_CHARS = 8
_MAX_TITLE_CHARS = 240
_MAX_AUTHORS = 12
_MAX_ABSTRACT_CHARS = 2400


@dataclass(frozen=True, slots=True)
class ExtractedMetadata:
    """Per-field heuristic extraction result. Any field may be ``None``."""

    title: str | None = None
    authors: tuple[str, ...] = ()
    year: int | None = None
    arxiv_id: str | None = None
    doi: str | None = None
    abstract: str | None = None


def extract_metadata(text: str) -> ExtractedMetadata:
    """Extract heuristic metadata from extracted PDF text.

    Handles both the well-structured case (pypdf preserves newlines) and
    the flattened case (no newlines, the whole front matter is one long
    line). We look at the first ~6000 chars (page 1 + a bit) for the
    title / authors / identifiers, and use the explicit ``Abstract``
    anchor to bound the abstract.
    """
    if not text:
        return ExtractedMetadata()
    head = text[:6000]
    arxiv_id = _extract_arxiv_id(text)
    doi = _extract_doi(text)
    abstract_start, abstract = _extract_abstract(text)
    pre_abstract = head[:abstract_start] if abstract_start is not None else head
    title, authors = _extract_title_and_authors(pre_abstract)
    year = _extract_year(head)
    return ExtractedMetadata(
        title=title,
        authors=authors,
        year=year,
        arxiv_id=arxiv_id,
        doi=doi,
        abstract=abstract,
    )


def _extract_arxiv_id(text: str) -> str | None:
    match = _ARXIV_RE.search(text) or _ARXIV_URL_RE.search(text)
    return match.group(1) if match else None


def _extract_doi(text: str) -> str | None:
    match = _DOI_RE.search(text)
    if not match:
        return None
    # Crossref DOIs sometimes have a trailing dot or paren picked up by
    # the regex — strip the obvious cases.
    return match.group(1).rstrip(".,;)")


def _extract_year(head: str) -> int | None:
    """Pick the first plausible 4-digit publication year in page 1."""
    for raw in _YEAR_RE.findall(head):
        year = int(raw)
        # Reject years that show up because of a phone number, ZIP code,
        # or version string by ensuring it's in the realistic window.
        if 1980 <= year <= 2099:
            return year
    return None


def _extract_abstract(text: str) -> tuple[int | None, str | None]:
    """Find the abstract anchor and the abstract text.

    Returns ``(anchor_start_index, abstract_text)``. The anchor index is
    where the "Abstract" header sits — used by the title/author extractor
    to know where the front matter ends. Both values are ``None`` if no
    anchor is found.

    Strategy: prefer an inline ``Abstract—`` / ``Abstract:`` / ``Abstract.``
    anchor (IEEE / ACM typesetting that survives pypdf flattening); fall
    back to a block-style ``Abstract\\n`` header for layouts that preserve
    newlines.
    """
    inline = _ABSTRACT_INLINE_RE.search(text)
    block = _ABSTRACT_BLOCK_RE.search(text)
    chosen = _pick_earlier_match(inline, block)
    if chosen is None:
        return None, None
    anchor_start = chosen.start()
    body_start = chosen.end()
    window = text[body_start : body_start + _MAX_ABSTRACT_CHARS * 2]
    end_match = _ABSTRACT_END_RE.search(window)
    body = window[: end_match.start()] if end_match else window[:_MAX_ABSTRACT_CHARS]
    abstract = " ".join(body.split())[:_MAX_ABSTRACT_CHARS]
    return anchor_start, (abstract or None)


def _pick_earlier_match(a: re.Match | None, b: re.Match | None) -> re.Match | None:
    if a and b:
        return a if a.start() <= b.start() else b
    return a or b


def _extract_title_and_authors(head: str) -> tuple[str | None, tuple[str, ...]]:
    """Pick the title and author list from the pre-abstract front matter.

    Works on two layouts:

    * **Newline-preserved** — pypdf kept paragraph breaks. We treat each
      newline-separated chunk as a candidate line and walk top-down,
      taking the first non-boilerplate run as the title and the next as
      authors.
    * **Flattened** — pypdf returned one long line. We use the author
      footnote / affiliation handoff as a split point: the title runs
      from the start to the first ``FirstName LastName ∗``-style author
      marker; authors run from there to the first affiliation token
      (``Department``, ``University``, ``@``, etc.).

    Conservative — when in doubt, returns ``None`` / ``()`` and lets the
    CLI fall back to its own defaults.
    """
    head = head.strip()
    if not head:
        return None, ()
    lines = [line.strip() for line in head.splitlines() if line.strip()]
    # If pypdf preserved at least two non-empty lines we have a structured
    # layout; otherwise fall back to the flattened-text path.
    if len(lines) >= 2:
        title, authors = _extract_from_lines(lines)
        if title is not None:
            return title, authors
    return _extract_from_flat_text(head)


def _extract_from_lines(lines: list[str]) -> tuple[str | None, tuple[str, ...]]:
    lines = [line for line in lines if not _is_boilerplate_line(line)]
    if not lines:
        return None, ()
    title_lines, rest = _collect_title_lines(lines)
    if not title_lines:
        return None, ()
    title = " ".join(title_lines).strip()
    if not (_MIN_TITLE_CHARS <= len(title) <= _MAX_TITLE_CHARS):
        return None, ()
    authors = _collect_authors(rest)
    return title, authors


_FLAT_AUTHOR_MARKER_RE = re.compile(
    # Token shaped like "FirstName LastName <marker>" at the
    # title→authors handoff on flattened front matter. The first token
    # MUST be Capitalised + lowercase only (``[A-Z][a-z'-]+``); the
    # second may include hyphens or further capitals (``Mc-Carthy``).
    # The boundary marker is one of three signals:
    #
    # 1. Footnote symbol (``*``, ``∗`` U+2217, ``⋆``, ``†``, ``‡``, ``§``);
    # 2. Numbered footnote (``\d``) — common in CCS / NeurIPS layouts that
    #    use ``Wen Cheng¹``;
    # 3. Inline affiliation token (`` Royal Holloway, University``) — the
    #    pure-text layout where neither footnote nor comma sits between
    #    the last author name and the first affiliation word.
    #
    # The leading ``\s`` makes ``marker.start()`` point to the space
    # *before* the first name, which is exactly where the title ends.
    r"\s([A-Z][a-z'\-]+\s+[A-Z][a-zA-Z'\-]+)"
    r"(?:\s*[\*∗⋆†‡§\d,]"
    r"|\s+(?:[A-Z][a-z]+[\s,]+){1,3}"
    r"(?:University|Department|Institute|Laboratory|College))",
)
_FLAT_AUTHOR_END_RE = re.compile(
    # First token where the authors list clearly ends — affiliation /
    # email block markers. An optional capitalised modifier
    # ([A-Z][a-z]+\s+) sits before the affiliation keyword so
    # "Northeastern University" terminates at "Northeastern" rather
    # than swallowing it into the last author's name.
    r"(?:[A-Z][a-z]+\s+)?"
    r"(?:Department|University|Institute|Laboratory|College|"
    r"School\s+of|@|\{)",
)


def _extract_from_flat_text(head: str) -> tuple[str | None, tuple[str, ...]]:
    # Strip the arXiv preamble first — when a preprint includes the
    # arXiv stamp at the top, that prefix would otherwise become part
    # of the extracted title.
    head = _ARXIV_PREAMBLE_RE.sub("", head, count=1)
    marker = _FLAT_AUTHOR_MARKER_RE.search(head)
    if not marker:
        return None, ()
    title = head[: marker.start()].strip(" ,.;:")
    title = " ".join(title.split())
    if not (_MIN_TITLE_CHARS <= len(title) <= _MAX_TITLE_CHARS):
        return None, ()
    end = _FLAT_AUTHOR_END_RE.search(head, marker.start())
    authors_chunk = head[marker.start() : end.start() if end else marker.start() + 400]
    authors_chunk = re.sub(r"\s+", " ", authors_chunk).strip()
    authors = _split_flat_author_chunk(authors_chunk)
    return title, authors


def _split_flat_author_chunk(chunk: str) -> tuple[str, ...]:
    parts = _AUTHOR_SEPARATOR_RE.split(chunk)
    names: list[str] = []
    for raw in parts:
        # Strip a leading "and " left behind when "Author, and OtherAuthor"
        # gets split on the comma first.
        candidate = re.sub(r"^\s*and\s+", "", raw or "", flags=re.IGNORECASE)
        cleaned = _clean_author(candidate)
        if cleaned and cleaned not in names:
            names.append(cleaned)
        if len(names) >= _MAX_AUTHORS:
            break
    return tuple(names)


def _is_boilerplate_line(line: str) -> bool:
    lower = line.lower()
    if any(lower.startswith(prefix) for prefix in _BOILERPLATE_PREFIXES):
        return True
    # Reject page-number-only lines.
    return bool(re.fullmatch(r"\d{1,3}", line))


def _collect_title_lines(lines: list[str]) -> tuple[list[str], list[str]]:
    """Return (title_lines, remaining_lines). Title runs from the top to the
    first line that smells like an author block (commas/and-separator with no
    sentence punctuation, no department-style affiliation tokens)."""
    title_buf: list[str] = []
    for idx, line in enumerate(lines):
        if _looks_like_authors_line(line):
            return title_buf, lines[idx:]
        title_buf.append(line)
        if len(title_buf) >= _MAX_TITLE_LINES:
            return title_buf, lines[idx + 1:]
        # Title rarely ends in a sentence period in academic typesetting,
        # so we don't try to detect "end of title" — we use the author-line
        # heuristic and the line-count cap.
    return title_buf, []


def _looks_like_authors_line(line: str) -> bool:
    if any(tok in line.lower() for tok in _NON_AUTHOR_TOKENS):
        return False
    if "." in line and "," not in line and " and " not in line.lower():
        return False
    # An author line usually has at least one separator AND at least two
    # capitalised words.
    has_separator = bool(_AUTHOR_SEPARATOR_RE.search(line))
    capital_words = sum(1 for w in line.split() if w[:1].isupper())
    return has_separator and capital_words >= 2


def _collect_authors(lines: list[str]) -> tuple[str, ...]:
    """Pull author names from the lines immediately after the title."""
    names: list[str] = []
    for line in lines:
        if any(tok in line.lower() for tok in _NON_AUTHOR_TOKENS):
            break
        if _EMAIL_RE.search(line):
            break
        if not _looks_like_authors_line(line):
            # Author lines often span multiple typeset lines — give it
            # one more chance before bailing.
            if names:
                break
            continue
        for raw in _AUTHOR_SEPARATOR_RE.split(line):
            cleaned = _clean_author(raw)
            if cleaned and cleaned not in names:
                names.append(cleaned)
            if len(names) >= _MAX_AUTHORS:
                return tuple(names)
    return tuple(names)


_AUTHOR_NOISE_RE = re.compile(r"[†‡§*∗⋆0-9]+")


def _clean_author(raw: str) -> str | None:
    """Strip footnote markers / superscripts / trailing punctuation from one name.

    On numbered-footnote layouts (``Wang1 1State Key Laboratory...``) the
    second digit is the affiliation footnote — everything after the first
    digit run belongs to the affiliation, not the author. We split on the
    first ``\\d+`` run and keep only the head.
    """
    candidate = re.split(r"\d+", raw, maxsplit=1)[0]
    cleaned = _AUTHOR_NOISE_RE.sub("", candidate).strip(" ,.;").strip()
    if len(cleaned.split()) < 2:
        return None
    if len(cleaned) > 80:
        return None
    if any(tok in cleaned.lower() for tok in _NON_AUTHOR_TOKENS):
        return None
    return cleaned
