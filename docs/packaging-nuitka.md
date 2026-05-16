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

## The two project-specific gotchas

Same shape as the PyInstaller doc, just different flags.

1. **Source plugins are loaded by name at runtime.** Nuitka's static
   analysis also misses `importlib.import_module("arxiv")`. The fix
   is `--include-package=<name>` per source.

2. **The `sources/` directory must travel with the bundle.** The
   runtime computes `_SOURCES_DIR = Path(__file__).resolve().parents[2]
   / "sources"` to add it to `sys.path`. In a Nuitka onefile, that
   path resolves into the temp unpack directory, so we ship
   `sources/` as a data dir via `--include-data-dir=sources=sources`.

## Build the CLI (`autopapertoppt`)

```powershell
python -m nuitka `
  --standalone `
  --onefile `
  --output-filename=autopapertoppt `
  --include-package=autopapertoppt `
  --include-package=arxiv `
  --include-package=semantic_scholar `
  --include-package=openalex `
  --include-package=pubmed `
  --include-package=acm `
  --include-package=ieee `
  --include-package=scholar `
  --include-package=dblp `
  --include-package=crossref `
  --include-package=openaire `
  --include-package=springer `
  --include-data-dir=sources=sources `
  --include-package-data=python_pptx `
  --include-package-data=openpyxl `
  --assume-yes-for-downloads `
  autopapertoppt/__main__.py
```

Linux / macOS use the same command (Nuitka's flag syntax is
OS-neutral; the `;` separator quirk that PyInstaller has does not
apply here).

The binary lands at `./autopapertoppt` (or `.exe` on Windows) in the
working directory. Subsequent rebuilds reuse the cache under
`./<entrypoint>.build/` so the first build is slow but later builds
are 2–3 minutes.

## Build the MCP server (`autopapertoppt-mcp`)

```powershell
python -m nuitka `
  --standalone `
  --onefile `
  --output-filename=autopapertoppt-mcp `
  --include-package=autopapertoppt `
  --include-package=arxiv --include-package=semantic_scholar `
  --include-package=openalex --include-package=pubmed `
  --include-package=acm --include-package=ieee `
  --include-package=scholar --include-package=dblp `
  --include-package=crossref --include-package=openaire `
  --include-package=springer `
  --include-data-dir=sources=sources `
  --assume-yes-for-downloads `
  autopapertoppt/mcp/__main__.py
```

## Standalone vs onefile

Nuitka has two modes worth knowing:

- `--standalone` — build a directory (`autopapertoppt.dist/`) that
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
.\autopapertoppt.exe --query "transformer" --source arxiv --max 3 `
                     --out .\smoke-nuitka\
```

Confirm:

- No `ModuleNotFoundError` — all 11 source plugins were bundled.
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

**Slow CI builds.** Cache the Nuitka build dir between runs:

```yaml
- name: Restore Nuitka cache
  uses: actions/cache@v4
  with:
    path: |
      ~/.nuitka
      autopapertoppt.build
    key: nuitka-${{ runner.os }}-${{ hashFiles('pyproject.toml') }}
```

Cuts subsequent builds from 15 minutes to 2–3 minutes.

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
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]" nuitka
      - name: Cache Nuitka build
        uses: actions/cache@v4
        with:
          path: |
            ~/.nuitka
            autopapertoppt.build
          key: nuitka-${{ runner.os }}-${{ hashFiles('pyproject.toml') }}
      - run: |
          python -m nuitka --standalone --onefile \
            --output-filename=autopapertoppt \
            --include-package=autopapertoppt \
            --include-data-dir=sources=sources \
            --assume-yes-for-downloads \
            autopapertoppt/__main__.py
      - uses: actions/upload-artifact@v4
        with:
          name: autopapertoppt-${{ matrix.os }}
          path: |
            autopapertoppt
            autopapertoppt.exe
```

## When to pick which

| Scenario | Use |
|---|---|
| You want a single binary tomorrow with minimal fuss. | PyInstaller |
| Build time is paid in CI, end users run it many times. | Nuitka |
| Bundle size or startup matters. | Nuitka |
| You want to bytecode-protect commercial use. | Nuitka |
| You iterate on the build script frequently. | PyInstaller |
