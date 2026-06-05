# Desktop GUI (PySide6)

ThesisAgents ships an optional desktop interface built on
[PySide6](https://doc.qt.io/qtforpython-6/). It wraps the existing
CLI flow (search → results table → export) in a window so users who
don't want a terminal can still drive the project.

## Install

The GUI is gated behind a separate extra to avoid forcing PySide6
(~80 MB) on CLI / MCP users who don't need it:

```powershell
pip install thesisagents[gui]
```

If you also want the rich-tier enrichment path:

```powershell
pip install thesisagents[gui,intelligence,mcp]
```

## Launch

Three equivalent entry points:

```powershell
thesisagents-gui                    # PyPI console script
thesisagents gui                    # CLI subcommand
py -m thesisagents gui              # module entry, useful while developing
```

The Windows release `.exe` also accepts `thesisagents.exe gui` —
the bundle includes PySide6 and the source plugins so no extra
install is needed.

## Tabs

The window has four tabs. **All four are functional in this release.**

### Search

The core search → export flow.

- **Query** — keyword string (UTF-8; CJK works).
- **Sources** — checkbox grid; pre-selected to the same default set
  as the CLI (`arxiv`, `semantic_scholar`, `openalex`, `pubmed`,
  `dblp`, `crossref`, `openaire`). Opt-in plugins (`scholar`,
  `ieee`) are unchecked until you tick them and have the
  corresponding env var set in **Settings**.
- **Slide language** — picks the language for any `.pptx` exported
  from this run. Defaults to English.
- **Max results per source** — 1 … 200 (same as the CLI `--max`).
- **Year from / Year to** — leave at `—` to disable.
- **Top-tier venues only** — mirrors the CLI's default; un-tick to
  keep every result.

Press **Search**. The query runs on a worker thread so the UI stays
responsive; the status bar reports progress and the results table
populates when the run finishes.

Press **Export…**, pick an output directory, and the standard
`.pptx` + `.xlsx` + `.bib` triple lands there.

### Settings

API keys, contact email, cookies file, and UI language are stored
locally via Qt's
[`QSettings`](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QSettings.html)
(Windows registry, macOS plist, Linux ini). Saving a value also
exports the matching environment variable into the current process,
so the source plugins pick it up without a shell restart.

Fields:

| UI label | Env var written |
|---|---|
| Anthropic API key | `ANTHROPIC_API_KEY` |
| Semantic Scholar API key | `THESISAGENTS_S2_API_KEY` |
| NCBI / PubMed API key | `THESISAGENTS_NCBI_API_KEY` |
| IEEE Xplore API key | `THESISAGENTS_IEEE_API_KEY` |
| Springer Nature API key | `THESISAGENTS_SPRINGER_API_KEY` |
| Crossref Plus token | `THESISAGENTS_CROSSREF_PLUS_TOKEN` |
| Contact email | `THESISAGENTS_CONTACT_EMAIL` |
| PDF cookies file | `THESISAGENTS_PDF_COOKIES_FILE` |

Empty values clear the corresponding env var. **Restart the app**
to refresh fetcher singletons that cached the env value at
construction time.

### Enrich

Drives the per-paper PDF + LLM enrichment step. The Search tab emits
a `collection_ready` signal as soon as the results table populates;
the Enrich tab catches it and renders a per-paper row showing:

- The paper's BibTeX key + title (clickable → opens the URL).
- A **PDF** column — green tick when a `pdf_url` is on file (Unpaywall
  / S2 / arXiv / CORE.ac.uk lifted it), grey dash otherwise.
- An **Enrich** action that runs either the Python pipeline
  (Anthropic API, needs `ANTHROPIC_API_KEY` in Settings) or surfaces
  the LLM-as-agent path for runs without an API key.
- A progress strip across the bottom — the worker reports the current
  paper, elapsed seconds, and a per-paper success/failure tally.

Authored summaries are merged back onto the in-memory `PaperCollection`,
so a subsequent **Export** picks up the rich-tier layout automatically.

### Deck

The pre-export deck-shaping controls. Wires `ExportOptions` fields
behind Qt widgets:

- **Light mode** checkbox — unchecked (default) ships the dark deck
  (slide bg `#12151B`, body text `#E5E7EB`, brighter teal accent
  `#2DD4BF`). Tick it for the printable / well-lit-room variant
  (white bg + navy text). Mirrors the CLI `--light-mode` flag.
- **Max slides per paper** — integer spinner. Defaults to 25;
  `0` means unlimited.
- **Max figures per paper** — controls how many `figures=` entries the
  rich-tier layout actually renders. The priority trim keeps the
  cover / references / contributions slides intact and drops Q&A /
  figure / paper-table slides first when the cap kicks in.
- **Include abstract** checkbox — when off, the deck skips the
  abstract slide entirely (useful for an "executive overview only"
  variant).

The PPTX inspector / editor surface (drives `pptx_inspect` /
`pptx_update_slide` / `pptx_reorder_slides` / `pptx_delete_slide` /
`pptx_add_slide`) is wired to the same shape names the exporter
produces — `title`, `meta`, `body`, `kpi`, `rq_question`, `figure`,
`accent_top`, `accent_left` — so the editor list view labels each
slide by its semantic role rather than by raw shape index.

## i18n

The UI ships in **all 14 languages** that the slide-deck exporter
supports: English, 繁體中文, 简体中文, 日本語, Español, Français,
Deutsch, 한국어, Português, Русский, Italiano, Tiếng Việt, हिन्दी,
Bahasa Indonesia.

Pick the language under **Settings → Interface language** (the
dropdown shows each language in its own script). Restart the app
to apply.

First-run behaviour: if no language is saved yet, the app reads
the OS locale via `QLocale().name()` and maps it to the closest
supported code (e.g. `zh_TW` → `zh-tw`, `es_ES` → `es`,
`zh-Hant-TW` → `zh-tw`). Unsupported locales fall back to English.

Two separate i18n tables live in the repo:

- `thesisagents/gui/i18n.py` — UI labels (this page).
- `thesisagents/exporters/i18n.py` — slide-deck output strings.

They're kept in lockstep by `tests/gui/test_i18n.py::test_supported
_languages_match_deck_table`. Adding a key is a single-file change;
the per-key, per-language coverage test catches any missing entry
at PR time.

## Responsive layout & HiDPI

- The window has a minimum size of 900×600 (still fits a 720p
  laptop) and a default of 1280×800.
- Each tab page lives inside a `QScrollArea` with
  `widgetResizable=True`, so the form widgets stretch horizontally
  with the window width and reveal a vertical scrollbar when the
  window shrinks below the form's natural height.
- HiDPI scaling is enabled at boot via
  `QT_ENABLE_HIGHDPI_SCALING=1` and
  `QT_SCALE_FACTOR_ROUNDING_POLICY=PassThrough`. Both are set
  *before* `QApplication` is constructed, which is the only safe
  time to pin them.
- The default font is bumped to point size 10 (Qt's platform
  default is 8 on some Windows machines) so CJK glyphs stay
  readable on dense screens. The font family list includes
  Windows-shipped CJK / Devanagari fallbacks (Microsoft JhengHei
  UI, Yu Gothic UI, Malgun Gothic, Nirmala UI) so a missing glyph
  in the primary font cascades cleanly rather than rendering a
  tofu box.

## Threading model

Every backend call runs off the main thread:

- `AsyncWorker` wraps a coroutine factory and calls `asyncio.run`
  inside `QRunnable.run` — used for `run_search`, single-paper
  fetches, anything that touches `httpx.AsyncClient`.
- `BlockingWorker` wraps a plain function — used for
  `export_collection`, which renders the `.pptx` via python-pptx.

Both emit `finished(object)` / `failed(object)` signals on
completion; the receiving slot lives on the main thread so it can
update widgets safely.

## Testing the GUI

The test suite under `tests/gui/` uses `pytest-qt` (installed by
the `[dev]` extra). It mocks the backend so no live HTTP is made:

```powershell
pip install -e ".[dev]"
py -m pytest tests/gui/
```

Tests fall into three families: i18n coverage, Qt model behaviour,
and page-level wiring (a search button click populates the table,
the export button stays disabled until results arrive, settings
round-trip through QSettings).

## Known limitations

- The Settings page does not validate keys against the live API —
  validation would leak the key into HTTP logs and slow down save.
  An invalid key surfaces later as a `ConfigError` / 401 from the
  relevant source plugin.
- The window does not yet remember its size / position between
  runs. Add `QMainWindow.saveGeometry` / `restoreGeometry` if you
  want that.
