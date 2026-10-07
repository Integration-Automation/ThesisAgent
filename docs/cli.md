# CLI reference

`python -m thesisagents` (also installed as the `thesisagents`
console script) is the canonical entrypoint. It has two mutually
exclusive modes:

- **Search mode** — `--query <keywords>` runs the search pipeline against
  the requested source(s).
- **Single-paper mode** — `--paper <identifier>` resolves one paper by
  arXiv ID / URL, DOI, PMID, or IEEE document URL.

## Usage

```
thesisagents (--query KEYWORDS | --paper IDENTIFIER)
                [--source SOURCES] [--exclude-source SOURCES]
                [--max N]
                [--year-from YEAR] [--year-to YEAR] [--min-citations N]
                [--export FORMATS]
                [--out DIR]
                [--filename-stem STEM]
                [--no-abstract]
                [--lang LANG]
                [--enrich] [--lightweight]
                [--llm-model MODEL]
                [--top-tier-only]
                [--paywall-threshold FLOAT] [--yes]
                [--max-slides N] [--dark-mode]
                [--no-verify-identifiers] [--diagnostics]
                [--quiet]
```

## Flags

| Flag | Default | Notes |
|---|---|---|
| `--query` / `-q` | — | Keywords; mutually exclusive with `--paper`. |
| `--paper` / `-p` | — | arXiv (`2401.08741` / `https://arxiv.org/abs/...`), DOI (`10.x/y`), PMID (`12345678` or `https://pubmed.ncbi.nlm.nih.gov/...`), or IEEE document URL (`https://ieeexplore.ieee.org/document/...`). |
| `--source` / `-s` | default mix | Comma-separated. Available: `arxiv`, `semantic_scholar`, `openalex`, `pubmed`, `acm`, `dblp`, `crossref`, `openaire`, `europepmc`, `doaj`, `hal`, `ieee`, `springer`, `core`, `scholar` (15 total). **Default-on**: every open source (incl. `europepmc`, `doaj`, `hal`) + `ieee` + `scholar` (the latter two run visible Chrome via WebRunner; opt out with `THESISAGENTS_DISABLE_IEEE_SCRAPING=1` / `THESISAGENTS_DISABLE_SCHOLAR_SCRAPING=1`). `springer` joins only when `THESISAGENTS_SPRINGER_API_KEY` is set; `core` only when `THESISAGENTS_CORE_API_KEY` is set. `THESISAGENTS_IEEE_API_KEY` switches IEEE to the official Xplore API (anonymous-safe, no Chrome needed). |
| `--exclude-source` / `-x` | — | Comma-separated sources to remove from the mix, subtracted **after** `--source` resolves. The no-VPN gesture is to leave `--source` at its default and pass `--exclude-source ieee` — every other default source stays in. An unknown name (or excluding the whole mix) is an error. |
| `--max` / `-n` | `25` | Range 1..200. |
| `--year-from`, `--year-to` | — | Inclusive year filter. |
| `--min-citations` | — | Drop papers below this citation count, enforced across **all** sources (not just Semantic Scholar). Papers whose source reports no count are kept. Omit for no minimum. |
| `--export` / `-e` | mode-specific | Any of `pptx`, `xlsx`, `md`, `bib`, `json`, `ris`, `csv`, `csl`. **Default with `--query` is `pptx,xlsx,bib`; default with `--paper` is `pptx,bib`** (one-row Excel is busy work). Explicit `--export` always wins. `ris` (Zotero/Mendeley/EndNote), `csv` (flat table) and `csl` (CSL-JSON for Pandoc, written as `<stem>.csl.json`) are the interchange formats. |
| `--list-sources`, `--list-exports` | — | Print the available search sources / export formats and exit (no query needed). |
| `--out` / `-o` | `./exports` | Created if missing. |
| `--filename-stem` | auto | `{first-32-chars-of-query}-{YYYYMMDD-HHMMSS}` by default. |
| `--no-abstract` | off | Drops abstracts and any LLM summary content; the deck shows only title / author / link slides. |
| `--lang` / `-l` | `en` | Slide-deck template language. Supported: `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id` (14 in total). When combined with `--enrich`, also instructs the LLM to write its bullets in this language. |
| `--enrich` | auto-on when `ANTHROPIC_API_KEY` is set | Fetch each paper's PDF and have the Anthropic API write a structured summary; the deck switches to thesis-style layout. Requires `ANTHROPIC_API_KEY` and the `[intelligence]` extra. **Not needed when running over MCP** — an LLM agent can call `fetch_pdf_text` + `export` directly with a hand-crafted summary. |
| `--lightweight` | off | Force the abstract-only deck even when `ANTHROPIC_API_KEY` is set. Useful for unattended runs where you do not want to spend tokens. **When an LLM agent is in the editor session**, prefer the LLM-as-agent flow under `scripts/llm_*.py` (the LLM authors a rich `PaperSummary` per paper) over `--lightweight`. |
| `--llm-model` | `claude-opus-4-7` | Override the default model used when `--enrich` is on. Also reads `THESISAGENTS_LLM_MODEL`. |
| `--top-tier-only` | off | Restrict results to the curated top-tier CS venue whitelist (S&P / CCS / NDSS / USENIX Security / NeurIPS / ICML / ICSE / SIGMOD / SIGCOMM / CHI / etc.) + arXiv pass-through. **Off by default** so IEEE / ACM workshop papers (which dominate "LLM × security" / "LLM × X" topics) survive. |
| `--no-oa-resolve` | off | Skip the open-access PDF resolver step that runs after dedup. By default the pipeline looks up every paper without `pdf_url` in Unpaywall (needs `THESISAGENTS_CONTACT_EMAIL`) and falls back to an arXiv title search — typical lift of 40-70% for IEEE / ACM / Springer / Elsevier paywalled papers. Use this flag if you want raw source output without OA enrichment, or to skip the extra HTTP round-trips on a tight latency budget. |
| `--paywall-threshold` | `0.30` | Fraction of paywalled results above which the search-mode pipeline asks the user before generating per-paper PPTs. |
| `--yes` | off | Auto-accept the paywall prompt. |
| `--max-slides` | `25` | Per-paper slide cap. Pass `0` for unlimited. |
| `--dark-mode` | off | Render the pptx in dark mode. **The light navy-band deck is the default** (white slides, full-width navy header band with a white title, navy cover panel). Pass this flag for the dark variant — a post-build pass swaps to a dark slide background (`#12151B`) + near-white text (`#E5E7EB`) and lightens the navy band / cover / table-row fills so the same chrome reads on OLED projectors and in low-light venues. |
| `--no-verify-identifiers` | off | Export without the identifier preflight. By default every paper's DOI is looked up at doi.org and every URL is requested once, right after the search, and a wrong or unreachable DOI / URL stops the run before any PDF is downloaded or any file is written. Pass this flag when working offline. The notice that the check was skipped goes to stderr even under `--quiet`. See "Identifier verification" below. |
| `--diagnostics` | off | Explain the ranking of a `--query` search. Prints each paper's score split into relevance, recency and citations with an advisory `keep` / `review` / `prune` recommendation, and writes the full breakdown to `diagnostics.json` in `--out`. Advice only: every paper stays in the results. See "Ranking diagnostics" below. |
| `--quiet` | off | Suppress the per-paper one-line printout to stdout. |

## Examples

### Keyword search

```bash
# Default exports: pptx + xlsx + bib
thesisagents --query "diffusion models" --source arxiv --max 10 \
                --out ./exports/

# Restrict to recent work + custom filename
thesisagents --query "graph neural network drug discovery" \
                --year-from 2022 --year-to 2025 \
                --max 15 --export pptx,xlsx,bib --out ./exports/ \
                --filename-stem gnn-drug-review
```

### Single paper

```bash
thesisagents --paper 2401.08741 --out ./exports/
thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                --filename-stem attention --out ./exports/
thesisagents --paper "https://pubmed.ncbi.nlm.nih.gov/34567890/" \
                --out ./exports/
thesisagents --paper "https://ieeexplore.ieee.org/document/10965643" \
                --out ./exports/
```

### Local PDF (single or batch)

```bash
# One PDF — title / authors / year / DOI / arXiv ID / real abstract are
# extracted heuristically from the PDF front matter.
thesisagents --pdf ./papers/attention.pdf --out ./exports/

# Override any extracted field with a flag (only applies when exactly
# one PDF is passed).
thesisagents --pdf ./papers/preprint.pdf \
                --title "Custom Title" --authors "A. Smith, B. Jones" \
                --year 2025 --venue "NeurIPS 2025" \
                --out ./exports/

# Directory — every *.pdf is read, metadata-extracted, and emitted as its
# own deck named after its BibTeX key (e.g. wang2024diffusion.pptx).
thesisagents --pdf ./papers/ --out ./exports/
```

### Localised deck

```bash
thesisagents --paper 1706.03762 --lang zh-tw --out ./exports/
thesisagents --paper 1706.03762 --lang ja    --out ./exports/
thesisagents --paper 1706.03762 --lang fr    --out ./exports/
thesisagents --paper 1706.03762 --lang de    --out ./exports/
thesisagents --paper 1706.03762 --lang ko    --out ./exports/
# Also supported: es, pt, ru, it, vi, hi, id
```

### Enriched thesis-style deck (Python pipeline)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                --enrich --lang zh-tw --out ./exports/
```

When `--enrich` is on, ThesisAgents downloads the PDF, sends the body
text + paper metadata to Claude (`claude-opus-4-7` by default), parses
back a structured `PaperSummary` (motivation, contributions, method,
results, limitations, takeaways — plus the rich tier: pain points,
research question, KPI metrics, technique table, literature
positioning, per-RQ result tables, …), and the PPT exporter renders the
thesis-style layout.

### Review an existing deck

```bash
thesisagents review ./exports/attention.pptx
thesisagents review ./exports/*.pptx --lang zh-tw
```

The `review` subcommand audits a finished `.pptx` against all three
deck-quality contracts in one pass — slide **overflow**, the dark-mode /
no-red / contrast **colour** contracts, and `paper_rule` **section
completeness** (Introduction, Literature Review, Methodology, Experiment,
Conclusion). `--lang` is optional; the deck's language is auto-detected
from its slide titles otherwise. It prints a per-deck report and exits
with the number of decks that failed (`0` = all clean), so it drops into
CI. Section completeness only fails a *thesis-style* deck — a lightweight
abstract-only deck is never failed for legitimately lacking sections.
The same audit is the MCP `pptx_review` tool.

## Identifier verification

Every run checks the DOI and URL of every paper before it exports
anything. The check exists because a hand-written `Paper` can carry a
DOI typed from memory, and nothing else in the pipeline would notice
before it reached a `.bib` file or a references slide.

What is checked:

- **DOI**: the syntax first, with no network (`10.<registrant>/<suffix>`),
  then whether doi.org has it registered. The lookup goes to the doi.org
  handle API, so it never touches the publisher's site.
- **URL**: one request that reads only the response headers. Redirects
  are followed one hop at a time, and a hop to plain `http` or to a
  publisher page is not requested.
- A URL on a publisher host that needs a real browser (IEEE Xplore, ACM
  Digital Library, Springer, ScienceDirect, Wiley, …) is not requested.
  The paper's DOI is checked in its place.

Each identifier ends in one of five states:

| Status | Meaning | Stops the run |
|---|---|---|
| `ok` | The identifier exists. | no |
| `invalid` | Definitely wrong: a malformed DOI, a DOI doi.org does not know, a URL that answers 404 or 410. | yes |
| `unreachable` | No definite answer: DNS or connection failure, HTTP 5xx. Retried once first. | yes |
| `timeout` | No answer within 8 seconds. Retried once first. | yes |
| `skipped` | Not checked: a `file://` URL, a browser-only publisher page, or a server that refuses automated access (HTTP 401 / 403 / 429). | no |

`skipped` never stops a run, because "could not check" is not evidence
that the identifier is wrong.

A passing check shows that the identifier exists. It does not show that
the identifier belongs to this paper, so identifiers still have to be
copied from the search results and never composed by hand.

On success the CLI prints one line:

```
Identifiers: 41 verified, 6 not checkable, 0 failed.
```

On failure it exits with code `2` and names each identifier:

```
error: [preflight] identifier verification failed for 1 identifier(s) in 1 paper(s):
  - smith2024attention: doi 10.1234/typo is invalid (doi.org has no such DOI registered)
Copy each DOI / URL from the search results instead of typing it. To export without this check (for example offline), pass --no-verify-identifiers on the CLI, or verify_identifiers=False to the MCP export tool / ExportOptions.
```

The paper's own `doi` and `url` are never rewritten. Where a link leads
after its redirects is reported separately and is not written into the
bibliography.

## Source statistics

After every `--query` search the CLI prints what each source contributed.
No flag is needed, and `--quiet` hides it.

```
Sources (up to 25 requested from each):
  arxiv      23 returned, 23 after dedup
  openalex   25 returned, 21 after dedup
  dblp        0 returned, 0 after dedup
  ieee        0 returned  failed: [ieee] search page returned HTTP 403
  springer    0 returned  disabled: THESISAGENTS_SPRINGER_API_KEY is not set
```

A source that fails is skipped without stopping the search. That keeps
one broken publisher from sinking a run, and it also means a search that
lost half its sources looks, from the result list alone, like a search
on a topic with few papers. This table is how to tell them apart.

| Column | Meaning |
|---|---|
| requested | The per-source cap of the query (`--max`). |
| returned | Records the source sent back, before de-duplication. |
| after dedup | Unique papers credited to this source. A paper several sources returned is credited to the first of them in `--source` order, so the values add up to the number of unique papers. |
| status | Shown only when it is not `ok`: `failed` (the source raised an error), `rate_limited` (it kept answering HTTP 429 through every retry) or `disabled` (the plugin could not be loaded, usually a missing API key), followed by the error text. |

In the example OpenAlex returned 25 records and is credited with 21,
because four of them were papers arXiv had already returned and arXiv is
named first. DBLP answered and had nothing, which is not a failure. IEEE
and Springer contributed nothing for reasons that have nothing to do
with the topic.

The counts are taken before the year, citation and top-tier filters and
before the final cut to `--max` results, so they describe the sources,
not the filtered list. The example found 44 unique papers and the run
kept the best 25.

`--list-sources` is a different question: it lists the sources that
exist and which run by default, not what they returned for a query.

## Ranking diagnostics

A keyword search returns off-topic papers by construction: a "Claude
code" query once returned a Viterbi-decoder paper because both contain
"code". `--diagnostics` shows why each paper ranks where it does, so
those papers can be spotted before their PDFs are read.

```bash
thesisagents --query "transformer attention" --source arxiv --max 10 \
    --diagnostics --out ./exports/attention/
```

Right after the search the CLI prints one line per paper. The reasons
are spelled out only for papers recommended for review or pruning. The
four papers below are made up for the example, and the numbers are what
the tool prints for them in 2026:

```
Ranking diagnostics for: transformer attention
  [  1] keep    total 5.42 = relevance 4.60 + recency 0.82 + citations 0.00
        Transformer Attention at Scale
  [  2] keep    total 3.85 = relevance 3.30 + recency 0.55 + citations 0.00
        Efficient Attention for Vision Transformers
  [  3] review  total 1.61 = relevance 0.60 + recency 0.37 + citations 0.65
        A Survey of Sequence Models
        - abstract matches 2 of 2 query terms (transformer, attention): +0.60
        - published 2021: recency +0.37
        - 40 citations: +0.65
        > relevance is 13% of the best this query allows, below the review threshold 30%
        rule: review_below_relevance=0.30
  [  4] prune   total 0.56 = relevance 0.00 + recency 0.11 + citations 0.45
        Cooking With Gas: A Kitchen Safety Study
        - no query term appears in the title or abstract
        - published 2015: recency +0.11
        - 12 citations: +0.45
        > relevance is 0% of the best this query allows, below the prune threshold 10%
        rule: prune_below_relevance=0.10
Recommendations: 2 keep, 1 review, 1 prune. Advice only, nothing was removed.
Diagnostics written to: /abs/path/exports/attention/diagnostics.json
```

Paper 3 mentions both query words only in its abstract, which earns 13%
of the best possible relevance, so it is worth a second look. Paper 4
shares no word with the query.

The score is the sum of three parts (see
[`architecture.md`](architecture.md) "Ranking"):

| Part | What it measures |
|---|---|
| `relevance` | How much of the query appears in the title (weighted most) and the abstract, plus a bonus when query words that are adjacent in the query are also adjacent in the title. |
| `recency` | Decays with the paper's age. A paper published this year scores 1.00, a five-year-old one 0.37. |
| `citations` | Grows with the logarithm of the citation count, damped so that a heavily cited off-topic paper cannot outrank an on-topic one. |

The recommendation comes from three rules, applied in this order:

| Rule | Recommendation |
|---|---|
| Relevance below 10% of the best this query allows | `prune` |
| Relevance below 30% | `review`, or `prune` when the paper is also ten or more years old and has fewer than 5 citations |
| Title shares at least 85% of its terms with a higher-ranked paper | `review` (the two are probably versions of one work) |

A low citation count on its own never produces a recommendation: a new,
on-topic paper has no citations yet. An unknown year or an unknown
citation count is not treated as old or uncited.

`diagnostics.json` holds one entry per paper with the full reasons for
every paper, including the ones marked `keep`:

```json
{
  "keywords": "transformer attention",
  "advisory": true,
  "summary": {"keep": 2, "review": 1, "prune": 1},
  "papers": [
    {"rank": 4, "paper_key": "hash:c91ad152ca0a7fa4",
     "bibtex_key": "park2015cooking",
     "title": "Cooking With Gas: A Kitchen Safety Study",
     "score": {"total": 0.5564, "relevance": 0.0, "recency": 0.1108,
               "citation": 0.4456, "relevance_ratio": 0.0,
               "matched_terms": [], "matched_phrases": [],
               "reasons": ["no query term appears in the title or abstract",
                           "published 2015: recency +0.11",
                           "12 citations: +0.45"]},
     "recommendation": {"action": "prune",
                        "threshold": "prune_below_relevance=0.10",
                        "reasons": ["relevance is 0% of the best this query allows, below the prune threshold 10%"]}}
  ]
}
```

(Only the fourth of the four entries is shown.) `paper_key` is the
paper's identity key: its DOI, else its arXiv ID, else a hash of title,
first author and year, as here.

`bibtex_key` is how the PDFs and per-paper decks of the run are named
(`pdfs/<bibtex_key>.pdf`, `<bibtex_key>.pptx`), so a script that acts on
the recommendations can find the files.

The recommendations are advice. No paper is removed from the results,
the exports, or the disk. Read the abstracts of the `review` and
`prune` papers before deleting anything.

`--diagnostics` applies to `--query` searches. `--paper` and `--pdf`
fetch specific papers with no query to be relevant to, and say so.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success — every requested export was written. |
| `1` | Search returned zero results, or the single paper had no metadata. |
| `2` | Validation error (unknown source, malformed identifier, bad year range, missing API key when `--enrich`, …). Also returned when the identifier preflight stops the run because a DOI or URL is wrong or unreachable. |

## Output structure

```
exports/
├── diffusion-models-20260515-001027.pptx
├── diffusion-models-20260515-001027.xlsx
├── diffusion-models-20260515-001027.bib
└── diffusion-models-20260515-001027.json   # only when --export includes json
```

Filenames are derived from a sanitised slug of the keyword + timestamp;
pass `--filename-stem` to fix the stem. The `.pptx` file produced here
can be edited via the `pptx_*` MCP tools or the `pptx_edit` Python
module — see [pptx editing](pptx_editing.md).

## Source plugin opt-ins

Some plugins are opt-in either because their upstream terms restrict
automated traffic, or because the upstream service needs an API key
that we cannot ship in the repo:

```bash
# IEEE — official API path (anonymous-safe, no Chrome needed)
export THESISAGENTS_IEEE_API_KEY=...
thesisagents --paper "https://ieeexplore.ieee.org/document/10965643" --out ./exports/

# IEEE — default visible-Chrome path (no key needed; works if you have VPN/subscription)
# IEEE is default-ON; opt out only on CI / no-Chrome:
# export THESISAGENTS_DISABLE_IEEE_SCRAPING=1
thesisagents --paper "https://ieeexplore.ieee.org/document/10965643" --out ./exports/

# Springer Nature — free API key from https://dev.springernature.com/
export THESISAGENTS_SPRINGER_API_KEY=...
thesisagents --query "diffusion models" --source springer --out ./exports/

# Google Scholar — default-ON via visible Chrome
# Opt out (e.g. on CI) with: export THESISAGENTS_DISABLE_SCHOLAR_SCRAPING=1
thesisagents --query "attention mechanism" --source scholar --out ./exports/

# Persistent Chrome profile — set once, VPN/SSO + Google sign-in survive across runs
export THESISAGENTS_CHROME_PROFILE_DIR=~/.cache/thesisagents-chrome
thesisagents --query "speculative decoding" --out ./exports/
```

Other source-related env vars (all optional):

| Variable | Effect |
|---|---|
| `THESISAGENTS_S2_API_KEY` | Higher rate limit on Semantic Scholar. |
| `THESISAGENTS_NCBI_API_KEY` | Raises PubMed's anonymous limit (3 → 10 req/s). |
| `THESISAGENTS_CONTACT_EMAIL` | Sent to Crossref / OpenAlex (`mailto`) → polite-pool rate; sent to NCBI (`tool` + `email`) as standard etiquette. |
| `THESISAGENTS_CROSSREF_PLUS_TOKEN` | Attached as `Crossref-Plus-API-Token: Bearer ...` on `acm` and `crossref` requests. Lifts rate limit + freshens cache. |
| `THESISAGENTS_PDF_COOKIES_FILE` | Path to a Netscape-format `cookies.txt`. Cookies for hosts matching a PDF URL are attached only on PDF download requests. Use this only with publishers you have legitimate access to. |
