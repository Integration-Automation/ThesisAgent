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
    top_tier_only: bool = True        # apply the venue whitelist
    min_citations: int | None = None  # discard below this (MCP-only flag)
```

| Field | Required | Notes |
|---|---|---|
| `keywords` | yes | Must be non-empty after `normalize_query`. URL/HTML encoding is per-source — you pass plain text. |
| `sources` | yes | Empty tuple is rejected at construction. Use `ALL_SOURCES` from `core.constants` to get the full list. |
| `max_results` | no | Clamped to `[1, MAX_RESULTS_PER_SOURCE]` (200) by `pydantic` validation. |
| `year_from` / `year_to` | no | Either or both. `year_from > year_to` is rejected. |
| `top_tier_only` | no | When True (default), filters to the curated CS top-tier whitelist + arXiv pass-through. |
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
```

| Field | Notes |
|---|---|
| `query` | Used by the `.xlsx` exporter's "Query" provenance sheet, by the `.md` exporter's header, and by the `.pptx` exporter's footer. |
| `papers` | Tuple (frozen). Order matters — exporters render in the order given. |

### Helpers

```python
len(collection)                # → len(collection.papers)
collection.to_dict()           # → JSON-serialisable
PaperCollection.from_dict(d)   # → round-trip
```

## `ExportOptions`

The exporter contract.

```python
@dataclass(frozen=True)
class ExportOptions:
    formats: tuple[str, ...]       # subset of ALL_EXPORTS
    out_dir: str                   # filesystem path
    filename_stem: str | None = None  # override autogen
    include_abstract: bool = True  # off → drops abstract + summary
    language: str = "en"           # slide-deck language code
    max_slides_per_paper: int = 25 # 0 = unlimited
```

| Field | Notes |
|---|---|
| `formats` | Validated against `ALL_EXPORTS = ("pptx", "xlsx", "bibtex", "markdown", "json")`. |
| `out_dir` | Created if missing. Path-traversal-safe (resolved via `utils.path_safety`). |
| `filename_stem` | When `None`, the pipeline generates `{slug-of-query}-{YYYYMMDD-HHMMSS}`. Hand-authored regen scripts typically set this to the BibTeX key. |
| `include_abstract` | False produces a deck that's title + authors + link slides only — useful when you want a one-sentence summary deck for hundreds of papers. |
| `language` | Must be one of the 14 supported slide-deck languages. Unknown codes fall back to `en` via `normalise_language`. |
| `max_slides_per_paper` | Caps each paper's slide count; the exporter drops lower-priority sections (figures, paper-tables, contribution-summary, pagination tails) until the count fits. Cover / overview / contributions / metrics / core observation / references are always kept. Pass `0` to disable the cap. |

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
│   └── SourceUnavailableError           # 5xx that retries can't recover
├── CacheError                           # disk-cache I/O failure
└── ExportError                          # exporter failed to write
```

Every fetcher's top-level method wraps upstream exceptions into
one of the above. Surface code (CLI / MCP / GUI) catches the base
`ThesisAgentsError` and renders it as a one-line error message;
unexpected exceptions surface as a stack trace so bugs are loud.
