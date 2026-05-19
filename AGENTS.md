# AGENTS.md

Cross-agent guide for **AutoPaperToPPT**. Mirrored from `CLAUDE.md`, kept
short so any agent (Codex CLI, Cursor, Aider, Windsurf, Cline, Continue,
or a future tool) can pick up the must-know rules without parsing the
full project guide. `CLAUDE.md` remains the canonical, deeper reference
— this file links the rules an agent is most likely to mis-handle.

## Project shape

Python 3.12+ CLI + MCP server that searches papers, downloads PDFs,
and produces `.pptx` / `.xlsx` / `.bib`. Default flow: multi-source
search → dedup → per-source rate-limited fetch → per-paper PPT only
when the PDF is downloadable. See `CLAUDE.md` for the full architecture,
fetcher plugin layout, and Definition of Done gates.

## LLM-as-agent default path (CRITICAL — read before any search work)

**Rich thesis-style PPT is the default deliverable. Lightweight is a
fallback, never the goal when an LLM is in the loop.**

### Decision tree

1. Does the user have `ANTHROPIC_API_KEY` set?
   * **YES** → the CLI auto-enriches; just run it and you are done.
2. Does an LLM agent (you) drive this session?
   * **YES** — you are reading this, so the answer is always yes when
     this rule applies — **you produce the rich summary yourself**.
     Read each PDF, hand-author a `PaperSummary` with rich-tier fields,
     drop a `scripts/regen_<query>.py` script, run it. The lightweight
     deck that the CLI just emitted is an intermediate artefact, not
     the deliverable.
3. No LLM, no key (CI / cron / unattended scripts)
   * The lightweight deck is acceptable. Authors get an abstract-based
     summary; that's the limit without an LLM.

### Anti-patterns (do NOT do these)

* **Do NOT** end a multi-paper search by saying "set `ANTHROPIC_API_KEY`
  for a rich deck" — you ARE the LLM that could write the summaries.
  Telling the user to acquire a separate API key is offloading your own
  job. The user invoked you precisely so they wouldn't have to.
* **Do NOT** treat the per-paper lightweight `.pptx` as the final
  deliverable when the user asked for slides. Lightweight is page 1 of
  your work, not the report.
* **Do NOT** stop after `download_pdfs` reports "N PDFs saved" — that's
  the start of the rich-authoring phase, not the end.
* **Do NOT** invent numbers, RQs, contributions, or limitations not in
  the paper. Every figure must trace back to text in the PDF.
* **Do NOT** fabricate `url` / `doi` / `arxiv_id` from memory when
  hand-authoring a `Paper`. Publisher URL paths *cannot* be guessed
  (AAAI uses numeric IDs not author slugs; IEEE uses `arnumber`; ACM
  uses opaque DOIs). Always copy these fields **verbatim from the xlsx
  the same search produced** — see "URL / DOI verification" below.
* **Do NOT** leave irrelevant downloads in the run directory. The
  search keyword often pulls in off-topic papers (e.g. "code review"
  matched a paper on object detection literature review; "Claude code"
  matched a Viterbi decoder paper). Once you classify a downloaded
  paper as off-topic for the user's actual intent, **delete its
  `pdfs/<key>.pdf` and the lightweight `<key>.pptx`** so the run dir
  cleanly reflects the deliverable. The aggregate xlsx / bib record
  the full search and stay as-is.

### Worked example
`scripts/regen_llm_security_batch.py` ships 7 hand-authored rich
summaries built exactly this way — read each PDF, author the summary,
batch-export. Reuse it as the template for any future multi-paper
search.

### Per-paper flow

1. Get the PDF into the exports dir, one of two ways:
   * `py -m autopapertoppt --paper <url-or-id> --out ./exports/<run>/` to
     fetch metadata and download the PDF (`./exports/<run>/pdfs/<key>.pdf`
     lands automatically); or
   * `py -m autopapertoppt --pdf <local-path> --out ./exports/<run>/`
     when the user supplied a PDF themselves — the file is copied into
     `./exports/<run>/pdfs/` and a stub `Paper` (with `source="local"`)
     is built. Use `--title --authors --year --venue --doi --arxiv-id`
     to override metadata when the filename / heuristic isn't right.
2. Read the PDF yourself. If your editor's Read tool can't handle the
   full file, dump plain text via the project's internal extractor —
   `from autopapertoppt.intelligence.pdf import _extract_text` — then
   chunk the output. Do not re-implement PDF extraction.
3. Hand-author a `PaperSummary` populated with the rich-tier fields
   (`pain_points`, `research_question`, `contributions_detailed`,
   `headline_metrics`, `technique_table`, `method_sections`,
   `evaluation_sections`, `system_flow`, `research_questions`,
   `rq_results`, `core_observation`, `limitations`, `future_work`).
   Only include numbers / claims that appear verbatim in the paper.
   Set `model="<your model id> (LLM-as-agent, read N-page PDF)"` and
   `raw_text_chars` to the extracted length so provenance is visible on
   the deck.
4. Call the exporter — either through the MCP `export` tool (when a
   live MCP server is in play) or directly in Python by constructing a
   `Paper` with `summary=…`, wrapping it in a `PaperCollection`, and
   passing it to `export_collection(...)`. Save the script under
   `scripts/regen_<authoryear>_<slug>.py` so the regen is reproducible.
5. **Canonical filename, no `-rich` suffix.** Set
   `filename_stem=paper.bibtex_key()` so the rich deck **overwrites**
   the CLI's lightweight emit at the same path. One `.pptx` per paper,
   the rich one. Do NOT keep both — the lightweight is not a
   deliverable. (Language variants are the only exception: a zh-tw
   companion uses `f"{key}-zh-tw"`, but no en deck ever uses `-rich`.)
6. Cap `contributions_detailed` at **≤ 4 entries**. The contributions
   slide's stack layout overshoots the 7.05" footer guard above that.
7. Run the headless overflow check before handing the deck back — every
   non-`footer` / non-`page_number` shape must have
   `top + height ≤ 7.05"` on a 16:9 widescreen slide.

Working templates: `scripts/regen_llm_security_batch.py` (batch, 7
papers), `scripts/regen_ling2026_agent_skills.py` (single paper en),
`scripts/regen_ling2026_agent_skills_zh_tw.py` (single paper zh-tw),
`scripts/regen_ieee_thesis_style.py` (single paper).

### URL / DOI verification (mandatory)

Publisher URL paths cannot be guessed — AAAI uses numeric article IDs
(`v40i5.37389`, not `view/fang2026`); IEEE uses `arnumber`; ACM uses
opaque DOIs. Fabricated identifiers ship broken links to the user.

**Rule**: When hand-authoring a `Paper`, copy `url` / `doi` /
`arxiv_id` *verbatim from the search xlsx that produced this run*.
Never write them from memory; never construct them from the title.

Concrete workflow:

```python
# After running the search the user requested:
#   py -m autopapertoppt --query "..." --out ./exports/<run>/
# the aggregate xlsx sits at exports/<run>/<slug>-<timestamp>.xlsx
# with columns: # | Title | Authors | Year | Source | Indexed via |
#               DOI | URL | PDF | Citations | Abstract
#
# For each paper you author a PaperSummary for, copy:
#   - column 7 (DOI)  → Paper.doi
#   - column 8 (URL)  → Paper.url
#   - extract the arxiv ID from column 8 if it points at arxiv.org
#
# Strip any "v1" / "v2" version suffix from arxiv URLs:
#   "https://arxiv.org/abs/2506.09580v1" → arxiv_id "2506.09580"
#
# If a column is empty, leave the field as None — do NOT fabricate.
```

After the regen script finishes, audit by comparing each paper's `url`
back to that column:

```bash
.venv/Scripts/python.exe -X utf8 -c "
from openpyxl import load_workbook
import sys; sys.path.insert(0, '.'); sys.path.insert(0, 'scripts')
from scripts.regen_<run> import ALL_PAPERS
wb = load_workbook('exports/<run>/<slug>-<ts>.xlsx')
real = {sh.cell(row=r, column=2).value: sh.cell(row=r, column=8).value
        for sh in [wb['Papers']]
        for r in range(2, sh.max_row + 1)}
for p in ALL_PAPERS:
    actual = next((u for t, u in real.items() if p.title[:30] in (t or '')), None)
    if actual and not (p.url == actual or p.url.split('v')[0] == actual.split('v')[0]):
        print(f'! {p.bibtex_key():<30s} authored {p.url} vs real {actual}')
"
```

Any `!` line means a fabricated URL — fix it before handing the deck
to the user. `scripts/regen_llm_security_batch.py` was rebuilt this
way after two papers (Wen, Fang) were caught with fabricated AAAI
URLs that pointed nowhere.

### Pruning irrelevant downloads (mandatory)

The search engine is keyword-based, so off-topic papers will slip in:
a "Claude code" query returned a Viterbi decoder paper because both
contain "code"; an "LLM code review" query returned a paper on object
detection literature review. Once you read the abstracts and decide a
paper is off-topic for the user's actual intent, prune the run dir:

```python
from pathlib import Path
run = Path("exports/<run>")
irrelevant_keys = ("key-of-off-topic-paper-1", "key-of-off-topic-paper-2")
for key in irrelevant_keys:
    for path in (run / "pdfs" / f"{key}.pdf", run / f"{key}.pptx"):
        if path.exists():
            path.unlink()
```

Delete: `exports/<run>/pdfs/<key>.pdf` + `exports/<run>/<key>.pptx`.

Keep: the aggregate xlsx / bib — those are the **honest record** of
what the search returned. Off-topic papers staying in the xlsx is
fine; the user can see the full search outcome there.

Decision rule: a paper is off-topic when its actual research question
doesn't match the user's intent. "Claude (Sonnet 4.6) across six
languages" is off-topic for a "Claude Code code review" query (paper
is about Claude the model's multilingual ability, not Claude Code
the agentic tool). Borderline cases get a rich summary — better to
over-include than to silently drop a possible match.

## Sources you can search

Default mix (no env vars required): `arxiv`, `semantic_scholar`, `openalex`,
`pubmed`, `acm` (Crossref-scoped), `dblp`, `crossref` (unscoped),
`openaire`. Pulled in automatically when `--source` is not given.

Opt-in plugins (need an env var or explicit flag):
- `ieee` — **on by default**, search and document fetch go through
  **visible Chrome via WebRunner** (`sources/ieee/webrunner_backend.py`).
  See "IEEE / paywalled domains use WebRunner" below — this is a hard
  rule, not a perf hint. Set `AUTOPAPERTOPPT_IEEE_API_KEY` to switch
  to the official Xplore API path; set
  `AUTOPAPERTOPPT_DISABLE_IEEE_SCRAPING=1` to opt out entirely
  (CI / no-Chrome environments only).
- `springer` — set `AUTOPAPERTOPPT_SPRINGER_API_KEY` (free key from
  https://dev.springernature.com/). Required — the plugin raises
  `ConfigError` without it.
- `scholar` — set `AUTOPAPERTOPPT_ENABLE_SCHOLAR_SCRAPING=1`. Google
  Scholar ToS forbids scraping; off by default. When on, also goes
  through WebRunner (visible Chrome), not httpx.

For top-tier-only searches (the default), the filter in
`autopapertoppt/core/top_venues.py` accepts arXiv passthrough plus a
curated whitelist of CS conferences/journals and multidisciplinary
flagships (Nature, Science, PNAS, CACM, Lecture Notes in CS, …). Pass
`--all-venues` to disable the filter.

## Other rules you will trip on

- **No live network in tests.** Every fetcher test uses recorded
  fixtures under `tests/fixtures/<source>/`. Re-recording is a
  separate manual step (`scripts/record_fixture.py`).
- **HTTPS-only.** All outbound HTTP goes through
  `autopapertoppt/fetchers/http.py::get_client(source)`. The transport
  rejects non-HTTPS requests, including mid-flight redirects. Do not
  call `httpx.get` / `requests.get` directly.
- **Per-paper PPT gate.** When `--query` results trigger pptx
  generation, a paywall ratio above 30 percent prompts the user before
  any slides are produced. `--yes` skips the prompt. Single-paper
  `--paper` mode aborts with exit 1 if the PDF can't be retrieved.
- **IEEE / paywalled domains use WebRunner, not httpx.** IEEE search,
  IEEE document fetch, Google Scholar search, and any paywalled-PDF
  download from publisher CDNs (ieeexplore.ieee.org, dl.acm.org,
  link.springer.com, sciencedirect.com, wiley/oup/nature/science/…)
  MUST go through visible Chrome — the IEEE plugin's WebRunner backend,
  the Scholar plugin's WebRunner backend, or `mcp__webrunner__*` tools
  from the LLM-as-agent session. The httpx branch in those plugins is
  a CI safety net for environments without Chrome; on a user machine
  with VPN access, a silent fall-through to httpx is a bug, not an
  acceptable degradation. If you don't see a Chrome window open for an
  IEEE search, treat the result set as suspect. Full rule + audit
  checklist: `.claude/agents/compliance-auditor.md`.
- **Slide-deck guards.** 16:9 widescreen, body between 1.5" and 7.0",
  `FOOTER_GUARD = 7.05"`. Every textbox runs through `_truncate(...)`
  with the per-layout cap. Don't add slides that balance "stacks + tail
  callout" inside a fixed height — split onto their own slides.
- **Commits.** Never add `Co-Authored-By` lines. Never mention any AI
  tool / model name in commit messages, PR titles, PR descriptions,
  code comments, or docs. (See `CLAUDE.md` "Git Commits" for full
  detail.)
- **Definition of Done.** Every change must pass `py -m pytest tests/`,
  `py -m ruff check .`, and
  `py -m bandit -c pyproject.toml -r autopapertoppt/ sources/` before
  it can be committed. New code requires new tests.

## Where to look for the rest

- Slim overview + Git Commit hygiene + Browser-Automation hard rule:
  **`CLAUDE.md`** (top-level, always loaded).
- Code-quality / SOLID / linter / SonarQube rule list:
  `.claude/agents/code-quality-reviewer.md`.
- Network safety, core-vs-source-plugin boundary, browser-automation
  audit checklist, path-safety, suppression conventions, bandit-skip
  config: `.claude/agents/compliance-auditor.md`.
- pptx rendering tiers, truncation caps, semantic shape names, i18n,
  enrichment dispatch: `.claude/agents/slide-deck-rules.md`.
- Env vars + Python / `.venv` toolchain reference:
  `.claude/agents/env-vars.md`.
- DoD gate runner: `.claude/agents/dod-verify.md`.
- LLM-as-agent thesis-style authoring: `.claude/agents/paper-summary-author.md`
  + `post-author-audit.md` + `slide-overflow-check.md`.
- Per-source plugin contract and recorded fixtures: `sources/<name>/`
  + `tests/fixtures/<name>/`.
- LLM-as-agent flow examples: `scripts/regen_*.py`.
