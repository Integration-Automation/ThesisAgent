---
name: slide-deck-rules
description: Reference for the pptx exporter — rendering tiers, layout geometry (16:9 widescreen, FOOTER_GUARD), truncation caps, per-slide content caps, semantic shape names, i18n keys, and the LLM-as-agent-vs-Python-pipeline enrichment dispatch. Invoke when editing `thesisagents/exporters/pptx.py`, `thesisagents/exporters/i18n.py`, `thesisagents/exporters/pptx_edit.py`, or any `scripts/regen_*.py`. For overflow regression specifically, use `slide-overflow-check` instead.
tools: Read, Grep, Glob
---

You are the slide-deck rules reference for ThesisAgents. When invoked, return the relevant rule(s) for the change being made and flag any direct violations you can spot in the diff. The actual overflow inspection lives in the sibling `slide-overflow-check` subagent — don't re-implement it here.

**Scope split** — this agent owns *geometry* and *content safety*
(slide dimensions, footer guard, truncation caps, per-slide content
caps, semantic shape names, i18n keys, rendering-tier dispatch). The
sibling `deck-design` subagent owns *visual identity* (typography per
language, brand palette, accent geometry, "looks AI-generated"
anti-patterns). Both apply to any change to
`thesisagents/exporters/pptx.py` — consult the appropriate one for
the concern at hand.

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

All template strings (section labels, "Paper N of M", "References", footer copy, "n.d." for missing years) flow through `thesisagents/exporters/i18n.py`.

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

### 8. Content clarity & first-use context (HARD)

**Every acronym, specialised term, math notation, and library / tool name that appears on a slide MUST carry its definition at first use** — same principle as `paper_rule`'s technical-terminology rule, but the slide context tightens it further. Slide decks are read at presentation speed (~30 seconds per slide), often by a thesis-committee member who arrived in the middle of the talk, and that reader has no time to flip back to find where `ADA` was defined four slides ago. The rule applies to:

- **Acronyms** — `ADA`, `HOR`, `FPR`, `IL`, `EC`, `AT`, `VAE`, `DPI`, `AID`, `RAG`, `CoT`, `KD`, `PEFT`, `QLoRA`, `STA`, …
- **Library / tool names** — `FAISS`, `Qwen3-Coder-30B`, `PyTorch Geometric`, `BLEU`, `ROUGE`, …
- **Math notation** — `I(za;zb|Ep)`, `‖·‖_2`, `argmin`, `λ_max`, eigenvector / Laplacian terms
- **Workflow / domain terms** — `Pull Request`, `code smell`, `Post-output moderation`, `Embedding Clustering`, `對抗訓練`, …

**Two patterns — pick the one the slide layout supports:**

1. **Inline parenthetical gloss** (preferred — no extra slides, fits any layout):
   ```
   規則式 ADA(對抗偵測準確率, Adversarial Detection Accuracy)在多樣 benchmark 上掉到 65.4%
   VAE(變分自編碼器, Variational Autoencoder)編碼器把 prompt 切成對抗 za 與良性 zb
   互資訊 I(za;zb|Ep) — 論文以 DPI(Data Processing Inequality)給出形式化證明
   ```
   Gloss = full Chinese name + (optional) English expansion + (when needed) one short clause on *what it does*. Keep it to ≤ 20 chars when possible.

2. **Definition-list block** (use when slide is dedicated to "evaluation metrics" or "method components" — i.e. the slide is already an inventory):
   ```
   • 對抗偵測準確率 (ADA): 偵測到的對抗 prompt / 全部對抗 prompt
   • 有害輸出減量    (HOR): 1 − (含有害輸出的回答數 / 對照組)
   • 偽陽性率        (FPR): 被誤判為對抗的良性 prompt 比例
   ```

**Anti-patterns** (instant "I wrote this for my own lab" tells):

1. **Acronym soup at first use** — `規則式 ADA 在多樣 benchmark 上掉到 65.4%` with no prior definition. The audience hears "65.4%" but doesn't know what's being measured.
2. **Definition appearing AFTER first use** — `ADA` on slide 3, definition on slide 9. The opposite of "脈絡清楚" — by the time the reader sees the definition, they've already disengaged.
3. **Math notation dropped without naming the operator** — `min I(za;zb|Ep)` instead of `min 互資訊 I(za;zb|Ep)`. The audience reads `I(·;·|·)` as "some math symbol" rather than "this is mutual information between two variables conditioned on a third".
4. **Library / model name without provenance** — `FAISS 依語意檢索` instead of `FAISS(Facebook AI 釋出之向量索引庫,支援高速近似最近鄰搜尋)依語意檢索`. The audience has to Google to know whether FAISS is a model, library, or dataset.
5. **Separate "Glossary" / "縮寫表" slide** — bloats the deck and breaks reading flow, and readers don't flip back anyway. Inline glosses at first use are the right pattern. (Exception: a metric-definitions slide is fine because it's content, not a glossary.)

**Builder responsibility:** when authoring a new section / RQ / pain-point / contribution slide in `PptxExporter` or via the LLM-as-agent flow (`paper-summary-author`), check every term the slide introduces against the slide deck so far. If this is the term's first appearance, the gloss must be on this slide. The audit is mechanical — grep the slide-by-slide text dump for acronyms in caps + standalone math notation + 英文 library names.

**Interaction with content caps:** glosses cost chars and may push a bullet over `_BULLET_MAX_CHARS = 96`. When they do, the priority order from `paper_rule`'s tech-term rule applies: keep the gloss, trim adjacent filler, never drop the gloss.

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

The Python process calls Anthropic itself via `thesisagents/intelligence/summarise.py`. Auto-enrichment is the default when the env var is present.

- `--lightweight` skips it (no API calls).
- `--enrich` flag fails loud if the env var is missing, rather than falling back.
- Default model `claude-opus-4-7`; override via `--llm-model` or `THESISAGENTS_LLM_MODEL`.
- Requires the `[intelligence]` extra (`pypdf` + `anthropic`).

### Rule

Do not collapse these into a single path. The dispatch lives in `thesisagents/cli.py` and `thesisagents/intelligence/__init__.py` — keep them separate.

**When you (the LLM) drive the session and there's no key,** rich thesis-style PPT is the default deliverable — lightweight is a fallback. **Delegate to the `paper-summary-author` subagent**, which owns the full authoring procedure (PDF reading, URL-from-xlsx rule, contributions cap, paywalled-PDF WebRunner MCP path, anti-patterns) and chains `post-author-audit` + `slide-overflow-check` before the deck ships. Do NOT tell the user "set `ANTHROPIC_API_KEY` for a rich deck" — you ARE the LLM that could write the summaries.

---

## When invoked

1. Identify which file the parent agent is editing.
2. Surface only the rules in this doc that apply (don't dump the whole doc).
3. If the diff visibly violates a rule (e.g. a textbox without `name=`, a section header > 60 chars hardcoded, a new i18n key only added to `en`), flag it: `path:line — rule — one-line summary`.
4. For overflow, defer to `slide-overflow-check`.
