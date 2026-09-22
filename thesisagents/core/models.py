"""Core domain models. Frozen dataclasses; mutations create new instances."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, replace
from typing import Any

from thesisagents.core.constants import (
    ABSTRACT_TRUNCATE_CHARS,
    DEFAULT_PAGE_SIZE,
    MAX_RESULTS_PER_SOURCE,
)
from thesisagents.core.exceptions import ThesisAgentsError

_TITLE_NOISE_RE = re.compile(r"[^a-z0-9]+")


def _canon_title(title: str) -> str:
    """Canonical title form for dedup hashing: lowercase with every
    non-alphanumeric run (punctuation, whitespace) stripped.

    ``"Attention Is All You Need"``, ``"Attention is all you need."`` and
    ``"Attention—Is All You Need"`` all map to ``"attentionisallyouneed"``,
    so cross-source punctuation/spacing noise collapses into one dedup key.
    """
    return _TITLE_NOISE_RE.sub("", title.lower())


def _canon_author(name: str) -> str:
    """Canonical surname token of an author name for dedup hashing.

    Sources format the first author differently — ``"Vaswani, Ashish"``
    (PubMed), ``"Ashish Vaswani"`` (arXiv), ``"A. Vaswani"`` (Crossref). Reduce
    each to its surname so a DOI-less paper isn't split into duplicates by name
    formatting: a comma form keeps the part before the comma, otherwise the last
    whitespace-separated token. All three examples above collapse to
    ``"vaswani"``.
    """
    name = name.strip().lower()
    if not name:
        return ""
    if "," in name:
        return name.split(",", 1)[0].strip()
    parts = name.split()
    return parts[-1] if parts else ""


@dataclass(frozen=True, slots=True)
class RqResult:
    """One research-question evaluation block: question + result table + bullets.

    ``table`` rows include the header row as the first entry. ``analysis``
    bullets sit underneath the table.
    """

    rq_id: str
    question: str
    table: tuple[tuple[str, ...], ...] = ()
    analysis: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PaperSummary:
    """Structured summary of a paper, ready to drive the slide deck.

    Two tiers of fields:

    * **Lightweight** (``motivation`` … ``takeaways``): used when only an
      abstract is available, or when an LLM produces a quick summary. Each
      list is a sequence of bullet-ready sentences.
    * **Rich** (``pain_points`` … ``rq_results``): used when the LLM has
      read the full paper and can produce a thesis-style deck — multi-column
      pain-point quadrants, headline KPI metrics, technique-comparison
      tables, per-RQ result tables, etc.

    Either tier may be partially populated. The exporter renders only the
    slide variants whose underlying field has content; everything is
    skippable so a paper without (say) tabular results just omits those
    slides instead of emitting blanks.
    """

    language: str

    # ---- Lightweight (abstract-only) tier ----------------------------------
    motivation: tuple[str, ...] = ()
    contributions: tuple[str, ...] = ()
    method: tuple[str, ...] = ()
    results: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    takeaways: tuple[str, ...] = ()

    # ---- Rich (full-text) tier ---------------------------------------------
    #: Pain-points / background for a multi-column or 4-quadrant slide.
    #: Each entry is (sub-heading, bullets).
    pain_points: tuple[tuple[str, tuple[str, ...]], ...] = ()
    #: A single highlighted research question rendered in a callout box.
    research_question: str = ""
    #: Contributions with named sub-headings — drives a structured (not flat
    #: bullet) Contributions slide. Each entry is (heading, description).
    contributions_detailed: tuple[tuple[str, str], ...] = ()
    #: Headline KPIs rendered as bold inline numbers. Each entry is
    #: (label, value, optional_baseline).
    headline_metrics: tuple[tuple[str, str, str], ...] = ()
    #: Two-column "technique → role" table.
    technique_table: tuple[tuple[str, str], ...] = ()
    #: Literature positioning table — first row is the header.
    literature_table: tuple[tuple[str, ...], ...] = ()
    #: Method sub-sections — each (heading, bullets).
    method_sections: tuple[tuple[str, tuple[str, ...]], ...] = ()
    #: Evaluation method sub-sections — each (heading, bullets).
    evaluation_sections: tuple[tuple[str, tuple[str, ...]], ...] = ()
    #: Sequential system-flow steps (bullets).
    system_flow: tuple[str, ...] = ()
    #: Research questions, each (id, question).
    research_questions: tuple[tuple[str, str], ...] = ()
    #: Per-RQ result blocks.
    rq_results: tuple[RqResult, ...] = ()
    #: Closing one-paragraph "core observation" rendered as a highlight box.
    core_observation: str = ""
    #: Future-work bullets (limitations stays in the lightweight tier).
    future_work: tuple[str, ...] = ()
    #: Figures from the paper, each as (caption, image_path, description
    #: bullets). ``image_path`` is a filesystem path to a PNG/JPEG; the
    #: exporter copies it onto a dedicated slide above the caption.
    figures: tuple[tuple[str, str, tuple[str, ...]], ...] = ()
    #: Tables that appear in the paper (distinct from per-RQ result tables
    #: which already live on rq_results). Each entry is (caption, rows,
    #: analysis bullets); ``rows[0]`` is the header row.
    paper_tables: tuple[
        tuple[str, tuple[tuple[str, ...], ...], tuple[str, ...]], ...
    ] = ()

    raw_text_chars: int = 0
    model: str = ""

    def is_empty(self) -> bool:
        return not any((
            self.motivation, self.contributions, self.method,
            self.results, self.limitations, self.takeaways,
            self.pain_points, self.research_question, self.contributions_detailed,
            self.headline_metrics, self.technique_table, self.literature_table,
            self.method_sections, self.evaluation_sections, self.system_flow,
            self.research_questions, self.rq_results, self.core_observation,
            self.future_work, self.figures, self.paper_tables,
        ))

    def has_rich_fields(self) -> bool:
        return bool(
            self.pain_points or self.research_question
            or self.contributions_detailed or self.headline_metrics
            or self.technique_table or self.literature_table
            or self.method_sections or self.evaluation_sections
            or self.system_flow or self.research_questions
            or self.rq_results or self.core_observation
            or self.future_work or self.figures or self.paper_tables
        )


@dataclass(frozen=True, slots=True)
class FieldProvenance:
    """Record which source supplied one normalised paper field.

    This keeps cross-source merge decisions auditable without retaining an
    entire upstream payload. For example, a canonical ACM record may carry
    ``FieldProvenance("pdf_url", "openalex", "W123")`` after OpenAlex
    supplies the missing open-access PDF URL.
    """

    field: str
    source: str
    source_id: str


@dataclass(frozen=True, slots=True)
class Paper:
    """One paper, normalised across sources."""

    source: str
    source_id: str
    title: str
    authors: tuple[str, ...]
    year: int | None
    venue: str | None
    abstract: str
    url: str
    doi: str | None = None
    arxiv_id: str | None = None
    citation_count: int | None = None
    pdf_url: str | None = None
    summary: PaperSummary | None = None
    provenance: tuple[FieldProvenance, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    def doi_key(self) -> str | None:
        """Normalised DOI identity key, or ``None`` when the paper has no DOI."""
        return f"doi:{self.doi.lower().strip()}" if self.doi else None

    def arxiv_key(self) -> str | None:
        """Normalised arXiv identity key, or ``None`` when there is no arXiv ID.

        The version suffix is dropped — ``2401.00001v1`` and ``2401.00001v2``
        are one paper (a revision), so they must collapse.
        """
        if not self.arxiv_id:
            return None
        stripped = re.sub(r"v\d+$", "", self.arxiv_id.strip().lower())
        return f"arxiv:{stripped}"

    def title_key(self) -> str:
        """Fuzzy identity key over canonical title + first-author surname + year.

        Both components are normalised so cosmetic cross-source differences
        don't split one paper into two records: :func:`_canon_title` strips
        punctuation and case (``"Attention Is All You Need"`` ==
        ``"Attention is all you need."``), and :func:`_canon_author` reduces the
        first author to a surname (``"Vaswani, Ashish"`` == ``"Ashish Vaswani"``
        == ``"A. Vaswani"``).
        """
        first_author = _canon_author(self.authors[0]) if self.authors else ""
        seed = f"{_canon_title(self.title)}|{first_author}|{self.year or ''}"
        digest = hashlib.sha256(seed.encode("utf-8"), usedforsecurity=False).hexdigest()
        return f"hash:{digest[:16]}"

    def identity_keys(self) -> tuple[str, ...]:
        """EVERY key under which this paper can be recognised, strongest first.

        A paper carries up to three identities at once — its DOI, its arXiv ID,
        and its fuzzy title hash — and sources populate different subsets of
        them. Crossref returns a DOI and no arXiv ID; arXiv returns the reverse;
        a Scholar scrape often has neither. Treating only the *strongest*
        available key as the paper's identity (what :meth:`dedup_key` returns)
        means a DOI-less ACM record and a DOI-carrying OpenAlex record of the
        same paper never even compare, and both ship in the results.

        :func:`thesisagents.core.dedup.dedupe` therefore groups on the whole
        tuple: papers sharing ANY key are the same paper.

        Example: ``Paper(doi="10.1/x", arxiv_id="2401.1", title="On X")`` →
        ``("doi:10.1/x", "arxiv:2401.1", "hash:…")``.
        """
        keys: list[str] = []
        doi = self.doi_key()
        if doi:
            keys.append(doi)
        arxiv = self.arxiv_key()
        if arxiv:
            keys.append(arxiv)
        keys.append(self.title_key())
        return tuple(keys)

    def dedup_key(self) -> str:
        """The single strongest identity key: DOI, else arXiv ID, else title hash.

        Kept as the paper's canonical one-line identity (logs, cache keys,
        stable ordering). Dedup itself matches on :meth:`identity_keys` —
        see that method for why one key is not enough.
        """
        return self.identity_keys()[0]

    def bibtex_key(self) -> str:
        """Deterministic BibTeX cite key.

        Why the ``surname_tokens`` guard: ``authors`` is not guaranteed to hold
        printable names. An MCP ``export`` payload written by an LLM agent, or a
        scraped record whose author cell was blank, can carry ``("",)`` — and
        ``"".split()[-1]`` is an ``IndexError``. Because ``bibtex_key`` is called
        from the PDF downloader, the OA resolver and the per-paper deck emitter,
        that single blank string used to abort a whole run. Fall back to
        ``"anon"``, exactly as for a paper with no authors at all.

        Example: ``Paper(authors=("",), title="On X", year=2024).bibtex_key()``
        returns ``"anon2024untitled"``-style output instead of raising.
        """
        first_author_last = "anon"
        if self.authors:
            surname_tokens = self.authors[0].split()
            if surname_tokens:
                first_author_last = surname_tokens[-1].lower()
        year_part = str(self.year) if self.year else "nd"
        title_word = "untitled"
        for token in self.title.split():
            stripped = "".join(c for c in token.lower() if c.isalnum())
            if len(stripped) >= 4:
                title_word = stripped
                break
        return f"{first_author_last}{year_part}{title_word}"

    def short_abstract(self) -> str:
        """Abstract truncated for slides / summaries."""
        cleaned = " ".join(self.abstract.split())
        if len(cleaned) <= ABSTRACT_TRUNCATE_CHARS:
            return cleaned
        return cleaned[: ABSTRACT_TRUNCATE_CHARS - 1].rstrip() + "…"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_id": self.source_id,
            "title": self.title,
            "authors": list(self.authors),
            "year": self.year,
            "venue": self.venue,
            "abstract": self.abstract,
            "url": self.url,
            "doi": self.doi,
            "arxiv_id": self.arxiv_id,
            "citation_count": self.citation_count,
            "pdf_url": self.pdf_url,
            "summary": _summary_to_dict(self.summary),
            "provenance": [
                {
                    "field": entry.field,
                    "source": entry.source,
                    "source_id": entry.source_id,
                }
                for entry in self.provenance
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Paper:
        """Rebuild a ``Paper`` from its ``to_dict()`` shape.

        The four identity fields (``source`` / ``source_id`` / ``title`` /
        ``url``) are required, but a missing one raises a named
        :class:`ThesisAgentsError` rather than a bare ``KeyError``. Why: the
        documented LLM-as-agent path hands hand-written paper dicts to the MCP
        ``export`` / ``download_pdfs`` tools, and an omitted ``url`` used to
        surface as an opaque ``KeyError: 'url'`` with no hint about which paper
        or which field was at fault.

        Example: ``Paper.from_dict({"source": "arxiv"})`` raises
        ``"paper dict is missing required field(s): source_id, title, url"``.
        """
        missing = [
            name
            for name in ("source", "source_id", "title", "url")
            if data.get(name) is None
        ]
        if missing:
            raise ThesisAgentsError(
                "paper dict is missing required field(s): "
                f"{', '.join(missing)} (got keys: {', '.join(sorted(data)) or '<none>'})"
            )
        return cls(
            source=data["source"],
            source_id=data["source_id"],
            title=data["title"],
            authors=tuple(data.get("authors") or ()),
            year=data.get("year"),
            venue=data.get("venue"),
            abstract=data.get("abstract") or "",
            url=data["url"],
            doi=data.get("doi"),
            arxiv_id=data.get("arxiv_id"),
            citation_count=data.get("citation_count"),
            pdf_url=data.get("pdf_url"),
            summary=_summary_from_dict(data.get("summary")),
            # Provenance is bookkeeping, never load-bearing: a half-written
            # entry must not sink an otherwise valid paper, so entries are
            # filled with "" rather than raising.
            provenance=tuple(
                FieldProvenance(
                    field=str(entry.get("field") or ""),
                    source=str(entry.get("source") or ""),
                    source_id=str(entry.get("source_id") or ""),
                )
                for entry in (data.get("provenance") or ())
                if isinstance(entry, dict)
            ),
        )


def _summary_to_dict(summary: PaperSummary | None) -> dict[str, Any] | None:
    if summary is None:
        return None
    return {
        "language": summary.language,
        "motivation": list(summary.motivation),
        "contributions": list(summary.contributions),
        "method": list(summary.method),
        "results": list(summary.results),
        "limitations": list(summary.limitations),
        "takeaways": list(summary.takeaways),
        "pain_points": [[h, list(b)] for h, b in summary.pain_points],
        "research_question": summary.research_question,
        "contributions_detailed": [list(pair) for pair in summary.contributions_detailed],
        "headline_metrics": [list(triple) for triple in summary.headline_metrics],
        "technique_table": [list(pair) for pair in summary.technique_table],
        "literature_table": [list(row) for row in summary.literature_table],
        "method_sections": [[h, list(b)] for h, b in summary.method_sections],
        "evaluation_sections": [[h, list(b)] for h, b in summary.evaluation_sections],
        "system_flow": list(summary.system_flow),
        "research_questions": [list(pair) for pair in summary.research_questions],
        "rq_results": [
            {
                "rq_id": r.rq_id,
                "question": r.question,
                "table": [list(row) for row in r.table],
                "analysis": list(r.analysis),
            }
            for r in summary.rq_results
        ],
        "core_observation": summary.core_observation,
        "future_work": list(summary.future_work),
        "figures": [
            [cap, path, list(bullets)] for cap, path, bullets in summary.figures
        ],
        "paper_tables": [
            [cap, [list(row) for row in rows], list(analysis)]
            for cap, rows, analysis in summary.paper_tables
        ],
        "raw_text_chars": summary.raw_text_chars,
        "model": summary.model,
    }


def _summary_from_dict(data: dict[str, Any] | None) -> PaperSummary | None:
    if not data:
        return None
    return PaperSummary(
        language=data.get("language", "en"),
        motivation=tuple(data.get("motivation") or ()),
        contributions=tuple(data.get("contributions") or ()),
        method=tuple(data.get("method") or ()),
        results=tuple(data.get("results") or ()),
        limitations=tuple(data.get("limitations") or ()),
        takeaways=tuple(data.get("takeaways") or ()),
        pain_points=tuple(
            (h, tuple(b)) for h, b in (data.get("pain_points") or ())
        ),
        research_question=data.get("research_question") or "",
        contributions_detailed=tuple(
            tuple(pair) for pair in (data.get("contributions_detailed") or ())
        ),
        headline_metrics=tuple(
            tuple(triple) for triple in (data.get("headline_metrics") or ())
        ),
        technique_table=tuple(
            tuple(pair) for pair in (data.get("technique_table") or ())
        ),
        literature_table=tuple(
            tuple(row) for row in (data.get("literature_table") or ())
        ),
        method_sections=tuple(
            (h, tuple(b)) for h, b in (data.get("method_sections") or ())
        ),
        evaluation_sections=tuple(
            (h, tuple(b)) for h, b in (data.get("evaluation_sections") or ())
        ),
        system_flow=tuple(data.get("system_flow") or ()),
        research_questions=tuple(
            tuple(pair) for pair in (data.get("research_questions") or ())
        ),
        rq_results=tuple(
            RqResult(
                rq_id=r.get("rq_id", ""),
                question=r.get("question", ""),
                table=tuple(tuple(row) for row in r.get("table") or ()),
                analysis=tuple(r.get("analysis") or ()),
            )
            for r in (data.get("rq_results") or ())
        ),
        core_observation=data.get("core_observation") or "",
        future_work=tuple(data.get("future_work") or ()),
        figures=tuple(
            (cap, path, tuple(bullets))
            for cap, path, bullets in (data.get("figures") or ())
        ),
        paper_tables=tuple(
            (cap, tuple(tuple(row) for row in rows), tuple(analysis))
            for cap, rows, analysis in (data.get("paper_tables") or ())
        ),
        raw_text_chars=data.get("raw_text_chars") or 0,
        model=data.get("model") or "",
    )


@dataclass(frozen=True, slots=True)
class Query:
    """A normalised search request."""

    keywords: str
    sources: tuple[str, ...]
    max_results: int = DEFAULT_PAGE_SIZE
    year_from: int | None = None
    year_to: int | None = None
    min_citations: int | None = None
    #: When True, the pipeline drops papers whose venue isn't on the
    #: top-tier whitelist (see ``thesisagents/core/top_venues.py``).
    #: Default is False everywhere; the CLI exposes it as the opt-in
    #: ``--top-tier-only`` flag.
    top_tier_only: bool = False

    def __post_init__(self) -> None:
        if not self.keywords.strip():
            raise ValueError("keywords must be non-empty")
        if not self.sources:
            raise ValueError("at least one source must be specified")
        if self.max_results < 1 or self.max_results > MAX_RESULTS_PER_SOURCE:
            raise ValueError(
                f"max_results must be in [1, {MAX_RESULTS_PER_SOURCE}]"
            )
        if (
            self.year_from is not None
            and self.year_to is not None
            and self.year_from > self.year_to
        ):
            raise ValueError("year_from must be <= year_to")

    def with_max(self, max_results: int) -> Query:
        return replace(self, max_results=max_results)

    @staticmethod
    def clamp_max_results(count: int) -> int:
        """Clamp a paper count into the legal ``max_results`` range.

        For callers that build a *synthetic* Query purely to satisfy
        ``PaperCollection`` — the MCP ``export`` / ``download_pdfs`` tools and
        the CLI's ``--pdf <directory>`` mode — ``max_results`` describes nothing
        the pipeline will act on; it just has to be valid. Passing the raw
        paper count made a 250-paper export die on
        ``ValueError: max_results must be in [1, 200]``, an error about a
        per-source page size that the caller never set.

        Example: ``Query.clamp_max_results(0)`` -> ``1``;
        ``Query.clamp_max_results(250)`` -> ``200``.
        """
        return max(1, min(count, MAX_RESULTS_PER_SOURCE))


@dataclass(frozen=True, slots=True)
class PaperCollection:
    """An ordered, deduplicated set of papers produced by the pipeline."""

    query: Query
    papers: tuple[Paper, ...]

    def __len__(self) -> int:
        return len(self.papers)

    def __iter__(self):
        return iter(self.papers)

    def __getitem__(self, index: int) -> Paper:
        return self.papers[index]


@dataclass(frozen=True, slots=True)
class ExportOptions:
    """Parameters controlling export rendering."""

    formats: tuple[str, ...]
    out_dir: str
    filename_stem: str | None = None
    pptx_template: str | None = None
    include_abstract: bool = True
    language: str = "en"
    #: Hard cap on slides per paper for the pptx exporter. Defaults to
    #: 25 — enough to keep the rich-tier deck intact for typical papers
    #: while protecting against content-heavy outliers blowing up the
    #: deck. Use ``0`` (or any non-positive int) to disable the cap and
    #: render the full deck regardless of size; ``None`` is treated
    #: identically to the default.
    max_slides_per_paper: int | None = 25
    #: When True, the pptx exporter applies a dark-mode palette
    #: post-build: dark slide background, light text, dark table-row
    #: stripe. **Defaults to False** — the project's default deck is now
    #: the light navy-band style (white slides, full-width navy header
    #: band with a white title, navy cover panel). Pass ``--dark-mode``
    #: on the CLI / tick the "Dark mode" box in the GUI Deck tab (or set
    #: this True) for OLED projectors / low-light venues, where the
    #: post-build pass lightens the band / cover / table fills so the
    #: same chrome reads on the dark background.
    dark_mode: bool = False

    def __post_init__(self) -> None:
        if not self.formats:
            raise ValueError("at least one export format must be specified")
