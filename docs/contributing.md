# Contributing

How to add a feature, fix a bug, or improve docs without breaking
the project's invariants.

## Quick start

```bash
git clone https://github.com/Integration-Automation/AutoPaperToPPT.git
cd AutoPaperToPPT
python -m venv .venv
.\.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate             # macOS / Linux
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Make a branch off `dev`, push, open a PR against `main`. The
project auto-bumps the patch version and publishes on every
merge to `main` that passes CI — see [Releases](releases.md).

## Definition of Done

**Every change** must satisfy all of the following before commit.
No exceptions — incomplete work stays on the working copy until
the gates pass.

1. **Unit tests written and passing.** New code without new tests
   is incomplete; see "Test coverage expected" below.
2. **`pytest tests/` runs clean.** Pre-existing skips are OK; new
   skips need a written reason.
3. **`ruff check .` reports no new errors.**
4. **`bandit -c pyproject.toml -r autopapertoppt/ sources/`**
   reports `No issues identified`. The `-c` flag is **mandatory** —
   without it bandit ignores the project skip config.
5. **End-to-end smoke** for changes touching `sources/`,
   `autopapertoppt/exporters/`, `autopapertoppt/intelligence/`, or
   `autopapertoppt/mcp/`:
   - Search: `autopapertoppt --query "transformer attention" --source arxiv --max 3 --out ./exports/smoke/`
     — confirm `.pptx`, `.xlsx`, `.bib` land on disk and the deck
     opens without warnings.
   - PPTX changes: also regenerate an enriched / thesis-style deck
     against a known paper (see `scripts/regen_*.py`) and run the
     headless overflow check.
   - MCP changes: `python -c "from autopapertoppt.mcp import build_server; import asyncio; print(asyncio.run(build_server().list_tools()))"`
     — every documented tool present.
6. **No live network calls in tests.** Use recorded fixtures
   under `tests/fixtures/<source>/`. Re-recording is a manual
   step (`scripts/record_fixture.py`) and the recorded file is
   committed.
7. **Commit message** contains no AI tool/model names and no
   `Co-Authored-By` line.

## Commit message rules

- **NEVER** add `Co-Authored-By` lines.
- **NEVER** mention "Claude", "Claude Code", "AI-generated", "GPT",
  "Copilot", or any AI tool / model name **anywhere** —
  including commit messages, PR titles, PR descriptions, code
  comments, and documentation.
- Use imperative mood for the subject line ("Add", "Fix",
  "Remove" — not "Added", "Fixes").
- Keep the subject ≤ 72 chars; wrap the body at 72.
- Explain **why**, not just **what**. The diff already shows
  what.

Good:

> Reject Windows-style absolute paths on POSIX in resolve_safe
>
> Path("C:/evil/path.txt").is_absolute() is False on Linux because
> the host Path class is PosixPath and "C:" is just treated as a
> directory name. test_resolve_safe_rejects_absolute was passing
> on Windows but failing on the Linux CI runner.
>
> Cross-check the reference against both PurePosixPath and
> PureWindowsPath so a drive-letter prefix is rejected regardless
> of host OS.

Bad:

> fix bug

## Test coverage expected

For every change:

| Coverage | What |
|---|---|
| Happy path | Representative input, expected output. |
| Edge cases | Empty / one-item / missing-optional-field inputs. |
| Error handling | Every `except` branch exercised. HTTP 429 → `RateLimitError`. Malformed JSON → `ParseError`. Unwritable path → `ExportError`. |
| Boundary conditions | Values just inside and outside any limit (max keyword length, max results, year filter). |
| Round-trips | `Paper.to_dict → from_dict → equal`, BibTeX render → parse → equal, cache write → read → equal. |

Test placement:

- `tests/test_<module>.py` for core modules.
- `tests/sources/<name>/test_<name>.py` for fetchers (with
  recorded fixtures under `tests/fixtures/<source>/`).
- `tests/exporters/test_<format>.py` for exporters.
- `tests/gui/test_<page>.py` for GUI pages (uses `pytest-qt`).

Use the shared fixtures in `tests/conftest.py` (`http_recorder`,
`fake_cache`, `sample_papers`, `tmp_export_root`). Do not roll
your own async loop or `httpx` client.

## Code quality rules

Mirrored from the SonarQube / Codacy / pylint / flake8 / ruff
default rule sets:

### Complexity

- Cognitive complexity ≤ 15 per function (SonarQube `S3776`).
- Cyclomatic complexity ≤ 10 (pylint `R1260`, radon `C`).
- Function length ≤ 75 logical lines.
- File length ≤ 1000 lines (`S104`).
- Parameter count ≤ 7 (group into a dataclass when exceeded).
- Nesting depth ≤ 4 (use early returns / guards).
- Return statements ≤ 6 per function.
- Local variables ≤ 15 per function.

### Style

- `snake_case` for functions / methods / variables / modules.
- `PascalCase` for classes.
- `UPPER_CASE_WITH_UNDERSCORES` for module constants.
- `_leading_underscore` for private attributes / methods.
- No single-letter names except loop indices (`i`, `j`, `k`) or
  well-known short forms (`q` for query in obvious local scope).

### Errors

- Never `except:` (bare). Always specify exception type.
- Never `except Exception: pass` without a logged reason + comment.
- Never catch `BaseException` directly.
- Use specific exception types from
  `autopapertoppt.core.exceptions`. Chain with `raise X from err`
  to preserve context (ruff `B904`).
- Never use `assert` for runtime validation (assertions are
  stripped under `python -O`). Use explicit `raise` instead.

### Smells

- No unused imports / variables / params (prefix unused params
  with `_`).
- No commented-out code (git preserves history).
- No `print()` in production code; use `autopapertoppt.utils.logging`.
- No `TODO` / `FIXME` / `XXX` in merged code — file a ticket.
- No magic numbers — extract to `UPPER_CASE` constants.
  Exceptions: 0, 1, -1, 2 in obvious contexts.
- `is None` / `is not None`, never `== None`.
- `isinstance(x, T)`, never `type(x) == T`.
- No mutable default args (`def f(x=[])`).
- Prefer f-strings over `.format()` or `%`.
- Always use context managers (`with` / `async with`).

### Security

- `pickle.load(s)` on untrusted data forbidden. Cache uses JSON or
  msgpack.
- `yaml.load` without SafeLoader forbidden — use `yaml.safe_load`.
- MD5 / SHA-1 forbidden for security purposes — use SHA-256+.
  Allowed for cache keys / dedup hashes **only** with
  `usedforsecurity=False`.
- `subprocess` with `shell=True` forbidden when any argument
  comes from user input.
- Never `eval` / `exec` / `compile` on dynamic input.
- Never `tempfile.mktemp()` — use `tempfile.mkstemp()` or
  `NamedTemporaryFile`.
- Network binds default to `127.0.0.1`, not `0.0.0.0`.
- XML parsing uses `defusedxml`, never stdlib `xml.etree` on
  untrusted input.
- HTML parsing uses `beautifulsoup4` with `lxml` parser.
- Random for security uses `secrets`, not `random`.
- All `urlopen` / `httpx` calls go through the project HTTPS-only
  transport via `get_client(source)`.

### Typing & docs

- Public functions and methods MUST have type hints on parameters
  and return type. Use `pydantic` models or `dataclasses` for
  structured payloads — `list[Paper]`, not bare `list`.
- Public modules and classes SHOULD have a one-line docstring.
- Private helpers may omit docstrings if names are self-explanatory.

### Suppression comments

| Tool | Comment | Notes |
|---|---|---|
| ruff / flake8 | `# noqa: <CODE>` | Must list specific codes. |
| bandit | `# nosec B<NNN>` | ruff's `# noqa` does NOT suppress bandit. |
| SonarCloud | `# NOSONAR` | Use for hotspots that can't be config-skipped. |
| pylint | `# pylint: disable=<name>` | Prefer refactor over suppression. |

Every suppression must include a brief justification on the same
line (`# nosec B310  # scheme validated immediately above`).

## Branch / PR conventions

- **`main`** is the release branch. Every CI-success push to
  `main` triggers an auto-bump → PyPI publish → GitHub Release.
- **`dev`** is the integration branch. Open PRs against `main`
  from `dev` (or from a feature branch off `dev`).
- **Feature branches** are fine for non-trivial work — branch
  off `dev`, push, open PR to `dev`, then `dev` → `main`.
- **`[skip release]`** in a commit message gates off the
  auto-bump for that push — use for docs / typo / refactor
  commits where you don't want to burn a version number.

PR title + body:

- Title: imperative mood, ≤ 72 chars.
- Body: `## Summary` (1-3 sentences on the change) + `## Test
  plan` (a checklist of what was verified). Reference the issue
  number if one exists.
- Do NOT mention AI tools / models anywhere.

## Local CI reproduction

Before pushing, reproduce each gate locally:

```bash
# bandit (the -c flag is mandatory)
python -m bandit -c pyproject.toml -r autopapertoppt/ sources/

# ruff
python -m ruff check .

# pytest
python -m pytest tests/

# search-mode smoke
autopapertoppt --query "diffusion models" --source arxiv --max 3 --out ./smoke/

# single-paper smoke
autopapertoppt --paper "https://arxiv.org/abs/1706.03762" --out ./smoke/single/

# (only when touching pptx / i18n) overflow check
python -c "from autopapertoppt.exporters.pptx import inspect_overflow; \
           inspect_overflow('./smoke/your-deck.pptx')"
```

CI runs the same set on Ubuntu + Windows × Python 3.12 / 3.13 /
3.14 (6 jobs). If your change touches Linux-specific code paths
that pass on Windows locally, the Ubuntu cells will catch it.

## What lives where (for adding code)

| Adding... | Goes to... |
|---|---|
| A new source | `sources/<name>/` — see [Source plugin authoring](source_plugins.md). |
| A new export format | `autopapertoppt/exporters/<name>.py` + `tests/exporters/test_<name>.py`. Don't import from `autopapertoppt/fetchers/` — exporters consume `PaperCollection` only. |
| A new MCP tool | `autopapertoppt/mcp/server.py` (add the `@server.tool` registration), document in `docs/mcp.md`, smoke-test by listing tools. |
| A new CLI flag | `autopapertoppt/cli.py` (add to `build_parser`), document in `docs/cli.md`. Don't add `--<service>-key` flags — use env vars. |
| A new GUI tab | `autopapertoppt/gui/pages/<tab>.py`, register in `autopapertoppt/gui/main_window.py`, add a `pytest-qt` smoke test. |
| A new i18n key | Both tables (UI + deck) if user-facing on both surfaces; one if surface-specific. Always fill all 14 languages in one commit — the coverage tests block partial PRs. |
| A new env var | `autopapertoppt/utils/config.py` (or wherever it's consumed), document in `docs/configuration.md`, update `README.md`'s env-var table if user-facing. |

## What NOT to add

- A direct `httpx.get` / `requests.get` / `urllib.request.urlopen`
  call. Always use `get_client(source)`.
- A `pip install`-only dependency in core. Heavy / optional deps
  belong in an extra (`[intelligence]`, `[gui]`, `[mcp]`, `[web]`).
- A `--<service>-api-key` CLI flag. Keys go through env vars or
  the GUI Settings page.
- A feature flag for the auto-bump / release flow. The pipeline
  is intentionally minimal-state.
- A new top-level entry point (console script). The three we have
  (`autopapertoppt`, `autopapertoppt-mcp`, `autopapertoppt-gui`)
  cover every surface; new functionality goes as subcommands or
  tools.

## Reviewing PRs

Look for:

- The change has tests (Definition of Done #1).
- The diff is focused — no unrelated reformatting / "while I was
  here" cleanups (those go in a separate PR).
- The commit message explains **why**.
- No `Co-Authored-By` lines, no AI tool / model names.
- No `# type: ignore` / `# noqa` / `# nosec` without justification.
- The change respects the rate-limit policy of any source it
  touches.

## Releases

See [Releases](releases.md) for the auto-bump flow, the
`[skip release]` escape hatch, and the Nuitka exe pipeline.

## Asking for help

Open an issue at
<https://github.com/Integration-Automation/AutoPaperToPPT/issues>
or a draft PR with a question label. The maintainers are happy
to weigh in on design questions before you write the code.
