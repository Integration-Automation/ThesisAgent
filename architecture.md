# ThesisAgents Architecture

> Short orientation for people and tools before they touch the code. ThesisAgents (package
> `thesisagents`) turns a research topic into thesis-ready deliverables: it searches many paper
> sources, normalises / de-duplicates / ranks the results, optionally enriches each paper into a
> structured `PaperSummary`, and exports `.pptx`, `.xlsx`, `.bib` and other formats through a CLI,
> an MCP server, a PySide6 GUI or the Python library. The detailed design (pipeline diagram, dedup
> and ranking rules, OA-PDF resolution, rendering tiers, design rationale) is in
> [`docs/architecture.md`](docs/architecture.md); this file does not repeat it.
> Last verified: 2026-10-08 on `dev`, with the export identifier preflight
> (`thesisagents/core/export_validation.py`) and the search diagnostics
> (`thesisagents/core/diagnostics.py`, `pruning.py`, per-source statistics in `pipeline.py`), and
> citation snowballing (`thesisagents/core/snowball.py`, `thesisagents/fetchers/citations.py`), and
> the literature library (`thesisagents/library/`), and the deck template contract
> (`thesisagents/exporters/template.py`).

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
| `thesisagents/cli.py`, `__main__.py` | argparse CLI; bare invocation or `gui` launches the GUI, `review` audits a deck. `cli.py` holds the flags and the order of the stages, with one module per group of flags beside it: `cli_output.py` (what a run prints), `cli_snowball.py` (`--snowball*`), `cli_library.py` (`--library*`), `cli_template.py` (`--pptx-template*`), `cli_local_pdf.py` (`--pdf` mode) |
| `thesisagents/core/` | Frozen models (`models.py`: `Query`, `Paper`, `PaperSummary`, `PaperCollection`, `ExportOptions`), `pipeline.run_search`, `dedup.py`, `ranking.py` (`rank` and the explained `rank_with_scores`), `pruning.py` (advisory keep / review / prune), `diagnostics.py` (the records both produce), `top_venues.py`, `oa_resolver.py`, `pdf_download.py`, `snowball.py` (bounded citation snowballing over `CitationProvider`s), `export_validation.py` (the DOI / URL preflight every export runs first), `constants.py` (source and export names) |
| `thesisagents/fetchers/` | `Fetcher` base and `load_fetcher()`, HTTPS-only per-source `httpx` client (`http.get_client`, plus `http.scoped_client` for code that runs on a private event loop), token-bucket `rate_limit.py`, `citations.py` (`CitationProvider` base, `load_citation_provider()`, the shared `get_json`), visible-Chrome helpers (`webrunner_browser.py`, `webrunner_pdf.py`) |
| `thesisagents/sources/<name>/` | One plugin per source: `__init__.py` exposes `fetcher_class`, `fetcher.py`, `parser.py`; browser-backed sources (`ieee`, `scholar`) add `webrunner_backend.py`, and sources with citation data (`openalex`, `semantic_scholar`, `crossref`) add `citations.py` exposing `citation_provider_class` |
| `thesisagents/exporters/` | `Exporter` strategies (`pptx`, `xlsx`, `bibtex`, `markdown`, `json`, `ris`, `csv`, `csl`) and the `_REGISTRY` in `__init__.py`; `pptx_edit.py`, `review.py` / `audit.py` / `overflow.py` (deck audits), `i18n.py` (deck strings), `template.py` (the deck template contract: layout per slide role, `TemplateConfig`, `validate_template`) |
| `thesisagents/library/` | Literature library kept across runs in one SQLite file: `store.py` (`Library`: merge an import on the identity keys of `core/dedup.py`, search with `rank_with_scores`, `LibraryVerificationCache` for the export preflight), `schema.py` (tables, `SCHEMA_VERSION`, migrations). Reads and writes the core models, and nothing in `core/` imports it |
| `thesisagents/intelligence/` | PDF text / asset / metadata extraction and the API summariser (`summarise.py`), `[intelligence]` extra |
| `thesisagents/mcp/` | FastMCP server (`server.build_server()`, with the library tools in `library_tools.py`), `[mcp]` extra (held below mcp 2.0, which renamed FastMCP) |
| `thesisagents/gui/` | PySide6 desktop app (`app.py`, `main_window.py`, `pages/`, `workers.py` on `QThreadPool`, `i18n.py`), `[gui]` extra |
| `thesisagents/evaluation/` | Offline search-quality benchmark (`search_quality.py`; see `docs/search-quality.md`) |
| `thesisagents/utils/` | Logging, path safety, and `async_helpers.run_blocking` (finish a coroutine from synchronous code, inside or outside a running loop) |
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
  overrides), and two that read a literature library instead of searching: `--library-search QUERY`
  and `--library-export [QUERY]`. Source and output control: `--source/-s`, `--exclude-source/-x`, `--max/-n`,
  `--year-from`, `--year-to`, `--min-citations`, `--top-tier-only`, `--export/-e`, `--out/-o`,
  `--filename-stem`, `--lang/-l`, `--enrich`, `--llm-model`, `--lightweight`, `--max-slides`,
  `--dark-mode`, `--no-pdf`, `--no-oa-resolve`, `--no-verify-identifiers`, `--diagnostics`,
  `--snowball` (with `--snowball-seeds`, `--snowball-depth`, `--snowball-max-per-seed`,
  `--snowball-max-total`, `--snowball-min-relevance`), `--library PATH` (the library file, also the
  run's identifier cache) with `--library-add`, `--pptx-template FILE` with
  `--pptx-template-config FILE`, `--paywall-threshold`,
  `--yes/-y`, `--quiet`.
  Discovery: `--list-sources`, `--list-exports`. Subcommands: `review <deck.pptx>`
  (`exporters/review.py`), `validate-template <template.pptx>` (`exporters/template.py`), `gui`.
  Reference: `docs/cli.md`.
- **MCP**: `thesisagents-mcp` (`thesisagents/mcp/__main__.py`). Tools cover discovery (`list_sources`,
  `list_exports`), `search`, `snowball`, `library_add`, `library_search`, `library_stats`, `fetch_paper`,
  `fetch_pdf_text`, `download_pdfs`, `pptx_validate_template`, `export`, and deck
  tools `pptx_inspect`, `pptx_review`, `pptx_update_slide`, `pptx_delete_slide`,
  `pptx_reorder_slides`, `pptx_add_slide`. Stateless across calls: what should outlast a session goes
  into a library file the caller names. Reference: `docs/mcp.md`.
- **GUI**: `thesisagents-gui` (`thesisagents.gui.app:main`), or `thesisagents` with no arguments.
- **Library**: `thesisagents.core.pipeline.run_search(query)` and
  `thesisagents.exporters.export_collection(collection, ExportOptions(...))`. The export verifies
  every DOI / URL first and raises `IdentifierVerificationError` on a wrong or unreachable one,
  unless `ExportOptions(verify_identifiers=False)`. `thesisagents.library.Library(path)` keeps
  collections across runs (`add_collection`, `search`, `collection`, `verification_cache`).
- **Configuration** (env vars): `ANTHROPIC_API_KEY`, `THESISAGENTS_CONTACT_EMAIL`,
  `THESISAGENTS_SPRINGER_API_KEY`, `THESISAGENTS_CORE_API_KEY`, `THESISAGENTS_IEEE_API_KEY`,
  `THESISAGENTS_DISABLE_IEEE_SCRAPING`, `THESISAGENTS_DISABLE_SCHOLAR_SCRAPING`,
  `THESISAGENTS_DISABLE_WEBRUNNER`. Reference: `docs/configuration.md`.
- **Build / release**: `pyproject.toml` extras (`mcp`, `intelligence`, `gui`, `web`, `dev`);
  `docs/packaging-nuitka.md`, `docs/packaging-pyinstaller.md`; `.github/workflows/ci.yml`, `release.yml`.
  The `publish-pypi` job of `release.yml` holds the PyPI token and installs nothing but
  `.github/requirements/publish.txt` (`build`, `twine`, and the build backend `setuptools`, `wheel`):
  wheels only, at locked hashes, generated from `publish.in` beside it. It builds with
  `python -m build --no-isolation`, so the backend is the locked one and not a fresh download.
  `tests/test_workflow_actions.py` fails when that job runs any other `pip install`, builds with
  isolation, or when the lock does not satisfy `[build-system] requires` of `pyproject.toml`.
  Reference: `docs/releases.md`.

## 4. Main flows

**Query → sources → dedup / rank → exporters**

```
Query (CLI flags / MCP search / GUI / library)
  → core.pipeline.run_search
  → fetchers.base.load_fetcher(name) for each source      (imports thesisagents.sources.<name>)
  → asyncio.gather over Fetcher.fetch, one outcome per source (per-source token bucket, HTTPS-only client;
                                                            ieee / scholar via visible Chrome)
  → parser → list[Paper] → core.dedup → core.ranking (score per paper kept) → Query filters
  → core.pruning (advisory keep / review / prune, nothing removed) → PaperCollection.diagnostics
  → optional core.snowball (top results → CitationProviders → more papers, each with its path)
  → core.oa_resolver (fills pdf_url) → optional PDF download → optional enrichment → PaperCollection
  → optional library.Library.add_collection (--library-add: merge into the SQLite library)
  → exporters.export_collection
      → core.export_validation (identifier preflight: DOI at doi.org, URL once; a failure stops here)
      → _REGISTRY[format] → files under --out
          pptx with a template: exporters.template.open_template validates it first, then every
          slide takes the layout of its role (cover / section / content / table / references / qa)
```

A failing source returns nothing and never breaks the others, and the search records what each
source returned and why a source came back empty (`PaperCollection.diagnostics.source_stats`,
printed by the CLI and returned by the MCP `search` tool). The CLI runs the identifier preflight
right after the search, before PDF download and enrichment, and reuses its verdicts for every
export call of the run. With `--library` the verdicts are kept in the library, and one that let an
export through is reused by later runs for 30 days.

**Library → exporters**: `--library-search` and `--library-export` (MCP `library_search`) read the
library instead of running a search. `Library.collection()` returns a `PaperCollection`, which then
goes through the same preflight and exporters. When the paywalled share of a result
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
- **New citation provider**: add `thesisagents/sources/<name>/citations.py` with a `CitationProvider`
  subclass, expose it as `citation_provider_class` in the plugin's `__init__.py`, and add the name to
  `DEFAULT_CITATION_PROVIDERS` in `thesisagents/core/constants.py` if it should be asked by default.
  Guide: [`docs/source_plugins.md`](docs/source_plugins.md) "Adding a citation provider".
- **New library schema version**: append one migration function to `MIGRATIONS` in
  `thesisagents/library/schema.py` and raise `SCHEMA_VERSION`. Never edit a migration that has
  shipped, libraries in the field have already run it. `tests/test_library.py` shows the pattern.
- **New exporter**: subclass `Exporter` (`thesisagents/exporters/base.py`), add an `EXPORT_*` name in
  `thesisagents/core/constants.py`, and register it in `_REGISTRY` in `thesisagents/exporters/__init__.py`.
- **New deck template setting**: add it to `TemplateConfig` and its parser in
  `thesisagents/exporters/template.py`, apply it as a post-build pass in
  `thesisagents/exporters/pptx.py` (the way `_apply_template_palette` does), and document it in
  [`docs/pptx_templates.md`](docs/pptx_templates.md). A new slide role is a new entry in `ROLES`
  plus the `role=` argument at the builder that makes those slides.
- **New MCP tool**: add it in one of the `_register_*` functions called by
  `thesisagents/mcp/server.py::build_server()`, or in a module of its own registered from there
  (`thesisagents/mcp/library_tools.py` is the example).
- **New localised string**: `thesisagents/exporters/i18n.py` (decks) or `thesisagents/gui/i18n.py`
  (UI); every supported language must be filled (`tests/test_i18n.py`, `tests/gui/test_i18n.py`).
- **New summary field**: `PaperSummary` in `thesisagents/core/models.py`, consumed by the thesis-style
  tier in `thesisagents/exporters/pptx.py`.

## 6. Cross-project boundaries

- No dependency on the workspace's WebRunner project: `thesisagents/fetchers/webrunner_browser.py`
  drives Selenium directly with one Chrome per call, because WebRunner's module-level driver
  singleton breaks concurrent sources. `selenium>=4.11` is declared directly; the module and the
  `THESISAGENTS_DISABLE_WEBRUNNER` variable keep their historical names.
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
- No live network in tests (`tests/conftest.py` refuses it); all HTTP through `get_client(source)` or
  `scoped_client(source)` (both HTTPS-only); slide geometry guards
  (`AGENTS.md` "Other rules you will trip on").
- Core versus source-plugin split is about dependency surface and failure isolation
  (`docs/architecture.md` "Core vs source plugins").

## 8. When to update this file

- A subpackage or surface (CLI, MCP, GUI, library) is added, removed or renamed.
- The pipeline stage order changes (fetch, dedup, rank, snowball, OA resolution, download, enrichment,
  library merge, export).
- Source or exporter registration, MCP tool registration, or the i18n contract changes.
- Console scripts, extras, CLI modes / subcommands or configuration env vars change.
- A cross-project link in §6 changes (WebRunner dependency, prthinker manuscript provenance).
- The currently uncommitted modules are committed, moved or dropped.
- Update the "Last verified" line with the date and commit whenever this file is revised.
