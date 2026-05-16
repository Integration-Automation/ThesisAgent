"""Core domain models. Frozen dataclasses; mutations create new instances."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from typing import Any

from autopapertoppt.core.constants import (
    ABSTRACT_TRUNCATE_CHARS,
    DEFAULT_PAGE_SIZE,
    MAX_RESULTS_PER_SOURCE,
)


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
    raw: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    def dedup_key(self) -> str:
        """Stable identity for dedup across sources.

        Why: Google Scholar and Semantic Scholar may return the same paper with
        different source-side IDs. DOI is best; arXiv ID next; otherwise hash
        title + first-author + year.
        """
        if self.doi:
            return f"doi:{self.doi.lower()}"
        if self.arxiv_id:
            return f"arxiv:{self.arxiv_id.lower()}"
        first_author = self.authors[0].lower() if self.authors else ""
        seed = f"{self.title.strip().lower()}|{first_author}|{self.year or ''}"
        digest = hashlib.sha256(seed.encode("utf-8"), usedforsecurity=False).hexdigest()
        return f"hash:{digest[:16]}"

    def bibtex_key(self) -> str:
        """Deterministic BibTeX cite key."""
        first_author_last = "anon"
        if self.authors:
            first_author_last = self.authors[0].split()[-1].lower()
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
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Paper:
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
    #: top-tier whitelist (see ``autopapertoppt/core/top_venues.py``).
    #: Default is False so library callers see the historical behaviour;
    #: the CLI flips this on by default.
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

    def __post_init__(self) -> None:
        if not self.formats:
            raise ValueError("at least one export format must be specified")
