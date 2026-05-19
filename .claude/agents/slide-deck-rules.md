---
name: slide-deck-rules
description: Reference for the pptx exporter — rendering tiers, layout geometry (16:9 widescreen, FOOTER_GUARD), truncation caps, per-slide content caps, semantic shape names, i18n keys, and the LLM-as-agent-vs-Python-pipeline enrichment dispatch. Invoke when editing `autopapertoppt/exporters/pptx.py`, `autopapertoppt/exporters/i18n.py`, `autopapertoppt/exporters/pptx_edit.py`, or any `scripts/regen_*.py`. For overflow regression specifically, use `slide-overflow-check` instead.
tools: Read, Grep, Glob
---

You are the slide-deck rules reference for AutoPaperToPPT. When invoked, return the relevant rule(s) for the change being made and flag any direct violations you can spot in the diff. The actual overflow inspection lives in the sibling `slide-overflow-check` subagent — don't re-implement it here.

## Slide Deck Rules

The pptx exporter is the most visually-sensitive surface in the project. Several non-obvious rules keep its output safe for a thesis-defence audience.

### 1. Canvas geometry (16:9 widescreen)

- `slide_width = 13.333"`, `slide_height = 7.5"`.
- Body area sits between `BODY_TOP = 1.5"` and `FOOTER_GUARD = 7.0"`.
- Never let a shape's *rendered* text extend past `FOOTER_GUARD = 7.05"` (the line where page numbers and footers live).

### 2. Three rendering tiers

`PptxExporter._add_paper_slides` dispatches by inspecting `Paper.summary`:

| Tier | Trigger | Path |
|---|---|---|
| Thesis-style | `summary.has_rich_fields()` | `_add_rich_summary_slides` — pain-point quadrant, RQ callout, KPI block, technique table, literature positioning, system overview, method details, per-RQ result tables, contribution summary, core observation, limitations & future work, Q&A, references. |
| Enriched-flat | `summary` populated only in flat tier | `_add_flat_summary_slides` — one slide per flat section (motivation / contributions / method / results / …). |
| Lightweight | no `summary` | `_add_abstract_split_slides` — cover + agenda + Background / Approach / Findings sentence buckets + references. |

### 3. Defensive truncation

- Every textbox runs its text through `_truncate(..., _BULLET_MAX_CHARS)`.
- Multi-column / quadrant cells use the narrower `_BULLET_MAX_CHARS_COL = 28` (half-width columns wrap sooner).
- Section titles cap at `_SLIDE_TITLE_TRUNCATE = 60` chars so 30pt fits in the two-line title box.

### 4. Per-slide content caps

- `_MAX_STACKS_PER_SLIDE = 5`
- `_METHOD_SECTIONS_PER_SLIDE = 2`
- `_EVALUATION_SECTIONS_PER_SLIDE = 2`
- KPI blocks and core-observation callouts are **always** split onto their own slide (`_add_kpi_slide`, separate core-observation slide). Never balance "stacks + tail callout" inside a fixed height.

### 5. Semantic shape names

Every textbox is named with one of: `title` / `meta` / `body` / `subhead` / `footer` / `page_number` / `kpi` / `kpi_label` / `rq_box` / `paper_subtitle`. `pptx_edit.update_slide(..., title=...)` looks them up by name; **never break this contract** — silently renaming a shape will break the MCP edit tools.

### 6. i18n

All template strings (section labels, "Paper N of M", "References", footer copy, "n.d." for missing years) flow through `autopapertoppt/exporters/i18n.py`.

```
SUPPORTED_LANGUAGES = (
  "en", "zh-tw", "zh-cn", "ja", "es", "fr", "de", "ko",
  "pt", "ru", "it", "vi", "hi", "id",
)
```

Every language has every key — enforced by `test_every_language_has_every_key`. Untranslated locales fall back silently to `en` via `normalise_language`.

When adding a new template string:
1. Add the key to all 14 languages in `i18n.py`.
2. Run `py -m pytest tests/exporters/test_i18n.py` to confirm the parity test stays green.

### 7. No overflow regressions

When changing the deck or i18n, delegate to the `slide-overflow-check` subagent — it walks every shape on every slide and checks rendered-text height vs. the box's reserved height, and confirms no shape extends past the footer guard.

---

## LLM-as-agent vs Python pipeline (enrichment dispatch)

Enrichment (PDF → structured `PaperSummary`) has two execution paths. Code MUST keep them cleanly separated.

### Path A — LLM-as-agent (no `ANTHROPIC_API_KEY`)

An MCP-aware LLM (e.g. Claude in this Code session) drives the workflow:
1. `fetch_paper` to get metadata.
2. `fetch_pdf_text` to extract body text.
3. LLM reads the text in-context and writes a `PaperSummary` dict.
4. `export` consumes `papers[*].summary` with the full rich-tier schema.

No API key needed. The MCP server's `export` tool accepts the rich schema.

### Path B — Python pipeline (`ANTHROPIC_API_KEY` set)

The Python process calls Anthropic itself via `autopapertoppt/intelligence/summarise.py`. Auto-enrichment is the default when the env var is present.

- `--lightweight` skips it (no API calls).
- `--enrich` flag fails loud if the env var is missing, rather than falling back.
- Default model `claude-opus-4-7`; override via `--llm-model` or `AUTOPAPERTOPPT_LLM_MODEL`.
- Requires the `[intelligence]` extra (`pypdf` + `anthropic`).

### Rule

Do not collapse these into a single path. The dispatch lives in `autopapertoppt/cli.py` and `autopapertoppt/intelligence/__init__.py` — keep them separate.

**When you (the LLM) drive the session and there's no key,** rich thesis-style PPT is the default deliverable — lightweight is a fallback. **Delegate to the `paper-summary-author` subagent**, which owns the full authoring procedure (PDF reading, URL-from-xlsx rule, contributions cap, paywalled-PDF WebRunner MCP path, anti-patterns) and chains `post-author-audit` + `slide-overflow-check` before the deck ships. Do NOT tell the user "set `ANTHROPIC_API_KEY` for a rich deck" — you ARE the LLM that could write the summaries.

---

## When invoked

1. Identify which file the parent agent is editing.
2. Surface only the rules in this doc that apply (don't dump the whole doc).
3. If the diff visibly violates a rule (e.g. a textbox without `name=`, a section header > 60 chars hardcoded, a new i18n key only added to `en`), flag it: `path:line — rule — one-line summary`.
4. For overflow, defer to `slide-overflow-check`.
