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
                [--all-venues]
                [--paywall-threshold FLOAT] [--yes]
                [--max-slides N] [--dark-mode]
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

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success — every requested export was written. |
| `1` | Search returned zero results, or the single paper had no metadata. |
| `2` | Validation error (unknown source, malformed identifier, bad year range, missing API key when `--enrich`, …). |

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
