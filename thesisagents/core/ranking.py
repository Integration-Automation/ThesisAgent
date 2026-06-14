"""Relevance + recency + citation ranking.

Each source returns a roughly relevance-sorted list, but de-duplication merges
those lists across sources and discards each source's local ordering. Without an
explicit relevance signal the merged list would sort purely by recency +
citation — which buries a highly-relevant older paper under a recent, more-cited,
*off-topic* one. (Concrete failure this prevents: a search for "transformer
attention" that surfaces a 100k-citation ResNet paper above an on-topic survey,
simply because ResNet is cited more.)

So each paper is scored on three axes and stable-sorted by the sum:

* **relevance** (dominant) — overlap between the query keywords and the paper's
  title (weighted heavily) + abstract (weighted lightly). Research starts from
  "is this on my topic?", so an on-topic paper should beat an off-topic one even
  when the off-topic one is older-and-more-cited. The relevance axis goes beyond
  exact word matching in four ways so it does not silently miss on-topic papers:

  1. **Light stemming** — a query for ``transformer`` matches a ``Transformers``
     title (a plural/inflection difference is the same concept). Stemming is
     deliberately conservative: only a small whitelist of suffixes is stripped,
     and only when the remaining stem stays ``>= _MIN_STEM_LEN`` so short words
     (``bias``, ``ring``, ``gas``) are never mangled into a false match.
  2. **Phrase adjacency bonus** — for a multi-word query, a title where the
     query words appear *adjacent* (``Retrieval-Augmented Generation``) scores
     above one where they are merely *scattered* across the title.
  3. **Acronym synonyms** — a query for ``llm`` matches a title that only ever
     writes ``large language model`` (and vice-versa), via a small curated map.
  4. **CJK support** — Chinese/Japanese/Korean runs are tokenised into character
     bigrams, so a Chinese-keyword search gets a real relevance signal instead
     of falling back to recency+citation only (the prior ``[a-z0-9]+`` tokenizer
     dropped every CJK character).
* **recency** — exponential decay over paper age (~5-year scale).
* **citation** — ``log10`` of the citation count (diminishing returns), then
  damped by ``_CITATION_WEIGHT`` so a huge citation count is a strong tie-break
  but cannot by itself outrank an on-topic title.

``keywords`` is optional: callers that rank a single fetched paper (no query, e.g.
``run_single_paper``) pass ``None`` and keep the pre-relevance recency+citation
behaviour.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable

from thesisagents.core.models import Paper

_CURRENT_YEAR_FALLBACK = 2026

# Relevance weights. Title overlap dominates; abstract overlap is a softer
# secondary signal. Tuned together with _CITATION_WEIGHT so that a full
# title match (= _TITLE_WEIGHT) outranks even a ~100k-citation off-topic paper
# (citation term ≈ _CITATION_WEIGHT * log10(1e5) = 0.4 * 5 = 2.0 < 3.0).
_TITLE_WEIGHT = 3.0
_ABSTRACT_WEIGHT = 0.6
# Bonus when the query's adjacent word pairs (bigrams) also appear adjacent in
# the title. Smaller than _TITLE_WEIGHT so it only *re-orders* papers that
# already share the query words — a phrase match is a tie-break in favour of the
# more on-topic title, not a signal that can outweigh actual word overlap.
_PHRASE_WEIGHT = 1.0
# Damping on the log10 citation term. Keeps "most-cited" a meaningful tie-break
# among similarly-relevant papers without letting it swamp the topic signal.
_CITATION_WEIGHT = 0.4
# Query/title tokens shorter than this are dropped as stop-word-ish noise
# ("a", "of", "is", "the"). 3 keeps useful short terms like "llm", "rag", "gan".
_MIN_TERM_LEN = 3
# A suffix is only stripped when the remaining stem stays at least this long.
# Guards against over-stripping short words into spurious collisions, e.g.
# "ring" -> "r", "bias" -> "bia", "gas" -> "ga". 4 keeps stemming useful for
# real content words ("transformers" -> "transformer", "learning" -> "learn")
# while leaving every short word untouched.
_MIN_STEM_LEN = 4

# One regex, two alternatives: an ASCII alphanumeric run, OR a run of CJK
# characters (CJK unified incl. Ext-A, hiragana, katakana, hangul syllables,
# CJK compatibility ideographs). Matching both in one pass keeps token order so
# adjacency (the phrase bonus) is computed across the original sequence.
_TOKEN_RE = re.compile(
    r"[a-z0-9]+"
    r"|[぀-ヿ㐀-鿿가-힯豈-﫿]+"
)

# Conservative English suffix rules, longest/most-specific first so "ies" wins
# over "s" ("studies" -> "study", not "studie"). Each maps a suffix to its
# replacement. Only applied when the resulting stem stays >= _MIN_STEM_LEN.
_SUFFIX_RULES: tuple[tuple[str, str], ...] = (
    ("ies", "y"),
    ("es", ""),
    ("ed", ""),
    ("ing", ""),
    ("s", ""),
)

# Acronym <-> expansion synonyms. Each entry lets a search for the short form
# surface papers that only write the long form, and vice-versa.
# Why: without this the relevance axis misses a whole class of on-topic papers
# (a "llm" search never matching a "Large Language Models: A Survey" title).
# Only acronyms of length >= _MIN_TERM_LEN are listed — shorter ones ("rl",
# "ml") would be dropped by the stop-word floor before they could be matched.
_SYNONYM_GROUPS: tuple[tuple[str, str], ...] = (
    ("llm", "large language model"),
    ("rag", "retrieval augmented generation"),
    ("gnn", "graph neural network"),
    ("cnn", "convolutional neural network"),
    ("rnn", "recurrent neural network"),
    ("nlp", "natural language processing"),
    ("vlm", "vision language model"),
    ("gan", "generative adversarial network"),
)


def _stem(token: str) -> str:
    """Conservatively normalise one token's English inflection.

    CJK bigrams, digits, and mixed alphanumerics pass through unchanged — only
    pure ASCII alphabetic tokens are stemmed, and only when the stem stays
    ``>= _MIN_STEM_LEN``. A trailing "ss" (``process``, ``address``) is left
    alone so the plural "s" rule does not bite into a doubled consonant.

    Example: ``_stem("transformers") == "transformer"``;
    ``_stem("ring") == "ring"`` (stripping "ing" -> "r" fails the length guard).
    """
    if not token.isascii() or not token.isalpha():
        return token
    for suffix, repl in _SUFFIX_RULES:
        if suffix == "s" and token.endswith("ss"):
            continue
        if token.endswith(suffix):
            stem = token[: len(token) - len(suffix)] + repl
            return stem if len(stem) >= _MIN_STEM_LEN else token
    return token


def _ordered_tokens(text: str) -> list[str]:
    """Position-ordered, stemmed, stop-word-filtered tokens of ``text``.

    ASCII runs become stemmed words kept only when ``len >= _MIN_TERM_LEN``; CJK
    runs become character bigrams (each length 2, always kept). Order is
    preserved across scripts so the bigram (phrase) pass sees real adjacency.
    """
    out: list[str] = []
    for match in _TOKEN_RE.finditer(text.lower()):
        chunk = match.group()
        if chunk[0].isascii():
            stem = _stem(chunk)
            if len(stem) >= _MIN_TERM_LEN:
                out.append(stem)
        elif len(chunk) == 1:
            out.append(chunk)
        else:
            out.extend(chunk[i : i + 2] for i in range(len(chunk) - 1))
    return out


# Acronym -> stemmed long-form tokens. One direction only: an acronym is
# specific, so seeing "llm" in a document safely implies "large language model".
# The REVERSE (long form -> acronym) deliberately is NOT a per-token map — a lone
# shared word like "language" must not inject "nlp"/"vlm"; it requires the whole
# long form and is handled by _SYNONYM_LONG_TO_SHORT below.
_SYNONYM_EXPAND: dict[str, tuple[str, ...]] = {
    short: tuple(_ordered_tokens(long_form))
    for short, long_form in _SYNONYM_GROUPS
}
# Whole stemmed long forms -> acronym: the acronym is added to a document's term
# set only when every token of the long form is present (so "Large Language
# Models" gains "llm", but "language models" alone does not).
_SYNONYM_LONG_TO_SHORT: tuple[tuple[frozenset[str], str], ...] = tuple(
    (frozenset(_ordered_tokens(long_form)), short)
    for short, long_form in _SYNONYM_GROUPS
)


def rank(
    papers: Iterable[Paper],
    keywords: str | None = None,
    current_year: int | None = None,
) -> list[Paper]:
    """Stable sort by descending composite score (relevance + recency + citation).

    ``keywords`` is the raw query string; when given, papers whose title /
    abstract share terms with it rank higher. ``None`` disables the relevance
    axis (single-paper / query-less callers).
    """
    year_base = current_year or _CURRENT_YEAR_FALLBACK
    terms = frozenset(_ordered_tokens(keywords)) if keywords else frozenset()
    bigrams = _bigrams(keywords) if keywords else frozenset()
    return sorted(
        papers,
        key=lambda paper: _score(paper, year_base, terms, bigrams),
        reverse=True,
    )


def _score(
    paper: Paper,
    current_year: int,
    terms: frozenset[str],
    query_bigrams: frozenset[tuple[str, str]],
) -> float:
    return (
        _relevance_score(paper, terms, query_bigrams)
        + _recency_score(paper.year, current_year)
        + _citation_score(paper.citation_count)
    )


def _bigrams(text: str) -> frozenset[tuple[str, str]]:
    """Adjacent token pairs of ``text`` (empty when fewer than two tokens)."""
    tokens = _ordered_tokens(text)
    return frozenset(zip(tokens, tokens[1:], strict=False))


def _term_set(text: str) -> frozenset[str]:
    """Synonym-expanded term set of a document field (title / abstract).

    Documents — not the query — are expanded, so the relevance denominator stays
    the user's actual query size (expanding the query would dilute the fraction).
    """
    base = set(_ordered_tokens(text))
    expanded = set(base)
    for token in base:
        expanded.update(_SYNONYM_EXPAND.get(token, ()))
    for long_tokens, short in _SYNONYM_LONG_TO_SHORT:
        if long_tokens <= base:
            expanded.add(short)
    return frozenset(expanded)


def _relevance_score(
    paper: Paper,
    terms: frozenset[str],
    query_bigrams: frozenset[tuple[str, str]],
) -> float:
    """Title/abstract overlap with the query, title-weighted, plus a phrase bonus.

    Range ``[0, _TITLE_WEIGHT + _ABSTRACT_WEIGHT + _PHRASE_WEIGHT]``. ``0.0``
    when no query terms were supplied, so the score reduces to recency +
    citation.
    """
    if not terms:
        return 0.0
    title_terms = _term_set(paper.title)
    abstract_terms = _term_set(paper.abstract)
    title_hit = len(terms & title_terms) / len(terms)
    abstract_hit = len(terms & abstract_terms) / len(terms)
    score = title_hit * _TITLE_WEIGHT + abstract_hit * _ABSTRACT_WEIGHT
    if query_bigrams:
        matched = len(query_bigrams & _bigrams(paper.title))
        score += _PHRASE_WEIGHT * (matched / len(query_bigrams))
    return score


def _recency_score(year: int | None, current_year: int) -> float:
    if year is None:
        return 0.0
    age = max(0, current_year - year)
    return math.exp(-age / 5.0)


def _citation_score(citations: int | None) -> float:
    if citations is None or citations <= 0:
        return 0.0
    return _CITATION_WEIGHT * math.log10(citations + 1.0)
