# PPTX editing & layout

ThesisAgents's slide-deck exporter writes a **16:9 widescreen** deck
sized at 13.33" × 7.5". Three rendering tiers pick themselves based on
what's attached to each `Paper`:

| Tier | When | Slides per paper |
|---|---|---|
| **Lightweight** | Only `paper.abstract` is available (default for arXiv search results without `--enrich`). | cover + agenda + (divider + overview + Background / Approach / Findings sentence buckets) + references |
| **Enriched-flat** | `Paper.summary` has the flat tier populated (`motivation` / `contributions` / `method` / `results` / `limitations` / `takeaways`). | cover + agenda + (divider + overview + one slide per non-empty flat section) + references |
| **Thesis-style** | `Paper.summary.has_rich_fields()` (pain_points / research_question / headline_metrics / technique_table / literature_table / system_flow / method_sections / evaluation_sections / research_questions / rq_results / core_observation / future_work). | cover + overview + pain-points quadrant + contributions stacks + headline-metrics KPI + technique table + literature table + system overview + method details (2 per slide) + evaluation method (2 per slide) + research questions + per-RQ result tables + contribution summary + core observation + limitations & future work + Q&A + references |

Every slide carries a **page number** "N / total" in the bottom-right
corner except the cover.

## Shape naming convention

| Shape name | Used on | Contents |
|---|---|---|
| `title` | every slide except cover | Section heading at the top. |
| `subtitle` | cover (single-paper deck) | English / original-language paper title under the localised title. |
| `meta` | cover, paper overview, content slides | Authors / year / venue / source URL or "Paper N of M" counter. |
| `paper_subtitle` | thesis-style slides | Small grey "paper title · source" line under the rule. |
| `subhead` | multi-column cells, stacked sections, method sub-sections | Bold sub-heading. |
| `body` | most slides | Bullet list or paragraph text. |
| `kpi_label`, `kpi` | contributions / KPI slide | "Headline Metrics" label + KPI lines. |
| `rq_box` | research-question highlight, core-observation callout | Filled rounded rectangle with bold text. |
| `footer` | non-cover slides | Source · BibTeX key, etc. |
| `page_number` | every slide except cover | "N / total". |

Decks produced by other tools may not follow this convention — the
edit helpers fall back to **integer indexes** into the slide's
text-bearing shapes (`shape_updates={0: "..."}`).

## i18n

All template strings (Agenda / Background / References / Paper N of M /
footer copy / "n.d." for missing dates / etc.) flow through
`thesisagents.exporters.i18n`. Supported languages: `en`, `zh-tw`,
`zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`,
`id` (14 in total). Set on the deck via `ExportOptions.language` (CLI
`--lang`, MCP `export(language=...)`).

The `test_every_language_has_every_key` test enforces that every
language has every key present in the default English table — add a
new language by adding one new dict in `i18n._TABLE` and the test will
flag missing entries.

## Layout rules the exporter enforces

These prevent overflow on real decks. Document them so callers don't
need to fight the renderer:

1. **Title height = 1.0".** Section titles are 30pt; a wrapped 2-line
   title fits the box. Section titles auto-truncate to
   `_SLIDE_TITLE_TRUNCATE = 60` chars; the overview slide uses the
   same cap on the paper title.
2. **Horizontal rule sits at 1.35".** Body content starts at
   `_BODY_TOP = 1.5"`. Never push a body shape above this line.
3. **Footer guard at 7.05".** No shape may render past it. KPI blocks
   and core-observation callouts ALWAYS get their own slide so the
   "stacks + tail" sum can't exceed the body area.
4. **Multi-column cells** (pain-points quadrant, evaluation method)
   use `_BULLET_MAX_CHARS_COL = 28` chars per bullet — narrower than
   the full-width `_BULLET_MAX_CHARS = 60` — so 6"-wide cells don't
   wrap to 3+ lines.
5. **Per-slide content caps**: `_MAX_STACKS_PER_SLIDE = 5`,
   `_METHOD_SECTIONS_PER_SLIDE = 2`,
   `_EVALUATION_SECTIONS_PER_SLIDE = 2`. Excess sections split onto
   labelled continuation slides (`方法細節 (1/2)` etc.).
6. **Long bullet lists** show only the first 3-6 (depending on
   context) and append a trailing `…(+N)` bullet for the rest.

## Python API

```python
from thesisagents.exporters import pptx_edit

# Inspect a deck (any deck — yours, ours, anyone's).
slides = pptx_edit.inspect("exports/attention.pptx")
for slide in slides:
    print(slide.index, slide.title)
    for shape in slide.shapes:
        print(" ", shape.index, shape.name, shape.text[:60])

# Update by shape name (works on ThesisAgents decks).
pptx_edit.update_slide(
    "exports/attention.pptx", slide_index=2,
    title="Custom title", body="Custom body bullet text",
)

# Update by shape index (fallback for foreign decks).
pptx_edit.update_slide(
    "exports/foreign.pptx", slide_index=0,
    shape_updates={0: "Custom title", 1: "Custom body"},
)

# Reorder, delete, add.
pptx_edit.reorder_slides("exports/attention.pptx", [0, 2, 1, 3, 4])
pptx_edit.delete_slide("exports/attention.pptx", slide_index=3)
pptx_edit.add_slide(
    "exports/attention.pptx",
    title="Discussion", meta="My follow-up notes",
    body="Point 1\nPoint 2", position=None,   # None = append
)
```

By default every helper saves in place. Pass `out_path="copy.pptx"` to
write a separate file and leave the original untouched.

## MCP equivalents

Same operations are exposed as MCP tools (see [mcp.md](mcp.md)):
`pptx_inspect`, `pptx_update_slide`, `pptx_delete_slide`,
`pptx_reorder_slides`, `pptx_add_slide`. These let an LLM agent iterate
on a deck after generation without going back to Python.

## How slide deletion / reordering works

`python-pptx` doesn't expose slide deletion or reordering as public
API, so the helpers manipulate the `sldIdLst` XML directly:

- **Delete**: remove the `<p:sldId>` element from `sldIdLst` and call
  `presentation.part.drop_rel(rid)` so the orphaned relationship
  doesn't corrupt the file when re-opened.
- **Reorder**: read every child of `sldIdLst`, build the new order,
  detach them all, then re-append in the new order. Validates that
  `new_order` is a true permutation of `[0..slide_count-1]`.

Both operations are tested end-to-end in `tests/test_pptx_edit.py` —
write a deck with the exporter, mutate it, and re-open with
`python-pptx` to assert the change persisted.

## Avoiding overflow when adding rich content

If you're building a `PaperSummary` by hand (the LLM-as-agent flow),
keep these caps in mind:

| Field | Max items before split / truncate | Per-item char budget |
|---|---|---|
| `pain_points` | 4 entries (2×2 quadrant) | bullets ≤ 28 chars (`_BULLET_MAX_CHARS_COL`) |
| `contributions_detailed` | 5 stacks; otherwise truncated | body ≤ ~90 chars per stack |
| `headline_metrics` | 6 metrics (own slide) | label + value short enough to fit one line |
| `technique_table` | ~10 rows comfortably | ~50 chars per cell |
| `literature_table` | 6-7 rows × 5 cols | ~20 chars per cell |
| `method_sections` | 2 per slide (auto-splits) | sub-section ≤ 4 bullets, each ≤ 60 chars |
| `evaluation_sections` | 2 per slide (auto-splits) | same as above |
| `rq_results.table` | ~6 rows | ~25 chars per cell |
| `rq_results.analysis` | 3 bullets after the table | ≤ 60 chars per bullet |
| `core_observation` | 1 callout box | ≤ ~120 chars (wraps to 2 lines) |

Anything beyond these caps gets truncated with `…` or appended as
`…(+N)` bullets. The renderer never silently overflows.
