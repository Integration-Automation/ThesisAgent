# Desktop GUI (PySide6)

AutoPaperToPPT ships an optional desktop interface built on
[PySide6](https://doc.qt.io/qtforpython-6/). It wraps the existing
CLI flow (search → results table → export) in a window so users who
don't want a terminal can still drive the project.

## Install

The GUI is gated behind a separate extra to avoid forcing PySide6
(~80 MB) on CLI / MCP users who don't need it:

```powershell
pip install autopapertoppt[gui]
```

If you also want the rich-tier enrichment path:

```powershell
pip install autopapertoppt[gui,intelligence,mcp]
```

## Launch

Three equivalent entry points:

```powershell
autopapertoppt-gui                    # PyPI console script
autopapertoppt gui                    # CLI subcommand
py -m autopapertoppt gui              # module entry, useful while developing
```

The Windows release `.exe` also accepts `autopapertoppt.exe gui` —
the bundle includes PySide6 and the source plugins so no extra
install is needed.

## Tabs

The window has four tabs. The first two are functional in this
release; the other two are placeholders that will land in a
follow-up.

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
| Semantic Scholar API key | `AUTOPAPERTOPPT_S2_API_KEY` |
| NCBI / PubMed API key | `AUTOPAPERTOPPT_NCBI_API_KEY` |
| IEEE Xplore API key | `AUTOPAPERTOPPT_IEEE_API_KEY` |
| Springer Nature API key | `AUTOPAPERTOPPT_SPRINGER_API_KEY` |
| Crossref Plus token | `AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN` |
| Contact email | `AUTOPAPERTOPPT_CONTACT_EMAIL` |
| PDF cookies file | `AUTOPAPERTOPPT_PDF_COOKIES_FILE` |

Empty values clear the corresponding env var. **Restart the app**
to refresh fetcher singletons that cached the env value at
construction time.

### Enrich (coming soon)

Per-paper PDF + LLM enrichment will land here. For now: set
`ANTHROPIC_API_KEY` in **Settings**, run a search, then export —
the CLI side auto-enriches each paper that has a downloadable PDF.

### Deck (coming soon)

PPTX inspector / editor. The MCP server already exposes
`pptx_inspect` / `pptx_update_slide` / `pptx_reorder_slides` /
`pptx_delete_slide` / `pptx_add_slide`; this tab will wire them
behind a Qt list view + form panel.

## i18n

The UI labels ship in **English** and **Traditional Chinese**.
Pick the language under **Settings → Interface language**;
re-launch to apply.

Adding a new language is a single-file change to
`autopapertoppt/gui/i18n.py` — extend each `_LABELS` entry with a
new code, then `tests/gui/test_i18n.py` will tell you which keys
are still missing.

The slide-deck output language (the strings that render *inside*
the generated `.pptx`) is a separate 14-language table at
`autopapertoppt/exporters/i18n.py`. Decoupling the two lets the
UI ship with fewer translations while still emitting decks in any
of the supported deck languages.

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
- High-DPI scaling follows Qt's defaults; on Windows you may want
  to set `QT_ENABLE_HIGHDPI_SCALING=1` before launching for
  blurry-text fixes on fractional scale factors.
