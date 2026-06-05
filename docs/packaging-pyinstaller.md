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

## The project-specific gotcha

**Source plugins are loaded by name at runtime.** The pipeline calls
`importlib.import_module("thesisagents.sources.<name>")` via
`thesisagents.fetchers.base.load_fetcher`. PyInstaller's static analysis
cannot see these imports, so without help it tree-shakes the plugins
away. The fix is `--collect-submodules thesisagents`, which collects every
sub-module of the package (including `thesisagents.sources.*`).

> **Note (2026-05 migration).** Older commands listed every plugin with
> its own `--hidden-import arxiv …` and copied a sibling `sources/`
> directory via `--add-data "sources;sources"` plus `--paths sources`.
> All of that is obsolete: the plugins now live **inside** the package
> (`thesisagents/sources/`), there is no sibling `sources/` directory, and
> the old `sys.path` injection was removed. `--collect-submodules
> thesisagents` replaces the whole lot.

## Build the CLI (`thesisagents`)

```powershell
pyinstaller `
  --onefile `
  --name thesisagents `
  --collect-submodules thesisagents `
  thesisagents/__main__.py
```

`--collect-submodules thesisagents` is the one flag that matters: the
source plugins load dynamically via
`importlib.import_module("thesisagents.sources.<name>")`, which
PyInstaller's static analysis can't see, so it collects **every**
sub-module of the package (including all of `thesisagents.sources.*`).
That single flag replaces the long per-source `--hidden-import` list.

The command is identical on Linux / macOS — there is no `--add-data`
separator to worry about, because the plugins live inside the package
(`thesisagents/sources/`) and travel with it; there is no sibling
`sources/` directory to copy.

The output binary lands at `dist/thesisagents` (or
`dist/thesisagents.exe` on Windows).

## Build the MCP server (`thesisagents-mcp`)

```powershell
pyinstaller `
  --onefile `
  --name thesisagents-mcp `
  --collect-submodules thesisagents `
  thesisagents/mcp/__main__.py
```

(The MCP entry point is `thesisagents.mcp.__main__:main` — see
`pyproject.toml`'s `[project.scripts]`.)

## Build with a `.spec` file (cleaner for repeated builds)

The flag-soup above is awkward to maintain. PyInstaller's first run
emits a `.spec` file; commit it so subsequent builds are one command.
A hand-tuned spec for this project:

```python
# thesisagents.spec
# Usage: pyinstaller thesisagents.spec
from PyInstaller.utils.hooks import collect_submodules

# Source plugins load dynamically via importlib, so collect every
# sub-module of the package (this pulls in thesisagents.sources.* too).
hidden = collect_submodules("thesisagents")

a = Analysis(
    ["thesisagents/__main__.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas,
    name="thesisagents",
    console=True,
    onefile=True,
    debug=False,
    strip=False,
    upx=False,
)
```

## Verify the executable works

```powershell
dist\thesisagents.exe --query "transformer" --source arxiv --max 3 `
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

Then `dist\thesisagents.exe --query "..." --enrich` works
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
behaviour by wrapping with `chcp 65001 && dist\thesisagents.exe
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
          pyinstaller thesisagents.spec
      - uses: actions/upload-artifact@v4
        with:
          name: thesisagents-${{ matrix.os }}
          path: dist/
```

Enable it via `workflow_dispatch` (manual trigger) rather than every
push — packaging adds 3–5 minutes per OS.
