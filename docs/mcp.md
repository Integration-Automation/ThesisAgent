# MCP server

ThesisAgents ships a [Model Context Protocol](https://modelcontextprotocol.io/)
server so any MCP-aware LLM agent can run the same search / export /
pptx-edit operations as the CLI. The server is headless and runs over
stdio.

## Two enrichment paths

There are two ways to produce a thesis-style enriched deck:

**A) LLM-as-agent (no API key)** — preferred when an MCP-aware LLM is
already driving the workflow:

1. *(Optional)* `list_sources()` to see which plugins are enabled in
   the current process. Disabled plugins are silently skipped, so
   this prevents the agent from passing a source that won't actually
   run.
2. *Either* `search(keywords, sources, top_tier_only, ...)` for a
   multi-paper query, *or* `fetch_paper(identifier)` for a single
   paper by ID / URL / DOI / PMID.
3. *(Optional)* `download_pdfs(papers, out_dir)` to persist every
   paper's PDF on disk in one batch — useful when the agent plans to
   re-read or embed figures later.
4. `fetch_pdf_text(paper.pdf_url)` per paper to extract body text.
5. *The LLM reads the body text and produces a structured `summary` dict
   in-context* (with `pain_points`, `research_question`,
   `headline_metrics`, `technique_table`, `literature_table`,
   `method_sections`, `research_questions`, `rq_results`, …).
6. `export(papers=[{..., "summary": {...}}], language="zh-tw", ...)`.

No `ANTHROPIC_API_KEY` is needed because the LLM is the agent itself.

**B) Python pipeline (`--enrich` CLI flag)** — for non-agent automation
where there is no calling LLM. The CLI calls Anthropic's API with the PDF
text and writes the structured summary itself; this path requires
`ANTHROPIC_API_KEY` and the `[intelligence]` extra to be installed.

## Install

The server lives in `thesisagents.mcp.server`. The `mcp` SDK is the
only extra dependency:

```bash
pip install -e .[mcp]    # only the SDK
pip install -e .[dev]    # SDK + test deps (recommended)
```

That installs an `thesisagents-mcp` console script. `python -m
thesisagents.mcp` works too.

## Configure your MCP client

Add via Claude Code's CLI:

```powershell
claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp
```

Or hand-edit `~/.claude.json` (or project-local `.claude/settings.json`):

```json
{
  "mcpServers": {
    "thesisagents": {
      "command": ".venv\\Scripts\\python.exe",
      "args": ["-m", "thesisagents.mcp"]
    }
  }
}
```

If you'd rather rely on the installed console script, point at the
venv-resolved binary directly:

```json
{
  "mcpServers": {
    "thesisagents": {
      "command": ".venv\\Scripts\\thesisagents-mcp.exe"
    }
  }
}
```

(Linux / macOS: `.venv/bin/thesisagents-mcp`.)

## Tools

The server exposes twelve tools, grouped into five concerns.

### `list_sources`

Report every source plugin the server can load, whether it is in the
default mix, and whether the env vars required to enable it are set.
Call this once before `search` so the agent only passes enabled plugins
— disabled plugins are silently skipped by the pipeline but the agent
has no other way to know about them.

```json
{}
```

Returns:

```json
{
  "default_sources": ["arxiv", "semantic_scholar", "openalex", "pubmed",
                     "acm", "dblp", "crossref", "openaire"],
  "sources": [
    {"name": "arxiv",            "in_default_mix": true,  "needs_env_var": [],
     "enabled": true},
    {"name": "springer",         "in_default_mix": true,  "enabled": false,
     "needs_env_var": ["THESISAGENTS_SPRINGER_API_KEY"]},
    {"name": "ieee",             "in_default_mix": true,  "enabled": true,
     "opt_out_env_var": "THESISAGENTS_DISABLE_IEEE_SCRAPING",
     "needs_env_var":   ["THESISAGENTS_IEEE_API_KEY"]},
    {"name": "scholar",          "in_default_mix": true,  "enabled": true,
     "opt_out_env_var": "THESISAGENTS_DISABLE_SCHOLAR_SCRAPING"}
  ]
}
```

The full plugin set is `arxiv`, `semantic_scholar`, `openalex`, `pubmed`,
`acm`, `dblp`, `crossref`, `openaire`, `europepmc`, `doaj`, `hal`, `ieee`,
`springer`, `core`, `scholar` (15). `core` is opt-in via
`THESISAGENTS_CORE_API_KEY`, like `springer`.

### `list_exports`

Discovery tool symmetric to `list_sources`: report every export format the
`export` tool accepts, each with a one-line description and an `aggregate`
flag. Call it once before `export` so the agent passes only recognised
formats.

```json
{}
```

Returns (abridged):

```json
{
  "formats": [
    {"format": "pptx", "description": "Thesis-style PowerPoint deck ...", "aggregate": false},
    {"format": "ris",  "description": "RIS interchange for Zotero / Mendeley / EndNote / RefWorks.", "aggregate": true},
    {"format": "csv",  "description": "Flat one-row-per-paper CSV ...", "aggregate": true},
    {"format": "csl",  "description": "CSL-JSON for Pandoc / citeproc ...", "aggregate": true}
  ]
}
```

`aggregate: true` writes one file for the whole run (`xlsx`, `md`, `bib`,
`json`, `ris`, `csv`, `csl`); `pptx` and `pdf` are emitted per paper.

### `search`

Run a keyword search across one or more sources. Returns a JSON
payload whose `papers` list is in the same shape as `Paper.to_dict()`
— pass it straight to `export`.

When `sources` is omitted, the search runs against the full default
mix (every plugin that needs no API key). `exclude_sources` is
subtracted **after** `sources` resolves — the no-VPN gesture is to omit
`sources` and pass `exclude_sources: ["ieee"]`, keeping every other
default source. `top_tier_only` (default `true`) keeps only papers whose
venue matches the curated whitelist (flagship CS conferences + Nature /
Science / PNAS / CACM / LNCS); pass `false` for a broader net. arXiv
preprints always pass through.

```json
{
  "keywords": "attention is all you need",
  "sources": ["arxiv", "openalex", "crossref"],
  "exclude_sources": ["ieee"],
  "max_results": 10,
  "year_from": 2017,
  "year_to": null,
  "top_tier_only": true,
  "min_citations": 50
}
```

Returns:

```json
{
  "query": {"keywords": "attention is all you need", "sources": ["arxiv"], "max_results": 10, "year_from": 2017, "year_to": null},
  "count": 10,
  "papers": [{"source": "arxiv", "source_id": "1706.03762v5", "title": "Attention Is All You Need", "...": "..."}]
}
```

### `fetch_paper`

Fetch exactly one paper by identifier. Accepts the same forms as the
CLI's `--paper` flag — arXiv ID / URL, DOI, PMID, IEEE document URL.

```json
{"identifier": "https://arxiv.org/abs/1706.03762"}
```

Returns:

```json
{
  "paper": {"title": "Attention Is All You Need", "...": "..."},
  "identifier": {"kind": "arxiv", "value": "1706.03762"}
}
```

### `fetch_pdf_text`

Download a paper's PDF over HTTPS-only and extract its body text. This
is the MCP entry point for the **LLM-as-agent enrichment flow** — the
calling LLM reads the body text in its own context and produces the
structured `summary` itself, no API key required.

```json
{"pdf_url": "https://arxiv.org/pdf/1706.03762", "source": "arxiv"}
```

Returns:

```json
{
  "url": "https://arxiv.org/pdf/1706.03762",
  "page_count": 12,
  "chars": 47200,
  "text": "Attention Is All You Need\n\nAshish Vaswani ..."
}
```

Hard caps: 20 MB downloaded, first 60 pages, first 80,000 characters
of extracted text. The extraction is local (`pypdf`); the LLM consumes
the returned text.

### `download_pdfs`

Batch-download the PDFs for a list of papers into `{out_dir}/pdfs/`.
Each result is keyed by the paper's BibTeX key so an agent can match
results back to the input list. Use this between `search` and
`fetch_pdf_text` when you need the PDFs persisted on disk (e.g. for
later re-reading or for embedding into the rich PPT via figure
extraction).

```json
{
  "papers": [
    {"source": "arxiv", "source_id": "1706.03762v5", "...": "...",
     "pdf_url": "https://arxiv.org/pdf/1706.03762"}
  ],
  "out_dir": "./exports/attention/"
}
```

Returns:

```json
{
  "out_dir": "./exports/attention/",
  "saved": 1,
  "skipped": 0,
  "results": [
    {"paper_key": "vaswani2017attention",
     "path": "./exports/attention/pdfs/vaswani2017attention.pdf",
     "reason": null}
  ]
}
```

Papers without a `pdf_url` come back with `reason: "no_pdf_url"`;
HTTP 403 / non-PDF content-type / oversize bodies come back with the
matching reason string.

### `export`

Render a papers list to any combination of `.pptx`, `.xlsx`, `.md`,
`.bib`, `.json`, `.ris`, `.csv`, `.csl.json` files. Call `list_exports`
for the format catalogue.

```json
{
  "papers": [
    {"source": "arxiv", "source_id": "1706.03762v5",
     "title": "Attention Is All You Need", "...": "...",
     "summary": {
        "language": "zh-tw",
        "pain_points": [["...", ["...", "..."]]],
        "research_question": "...",
        "contributions_detailed": [["...", "..."]],
        "headline_metrics": [["BLEU on En→De", "28.4", "baseline 25.16"]],
        "rq_results": [{"rq_id": "RQ1", "question": "...",
                        "table": [["metric", "ours"], ["a", "1.0"]],
                        "analysis": ["..."]}],
        "limitations": ["..."],
        "future_work": ["..."]
     }}
  ],
  "keywords": "attention",
  "formats": ["pptx", "xlsx", "bib"],
  "out_dir": "./exports",
  "filename_stem": "attention",
  "include_abstract": true,
  "language": "zh-tw",
  "max_slides_per_paper": 25,
  "dark_mode": true
}
```

`max_slides_per_paper` (default 25) caps the per-paper slide count
after the priority-based trim — cover / references / contributions are
kept first; Q&A / figure / paper-table slides drop first. Pass `0`
(or omit the field) for unlimited.

`dark_mode` (default `true`) toggles the post-build recolour pass.
On: dark slide background (`#12151B`) + near-white body text (`#E5E7EB`)
+ darker table-row stripe — designed for OLED projectors and low-light
venues. Off: the light/printable variant (white background + navy text
`#1F3A66`). Both modes share the same builder pipeline — the dark pass
runs over the rendered tree, so the agent doesn't pick layouts up-front.
The teal accent (`#0E7490` → `#2DD4BF` in dark) marks KPI values and RQ
question callouts; red is banned for text in both modes.

Returns:

```json
{
  "written": {
    "pptx": "/abs/path/exports/attention.pptx",
    "xlsx": "/abs/path/exports/attention.xlsx",
    "bib":  "/abs/path/exports/attention.bib"
  },
  "pptx_path": "/abs/path/exports/attention.pptx"
}
```

The `pptx_path` field is a convenience so an agent can pipe the
result straight into the `pptx_*` editing tools.

**`papers[*].summary`**: when populated with any rich-tier field, the
PPT exporter switches to thesis-style layout (pain-point quadrants,
KPI block, technique table, per-RQ result tables, contribution
summary, core observation callout, limitations & future work, Q&A).
When only the flat fields are set, the deck has one slide per
non-empty section. When `summary` is absent, the deck uses
sentence-bucketing on `paper.abstract`.

**`language`**: one of 14 locales — `en`, `zh-tw`, `zh-cn`, `ja`, `es`,
`fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. Drives both the
template strings (Agenda / References / "Paper N of M" / footer) and
the suggested LLM output language when the agent fills in the summary.
Anything outside that set falls back to `en` silently. Each locale
also drives the per-language typography pass (Inter for Latin, plus
Microsoft JhengHei UI for zh-tw / YaHei UI for zh-cn / Yu Gothic UI
for ja / Malgun Gothic for ko / Nirmala UI for hi) — replaces the
PowerPoint Calibri default, which is the biggest "AI-generated" tell.

### `pptx_inspect`

Read the structure of an existing `.pptx`.

```json
{"path": "./exports/attention.pptx"}
```

Returns the slide count and, for each slide, every text-bearing
shape's index, name, and text:

```text
{
  "path": "./exports/attention.pptx",
  "slide_count": 3,
  "slides": [
    {"index": 0, "title": "Paper search: attention",
     "shapes": [{"index": 0, "name": "title", "text": "Paper search: attention"},
                {"index": 1, "name": "body",  "text": "Sources: arxiv\n..."}]},
    {"index": 1, "title": "1/2  Attention Is All You Need", "shapes": [...]}
  ]
}
```

Shape names are set by `PptxExporter`: each slide carries `title`,
`meta`, and (when an abstract was included) `body` shapes. Decks built
elsewhere may not have these names — fall back to `shape_updates`
addressed by integer index.

### `pptx_review`

Audit an existing deck against all three deck-quality contracts in one
call: slide **overflow**, the dark-mode / no-red / contrast **colour**
contracts, and `paper_rule` **section completeness**.

```json
{"path": "./exports/attention.pptx"}
```

`language` is optional — it is auto-detected from the slide titles when
omitted (pass e.g. `"zh-tw"` to force it). Returns:

```text
{
  "path": "./exports/attention.pptx",
  "language": "zh-tw",
  "thesis_style": true,
  "ok": true,
  "overflow": [],                 // {slide, shape, kind, rendered_in, limit_in}
  "contrast": [],                 // {slide, shape, kind, detail, hard}
  "missing_sections": [],         // canonical body sections with no covering slide
  "completeness_gated": true      // missing_sections only fail a thesis-style deck
}
```

`ok` is `false` when there is any overflow, any *hard* contrast issue
(invisible / red / light-on-light text), or — for a thesis-style deck —
any missing body section (Introduction, Literature Review, Methodology,
Experiment, Conclusion). A lightweight abstract-only deck is never failed
for lacking sections (`thesis_style` / `completeness_gated` say which).
The same audit is available on the command line as
`python -m thesisagents review <deck.pptx> [more.pptx ...] [--lang xx]`.

### `pptx_update_slide`

Replace text on one slide.

```json
{
  "path": "./exports/attention.pptx",
  "slide_index": 1,
  "title": "New title",
  "body": "Replaced abstract.",
  "meta": "Vaswani et al.\n2017 · NeurIPS",
  "shape_updates": {"4": "extra-shape text"},
  "out_path": null
}
```

`title` / `body` / `meta` look the shape up by name. `shape_updates`
is an integer-keyed map for any shape addressable by its zero-based
index among the slide's text-bearing shapes. `out_path` writes a copy
instead of updating in place.

### `pptx_delete_slide`

Remove a slide and its part relationship.

```json
{"path": "./exports/attention.pptx", "slide_index": 0}
```

### `pptx_reorder_slides`

Permute the slide list. `new_order[i]` is the *old* index that should
now occupy position `i`. The list must be a true permutation of
`[0..slide_count-1]`.

```json
{"path": "./exports/attention.pptx", "new_order": [2, 0, 1]}
```

### `pptx_add_slide`

Append (default) or insert at `position` a new slide with `title`,
optional `meta`, and optional `body` textboxes.

```json
{
  "path": "./exports/attention.pptx",
  "title": "Conclusion",
  "meta": "Summary of findings",
  "body": "We covered transformers, diffusion, and survey work.",
  "position": null
}
```

## Path safety

`pptx_*` tools operate on user-supplied paths. Each call resolves the
target through `Path.expanduser().resolve()` and refuses to operate on
a non-existent file (delete / update / inspect) or on a path that is
not a directory when one is expected. Export paths go through
`thesisagents.utils.path_safety.ensure_export_dir`, which rejects
collisions with non-directory files.

## Adding a new tool

1. Open `thesisagents/mcp/server.py` and find the right group helper
   (`_register_search_tools`, `_register_export_tool`,
   `_register_pptx_tools`). Add a new helper if the tool doesn't fit
   any existing group — `build_server` is intentionally kept under
   complexity 15 by delegating to these helpers.
2. Register your tool with `@server.tool()`. The docstring becomes the
   description the calling agent sees — make it specific.
3. Add an integration test in `tests/test_mcp_tools.py`. Use the
   `_call` helper which exercises the same call path FastMCP uses
   over stdio.
