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
│  HTTPS-only client · token-bucket rate limit · i18n         │
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
│   ├── library/                    # SQLite literature library kept across runs
│   ├── evaluation/                 # offline search-quality benchmark (see docs/search-quality.md)
│   ├── mcp/                        # FastMCP server registering 18 tools ([mcp] extra)
│   ├── gui/                        # PySide6 desktop UI ([gui] extra)
│   ├── utils/                      # logging, path safety, async helpers
│   ├── cli.py                      # argparse CLI
│   └── __main__.py                 # `python -m thesisagents`
├── thesisagents/sources/<name>/    # per-source plugins (arxiv, pubmed, …)
│   ├── __init__.py                 # exports `fetcher_class`
│   ├── fetcher.py                  # Fetcher subclass + RateLimit + endpoint URL
│   └── parser.py                   # payload → Paper
├── tests/                          # pytest suite + recorded fixtures
├── docs/                           # Sphinx (en + 13 language stubs)
├── scripts/                        # regen / fixture-record helpers
└── pyproject.toml                  # metadata, ruff, bandit, extras
```

## Core vs source plugins

The split between core modules and `thesisagents/sources/<name>/` is
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
            │ dedupe   │  group on ANY of: DOI / arXiv ID / SHA-256(title+1st-author+year)
            └──────────┘
                  │
                  ▼
            ┌──────────┐
            │ rank     │  relevance + recency + citation, the three
            └──────────┘  parts kept per paper (rank_with_scores)
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
        (optional) snowball    citation links → more papers, each with
                  │            the path that reached it
                  ▼
        (optional) enrich      PDF → PaperSummary
                  │
                  ▼
          PaperCollection      + diagnostics: score per paper and
                  │              advisory keep / review / prune
                  ▼
        (optional) library     merge into the SQLite library, which
                  │            also remembers the preflight verdicts
                  ▼
          ┌───────────────┐
          │ preflight     │  every DOI at doi.org, every URL once;
          └───────────────┘  a wrong / unreachable one stops the export
                  │
                  ▼
          ┌───────────────┐
          │ Exporter      │  pptx, xlsx, bibtex, md, json, ris, csv, csl
          └───────────────┘
```

### Citation providers and snowballing

`core/snowball.py` grows a result along citation links: backward to the
papers a seed cites, forward to the papers that cite it. It runs after
ranking, on the top results, and the papers it finds join the collection
before the export preflight.

The citation logic is not in the search plugins' fetchers and not in the
exporters. It sits behind `fetchers/citations.py::CitationProvider`
(`references(paper, limit)`, `cited_by(paper, limit)`), implemented by a
`citations.py` inside each plugin that has citation data:

| Provider | Directions | Resolves a paper by |
|---|---|---|
| `openalex` | both | DOI, or its own work ID |
| `semantic_scholar` | both | DOI, arXiv ID, or its own paper ID |
| `crossref` | references only, and only those with a DOI | DOI |

For each paper and direction the providers are asked in that order until
one returns papers. `CitationNotAvailableError` ("I have no answer for
this paper") moves on quietly. Any other error is recorded in the
result and the next provider is asked, the same containment the search
applies to a failing source.

Four properties keep an unbounded graph in check:

- **Bounds.** Depth 1 by default and at most 3, a cap per seed and
  direction, and a cap on the total. A paper is expanded at most once.
- **One identity model.** Found papers are matched with
  `dedup.IdentityIndex`, the incremental form of `dedupe`: same DOI /
  arXiv ID / title-hash keys, same guard against merging two papers
  whose DOIs disagree. A paper reached along two paths is one paper.
- **Provenance.** Each discovered paper keeps the first path that
  reached it as a `PaperRelation(source_key, target_key, relation,
  provider, depth)`. Levels are expanded in order, so the first path is
  also a shortest one. Every link seen is kept for a citation graph.
- **Relevance is scored.** Discovered papers go through
  `rank_with_scores` against the query. A citation link is not treated
  as evidence that a paper is on topic.

The relationship lives in `PaperRelation`, outside `Paper`, because one
paper can be reached along many paths and a list of them does not
belong in a bibliographic record.

### Literature library

`thesisagents/library/` keeps what the runs find in one SQLite file.
It is a layer of its own beside the exporters: it reads and writes the
core models and nothing in `core/` imports it.

```
run_search / snowball ──► PaperCollection ──► Library.add_collection
                                                   │  merge on identity keys
                                                   ▼
                                   papers · runs · observations
                                   relations · verifications
                                                   │
        Library.search / .collection ◄─────────────┤
                    │                              │
                    ▼                              ▼
              exporters              LibraryVerificationCache
                                     (the export preflight's memory)
```

Three decisions shape it:

- **One identity model.** A stored paper is matched with the same keys
  and the same two functions search de-duplication uses
  (`Paper.identity_keys`, `dedup.fuzzy_link_allowed`,
  `dedup.merge_papers`). An import therefore merges exactly the records
  `dedupe` would have merged had they arrived in one search, and adding
  a search twice changes no paper count.
- **The relationship model is the snowball's.** Citation links are
  stored as the `PaperRelation` records snowballing produces, between
  rows instead of keys. That is why the citation providers were built
  first: the library persists a model that already existed.
- **Only passing verdicts are reused.** The preflight's verdicts are
  stored with a timestamp. One that lets an export through is reused
  for 30 days, a failure never, because a reused failure would block
  exports with no request made that could clear it.

The schema carries an explicit version (`PRAGMA user_version`) and an
application id. `schema.prepare` brings an older file up to date one
migration at a time, each in a transaction, and refuses a newer one or
a file that is not a library. WAL mode lets other processes read while
one writes.

Search inside the library is not SQL text matching. `Library.search`
scores the stored papers with `rank_with_scores`, so a library lookup
understands a query the way a search does (stemming, phrases, acronym
expansion, CJK tokenisation) and returns the same score breakdown.

### Export preflight

`export_collection` runs `core/export_validation.py` before any
exporter. Each paper's DOI is checked for syntax and then looked up at
the doi.org handle API, and each URL gets one request that reads only
the response headers. A wrong or unreachable identifier raises
`IdentifierVerificationError` (an `ExportError`) carrying the full
report, and no file is written. `ExportOptions(verify_identifiers=False)`
skips the check and logs a warning.

Three choices keep a default-on gate from blocking honest exports:

- **Publisher pages are not requested.** A URL on a host that needs a
  real browser (the list in `fetchers/webrunner_pdf.py`) would answer a
  plain client with 403. The DOI lookup stands in for it, and the DOI
  registry is not behind a bot wall.
- **"Could not check" does not block.** HTTP 401 / 403 / 429, a
  `file://` URL and a browser-only host end as `skipped`. Only a
  definite failure (`invalid`) or no answer at all (`unreachable`,
  `timeout`, each after one retry) stops the export.
- **Verdicts are cached.** The CLI checks once, right after the search,
  and hands the same `MemoryVerificationCache` to every later
  `export_collection` call, so the per-paper deck exports ask nothing
  twice.

The preflight opens its own client through `fetchers.http.scoped_client`
instead of the shared registry. `export_collection` is synchronous and
may be called from inside a running event loop (the CLI's `_run`), in
which case `utils.async_helpers.run_blocking` runs the probes on a
private loop in a worker thread. A registry client would stay bound to
that loop after it closed.

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

`thesisagents.core.dedup` is a single pass that groups on *every*
identity a paper carries, then unions the fields:

1. Identity keys — `Paper.identity_keys()` returns up to three keys
   per record: `doi:<lowercased>`, `arxiv:<version-stripped>`, and
   always a fuzzy `hash:<sha256(canonical_title + first_author_surname
   + year)>`. Two papers sharing **any** key are the same paper, so a
   DOI-less ACM record and a DOI-carrying OpenAlex record of the same
   work still meet. A record arriving later can also join two earlier
   groups transitively (an arXiv record and a publisher record united
   by a third that carries both IDs).
2. Conflict guard — a *fuzzy* match alone never merges two records
   whose DOIs (or arXiv IDs) disagree; same title + author + year with
   two DOIs is how a workshop paper and its extended journal version
   look. A blank / punctuation-only title is likewise barred from
   linking, since `_canon_title` collapses every such title to the same
   hash. An exact DOI match is unaffected by the guard.
3. Field union — for merged duplicates, every optional field
   (`doi`, `arxiv_id`, `pdf_url`, `venue`, `citation_count`, `year`,
   `abstract`, `authors`, `summary`) is taken from whichever source had
   it, and each backfill is recorded in `Paper.provenance`. The
   canonical record's `source` / `source_id` / `url` / `title` never
   change, so links stay stable across runs.

The pass is O(N) in the common case; regrouping only walks the key
index when a record unites two existing groups, which is rare.
Measured at the full pipeline load (15 sources × 200 results = 3000
papers, heavy overlap) it completes in under 50 ms.

### Per-source statistics

`run_search` keeps one outcome per source instead of flattening the
results at once, and records for each source `requested`, `returned`,
`after_dedup` and a `status` (`ok`, `failed`, `rate_limited`,
`disabled`) in `PaperCollection.diagnostics.source_stats`.

Failure isolation is unchanged: a source that cannot be loaded or that
raises contributes nothing and the others carry on. What changed is that
the search now says so. Before, a run that lost half its sources was
indistinguishable from a run on a topic with few papers.

`after_dedup` follows from how de-duplication picks the canonical
record. The merged paper keeps the `source` / `source_id` of its first
occurrence, so it is credited to the first source whose results contain
that pair, and the values of all sources add up to the number of unique
papers. The counts are taken before the `Query` filters and the
`max_results` cut: they describe the sources, not the filtered result.

### Ranking

`core/ranking.py` scores each paper on three axes and sorts by the sum:

| Axis | Formula | Range |
|---|---|---|
| relevance | `3.0 · (query terms in the title / query terms) + 0.6 · (query terms in the abstract / query terms) + 1.0 · (adjacent query pairs adjacent in the title / adjacent query pairs)` | 0 to 4.6 (3.6 for a one-word query) |
| recency | `exp(-age_in_years / 5)` | 0 to 1 |
| citation | `0.4 · log10(citation_count + 1)` | about 2.0 at 100,000 citations |

Relevance dominates on purpose. De-duplication merges the sources'
lists and discards each source's own ordering, so without a relevance
term the merged list would sort by recency and citations alone and a
heavily cited off-topic paper would bury an on-topic one. A full title
match (3.0) outranks even a 100,000-citation paper (2.0).

Matching is more than exact words: light stemming (`transformers`
matches `transformer`), a small acronym map (`llm` matches "large
language model" and the reverse), and character bigrams for Chinese,
Japanese and Korean text.

`rank(papers, keywords)` returns the sorted papers.
`rank_with_scores(papers, keywords)` returns the same order with a
`RelevanceScore` per paper: the three axis values, the matched terms
and phrases, and one sentence per contribution. `run_search` uses the
second form and attaches the result to `PaperCollection.diagnostics`.

### Pruning recommendations

`core/pruning.py` reads those scores and labels each paper `keep`,
`review` or `prune`, naming the rule and threshold behind the label:

1. relevance below 10% of the best the query allows is `prune`, below
   30% is `review`,
2. a `review` paper that is also ten or more years old and has fewer
   than 5 citations becomes `prune`,
3. a paper whose title shares at least 85% of its terms with a
   higher-ranked paper is `review`. De-duplication keeps a workshop
   paper and its journal version apart because their DOIs differ, and
   this is where the overlap is reported.

The recommendations are advice. `run_search` attaches them to the
collection and removes nothing: a paper marked `prune` is still
returned, downloaded and exported until a person or an agent decides
otherwise. Two things never trigger a recommendation: a low citation
count on its own (a new on-topic paper has none yet), and an unknown
year or citation count (the source did not say, which is not the same
as old or uncited).

The `min_citations`, year-range and top-tier filters are separate from
ranking. They run after it, in `run_search`, for every source.

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

FastMCP registers eighteen tools. The agent calls them in sequence
(`list_sources` → `search` → optionally `snowball` → `fetch_pdf_text`
per paper → `export`). The server is stateless across tool calls, so
state lives in the agent's context, or, when it should outlast the
session, in a literature library the agent names in `library_add` /
`library_search`. See [MCP doc](mcp.md).

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
        ExportOptions(formats=("pptx", "bib"), out_dir="./exports"),
    )
    print(written)

asyncio.run(main())
```

`export_collection` verifies every paper's DOI and URL first and raises
`IdentifierVerificationError` when one is wrong or unreachable (see
"Export preflight" above). Catch it to read the structured report from
its `report` attribute, or pass
`ExportOptions(..., verify_identifiers=False)` to export without the
check.

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
declares its bucket parameters in its fetcher module:

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

### Request reuse

The shared HTTP client pools connections per source. ThesisAgents does
not currently persist API responses, so repeated searches contact the
configured sources again.

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

A source plugin lives at `thesisagents/sources/<name>/` and must expose:

- `thesisagents/sources/<name>/__init__.py` setting `fetcher_class = FetcherClass`.
- `thesisagents/sources/<name>/fetcher.py` with a `Fetcher` subclass and rate limit.
- `thesisagents/sources/<name>/parser.py` converting raw payloads to `Paper`.

The pipeline imports `thesisagents.sources.<name>`, reads
`fetcher_class`, and instantiates it with the shared HTTP client.

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

After the chosen tier builds the deck on the light palette,
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
   to `#E5E7EB`; the blue accent (`#2563EB`) goes to a brighter
   `#60A5FA`. The pass is intentionally non-invasive: it doesn't
   refactor the 100+ direct `_BRAND_*` constant references in the
   builders, it just rewrites RGBs after the fact.
4. **Template styling** (only with `ExportOptions.pptx_template`).
   `_recolor_text_without_chrome` gives white-on-navy text a dark
   colour where a template config switched the navy off, and
   `_apply_template_palette` swaps the built-in palette for the
   config's `[colors]` with the same lookup-and-swap as dark mode. It
   runs in place of the dark-mode pass, never with it: dark mode
   keeps its own palette.

### Deck templates

A user template replaces the blank layout the built-in deck sits on.
`thesisagents/exporters/template.py` holds the contract:

```
ExportOptions.pptx_template (+ pptx_template_config)
        │
        ▼
open_template ── validate ──► TemplateError (every problem, nothing rendered)
        │
        ▼
LayoutSet: role → layout        TemplateConfig: fonts, colours, chrome
        │                                   │
        ▼                                   ▼
builders call layout.add_slide(prs, role)   the post-build passes above
```

- **Roles, not indices.** Every slide has one of six roles (cover,
  section, content, table, references, qa). A role's layout is the one
  the config names, else a layout named after the role, else the
  content layout, else (for content) the blank layout. The exporter
  used to take `slide_layouts[6]`, which is blank only in
  python-pptx's own template.
- **The exporter still draws the slide.** A layout contributes its
  artwork. Its placeholders are removed from each new slide, and the
  exporter places its named text boxes as before, so geometry, the
  content caps and the overflow check hold on any template. The one
  opt-in exception is the slide title, which a config can send into
  the layout's title placeholder for content, table and reference
  slides.
- **Validation is the first step of the export**, on the same
  presentation object that is then filled, and the CLI runs it before
  the search. `validate_template()` exposes the check on its own.
- **Fixed on purpose**: font sizes and margins. The config parser
  refuses them with the reason.

The built-in path goes through the same `LayoutSet` with every role on
the blank layout, so there is one code path and the built-in deck is
unchanged. User-facing reference: [Deck templates](pptx_templates.md).

The passes ship with regression tests in
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
| **Controlled global state** | HTTP clients and rate-limit buckets are encapsulated in module-level registries and reset by test fixtures. |

## Performance notes

- The bottleneck for a typical search is **network latency**, not
  CPU. Async fan-out across sources brings a 10-source search
  down from `sum(latency)` to `max(latency)`.
- The `pptx` exporter is the single biggest CPU consumer — about
  200 ms per paper for the thesis-style tier. Lightweight tier is
  10× faster.
- Dedup is O(N) on the number of papers in the common case; with
  `--max 200` × 15 sources that's 3000 papers max, and dedup still
  finishes in under 50 ms (measured with heavy cross-source overlap,
  the case that exercises the group-merge path).
- The `[intelligence]` extra's Anthropic API call is the dominant
  cost when `--enrich` is on — typically 5–15 s per paper. The
  pipeline batches these with a per-source semaphore.

See `thesisagents/utils/profiling.py` for `with section("name"):`
helpers if you're chasing a regression.
