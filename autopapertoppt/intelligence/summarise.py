"""Summarise a paper's full text into a structured ``PaperSummary``.

Talks to Anthropic's Claude API. The system prompt is marked
``cache_control=ephemeral`` so the model picks it up from the prompt cache
on the second paper onwards — running 20 papers in one session pays the
schema prompt ingestion cost once, not 20 times.

Required: ``ANTHROPIC_API_KEY`` in the environment.
Optional: ``AUTOPAPERTOPPT_LLM_MODEL`` overrides ``DEFAULT_MODEL``.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from autopapertoppt.core.exceptions import ConfigError, ParseError
from autopapertoppt.core.models import Paper, PaperSummary
from autopapertoppt.exporters.i18n import normalise_language
from autopapertoppt.intelligence.pdf import ExtractedPdf
from autopapertoppt.utils.logging import get_logger

_LOG = get_logger(__name__)

DEFAULT_MODEL: str = "claude-opus-4-7"
_API_KEY_ENV: str = "ANTHROPIC_API_KEY"
_MODEL_ENV: str = "AUTOPAPERTOPPT_LLM_MODEL"

_MAX_PDF_CHARS_TO_SEND: int = 80_000
_MAX_OUTPUT_TOKENS: int = 2_000

_LANGUAGE_LABELS: dict[str, str] = {
    "en": "English",
    "zh-tw": "Traditional Chinese (繁體中文)",
    "zh-cn": "Simplified Chinese (简体中文)",
    "ja": "Japanese (日本語)",
}

_BUCKET_ALIASES: dict[str, str] = {
    "motivation": "motivation",
    "background": "motivation",
    "problem": "motivation",
    "contributions": "contributions",
    "contribution": "contributions",
    "key_contributions": "contributions",
    "key contributions": "contributions",
    "method": "method",
    "methods": "method",
    "approach": "method",
    "methodology": "method",
    "results": "results",
    "findings": "results",
    "evaluation": "results",
    "limitations": "limitations",
    "limitation": "limitations",
    "future_work": "limitations",
    "future work": "limitations",
    "takeaways": "takeaways",
    "takeaway": "takeaways",
    "conclusion": "takeaways",
    "conclusions": "takeaways",
    "implications": "takeaways",
}


@dataclass(frozen=True, slots=True)
class AnthropicSummariser:
    """One configured Anthropic client + model. Reusable across papers."""

    model: str = DEFAULT_MODEL
    api_key: str | None = None

    def _client(self):
        try:
            import anthropic  # imported lazily so the extra is truly optional
        except ImportError as err:
            raise ConfigError(
                "anthropic is not installed; "
                "run `pip install autopapertoppt[intelligence]`"
            ) from err
        api_key = self.api_key or os.environ.get(_API_KEY_ENV)
        if not api_key:
            raise ConfigError(
                f"{_API_KEY_ENV} is not set — required for --enrich mode"
            )
        return anthropic.Anthropic(api_key=api_key)

    def summarise(
        self, paper: Paper, pdf_text: str, language: str, raw_text_chars: int
    ) -> PaperSummary:
        canonical_lang = normalise_language(language)
        lang_label = _LANGUAGE_LABELS.get(canonical_lang, "English")
        prompt = _build_user_message(paper, pdf_text, lang_label)
        client = self._client()
        response = client.messages.create(
            model=self.model,
            max_tokens=_MAX_OUTPUT_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )
        text = _first_text_block(response)
        data = _parse_json_blob(text)
        return _data_to_summary(
            data, language=canonical_lang, model=self.model, raw_text_chars=raw_text_chars
        )


def summarise_paper(
    paper: Paper,
    pdf: ExtractedPdf,
    *,
    language: str = "en",
    model: str | None = None,
    api_key: str | None = None,
) -> PaperSummary:
    """Convenience wrapper for one-shot summarisation."""
    summariser = AnthropicSummariser(
        model=model or os.environ.get(_MODEL_ENV) or DEFAULT_MODEL,
        api_key=api_key,
    )
    return summariser.summarise(
        paper=paper,
        pdf_text=pdf.text,
        language=language,
        raw_text_chars=pdf.chars,
    )


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------


_SYSTEM_PROMPT = """\
You read full academic papers and produce a structured summary suitable for a
presentation deck. Output rules:

1. Return ONLY a single JSON object — no preamble, no markdown fences, no trailing prose.
2. The JSON has exactly these keys, every value an array of short bullet-style strings:
     - "motivation"     (why this paper exists; the problem it tackles)
     - "contributions"  (concrete novel claims the paper makes)
     - "method"         (the technical approach / architecture / experimental design)
     - "results"        (key quantitative or qualitative findings)
     - "limitations"    (caveats, threats to validity, future work)
     - "takeaways"      (one-line conclusions a reader should remember)
3. Each bullet is one declarative sentence, ≤ 30 words, with no leading bullet glyph.
4. 2-5 bullets per section. Omit (use empty array) a section the paper genuinely doesn't cover.
5. Be specific. Prefer concrete numbers, method names, dataset names. Avoid filler like
   "the authors propose a novel approach" — name the approach.
6. Cite figures only by phrase ("Figure 3 shows…"); do not invent numbers not in the text.
7. NEVER hallucinate authors, datasets, or results that are not visible in the supplied text.
8. The reader's preferred language is given in the user message. Write every bullet in that
   language. Keep proper nouns (model names, dataset names, acronyms) in their original form.
"""


def _build_user_message(paper: Paper, pdf_text: str, lang_label: str) -> str:
    truncated = pdf_text[:_MAX_PDF_CHARS_TO_SEND]
    header_bits = [
        f"TITLE: {paper.title}",
        f"AUTHORS: {', '.join(paper.authors) if paper.authors else 'unknown'}",
        f"YEAR: {paper.year or 'unknown'}",
        f"VENUE: {paper.venue or 'unknown'}",
        f"DOI: {paper.doi or 'unknown'}",
        f"OUTPUT LANGUAGE: {lang_label}",
    ]
    header = "\n".join(header_bits)
    return (
        f"{header}\n\n"
        f"=== FULL PAPER TEXT (truncated to {_MAX_PDF_CHARS_TO_SEND} chars) ===\n"
        f"{truncated}\n"
        f"=== END PAPER TEXT ===\n\n"
        f"Produce the structured JSON summary as described in the system instructions. "
        f"Output language: {lang_label}."
    )


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _first_text_block(response) -> str:
    for block in response.content:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text:
            return text
    raise ParseError("intelligence", "Anthropic response had no text block")


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.S)


def _parse_json_blob(text: str) -> dict:
    """Tolerate (1) clean JSON, (2) JSON inside markdown fences, (3) leading prose."""
    candidate = text.strip()
    if candidate.startswith("```"):
        # strip first fence line and any trailing fence
        candidate = re.sub(r"^```[a-zA-Z]*\n", "", candidate)
        candidate = candidate.rstrip("`").rstrip()
        if candidate.endswith("```"):
            candidate = candidate[:-3].rstrip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    match = _JSON_BLOCK_RE.search(text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as err:
            raise ParseError("intelligence", f"LLM response is not JSON: {err}") from err
    raise ParseError("intelligence", "LLM response contained no JSON object")


def _data_to_summary(
    data: dict, *, language: str, model: str, raw_text_chars: int
) -> PaperSummary:
    buckets: dict[str, list[str]] = {
        "motivation": [],
        "contributions": [],
        "method": [],
        "results": [],
        "limitations": [],
        "takeaways": [],
    }
    for key, value in data.items():
        canonical = _BUCKET_ALIASES.get(key.lower().strip())
        if canonical is None:
            continue
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, str) and item.strip():
                buckets[canonical].append(item.strip())
    return PaperSummary(
        language=language,
        motivation=tuple(buckets["motivation"]),
        contributions=tuple(buckets["contributions"]),
        method=tuple(buckets["method"]),
        results=tuple(buckets["results"]),
        limitations=tuple(buckets["limitations"]),
        takeaways=tuple(buckets["takeaways"]),
        raw_text_chars=raw_text_chars,
        model=model,
    )
