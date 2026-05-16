# Project Guidelines

> **Other agents:** `AGENTS.md` mirrors the cross-agent must-knows
> (LLM-as-agent default path, HTTPS-only, paywall gate, slide-deck
> guards, Definition of Done). Codex CLI, recent Aider, and several
> other tools auto-load `AGENTS.md`; this file remains the canonical,
> deeper reference. Keep them in sync when you change the rules.

## Project Overview

AutoPaperToPPT is a Python CLI + MCP assistant that:

1. **Searches academic papers** by user-supplied keywords across multiple sources
   (arXiv, Semantic Scholar, OpenAlex, PubMed, IEEE Xplore, ACM Digital Library, DBLP,
   Crossref, OpenAIRE, Springer Nature, and Google Scholar via opt-in scraping). Each
   source ships behind a fetcher adapter so adding a new source does not touch the
   exporter layer or the MCP server.
2. **Normalises the results** into a single internal `Paper` record (title, authors,
   year, venue, abstract, source URL/DOI, BibTeX key, raw payload, optional
   `PaperSummary`), de-duplicates by DOI / arXiv ID / title-fuzzy-match, and ranks by
   recency + citation count.
3. **Optionally enriches each paper** by fetching its PDF and producing a structured
   `PaperSummary`. Two enrichment paths:
   - **LLM-as-agent (no API key)** — an MCP-aware client (e.g. Claude Code) calls
     `fetch_paper` + `fetch_pdf_text`, reads the body text in-context, writes a
     summary dict, and passes it to `export`.
   - **Python pipeline (`--enrich`)** — the CLI calls the Anthropic API itself
     (`ANTHROPIC_API_KEY` required); default model `claude-opus-4-7`.
4. **Generates four outputs** from a chosen result set:
   - **`.pptx` slide deck** — 16:9 widescreen, page-numbered. Three rendering paths
     pick themselves based on what's present:
     - *Lightweight* (abstract only) — cover + agenda + Background / Approach /
       Findings sentence buckets + references.
     - *Enriched-flat* (`PaperSummary` motivation/contributions/method/results/…)
       — one slide per flat section.
     - *Thesis-style* (`PaperSummary` rich fields) — pain-point quadrant +
       research-question callout + KPI block + technique table + literature
       positioning table + system overview + method details + per-RQ result
       tables + contribution summary + core observation + limitations &
       future work + Q&A + references.
   - **`.xlsx` workbook** — "Papers" sheet with hyperlinked URL/PDF, "Query" sheet
     with provenance.
   - **`.bib` BibTeX file** — stable, collision-free citation keys, LaTeX-escaped.
   - **`.md` summary** and **`.json` raw payload** also available as exporters.
5. **Exposes an MCP server** that surfaces every step as a tool (`search`,
   `fetch_paper`, `fetch_pdf_text`, `export`, `pptx_inspect`, `pptx_update_slide`,
   `pptx_delete_slide`, `pptx_reorder_slides`, `pptx_add_slide`).

The whole stack is single-process and runs on Python 3.12+. Heavy I/O (network
fetches, PDF text extraction, LLM calls) MUST happen off the event loop's main
thread; the shared `httpx.AsyncClient` registry pools connections per source.

### Top-level layout

```
AutoPaperToPPT/
├── autopapertoppt/                 # main package
│   ├── core/                        # Paper / PaperSummary / RqResult / Query models,
│   │                                # constants, dedup, ranking, pipeline, identifiers
│   ├── fetchers/                    # HTTPS-only shared client, token-bucket rate
│   │                                # limit, Fetcher abstract base
│   ├── exporters/                   # pptx (thesis-style + lightweight), xlsx, bibtex,
│   │                                # markdown, json + pptx_edit + i18n
│   ├── intelligence/                # PDF fetch/extract + Anthropic summariser
│   │                                # (optional [intelligence] extra)
│   ├── mcp/                         # FastMCP server registering all tools
│   ├── utils/                       # logging, path safety, async helpers
│   ├── cli.py                       # argparse CLI
│   └── __main__.py                  # `python -m autopapertoppt`
├── sources/<name>/                  # per-source plugins (arxiv/, semantic_scholar/,
│                                    # openalex/, pubmed/, ieee/, acm/, scholar/,
│                                    # dblp/, crossref/, openaire/, springer/)
│   ├── __init__.py                  # sets `fetcher_class`
│   ├── fetcher.py                   # Fetcher subclass
│   └── parser.py                    # source-specific payload → Paper
├── tests/                           # pytest suite + fixtures (hermetic, no live HTTP)
│   ├── fixtures/<source>/*.json|xml|html
│   └── sources/test_<source>.py
├── docs/                            # Sphinx tree (en + zh-tw + zh-cn)
├── scripts/                         # one-off regen / fixture-record scripts
├── pyproject.toml                   # ruff, bandit, build, optional extras
└── .bandit                          # canonical bandit skip list
```

## Definition of Done (HARD REQUIREMENT)

Every feature, bug fix, refactor, or behaviour change MUST satisfy ALL of the following before
it can be committed. No exceptions — incomplete work stays on the working copy until the gates
pass.

1. **Unit tests are written and they pass.** New code without new tests is incomplete; the
   commit fails this gate. See the **Unit Tests** section below for the exact coverage
   expectations.
2. `py -m pytest tests/` runs clean (or only skips that already existed before the change).
3. `py -m ruff check .` reports no new errors.
4. `py -m bandit -c pyproject.toml -r autopapertoppt/ sources/` reports `No issues identified`.
5. **End-to-end smoke check** for any change that touches `sources/`,
   `autopapertoppt/exporters/`, `autopapertoppt/intelligence/`, or
   `autopapertoppt/mcp/`:
   - Run `py -m autopapertoppt --query "transformer attention" --source arxiv
     --max 3 --out ./exports/smoke/` and confirm `.pptx`, `.xlsx`, `.bib` land
     on disk and the deck opens without warnings (no overflow into the footer).
   - For pptx changes, also run an enriched / thesis-style regen against a
     known paper (see `scripts/regen_*.py`) and inspect the output with a
     headless slide-overflow check — every shape's rendered text height must
     fit within its allotted box, no shape may extend past 7.05" on a 16:9
     widescreen slide.
   - For MCP changes, hit `python -c "from autopapertoppt.mcp import
     build_server; import asyncio; print(asyncio.run(build_server().list_tools()))"`
     and verify every documented tool is present.
6. **No live network calls in tests** — every fetcher test uses recorded fixtures
   (`tests/fixtures/<source>/*.json|html`). Recording new fixtures is a separate, manual step
   (`scripts/record_fixture.py`) and the recorded file is committed.
7. The commit message contains no AI tool/model names and no `Co-Authored-By` line.

When you finish editing code, work through this list explicitly before staging. If a gate
fails, fix it — do not ship around it. Skipping tests "to come back later" is not allowed
because later never happens and the gap compounds.

## Git Commits

- NEVER add `Co-Authored-By` lines to commit messages. All commits should only contain the
  commit message itself with no co-author attribution.
- NEVER mention "Claude", "Claude Code", "AI-generated", "GPT", "Copilot", or any AI tool /
  model name anywhere — including commit messages, PR titles, PR descriptions, code
  comments, and documentation.

## Code Quality Requirements

### Design Patterns

- Apply appropriate design patterns (Strategy, Adapter, Factory, Observer, Command, Builder,
  Decorator, Template Method) where they fit naturally. Fetchers are Strategies behind a
  Factory; exporters are Strategies; the search pipeline is a Chain of Responsibility
  (fetch → normalise → dedup → rank → cache); rate limiting is a Decorator on the HTTP
  client.
- Prefer composition over inheritance. A `Paper` is a dataclass of fields + a `RawPayload`
  attachment, not a deep class hierarchy.
- Follow SOLID principles: Single Responsibility, Open/Closed, Liskov Substitution, Interface
  Segregation, Dependency Inversion. The exporter layer depends on the `Paper` /
  `PaperCollection` interfaces, never on a concrete fetcher's response shape.
- Apply DRY — extract shared HTTP / rate-limit / retry logic into `autopapertoppt/fetchers/`;
  never copy a `requests`/`httpx` setup across source plugins.
- Reuse the existing project patterns: `httpx.AsyncClient` for network, `asyncio.Semaphore`
  for per-source concurrency caps, FastAPI dependency injection for the cache + settings,
  Streamlit `st.session_state` (never module globals) for UI state.

### Software Engineering Practices

- Separate concerns: the exporters never call the network — they consume an in-memory
  `PaperCollection`. The UI never parses HTML — it receives normalised `Paper` records from
  the API layer.
- Write self-documenting code with clear naming; add comments only for non-obvious "why"
  explanations (e.g. "Google Scholar returns no stable ID, so we hash title+first-author+year
  to form the dedup key").
- Favor immutability where practical — `Paper`, `Query`, and `ExportRequest` are frozen
  dataclasses; mutations create a new instance.
- Handle errors explicitly at system boundaries (network calls, file IO, HTML parsing,
  exporter rendering); propagate exceptions cleanly through internal layers. Wrap every
  HTTP call in a helper that raises a typed `FetchError` (`RateLimitError`, `ParseError`,
  `SourceUnavailableError`) — never swallow.
- Keep functions short and focused — one function, one responsibility.
- Delete dead code immediately; do not comment it out or leave unused imports/variables.

### Performance

- Always consider and implement the best-performance approach for the task.
- Use lazy loading and on-demand initialization where applicable. Fetcher plugins are
  imported on first use, not at app startup; the pptx template is parsed once and cached.
- Avoid unnecessary memory allocations and copies — stream large response bodies through
  `httpx` rather than loading entire HTML pages into memory when only a result list is
  needed.
- Prefer batch operations over per-item processing. Group fetches by source, run sources in
  parallel with `asyncio.gather`, but cap per-source concurrency with a semaphore.
- Use appropriate data structures: dict for O(1) DOI / arXiv-ID lookup, set for the dedup
  key set, deque for the rate-limit token bucket history, dataclasses for hot record paths.
- Profile and measure before optimizing hot paths; avoid premature optimization of cold
  paths. `autopapertoppt/utils/profiling.py` exposes `with section("name"):` — use it before
  claiming a perf win.
- Cache expensive operations with `functools.lru_cache` (in-process) or the disk cache in
  `autopapertoppt/cache/` (cross-run). Every raw network response is cached keyed by
  `sha256(source + normalized_query + page)`; default TTL is configurable per source.
- Use generators / `AsyncIterator` for large result pages so the UI can start rendering the
  first page before later pages arrive.
- Never block the event loop with synchronous network calls. Use `httpx.AsyncClient`, not
  `requests`. Synchronous `requests` is allowed ONLY in the fixture-recording script.

### Async & Concurrency Rules

- The FastAPI process owns **exactly one** `httpx.AsyncClient` per source, created at
  startup and reused for the whole process lifetime. Do NOT create a fresh client per
  request — connection pooling and rate-limit token-bucket state must persist.
- Per-source rate limits live in `autopapertoppt/fetchers/rate_limit.py` as a token-bucket
  decorator. Each source plugin declares its own bucket (`arxiv: 1 req/3s`,
  `semantic_scholar: 1 req/s`, `scholar: 1 req/10s with jitter`, etc.). Do NOT bypass the
  bucket — even retries go through it.
- Streamlit runs the UI on a separate thread per session. Mutate `st.session_state` only,
  never module globals. Long-running export jobs are dispatched to the FastAPI backend and
  polled, not run inline in the Streamlit script.
- All fixture-recording, CLI exports, and tests use `asyncio.run` at the outermost layer
  and never inside library code.

### Security

- Never hardcode secrets, API keys, tokens, or passwords in source code — use environment
  variables (`AUTOPAPERTOPPT_IEEE_API_KEY`, `AUTOPAPERTOPPT_SCHOLAR_PROXY`, …) loaded via
  `pydantic-settings`. Document required env vars in `README.md`.
- Validate and sanitize ALL external input (user keywords, API responses, scraped HTML,
  uploaded BibTeX) at system boundaries. Strip control characters from keywords before
  building URLs; cap query length to a configurable hard limit.
- Sanitize file paths to prevent path traversal — every export `out` path is resolved
  through `autopapertoppt/utils/path_safety.py::resolve_safe(root, reference)`, which rejects
  `..` segments, rejects absolute paths from the API request body, and asserts the resolved
  path stays under `root`.
- Apply the principle of least privilege — fetcher plugins only see the curated HTTP client
  and a logger. They never see the filesystem, the cache layer, or other sources'
  credentials.
- Avoid `eval()`, `exec()`, `pickle.loads()` on untrusted data, and `subprocess` with
  `shell=True`. Cached payloads are stored as JSON or msgpack, never pickle.
- All network traffic uses HTTPS. The shared HTTP client rejects any URL whose scheme is
  not `https` via the `_https_only_transport` wrapper (see **Network Safety** below).
- Respect robots / ToS — Google Scholar scraping is OFF by default and must be opted in by
  setting `AUTOPAPERTOPPT_ENABLE_SCHOLAR_SCRAPING=1`. Per-source `User-Agent`, request
  spacing, and concurrency caps are declared in each plugin and MUST NOT be removed to "make
  things faster".
- Use secure defaults: SHA-256 for cache keys and dedup hashes, `secrets.token_urlsafe` for
  any session token, constant-time comparisons for any future signature checks.
- Log security-relevant events (rejected URLs, malformed responses, rate-limit hits) but
  never log full API keys or full HTML response bodies — truncate to 256 chars and redact
  any token-shaped strings.

### Unit Tests

Tests are not optional polish — they are part of the change. A feature without tests is an
incomplete feature and MUST NOT be committed. This rule applies equally to bug fixes
(regression test required) and refactors (existing behaviour must remain green; add a test
if the refactor exposes a previously untested path).

**Required coverage for every change:**

- **Happy path** — the new code does what it advertises on a representative input (a small
  recorded arXiv response, a 2-result PubMed XML, a single-page Scholar HTML snapshot).
- **Edge cases** — empty result sets, single-paper sets, missing optional fields (no DOI,
  no abstract, no year), Unicode-heavy titles, multi-author truncation, duplicate papers
  across sources.
- **Error handling** — every `except` branch is exercised; HTTP 429 raises
  `RateLimitError`; malformed JSON / HTML raises `ParseError`; an exporter writing to an
  unwritable path raises `ExportError`.
- **Boundary conditions** — values just inside and just outside any limit (max keyword
  length, max results per page, min/max year filter, BibTeX key collision counter).
- **Round-trips** — `Paper.to_dict → from_dict → equal`; `BibTeX render → parse → equal`;
  cache write → cache read → equal.

**Required test types for every feature:**

- **Pure-helper tests.** Extract pure logic out of network / IO classes (dedup hashing,
  ranking, BibTeX key generation, abstract cleaning) into helper modules and unit-test
  those directly without spinning up `httpx` or FastAPI. Cheap, fast, deterministic.
- **Fetcher tests against recorded fixtures.** Every source plugin has a
  `tests/sources/<name>/test_<name>.py` that loads
  `tests/fixtures/<name>/<scenario>.json|html` via a monkeypatched transport and asserts
  the parsed `Paper` list. No live network calls — the test suite must be runnable
  offline.
- **API tests.** Use FastAPI's `TestClient` to call `/search`, `/export`, `/status` with
  the fetcher layer monkeypatched to a fake that returns canned `Paper` records.
- **UI smoke test.** Use `streamlit.testing.v1.AppTest` to drive the Streamlit page,
  enter a keyword, click search, and assert the results table renders. Long-running
  features get their own AppTest scenario.
- **Exporter tests.** Render to a `tmp_path`, then re-open the artefact and assert
  structure: `python-pptx` to assert slide count + title text; `markdown-it` (or plain
  string match) for `.md`; `bibtexparser` for `.bib`. Binary PDF tests assert non-empty
  file + valid `%PDF-` magic header.
- **Integration test where the wiring is non-obvious.** End-to-end fetch → dedup → rank →
  export on a small recorded multi-source fixture.

**Mechanics:**

- Use `pytest` + `pytest-asyncio` style. Module-level functions and `Test*` classes are
  both fine; follow the style of the file you're adding to.
- Test file naming: `tests/test_<module_name>.py` for core, `tests/sources/<name>/...` for
  fetchers, `tests/exporters/test_<format>.py` for exporters.
- Use the shared fixtures in `tests/conftest.py` (`http_recorder`, `fake_cache`,
  `sample_papers`, `tmp_export_root`). Do not roll your own async loop or `httpx` client.
- Tests that need a recorded HTTP exchange use the `http_recorder` fixture, which loads
  the matching JSON/HTML file and asserts the request URL + headers match what was
  recorded. Re-recording is a manual step (`scripts/record_fixture.py`) — never let a
  test silently mutate fixtures.
- Never write to the user's real cache or settings file. The autouse
  `_isolate_user_paths` fixture redirects `AUTOPAPERTOPPT_CACHE_DIR` and
  `AUTOPAPERTOPPT_CONFIG_DIR` to `tmp_path`.
- Run `py -m pytest tests/` before committing. If a test was already skipping because of
  a missing optional dependency, leave it skipping — but every NEW test must run, not
  skip.

### Linter & Static Analysis Compliance (SonarQube / Codacy / pylint / flake8 / ruff)

All new and modified code MUST pass the following rules without warnings. These mirror the
default rule sets of SonarQube, Codacy, pylint, flake8, ruff, and bandit for Python.

#### Complexity & Size

- **Cognitive complexity**: keep each function ≤ 15 (SonarQube `python:S3776`). Break
  nested branches into helper functions when exceeded.
- **Cyclomatic complexity**: keep each function ≤ 10 (pylint `R1260`, radon `C`).
- **Function length**: ≤ 75 logical lines. Split long functions into focused helpers.
- **File length**: ≤ 1000 lines (SonarQube `python:S104`). Split large modules.
- **Parameter count**: ≤ 7 per function (SonarQube `python:S107`). Group related params
  into a dataclass when exceeded. (`Query`, `ExportOptions`, `FetcherConfig`.)
- **Nesting depth**: ≤ 4 levels (SonarQube `python:S134`). Use early returns / guard
  clauses.
- **Boolean expression complexity**: ≤ 3 operators in one expression (SonarQube
  `python:S1067`). Extract to named booleans.
- **Return statements**: ≤ 6 per function (pylint `R0911`).
- **Local variables**: ≤ 15 per function (pylint `R0914`).

#### Duplication

- Do NOT copy-paste blocks of ≥ 3 statements across functions or files (SonarQube
  `common-python:DuplicatedBlocks`, Codacy duplication detector). Extract shared logic —
  HTTP setup, retry/backoff, abstract cleaning, BibTeX key generation all live in one
  place.
- Do NOT declare the same string literal ≥ 3 times (SonarQube `python:S1192`). Assign to
  a module-level constant. Source names (`"arxiv"`, `"pubmed"`, …) live in
  `autopapertoppt/core/sources.py` constants.

#### Naming (PEP 8)

- `snake_case` for functions, methods, variables, modules (SonarQube `python:S1542`,
  pylint `C0103`).
- `PascalCase` for classes (pylint `C0103`).
- `UPPER_CASE_WITH_UNDERSCORES` for module-level constants.
- `_leading_underscore` for private attributes / methods.
- No single-letter names except loop indices (`i`, `j`, `k`) or well-known short forms
  (`q` for query in obvious local scope, `r` for response in a `with httpx.stream(...)`
  block).

#### Errors & Exceptions

- Never use bare `except:` — always specify the exception type (SonarQube `python:S5754`,
  flake8 `E722`).
- Never write `except Exception: pass` without a logged reason and comment explaining why
  it is safe.
- Never catch `BaseException` directly (covers `KeyboardInterrupt`, `SystemExit`).
- Raise specific exception types — define a domain hierarchy: `AutoPaperToPPTError` →
  `FetchError` (`RateLimitError`, `ParseError`, `SourceUnavailableError`), `CacheError`,
  `ExportError`, `ConfigError`.
- Chain exceptions with `raise X from err` to preserve context (ruff `B904`).
- Never use `assert` for runtime validation (assertions are stripped under `python -O`);
  use explicit `raise` instead. `assert` is only for invariants in tests.

#### Code Smells

- No unused imports, variables, or function parameters (pyflakes `F401`, `F841`, pylint
  `W0612`, `W0613`). Prefix intentionally unused params with `_`.
- No commented-out code. Delete it — git preserves history.
- No `print()` calls in production code; use the project's logger
  (`autopapertoppt/utils/logging`).
- No `TODO` / `FIXME` / `XXX` left in merged code (SonarQube `python:S1135`). File a
  ticket instead.
- No magic numbers — extract to `UPPER_CASE` constants (SonarQube `python:S109`).
  Exceptions: `0`, `1`, `-1`, `2` in obvious contexts. Common constants
  (`DEFAULT_PAGE_SIZE = 25`, `MAX_RESULTS_PER_SOURCE = 200`, `CACHE_TTL_SECONDS = 86400`)
  live in `autopapertoppt/core/constants.py`.
- Use `is None` / `is not None` (never `== None` / `!= None`) (pycodestyle `E711`).
- Use `isinstance(x, T)` instead of `type(x) == T` (pycodestyle `E721`).
- No mutable default arguments (`def f(x=[])`) — use `None` and assign inside (ruff
  `B006`, pylint `W0102`).
- No global mutable state; if unavoidable, encapsulate in a module-level class or
  singleton (the shared HTTP client registry, the cache handle, the rate-limit buckets).
- Prefer f-strings over `.format()` or `%` (ruff `UP032`).
- Always use context managers (`with` / `async with`) for file / HTTP / DB resource
  handles (ruff `SIM115`).
- Prefer `dict.get(key, default)` over `if key in dict: ... else: ...` (ruff `SIM401`).
- Use comprehensions / generator expressions instead of `map` + `lambda` or manual
  `append` loops when clearer.

#### Security (bandit / SonarQube `python:S*` security rules)

- `pickle.load(s)` on untrusted data is forbidden (`B301`, SonarQube `python:S5135`).
  Cache payloads are JSON or msgpack with a strict schema.
- `yaml.load` without `SafeLoader` is forbidden — use `yaml.safe_load` (`B506`).
- MD5 / SHA-1 are forbidden for security purposes — use SHA-256+ (`B303`, `B304`,
  SonarQube `python:S4790`). Allowed for non-security uses (cache keys, dedup hashes)
  ONLY with `usedforsecurity=False`.
- `subprocess` with `shell=True` is forbidden when any argument comes from user input
  (`B602`). The PDF export shells out to `pandoc` / `weasyprint` via the args-list form
  only.
- Never use `eval`, `exec`, `compile` on dynamic input (`B307`). There are no exceptions
  in this project.
- Never use `tempfile.mktemp()` — use `tempfile.mkstemp()` or `NamedTemporaryFile`
  (`B306`).
- Network binds must not use `0.0.0.0` unless intentional and documented (`B104`). The
  FastAPI app defaults to `127.0.0.1`.
- XML parsing (PubMed XML, arXiv Atom feed) MUST use `defusedxml`, never stdlib
  `xml.etree` on untrusted input (`B405`–`B411`).
- HTML parsing uses `beautifulsoup4` with `lxml` parser; never `eval`-style attribute
  evaluators.
- Random number generation for security must use `secrets`, not `random` (`B311`).
  Backoff jitter MAY use `random` and should pin a seed in tests for reproducibility.
- All `urlopen` / `httpx` calls go through the project HTTPS-only transport (see
  **Network Safety** below). Direct `requests.get` / `urllib.request.urlopen` is
  forbidden in production code.

#### Typing & Documentation

- Public functions and methods MUST have type hints on parameters and return type. Use
  `pydantic` models or `dataclasses` for structured payloads; `list[Paper]`, not bare
  `list`.
- Public modules and classes SHOULD have a one-line docstring describing their purpose.
- Private helpers may omit docstrings if names are self-explanatory.
- Each source plugin's `fetcher.py` carries a module docstring stating the source name,
  the endpoint(s) it talks to, the rate limit, and whether an API key is required.

#### Enforcement

When writing or modifying code, mentally check each function against the above rules
before finalising. If unavoidable rule violation (e.g. a FastAPI dependency signature
forces extra parameters, or a parser genuinely needs a long match block), add a
`# noqa: <rule>` or equivalent suppression with a brief justification comment on the
same line.

## Project-Specific Compliance Patterns

### Core vs Source Plugins

The line between `autopapertoppt/` (the main package) and `sources/<name>/` is **not**
"anything source-related goes in sources" — it's **dependency surface and failure
isolation**.

**A feature is a source plugin when ANY of the following is true:**

1. It needs a **heavy / optional runtime dependency** that we don't want to force on every
   user (e.g. `selenium` for Scholar JS-rendered pages, `xmltodict` for PubMed, a vendor
   SDK for IEEE Xplore).
2. It needs **failure isolation** — a flaky third-party API or scraping target should
   never bring down the search pipeline. Other sources keep returning results.
3. It needs **independent release cadence** — a Scholar HTML layout change can be patched
   without re-shipping the core engine.

**A feature stays in the core when:**

- It runs on the default dep set (`httpx`, `pydantic`, `defusedxml`, `python-pptx`,
  `openpyxl`, `bibtexparser`, `beautifulsoup4`, `lxml`, `markdown-it-py`).
- It's part of the everyday search / export workflow that all users should see by
  default (arXiv, Semantic Scholar, PubMed are core; Scholar scraping and IEEE
  scraping are opt-in plugins gated by env vars; ACM via Crossref is a plugin).

#### Optional extras (opt-in installs)

| Extra | Pulled in | Why optional |
|---|---|---|
| `[intelligence]` | `pypdf`, `anthropic` | PDF text extraction + Anthropic API for `--enrich`. Not needed for the LLM-as-agent flow over MCP. |
| `[mcp]` | `mcp` SDK | Only for users who want to run / register the MCP server. |
| `[web]` | `fastapi`, `uvicorn`, `streamlit` | Reserved for the future web UI. CLI + MCP do not need it. |
| `[dev]` | All of the above + `pytest*`, `ruff`, `bandit` | Developer toolchain. |

#### Directory rules

- **Core**: `autopapertoppt/<area>/<feature>.py` for pure logic.
- **Source plugin**: `sources/<name>/__init__.py` (sets `fetcher_class`),
  `sources/<name>/fetcher.py` for the adapter, and **all source-internal parsing /
  HTML-specific logic lives INSIDE the source directory**. Never put HTML selectors
  or vendor SDK calls under `autopapertoppt/core/`.
- **Intelligence**: `autopapertoppt/intelligence/pdf.py` and `summarise.py` are
  lazy-imported behind the `[intelligence]` extra. They MUST not be imported at
  module top-level by any non-intelligence file.
- **Recorded fixtures**: `tests/fixtures/<source>/<scenario>.{json,html,xml}`.
  Re-record with `scripts/record_fixture.py --source <name> --query "..."`. Strip
  any user-specific tokens before committing.

#### Testing source-internal modules

Source plugins are not on the default `sys.path` — at runtime
`autopapertoppt/app/source_manager.py` prepends `sources/` so each source folder becomes
importable as a package. `tests/conftest.py` mirrors that injection at session-collect
time, which lets tests in `tests/` import source modules with
`from <name>.<module> import …`. Do not duplicate the path injection in individual test
files.

#### When in doubt

Ask: "if a user installs AutoPaperToPPT with the default `requirements.txt` and never
enables a source plugin, should this source work?" If yes → core. If no → source plugin.

### Network Safety

- **All outbound HTTP MUST go through `autopapertoppt/fetchers/http.py::get_client(source)`.**
  It returns a per-source `httpx.AsyncClient` configured with: HTTPS-only transport,
  source-specific `User-Agent`, source-specific rate-limit decorator, exponential backoff
  with jitter on 429 / 5xx, and a hard total-timeout.
- Do NOT call `httpx.get` / `requests.get` / `urllib.request.urlopen` directly in new
  code. Import `get_client` instead.
- The HTTPS-only transport rejects any URL whose scheme is not `https`. If a source's
  documented endpoint is `http`, fix the source's config — do not bypass the transport.
- Any redirect chain that crosses to a non-`https` scheme is rejected mid-flight.
- Per-source rate limits are declared in `sources/<name>/config.py` as a `RateLimit`
  dataclass (`requests_per_second`, `burst`, `jitter_seconds`). Tests assert the configured
  values against the source's published policy.
- Mirror the `# nosec` pattern only where genuinely necessary: any direct `urlopen` left
  for the fixture-recording script carries `# nosec B310  # scheme validated above` and
  is gated by an `if scheme != "https": raise` check immediately before the call.

### Query & Input Safety

- User keywords are passed through `autopapertoppt/core/query.py::normalize_query` before
  being embedded in any URL or body. It strips control characters, normalises Unicode
  (NFC), caps length, and HTML/URL-encodes per the target source's rules.
- Date ranges, year filters, and result-count limits are validated at the FastAPI layer
  with `pydantic` `Field` constraints. Out-of-range values return HTTP 422, never silent
  clamping deep inside a fetcher.
- BibTeX uploads (for "import existing bibliography" features) are parsed with
  `bibtexparser` in strict mode, capped at a size limit, and rejected on schema violation.

### Export Path Safety

- Every export `out_dir` from the CLI / MCP is resolved through
  `autopapertoppt/utils/path_safety.py::ensure_export_dir(...)` and
  `safe_filename(...)`.
- Filenames inside the export root are derived from a sanitised slug of the query +
  timestamp (`{slug}-{YYYYMMDD-HHMMSS}.pptx`). Never use raw user-supplied filenames.

### Slide Deck Rules

The pptx exporter is the most visually-sensitive surface in the project. Several
non-obvious rules keep its output safe to ship to a thesis-defence audience:

1. **16:9 widescreen.** `slide_width = 13.333"`, `slide_height = 7.5"`. Body area
   sits between `BODY_TOP = 1.5"` and `FOOTER_GUARD = 7.0"`. Never let a shape's
   *rendered* text extend past `FOOTER_GUARD` — that's the line at which page
   numbers and footers live.
2. **Three rendering tiers.** `PptxExporter._add_paper_slides` dispatches by
   inspecting `Paper.summary`:
   - `summary.has_rich_fields()` → `_add_rich_summary_slides` (thesis-style).
   - `summary` populated only in the flat tier → `_add_flat_summary_slides`.
   - No summary → `_add_abstract_split_slides` (sentence-bucketing fallback).
3. **Defensive truncation.** Every textbox runs its text through `_truncate(...,
   _BULLET_MAX_CHARS)`; multi-column / quadrant cells use the narrower
   `_BULLET_MAX_CHARS_COL = 28` because half-width columns wrap sooner. Section
   titles cap at `_SLIDE_TITLE_TRUNCATE = 60` chars so 30pt fits in the
   two-line title box.
4. **Per-slide content caps.** `_MAX_STACKS_PER_SLIDE = 5`,
   `_METHOD_SECTIONS_PER_SLIDE = 2`, `_EVALUATION_SECTIONS_PER_SLIDE = 2`. KPI
   blocks and core-observation callouts are ALWAYS split onto their own slide
   (`_add_kpi_slide`, separate core-observation slide). Never balance "stacks
   + tail callout" inside a fixed height.
5. **Semantic shape names.** Every textbox is named `title` / `meta` / `body` /
   `subhead` / `footer` / `page_number` / `kpi` / `kpi_label` / `rq_box` /
   `paper_subtitle`. `pptx_edit.update_slide(..., title=...)` looks them up by
   name; never break the contract.
6. **i18n.** All template strings (section labels, "Paper N of M", "References",
   footer copy, "n.d." for missing years) flow through
   `autopapertoppt/exporters/i18n.py`. `SUPPORTED_LANGUAGES = ("en", "zh-tw",
   "zh-cn", "ja", "es", "fr", "de", "ko", "pt", "ru", "it", "vi", "hi",
   "id")` — every language has every key, enforced by the
   `test_every_language_has_every_key` test. Untranslated locales fall back
   silently to `en` via `normalise_language`.
7. **No overflow regressions.** When changing the deck, run a headless
   text-fit check that estimates the wrapped-text height of every shape (see
   `scripts/regen_ieee_thesis_style.py` for an example deck and
   `exports/v3-final-overflow-check.txt` for the inspection format).

### LLM-as-agent vs Python pipeline

Enrichment (PDF → structured `PaperSummary`) has two execution paths and code
MUST keep them cleanly separated:

- **LLM-as-agent**: an MCP-aware LLM (e.g. Claude in this Code session) drives
  the workflow. The MCP tools `fetch_paper` + `fetch_pdf_text` give it
  metadata + body text; the LLM produces the structured summary in its own
  context window; `export` writes the artefacts. **No `ANTHROPIC_API_KEY` is
  required.** The MCP server's `export` tool understands `papers[*].summary`
  with the full rich-tier schema.
- **Python pipeline (auto-on when ANTHROPIC_API_KEY is set)**: the Python
  process calls Anthropic's API itself via
  `autopapertoppt/intelligence/summarise.py` and produces a rich
  thesis-style deck. Auto-enrichment is the **default** when the env var
  is present; pass `--lightweight` to skip it and `--enrich` to fail-loud
  rather than fall-back-quietly when the extras aren't installed. Default
  model is `claude-opus-4-7` (override via `--llm-model` or
  `AUTOPAPERTOPPT_LLM_MODEL`). Requires the `[intelligence]` extra.

Do not collapse these into a single path. The LLM-agent flow is the cheaper
default for interactive MCP use; the Python pipeline is for unattended
automation where no LLM is otherwise in the loop.

**Preferred path when an LLM is in the loop (CRITICAL).** Rich
thesis-style PPT is the default deliverable. Lightweight is a fallback,
never the goal when an LLM agent is in the loop.

Decision tree:

1. `ANTHROPIC_API_KEY` set? → CLI auto-enriches; just run it.
2. No key but you (an LLM agent) drive the session → **you write the
   rich summary yourself**. The lightweight per-paper `.pptx` the CLI
   just emitted is an intermediate artefact, not the deliverable. Read
   each PDF, hand-author a `PaperSummary` with rich-tier fields, drop a
   `scripts/regen_<query>.py`, run it.
3. No LLM in the loop (CI / cron / unattended) → lightweight is
   acceptable.

Anti-patterns (do NOT):

* Tell the user "set `ANTHROPIC_API_KEY` for a rich deck" while you
  yourself are the LLM that could write the summaries. You are the
  agent precisely so they don't have to acquire a separate key.
* Treat the per-paper lightweight `.pptx` as the final deliverable.
* Stop after `download_pdfs` reports N PDFs saved — that is the start
  of the rich-authoring phase, not the end.
* Invent numbers, RQs, contributions, or limitations that don't trace
  back to the paper's text.
* Fabricate `url` / `doi` / `arxiv_id` from memory when hand-authoring
  a `Paper`. Publisher URL paths cannot be guessed (AAAI uses numeric
  IDs like `v40i5.37389`, not author slugs; IEEE uses `arnumber`; ACM
  uses opaque DOIs). Always copy these fields verbatim from the search
  xlsx — see "URL / DOI verification" below.
* Leave irrelevant downloads in the run directory. The search keyword
  matching is keyword-based — a query like "code review" can return a
  paper on object detection literature review; "Claude code" can match
  a Viterbi decoder paper because both contain "code". Once you read
  the abstracts and decide a paper is off-topic for the user's actual
  intent, **delete `exports/<run>/pdfs/<key>.pdf` and the lightweight
  `exports/<run>/<key>.pptx`** so the run dir cleanly reflects the
  deliverable. Keep the aggregate xlsx / bib intact — those are the
  honest record of what the search returned. See "Pruning irrelevant
  downloads" below for the concrete procedure.

Worked example: `scripts/regen_llm_security_batch.py` ships 7
hand-authored rich summaries built exactly this way.

Per-paper flow:

1. Get the PDF into the exports dir, one of two ways:
   * `--paper <url-or-id>` fetches metadata and downloads the PDF
     (`exports/<run>/pdfs/<key>.pdf` lands automatically); or
   * `--pdf <local-path>` when the user supplied a PDF themselves —
     the file is copied into `exports/<run>/pdfs/` and a single-paper
     collection is built with `source="local"`. Use `--title --authors
     --year --venue --doi --arxiv-id` to override metadata when the
     filename heuristic isn't right.
2. Read the PDF yourself. If the body is too large for the editor's Read
   tool, run `pypdf` via the project's `intelligence.pdf._extract_text` to
   dump plain text, then chunk it. Do not re-implement PDF extraction.
3. Hand-author a `PaperSummary` populated with the rich-tier fields
   (`pain_points`, `research_question`, `contributions_detailed`,
   `headline_metrics`, `technique_table`, `method_sections`,
   `evaluation_sections`, `system_flow`, `research_questions`,
   `rq_results`, `core_observation`, `limitations`, `future_work`) — only
   include numbers / claims that appear verbatim in the paper. Set
   `model="<your model id> (LLM-as-agent, read N-page PDF)"` and
   `raw_text_chars` to the extracted length so provenance is visible on
   the deck.
4. Call the exporter — either via the MCP `export` tool (when running
   against a live MCP server) or directly in Python by constructing a
   `Paper` with `summary=…`, wrapping it in a `PaperCollection`, and
   passing it to `export_collection(...)`. Save the script under
   `scripts/regen_<authoryear>_<slug>.py` so the regen is reproducible.
5. **Canonical filename, no `-rich` suffix.** Set
   `filename_stem=paper.bibtex_key()` so the rich deck overwrites the
   CLI's lightweight emit at the same path. One `.pptx` per paper, the
   rich one. Do not keep both — lightweight is not a deliverable.
   Language variants are the only exception (e.g. `f"{key}-zh-tw"`).
6. Cap `contributions_detailed` at ≤ 4 entries (the contributions slide's
   stack layout overshoots the 7.05" footer guard above that). Run the
   headless overflow check from the **Slide Deck Rules** section before
   handing the deck back.

Working templates: `scripts/regen_llm_security_batch.py` (batch, 7
papers), `scripts/regen_ling2026_agent_skills.py` (single paper en),
`scripts/regen_ling2026_agent_skills_zh_tw.py` (single paper zh-tw),
`scripts/regen_ieee_thesis_style.py` (single paper).

#### URL / DOI verification (mandatory before handing the deck back)

Publisher URL paths **cannot be guessed**. The author-slug pattern an
agent might invent (`view/fang2026`) is never the real AAAI URL —
AAAI uses numeric IDs (`v40i5.37389`); IEEE uses an opaque `arnumber`;
ACM uses opaque DOIs like `10.1145/3411764.3445005`. A fabricated URL
in the slide deck is worse than no URL — it visibly points the user
at a 404.

The rule: when hand-authoring a `Paper`, copy `url` / `doi` /
`arxiv_id` **verbatim from the same search's xlsx**. Never write them
from memory; never construct them from the title.

Concrete workflow:

1. Run the user's search:
   `py -m autopapertoppt --query "..." --out ./exports/<run>/`.
   The aggregate xlsx is written to
   `exports/<run>/<slug>-<YYYYMMDD-HHMMSS>.xlsx` with columns
   `# | Title | Authors | Year | Source | Indexed via | DOI | URL | PDF | Citations | Abstract`.
2. For every paper you author a `PaperSummary` for, copy:
   * **column 7 (DOI)** → `Paper.doi`
   * **column 8 (URL)** → `Paper.url`
   * extract the arXiv id from column 8 when the URL is on `arxiv.org`
   * leave any empty column as `None` — do NOT fabricate to fill it.
3. Strip a trailing `v1` / `v2` version suffix from arxiv URLs:
   `https://arxiv.org/abs/2506.09580v1` → `arxiv_id="2506.09580"`,
   `url="https://arxiv.org/abs/2506.09580"`.
4. After the regen script finishes, audit `Paper.url` vs. the xlsx
   column 8 for every entry — any mismatch beyond a version suffix is
   a fabrication and must be fixed before the deck ships:

   ```python
   from openpyxl import load_workbook
   from scripts.regen_<run> import ALL_PAPERS
   real = {sh.cell(row=r, column=2).value: sh.cell(row=r, column=8).value
           for sh in [load_workbook("exports/<run>/<slug>-<ts>.xlsx")["Papers"]]
           for r in range(2, sh.max_row + 1)}
   for p in ALL_PAPERS:
       actual = next((u for t, u in real.items()
                      if p.title[:30] in (t or "")), None)
       if actual and not (p.url == actual
                          or p.url.split("v")[0] == actual.split("v")[0]):
           print(f"! {p.bibtex_key()} authored {p.url} vs real {actual}")
   ```

   This audit caught two fabrications in `regen_llm_security_batch.py`
   (Wen 2025: wrong AAAI volume; Fang 2026: invented `view/fang2026`
   path) before the user noticed. Re-run it whenever you add a new
   paper to a regen script.

#### Pruning irrelevant downloads (mandatory before handing the deck back)

The search engine is keyword-based, so off-topic papers will slip in:
a query like "Claude code" returned a Viterbi decoder paper because
both contain "code"; "LLM code review" returned a paper on object
detection literature review for the same reason. Once you read the
abstracts and decide a paper is **off-topic for the user's actual
intent**, prune the run directory:

```python
from pathlib import Path

run_dir = Path("exports/<run>")
irrelevant_keys = (
    "key-of-off-topic-paper-1",
    "key-of-off-topic-paper-2",
)
for key in irrelevant_keys:
    for path in (run_dir / "pdfs" / f"{key}.pdf",
                 run_dir / f"{key}.pptx"):
        if path.exists():
            path.unlink()
```

What to delete:

- `exports/<run>/pdfs/<key>.pdf` — the downloaded PDF
- `exports/<run>/<key>.pptx` — the CLI's lightweight emit

What to **keep**:

- The aggregate `exports/<run>/<slug>-<timestamp>.xlsx` and `.bib` —
  they are the honest record of what the search returned. Pruning them
  would rewrite history. Off-topic papers staying in the xlsx is fine
  because the user can see the full search outcome there.
- The rich `*-zh-tw.pptx` / `*.pptx` files for the *relevant* papers
  you hand-authored.

Decision rule: a paper is off-topic when its actual research question
doesn't match the user's intent. "Claude (Sonnet 4.6) across six
languages" is off-topic for a "Claude Code code review" query because
the paper is about Claude the model's multilingual ability, not the
Claude Code agentic tool. Borderline cases get a rich summary (better
to over-include than to silently drop a possible match).

### Suppression Comment Conventions

Use the right comment for the right tool. They are NOT interchangeable.

| Tool          | Comment form                            | Placement   | Notes                                               |
|---------------|-----------------------------------------|-------------|-----------------------------------------------------|
| ruff / flake8 | `# noqa: <CODE>` (e.g. `# noqa: S310`)  | line-level  | Must list specific codes — never bare `# noqa`.     |
| bandit        | `# nosec B<NNN>` (e.g. `# nosec B310`)  | line-level  | ruff's `# noqa` does NOT suppress bandit.           |
| SonarCloud    | `# NOSONAR`                             | line-level  | Use for hotspots that cannot be config-skipped.     |
| pylint        | `# pylint: disable=<name>`              | line-level  | Prefer refactor over suppression.                   |

Every suppression MUST include a brief justification on the same line
(`# nosec B310  # scheme validated immediately above`). Unexplained suppressions will not
pass review.

### Project-Wide Skip Configuration

Systemic false positives are skipped at the config level, never with per-line comments.
The authoritative skip lists live in:

- `.bandit` (YAML, with per-rule justification comments) — the canonical source.
- `pyproject.toml` `[tool.bandit]` — mirror for tooling that only reads `pyproject.toml`.
  Keep both files in sync.

When adding a new bandit skip:
1. Add it to `.bandit` with a `# B<NNN>: <one-line reason>` comment.
2. Mirror it in `pyproject.toml` `[tool.bandit].skips`.
3. Verify locally: `py -m bandit -c pyproject.toml -r autopapertoppt/ sources/` must return
   `No issues identified`.

### Local CI Reproduction

Before pushing, reproduce each engine locally so CI does not have to tell you:

- **bandit**: `py -m bandit -c pyproject.toml -r autopapertoppt/ sources/`
  (the `-c` flag is REQUIRED — without it, bandit ignores the skip config).
- **ruff**: `py -m ruff check .`
- **pytest**: `py -m pytest tests/`
- **search-mode smoke**:
  `py -m autopapertoppt --query "diffusion models" --source arxiv --max 3
   --out ./smoke/` — confirm `.pptx`, `.xlsx`, `.bib` produced (the new search
  default).
- **single-paper smoke**:
  `py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" --out
   ./smoke/single/` — confirm `.pptx` + `.bib` only (single-paper default).
- **deck-overflow smoke** (when touching pptx/i18n):
  inspect every shape's wrapped-text height ≤ its box AND ≤ 7.05" footer
  guard. See `scripts/regen_ieee_thesis_style.py` for the inspection pattern.

### Environment

- Python 3.12+ (developed against 3.14) in the project-local `.venv/`. Activate
  with `.venv\Scripts\Activate.ps1` (PowerShell) or `.venv\Scripts\activate.bat`
  (cmd) before running `py -m ...` commands, OR call the venv interpreter
  directly: `.venv\Scripts\python.exe -m pytest tests/`.
- Required runtime deps: `httpx`, `pydantic`, `pydantic-settings`, `defusedxml`,
  `python-pptx`, `openpyxl`, `bibtexparser`, `beautifulsoup4`, `lxml`,
  `markdown-it-py`.
- Optional extras (declared in `pyproject.toml`):
  - `[intelligence]` — `pypdf` + `anthropic` for PDF extraction + `--enrich`.
  - `[mcp]` — the `mcp` SDK for running / registering the MCP server.
  - `[web]` — reserved for the future FastAPI / Streamlit UI.
  - `[dev]` — all of the above + `pytest*`, `ruff`, `bandit`.

### Env vars

| Variable | Used by | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` Python path | LLM auth. **NOT** needed for the LLM-as-agent path over MCP. |
| `AUTOPAPERTOPPT_LLM_MODEL` | `--enrich` | Override the default `claude-opus-4-7`. |
| `AUTOPAPERTOPPT_S2_API_KEY` | Semantic Scholar plugin | Higher rate limit on `api.semanticscholar.org`. Optional. |
| `AUTOPAPERTOPPT_NCBI_API_KEY` | PubMed plugin | Raises NCBI's anonymous limit (3/s) to 10/s. Optional. |
| `AUTOPAPERTOPPT_CONTACT_EMAIL` | PubMed (`tool` / `email`), ACM/Crossref (`mailto`) | Puts Crossref in the polite pool. |
| `AUTOPAPERTOPPT_ENABLE_IEEE_SCRAPING` | IEEE plugin (scraping path) | Must be `=1`. IEEE Xplore ToS-grey. Not needed when `AUTOPAPERTOPPT_IEEE_API_KEY` is set. |
| `AUTOPAPERTOPPT_IEEE_API_KEY` | IEEE plugin (API path) | Switches the IEEE plugin to the official Xplore API (`ieeexploreapi.ieee.org`). Surfaces `pdf_url` for papers in the key's subscription scope. Apply at https://developer.ieee.org/. |
| `AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN` | ACM / Crossref plugin | Crossref Plus subscriber token; attached as `Crossref-Plus-API-Token: Bearer …`. Raises rate limits + cache freshness. |
| `AUTOPAPERTOPPT_SPRINGER_API_KEY` | Springer plugin | Free key from https://dev.springernature.com/. Required — the Springer plugin raises `ConfigError` without it. Covers Nature, Scientific Reports, Lecture Notes in CS. |
| `AUTOPAPERTOPPT_PDF_COOKIES_FILE` | PDF downloader | Path to a Netscape-format `cookies.txt` file. Cookies whose domain matches a PDF URL's host are attached on the request. Off by default. Use when publishers return 403 to anonymous requests for paywalled PDFs you have institutional access to. **You are responsible for compliance with each publisher's terms of service.** A startup warning fires when the env var is loaded. |
| `AUTOPAPERTOPPT_ENABLE_SCHOLAR_SCRAPING` | Scholar plugin | Must be `=1`. Google Scholar terms forbid scraping; off by default. |
| `AUTOPAPERTOPPT_LOG_LEVEL` | logger | `INFO` default; set `DEBUG` for verbose tracing. |
