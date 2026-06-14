# Architecture

How ThesisAgents is organised, why those boundaries exist, and
how a single keyword turns into a thesis-style `.pptx`.

## One-paragraph summary

A user (a human, a CLI process, an MCP-aware LLM, or the desktop
GUI) submits a `Query`. The pipeline fans out to per-source
**Fetcher** plugins, normalises each plugin's payload into a
shared `Paper` record, deduplicates by DOI / arXiv-ID / fuzzy
title, ranks by recency + citation count, optionally enriches
each paper with a structured `PaperSummary`, and hands the
resulting `PaperCollection` to one or more **Exporter** plugins
(`.pptx`, `.xlsx`, `.bib`, `.md`, `.json`, `.ris`, `.csv`, `.csl.json`).
All outbound HTTP
goes through one HTTPS-only client per source, all per-source
rate limits live in a token bucket, and every fetcher test uses
a recorded fixture (zero live HTTP in the test suite).

## Layered view

```
┌─────────────────────────────────────────────────────────────┐
│  Surfaces                                                   │
│  CLI · MCP server · Desktop GUI (PySide6) · Python library  │
├─────────────────────────────────────────────────────────────┤
│  Pipeline                                                   │
│  Query → fetch → normalise → dedup → rank → enrich → export │
├─────────────────────────────────────────────────────────────┤
│  Core domain                                                │
│  Paper · PaperCollection · PaperSummary · RqResult · Query  │
├──────────────────────────┬──────────────────────────────────┤
│  Fetchers                │  Exporters                       │
│  arxiv, semantic_scholar │  pptx (3 tiers) · xlsx · bibtex  │
│  openalex, pubmed, …     │  markdown · json · pptx_edit     │
├──────────────────────────┴──────────────────────────────────┤
│  Infra                                                      │
│  HTTPS-only client · token-bucket rate limit · cache · i18n │
└─────────────────────────────────────────────────────────────┘
```

Dependencies only flow downward. Surfaces depend on the pipeline,
the pipeline depends on the core domain + fetchers + exporters,
and everything depends on infra. **An exporter never imports a
fetcher** — it only consumes a `PaperCollection`.

## Top-level layout

```
ThesisAgents/
├── thesisagents/                 # main package — core runtime
│   ├── core/                       # domain (Paper, Query, dedup, rank, pipeline)
│   ├── fetchers/                   # HTTPS-only http client + Fetcher base
│   ├── exporters/                  # pptx / xlsx / bib / md / json / ris / csv / csl + pptx_edit + i18n
│   ├── intelligence/               # PDF + Anthropic summariser ([intelligence] extra)
│   ├── mcp/                        # FastMCP server registering 12 tools ([mcp] extra)
│   ├── gui/                        # PySide6 desktop UI ([gui] extra)
│   ├── utils/                      # logging, path safety, async helpers
│   ├── cli.py                      # argparse CLI
│   └── __main__.py                 # `python -m thesisagents`
├── sources/<name>/                 # per-source plugins (arxiv, pubmed, …)
│   ├── __init__.py                 # exports `fetcher_class`
│   ├── fetcher.py                  # Fetcher subclass
│   ├── parser.py                   # payload → Paper
│   └── config.py                   # RateLimit + endpoint URL
├── tests/                          # pytest suite + recorded fixtures
├── docs/                           # Sphinx (en + 13 language stubs)
├── scripts/                        # regen / fixture-record helpers
└── pyproject.toml                  # metadata, ruff, bandit, extras
```

## Core vs source plugins

The split between `thesisagents/` and `sources/<name>/` is
**dependency surface and failure isolation**, not "anything
source-related is a plugin."

A feature is a **source plugin** when ANY of the following holds:

1. It needs a heavy or optional runtime dep (vendor SDK, Selenium).
2. It needs failure isolation — a flaky upstream should not break
   the rest of the pipeline.
3. It needs an independent release cadence — a Scholar HTML layout
   change should ship without re-shipping the engine.

A feature stays in **core** when:

- It runs on the default dep set (no extras).
- It serves the everyday workflow every user expects to work
  (arxiv, semantic_scholar, pubmed, openalex are core; scholar
  scrape and ieee scrape are opt-in plugins).

Concrete consequence: a flaky ACM endpoint cannot break an arXiv
search. Each fetcher catches its own exceptions and returns an
empty result; the pipeline aggregates whatever non-empty results
came back.

## The pipeline

```
                Query
                  │
                  ▼
          ┌───────────────┐
          │ load_fetcher  │  one per Query.source
          └───────────────┘
                  │
                  ▼ (asyncio.gather, per-source semaphore)
       ┌──────────┴──────────┐
       ▼          ▼          ▼
   Fetcher     Fetcher     Fetcher     ← per-source token-bucket rate limit
   .fetch()    .fetch()    .fetch()       on the HTTPS-only async client
       │          │          │
       └──────────┼──────────┘
                  ▼
            list[Paper]
                  │
                  ▼
            ┌──────────┐
            │ dedupe   │  by DOI → arXiv ID → SHA-256(title+1st-author+year)
            └──────────┘
                  │
                  ▼
            ┌──────────┐
            │ rank     │  recency × log(citation_count)
            └──────────┘
                  │
                  ▼
        (optional) top-tier filter
                  │
                  ▼
          ┌────────────────┐
          │ oa_resolver    │  Unpaywall + arXiv title fallback —
          └────────────────┘  fills pdf_url for paywalled-source papers
                  │
                  ▼
        (optional) enrich      PDF → PaperSummary
                  │
                  ▼
          PaperCollection
                  │
                  ▼
          ┌───────────────┐
          │ Exporter      │  pptx, xlsx, bibtex, md, json, ris, csv, csl
          └───────────────┘
```

### OA PDF resolution

`thesisagents.core.oa_resolver` runs after dedup + rank + top-tier
filter. For every paper still missing `pdf_url`, five strategies fire
in order, returning the first hit:

1. **arXiv-ID direct** — if the paper carries `arxiv_id` (set by the
   openalex / pubmed / crossref / semantic_scholar parsers when the
   upstream identified an arXiv preprint), derive
   `https://arxiv.org/pdf/{arxiv_id}.pdf` directly. Zero network
   round-trip; highest precision; fastest.
2. **Unpaywall** (https://api.unpaywall.org/v2/{doi}) — free, no API
   key; needs `THESISAGENTS_CONTACT_EMAIL` for politeness. ~50M
   papers indexed.
3. **Semantic Scholar OA index** — S2's `openAccessPdf` field is
   partially disjoint from Unpaywall; when one misses, the other
   often hits. Free, no API key required (rate-limited).
4. **CORE.ac.uk** — aggregator of 200M+ OA repository items
   (institutional repos, regional preprint servers, OA journals).
   Needs `THESISAGENTS_CORE_API_KEY` (free); skipped silently when
   unset.
5. **arXiv title search** — for papers without a DOI / arxiv_id, search
   arXiv by the paper's title. Exact-match on the normalised title.

Every lookup is best-effort and never raises; a paper that resists
all five passes through with `pdf_url=None` and the downstream
paywall gate / per-paper renderer falls back to the lightweight tier.

Disabled per-run via the CLI's `--no-oa-resolve` flag or
`run_search(query, resolve_oa=False)` from Python.

### Dedup

`thesisagents.core.dedup` is a three-pass merge:

1. Strong-ID pass — papers sharing a DOI or arXiv ID are merged
   into one, keeping the most complete record (longest abstract,
   most authors, citation count from the source that has it).
2. Title pass — among papers without strong IDs, normalise the
   title (NFKC + lowercase + strip punctuation), then
   SHA-256-hash `title + first_author + year`. Identical hashes
   are merged.
3. Field union — for merged duplicates, every optional field
   ( `doi`, `arxiv_id`, `pdf_url`, `venue`, `citation_count`,
   `abstract`) is taken from whichever source had it.

The dedup pass is O(N) — the bottleneck is hashing, not the
field union step.

### Ranking

Default rank score: `0.5 · normalised_year + 0.5 · log(1 + citation_count) / 20`.

Older but heavily-cited papers (the "Attention Is All You Need"
of any field) still win against recent unknowns; very recent
papers without citations are surfaced because the recency term
keeps them in the top quartile.

Override the weight split per query via the optional `min_citations`
filter on the MCP `search` tool.

### Enrichment

Two distinct paths. The decision tree:

```
ANTHROPIC_API_KEY set?
├── yes → Python pipeline: pypdf/pymupdf extracts text,
│         thesisagents.intelligence.summarise calls the
│         Anthropic API, returns a structured PaperSummary
│         (motivation, contributions, method, results,
│         limitations + the rich tier).
└── no  → LLM-as-agent: the MCP client (e.g. Claude Code)
          calls fetch_pdf_text(), reads the text in its own
          context, writes a summary dict, passes it to export().
          No API key needed.
```

Both paths produce the same `PaperSummary` shape; the exporter
doesn't know or care which one wrote it.

## The data model

Three frozen dataclasses carry the entire flow. Their fields
are described in detail in [Data model](data_model.md); a
one-line summary:

- **`Query`** — keywords, sources, max_results, year window, flags.
- **`Paper`** — title / authors / year / venue / abstract / URLs /
  IDs / citation count / optional `summary: PaperSummary`.
- **`PaperCollection`** — `query: Query` + `papers: tuple[Paper]`.

Frozen by design: any "edit" creates a new instance via
`dataclasses.replace(paper, summary=...)`. This makes the pipeline
trivially safe to fan out across asyncio tasks.

## Surfaces

Each surface is a thin adapter over the same pipeline.

### CLI (`thesisagents.cli`)

`argparse` parses flags into a `Query` / single-paper identifier.
The CLI is the only surface that does its own `asyncio.run`; the
library APIs return coroutines.

### MCP server (`thesisagents.mcp`)

FastMCP registers twelve tools. The agent calls them in sequence
(`list_sources` → `search` → `fetch_pdf_text` per paper →
`export`); the server is stateless across tool calls so the
agent's context is the only place state lives. See [MCP doc](mcp.md).

### Desktop GUI (`thesisagents.gui`)

PySide6 widgets call the same `run_search` / `export_collection`
that the CLI does, but on a `QThreadPool` worker so the UI thread
stays responsive. See [GUI doc](gui.md).

### Python library

Anything in `thesisagents.core.pipeline` is importable from
your own code:

```python
import asyncio
from thesisagents.core.models import Query
from thesisagents.core.pipeline import run_search
from thesisagents.exporters import export_collection
from thesisagents.core.models import ExportOptions

async def main():
    q = Query(keywords="transformer", sources=("arxiv",), max_results=10)
    collection = await run_search(q)
    written = export_collection(
        collection,
        ExportOptions(formats=("pptx", "bibtex"), out_dir="./exports"),
    )
    print(written)

asyncio.run(main())
```

## Infrastructure

### HTTPS-only HTTP client

`thesisagents.fetchers.http.get_client(source)` returns a
per-source `httpx.AsyncClient` that:

- Refuses any URL whose scheme isn't `https` (refused both at
  request time AND mid-redirect).
- Carries the source's User-Agent.
- Routes every request through the source's token-bucket
  rate limiter.
- Retries 429 / 5xx with exponential backoff + jitter.
- Pools connections for the process lifetime.

There is exactly **one** client per source per process. Re-entering
the pipeline reuses the same client. `shutdown_clients()` closes
all clients at CLI exit; it's tolerant of clients whose loop
already closed (test-suite isolation requirement).

### Rate limiting

Token bucket in `thesisagents.fetchers.rate_limit`. Each source
declares its bucket parameters in `sources/<name>/config.py`:

```python
RATE_LIMIT = RateLimit(
    requests_per_second=1 / 3.0,   # 1 request every 3 s
    burst=1,
    jitter_seconds=0.5,
)
```

The bucket is a decorator on the HTTP client — **retries also go
through it**. There is no way to bypass the bucket without
deleting code from the source plugin.

### Cache

`thesisagents.core.cache` provides an SHA-256-keyed disk cache
for raw responses. Default TTL is 24h; override per-source if
needed. Tests redirect the cache root to `tmp_path` so they never
touch the user's cache.

### i18n

Two separate tables to balance scope:

- `thesisagents.exporters.i18n` — slide-deck strings ("Agenda",
  "References", "Paper N of M", "Background", etc.) in all 14
  supported languages. Coverage enforced by
  `tests/test_i18n.py::test_every_language_has_every_key`.
- `thesisagents.gui.i18n` — UI label strings, identical
  language set, coverage enforced by `tests/gui/test_i18n.py`.

Adding a new key requires filling in all 14 languages.

## Source plugin contract

A source plugin lives at `sources/<name>/` and must expose:

- `sources/<name>/__init__.py` setting `fetcher_class = FetcherClass`.
- `sources/<name>/fetcher.py` with a `Fetcher` subclass.
- `sources/<name>/parser.py` converting raw payloads → `Paper`.
- `sources/<name>/config.py` declaring the `RateLimit`.

The pipeline finds plugins by injecting `sources/` into
`sys.path` at startup (`thesisagents.app.source_manager`). At
fetch time it imports `<name>`, reads `fetcher_class`, and
instantiates it with the shared HTTP client + cache.

Full authoring guide: [Source plugin authoring](source_plugins.md).

## Slide-deck rendering tiers

The `.pptx` exporter dispatches to one of three layouts based on
how much info each paper carries:

| Tier | Trigger | Slides per paper |
|---|---|---|
| Lightweight | only `abstract` populated | 4–6 (cover + agenda + Background / Approach / Findings sentence buckets + references) |
| Enriched-flat | `Paper.summary` has `motivation` / `contributions` / `method` / `results` / `limitations` / `takeaways` | one slide per non-empty section |
| Thesis-style | `Paper.summary.has_rich_fields()` is true (pain_points, research_question, contributions_detailed, headline_metrics, technique_table, evaluation_sections, system_flow, research_questions, rq_results, core_observation, limitations, future_work, ...) | 20+ slides per paper |

All three tiers share the same shape-naming convention so
`pptx_edit.update_slide(..., title=...)` looks up shapes by name.

### Post-build visual-identity passes

After the chosen tier builds the deck on the light palette, three
non-invasive walk-and-rewrite passes run before the file is saved:

1. **Typography** (`_apply_typography(prs, language)`) — walks every
   text run, writes `<a:latin typeface=…>` AND `<a:ea typeface=…>` on
   the run's XML based on `_FONT_FAMILIES[language]`. Setting only
   `run.font.name` (the Latin slot) leaves CJK glyphs in PowerPoint's
   default East-Asian font; both slots matter.
2. **Accent geometry** (`_decorate_with_accents(prs)`) — adds the
   `accent_top` bar to every content slide and an `accent_left` band
   to the cover. Both are full-width / full-height navy rectangles
   the user never sees as separate shapes but instantly reads as
   "this deck has an identity".
3. **Dark-mode recolour** (`_apply_dark_mode(prs)`, runs when
   `ExportOptions.dark_mode=True`, which is opt-in — the default deck
   is light) — walks every
   slide / shape / run / table cell and swaps light-palette RGBs to
   their dark equivalents via `_LIGHT_TO_DARK_TEXT` + `_LIGHT_TO_DARK_FILL`
   dicts. The slide background switches to `#12151B`; body text goes
   to `#E5E7EB`; the teal accent (`#0E7490`) goes to a brighter
   `#2DD4BF`. The pass is intentionally non-invasive: it doesn't
   refactor the 100+ direct `_BRAND_*` constant references in the
   builders, it just rewrites RGBs after the fact.

The three passes ship with regression tests in
`tests/test_exporters.py`: `test_pptx_default_is_dark_mode`,
`test_pptx_dark_mode_has_no_invisible_runs` (no run is `rgb=None` or
black), `test_pptx_dark_mode_no_light_text_on_light_fill` (no
near-white text inside a near-white-filled callout), and
`test_pptx_no_red_text_runs` (red `#C0392B` is banned for text).

## Why the design choices

| Choice | Reason |
|---|---|
| **Per-source plugins, not adapters** | A flaky upstream (Scholar layout change, IEEE token expiry) shouldn't break the whole pipeline. Plugins fail in isolation. |
| **Async I/O, sync exporters** | Network is parallelisable; rendering a `.pptx` is CPU-bound and finishes in milliseconds — no win from making it async. |
| **One HTTPS-only client per source** | Shared connection pools + token bucket. Multiple clients per source would defeat both. |
| **Frozen dataclasses** | Trivially thread/coroutine-safe; "edits" create new instances via `dataclasses.replace`. |
| **Recorded fixtures only** | Tests run offline, deterministically, in <30 s. Live HTTP would make CI flaky and rate-limited. |
| **Two i18n tables (UI vs deck)** | Lets the UI ship with fewer translations than the deck if needed; today both cover all 14 languages, but the split keeps optionality. |
| **No global mutable state** | Singletons (HTTP clients, cache handle, rate-limit buckets) are encapsulated in module-level classes. Streamlit `st.session_state` is the only mutable per-session state, and it's per-session by design. |

## Performance notes

- The bottleneck for a typical search is **network latency**, not
  CPU. Async fan-out across sources brings a 10-source search
  down from `sum(latency)` to `max(latency)`.
- The `pptx` exporter is the single biggest CPU consumer — about
  200 ms per paper for the thesis-style tier. Lightweight tier is
  10× faster.
- Dedup is O(N) on the number of papers; with `--max 200` × 11
  sources that's ~2200 papers max, and dedup still finishes in
  under 50 ms.
- The `[intelligence]` extra's Anthropic API call is the dominant
  cost when `--enrich` is on — typically 5–15 s per paper. The
  pipeline batches these with a per-source semaphore.

See `thesisagents/utils/profiling.py` for `with section("name"):`
helpers if you're chasing a regression.
