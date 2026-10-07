# Data model

Every record shape the pipeline produces, every field on each, and
when each field is populated. All four core types are frozen
dataclasses defined in `thesisagents.core.models`.

## `Query`

The input contract: what the user is asking for.

```python
@dataclass(frozen=True)
class Query:
    keywords: str                     # NFC-normalised, whitespace-collapsed
    sources: tuple[str, ...]          # subset of ALL_SOURCES
    max_results: int = 25             # 1..200 per source
    year_from: int | None = None      # inclusive lower bound
    year_to: int | None = None        # inclusive upper bound
    top_tier_only: bool = False       # apply the venue whitelist
    min_citations: int | None = None  # discard below this (MCP-only flag)
```

| Field | Required | Notes |
|---|---|---|
| `keywords` | yes | Must be non-empty after `normalize_query`. URL/HTML encoding is per-source — you pass plain text. |
| `sources` | yes | Empty tuple is rejected at construction. Use `ALL_SOURCES` from `core.constants` to get the full list. |
| `max_results` | no | Clamped to `[1, MAX_RESULTS_PER_SOURCE]` (200) by `pydantic` validation. |
| `year_from` / `year_to` | no | Either or both. `year_from > year_to` is rejected. |
| `top_tier_only` | no | Off by default. When True (CLI: `--top-tier-only`), filters to the curated CS top-tier whitelist + arXiv pass-through. |
| `min_citations` | no | Surfaced via the MCP `search` tool's `min_citations` parameter only. |

## `Paper`

The normalised result shape every source plugin produces. See
`thesisagents.core.models.Paper` for the source.

```python
@dataclass(frozen=True)
class Paper:
    source: str                       # source plugin name (e.g. "arxiv")
    source_id: str                    # the plugin's stable record ID
    title: str
    authors: tuple[str, ...]
    year: int | None
    venue: str | None                 # the REAL publication venue
    abstract: str
    url: str                          # canonical landing page
    doi: str | None = None
    arxiv_id: str | None = None
    pdf_url: str | None = None        # PDF if publicly accessible
    citation_count: int | None = None
    raw: dict[str, Any] | None = None # the source's raw payload
    summary: PaperSummary | None = None
    provenance: tuple[FieldProvenance, ...] = ()  # which source filled which field
```

### Field reference

| Field | Required | Populated by |
|---|---|---|
| `source` | yes | Source plugin name (`"arxiv"`, `"pubmed"`, `"openalex"`, …). Always one of `ALL_SOURCES`. |
| `source_id` | yes | The plugin's stable ID for the record (arXiv: ID without version suffix; pubmed: PMID; openalex: opaque ID). Used to form the BibTeX key fallback when DOI is missing. |
| `title` | yes | Plain text, no Markdown. CJK supported. |
| `authors` | yes | Tuple of `"Firstname Lastname"` strings. Empty tuple is allowed (rare; some preprint servers omit authors). The exporter shows the first three then `…`. |
| `year` | no | `None` only when the source genuinely lacks year metadata. Slide layouts substitute `"n.d."` (configurable via i18n). |
| `venue` | no | Real publication venue when available. `None` for preprints with no venue, scrape results that can't determine a venue, and local PDFs. |
| `abstract` | yes | Plain text. May be empty string for entries with no abstract (the lightweight tier falls back to bullet placeholders). |
| `url` | yes | The canonical landing page URL — what a human would click to read the paper. arXiv: `https://arxiv.org/abs/<id>` (no `v<N>` suffix). DOI papers: `https://doi.org/<doi>`. Locally-fed PDFs: `file:///...`. |
| `doi` | no | `10.x/y` form, no `https://doi.org/` prefix. Used as the BibTeX key when present. |
| `arxiv_id` | no | The bare arXiv ID (`2401.08741`), no `v<N>` suffix. Strip the version when populating. |
| `pdf_url` | no | A publicly fetchable PDF URL. `None` when the paper is paywalled or the source can't surface a PDF link. The pipeline's paywall gate triggers when more than 30% of results have `pdf_url=None`. |
| `citation_count` | no | Integer when the source reports one. Used in the rank score. |
| `raw` | no | The source's raw payload (parsed JSON / dict). Available for debugging and for the LLM-as-agent flow (`raw["extracted_text"]` when populated by `--pdf`). Excluded from `.json` export when too large. |
| `summary` | no | A `PaperSummary` dataclass — populated by `--enrich`, the LLM-as-agent flow, or hand-authored regen scripts. |
| `provenance` | no | Tuple of `FieldProvenance(field, source, source_id)` records appended by the dedup merge. Each entry names the duplicate-source record that filled a field the canonical record was missing (e.g. an OpenAlex mirror supplying `pdf_url` to an ACM-canonical paper), so cross-source merges stay auditable without keeping the whole upstream payload. Empty for papers seen by only one source. Round-trips through `to_dict()` / `from_dict()`. |

### Derived methods

```python
paper.bibtex_key()      # → "vaswani2017attention" (lowercase, ASCII-folded)
paper.to_dict()         # → JSON-serialisable dict (drops `raw` when huge)
Paper.from_dict(data)   # → Paper (round-trip equality)
```

The BibTeX key generation is:

1. Last name of first author (ASCII-folded, lowercase).
2. Four-digit year (or `nd` when missing).
3. First non-stopword from the title (lowercase, ASCII-folded).
4. If a collision: append `a`, `b`, `c`, … per the project's
   collision counter.

## `PaperSummary`

The structured per-paper summary attached as `Paper.summary`.
Three usage tiers stack additively:

```python
@dataclass(frozen=True)
class PaperSummary:
    # Flat tier — enriched-flat exporter renders these one per slide
    motivation: str = ""
    contributions: tuple[str, ...] = ()
    method: str = ""
    results: str = ""
    limitations: str = ""
    takeaways: tuple[str, ...] = ()

    # Rich tier — thesis-style exporter activates when has_rich_fields()
    pain_points: tuple[str, ...] = ()
    research_question: str = ""
    contributions_detailed: tuple[ContributionDetail, ...] = ()
    headline_metrics: tuple[Metric, ...] = ()
    technique_table: tuple[TechniqueRow, ...] = ()
    literature_positioning: tuple[LiteratureRow, ...] = ()
    system_flow: tuple[str, ...] = ()
    method_sections: tuple[MethodSection, ...] = ()
    evaluation_method: str = ""
    research_questions: tuple[str, ...] = ()
    rq_results: tuple[RqResult, ...] = ()
    contribution_summary: str = ""
    core_observation: str = ""
    future_work: tuple[str, ...] = ()

    # Provenance
    model: str = ""               # "claude-opus-4-7 (LLM-as-agent, read 12-page PDF)"
    raw_text_chars: int = 0       # length of source text that was summarised
    language: str = "en"
```

`has_rich_fields()` returns `True` when any rich-tier field has
non-empty content; this is what the `.pptx` exporter checks to
pick between the enriched-flat and thesis-style layouts.

### When each tier is populated

| Source | Flat tier | Rich tier |
|---|---|---|
| CLI `--enrich` (Python pipeline) | yes | yes — Claude prompts produce both tiers |
| MCP `export` from LLM-as-agent | yes if the LLM writes them | yes if the LLM writes them |
| Hand-authored regen script | yes | yes |
| CLI default (no enrichment) | empty | empty |

## Nested types (rich tier)

### `ContributionDetail`

```python
@dataclass(frozen=True)
class ContributionDetail:
    title: str                # "Two-tower fine-tuning"
    description: str          # one sentence explaining what + why
    bullets: tuple[str, ...] = ()  # 2-4 supporting points
```

Renders as one stack on the contributions slide. Cap the slide at
**≤ 4 contributions** — the overflow check trips above that.

### `Metric`

```python
@dataclass(frozen=True)
class Metric:
    name: str                 # "Top-1 accuracy on ImageNet-1k"
    value: str                # "84.7%"
    delta: str = ""           # "+2.3% vs. ViT-B/16"
```

Renders as one row of the KPI slide. Aim for 3–5 metrics.

### `TechniqueRow`

```python
@dataclass(frozen=True)
class TechniqueRow:
    technique: str            # "RoPE positional encoding"
    used_for: str             # "long-context generalisation"
    note: str = ""            # optional aside
```

Renders as one row of the technique table.

### `LiteratureRow`

```python
@dataclass(frozen=True)
class LiteratureRow:
    work: str                 # citation key or short ref ("BERT (2019)")
    contribution: str         # what they did
    delta: str                # what this paper adds beyond them
```

Renders as one row of the literature-positioning table.

### `MethodSection`

```python
@dataclass(frozen=True)
class MethodSection:
    title: str                # "3.1 Encoder"
    bullets: tuple[str, ...]  # 3-6 bullets, ≤ 28 chars each for column layout
```

Renders as one column block on the method slide. The
`_METHOD_SECTIONS_PER_SLIDE = 2` cap means the exporter splits into
multiple method slides automatically.

### `EvaluationSection`

```python
@dataclass(frozen=True)
class EvaluationSection:
    title: str                # "4.1 ImageNet-1k benchmark"
    bullets: tuple[str, ...]  # 3-6 bullets
```

Same shape as `MethodSection`; same `_EVALUATION_SECTIONS_PER_SLIDE = 2` cap.

### `RqResult`

```python
@dataclass(frozen=True)
class RqResult:
    research_question: str    # "RQ1: Does X improve Y under constraint Z?"
    headline: str             # one-sentence answer
    table: tuple[tuple[str, ...], ...] = ()  # rows of cells; first row is header
    notes: tuple[str, ...] = ()  # 2-4 supporting bullets below the table
```

Renders as one slide per RQ. The pipeline pairs `research_questions[i]`
with `rq_results[i]` by index; lengths must match.

## `PaperCollection`

The pipeline's output and every exporter's input.

```python
@dataclass(frozen=True)
class PaperCollection:
    query: Query              # the originating query (for provenance)
    papers: tuple[Paper, ...] # deduplicated, ranked
    diagnostics: SearchDiagnostics | None = None  # why each paper ranks where it does
```

| Field | Notes |
|---|---|
| `query` | Used by the `.xlsx` exporter's "Query" provenance sheet, by the `.md` exporter's header, and by the `.pptx` exporter's footer. |
| `papers` | Tuple (frozen). Order matters — exporters render in the order given. |
| `diagnostics` | Filled in by `run_search`: the score behind each paper's position and the advisory pruning recommendations. `None` for a collection built by hand (the MCP `export` tool, a regen script, `--pdf` mode), so every reader must accept `None`. Not part of `==`: two collections with the same papers are equal however they were explained. See "Search diagnostics" below. |

### Helpers

```python
len(collection)                # → len(collection.papers)
for paper in collection: ...   # iterates collection.papers
collection[0]                  # → collection.papers[0]
```

A stage that swaps the papers of a collection uses
`dataclasses.replace(collection, papers=...)`, so `diagnostics` comes
along. Its entries are keyed by `Paper.dedup_key()`, which stays the
same when a later stage fills in `pdf_url` or attaches a `summary`.

## Search diagnostics

`thesisagents.core.diagnostics` holds the records that explain a search
result. `ranking.rank_with_scores` and `pruning.recommend_pruning`
produce them.

```python
@dataclass(frozen=True)
class RelevanceScore:
    total: float                      # relevance + recency + citation
    relevance: float                  # query overlap with title / abstract, plus phrase bonus
    recency: float                    # exp(-age / 5 years)
    citation: float                   # 0.4 * log10(citations + 1)
    matched_terms: tuple[str, ...]    # query terms found, in query order, stemmed
    matched_phrases: tuple[str, ...]  # adjacent query pairs adjacent in the title
    reasons: tuple[str, ...]          # one sentence per contribution
    relevance_ratio: float | None     # relevance / best possible, None without a query

@dataclass(frozen=True)
class PruningRecommendation:
    paper_key: str                    # Paper.dedup_key()
    rank: int                         # 1-based position in the collection
    action: PruningAction             # "keep" | "review" | "prune"
    reasons: tuple[str, ...]
    threshold: str                    # e.g. "prune_below_relevance=0.10", "" for keep

@dataclass(frozen=True)
class SourceStat:
    source: str                       # the source name the query asked for
    requested: int                    # the per-source cap (Query.max_results)
    returned: int                     # records sent back, before de-duplication
    after_dedup: int                  # unique papers credited to this source
    status: SourceStatus              # "ok" | "failed" | "rate_limited" | "disabled"
    detail: str                       # the error text for anything but "ok"

@dataclass(frozen=True)
class SearchDiagnostics:
    scores: tuple[PaperScore, ...]    # PaperScore(paper_key, rank, score)
    pruning: tuple[PruningRecommendation, ...]
    source_stats: tuple[SourceStat, ...]   # one per source, in query order
    relations: tuple[PaperRelation, ...]   # citation links, empty without snowballing
    # .score_for(paper_key) / .recommendation_for(paper_key)
```

`source_stats` is what makes a skipped source visible. A paper several
sources returned is credited to the first of them in the query's source
order, so the `after_dedup` values add up to the number of unique
papers. Both counts are taken before the `Query` filters and the final
`max_results` cut. `source_stats_payload(collection)` returns them as
JSON-ready dicts, an empty list for a collection without diagnostics.

Ranking a list yourself:

```python
from thesisagents.core.pruning import recommend_pruning
from thesisagents.core.ranking import rank_with_scores

ranked = rank_with_scores(papers, "retrieval augmented generation")
for entry, advice in zip(ranked, recommend_pruning(ranked)):
    print(entry.rank, f"{entry.score.total:.2f}", advice.action, entry.paper.title)
```

`rank(papers, keywords)` returns the same order as
`rank_with_scores(papers, keywords)` without the scores.
`RankingPolicy` (the axis weights) and `PruningPolicy` (the thresholds)
are optional arguments with the defaults described in
[`architecture.md`](architecture.md) "Ranking" and
[`cli.md`](cli.md) "Ranking diagnostics".

`collection_report(collection)` joins the scores and recommendations to
the papers, one entry per paper. It is the shape of the CLI's
`diagnostics.json` and of the MCP `search` tool's `diagnostics` block.

The pruning recommendations are advice. Nothing in the pipeline removes
a paper because of them.

## `ExportOptions`

The exporter contract.

```python
@dataclass(frozen=True)
class ExportOptions:
    formats: tuple[str, ...]       # subset of ALL_EXPORTS
    out_dir: str                   # filesystem path
    filename_stem: str | None = None  # override autogen
    pptx_template: str | None = None  # a .pptx / .potx to build decks on
    pptx_template_config: str | None = None  # TOML / JSON overrides for it
    include_abstract: bool = True  # off → drops abstract + summary
    language: str = "en"           # slide-deck language code
    max_slides_per_paper: int = 25 # 0 = unlimited
    dark_mode: bool = False        # dark post-build recolour pass
    verify_identifiers: bool = True   # DOI / URL preflight before export
```

| Field | Notes |
|---|---|
| `formats` | Validated against `ALL_EXPORTS = ("bib", "md", "pptx", "xlsx", "pdf", "json", "ris", "csv", "csl")`. |
| `out_dir` | Created if missing. Path-traversal-safe (resolved via `utils.path_safety`). |
| `filename_stem` | When `None`, the pipeline generates `{slug-of-query}-{YYYYMMDD-HHMMSS}`. Hand-authored regen scripts typically set this to the BibTeX key. |
| `pptx_template` | A PowerPoint template whose layouts, background and logo the deck is built on. `None` is the built-in navy-band deck. Checked against the template contract before any slide is rendered, and a template that does not meet it raises `TemplateError` with every problem. See [Deck templates](pptx_templates.md). |
| `pptx_template_config` | A TOML or JSON file of overrides for `pptx_template`: the layout each slide role uses, roles whose title goes into the layout's title placeholder, font families, the four palette colours, and whether the header band and cover panel are drawn. Setting it without `pptx_template` raises `ValueError`. |
| `include_abstract` | False produces a deck that's title + authors + link slides only — useful when you want a one-sentence summary deck for hundreds of papers. |
| `language` | Must be one of the 14 supported slide-deck languages. Unknown codes fall back to `en` via `normalise_language`. |
| `max_slides_per_paper` | Caps each paper's slide count; the exporter drops lower-priority sections (figures, paper-tables, contribution-summary, pagination tails) until the count fits. Cover / overview / contributions / metrics / core observation / references are always kept. Pass `0` to disable the cap. |
| `dark_mode` | `False` builds the light navy-band deck. `True` runs the dark post-build pass (slide background `#12151B`, body text `#E5E7EB`). |
| `verify_identifiers` | `True` makes `export_collection` check every paper's DOI and URL first and raise `IdentifierVerificationError` when one is wrong or unreachable, before any file is written. `False` skips the check and logs a warning, for a machine with no network. See "Identifier verification report" below. |

## Citation links and snowballing

`thesisagents.core.snowball.snowball()` grows a set of papers along its
citation links. A link is a `PaperRelation`, kept outside `Paper`
because one paper can be reached along many paths:

```python
@dataclass(frozen=True)
class PaperRelation:
    source_key: str            # Paper.dedup_key() of the paper that was expanded
    target_key: str            # Paper.dedup_key() of the paper found from it
    relation: RelationKind     # "references" | "cited_by"
    provider: str              # the source that reported the link
    depth: int                 # steps from a seed, 1 = straight from a seed
    # .citing_key / .cited_key give the direction of the citation
```

For `references` the source cites the target. For `cited_by` the target
cites the source.

```python
from thesisagents.core.snowball import expand_collection, snowball

result = await snowball(
    collection.papers[:5],              # seeds
    known=collection.papers,            # do not rediscover the rest
    direction="both",                   # "references" | "cited_by" | "both"
    depth=1,                            # 1..3
    max_per_seed=20,                    # 1..100
    max_total=200,                      # 1..1000
    keywords=collection.query.keywords, # scores what is found
    min_relevance=0.3,                  # optional, needs keywords
)
for found in result.discovered:         # DiscoveredPaper(paper, found_by, score)
    print(found.paper.title, found.found_by.relation, found.found_by.source_key)
collection = expand_collection(collection, result)
```

`SnowballResult` carries `seeds`, `discovered`, `relations` (every link
seen), `errors` (a provider that failed) and `truncated` (the total cap
ended the search early). `expand_collection` appends the discovered
papers to the collection and records the links, scores and pruning
recommendations in its `diagnostics`.

`CitationProvider` (`thesisagents/fetchers/citations.py`) is the
source-neutral interface behind it, with `references(paper, limit)` and
`cited_by(paper, limit)`. See
[`source_plugins.md`](source_plugins.md) "Adding a citation provider".

`IdentityIndex` (`thesisagents/core/dedup.py`) is the incremental form
of `dedupe`: `add(paper)` returns `(slot, is_new)`, so a caller that
meets papers one at a time can ask "have I seen this one?".

## Literature library

`thesisagents.library.Library` keeps papers across runs in one SQLite
file. A `PaperCollection` lives for one process, a library is what the
processes leave behind.

```python
from thesisagents.library import Library

with Library("thesis.db") as library:
    report = library.add_collection(collection)     # AddReport
    hits = library.search("graph neural network", limit=10)
    for entry in hits:                              # LibraryEntry
        print(entry.paper.title, entry.times_seen, entry.sources, entry.score.total)
    export_collection(
        library.collection("graph neural network"),
        options,
        verification_cache=library.verification_cache(),
    )
```

| Call | Returns | Purpose |
|---|---|---|
| `add_collection(collection, kind="search")` | `AddReport` | Merge a search result in, with its query, source statistics, scores and citation links. |
| `add_papers(papers, keywords="", relations=())` | `AddReport` | Merge papers that did not come from `run_search`. |
| `search(query="", limit=50, year_from, year_to)` | `list[LibraryEntry]` | Stored papers matching `query`, scored by `rank_with_scores`. An empty query lists the most recently seen. |
| `collection(query="", limit=None)` | `PaperCollection` | The same papers in the shape the exporters take, with scores, pruning advice and the links between them in `diagnostics`. |
| `relations()` | `tuple[PaperRelation, ...]` | Every stored citation link. |
| `runs()` | `list[LibraryRun]` | Every import, newest first. |
| `stats()` | `LibraryStats` | Counts for a summary. |
| `verification_cache()` | `LibraryVerificationCache` | A `VerificationCache` for `export_collection`. |

`Library(path, create=False)` refuses a path that does not exist, which
is what a read wants: a mistyped path is an error and not an empty
library.

```python
@dataclass(frozen=True)
class AddReport:
    run_id: int
    added: int               # papers the library did not hold
    merged: int              # papers that matched one already held
    relations_added: int
    relations_skipped: int   # links whose other paper is not in the library
    total: int               # papers held after the import

@dataclass(frozen=True)
class LibraryEntry:
    paper: Paper
    first_seen: str          # ISO 8601, UTC
    last_seen: str
    times_seen: int          # imports that saw the paper
    sources: tuple[str, ...] # every source that returned it, across imports
    score: RelevanceScore | None   # set by search() when a query was given
```

**Identity.** An import is a merge. A paper is matched on every key of
`Paper.identity_keys()` (DOI, arXiv ID, title hash) with the rules of
`core/dedup.py`: `fuzzy_link_allowed` keeps two papers with the same
title and different DOIs apart, and `merge_papers` fills the stored
record's empty fields from the new one, recording each in
`Paper.provenance`. A paper that carries the DOI of one stored paper and
the arXiv ID of another joins the two into one. The stored record keeps
its `source`, `source_id`, `url` and `title`. One field departs from
"first value wins": a later, higher `citation_count` replaces the
stored one.

**Tables** (schema version 1, in `thesisagents/library/schema.py`):

| Table | Holds |
|---|---|
| `papers` | One row per distinct paper: its `Paper.to_dict()` record as JSON, and when it was first and last seen. |
| `identity_keys` | Every key a paper is known by, pointing at its row. |
| `runs` | One row per import: when, what kind, the query, what each source returned. |
| `observations` | Which run saw which paper, through which source, at what rank, with what score and pruning recommendation. |
| `relations` | Citation links between two stored papers, with provider and depth. |
| `verifications` | The export preflight's latest verdict per DOI / URL and when it was reached. |

**Schema version.** The version is SQLite's `PRAGMA user_version`, and
`PRAGMA application_id` marks the file as a ThesisAgents library.
Opening a library runs the migrations it has not seen yet, each in one
transaction with its version bump. A library with a higher version than
this build knows raises `LibraryError` naming both versions, and so
does a file that is not a library. To change the schema, append one
function to `schema.MIGRATIONS` and raise `SCHEMA_VERSION`.

**Verdict reuse.** `LibraryVerificationCache` reuses a stored verdict
only when it lets an export through (`ok`, `skipped`) and is younger
than `VERIFIED_FOR` (30 days). A failure (`invalid`, `unreachable`,
`timeout`) is stored for the record and always checked again, so a
timeout from last week cannot keep failing an export.

**Concurrency.** The file is in WAL mode: readers in other processes do
not block a writer, and a writer does not block them. Every write that
touches more than one row runs in one transaction. One `Library` object
owns one connection, guarded by a lock.

## Identifier verification report

`thesisagents.core.export_validation` holds the export preflight.
`export_collection` runs it first, and it can be called on its own:

```python
from thesisagents.core.export_validation import verify_collection

report = await verify_collection(collection)
for check in report.failures:
    print(check.paper_key, check.kind, check.value, check.status, check.detail)
```

```python
class VerificationStatus(StrEnum):
    OK = "ok"                    # the identifier exists
    INVALID = "invalid"          # malformed DOI, unknown DOI, URL 404 / 410
    UNREACHABLE = "unreachable"  # DNS / connection failure, HTTP 5xx
    TIMEOUT = "timeout"          # no answer in time
    SKIPPED = "skipped"          # not checked, reason in `detail`

@dataclass(frozen=True)
class IdentifierCheck:
    paper_key: str               # Paper.bibtex_key()
    title: str
    kind: str                    # "doi" | "url"
    value: str                   # exactly as the paper carries it
    status: VerificationStatus
    resolved_url: str | None     # DOI landing page / redirect target
    detail: str                  # why, for every status except a plain ok

@dataclass(frozen=True)
class VerificationReport:
    checks: tuple[IdentifierCheck, ...]
    # .failures -> checks that block a strict export
    # .ok       -> True when nothing blocks
    # .counts() -> {"ok": n, "invalid": n, ...}
    # .to_dict() -> JSON-ready, the MCP `export` response's `verification`
```

`invalid`, `unreachable` and `timeout` block a strict export. `skipped`
does not: a `file://` URL, a publisher page that needs a real browser,
or a server that answers 401 / 403 / 429 could not be checked, which is
not evidence the identifier is wrong.

`value` is never replaced by `resolved_url`. A redirect target is where
the link leads today, not what the bibliography should cite.

`export_collection(collection, options, verification_cache=cache)`
accepts a cache (`MemoryVerificationCache`, or anything with the same
`get` / `put` methods) so that several exports of the same papers in one
run check each identifier once.

## Identifier parsing

`thesisagents.core.identifiers.parse_identifier(value: str)` is
the single entry point for resolving a `--paper` argument. It
returns a `ParsedIdentifier` carrying:

```python
@dataclass(frozen=True)
class ParsedIdentifier:
    value: str           # canonical form (e.g. "2401.08741")
    kind: IdentifierKind # ARXIV | DOI | PMID | IEEE_DOC
```

Accepted input forms:

| Kind | Examples |
|---|---|
| arXiv | `2401.08741`, `2401.08741v2`, `arXiv:2401.08741`, `https://arxiv.org/abs/2401.08741`, `https://arxiv.org/pdf/2401.08741v2.pdf`, `cs.LG/0001001` (legacy) |
| DOI | `10.1145/3411764.3445005`, `doi:10.1145/...`, `https://doi.org/10.1145/...` |
| PMID | `34567890`, `https://pubmed.ncbi.nlm.nih.gov/34567890/` |
| IEEE | `https://ieeexplore.ieee.org/document/10965643` (number is the IEEE document ID, not the DOI) |

The CLI raises a friendly `error: could not classify identifier`
for any value that doesn't match.

## Exceptions

The whole project's error type hierarchy is in
`thesisagents.core.exceptions`:

```
ThesisAgentsError                     # base — surfaces as exit code 2
├── ConfigError                          # missing API key, malformed env var
├── FetchError
│   ├── RateLimitError                   # 429 / explicit upstream rate limit
│   ├── ParseError                       # malformed JSON / XML / HTML
│   ├── CitationNotAvailableError        # a citation provider has no answer for this paper (expected, not a failure)
│   └── SourceUnavailableError           # 5xx that retries can't recover
├── CacheError                           # disk-cache I/O failure
├── LibraryError                         # the --library path is not a usable library (not SQLite, another app's file, newer schema)
└── ExportError                          # exporter failed to write
    ├── IdentifierVerificationError      # preflight found a wrong / unreachable DOI or URL
    └── TemplateError                    # a deck template or its config does not meet the template contract
```

Every fetcher's top-level method wraps upstream exceptions into
one of the above. Surface code (CLI / MCP / GUI) catches the base
`ThesisAgentsError` and renders it as a one-line error message;
unexpected exceptions surface as a stack trace so bugs are loud.
