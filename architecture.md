# ThesisAgents Architecture

> Short orientation for people and tools before they touch the code. ThesisAgents (package
> `thesisagents`) turns a research topic into thesis-ready deliverables: it searches many paper
> sources, normalises / de-duplicates / ranks the results, optionally enriches each paper into a
> structured `PaperSummary`, and exports `.pptx`, `.xlsx`, `.bib` and other formats through a CLI,
> an MCP server, a PySide6 GUI or the Python library. The detailed design (pipeline diagram, dedup
> and ranking rules, OA-PDF resolution, rendering tiers, design rationale) is in
> [`docs/architecture.md`](docs/architecture.md); this file does not repeat it.
> Last verified: 2026-09-22 against `ba74127` on `dev` plus the work that was uncommitted then (for
> example `thesisagents/evaluation/`, `docs/search-quality.md`, `scripts/regen_chen2026_*.py`),
> which has since been committed on `dev`.

## 1. Purpose

- Keyword or single-paper search across academic sources, merged into one `PaperCollection`.
- Deliverables shaped by a thesis structure: a rich `PaperSummary` maps onto thesis sections, and a
  thesis-style deck is judged against a seven-section skeleton (see `CLAUDE.md` "Paper Writing Rules").
- Two enrichment paths that produce the same `PaperSummary`: a Python summariser that calls an LLM
  API when `ANTHROPIC_API_KEY` is set, or the LLM-as-agent path in which an MCP-aware language model
  reads the PDF text and authors the summary itself (no API key).
- Deck maintenance after export: inspect, edit and audit existing `.pptx` files.

## 2. Layers and directories

| Path | Responsibility |
|---|---|
| `thesisagents/cli.py`, `__main__.py` | argparse CLI; bare invocation or `gui` launches the GUI, `review` audits a deck |
| `thesisagents/core/` | Frozen models (`models.py`: `Query`, `Paper`, `PaperSummary`, `PaperCollection`, `ExportOptions`), `pipeline.run_search`, `dedup.py`, `ranking.py`, `top_venues.py`, `oa_resolver.py`, `pdf_download.py`, `constants.py` (source and export names) |
| `thesisagents/fetchers/` | `Fetcher` base and `load_fetcher()`, HTTPS-only per-source `httpx` client (`http.get_client`), token-bucket `rate_limit.py`, visible-Chrome helpers (`webrunner_browser.py`, `webrunner_pdf.py`) |
| `thesisagents/sources/<name>/` | One plugin per source: `__init__.py` exposes `fetcher_class`, `fetcher.py`, `parser.py`; browser-backed sources (`ieee`, `scholar`) add `webrunner_backend.py` |
| `thesisagents/exporters/` | `Exporter` strategies (`pptx`, `xlsx`, `bibtex`, `markdown`, `json`, `ris`, `csv`, `csl`) and the `_REGISTRY` in `__init__.py`; `pptx_edit.py`, `review.py` / `audit.py` / `overflow.py` (deck audits), `i18n.py` (deck strings) |
| `thesisagents/intelligence/` | PDF text / asset / metadata extraction and the API summariser (`summarise.py`), `[intelligence]` extra |
| `thesisagents/mcp/` | FastMCP server (`server.build_server()`), `[mcp]` extra |
| `thesisagents/gui/` | PySide6 desktop app (`app.py`, `main_window.py`, `pages/`, `workers.py` on `QThreadPool`, `i18n.py`), `[gui]` extra |
| `thesisagents/evaluation/` | Offline search-quality benchmark (`search_quality.py`; see `docs/search-quality.md`) |
| `thesisagents/utils/` | Logging and path safety |
| `tests/` | pytest suite with recorded fixtures under `tests/fixtures/<source>/`; no live HTTP |
| `scripts/` | Reproducible `regen_*.py` deck builds (hand-authored summaries) and one-off deck maintenance scripts |
| `docs/`, `readmes/` | Sphinx docs with per-language index stubs; translated READMEs |
| `assets/` | App icon and figures used by the regen scripts (`assets/figures/`) |
| `exports/` | Default output area (git-ignored) |

Dependencies flow downward: surfaces → pipeline → core, fetchers, exporters → infra.
An exporter never imports a fetcher; it only consumes a `PaperCollection`.

## 3. Entry points and public interfaces

- **CLI**: `thesisagents` / `python -m thesisagents`. Modes: `--query/-q`, `--paper/-p <url-or-id>`,
  `--pdf <local file>` (with `--title`, `--authors`, `--year`, `--venue`, `--doi`, `--arxiv-id`
  overrides). Source and output control: `--source/-s`, `--exclude-source/-x`, `--max/-n`,
  `--year-from`, `--year-to`, `--min-citations`, `--top-tier-only`, `--export/-e`, `--out/-o`,
  `--filename-stem`, `--lang/-l`, `--enrich`, `--llm-model`, `--lightweight`, `--max-slides`,
  `--dark-mode`, `--no-pdf`, `--no-oa-resolve`, `--paywall-threshold`, `--yes/-y`, `--quiet`.
  Discovery: `--list-sources`, `--list-exports`. Subcommands: `review <deck.pptx>`
  (`exporters/review.py`), `gui`. Reference: `docs/cli.md`.
- **MCP**: `thesisagents-mcp` (`thesisagents/mcp/__main__.py`). Tools cover discovery (`list_sources`,
  `list_exports`), `search`, `fetch_paper`, `fetch_pdf_text`, `download_pdfs`, `export`, and deck
  tools `pptx_inspect`, `pptx_review`, `pptx_update_slide`, `pptx_delete_slide`,
  `pptx_reorder_slides`, `pptx_add_slide`. Stateless across calls. Reference: `docs/mcp.md`.
- **GUI**: `thesisagents-gui` (`thesisagents.gui.app:main`), or `thesisagents` with no arguments.
- **Library**: `thesisagents.core.pipeline.run_search(query)` and
  `thesisagents.exporters.export_collection(collection, ExportOptions(...))`.
- **Configuration** (env vars): `ANTHROPIC_API_KEY`, `THESISAGENTS_CONTACT_EMAIL`,
  `THESISAGENTS_SPRINGER_API_KEY`, `THESISAGENTS_CORE_API_KEY`, `THESISAGENTS_IEEE_API_KEY`,
  `THESISAGENTS_DISABLE_IEEE_SCRAPING`, `THESISAGENTS_DISABLE_SCHOLAR_SCRAPING`,
  `THESISAGENTS_DISABLE_WEBRUNNER`. Reference: `docs/configuration.md`.
- **Build / release**: `pyproject.toml` extras (`mcp`, `intelligence`, `gui`, `web`, `dev`);
  `docs/packaging-nuitka.md`, `docs/packaging-pyinstaller.md`; `.github/workflows/ci.yml`, `release.yml`.

## 4. Main flows

**Query → sources → dedup / rank → exporters**

```
Query (CLI flags / MCP search / GUI / library)
  → core.pipeline.run_search
  → fetchers.base.load_fetcher(name) for each source      (imports thesisagents.sources.<name>)
  → asyncio.gather over Fetcher.fetch                      (per-source token bucket, HTTPS-only client;
                                                            ieee / scholar via visible Chrome)
  → parser → list[Paper] → core.dedup → core.ranking → optional top-venue filter
  → core.oa_resolver (fills pdf_url) → optional PDF download → optional enrichment → PaperCollection
  → exporters.export_collection → _REGISTRY[format] → files under --out
```

A failing source returns nothing and never breaks the others. When the paywalled share of a result
set exceeds `--paywall-threshold`, the CLI asks before building per-paper decks (`--yes` skips).

**Enrichment**

```
ANTHROPIC_API_KEY set → intelligence.pdf extracts text → intelligence.summarise → PaperSummary
no key, model in the loop → MCP fetch_pdf_text → model authors PaperSummary
                            → MCP export, or a scripts/regen_<key>.py that calls the exporter
no key, no model → lightweight, abstract-based deck
```

**Deck audit**: `thesisagents review <deck.pptx>` and the MCP `pptx_review` tool run the same checks
(overflow, colour contracts, section completeness).

## 5. Extension points

- **New source**: create `thesisagents/sources/<name>/` (`__init__.py` with `fetcher_class`,
  `fetcher.py` with a `Fetcher` subclass and its `RATE_LIMIT`, `parser.py` → `Paper`), register the
  name in `thesisagents/core/constants.py` (`CORE_SOURCES` or `PLUGIN_SOURCES`, plus `DEFAULT_SOURCES`
  if it should run by default), and add recorded fixtures under `tests/fixtures/<name>/`.
  Paywalled or captcha-prone sources add a `webrunner_backend.py` on top of
  `thesisagents/fetchers/webrunner_browser.py`. Guide: [`docs/source_plugins.md`](docs/source_plugins.md).
- **New exporter**: subclass `Exporter` (`thesisagents/exporters/base.py`), add an `EXPORT_*` name in
  `thesisagents/core/constants.py`, and register it in `_REGISTRY` in `thesisagents/exporters/__init__.py`.
- **New MCP tool**: add it in one of the `_register_*` functions called by
  `thesisagents/mcp/server.py::build_server()`.
- **New localised string**: `thesisagents/exporters/i18n.py` (decks) or `thesisagents/gui/i18n.py`
  (UI); every supported language must be filled (`tests/test_i18n.py`, `tests/gui/test_i18n.py`).
- **New summary field**: `PaperSummary` in `thesisagents/core/models.py`, consumed by the thesis-style
  tier in `thesisagents/exporters/pptx.py`.

## 6. Cross-project boundaries

- Declares `je_web_runner>=0.0.60` (the workspace's WebRunner project) but does **not** import it:
  `thesisagents/fetchers/webrunner_browser.py` drives raw Selenium with one Chrome per call because
  WebRunner's module-level driver singleton breaks concurrent sources. Selenium itself currently
  arrives through that dependency, so removing it needs an explicit `selenium` requirement.
- `scripts/regen_chen2026_codereview.py`, `regen_chen2026_tcse.py` and
  `regen_chen2026_tcse_features.py` cite the prthinker repository's `paper/` manuscripts by absolute
  path as their source of truth; numbers are copied into the scripts and figures into
  `assets/figures/chen2026*/`. The manuscript versions they cite are no longer in that `paper/`
  directory, so re-verification means reading the current drafts there.
- External services (arXiv, Semantic Scholar, OpenAlex, publishers, Unpaywall, …) are reached only
  through `thesisagents/fetchers/http.py` or the visible-Chrome helpers.

## 7. Design constraints

Summarised from `CLAUDE.md` and `AGENTS.md`; each bullet names the section with the full rule.

- Every change passes `py -m pytest tests/`, `py -m ruff check .` and
  `py -m bandit -c pyproject.toml -r thesisagents/`, with new tests (`CLAUDE.md` "Definition of Done";
  `AGENTS.md` "Other rules you will trip on").
- Additions carry their context and a detailed explanation; deliverable prose avoids `；` / `;` and
  prose dashes; implemented features are not claimed as evaluated (`CLAUDE.md` "Content additions must be
  context-clear + detail-explained").
- IEEE, Google Scholar and paywalled-publisher PDFs go through visible Chrome, never headless; confirm
  VPN / institutional access before paywalled searches (`CLAUDE.md` "IEEE / Publisher CDN: Browser
  Automation Is Mandatory").
- Before editing any `.pptx`, read the deck rule documents; every text run sets an explicit colour, no
  light text on light fills, no red text; the default deck is light (`CLAUDE.md` "Read … BEFORE Editing
  Any .pptx", "Dark-Mode Contract").
- Thesis-style outputs follow the seven-section paper skeleton and the `PaperSummary` → section mapping
  (`CLAUDE.md` "Paper Writing Rules").
- When a model drives the session the rich deck is the deliverable; never invent numbers, URLs, DOIs
  or arXiv IDs (copy them from the search's `.xlsx`); prune off-topic downloads (`AGENTS.md`
  "LLM-as-agent default path").
- No live network in tests; all HTTP through `get_client(source)` (HTTPS-only); slide geometry guards
  (`AGENTS.md` "Other rules you will trip on").
- Core versus source-plugin split is about dependency surface and failure isolation
  (`docs/architecture.md` "Core vs source plugins").

## 8. When to update this file

- A subpackage or surface (CLI, MCP, GUI, library) is added, removed or renamed.
- The pipeline stage order changes (fetch, dedup, rank, OA resolution, download, enrichment, export).
- Source or exporter registration, MCP tool registration, or the i18n contract changes.
- Console scripts, extras, CLI modes / subcommands or configuration env vars change.
- A cross-project link in §6 changes (WebRunner dependency, prthinker manuscript provenance).
- The currently uncommitted modules are committed, moved or dropped.
- Update the "Last verified" line with the date and commit whenever this file is revised.
