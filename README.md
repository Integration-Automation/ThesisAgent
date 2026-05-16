# AutoPaperToPPT

<!--
Badges below use placeholder `OWNER/REPO` and `autopapertoppt` (PyPI
package name). After you push this repo to GitHub, replace `OWNER/REPO`
with your actual GitHub `<user>/<repo>` so the badges resolve.
-->

[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)
[![Release](https://github.com/OWNER/REPO/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/OWNER/REPO/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![Python](https://img.shields.io/pypi/pyversions/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Languages**: **English** · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **Documentation**: [Read the Docs source](docs/) (Sphinx)

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
  `openaire`, `springer` (needs API key), `ieee` (API key or opt-in
  scrape), `scholar` (opt-in scrape). Each lives in `sources/<name>/`
  behind a `Fetcher` adapter. A top-tier-venue whitelist filters results
  to flagship CS conferences/journals plus Nature/Science/PNAS by
  default; pass `--all-venues` to disable.
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
- **Safety by default**: HTTPS-only HTTP transport, per-source rate
  limit (token bucket), `defusedxml` for any XML payload,
  path-traversal-safe export paths, no `eval` / `exec` / `pickle` on
  user input. Scholar and IEEE scraping are off by default (env-var
  opt-in).

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
| `--enrich` | Download PDF + Anthropic-summarise. Needs `ANTHROPIC_API_KEY` and `[intelligence]` extra. |
| `--lightweight` | Force the abstract-only deck even when `ANTHROPIC_API_KEY` is set. |
| `--llm-model` | Override default `claude-opus-4-7` for enrichment. |
| `--all-venues` | Disable the top-tier whitelist (default keeps flagship CS venues + Nature / Science / PNAS / CACM / LNCS). |
| `--paywall-threshold` | Fraction of paywalled results that triggers the confirmation prompt. Default 0.30. |
| `--yes` | Skip the paywall prompt and proceed. |
| `--max-slides` | Per-paper slide cap (default 25; pass 0 for unlimited). |
| `--quiet` | Suppress per-paper printout. |

### Environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | LLM auth. Not needed for the LLM-as-agent path over MCP. |
| `AUTOPAPERTOPPT_LLM_MODEL` | `--enrich` | Override the default `claude-opus-4-7`. |
| `AUTOPAPERTOPPT_S2_API_KEY` | Semantic Scholar | Higher rate limit. Optional. |
| `AUTOPAPERTOPPT_NCBI_API_KEY` | PubMed | Raises NCBI's anonymous limit (3/s) to 10/s. Optional. |
| `AUTOPAPERTOPPT_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex | Puts requests into Crossref's polite pool. |
| `AUTOPAPERTOPPT_IEEE_API_KEY` | IEEE (API path) | Official IEEE Xplore API; surfaces `pdf_url` for in-scope papers. |
| `AUTOPAPERTOPPT_ENABLE_IEEE_SCRAPING` | IEEE (scrape path) | `=1` opts into scraping. Not needed when the API key is set. |
| `AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Crossref Plus subscriber token (Bearer header). Optional. |
| `AUTOPAPERTOPPT_SPRINGER_API_KEY` | Springer | Required; free key from <https://dev.springernature.com/>. Plugin is silently skipped without it. |
| `AUTOPAPERTOPPT_ENABLE_SCHOLAR_SCRAPING` | Google Scholar | `=1` opts into scraping. Off by default — Scholar ToS forbids scraping. |
| `AUTOPAPERTOPPT_PDF_COOKIES_FILE` | PDF downloader | Netscape `cookies.txt`. Off by default. Use only with publishers you have institutional rights to. |
| `AUTOPAPERTOPPT_LOG_LEVEL` | logger | `INFO` default; `DEBUG` for verbose tracing. |

Defaults: `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. Always
overridable with explicit `--export`.

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
  (`workflow_run` trigger). It runs only if CI succeeded. It then
  diffs `pyproject.toml` against the previous commit; if the
  `version = "..."` line changed, it pipelines:
  1. **`publish-pypi`** — build sdist + wheel, `twine check`,
     `twine upload` via `PYPI_API_TOKEN`.
  2. **`create-draft-release`** — open a *draft* GitHub release at
     tag `v<version>` with auto-generated notes.
  3. **`build-nuitka`** — fan out to Linux / Windows / macOS runners,
     each compiles a Nuitka onefile executable, smoke-tests it,
     attaches the binary + a `.sha256` checksum to the draft release.
     Build cache keyed on `pyproject.toml` cuts warm builds from
     ~15 min to ~3 min.
  4. **`publish-release`** — unmark the draft once all three Nuitka
     assets are uploaded, so users never see a half-finished release.

  If the version did **not** change, every job after `detect-version`
  is skipped — most merges to `main` are no-ops.

To enable PyPI publishing + release executables:

1. Generate a project-scoped API token at
   <https://pypi.org/manage/account/token/>.
2. In the GitHub repo: `Settings → Secrets and variables → Actions →
   New repository secret`. Name it `PYPI_API_TOKEN` and paste the
   token value.
3. To cut a release: bump `version` in `pyproject.toml` (e.g.
   `0.1.0` → `0.1.1`), open a PR, and merge it. CI runs against the
   merge commit; once green, the release pipeline kicks off. About
   3–5 minutes later the PyPI version is live; about 10–15 minutes
   after that (or 3–5 min with a warm Nuitka cache) the three
   platform binaries are attached and the GitHub release goes public.

A protected `pypi` GitHub Environment is referenced by the publish
step; create it under `Settings → Environments` if you want to
require manual approval before each release (optional).

## License

See `LICENSE`. The arXiv API is used under arXiv's API terms of use
(<https://info.arxiv.org/help/api/tou.html>) — observe the 1 request
per 3 seconds soft limit; the bundled fetcher already enforces this via
its token bucket.
