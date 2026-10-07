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

Two entry points share one scorer. :func:`rank` returns the sorted papers.
:func:`rank_with_scores` returns the same order with a ``RelevanceScore`` per
paper: the three axis values, the matched terms and phrases, and a sentence for
each contribution, so "why is this paper third?" has an answer.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Set
from dataclasses import dataclass
from datetime import UTC, datetime

from thesisagents.core.diagnostics import RelevanceScore
from thesisagents.core.models import Paper

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
# Time constant of the recency decay: a paper this many years old scores
# 1/e (about 0.37) on the recency axis, one twice as old about 0.14.
_RECENCY_SCALE_YEARS = 5.0
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


#: Acronym -> the long form as written, for the explanation shown to a user.
_LONG_FORMS: dict[str, str] = dict(_SYNONYM_GROUPS)


@dataclass(frozen=True, slots=True)
class RankingPolicy:
    """Weights of the three ranking axes.

    The defaults are the tuned values explained at the top of this module, and
    ``rank()`` always uses them. A caller passes its own policy to
    :func:`rank_with_scores` to weigh the axes differently, for example
    ``RankingPolicy(citation_weight=0.0)`` to ignore citation counts for a
    field where recent work is uncited by nature.
    """

    title_weight: float = _TITLE_WEIGHT
    abstract_weight: float = _ABSTRACT_WEIGHT
    phrase_weight: float = _PHRASE_WEIGHT
    citation_weight: float = _CITATION_WEIGHT
    recency_scale_years: float = _RECENCY_SCALE_YEARS

    def __post_init__(self) -> None:
        weights = (
            self.title_weight, self.abstract_weight,
            self.phrase_weight, self.citation_weight,
        )
        if any(weight < 0 for weight in weights):
            raise ValueError("ranking weights must be >= 0")
        if self.recency_scale_years <= 0:
            raise ValueError("recency_scale_years must be > 0")

    def max_relevance(self, *, has_phrases: bool) -> float:
        """Best relevance a query can earn: every term in title and abstract,
        plus every adjacent query pair adjacent in the title when the query
        has at least two terms."""
        phrase = self.phrase_weight if has_phrases else 0.0
        return self.title_weight + self.abstract_weight + phrase


DEFAULT_RANKING_POLICY = RankingPolicy()


@dataclass(frozen=True, slots=True)
class RankedPaper:
    """One paper with its score breakdown and its 1-based position."""

    paper: Paper
    score: RelevanceScore
    rank: int


@dataclass(frozen=True, slots=True)
class _QueryTerms:
    """The query, tokenised once and shared by every paper's scoring.

    ``ordered`` and ``phrases`` keep query order so explanations list matches
    the way the user typed them. ``terms`` is the same content as a set for
    the overlap arithmetic.
    """

    ordered: tuple[str, ...] = ()
    terms: frozenset[str] = frozenset()
    phrases: tuple[tuple[str, str], ...] = ()

    @classmethod
    def parse(cls, keywords: str | None) -> _QueryTerms:
        if not keywords:
            return cls()
        tokens = _ordered_tokens(keywords)
        pairs = zip(tokens, tokens[1:], strict=False)
        return cls(
            ordered=tuple(dict.fromkeys(tokens)),
            terms=frozenset(tokens),
            phrases=tuple(dict.fromkeys(pairs)),
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

    The order is exactly :func:`rank_with_scores` with the default policy.
    Call that instead when the score behind each position is wanted.
    """
    ranked = rank_with_scores(papers, keywords, current_year=current_year)
    return [entry.paper for entry in ranked]


def rank_with_scores(
    papers: Iterable[Paper],
    keywords: str | None = None,
    policy: RankingPolicy | None = None,
    *,
    current_year: int | None = None,
) -> list[RankedPaper]:
    """Rank ``papers`` and keep the reason for each position.

    Same scoring and the same stable sort as :func:`rank`: papers with equal
    scores stay in their input order. Each :class:`RankedPaper` carries the
    three axis values, the query terms and phrases that matched, and a
    sentence per contribution.

    Example::

        for entry in rank_with_scores(papers, "retrieval augmented generation"):
            print(entry.rank, f"{entry.score.total:.2f}", entry.paper.title)
            for reason in entry.score.reasons:
                print("   ", reason)

    ``current_year`` pins "now" for the recency axis so tests and replays are
    deterministic. It defaults to the current UTC year.
    """
    chosen = policy if policy is not None else DEFAULT_RANKING_POLICY
    year_base = current_year if current_year is not None else datetime.now(UTC).year
    query = _QueryTerms.parse(keywords)
    scored = [(paper, _score_paper(paper, query, year_base, chosen)) for paper in papers]
    scored.sort(key=lambda pair: pair[1].total, reverse=True)
    return [
        RankedPaper(paper=paper, score=score, rank=position)
        for position, (paper, score) in enumerate(scored, start=1)
    ]


def title_terms(title: str) -> frozenset[str]:
    """Stemmed content terms of a title, with no synonym expansion.

    Shared with ``pruning.py``, which compares two titles term by term and
    must tokenise them exactly the way ranking does.

    Example: ``title_terms("Transformers for Vision")`` is
    ``frozenset({"transformer", "for", "vision"})``.
    """
    return frozenset(_ordered_tokens(title))


def _score_paper(
    paper: Paper, query: _QueryTerms, current_year: int, policy: RankingPolicy
) -> RelevanceScore:
    relevance = _relevance_part(paper, query, policy)
    recency = _recency_score(paper.year, current_year, policy)
    citation = _citation_score(paper.citation_count, policy)
    reasons = (
        *relevance.reasons,
        _recency_reason(paper.year, recency),
        _citation_reason(paper.citation_count, citation),
    )
    ratio = None
    if query.terms:
        best = policy.max_relevance(has_phrases=bool(query.phrases))
        ratio = relevance.value / best if best > 0 else 0.0
    return RelevanceScore(
        total=relevance.value + recency + citation,
        relevance=relevance.value,
        recency=recency,
        citation=citation,
        matched_terms=relevance.matched_terms,
        matched_phrases=relevance.matched_phrases,
        reasons=reasons,
        relevance_ratio=ratio,
    )


def _bigrams(text: str) -> frozenset[tuple[str, str]]:
    """Adjacent token pairs of ``text`` (empty when fewer than two tokens)."""
    tokens = _ordered_tokens(text)
    return frozenset(zip(tokens, tokens[1:], strict=False))


def _expand_terms(base: Set[str]) -> frozenset[str]:
    """``base`` plus the synonyms its tokens imply (see ``_SYNONYM_GROUPS``)."""
    expanded = set(base)
    for token in base:
        expanded.update(_SYNONYM_EXPAND.get(token, ()))
    for long_tokens, short in _SYNONYM_LONG_TO_SHORT:
        if long_tokens <= base:
            expanded.add(short)
    return frozenset(expanded)


def _term_set(text: str) -> frozenset[str]:
    """Synonym-expanded term set of a document field (title / abstract).

    Documents — not the query — are expanded, so the relevance denominator stays
    the user's actual query size (expanding the query would dilute the fraction).
    """
    return _expand_terms(set(_ordered_tokens(text)))


@dataclass(frozen=True, slots=True)
class _RelevancePart:
    """The relevance axis of one paper, with what produced it."""

    value: float = 0.0
    matched_terms: tuple[str, ...] = ()
    matched_phrases: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()


def _relevance_part(
    paper: Paper, query: _QueryTerms, policy: RankingPolicy
) -> _RelevancePart:
    """Title/abstract overlap with the query, title-weighted, plus a phrase bonus.

    Range ``[0, policy.max_relevance(...)]``. ``0.0`` when no query terms were
    supplied, so the score reduces to recency + citation.
    """
    if not query.terms:
        return _RelevancePart(
            reasons=("no query: ranked by recency and citations only",)
        )
    title_base = set(_ordered_tokens(paper.title))
    abstract_base = set(_ordered_tokens(paper.abstract))
    in_title = query.terms & _expand_terms(title_base)
    in_abstract = query.terms & _expand_terms(abstract_base)
    title_points = len(in_title) / len(query.terms) * policy.title_weight
    abstract_points = len(in_abstract) / len(query.terms) * policy.abstract_weight
    value = title_points + abstract_points
    reasons = [
        *_field_reason("title", in_title, query, title_points),
        *_field_reason("abstract", in_abstract, query, abstract_points),
    ]
    phrases: tuple[str, ...] = ()
    if query.phrases:
        title_pairs = _bigrams(paper.title)
        hits = [pair for pair in query.phrases if pair in title_pairs]
        phrase_points = policy.phrase_weight * (len(hits) / len(query.phrases))
        value += phrase_points
        phrases = tuple(" ".join(pair) for pair in hits)
        if hits:
            quoted = ", ".join(f'"{phrase}"' for phrase in phrases)
            reasons.append(
                f"query words adjacent in the title ({quoted}): +{phrase_points:.2f}"
            )
    matched = tuple(term for term in query.ordered if term in in_title | in_abstract)
    reasons.extend(_synonym_reasons(matched, title_base | abstract_base))
    if not matched:
        reasons.append("no query term appears in the title or abstract")
    return _RelevancePart(
        value=value,
        matched_terms=matched,
        matched_phrases=phrases,
        reasons=tuple(reasons),
    )


def _field_reason(
    field: str, hits: Set[str], query: _QueryTerms, points: float
) -> list[str]:
    """One sentence for a title / abstract overlap, or nothing when it is empty."""
    if not hits:
        return []
    listed = ", ".join(term for term in query.ordered if term in hits)
    return [
        f"{field} matches {len(hits)} of {len(query.terms)} query terms "
        f"({listed}): +{points:.2f}"
    ]


def _synonym_reasons(matched: Iterable[str], literal_tokens: Set[str]) -> list[str]:
    """Say which matches came through an acronym and not the word itself.

    ``literal_tokens`` are the tokens the title and abstract really contain. A
    matched query term that is not among them was supplied by the synonym
    expansion, and a user who searched "llm" deserves to know the paper says
    "large language model" instead.
    """
    notes: list[str] = []
    for term in matched:
        if term in literal_tokens:
            continue
        long_form = _LONG_FORMS.get(term)
        if long_form is not None:
            notes.append(f'"{term}" matched through its long form "{long_form}"')
            continue
        acronyms = sorted(
            short
            for short, long_tokens in _SYNONYM_EXPAND.items()
            if short in literal_tokens and term in long_tokens
        )
        if acronyms:
            notes.append(f'"{term}" matched through the acronym "{acronyms[0]}"')
    return notes


def _recency_score(
    year: int | None, current_year: int, policy: RankingPolicy = DEFAULT_RANKING_POLICY
) -> float:
    if year is None:
        return 0.0
    age = max(0, current_year - year)
    return math.exp(-age / policy.recency_scale_years)


def _recency_reason(year: int | None, points: float) -> str:
    if year is None:
        return "publication year unknown: recency +0.00"
    return f"published {year}: recency +{points:.2f}"


def _citation_score(
    citations: int | None, policy: RankingPolicy = DEFAULT_RANKING_POLICY
) -> float:
    if citations is None or citations <= 0:
        return 0.0
    return policy.citation_weight * math.log10(citations + 1.0)


def _citation_reason(citations: int | None, points: float) -> str:
    if citations is None:
        return "citation count unknown: citations +0.00"
    return f"{citations:,} citations: +{points:.2f}"
