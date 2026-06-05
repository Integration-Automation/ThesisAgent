# Installation

ThesisAgents targets **Python 3.12+** on Windows, macOS, and Linux.
This page covers every supported install path; pick the one that
matches how you plan to use the project.

## Install paths at a glance

| Use case | Command | Pulls in |
|---|---|---|
| CLI only | `pip install thesisagents` | The 10-package core runtime — enough to search and emit `.pptx` / `.xlsx` / `.bib`. |
| CLI + MCP server | `pip install "thesisagents[mcp]"` | Adds the `mcp` SDK so `thesisagents-mcp` works. |
| CLI + PDF + LLM enrichment | `pip install "thesisagents[intelligence]"` | Adds `pypdf` + `pymupdf` + `anthropic` for the `--enrich` flow. |
| CLI + desktop GUI | `pip install "thesisagents[gui]"` | Adds PySide6 for `thesisagents-gui` / `thesisagents gui`. |
| Everything | `pip install "thesisagents[intelligence,mcp,gui]"` | All three extras. |
| Developer / contributor | `pip install -e ".[dev]"` from a clone | Full toolchain — pytest, pytest-asyncio, pytest-httpx, pytest-qt, ruff, bandit + every runtime extra. |

The published distribution name on PyPI is `thesisagents`. The
console scripts installed are `thesisagents` (CLI),
`thesisagents-mcp` (MCP server), `thesisagents-gui` (desktop UI).

## Supported runtimes

| Component | Version |
|---|---|
| Python | 3.12, 3.13, 3.14 (CI runs against all three) |
| Operating system | Windows 10/11, macOS 13+, Ubuntu 22.04+ / Debian 12+ / any modern Linux |
| Architecture | x86_64 on all OSes; arm64 on macOS (Apple Silicon) and Linux |

Python 3.12 is the floor because the project uses PEP 695 type
syntax, structural pattern matching, and `httpx`'s 3.12-only async
helpers. Earlier Pythons would need a `from __future__` and
backport gymnastics that we chose not to take on.

## The full dependency surface

### Core (`pip install thesisagents`)

These come with every install. None has a heavy native step:

```
httpx >= 0.27               # async HTTP client
pydantic >= 2.7             # data models
pydantic-settings >= 2.3    # env-var loading
defusedxml >= 0.7           # secure XML parsing
python-pptx >= 0.6.23       # .pptx generation
openpyxl >= 3.1             # .xlsx generation
bibtexparser >= 1.4         # .bib round-trips
beautifulsoup4 >= 4.12      # HTML parsing for scrape fallbacks
lxml >= 5.2                 # parser backend for bs4 + python-pptx
markdown-it-py >= 3.0       # markdown export
```

`lxml` is the only one with a native compile step; pip serves a
prebuilt wheel for every supported platform.

### `[intelligence]` extra

```
pypdf >= 4.0                # text extraction from downloaded PDFs
pymupdf >= 1.24             # higher-fidelity PDF text extraction
anthropic >= 0.40           # Anthropic API client for --enrich
```

`pymupdf` carries a sizable native MuPDF dependency (~30 MB
installed). Prebuilt wheels are available on PyPI for Windows /
macOS / manylinux; on a very old Linux distro you may need to
install MuPDF dev headers and let pip build from source.

### `[mcp]` extra

```
mcp >= 1.2                  # Anthropic's MCP server SDK
```

Pure Python. Only needed if you actually run the MCP server.

### `[gui]` extra

```
PySide6 >= 6.7              # Qt 6 Python bindings
```

PySide6 carries the Qt 6 runtime (~80 MB installed). Prebuilt
wheels cover every supported platform. The wheel includes Qt's
QML, multimedia, charts, network, and SVG modules even though
the current GUI only uses QtWidgets — sized for forward compat
with the Deck-editor tab.

### `[dev]` extra

Everything above plus:

```
pytest >= 8.2
pytest-asyncio >= 0.23
pytest-httpx >= 0.30
pytest-qt >= 4.4
ruff >= 0.5
bandit >= 1.7
```

## Recommended local setup

A project-local virtualenv is strongly recommended so the install
doesn't pollute the system Python:

### Windows (PowerShell)

```powershell
git clone https://github.com/Integration-Automation/ThesisAgents.git
cd ThesisAgents

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"

# Sanity-check
python -m thesisagents --version
python -m pytest tests/
```

### macOS / Linux (bash / zsh)

```bash
git clone https://github.com/Integration-Automation/ThesisAgents.git
cd ThesisAgents

python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"

python -m thesisagents --version
python -m pytest tests/
```

After installation, the activated venv exposes three console
scripts: `thesisagents` (CLI), `thesisagents-mcp` (MCP
server), `thesisagents-gui` (desktop UI). All three also work
as `python -m` invocations:

```
python -m thesisagents ...
python -m thesisagents.mcp
python -m thesisagents.gui.app
```

## Linux: extra system packages for the GUI

PySide6's wheels link to a handful of system libraries that
some minimal Linux images don't preinstall. On Debian / Ubuntu:

```bash
sudo apt-get install -y \
    libegl1 libgl1 \
    libxkbcommon0 libxkbcommon-x11-0 \
    libdbus-1-3 \
    libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
    libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 \
    libxcb-xkb1 libfontconfig1
```

Without these, importing `PySide6.QtGui` fails with
`libEGL.so.1: cannot open shared object file` and pytest-qt
crashes during `pytest_configure` (before any test runs).

On a headless Linux box (CI, server) the GUI still imports if you
set `QT_QPA_PLATFORM=offscreen` — Qt renders into an in-memory
buffer instead of an X server.

## Windows: prebuilt `.exe`

Every release ships a self-contained Windows zip built with
Nuitka. Download `thesisagents-windows-x86_64.zip` from the
[GitHub Releases page](https://github.com/Integration-Automation/ThesisAgents/releases),
unzip anywhere, and run `thesisagents.exe` directly. The bundle
includes Python, every dependency (including PySide6), and the 11
source plugins — no separate Python install is needed.

The bundle entry point is `python -m thesisagents`, so all the
same CLI flags work:

```powershell
.\thesisagents.exe --query "diffusion models" --max 10 --out .\exports\
.\thesisagents.exe --paper "https://arxiv.org/abs/1706.03762" --out .\exports\
.\thesisagents.exe gui     # opens the desktop UI
```

A `.sha256` companion is attached to every release for integrity
checking.

## Installing from a pre-release / development branch

```bash
# From a Git ref directly
pip install "git+https://github.com/Integration-Automation/ThesisAgents@dev"

# From a local clone (editable — picks up your changes live)
pip install -e .
```

The editable install is the recommended developer setup because it
points the import path at your working copy, so source changes
take effect on the next `import` without a reinstall.

## Verifying an install

```bash
thesisagents --version       # prints package version + Python info
thesisagents --help          # full CLI flag list
python -c "import thesisagents; print(thesisagents.__file__)"
```

If the MCP extra is installed:

```bash
python -c "from thesisagents.mcp import build_server; import asyncio; \
    print(sorted(t.name for t in asyncio.run(build_server().list_tools())))"
```

You should see all eleven tool names: `list_sources`, `search`,
`fetch_paper`, `fetch_pdf_text`, `download_pdfs`, `export`,
`pptx_inspect`, `pptx_update_slide`, `pptx_delete_slide`,
`pptx_reorder_slides`, `pptx_add_slide`.

If the GUI extra is installed:

```bash
thesisagents gui             # opens the window
# or: python -m thesisagents.gui.app
```

## Uninstall

```bash
pip uninstall thesisagents
```

Saved API keys / cookies-file paths live in your platform's
QSettings store and are not removed by `pip uninstall`. To clear
them too:

- **Windows**: `HKEY_CURRENT_USER\Software\ThesisAgents\ThesisAgents`
- **macOS**: `~/Library/Preferences/com.ThesisAgents.ThesisAgents.plist`
- **Linux**: `~/.config/ThesisAgents/ThesisAgents.conf`

## Common install failures

**`error: Microsoft Visual C++ 14.0 or greater is required`** (Windows)

A dependency tried to build from source because pip couldn't find
a matching prebuilt wheel. Make sure you're on Python 3.12, 3.13,
or 3.14 — that covers every wheel published. If you're on a
prerelease Python, downgrade or install the MSVC C++ Build Tools.

**`No matching distribution found for thesisagents`**

`pip` is older than `pip install` needs to resolve a project with
`[project]` metadata. Upgrade:

```bash
python -m pip install --upgrade pip
```

**`error: setuptools needs to be at least version 68`**

Same root cause as above. The `pip install --upgrade pip` line
also pulls in a recent setuptools.

**`ImportError: libEGL.so.1`** (Linux GUI)

Install the system packages listed in the "Linux: extra system
packages for the GUI" section above.

**`OSError: [Errno 28] No space left on device` during pip install**

The cumulative install with `[dev]` is roughly 700 MB (PySide6 +
pymupdf + lxml + Anthropic SDK are the heaviest items). Make sure
the venv path has enough disk free.
