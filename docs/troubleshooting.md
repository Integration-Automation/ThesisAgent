# Troubleshooting

Failure modes you may hit, what each one means, and how to fix it.
Issues are grouped by where they surface.

## Install / import errors

### `error: Microsoft Visual C++ 14.0 or greater is required` (Windows)

A wheel for one of the deps wasn't found and pip tried to build
from source. Confirm:

```powershell
python --version    # must be 3.12 / 3.13 / 3.14
```

If you're on a prerelease Python, downgrade to a supported version
or install the MSVC C++ Build Tools.

### `ImportError: libEGL.so.1: cannot open shared object file` (Linux)

PySide6 needs Qt's system libraries. On Debian / Ubuntu:

```bash
sudo apt-get install -y \
    libegl1 libgl1 libxkbcommon0 libxkbcommon-x11-0 \
    libdbus-1-3 libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
    libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
    libxcb-shape0 libxcb-xinerama0 libxcb-xkb1 libfontconfig1
```

For headless CI, also set `QT_QPA_PLATFORM=offscreen`.

### `ModuleNotFoundError: No module named 'pptx'`

The core install lost `python-pptx`. Reinstall:

```bash
pip install --force-reinstall python-pptx>=0.6.23
```

The PyPI package name is `python-pptx`; the importable module name
is `pptx` (PyPI ↔ module mismatch is intentional from python-pptx).

### `ModuleNotFoundError: No module named 'PySide6'`

The GUI extra is not installed. Run:

```bash
pip install "thesisagents[gui]"
```

If you're using the Windows release `.exe`, this means the bundle
was built without `[gui]` — re-download the latest release zip.

### `ModuleNotFoundError: No module named 'thesisagents.gui'` from `thesisagents gui`

Same root cause. The `gui` subcommand short-circuits to a helpful
error when this happens; if you see the bare `ModuleNotFoundError`
you may be hitting an older release.

## CLI errors

### `error: refusing non-HTTPS request`

A source plugin or test pointed the HTTP client at an `http://`
URL. By design the project never makes plain-HTTP requests, even
after a redirect. Fix the source's URL — never bypass the
HTTPS-only transport.

### `error: could not classify identifier`

The `--paper` argument was not recognised as an arXiv ID, arXiv
URL, DOI, PMID, or IEEE document URL. Accepted forms:

```
2401.08741                                  # bare arXiv
2401.08741v2
arXiv:2401.08741
https://arxiv.org/abs/2401.08741
https://arxiv.org/pdf/2401.08741v2.pdf
cs.LG/0001001                               # legacy arXiv

10.1234/example
doi:10.1234/example
https://doi.org/10.1234/example

34567890
https://pubmed.ncbi.nlm.nih.gov/34567890/

https://ieeexplore.ieee.org/document/10965643
```

### `error: no source plugin available yet for <kind> identifiers`

The identifier parsed correctly but no plugin can resolve that kind.
Today this only fires for DOIs that don't have a Semantic Scholar /
Crossref hit. Workarounds:

- Use the arXiv version if the paper has one (`arxiv.org` mirror).
- Search by query instead of by paper.

### A search returns fewer papers than expected

Look at the `Sources` table the CLI prints after the search (the MCP
`search` tool returns the same as `source_stats`):

```
Sources (up to 25 requested from each):
  arxiv      23 returned, 23 after dedup
  openalex   25 returned, 21 after dedup
  dblp        0 returned, 0 after dedup
  ieee        0 returned  failed: [ieee] search page returned HTTP 403
  springer    0 returned  disabled: THESISAGENTS_SPRINGER_API_KEY is not set
```

| What the table shows | Cause | What to do |
|---|---|---|
| `failed: ...` | The source raised an error: a block page, a changed response format, a network failure. | Read the message. For `ieee` and `scholar`, check that a Chrome window opened and that VPN / institutional access is active. |
| `rate_limited: ...` | The source answered HTTP 429 through every retry. | Wait and run again, or set the source's API key (`THESISAGENTS_S2_API_KEY` for Semantic Scholar). |
| `disabled: ...` | The plugin could not be loaded, usually a missing API key (`springer`, `core`). | Set the variable named in the message, or ignore the source. |
| `0 returned, 0 after dedup` | The source answered and had nothing for this query. | Nothing is wrong. Try broader keywords. |
| `returned` far above `after dedup` | Most of the source's records duplicated an earlier source's. | Nothing is wrong. The source adds little for this query. |

A source that fails is skipped without stopping the search, so the
result list alone cannot tell a narrow topic from a search that lost
half its sources.

### `error: Unknown source(s): <name>`

You passed `--source` a name not in `ALL_SOURCES`. The valid set:

```
arxiv, semantic_scholar, openalex, pubmed, acm, dblp,
crossref, openaire, europepmc, doaj, hal, ieee, springer,
core, scholar
```

### `Lightweight deck — no ANTHROPIC_API_KEY in env.`

Informational, not an error. The CLI fell back to the abstract-only
lightweight deck because no API key was found and you didn't pass
`--enrich`. To upgrade:

- Set `ANTHROPIC_API_KEY` in the environment, or
- Run over MCP and let the LLM agent author the rich summary
  in-context (no key needed).

The full LLM-as-agent workflow is in
[AGENTS.md](../AGENTS.md) and the en docs index.

### `error: --enrich requires the [intelligence] extra`

`--enrich` needs `pypdf` + `anthropic` + `pymupdf`:

```bash
pip install "thesisagents[intelligence]"
```

### `Warning: 18/20 papers (90%) have no public PDF URL`

Most of the result set is paywalled. The CLI's paywall gate
fires when >30% of papers have `pdf_url=None`. You'll be asked
whether to continue:

```
Continue and generate slides for the 2 accessible paper(s)? [y/N]:
```

Bypass options:

- `--yes` to accept automatically (good for unattended runs).
- `--paywall-threshold 0.95` to disable the warning (bad — you'll
  generate empty decks for paywalled papers).
- Switch sources to ones with more open access (`arxiv`,
  `openalex`, `openaire`, `pubmed`, `europepmc`, `doaj`, `hal` —
  the last three are open by definition and usually carry a direct
  PDF link).

### `arXiv rate-limit hits`

The bundled token bucket already paces requests at 1 / 3s. If
you're still seeing 429s:

- You may be running multiple ThesisAgents processes in parallel
  against the same arXiv endpoint. Coordinate through a single
  process or lower `--max`.
- Confirm no proxy / VPN is rewriting your client IP into a
  shared pool that other arXiv users are hitting.

### `Springer plugin raises ConfigError`

The plugin requires `THESISAGENTS_SPRINGER_API_KEY` at
construction. With the key unset, the pipeline silently skips
Springer; with `--source springer` explicitly requested, the
error surfaces. Get a free key at
<https://dev.springernature.com/>.

### `error: --pdf path does not exist`

The path passed to `--pdf` resolves to nothing. Confirm the file
exists and the path is absolute or relative to your current
directory. The `--pdf` flag accepts either one `.pdf` or a
directory of them.

### `error: no library at <path>`

`--library-search` and `--library-export` (and the MCP `library_search`
/ `library_stats` tools) read a library, and the path does not exist. A
read never creates the file, so a mistyped path is an error and not an
empty result. Check the path. A library is created the first time
papers are added to it, with `--library PATH --library-add` or the
`library_add` tool.

### `error: <path> is not an SQLite database` / `is not a ThesisAgents library`

The `--library` path exists and is something else: a text file, a
directory, or another application's database. The file is left
untouched. Point `--library` at another path. A new library is created
when the path does not exist yet.

### `error: <path> has library schema version N, and this ThesisAgents understands up to version M`

The library was written by a newer ThesisAgents than the one running.
It is not opened, because the newer layout could be misread. Upgrade
ThesisAgents (`pip install -U thesisagents`), or point `--library` at
another file. The opposite case needs nothing: an older library is
upgraded in place when it is opened.

### An export keeps checking the same DOIs and URLs

Without `--library`, the identifier check starts from nothing on every
run. Name a library (`--library thesis.db`, or `library=` on the MCP
`export` tool) and a DOI or URL that verified is not checked again for
30 days. Identifiers reported as *not checkable* are remembered the
same way. A failed check is made again on every run by design, so an
export that failed while the network was down succeeds once it is back.

### `error: --pdf file is empty / not a PDF / encrypted`

The pre-flight check rejected the file. Encrypted PDFs need
decryption first (`qpdf --decrypt in.pdf out.pdf` or
`pdftk in.pdf input_pw=password output out.pdf`); empty / 0-byte
files indicate a failed prior download.

## MCP errors

### MCP client doesn't see any tools

Check the MCP server can be built locally:

```bash
python -c "from thesisagents.mcp import build_server; import asyncio; \
    print(sorted(t.name for t in asyncio.run(build_server().list_tools())))"
```

You should see all 12 tool names. If the import itself fails, the
`[mcp]` extra is not installed:

```bash
pip install "thesisagents[mcp]"
```

Then re-add the MCP server in your client config:

```powershell
claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp
```

### `download_pdfs` returns mostly `skipped`

A paper's PDF URL was missing (`pdf_url=None`) or the download
failed. The result entry has a `skipped_reason`:

| Reason | Fix |
|---|---|
| `no_pdf_url` | The source didn't surface a PDF link. Try IEEE/Springer keys, or accept the gap. |
| `unsupported_scheme` | The URL wasn't HTTPS. The HTTPS-only transport refuses it. |
| `http_<code>` | Network error. 403 = paywall (set up cookies file), 404 = stale URL, 5xx = retry later. |
| `too_large` | PDF exceeded the 100 MB safety cap. Increase locally or skip the paper. |

### `fetch_pdf_text` returns truncated text

`pypdf` (the default extractor) sometimes fails on scanned PDFs
with bad metadata. Workarounds:

- Install the `[intelligence]` extra so `pymupdf` becomes
  available as a fallback (higher fidelity).
- For scanned PDFs, OCR first with an external tool
  (`ocrmypdf in.pdf out.pdf`).

## PPTX / export errors

### `error: [preflight] identifier verification failed for N identifier(s)`

The export checks every paper's DOI and URL before it writes anything
(see [`cli.md`](cli.md) "Identifier verification"). Each line under the
error names one paper, one identifier, and why it failed:

| Reason shown | Cause | Fix |
|---|---|---|
| `is invalid (not a DOI: expected the form 10.<registrant>/<suffix>)` | The `doi` field is not a DOI, for example a URL fragment or a truncated value. | Copy the DOI from the search `.xlsx` (column 7). |
| `is invalid (doi.org has no such DOI registered)` | The DOI is well-formed but does not exist. Usually it was typed or composed, not copied. | Copy it from the search results. |
| `is invalid (HTTP 404: the page does not exist)` | The URL is dead or was guessed. Publisher URL paths cannot be derived from a title. | Copy the URL from the search `.xlsx` (column 8). |
| `is unreachable (ConnectError: …)` | The host does not resolve or refuses connections. A made-up domain fails this way, and so does every identifier when the machine is offline. | Check the URL. When offline, pass `--no-verify-identifiers`. |
| `is timeout (no answer within 8 s)` | The host did not answer, after one retry. | Run again, or pass `--no-verify-identifiers` if the host stays slow. |

Nothing is written when this error appears, so there is no partial
export to clean up.

An identifier reported as `skipped` is not an error. It means the check
could not be made: the URL is on a publisher host that only answers a
real browser, or the server refuses automated access (HTTP 401 / 403 /
429). The run continues.

### Export passes but a DOI points at the wrong paper

The preflight proves that an identifier exists. It cannot tell that the
DOI belongs to a different paper than the one it is attached to. Copy
`doi` / `url` / `arxiv_id` from the search results that produced the
run, and run the audit in `AGENTS.md` "URL / DOI verification" on any
hand-authored `scripts/regen_*.py`.

### `error: [pptx] template ... does not meet the template contract`

The file passed as `--pptx-template` (or `pptx_template`) cannot be
used as it is. The lines under the message each name one problem and
the change that fixes it: slides that are not 16:9 with
`slide_size = "reject"`, a layout name in `[layouts]` the template
does not have (the message lists the ones it has), no layout for slide
content, or a title placeholder that `[placeholders] title` asks for
and the layout lacks. Run `thesisagents validate-template FILE
--config CONFIG` to see the same report without starting a run. See
[Deck templates](pptx_templates.md).

### A template deck shows the template's artwork off-centre

The template is 4:3 (or another size) and was resized to 16:9, which
the run reports as `Template warning: the template's slides are ...`.
Artwork keeps the position it had on the narrower slide. Save a 16:9
version of the template in PowerPoint (Design > Slide Size) and use
that.

### Titles are invisible on a template deck

Slide titles are white because they sit on the exporter's navy header
band. If the template covers that band with its own artwork, switch
the band off in the config (`[chrome] header_band = false`), which
also sets the titles in the `primary` colour, or send the titles into
the template's title placeholder (`[placeholders] title = ["content",
"table", "references"]`).

### `Slide overflowed the footer guard at 7.05"`

A text box rendered taller than the 7.05" cap. Causes:

- A hand-authored `PaperSummary` with too many entries in one
  section (`contributions_detailed > 4`, `method_sections > 2`
  per slide, etc.).
- A custom shape added via `pptx_edit.add_slide` without
  considering the footer guard.

Run the headless overflow check:

```bash
python -c "from thesisagents.exporters.pptx import inspect_overflow; \
           inspect_overflow('exports/your.pptx')"
```

It lists every shape that overflows and by how much.

### `BibTeX key collision`

The pipeline's collision counter normally handles this by
suffixing `a`, `b`, `c`. If you see a collision error from
`bibtexparser`, you may have an upstream bug — file an issue
with the keys involved.

### Excel "Source" column shows `openalex` for a Nature paper

The column was renamed in commit `<earlier>`. **Source** (column 5)
is the real publication venue (`Nature`); **Indexed via** (column
6) is the fetcher plugin (`openalex`). Make sure your reader is
showing both columns, not just one.

## GUI errors

### Window opens but text is blurry on a HiDPI display

Set environment variables before launching:

```powershell
$env:QT_ENABLE_HIGHDPI_SCALING = "1"
$env:QT_SCALE_FACTOR_ROUNDING_POLICY = "PassThrough"
thesisagents gui
```

These are also pinned by `app.py` if unset, but a host
override of either to a wrong value can cause this symptom.

### `tofu` boxes for some characters

The font fallback chain didn't include a family with that
character's glyphs. The bundled chain covers Latin / CJK /
Devanagari on Windows. On Linux / macOS:

- Install Noto fonts (`apt-get install fonts-noto-cjk fonts-noto-color-emoji`).
- The bundled chain already references common Windows family names —
  these don't exist on Linux / macOS, so Qt falls back to its own
  default which should pick Noto when installed.

### Settings page values don't persist between launches

QSettings can't write its store. Check:

- Linux: `~/.config/ThesisAgents/` exists and is writable.
- macOS: `~/Library/Preferences/` is writable.
- Windows: registry write permission on
  `HKCU\Software\ThesisAgents`.

### `Search` button does nothing

Open the developer console (or run with
`THESISAGENTS_LOG_LEVEL=DEBUG`) and check for:

- An empty Sources selection — the page silently rejects because
  the search would have no targets.
- An empty query after whitespace trim — same.

The status label below the table shows the validation message in
both cases.

### Window resize cuts off form fields

Check you're on a version that includes the `QScrollArea`
wrapping (introduced in commit `1bb3913`). Each form sits in a
scroll area that exposes a vertical scrollbar when content exceeds
the available height.

## CI / Release errors

### Nuitka build timed out

The PySide6 cold build is heavy (~80-90 min on a GitHub Windows
runner). `release.yml` caps the job at 120 min. If you're forking and
seeing this on your fork's CI:

- Make sure your fork inherits the 120-min cap and the
  `NUITKA_CACHE_DIR` setting from `release.yml`.
- Subsequent runs should hit the Nuitka cache. If the Nuitka log ends
  with `Compiled N C files using clcache with 0 cache hits`, the cache
  step is not saving the directory `NUITKA_CACHE_DIR` points at.

### `Failed to locate package 'arxiv' you asked to include`

The build venv can't find `sources/<name>/` plugins because they
aren't installed packages. The fix in commit `ef1f52c` sets
`PYTHONPATH=sources` before invoking Nuitka. If you're on an
older release.yml, pull that change.

### `publish-pypi` succeeded but `publish-release` was skipped

`build-nuitka` failed somewhere; check its logs. Common causes
covered earlier in this doc (timeout, missing source plugin).
PyPI's version is published; the GitHub Release draft can be
deleted manually:

```bash
gh release delete v0.1.X --yes
```

## Test errors

### `RuntimeError: Event loop is closed` during `pytest`

A pre-existing test-isolation issue: an httpx client from an
earlier test outlives its asyncio loop, and a later test's
`asyncio.run` tries to close it. Fixed in commit `<sha>` —
`shutdown_clients()` now tolerates this. Pull latest if you
still see it.

### `pytest_configure INTERNALERROR ... libEGL.so.1`

pytest-qt imports `QtGui` at the `pytest_configure` hook, before
any test runs. Linux runner needs Qt's system libs (see Install
section above), AND `QT_QPA_PLATFORM=offscreen` in the test env.

### A specific GUI test passes locally but fails in CI

CI uses `QT_QPA_PLATFORM=offscreen`. If your test does anything
that the offscreen platform doesn't support (e.g. real window
geometry queries), pin the test to skip when offscreen:

```python
import os, pytest

@pytest.mark.skipif(
    os.environ.get("QT_QPA_PLATFORM") == "offscreen",
    reason="needs a real Qt platform",
)
def test_real_window_geometry(qtbot):
    ...
```

## Asking for help

If none of the above matches:

1. Run with `THESISAGENTS_LOG_LEVEL=DEBUG` to surface the full
   request / response cycle.
2. Copy the **smallest** reproducer (CLI command, MCP tool call
   sequence, or Python snippet) and the **complete** stack trace.
3. Open an issue at
   <https://github.com/Integration-Automation/ThesisAgents/issues>
   with the above + `python --version` + `pip freeze | grep -E
   "thesisagents|httpx|python-pptx|PySide6"`.
