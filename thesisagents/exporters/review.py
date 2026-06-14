"""One-stop deck reviewer: overflow + colour-contract + section completeness.

Why this exists
---------------
The three deck-quality contracts used to live in separate places — slide overflow
in ``scripts/check_overflow.py``, the dark-mode / no-red / contrast rules in
``scripts/_audit_dark_text.py``, and the "does a thesis deck cover the seven
``paper_rule`` sections" judgement only in a human-read subagent. To review a
deck you had to run several tools and eyeball the section coverage. ``review_deck``
folds all three into one call, exposed as the CLI ``review`` subcommand and the
MCP ``pptx_review`` tool.

What it reports
---------------
1. **overflow** — shapes whose wrapped text crosses their box or the 7.05" footer
   guard (reuses ``overflow.check_pptx_from_prs``).
2. **contrast** — invisible / red / light-on-light runs (reuses
   ``audit.audit_prs``); ``hard`` issues fail the deck, warnings don't.
3. **completeness** — which of the canonical ``paper_rule`` sections
   (Introduction, Literature Review, Methodology, Experiment, Conclusion,
   References) the deck's slides cover, recovered from the exporter's own
   ``_categorise_slides`` title classifier. This is only a PASS/FAIL gate for a
   *thesis-style* deck — a lightweight abstract-only deck legitimately lacks most
   sections and is never failed for it (``thesis_style`` flag says which).

``review_deck(path, language=None) -> DeckReview``. ``language`` may be omitted —
it is then auto-detected from the slide titles.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from pptx import Presentation

from thesisagents.exporters.audit import Issue, audit_prs
from thesisagents.exporters.i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    normalise_language,
)
from thesisagents.exporters.overflow import Violation, check_pptx_from_prs

# Reuse the exporter's own tested title -> category classifier rather than
# re-deriving one. Same package; the leading underscore marks it internal to the
# exporters layer, which review.py is part of.
from thesisagents.exporters.pptx import _categorise_slides

# Canonical paper_rule body sections -> the slide CATEGORIES that satisfy each. A
# deck "covers" a section if at least one slide carries one of its categories.
# Two of the seven paper_rule sections are intentionally NOT gated here:
#   * Abstract — the cover + overview always provide it, so it can't go missing.
#   * References — the rich single-paper tier folds the cited paper into the
#     cover / contribution-summary instead of a distinct references slide, so
#     gating on a references slide would false-fail every such deck.
# What remains are exactly the five body sections CLAUDE.md flags as the ones a
# rich deck must not drop (Literature Review, Experiment, Conclusion in
# particular).
_SECTION_CATEGORIES: tuple[tuple[str, frozenset[str]], ...] = (
    ("introduction", frozenset({
        "overview", "pain_points", "research_question",
        "contributions", "contribution_summary",
    })),
    ("literature_review", frozenset({"technique_table", "literature_table"})),
    ("methodology", frozenset({"method_details", "system_overview"})),
    ("experiment", frozenset({
        "evaluation", "research_questions", "rq_results", "metrics",
    })),
    ("conclusion", frozenset({"limitations_future", "core_observation"})),
)

# Categories only a thesis-style (rich) deck emits. Completeness is a PASS/FAIL
# gate only when one of these is present; otherwise the deck is lightweight and
# its missing sections are advisory, not a failure.
_THESIS_CATEGORIES = frozenset({
    "pain_points", "research_question", "method_details", "evaluation",
    "research_questions", "rq_results", "technique_table", "literature_table",
    "system_overview", "metrics", "core_observation", "limitations_future",
    "contribution_summary",
})


@dataclass(frozen=True)
class DeckReview:
    path: str
    language: str
    thesis_style: bool
    overflow: tuple[Violation, ...]
    contrast: tuple[Issue, ...]
    missing_sections: tuple[str, ...]
    references_missing: bool = False

    @property
    def hard_contrast(self) -> list[Issue]:
        """Contrast issues that fail the deck (invisible / red / light-on-light)."""
        return [i for i in self.contrast if i.hard]

    @property
    def completeness_failed(self) -> bool:
        """When missing sections fail the deck.

        Two different gates, because the exporter emits the sections under
        different conditions:
          * the five body sections gate only a *thesis-style* deck (a lightweight
            abstract-only deck legitimately lacks them), and
          * ``references`` gates only a *multi-paper* deck, which always carries a
            references slide — a single-paper rich deck folds references into the
            cover and an own-thesis deck omits self-citation, so neither is failed.
        """
        body_missing = any(s != "references" for s in self.missing_sections)
        return self.references_missing or (self.thesis_style and body_missing)

    @property
    def ok(self) -> bool:
        return not (self.overflow or self.hard_contrast or self.completeness_failed)

    def to_dict(self) -> dict:
        """JSON-friendly shape for the MCP ``pptx_review`` tool."""
        return {
            "path": self.path,
            "language": self.language,
            "thesis_style": self.thesis_style,
            "ok": self.ok,
            "overflow": [
                {
                    "slide": v.slide, "shape": v.shape, "kind": v.kind,
                    "rendered_in": v.rendered_in, "limit_in": v.limit_in,
                }
                for v in self.overflow
            ],
            "contrast": [
                {
                    "slide": i.slide, "shape": i.shape, "kind": i.kind,
                    "detail": i.detail, "hard": i.hard,
                }
                for i in self.contrast
            ],
            "missing_sections": list(self.missing_sections),
            "references_missing": self.references_missing,
            "completeness_gated": self.thesis_style,
        }


def _detect_language(prs) -> str:
    """Best-guess the deck's language from how many slide titles a locale matches.

    The exporter localises every section title, so the deck's real language is
    the one whose strings classify the most slides (``cover`` / ``overview`` are
    language-independent and excluded from the score). Ties / no match -> ``en``.
    """
    best_lang, best_score = DEFAULT_LANGUAGE, -1
    for lang in SUPPORTED_LANGUAGES:
        cats = _categorise_slides(prs, lang)
        score = sum(c not in ("unknown", "cover", "overview") for c in cats)
        if score > best_score:
            best_lang, best_score = lang, score
    return best_lang


def review_deck(path: str | Path, language: str | None = None) -> DeckReview:
    """Run all three deck audits and return a consolidated ``DeckReview``.

    Loads the ``.pptx`` once and shares the open object across the overflow,
    contrast, and completeness passes. ``language`` is auto-detected when omitted.
    """
    prs = Presentation(str(path))
    lang = normalise_language(language) if language else _detect_language(prs)
    overflow = tuple(check_pptx_from_prs(prs))
    contrast = tuple(audit_prs(prs))
    categories = set(_categorise_slides(prs, lang))
    body_missing = tuple(
        name for name, satisfied_by in _SECTION_CATEGORIES
        if not (satisfied_by & categories)
    )
    thesis_style = bool(categories & _THESIS_CATEGORIES)
    # A multi-paper deck is the one with a shared "agenda" slide; it always
    # carries a references slide listing the cited papers, so a missing one is a
    # real gap. A single-paper rich deck (no agenda) folds references into the
    # cover, and an own-thesis deck omits self-citation — neither is flagged.
    references_missing = "agenda" in categories and "references" not in categories
    missing = body_missing + (("references",) if references_missing else ())
    return DeckReview(
        str(path), lang, thesis_style, overflow, contrast, missing, references_missing,
    )


def format_report(review: DeckReview) -> str:
    """Human-readable one-deck report for the CLI ``review`` subcommand."""
    lines = [
        f"deck review — {review.path}",
        f"language:      {review.language}"
        + ("" if review.thesis_style else "  (lightweight deck)"),
    ]
    hard = review.hard_contrast
    warn = [i for i in review.contrast if not i.hard]
    lines.append(f"overflow:      {len(review.overflow)}")
    for v in review.overflow:
        lines.append(
            f'  slide {v.slide}, shape "{v.shape}": {v.kind} '
            f"— rendered {v.rendered_in}\" vs {v.limit_in}\""
        )
    lines.append(f"contrast:      {len(hard)} hard, {len(warn)} warning")
    for i in hard:
        lines.append(f'  slide {i.slide}, shape "{i.shape}": {i.kind} — {i.detail}')
    if review.missing_sections:
        lines.append(
            f"completeness:  {len(review.missing_sections)} section(s) missing "
            f"— {', '.join(review.missing_sections)}"
        )
    elif review.thesis_style:
        lines.append("completeness:  all sections present")
    else:
        lines.append("completeness:  not gated (lightweight single-paper deck)")
    lines.append(f"verdict:       {'PASS' if review.ok else 'FAIL'}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    """CLI entry: ``review [--lang XX] [--json] <deck.pptx> [more.pptx ...]``.

    Exit code is the number of decks that FAILED (0 = all clean), so CI / a
    wrapper can assert on it. ``--json`` emits one machine-readable array of
    ``DeckReview.to_dict()`` objects instead of the human report, so a CI step
    can parse the overflow / contrast / missing-section detail.
    """
    language: str | None = None
    as_json = False
    paths: list[str] = []
    i = 0
    while i < len(argv):
        if argv[i] in ("--lang", "--language") and i + 1 < len(argv):
            language = argv[i + 1]
            i += 2
            continue
        if argv[i] == "--json":
            as_json = True
            i += 1
            continue
        paths.append(argv[i])
        i += 1
    if not paths:
        print("usage: review [--lang XX] [--json] <deck.pptx> [more.pptx ...]")
        return 2
    reviews = [review_deck(path, language) for path in paths]
    if as_json:
        print(json.dumps([r.to_dict() for r in reviews], ensure_ascii=False, indent=2))
    else:
        print("\n\n".join(format_report(r) for r in reviews))
    return sum(1 for r in reviews if not r.ok)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
