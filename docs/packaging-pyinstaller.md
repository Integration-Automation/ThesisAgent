# Packaging with PyInstaller

[PyInstaller](https://pyinstaller.org/) bundles the interpreter, the
project, and all its dependencies into a single self-contained
executable. It is the right choice when you need to ship a binary
that runs on a machine without Python installed.

| Trade-off | Notes |
|---|---|
| Build time | Fast (under a minute on a warm cache). |
| Executable size | ~200–300 MB for this project (pulls in `lxml`, `python-pptx`, etc.). |
| Startup | 2–4 seconds — slower than running from source because the bundle has to unpack to a temp dir on each launch. |
| Cross-platform | You must build on the target OS. A Windows exe must be built on Windows, a macOS binary on macOS, etc. |
| Source protection | Low — the bundle is a zip; the `.pyc` files inside are easy to decompile. Use Nuitka if you want bytecode-level protection. |

## Install

PyInstaller is not in the standard dev extras — install it on demand:

```powershell
pip install pyinstaller
```

## The two project-specific gotchas

1. **Source plugins are loaded by name at runtime.** The pipeline calls
   `importlib.import_module("arxiv")` (and the other 10 source names)
   via `autopapertoppt.fetchers.base.load_fetcher`. PyInstaller's
   static analysis cannot see these imports, so without help it will
   tree-shake the source packages away. The fix is `--hidden-import`
   per source.

2. **The `sources/` directory must travel with the bundle.** The
   runtime computes `_SOURCES_DIR = Path(__file__).resolve().parents[2]
   / "sources"` to add it to `sys.path`. Inside a PyInstaller bundle,
   `__file__` points into the temp extraction dir, so the same
   relative path resolution still works **as long as you copy
   `sources/` into the bundle as data**. That's `--add-data`.

## Build the CLI (`autopapertoppt`)

```powershell
pyinstaller `
  --onefile `
  --name autopapertoppt `
  --paths sources `
  --add-data "sources;sources" `
  --hidden-import arxiv --hidden-import arxiv.fetcher --hidden-import arxiv.parser `
  --hidden-import semantic_scholar --hidden-import semantic_scholar.fetcher --hidden-import semantic_scholar.parser `
  --hidden-import openalex --hidden-import openalex.fetcher --hidden-import openalex.parser `
  --hidden-import pubmed --hidden-import pubmed.fetcher --hidden-import pubmed.parser `
  --hidden-import acm --hidden-import acm.fetcher --hidden-import acm.parser `
  --hidden-import ieee --hidden-import ieee.fetcher --hidden-import ieee.parser `
  --hidden-import scholar --hidden-import scholar.fetcher --hidden-import scholar.parser `
  --hidden-import dblp --hidden-import dblp.fetcher --hidden-import dblp.parser `
  --hidden-import crossref --hidden-import crossref.fetcher --hidden-import crossref.parser `
  --hidden-import openaire --hidden-import openaire.fetcher --hidden-import openaire.parser `
  --hidden-import springer --hidden-import springer.fetcher --hidden-import springer.parser `
  autopapertoppt/__main__.py
```

On Linux / macOS, replace the `;` separator in `--add-data` with `:`
(PyInstaller's argument separator follows the OS path separator):

```bash
pyinstaller \
  --onefile \
  --name autopapertoppt \
  --paths sources \
  --add-data "sources:sources" \
  --hidden-import arxiv ... \
  autopapertoppt/__main__.py
```

The output binary lands at `dist/autopapertoppt` (or
`dist/autopapertoppt.exe` on Windows).

## Build the MCP server (`autopapertoppt-mcp`)

```powershell
pyinstaller `
  --onefile `
  --name autopapertoppt-mcp `
  --paths sources `
  --add-data "sources;sources" `
  --hidden-import arxiv --hidden-import semantic_scholar `
  --hidden-import openalex --hidden-import pubmed `
  --hidden-import acm --hidden-import ieee --hidden-import scholar `
  --hidden-import dblp --hidden-import crossref `
  --hidden-import openaire --hidden-import springer `
  autopapertoppt/mcp/__main__.py
```

(The MCP entry point is `autopapertoppt.mcp.__main__:main` — see
`pyproject.toml`'s `[project.scripts]`.)

## Build with a `.spec` file (cleaner for repeated builds)

The flag-soup above is awkward to maintain. PyInstaller's first run
emits a `.spec` file; commit it so subsequent builds are one command.
A hand-tuned spec for this project:

```python
# autopapertoppt.spec
# Usage: pyinstaller autopapertoppt.spec
from PyInstaller.utils.hooks import collect_submodules

SOURCE_PLUGINS = (
    "arxiv", "semantic_scholar", "openalex", "pubmed", "acm",
    "ieee", "scholar", "dblp", "crossref", "openaire", "springer",
)

hidden = []
for plugin in SOURCE_PLUGINS:
    hidden.extend(collect_submodules(plugin))

a = Analysis(
    ["autopapertoppt/__main__.py"],
    pathex=["sources"],
    binaries=[],
    datas=[("sources", "sources")],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas,
    name="autopapertoppt",
    console=True,
    onefile=True,
    debug=False,
    strip=False,
    upx=False,
)
```

## Verify the executable works

```powershell
dist\autopapertoppt.exe --query "transformer" --source arxiv --max 3 `
                        --out .\smoke-pyinstaller\
```

Confirm:

- It runs without `ModuleNotFoundError` (your sources are bundled).
- `.pptx` + `.xlsx` + `.bib` land under `./smoke-pyinstaller/`.
- The deck is non-trivial (cover + agenda + result slides + references).

If you see `ConfigError: unknown or unavailable source plugin: arxiv`
— a source plugin wasn't bundled. Re-run with `--hidden-import` for
the missing module, or use the spec file approach.

## Optional dependencies (`[intelligence]`, `[mcp]`)

PyInstaller will bundle whatever's importable in your venv at build
time. To produce an exe that supports `--enrich`:

```powershell
pip install -e .[intelligence]
pyinstaller ... (same flags) ...
```

Then `dist\autopapertoppt.exe --query "..." --enrich` works
(provided `ANTHROPIC_API_KEY` is set in the env where the exe runs).

## Common issues

**`pymupdf` fails to import in the bundle**: pymupdf ships native
binaries that PyInstaller occasionally misses. Add
`--collect-binaries pymupdf` to pick up the `.so` / `.dll` files. If
the exe is for a machine that doesn't need figure extraction, omit
`[intelligence]` from the build venv and skip pymupdf entirely.

**`lxml` reports missing C extension**: pin to a wheel-based version
(`lxml>=5.2`, already in `pyproject.toml`). PyInstaller's lxml hook
in 6.0+ handles this; older PyInstaller versions need
`--collect-submodules lxml`.

**Bundle size matters**: the project ships ~200–300 MB by default
because `python-pptx` brings the full Office Open XML schema. Strip
unused branches with `--exclude-module tkinter --exclude-module
matplotlib --exclude-module pandas` (if you don't use the `[web]`
extra). Roughly 50 MB savings.

**Slow first launch**: this is `--onefile` extracting to a temp
directory. Drop `--onefile` for `--onedir` if you can ship a folder
instead of a single file — startup drops to under a second.

**Windows console encoding for CJK paper titles**: the bundled exe
inherits the system codepage. Run it with `python -X utf8` style
behaviour by wrapping with `chcp 65001 && dist\autopapertoppt.exe
...` or set `PYTHONUTF8=1` in the env.

## Verifying the same flow in CI

Once the spec file is committed, an optional CI job can verify the
bundle still builds:

```yaml
# .github/workflows/packaging.yml — sketch, not enabled by default
on: workflow_dispatch
jobs:
  pyinstaller:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: |
          pip install -e ".[dev]" pyinstaller
          pyinstaller autopapertoppt.spec
      - uses: actions/upload-artifact@v4
        with:
          name: autopapertoppt-${{ matrix.os }}
          path: dist/
```

Enable it via `workflow_dispatch` (manual trigger) rather than every
push — packaging adds 3–5 minutes per OS.
