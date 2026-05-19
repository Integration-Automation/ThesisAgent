# AutoPaperToPPT

[![CI](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![Python](https://img.shields.io/pypi/pyversions/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/AutoPaperToPPT.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/autopapertoppt/badge/?version=latest)](https://autopapertoppt.readthedocs.io/en/latest/)

> **Languages**: **English** · [繁體中文](readmes/README.zh-TW.md) · [简体中文](readmes/README.zh-CN.md) · [日本語](readmes/README.ja.md) · [Español](readmes/README.es.md) · [Français](readmes/README.fr.md) · [Deutsch](readmes/README.de.md) · [한국어](readmes/README.ko.md) · [Português](readmes/README.pt.md) · [Русский](readmes/README.ru.md) · [Italiano](readmes/README.it.md) · [Tiếng Việt](readmes/README.vi.md) · [हिन्दी](readmes/README.hi.md) · [Bahasa Indonesia](readmes/README.id.md)
> **Documentation**: [autopapertoppt.readthedocs.io](https://autopapertoppt.readthedocs.io/en/latest/)

A keyword-driven paper search assistant that fetches results from arXiv,
Semantic Scholar, OpenAlex, PubMed, ACM (via Crossref), IEEE Xplore,
DBLP, generic Crossref, OpenAIRE, Springer Nature, and Google Scholar,
normalises them into one record shape, and exports the deduplicated set
as a **thesis-style PowerPoint deck**, an **Excel workbook**, and a
**BibTeX file** — all from one CLI call or one MCP tool call. Optionally
enriches each paper by reading its PDF and producing a structured
per-paper summary either in-context (LLM-as-agent flow) or via the
Anthropic API (Python pipeline flow).

## For AI agents driving this project

**If you are an LLM (Claude Code, Cursor, Aider, Codex CLI, …) reading
this README to figure out what to do — start here.** Everything below
is also pinned in [`AGENTS.md`](AGENTS.md) (cross-agent mirror) and
[`CLAUDE.md`](CLAUDE.md) (canonical reference); read those before
making non-trivial changes.

### What the user actually wants

The default deliverable is **a thesis-style rich `.pptx` per paper**,
not the lightweight abstract-only deck the CLI produces by default. The
lightweight emit is an intermediate artefact — your job is to upgrade
it.

### Decision tree

1. Is `ANTHROPIC_API_KEY` set in the environment? → just run the CLI;
   it auto-enriches via the Anthropic API. You are done.
2. No key, but you (an LLM) are driving the session → **you produce
   the rich summary yourself**. Read each PDF, hand-author a
   `PaperSummary` with rich-tier fields (`pain_points`,
   `research_question`, `contributions_detailed`, `headline_metrics`,
   `technique_table`, `method_sections`, `evaluation_sections`,
   `system_flow`, `research_questions`, `rq_results`,
   `core_observation`, `limitations`, `future_work`), drop a
   `scripts/regen_<query>.py`, run it. **Do not tell the user to set
   the API key** — you are the LLM that would have written the
   summary.
3. No LLM in the loop (CI / cron / unattended) → lightweight is
   acceptable.

### 6-step MCP workflow

```
1. (optional) list_sources()                              # see which plugins are enabled
2. search(keywords, sources, top_tier_only=true, ...)
3. (optional) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # per paper
5. (you read each PDF and produce a structured summary dict)
6. export(papers=[{...paper, "summary": {...}}], language="zh-tw", ...)
```

All eleven MCP tools (including `list_sources`, `download_pdfs`,
`pptx_inspect` / `pptx_update_slide` / `pptx_add_slide` / etc.) are
documented in [`docs/mcp.md`](docs/mcp.md).

### Mandatory: URL / DOI verification before shipping

Publisher URL paths **cannot be guessed** — AAAI uses numeric IDs
(`v40i5.37389`), IEEE uses an opaque `arnumber`, ACM uses opaque DOIs.
When you hand-author a `Paper`, **copy `url` / `doi` / `arxiv_id`
verbatim from the search xlsx that produced this run** — never from
memory, never constructed from the title.

The xlsx is written to `exports/<run>/<slug>-<timestamp>.xlsx` with
column 7 = DOI, column 8 = URL. Audit your regen script when you
finish:

```python
from openpyxl import load_workbook
from scripts.regen_<run> import ALL_PAPERS
real = {sh.cell(row=r, column=2).value: sh.cell(row=r, column=8).value
        for sh in [load_workbook("exports/<run>/<slug>-<ts>.xlsx")["Papers"]]
        for r in range(2, sh.max_row + 1)}
for p in ALL_PAPERS:
    actual = next((u for t, u in real.items() if p.title[:30] in (t or "")), None)
    if actual and not (p.url == actual
                       or p.url.split("v")[0] == actual.split("v")[0]):
        print(f"! {p.bibtex_key()} authored {p.url} vs real {actual}")
```

Two fabrications caught this way in production: wrong AAAI volume
(`v39i23.34521` vs real `v39i22.34537`) and invented author-slug path
(`view/fang2026` instead of `v40i5.37389`).

### Mandatory: prune irrelevant downloads before shipping

Search keyword matching is keyword-based, so off-topic papers will
slip in: a "Claude code" query returned a Viterbi-decoder paper
because both contain "code"; "LLM code review" matched an
object-detection literature review. Once you read the abstracts and
classify a paper off-topic for the user's actual intent, prune the
run dir:

```python
from pathlib import Path
run = Path("exports/<run>")
irrelevant_keys = ("key-of-off-topic-paper-1", "key-of-off-topic-paper-2")
for key in irrelevant_keys:
    for path in (run / "pdfs" / f"{key}.pdf", run / f"{key}.pptx"):
        if path.exists():
            path.unlink()
```

Delete `exports/<run>/pdfs/<key>.pdf` + `exports/<run>/<key>.pptx`.
**Keep** the aggregate `<slug>-<timestamp>.xlsx` / `.bib` — those are
the honest record of what the search returned. Borderline cases get
a rich summary; better to over-include than to silently drop a
possible match.

### Worked example

[`scripts/regen_llm_security_batch.py`](scripts/regen_llm_security_batch.py)
ships 8 hand-authored rich summaries built exactly this way. Use it as
the template for any multi-paper search. The zh-tw companion is at
[`scripts/regen_llm_security_batch_zh_tw.py`](scripts/regen_llm_security_batch_zh_tw.py).

### Don'ts

- **Don't** end a multi-paper search by telling the user "set
  `ANTHROPIC_API_KEY` for a rich deck" — you are the LLM that could
  have written the summaries.
- **Don't** treat the per-paper lightweight `.pptx` as the
  deliverable.
- **Don't** stop after `download_pdfs` reports N PDFs saved — that's
  the start of the rich-authoring phase, not the end.
- **Don't** invent numbers, RQs, contributions, or limitations not in
  the paper.
- **Don't** fabricate URLs / DOIs / arXiv IDs — see the rule above.
- **Don't** leave irrelevant downloads in the run directory. Keyword
  search matches can include off-topic papers (a "Claude code" query
  pulled in a Viterbi-decoder paper; "LLM code review" pulled in an
  object-detection literature review). After classifying papers
  off-topic, delete their `pdfs/<key>.pdf` and lightweight
  `<key>.pptx`; keep the aggregate xlsx / bib as the honest record of
  what the search returned.
- **Don't** mention "Claude", "Claude Code", "AI-generated", "GPT",
  "Copilot", or any AI tool/model name in commit messages, PR
  descriptions, code comments, or documentation.

## Features

- **Eleven pluggable sources**: `arxiv`, `semantic_scholar`, `openalex`,
  `pubmed`, `acm` (Crossref-scoped), `dblp`, `crossref` (unscoped),
  `openaire`, `springer` (needs API key), `ieee` (default-on via visible
  Chrome; API key adds official Xplore API), `scholar` (default-on via
  visible Chrome). Each lives in `sources/<name>/` behind a `Fetcher`
  adapter. A top-tier-venue whitelist filters results to flagship CS
  conferences/journals plus Nature/Science/PNAS by default; pass
  `--all-venues` to disable.
- **Single-paper mode**: paste an arXiv ID, arXiv URL, DOI, PMID, or IEEE
  document URL — AutoPaperToPPT resolves it via the right source and
  emits the same export bundle. Useful for paper reading notes and thesis
  defence prep.
- **Local PDF mode** (`--pdf <path>`): pass one PDF or a directory.
  A heuristic extractor pulls **title, authors, year, arXiv ID, DOI, and
  the real abstract** straight from each PDF's front matter (anchored
  on the explicit `Abstract` / `ABSTRACT` / `摘要` header, not a blind
  prefix). `--title` / `--authors` / `--year` / `--venue` / `--doi` /
  `--arxiv-id` override on a single-PDF call; on a directory, per-file
  extraction wins so every paper gets its own deck named after its
  BibTeX key.
- **Five exporters**:
  - `.pptx` — 16:9 widescreen, page-numbered, three rendering tiers
    (lightweight abstract-only · enriched-flat · **thesis-style** with
    pain-point quadrants, KPI callouts, technique-comparison tables,
    per-RQ result tables, contribution summary, core observation,
    limitations & future work, Q&A, references). All template strings
    are i18n'd across **14 languages**: English, 繁體中文, 简体中文,
    日本語, Español, Français, Deutsch, 한국어, Português, Русский,
    Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia.
  - `.xlsx` — Papers sheet + Query provenance sheet, hyperlinked URL /
    PDF, frozen header, auto column widths. Column 5 (**Source**) shows
    the real publication venue (e.g. "IEEE Access"); column 6
    (**Indexed via**) shows which fetcher returned the metadata
    (e.g. "openalex"), so the two pieces of information never collide.
  - `.md` — full source / title / abstract list.
  - `.bib` — collision-free citation keys, LaTeX-escaped fields.
  - `.json` — raw payload for downstream tooling.
- **PPT editing toolkit**: `autopapertoppt.exporters.pptx_edit`
  (inspect / update_slide / delete_slide / reorder_slides / add_slide)
  works against any deck the exporter produces, plus the equivalent
  `pptx_*` MCP tools so an LLM agent can iterate on a generated deck.
- **MCP server**: 11 tools — `list_sources` (discovery),
  `search`, `fetch_paper`, `fetch_pdf_text`, `download_pdfs`,
  `export`, and the five `pptx_*` editing tools. Lets any MCP-aware LLM
  (Claude Code, Claude Desktop, Cursor, …) drive the whole workflow.
- **Two enrichment paths** for going beyond the abstract into a true
  thesis-style deck:
  - **LLM-as-agent (no API key)** — the calling LLM reads the PDF body
    text via `fetch_pdf_text`, writes a structured summary in-context,
    and passes it to `export`.
  - **Python pipeline (`--enrich`)** — the CLI calls Anthropic's API
    itself; default model `claude-opus-4-7`.
- **Visible-Chrome publisher flows**: Scholar SERP, IEEE `/rest/search`,
  and every paywalled-PDF download (ieeexplore / dl.acm / link.springer
  / sciencedirect / wiley / oup / nature / science / …) run inside a
  real visible Chrome session via `selenium`. The user solves captcha
  / completes SSO in the live window once; `AUTOPAPERTOPPT_CHROME_PROFILE_DIR`
  persists the cookies across runs.
- **LLM-as-agent flow** (`scripts/llm_*.py`): when the LLM in your editor
  wants to drive the browser itself (rather than let `asyncio.gather` do
  it), `scripts/llm_driven_search.py` opens Chrome on Scholar + IEEE,
  `scripts/llm_download_pdfs.py` walks an xlsx and downloads every paper
  in one Chrome session (IEEE / ACM / Springer / arXiv / ACL Anthology /
  NeurIPS / OpenReview), and `scripts/regen_*.py` shows the worked
  pattern for hand-authoring a rich `PaperSummary` per paper.
- **OA PDF resolver**: post-dedup, every paper without `pdf_url`
  goes through Unpaywall → S2 `openAccessPdf` → arXiv title search →
  CORE.ac.uk (when keys are set). Typical lift on IEEE / ACM / Springer
  / Elsevier-heavy queries: 40-70 percentage points.
- **Safety by default**: HTTPS-only HTTP transport, per-source rate
  limit (token bucket), `defusedxml` for any XML payload,
  path-traversal-safe export paths, no `eval` / `exec` / `pickle` on
  user input.

## Quick start

```powershell
git clone <repo-url>
cd AutoPaperToPPT
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Install with dev extras (also pulls in MCP SDK and intelligence deps)
pip install -e .[dev]
```

Search arXiv and export deck + workbook + BibTeX (default for `--query`):

```powershell
py -m autopapertoppt --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

Fetch a single paper by URL — defaults to `.pptx + .bib` (the `.xlsx`
makes less sense for one row):

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

Render the deck in 繁體中文:

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --lang zh-tw --out .\exports\
```

LLM-pipeline enrichment (Python calls Anthropic itself — needs API key):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang zh-tw --out .\exports\
```

## CLI flags

| Flag | Purpose |
|---|---|
| `--query` / `-q` | Keywords (required unless `--paper`). |
| `--paper` / `-p` | arXiv ID / URL, DOI, PMID, or IEEE document URL. Mutually exclusive with `--query`. |
| `--source` / `-s` | Comma-separated source list. Default `arxiv`. |
| `--max` / `-n` | Max results per source (1..200). Default 25. |
| `--year-from` / `--year-to` | Inclusive year filter. |
| `--export` / `-e` | Formats: any of `pptx,xlsx,md,bib,json`. Default depends on mode (see below). |
| `--out` / `-o` | Output directory. Default `./exports`. |
| `--filename-stem` | Override the generated filename stem. |
| `--no-abstract` | Omit abstract content from exports. |
| `--lang` / `-l` | Deck language: one of 14 — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. Default `en`. |
| `--enrich` | Fail-loud variant of auto-enrich. Needs `ANTHROPIC_API_KEY` and `[intelligence]` extra. (Auto-enrich is default when the key is set.) |
| `--lightweight` | Skip enrichment + force the abstract-only deck. Use only for quick / unattended runs; **when an LLM agent is driving, prefer the LLM-as-agent flow** below. |
| `--llm-model` | Override default `claude-opus-4-7` for enrichment. |
| `--no-pdf` | Skip the automatic PDF download. Also disables the per-paper PPT gate (no PDF → no full content). |
| `--no-oa-resolve` | Skip the post-dedup OA PDF resolver (Unpaywall + S2 + arXiv + CORE.ac.uk). |
| `--top-tier-only` | Restrict results to arXiv + a curated CS-flagship whitelist (S&P, CCS, NDSS, USENIX Security, NeurIPS, ICML, ICSE, …). Off by default. |
| `--paywall-threshold` | Fraction of paywalled results that triggers the confirmation prompt. Default 0.30. |
| `--yes` | Skip the paywall prompt and proceed. |
| `--max-slides` | Per-paper slide cap (default 25; pass 0 for unlimited). |
| `--quiet` | Suppress per-paper printout. |

### Environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | LLM auth. Not needed for the LLM-as-agent path over MCP. |
| `AUTOPAPERTOPPT_LLM_MODEL` | `--enrich` | Override the default `claude-opus-4-7`. |
| `AUTOPAPERTOPPT_S2_API_KEY` | Semantic Scholar + OA resolver | Higher rate limit; also used by the OA resolver's S2 `openAccessPdf` step. Free key at <https://www.semanticscholar.org/product/api>. |
| `AUTOPAPERTOPPT_NCBI_API_KEY` | PubMed | Raises NCBI's anonymous limit (3/s) to 10/s. Optional. |
| `AUTOPAPERTOPPT_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex, **Unpaywall** | Polite-pool tag + enables the OA resolver's Unpaywall step (biggest PDF-coverage win for IEEE / ACM / Springer / Elsevier-paywalled papers; typical lift 40-70 pp). |
| `AUTOPAPERTOPPT_IEEE_API_KEY` | IEEE (API path) | Official IEEE Xplore API; surfaces `pdf_url` for in-scope papers. |
| `AUTOPAPERTOPPT_DISABLE_IEEE_SCRAPING` | IEEE | **IEEE is default-ON via visible Chrome.** Set `=1` to opt out (e.g. CI without Chrome). The httpx scrape branch only runs as a fallback when WebRunner is unavailable. |
| `AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Crossref Plus subscriber token (Bearer header). Optional. |
| `AUTOPAPERTOPPT_SPRINGER_API_KEY` | Springer | Required; free key from <https://dev.springernature.com/>. Plugin raises `ConfigError` without it. |
| `AUTOPAPERTOPPT_DISABLE_SCHOLAR_SCRAPING` | Google Scholar | **Scholar is default-ON via visible Chrome.** Set `=1` to opt out (Google's ToS forbids automated access — default-on for coverage, opt-out to avoid captcha / IP-block risk). |
| `AUTOPAPERTOPPT_CHROME_PROFILE_DIR` | Scholar + IEEE + paywalled-PDF downloads | Persistent Chrome `--user-data-dir`. Set this and complete VPN / SSO / Google sign-in once; subsequent runs inherit the cookies so IEEE returns paywalled metadata and Scholar serves un-throttled SERPs. |
| `AUTOPAPERTOPPT_DISABLE_WEBRUNNER` | Scholar + IEEE + paywalled-PDF downloads | `=1` forces the httpx paths instead of driving real Chrome. Useful for CI / Docker without a Chrome binary; otherwise leave unset. |
| `AUTOPAPERTOPPT_CORE_API_KEY` | OA resolver | Free key from <https://core.ac.uk/services/api>. Enables the CORE.ac.uk lookup step (200M+ institutional / regional OA items). Other OA strategies (Unpaywall, S2, arXiv) still run without it. |
| `AUTOPAPERTOPPT_PDF_COOKIES_FILE` | PDF downloader | Netscape `cookies.txt`. Off by default. Use only with publishers you have institutional rights to. |
| `AUTOPAPERTOPPT_LOG_LEVEL` | logger | `INFO` default; `DEBUG` for verbose tracing. |

Defaults: `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. Always
overridable with explicit `--export`.

## LLM-as-agent flow

When an LLM in your editor (Claude Code, Cursor, Aider, Codex CLI, …)
wants to drive the publisher browser itself — pick URLs, inspect the
returned DOM, decide which papers to dig into — five scripts under
`scripts/` cover the canonical path:

| Script | What it does |
|---|---|
| `scripts/llm_driven_search.py "<query>"` | Boots visible Chrome, navigates Scholar SERP for the query, JS-fetches IEEE `/rest/search` from inside the IEEE origin, dumps SERP HTML + IEEE JSON to `exports/_llm_scratch/`. |
| `scripts/llm_parse_results.py` | Reads the dumped artefacts, runs the project's parsers, dedups + ranks + exports `.xlsx` + `.md` for the LLM to inspect. |
| `scripts/llm_download_pdfs.py <xlsx>` | Walks the xlsx, dispatches each row to the right per-publisher downloader (IEEE / ACM / Springer / arXiv / ACL Anthology / NeurIPS / OpenReview) in ONE Chrome session. Idempotent: papers with a valid `<id>.pdf` already on disk skip immediately. |
| `scripts/llm_download_{ieee,acm,springer}_pdf.py <id>` | Single-paper variants for iterating on selectors / debugging one entry. |
| `scripts/regen_*.py` | Worked example of hand-authored rich `PaperSummary` per paper → rich-tier `.pptx`. Look at `scripts/regen_speculative_decoding_zh_tw.py` for the canonical shape. |

Full end-to-end runbook (search → rich deck) lives in
`.claude/agents/paper-summary-author.md` — open it before starting a
new query so the LLM can run the flow without pausing for user input.

## MCP server

Register with Claude Code:

```powershell
claude mcp add autopapertoppt -- ".venv\Scripts\python.exe" -m autopapertoppt.mcp
```

Or write to your settings file:

```json
{
  "mcpServers": {
    "autopapertoppt": {
      "command": ".venv\\Scripts\\python.exe",
      "args": ["-m", "autopapertoppt.mcp"]
    }
  }
}
```

Tools:

| Tool | Purpose |
|---|---|
| `list_sources` | Enumerate every plugin + report whether each is enabled in the current env. Call this once before `search`. |
| `search` | Keywords → list of papers. Accepts `top_tier_only`, `min_citations`; defaults to the full no-API-key source mix. |
| `fetch_paper` | arXiv / DOI / PMID / IEEE identifier → single paper. |
| `fetch_pdf_text` | Download one PDF, return extracted body text. **The MCP path to "I read the paper".** |
| `download_pdfs` | Batch-download a papers list's PDFs into `{out_dir}/pdfs/`. Returns per-paper results keyed by BibTeX key. |
| `export` | Papers list + formats → writes `.pptx/.xlsx/.md/.bib/.json`. Accepts a `summary` field per paper for the rich thesis-style schema and `max_slides_per_paper` (default 25). |
| `pptx_inspect` | Read slide / shape structure of an existing deck. |
| `pptx_update_slide` | Replace `title` / `body` / `meta` (by shape name) or arbitrary shapes by index. |
| `pptx_delete_slide` | Remove a slide and its part relationship. |
| `pptx_reorder_slides` | Permute slides via `sldIdLst`. |
| `pptx_add_slide` | Append or insert a new title / body / meta slide. |

LLM-as-agent flow (no `ANTHROPIC_API_KEY` needed — the LLM is the agent):

```
1. (optional) list_sources()                       # discover enabled plugins
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (optional) download_pdfs(papers, out_dir="./exports/...")  # persist PDFs
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # per paper
5. (the LLM reads body text, produces a structured `summary` dict)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="zh-tw", formats=["pptx","bib"], ...)
```

Full reference in [`docs/mcp.md`](docs/mcp.md).

## Project layout

```
AutoPaperToPPT/
├── autopapertoppt/                 # main package
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # HTTPS-only async client, token-bucket rate limit
│   ├── exporters/                   # pptx (thesis-style) · xlsx · bib · md · json · pptx_edit · i18n
│   ├── intelligence/                # PDF fetch + Anthropic summariser  ([intelligence] extra)
│   ├── mcp/                         # FastMCP server (11 tools)
│   ├── utils/                       # logging, path safety
│   ├── cli.py                       # argparse CLI
│   └── __main__.py
├── sources/                         # plugin folders: arxiv, semantic_scholar,
│                                    #   openalex, pubmed, acm, ieee, scholar,
│                                    #   dblp, crossref, openaire, springer
├── tests/                           # pytest suite + recorded fixtures (no live HTTP)
├── docs/                            # Sphinx (14 language trees)
├── scripts/                         # one-off regen scripts
└── pyproject.toml                   # ruff, bandit, build, optional extras
```

## Definition of Done

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r autopapertoppt/ sources/
```

The `-c` flag on bandit is required — without it bandit ignores the
project skip config. When touching the pptx exporter, also run an
overflow check (see `CLAUDE.md` "Slide Deck Rules").

## Desktop GUI (PySide6)

A native desktop interface ships behind the `[gui]` extra:

```powershell
pip install autopapertoppt[gui]
autopapertoppt-gui                 # or: autopapertoppt gui
```

The window has four tabs — **Search** (functional), **Settings**
(functional, persists API keys via QSettings), **Enrich**, and
**Deck** (the latter two land in a follow-up). The Windows release
zip ships the Nuitka-compiled bundle with PySide6 included, so
`autopapertoppt.exe gui` works without a separate Python install.
**UI ships in all 14 languages** (English, 繁體中文, 简体中文,
日本語, Español, Français, Deutsch, 한국어, Português, Русский,
Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia) — first run picks
the language from your OS locale, then **Settings → Interface
language** lets you change it. The deck output language is a
separate dropdown so you can run the UI in one language and emit
slides in another. The layout is responsive: every form sits in
a `QScrollArea` and the window resizes down to 900×600 (still fits
720p), with HiDPI scaling on by default.

Full reference: [`docs/gui.md`](docs/gui.md).

## Packaging as a standalone executable

Two packagers are documented for shipping a single-file binary that
runs without Python installed:

- **[`docs/packaging-pyinstaller.md`](docs/packaging-pyinstaller.md)**
  — fast build (under a minute), 200–300 MB output, 2–4 s startup.
  Best when you iterate on the build script.
- **[`docs/packaging-nuitka.md`](docs/packaging-nuitka.md)** —
  slow build (5–15 minutes), 80–150 MB output, sub-second startup,
  some bytecode protection. Best when end users run the binary
  many times.

Both docs cover the project-specific gotcha — the dynamic source
plugins under `sources/<name>/` — and ship a verified command for
the CLI and the MCP server entry points.

## Continuous integration & releases

Two GitHub Actions workflows live under `.github/workflows/`:

- **`ci.yml`** runs on every push and PR to `main`. Matrix is Ubuntu +
  Windows × Python 3.12 / 3.13 / 3.14 (6 jobs). Each job runs
  `ruff check`, `bandit -c pyproject.toml`, and `pytest`.
- **`release.yml`** waits for `ci.yml` to complete on `main`
  (`workflow_run` trigger). It runs only if CI succeeded. **Every
  CI-success push to `main` is a release** — the workflow auto-bumps
  the patch version in `pyproject.toml`, commits the bump back to
  `main` as `chore: bump version to X.Y.Z`, and pipelines:
  1. **`bump-version`** — read current `X.Y.Z` from `pyproject.toml`,
     increment to `X.Y.(Z+1)`, commit + push back to `main` using the
     workflow `GITHUB_TOKEN`. That push does NOT re-trigger CI (per
     GitHub's rule that `GITHUB_TOKEN`-driven pushes can't start new
     workflow runs), so the cycle terminates naturally.
  2. **`publish-pypi`** — build sdist + wheel, `twine check`,
     `twine upload` via `PYPI_API_TOKEN`.
  3. **`create-draft-release`** — open a *draft* GitHub release at
     tag `v<version>` with auto-generated notes.
  4. **`build-nuitka`** — compile a Nuitka standalone bundle on a
     Windows runner (entry point: `python -m autopapertoppt` via
     `--python-flag=-m`), smoke-test it, zip the resulting
     `autopapertoppt.dist/` folder, and attach the zip + a `.sha256`
     checksum to the draft release. Standalone (not onefile) by
     design: onefile self-extracts to `%TEMP%` on every launch,
     adding startup latency and tripping antivirus heuristics on
     locked-down machines. Windows-only by design too: Linux / macOS
     users install from PyPI. Build cache keyed on `pyproject.toml`
     cuts warm builds from ~70 min cold to ~5–10 min.
  5. **`publish-release`** — unmark the draft once the Nuitka asset
     is uploaded, so users never see a half-finished release.

  **Skipping a release.** Include `[skip release]` anywhere in the
  commit message and the bump + every downstream job is skipped — use
  this for docs-only / typo / refactor commits that shouldn't burn a
  version number.

To enable PyPI publishing + release executables:

1. Generate a project-scoped API token at
   <https://pypi.org/manage/account/token/>.
2. In the GitHub repo: `Settings → Secrets and variables → Actions →
   New repository secret`. Name it `PYPI_API_TOKEN` and paste the
   token value.
3. Allow GitHub Actions to push to `main`: `Settings → Actions →
   General → Workflow permissions → Read and write permissions`. The
   bump commit is pushed by the workflow's `GITHUB_TOKEN`.
4. Cut releases by merging PRs into `main`. The pipeline takes
   ~3–5 min to publish to PyPI and ~50–70 min more (cold) or ~5–10 min
   (warm Nuitka cache) for the Windows zip to attach.

The `publish-pypi` job intentionally does NOT attach a GitHub
Environment, so each run surfaces as a Release entry (with its
Nuitka `.exe` attached) rather than as a "Deployment" sidebar
widget on the repo home — releases get their own dedicated page
and a Deployment entry on top would just be redundant noise.

## License

See `LICENSE`. The arXiv API is used under arXiv's API terms of use
(<https://info.arxiv.org/help/api/tou.html>) — observe the 1 request
per 3 seconds soft limit; the bundled fetcher already enforces this via
its token bucket.
