# Packaging with Nuitka

[Nuitka](https://nuitka.net/) compiles Python to C and then to a
native executable. Compared to PyInstaller it produces smaller and
faster binaries but takes much longer to build. Use it when:

- You want startup that feels like native code (under a second).
- You want some level of bytecode protection (the compiled binary is
  harder to decompile than a PyInstaller zip).
- You're shipping the binary to end users and the build time is paid
  once in CI, not every iteration.

| Trade-off | Notes |
|---|---|
| Build time | 5–15 minutes on this project (C compilation per module). |
| Executable size | ~80–150 MB — roughly half of a PyInstaller build. |
| Startup | <1 second — true native code, no temp-dir unpack. |
| Cross-platform | You must build on the target OS. Cross-compilation is not supported. |
| Source protection | Medium — Python becomes C; recovering the original source needs serious effort. Not security, but not trivial either. |

## Install

```powershell
pip install nuitka
```

Nuitka also needs a C compiler. On Windows you can use the
MinGW-w64 toolchain that Nuitka offers to download on first run; on
Linux any `gcc` works; on macOS install Xcode Command Line Tools.

## The project-specific gotcha

**Source plugins are loaded by name at runtime.** The pipeline calls
`importlib.import_module("thesisagents.sources.<name>")`, which Nuitka's
static analysis can't follow. The fix is a single
`--include-package=thesisagents`: it force-includes every sub-module of
the package, including all of `thesisagents.sources.*`, so the dynamic
import resolves at runtime.

> **Note (2026-05 migration).** Older build commands listed each source
> with its own `--include-package=arxiv` flag and shipped a sibling
> `sources/` directory via `--include-data-dir=sources=sources`. Both are
> gone: the plugins now live **inside** the package
> (`thesisagents/sources/`), there is no sibling `sources/` directory (so
> `--include-data-dir=sources=sources` is a fatal "directory does not
> exist" error), and the old `sys.path` injection was removed. One
> `--include-package=thesisagents` replaces all of it.

## Build the CLI (`thesisagents`)

```powershell
python -m nuitka `
  --standalone `
  --onefile `
  --output-filename=thesisagents `
  --include-package=thesisagents `
  --include-package-data=pptx `
  --include-package-data=openpyxl `
  --assume-yes-for-downloads `
  thesisagents/__main__.py
```

`--include-package=thesisagents` is what bundles the source plugins: the
pipeline loads them dynamically via
`importlib.import_module("thesisagents.sources.<name>")`, which Nuitka's
static analysis can't see, but `--include-package` pulls in **every**
sub-module of the package (including `thesisagents.sources.*`) regardless.
So you do **not** list the sources individually, and there is **no**
`--include-data-dir=sources=sources` — the plugins live inside the package
(`thesisagents/sources/`) since the 2026-05 migration, not in a sibling
`sources/` directory.

Linux / macOS use the same command (Nuitka's flag syntax is
OS-neutral; the `;` separator quirk that PyInstaller has does not
apply here).

The binary lands at `./thesisagents` (or `.exe` on Windows) in the
working directory. The first build is slow. Later builds reuse Nuitka's
compiler cache (clcache with MSVC, ccache elsewhere), which lives in
Nuitka's cache directory rather than in `./<entrypoint>.build/`:
`%LOCALAPPDATA%\Nuitka\Nuitka\Cache` on Windows, `~/.cache/Nuitka` on
Linux, `~/Library/Caches/Nuitka` on macOS. Set `NUITKA_CACHE_DIR` to
move it.

## Build the MCP server (`thesisagents-mcp`)

```powershell
python -m nuitka `
  --standalone `
  --onefile `
  --output-filename=thesisagents-mcp `
  --include-package=thesisagents `
  --assume-yes-for-downloads `
  thesisagents/mcp/__main__.py
```

## Standalone vs onefile

Nuitka has two modes worth knowing:

- `--standalone` — build a directory (`thesisagents.dist/`) that
  contains the exe plus every DLL/SO it needs. Distribute the whole
  folder. **No unpack delay on launch.** Best for users who can
  install a folder.
- `--onefile` — wrap the standalone dir in a single self-extracting
  binary that unpacks to a temp dir on launch. **Slightly slower
  startup (~0.5 s)** because of the unpack step. Best when you have
  to ship a single file.

Either form is fine; the commands above include both flags so you
get the onefile binary. Drop `--onefile` to keep the dist folder
instead.

## Verify the executable works

```powershell
.\thesisagents.exe --query "transformer" --source arxiv --max 3 `
                     --out .\smoke-nuitka\
```

Confirm:

- No `ModuleNotFoundError` — all 15 source plugins were bundled.
- `.pptx` + `.xlsx` + `.bib` land under `./smoke-nuitka/`.
- Startup is sub-second (the main win over PyInstaller).

## Optional dependencies (`[intelligence]`, `[mcp]`)

Nuitka bundles whatever's importable in the build venv. To produce a
binary that supports `--enrich`:

```powershell
pip install -e .[intelligence]
python -m nuitka ... --include-package=pypdf --include-package=anthropic `
                    --include-package=pymupdf ...
```

`pymupdf` is the most problematic dep across both packagers; see
the "Common issues" section below if the build fails on it.

## Common issues

**Build runs out of memory.** Nuitka's C compilation can use 4–8 GB
of RAM on a project this size. On a 16 GB machine close other apps;
on smaller systems add `--jobs=1` to compile serially and lower the
peak.

**`pymupdf` fails to import in the binary.** pymupdf wraps MuPDF
through Cython and ships precompiled native binaries that Nuitka
sometimes mis-routes. Add `--include-package-data=pymupdf` so the
`.so`/`.dll` files land next to the Python module. If still broken,
exclude `[intelligence]` from the build venv and skip pymupdf — the
LLM-as-agent flow over MCP doesn't need it.

**`lxml` build slowness or link errors.** lxml's C extension is
already compiled in the wheel; Nuitka just needs to copy it.
`--include-package-data=lxml` covers it. If the link fails on Linux
ensure `libxml2-dev` and `libxslt1-dev` are installed.

**Slow CI builds.** Point Nuitka's cache at a fixed directory and
save that directory between runs. The build folder is not the cache:
restoring `thesisagents.build` alone still recompiles every C file.

```yaml
env:
  NUITKA_CACHE_DIR: ~/nuitka-cache   # job level, so the Nuitka step sees it
steps:
  - name: Restore Nuitka cache
    uses: actions/cache@55cc8345863c7cc4c66a329aec7e433d2d1c52a9  # v6.1.0
    with:
      path: ~/nuitka-cache
      key: nuitka-${{ runner.os }}-${{ hashFiles('pyproject.toml') }}
```

Later builds then recompile only the C files that changed. The Nuitka
log reports it as `Compiled N C files using clcache with H cache hits`.

**Console encoding on Windows.** Same trick as the PyInstaller doc:
set `PYTHONUTF8=1` or `chcp 65001` before running the binary, so CJK
paper titles in the search output render correctly.

## Optional CI job

Mirror the PyInstaller CI sketch but with Nuitka. Note the longer
build time — make it `workflow_dispatch`-only:

```yaml
# .github/workflows/packaging.yml — sketch, manual trigger
on: workflow_dispatch
jobs:
  nuitka:
    runs-on: ${{ matrix.os }}
    timeout-minutes: 30
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    env:
      NUITKA_CACHE_DIR: ~/nuitka-cache
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
      - uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97  # v7.0.0
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]" nuitka
      - name: Cache Nuitka build
        uses: actions/cache@55cc8345863c7cc4c66a329aec7e433d2d1c52a9  # v6.1.0
        with:
          path: ~/nuitka-cache
          key: nuitka-${{ runner.os }}-${{ hashFiles('pyproject.toml') }}
      - run: |
          python -m nuitka --standalone --onefile \
            --output-filename=thesisagents \
            --include-package=thesisagents \
            --assume-yes-for-downloads \
            thesisagents/__main__.py
      - uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a  # v7.0.1
        with:
          name: thesisagents-${{ matrix.os }}
          path: |
            thesisagents
            thesisagents.exe
```

## When to pick which

| Scenario | Use |
|---|---|
| You want a single binary tomorrow with minimal fuss. | PyInstaller |
| Build time is paid in CI, end users run it many times. | Nuitka |
| Bundle size or startup matters. | Nuitka |
| You want to bytecode-protect commercial use. | Nuitka |
| You iterate on the build script frequently. | PyInstaller |
