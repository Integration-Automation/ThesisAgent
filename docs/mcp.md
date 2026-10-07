# MCP server

ThesisAgents ships a [Model Context Protocol](https://modelcontextprotocol.io/)
server so any MCP-aware LLM agent can run the same search / export /
pptx-edit operations as the CLI. The server is headless and runs over
stdio.

## Two enrichment paths

There are two ways to produce a thesis-style enriched deck:

**A) LLM-as-agent (no API key)** — preferred when an MCP-aware LLM is
already driving the workflow:

1. *(Optional)* `list_sources()` to see which plugins are enabled in
   the current process. Disabled plugins are silently skipped, so
   this prevents the agent from passing a source that won't actually
   run.
2. *Either* `search(keywords, sources, top_tier_only, ...)` for a
   multi-paper query, *or* `fetch_paper(identifier)` for a single
   paper by ID / URL / DOI / PMID.
3. *(Optional)* `download_pdfs(papers, out_dir)` to persist every
   paper's PDF on disk in one batch — useful when the agent plans to
   re-read or embed figures later.
4. `fetch_pdf_text(paper.pdf_url)` per paper to extract body text.
5. *The LLM reads the body text and produces a structured `summary` dict
   in-context* (with `pain_points`, `research_question`,
   `headline_metrics`, `technique_table`, `literature_table`,
   `method_sections`, `research_questions`, `rq_results`, …).
6. `export(papers=[{..., "summary": {...}}], language="zh-tw", ...)`.

No `ANTHROPIC_API_KEY` is needed because the LLM is the agent itself.

**B) Python pipeline (`--enrich` CLI flag)** — for non-agent automation
where there is no calling LLM. The CLI calls Anthropic's API with the PDF
text and writes the structured summary itself; this path requires
`ANTHROPIC_API_KEY` and the `[intelligence]` extra to be installed.

## Install

The server lives in `thesisagents.mcp.server`. The `mcp` SDK is the
only extra dependency:

```bash
pip install -e .[mcp]    # only the SDK
pip install -e .[dev]    # SDK + test deps (recommended)
```

That installs an `thesisagents-mcp` console script. `python -m
thesisagents.mcp` works too.

## Configure your MCP client

Add via Claude Code's CLI:

```powershell
claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp
```

Or hand-edit `~/.claude.json` (or project-local `.claude/settings.json`):

```json
{
  "mcpServers": {
    "thesisagents": {
      "command": ".venv\\Scripts\\python.exe",
      "args": ["-m", "thesisagents.mcp"]
    }
  }
}
```

If you'd rather rely on the installed console script, point at the
venv-resolved binary directly:

```json
{
  "mcpServers": {
    "thesisagents": {
      "command": ".venv\\Scripts\\thesisagents-mcp.exe"
    }
  }
}
```

(Linux / macOS: `.venv/bin/thesisagents-mcp`.)

## Tools

The server exposes seventeen tools, grouped into seven concerns:
discovery, search, citation snowballing, the literature library, PDF
retrieval, export and deck editing.

### `list_sources`

Report every source plugin the server can load, whether it is in the
default mix, and whether the env vars required to enable it are set.
Call this once before `search` so the agent only passes enabled plugins
— disabled plugins are silently skipped by the pipeline but the agent
has no other way to know about them.

```json
{}
```

Returns:

```json
{
  "default_sources": ["arxiv", "semantic_scholar", "openalex", "pubmed",
                     "acm", "dblp", "crossref", "openaire"],
  "sources": [
    {"name": "arxiv",            "in_default_mix": true,  "needs_env_var": [],
     "enabled": true},
    {"name": "springer",         "in_default_mix": true,  "enabled": false,
     "needs_env_var": ["THESISAGENTS_SPRINGER_API_KEY"]},
    {"name": "ieee",             "in_default_mix": true,  "enabled": true,
     "opt_out_env_var": "THESISAGENTS_DISABLE_IEEE_SCRAPING",
     "needs_env_var":   ["THESISAGENTS_IEEE_API_KEY"]},
    {"name": "scholar",          "in_default_mix": true,  "enabled": true,
     "opt_out_env_var": "THESISAGENTS_DISABLE_SCHOLAR_SCRAPING"}
  ]
}
```

The full plugin set is `arxiv`, `semantic_scholar`, `openalex`, `pubmed`,
`acm`, `dblp`, `crossref`, `openaire`, `europepmc`, `doaj`, `hal`, `ieee`,
`springer`, `core`, `scholar` (15). `core` is opt-in via
`THESISAGENTS_CORE_API_KEY`, like `springer`.

`list_sources` reports configuration only: which plugins exist and
which are enabled. How many records each source returned for a
particular query is in the `search` response's `source_stats`.

### `list_exports`

Discovery tool symmetric to `list_sources`: report every export format the
`export` tool accepts, each with a one-line description and an `aggregate`
flag. Call it once before `export` so the agent passes only recognised
formats.

```json
{}
```

Returns (abridged):

```json
{
  "formats": [
    {"format": "pptx", "description": "Thesis-style PowerPoint deck ...", "aggregate": false},
    {"format": "ris",  "description": "RIS interchange for Zotero / Mendeley / EndNote / RefWorks.", "aggregate": true},
    {"format": "csv",  "description": "Flat one-row-per-paper CSV ...", "aggregate": true},
    {"format": "csl",  "description": "CSL-JSON for Pandoc / citeproc ...", "aggregate": true}
  ]
}
```

`aggregate: true` writes one file for the whole run (`xlsx`, `md`, `bib`,
`json`, `ris`, `csv`, `csl`); `pptx` and `pdf` are emitted per paper.

### `search`

Run a keyword search across one or more sources. Returns a JSON
payload whose `papers` list is in the same shape as `Paper.to_dict()`
— pass it straight to `export`.

When `sources` is omitted, the search runs against the full default
mix (every plugin that needs no API key). `exclude_sources` is
subtracted **after** `sources` resolves — the no-VPN gesture is to omit
`sources` and pass `exclude_sources: ["ieee"]`, keeping every other
default source. `top_tier_only` (default `true`) keeps only papers whose
venue matches the curated whitelist (flagship CS conferences + Nature /
Science / PNAS / CACM / LNCS); pass `false` for a broader net. arXiv
preprints always pass through.

```json
{
  "keywords": "attention is all you need",
  "sources": ["arxiv", "openalex", "crossref"],
  "exclude_sources": ["ieee"],
  "max_results": 10,
  "year_from": 2017,
  "year_to": null,
  "top_tier_only": true,
  "min_citations": 50,
  "diagnostics": false,
  "snowball": null,
  "snowball_seeds": 5,
  "snowball_depth": 1,
  "snowball_max_per_seed": 20
}
```

Returns:

```json
{
  "query": {"keywords": "attention is all you need", "sources": ["arxiv"], "max_results": 10, "year_from": 2017, "year_to": null},
  "count": 10,
  "papers": [{"source": "arxiv", "source_id": "1706.03762v5", "title": "Attention Is All You Need", "...": "..."}],
  "source_stats": [
    {"source": "arxiv", "requested": 10, "returned": 10, "after_dedup": 10, "status": "ok", "detail": ""}
  ]
}
```

`source_stats` is always present and has one entry per source of the
query, in the order the sources were named:

| Field | Meaning |
|---|---|
| `requested` | The per-source cap (`max_results`). |
| `returned` | Records the source sent back, before de-duplication. |
| `after_dedup` | Unique papers credited to this source. A paper several sources returned is credited to the first of them, so the values add up to the number of unique papers. |
| `status` | `ok` (also when the source answered with nothing), `failed` (it raised an error), `rate_limited` (HTTP 429 through every retry) or `disabled` (the plugin could not be loaded, usually a missing API key). |
| `detail` | The error text for any status but `ok`. |

Read it before concluding that a topic has few papers. A failing source
is skipped without stopping the search, so `count` alone cannot tell a
narrow topic from a search that lost half its sources:

```json
"source_stats": [
  {"source": "arxiv",    "requested": 25, "returned": 23, "after_dedup": 23, "status": "ok", "detail": ""},
  {"source": "openalex", "requested": 25, "returned": 25, "after_dedup": 21, "status": "ok", "detail": ""},
  {"source": "dblp",     "requested": 25, "returned": 0,  "after_dedup": 0,  "status": "ok", "detail": ""},
  {"source": "ieee",     "requested": 25, "returned": 0,  "after_dedup": 0,  "status": "failed", "detail": "[ieee] search page returned HTTP 403"},
  {"source": "springer", "requested": 25, "returned": 0,  "after_dedup": 0,  "status": "disabled", "detail": "THESISAGENTS_SPRINGER_API_KEY is not set"}
]
```

Here IEEE and Springer contributed nothing for reasons unrelated to the
topic, and four of OpenAlex's 25 records were papers arXiv had already
returned. The counts are taken before the year, citation and top-tier
filters and before the cut to `max_results`.

`diagnostics` (default `false`) adds a `diagnostics` block that explains
the ranking. Without it the response is exactly the one above. The
example shows the block for a search that returned the one arXiv
record, scored in 2026:

```json
{
  "query": {"...": "..."},
  "count": 1,
  "papers": ["..."],
  "diagnostics": {
    "keywords": "attention is all you need",
    "advisory": true,
    "summary": {"keep": 1, "review": 0, "prune": 0},
    "papers": [
      {"rank": 1, "paper_key": "arxiv:1706.03762",
       "bibtex_key": "vaswani2017attention",
       "title": "Attention Is All You Need",
       "score": {"total": 4.1653, "relevance": 4.0, "recency": 0.1653,
                 "citation": 0.0, "relevance_ratio": 0.8696,
                 "matched_terms": ["attention", "all", "you", "need"],
                 "matched_phrases": ["attention all", "all you", "you need"],
                 "reasons": ["title matches 4 of 4 query terms (attention, all, you, need): +3.00",
                             "query words adjacent in the title (\"attention all\", \"all you\", \"you need\"): +1.00",
                             "published 2017: recency +0.17",
                             "citation count unknown: citations +0.00"]},
       "recommendation": {"action": "keep", "threshold": "",
                          "reasons": ["relevance is 87% of the best this query allows"]}}
    ]
  }
}
```

The query word "is" does not appear among the terms: words shorter than
three letters are dropped as noise. arXiv reports no citation count, so
that part is 0 and is said to be unknown, not zero.

Each entry of `diagnostics.papers` describes the paper at the same
position in `papers`:

| Field | Meaning |
|---|---|
| `score.total` | `relevance + recency + citation`, the number the results are sorted by. |
| `score.relevance_ratio` | Relevance as a fraction of the best this query allows, `0` to `1`. |
| `score.matched_terms` / `matched_phrases` | Query terms found in the title or abstract, and adjacent query word pairs that are adjacent in the title. Terms are shown in their stemmed form. |
| `score.reasons` | One sentence per contribution to the score. |
| `recommendation.action` | `keep`, `review` or `prune`. |
| `recommendation.threshold` | The rule that triggered a `review` / `prune`, for example `prune_below_relevance=0.10`. Empty for `keep`. |
| `bibtex_key` | The name `download_pdfs` and the per-paper decks use for this paper. |

The recommendations are advice. `papers` always holds every result and
nothing is removed for you. Use the block to decide which results are
off-topic before calling `download_pdfs`, and read the abstract of a
`review` or `prune` paper before dropping it. The rules behind the
recommendations are listed in [`cli.md`](cli.md) "Ranking diagnostics".

`snowball` (`"references"`, `"cited_by"` or `"both"`, default off)
expands the top `snowball_seeds` results along their citation links and
adds a `snowball` block shaped like the response of the `snowball` tool
below. `papers` is left as the search returned it: the discovered papers
are listed separately so you choose which to keep. They are scored
against `keywords` and capped at 50. For other seeds, a relevance floor
or a different cap, call the `snowball` tool.

### `snowball`

Grow a set of papers along its citation links. It finds work a keyword
search misses because the authors used other words.

```json
{
  "papers": [{"source": "crossref", "source_id": "10.1145/3292500.3330701",
              "title": "Optuna: A Next-generation Hyperparameter Optimization Framework",
              "url": "https://doi.org/10.1145/3292500.3330701",
              "doi": "10.1145/3292500.3330701", "...": "..."}],
  "direction": "both",
  "depth": 1,
  "max_per_seed": 10,
  "max_total": 20,
  "keywords": "hyperparameter optimization",
  "min_relevance": 0.3,
  "known": []
}
```

| Argument | Meaning |
|---|---|
| `papers` | The seeds: paper dicts from `search` or `fetch_paper`. |
| `direction` | `references` (what the seeds cite), `cited_by` (what cites them) or `both`. |
| `depth` | Steps from a seed, 1 to 3. `2` also expands the papers found at step 1. |
| `max_per_seed` | Papers taken per seed and direction, 1 to 100. |
| `max_total` | New papers in all, 1 to 1000. |
| `keywords` | Scores every discovered paper with the search ranker and lists them best first. |
| `min_relevance` | 0 to 1, needs `keywords`. Drops papers below that fraction of the best possible relevance. A dropped paper is not expanded either. |
| `known` | Papers you already hold besides the seeds. They are not reported as new. |

Returns (abridged from a run of that request on 2026-10-08, which found
five papers and listed this one second):

```json
{
  "seed_count": 1,
  "discovered_count": 5,
  "truncated": false,
  "errors": [],
  "discovered": [
    {"paper": {"source": "openalex", "title": "Hyperopt: a Python library for model selection and hyperparameter optimization", "...": "..."},
     "found_by": {"source_key": "doi:10.1145/3292500.3330701",
                  "target_key": "doi:10.1088/1749-4699/8/1/014008",
                  "relation": "references", "provider": "openalex", "depth": 1},
     "score": {"relevance_ratio": 1.0, "...": "..."}}
  ],
  "papers": [{"source": "openalex", "title": "Hyperopt: a Python library for model selection and hyperparameter optimization", "...": "..."}],
  "relations": [
    {"source_key": "doi:10.1145/3292500.3330701",
     "target_key": "doi:10.1088/1749-4699/8/1/014008",
     "relation": "references", "provider": "openalex", "depth": 1}
  ]
}
```

- `discovered` lists the new papers, best score first when `keywords`
  were given. `found_by` is the first path that reached the paper:
  `relation: "references"` means the paper at `source_key` cites the one
  at `target_key`, and `"cited_by"` means the one at `target_key` cites
  the one at `source_key`. `depth` is the number of steps from a seed.
- `papers` is the same list as plain paper dicts, ready for
  `download_pdfs` or `export`.
- `relations` holds every link seen, including links to papers that were
  already known.
- `errors` names a provider that failed. The search carried on with the
  next one.
- `truncated` is true when `max_total` ended the expansion early.

A paper reached along several paths is one paper, a seed is never
reported as discovered, and no paper is expanded twice. Being cited
often is not treated as a sign of being on topic, which is what
`keywords` and `min_relevance` are for. Links come from OpenAlex,
Semantic Scholar and Crossref, asked in that order until one returns
papers. A bound outside its range fails the call with a message such as
`depth must be in [1, 3]`.

### `library_add`

Keep papers in a literature library, so a later session can reuse them
instead of searching again. The library is one SQLite file. The server
keeps no state between calls, so every library tool names the file.

```json
{
  "library": "./thesis.db",
  "papers": [{"source": "openalex", "source_id": "W4360619614",
              "title": "An improved hyperparameter optimization framework for AutoML systems using evolutionary algorithms",
              "url": "https://doi.org/10.1038/s41598-023-32027-3",
              "doi": "10.1038/s41598-023-32027-3", "...": "..."}],
  "keywords": "hyperparameter optimization framework",
  "relations": []
}
```

| Argument | Meaning |
|---|---|
| `library` | Path of the library file. Created when it does not exist. |
| `papers` | Paper dicts from `search`, `snowball` or `fetch_paper`, with their `summary` when you have authored one. |
| `keywords` | What the papers were found for. Recorded with the import. |
| `relations` | The `relations` list `snowball` returns, passed as it is. A link is stored when both of its papers are in the library after this call. |

Returns:

```json
{"library": "/abs/path/thesis.db", "run_id": 3, "added": 1, "merged": 0,
 "relations_added": 0, "relations_skipped": 0, "total": 6}
```

Adding is a merge. A paper the library already holds (same DOI, same
arXiv ID, or same title with first author and year) is updated, not
duplicated: fields it lacked are filled in and the new sighting is
recorded. `added` counts new papers, `merged` the ones already held,
and `total` the papers in the library after the call.
`relations_skipped` counts links whose other paper is not in the
library.

### `library_search`

Find papers already in a library. No network access. Call it before a
new `search`: papers found and verified in an earlier session are here,
with any summary authored for them.

```json
{"library": "./thesis.db", "query": "evolutionary hyperparameter", "limit": 1}
```

Returns (from a library filled on 2026-10-08, abridged):

```json
{
  "library": "/abs/path/thesis.db",
  "query": "evolutionary hyperparameter",
  "total": 5,
  "count": 1,
  "papers": [{"source": "openalex", "source_id": "W4360619614",
              "title": "An improved hyperparameter optimization framework for AutoML systems using evolutionary algorithms",
              "doi": "10.1038/s41598-023-32027-3", "...": "..."}],
  "entries": [
    {"paper_key": "doi:10.1038/s41598-023-32027-3",
     "bibtex_key": "vincent2023improved",
     "first_seen": "2026-10-07T20:43:06+00:00",
     "last_seen": "2026-10-07T20:43:13+00:00",
     "times_seen": 2,
     "sources": ["openalex"],
     "score": {"total": 5.0249, "relevance": 3.6, "relevance_ratio": 0.7826,
               "matched_terms": ["evolutionary", "hyperparameter"], "...": "..."}}
  ]
}
```

- `papers` are plain paper dicts, ready for `export` or `download_pdfs`.
- `entries` has one item per paper, in the same order, with its history:
  when it was first and last seen (UTC), how many imports saw it, and
  every source that returned it. `score` is the search ranker's score
  for `query`.
- `query` is scored like a search (stemming, phrases, acronyms), and
  only papers matching at least one query term are returned. An empty
  `query` lists the most recently seen papers, with `score: null`.
- `limit` is 1 to 200 (default 20). `year_from` / `year_to` narrow the
  result. `total` is the number of papers in the library.

A `library` path that does not exist fails the call. It is not created
by a read.

### `library_stats`

Summarise a library.

```json
{"library": "./thesis.db"}
```

Returns (the same library):

```json
{
  "path": "/abs/path/thesis.db",
  "schema_version": 1,
  "papers": 5,
  "runs": 2,
  "relations": 2,
  "year_min": 2019,
  "year_max": 2025,
  "first_run": "2026-10-07T20:43:06+00:00",
  "last_run": "2026-10-07T20:43:13+00:00",
  "sources": {"openalex": 5},
  "verifications": {"ok": 5, "skipped": 5},
  "recent_runs": [
    {"run_id": 2, "started_at": "2026-10-07T20:43:13+00:00", "kind": "search",
     "keywords": "hyperparameter optimization framework", "papers": 3},
    {"run_id": 1, "started_at": "2026-10-07T20:43:06+00:00", "kind": "search",
     "keywords": "hyperparameter optimization framework", "papers": 5}
  ]
}
```

`sources` counts the papers each source has returned (a paper returned
by two sources counts once for each). `verifications` counts the stored
DOI / URL verdicts by status. `recent_runs` lists the ten latest
imports, and `kind` says where one came from: `search`, `paper` or `pdf`
for a CLI run, `mcp` for `library_add`.

### `fetch_paper`

Fetch exactly one paper by identifier. Accepts the same forms as the
CLI's `--paper` flag — arXiv ID / URL, DOI, PMID, IEEE document URL.

```json
{"identifier": "https://arxiv.org/abs/1706.03762"}
```

Returns:

```json
{
  "paper": {"title": "Attention Is All You Need", "...": "..."},
  "identifier": {"kind": "arxiv", "value": "1706.03762"}
}
```

### `fetch_pdf_text`

Download a paper's PDF over HTTPS-only and extract its body text. This
is the MCP entry point for the **LLM-as-agent enrichment flow** — the
calling LLM reads the body text in its own context and produces the
structured `summary` itself, no API key required.

```json
{"pdf_url": "https://arxiv.org/pdf/1706.03762", "source": "arxiv"}
```

Returns:

```json
{
  "url": "https://arxiv.org/pdf/1706.03762",
  "page_count": 12,
  "chars": 47200,
  "text": "Attention Is All You Need\n\nAshish Vaswani ..."
}
```

Hard caps: 20 MB downloaded, first 60 pages, first 80,000 characters
of extracted text. The extraction is local (`pypdf`); the LLM consumes
the returned text.

### `download_pdfs`

Batch-download the PDFs for a list of papers into `{out_dir}/pdfs/`.
Each result is keyed by the paper's BibTeX key so an agent can match
results back to the input list. Use this between `search` and
`fetch_pdf_text` when you need the PDFs persisted on disk (e.g. for
later re-reading or for embedding into the rich PPT via figure
extraction).

```json
{
  "papers": [
    {"source": "arxiv", "source_id": "1706.03762v5", "...": "...",
     "pdf_url": "https://arxiv.org/pdf/1706.03762"}
  ],
  "out_dir": "./exports/attention/"
}
```

Returns:

```json
{
  "out_dir": "./exports/attention/",
  "saved": 1,
  "skipped": 0,
  "results": [
    {"paper_key": "vaswani2017attention",
     "path": "./exports/attention/pdfs/vaswani2017attention.pdf",
     "reason": null}
  ]
}
```

Papers without a `pdf_url` come back with `reason: "no_pdf_url"`;
HTTP 403 / non-PDF content-type / oversize bodies come back with the
matching reason string.

### `export`

Render a papers list to any combination of `.pptx`, `.xlsx`, `.md`,
`.bib`, `.json`, `.ris`, `.csv`, `.csl.json` files. Call `list_exports`
for the format catalogue.

```json
{
  "papers": [
    {"source": "arxiv", "source_id": "1706.03762v5",
     "title": "Attention Is All You Need", "...": "...",
     "summary": {
        "language": "zh-tw",
        "pain_points": [["...", ["...", "..."]]],
        "research_question": "...",
        "contributions_detailed": [["...", "..."]],
        "headline_metrics": [["BLEU on En→De", "28.4", "baseline 25.16"]],
        "rq_results": [{"rq_id": "RQ1", "question": "...",
                        "table": [["metric", "ours"], ["a", "1.0"]],
                        "analysis": ["..."]}],
        "limitations": ["..."],
        "future_work": ["..."]
     }}
  ],
  "keywords": "attention",
  "formats": ["pptx", "xlsx", "bib"],
  "out_dir": "./exports",
  "filename_stem": "attention",
  "include_abstract": true,
  "language": "zh-tw",
  "max_slides_per_paper": 25,
  "dark_mode": true,
  "verify_identifiers": true,
  "library": null
}
```

`library` (optional) is the path of a literature library, see
`library_add`. When given, the identifier verdicts are kept there: a
DOI or URL that verified in an earlier call is not checked again for 30
days. A failed check is always made again. The papers themselves are
not stored by `export`, that is what `library_add` is for.

`max_slides_per_paper` (default 25) caps the per-paper slide count
after the priority-based trim — cover / references / contributions are
kept first; Q&A / figure / paper-table slides drop first. Pass `0`
(or omit the field) for unlimited.

`dark_mode` (default `false` — the project default is the light
navy-band deck) toggles the post-build recolour pass.
On: dark slide background (`#12151B`) + near-white body text (`#E5E7EB`)
+ darker table-row stripe — designed for OLED projectors and low-light
venues. Off: the light/printable variant (white background + navy text
`#1F3A66`). Both modes share the same builder pipeline — the dark pass
runs over the rendered tree, so the agent doesn't pick layouts up-front.
The teal accent (`#0E7490` → `#2DD4BF` in dark) marks KPI values and RQ
question callouts; red is banned for text in both modes.

`verify_identifiers` (default `true`) runs the identifier preflight
before anything is written: every paper's DOI is looked up at doi.org
and every URL is requested once. A DOI or URL that is wrong or
unreachable fails the call, and the error text names each paper and
identifier, for example
`smith2024attention: doi 10.1234/typo is invalid (doi.org has no such DOI registered)`.
No file is written in that case. Copy `doi` and `url` from the `search`
results instead of composing them, and pass `false` only when working
offline. The five statuses and what each one means are listed in
[`cli.md`](cli.md) "Identifier verification".

Returns:

```json
{
  "written": {
    "pptx": "/abs/path/exports/attention.pptx",
    "xlsx": "/abs/path/exports/attention.xlsx",
    "bib":  "/abs/path/exports/attention.bib"
  },
  "pptx_path": "/abs/path/exports/attention.pptx",
  "verification": {
    "enabled": true,
    "ok": true,
    "counts": {"ok": 2, "invalid": 0, "unreachable": 0, "timeout": 0, "skipped": 0},
    "checks": [
      {"paper_key": "vaswani2017attention", "title": "Attention Is All You Need",
       "kind": "doi", "value": "10.48550/arXiv.1706.03762", "status": "ok",
       "resolved_url": "https://arxiv.org/abs/1706.03762", "detail": ""},
      {"paper_key": "vaswani2017attention", "title": "Attention Is All You Need",
       "kind": "url", "value": "https://arxiv.org/abs/1706.03762",
       "status": "ok", "resolved_url": null, "detail": ""}
    ]
  }
}
```

The `pptx_path` field is a convenience so an agent can pipe the
result straight into the `pptx_*` editing tools.

`verification.checks` holds one entry per identifier per paper.
`value` is the identifier exactly as the paper carries it, and
`resolved_url` is where it leads (a DOI's registered landing page, or a
redirect target). The paper's own fields are never changed to match.
An identifier that could not be checked comes back with
`"status": "skipped"` and the reason in `detail`, for example a URL on a
publisher host that needs a real browser. It does not fail the call.
With `verify_identifiers: false` the block is `{"enabled": false}`.

**`papers[*].summary`**: when populated with any rich-tier field, the
PPT exporter switches to thesis-style layout (pain-point quadrants,
KPI block, technique table, per-RQ result tables, contribution
summary, core observation callout, limitations & future work, Q&A).
When only the flat fields are set, the deck has one slide per
non-empty section. When `summary` is absent, the deck uses
sentence-bucketing on `paper.abstract`.

**`language`**: one of 14 locales — `en`, `zh-tw`, `zh-cn`, `ja`, `es`,
`fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. Drives both the
template strings (Agenda / References / "Paper N of M" / footer) and
the suggested LLM output language when the agent fills in the summary.
Anything outside that set falls back to `en` silently. Each locale
also drives the per-language typography pass (Inter for Latin, plus
Microsoft JhengHei UI for zh-tw / YaHei UI for zh-cn / Yu Gothic UI
for ja / Malgun Gothic for ko / Nirmala UI for hi) — replaces the
PowerPoint Calibri default, which is the biggest "AI-generated" tell.

### `pptx_inspect`

Read the structure of an existing `.pptx`.

```json
{"path": "./exports/attention.pptx"}
```

Returns the slide count and, for each slide, every text-bearing
shape's index, name, and text:

```text
{
  "path": "./exports/attention.pptx",
  "slide_count": 3,
  "slides": [
    {"index": 0, "title": "Paper search: attention",
     "shapes": [{"index": 0, "name": "title", "text": "Paper search: attention"},
                {"index": 1, "name": "body",  "text": "Sources: arxiv\n..."}]},
    {"index": 1, "title": "1/2  Attention Is All You Need", "shapes": [...]}
  ]
}
```

Shape names are set by `PptxExporter`: each slide carries `title`,
`meta`, and (when an abstract was included) `body` shapes. Decks built
elsewhere may not have these names — fall back to `shape_updates`
addressed by integer index.

### `pptx_review`

Audit an existing deck against all three deck-quality contracts in one
call: slide **overflow**, the dark-mode / no-red / contrast **colour**
contracts, and `paper_rule` **section completeness**.

```json
{"path": "./exports/attention.pptx"}
```

`language` is optional — it is auto-detected from the slide titles when
omitted (pass e.g. `"zh-tw"` to force it). Returns:

```text
{
  "path": "./exports/attention.pptx",
  "language": "zh-tw",
  "thesis_style": true,
  "ok": true,
  "overflow": [],                 // {slide, shape, kind, rendered_in, limit_in}
  "contrast": [],                 // {slide, shape, kind, detail, hard}
  "missing_sections": [],         // canonical body sections with no covering slide
  "completeness_gated": true      // missing_sections only fail a thesis-style deck
}
```

`ok` is `false` when there is any overflow, any *hard* contrast issue
(invisible / red / light-on-light text), or — for a thesis-style deck —
any missing body section (Introduction, Literature Review, Methodology,
Experiment, Conclusion). A lightweight abstract-only deck is never failed
for lacking sections (`thesis_style` / `completeness_gated` say which).
The same audit is available on the command line as
`python -m thesisagents review <deck.pptx> [more.pptx ...] [--lang xx]`.

### `pptx_update_slide`

Replace text on one slide.

```json
{
  "path": "./exports/attention.pptx",
  "slide_index": 1,
  "title": "New title",
  "body": "Replaced abstract.",
  "meta": "Vaswani et al.\n2017 · NeurIPS",
  "shape_updates": {"4": "extra-shape text"},
  "out_path": null
}
```

`title` / `body` / `meta` look the shape up by name. `shape_updates`
is an integer-keyed map for any shape addressable by its zero-based
index among the slide's text-bearing shapes. `out_path` writes a copy
instead of updating in place.

### `pptx_delete_slide`

Remove a slide and its part relationship.

```json
{"path": "./exports/attention.pptx", "slide_index": 0}
```

### `pptx_reorder_slides`

Permute the slide list. `new_order[i]` is the *old* index that should
now occupy position `i`. The list must be a true permutation of
`[0..slide_count-1]`.

```json
{"path": "./exports/attention.pptx", "new_order": [2, 0, 1]}
```

### `pptx_add_slide`

Append (default) or insert at `position` a new slide with `title`,
optional `meta`, and optional `body` textboxes.

```json
{
  "path": "./exports/attention.pptx",
  "title": "Conclusion",
  "meta": "Summary of findings",
  "body": "We covered transformers, diffusion, and survey work.",
  "position": null
}
```

## Path safety

`pptx_*` tools operate on user-supplied paths. Each call resolves the
target through `Path.expanduser().resolve()` and refuses to operate on
a non-existent file (delete / update / inspect) or on a path that is
not a directory when one is expected. Export paths go through
`thesisagents.utils.path_safety.ensure_export_dir`, which rejects
collisions with non-directory files.

## Adding a new tool

1. Open `thesisagents/mcp/server.py` and find the right group helper
   (`_register_search_tools`, `_register_export_tool`,
   `_register_pptx_tools`). Add a new helper if the tool doesn't fit
   any existing group — `build_server` is intentionally kept under
   complexity 15 by delegating to these helpers.
2. Register your tool with `@server.tool()`. The docstring becomes the
   description the calling agent sees — make it specific.
3. Add an integration test in `tests/test_mcp_tools.py`. Use the
   `_call` helper which exercises the same call path FastMCP uses
   over stdio.
