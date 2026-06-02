# Project Guidelines

> **Other agents:** `AGENTS.md` mirrors the cross-agent must-knows. Codex CLI,
> recent Aider, and several other tools auto-load `AGENTS.md`; keep them in
> sync when you change rules. Detailed rules now live in `.claude/agents/`,
> organised into two subfolders — `rules/` (read-only reference subagents:
> `code-quality-reviewer`, `compliance-auditor`, `slide-deck-rules`,
> `deck-design`, `env-vars`, `language-vocabulary-check`, `paper_rule`) and
> `tasks/` (task-running / multi-tasking agents: `dod-verify`,
> `paper-summary-author`, `post-author-audit`, `slide-overflow-check`). Claude
> Code discovers them recursively by `name:`, so the path never affects how an
> agent is invoked. Full path index: see "Where the detailed rules live" below.

## Project Overview

AutoPaperToPPT is a Python CLI + MCP assistant that:

1. **Searches academic papers** by user-supplied keywords across multiple sources
   (arXiv, Semantic Scholar, OpenAlex, PubMed, IEEE Xplore, ACM Digital Library, DBLP,
   Crossref, OpenAIRE, Springer Nature, Google Scholar). Each source ships behind a
   fetcher adapter — adding a source does not touch the exporter layer or MCP server.
2. **Normalises** results into a `Paper` record, de-duplicates by DOI / arXiv ID /
   title-fuzzy-match, ranks by recency + citation count.
3. **Optionally enriches** each paper into a structured `PaperSummary` via either the
   LLM-as-agent flow (no API key — MCP-aware LLM authors the summary) or the
   Python pipeline (`ANTHROPIC_API_KEY` set — Anthropic API call).
4. **Generates** `.pptx` (three rendering tiers — lightweight / enriched-flat /
   thesis-style), `.xlsx`, `.bib`, `.md`, `.json` outputs.
5. **Exposes** every step as an MCP tool (`search`, `fetch_paper`, `fetch_pdf_text`,
   `export`, `pptx_inspect`, `pptx_update_slide`, `pptx_delete_slide`,
   `pptx_reorder_slides`, `pptx_add_slide`).

Single-process, Python 3.12+. Heavy I/O off the event loop; shared
`httpx.AsyncClient` registry pools connections per source.

### Top-level layout

```
AutoPaperToPPT/
├── autopapertoppt/                  # main package (everything installable lives here)
│   ├── core/                         # Paper / PaperSummary / Query models, dedup, ranking, pipeline
│   ├── fetchers/                     # HTTPS-only shared client, token-bucket rate limit, WebRunner browser
│   ├── exporters/                    # pptx (rich + lightweight), xlsx, bibtex, markdown, json + pptx_edit + i18n
│   ├── intelligence/                 # PDF fetch/extract + Anthropic summariser ([intelligence] extra)
│   ├── mcp/                          # FastMCP server registering all tools
│   ├── sources/<name>/               # per-source plugins (arxiv/, semantic_scholar/, openalex/, pubmed/,
│   │                                 # ieee/, acm/, scholar/, dblp/, crossref/, openaire/, springer/)
│   ├── utils/                        # logging, path safety, async helpers
│   ├── cli.py                        # argparse CLI
│   └── __main__.py
├── tests/                            # pytest + recorded fixtures (hermetic, no live HTTP)
├── docs/                             # Sphinx tree (en + zh-tw + zh-cn)
├── scripts/                          # one-off regen / fixture-record scripts
├── pyproject.toml                    # ruff, bandit, build, optional extras
└── .bandit                           # canonical bandit skip list
```

## Definition of Done (HARD REQUIREMENT)

Every change MUST pass the full gate set before commit. **Delegate to the
`dod-verify` subagent** — it owns the exact gate list, commands, and pass/fail
report format (and chains `slide-overflow-check` when exporters/i18n change,
`code-quality-reviewer` for deeper code-quality review,
`compliance-auditor` for project conventions). Skipping a gate "to come back
later" is not allowed.

## Content additions must be context-clear + detail-explained (HARD)

Every addition to this project — **a new rule in a subagent doc, a new
paragraph in a paper, a new bullet on a slide, a new constant or helper
in code** — must (1) have **clear context** for why it exists and (2)
carry a **detailed enough explanation** that a reader who didn't witness
the change can act on it without further questions.

Concretely:

| Addition type | "Clear context" means | "Detailed explanation" means |
|---|---|---|
| Subagent rule | A **Why:** clause naming the past incident / failure mode the rule prevents. | At least one **example** of the rule applied + one **anti-pattern** showing how it fails. Rules without examples bit-rot. |
| Paper / thesis paragraph | A topic sentence locating the paragraph in the larger argument (which section, which RQ, which contribution). | Every technical term defined at first use (see `paper_rule` "Technical terminology"), and every quantitative claim cited or shown in a table. |
| Slide bullet | A sub-head that says what the slide as a whole is about. | Every acronym / math notation / library name glossed at first use (see `slide-deck-rules` §8 "Content clarity & first-use context"). |
| Code helper | A docstring naming the boundary the helper guards and the failure mode it prevents. | Type hints + one usage example in either the docstring or a unit test. |

**Why this is a top-level rule rather than buried in one subagent**: it
applies across every surface this project produces (rules, papers,
slides, code) and has been the single most common review-cycle source of
churn — "why does X exist?" / "what does Y do?" questions that should
have been answered at write-time. The subagent-specific applications
(`paper_rule` "Technical terminology", `slide-deck-rules` §8 "Content
clarity & first-use context", `code-quality-reviewer` "docstring +
example") all derive from this top-level principle. When in doubt about
how to phrase an addition, default to "explain like the reader just
joined the conversation".

**Prose punctuation in additions**: prefer `，` (Chinese) or `,` (English)
to join clauses, and avoid `；` / `;`. **Why**: short comma-joined
clauses are easier to scan than semicolon-stacked compound sentences,
and mixed semicolon use creates inconsistent punctuation density across
the rule base — a reader scanning for the next rule loses focus on
"is this still part of the previous clause or a new point?". **How to
apply**: when a `;` would join two clauses, either swap it for `，` /
`,` or split into two sentences (the second option reads even more
clearly for rule prose). **Exceptions kept**: math notation like
`I(za;zb|Ep)` retains its mandatory `;` (it's part of the operator
syntax, not prose), and APA in-text citation grouping like
`(Lee, 2023; Smith et al., 2024)` keeps `;` because APA mandates it as
the separator inside a single citation parenthesis.

## Git Commits

- NEVER add `Co-Authored-By` lines.
- NEVER mention "Claude", "Claude Code", "AI-generated", "GPT", "Copilot", or any
  AI tool / model name anywhere — commit messages, PR titles, PR descriptions,
  code comments, documentation.

## IEEE / Publisher CDN: Browser Automation Is Mandatory (HARD RULE)

**Before triggering ANY search that involves paywalled publishers
(IEEE / ACM / Springer / etc.), the LLM in this session MUST confirm
the user's VPN / institutional access status first** — either by
recalling a recent statement, or by asking via `AskUserQuestion`
("Do you have VPN for IEEE / ACM / Springer for this topic?").
Without VPN, IEEE returns abstract-only / 403 for the PDF stage and
the per-paper download fails. When the user says no VPN, restrict
the search to `arxiv,openalex,pubmed,crossref,dblp,openaire,scholar`
— that is, **skip only `ieee`**. Google Scholar is publicly
accessible and stays in the mix even without VPN (Chrome still boots
for it because of captcha resilience, but the search itself works).
This gate applies BEFORE running `python -m autopapertoppt -q …`,
before `scripts/llm_driven_search.py`, and before any
`scripts/llm_download_*pdf*.py` invocation.

IEEE search, IEEE document fetch, Google Scholar search, and any paywalled-PDF
download from publisher CDNs (ieeexplore.ieee.org, dl.acm.org, link.springer.com,
sciencedirect.com, wiley/oup/nature/science/…) MUST go through **visible Chrome**.
Two paths exist:

1. **Python pipeline** — IEEE / Scholar plugins under `autopapertoppt/sources/<name>/` call their own `webrunner_backend`
   from inside `asyncio.gather`. Used by the CLI in unattended mode.
2. **LLM-as-agent** — the LLM in a Claude Code session drives Chrome itself via
   Bash + `autopapertoppt.fetchers.webrunner_browser.make_driver()`. Reference:
   `scripts/llm_driven_search.py` + `scripts/llm_parse_results.py`. The
   `mcp__webrunner__*` server registered for this project only exposes static
   helpers (lint / translate / score) — it does NOT expose
   `webrunner_run_actions` or any other browser-driving tool, so the LLM cannot
   skip the Bash + Selenium step.

The httpx branch in those plugins is a CI safety net for no-Chrome environments;
on a user machine with VPN, silent fall-through to httpx is a bug. **Never
suppress the visible window** (`--headless`, etc.). If you don't see a Chrome
window open during an IEEE / Scholar / paywalled-PDF step, the path is broken
— surface it, don't trust the results. Full rule + audit checklist:
`compliance-auditor` subagent.

## Read Subagents BEFORE Editing Any .pptx (HARD RULE)

**Before opening any `.pptx` file in this repository for edit — whether it
was generated by AutoPaperToPPT's exporter or supplied by the user as a
hand-made deck (e.g. anything under `exports/`, `assets/template/`, or any
ad-hoc path) — you MUST read `.claude/agents/rules/deck-design.md` AND
`.claude/agents/rules/slide-deck-rules.md` first**, in the same turn as the edit.
"Just reordering slides" / "just fixing typos" / "just adding a slide" all
count as edits. There is no exemption for hand-made decks: the dark-mode
contract, no-red-text contract, and light-on-light contrast contract apply
to every `.pptx` this project produces or modifies.

After the edit, audit the resulting deck against those subagents' contracts:

1. **Background is `_DARK_SLIDE_BG` (`#12151B`)** unless the user explicitly
   opted into light mode (`--light-mode`, `dark_mode=False`, GUI checkbox).
2. **No text run has `rgb=None` or `rgb=(0,0,0)`** (invisible on dark bg).
3. **No light fill contains light text** (luminance > 0.7 × 255 on both).
4. **No `#C0392B` red text runs** (banned in both modes).
5. **Top accent bar + cover left-band geometry** present on AutoPaperToPPT
   generated decks (hand-made decks are exempt from accent geometry but
   not from dark-mode / no-red / contrast contracts).

**For hand-made decks that don't follow the project's `_BRAND_*` constants**,
run `_apply_dark_mode(prs)` from `autopapertoppt.exporters.pptx` as a
post-pass — the `_swap_text_colors` safety net promotes None / pure-black
runs to `#E5E7EB` near-white, and `_set_slide_background` sets every slide
to `#12151B`.

The same "read-subagent-first" gate applies analogously to other
deliverable surfaces:

| Editing this surface | Read these subagent(s) FIRST |
|---|---|
| Any `.pptx` (generated or hand-made) | `deck-design`, `slide-deck-rules` |
| `autopapertoppt/exporters/pptx.py` visual code | `deck-design`, `slide-deck-rules` |
| `autopapertoppt/exporters/i18n.py` or any localised string | `slide-deck-rules`, `language-vocabulary-check` |
| Source plugins under `sources/` or `autopapertoppt/fetchers/` | `compliance-auditor` |
| Paper / thesis text in any locale | `paper_rule` |
| Hand-authoring `PaperSummary` from a PDF | `paper-summary-author`, `paper_rule` |
| Anything before commit | `dod-verify` (gate runner) |

When in doubt, read more subagents, not fewer. The subagent rules exist
*because* their violations have shipped before — skipping them is a known
failure mode, not a corner case.

## Dark-Mode Contract: Every Text Run Sets an Explicit Colour (HARD RULE)

Dark mode is the project's default pptx render path. The post-build
recolour pass swaps light-palette RGB values to their dark-palette
equivalents — but it can only swap colours it can read. **A text run
with `run.font.color.rgb = None` inherits the slide-master's theme
colour, renders as near-black on the dark slide background, and is
invisible.** Every text-adding helper in `autopapertoppt/exporters/pptx.py`
MUST therefore assign `run.font.color.rgb = _BRAND_*` (one of the four
palette constants) after creating or overwriting a run. Never leave the
colour at its default; never pass `colour=None` to `_add_textbox`;
never write `RGBColor(0, 0, 0)` — use `_BRAND_DARK` instead.

The `_swap_text_colors` pass in the dark-mode post-build now also
promotes any leftover `rgb is None` or `(0, 0, 0)` runs to `#E5E7EB`
near-white as a second layer of defence. The regression test
`tests/test_exporters.py::test_pptx_dark_mode_has_no_invisible_runs`
walks every run on every slide and fails if any non-empty run lacks an
explicit non-black colour. Full rule + the audit script + the
two-layer defence rationale live in `.claude/agents/rules/deck-design.md`
"Dark-mode contract".

**Mirror rule — light-on-light contrast.** Any new light-fill RGB
introduced in `pptx.py` (e.g. a callout / KPI / RQ-box background)
MUST also have an entry in `_LIGHT_TO_DARK_FILL`; otherwise the fill
stays near-white in dark mode while its text gets re-coloured to
near-white → invisible. Regression test
`test_pptx_dark_mode_no_light_text_on_light_fill` walks every shape
and fails when both fill and text luminance are > 0.7 of 255 in a
default-dark-mode render.

**No red text.** ``_BRAND_ACCENT`` (= ``#C0392B`` warm red) is BANNED
as a TEXT colour across both light and dark modes. Red text reads
as error / warning in slide conventions and pattern-matches strongly
to AI-generated KPI emphasis. The sanctioned text-emphasis colour is
**``_BRAND_HIGHLIGHT``** (teal-700, ``#0E7490``) — pair with
``run.font.bold = True``. Use ``_BRAND_GREY`` for caption / placeholder /
chrome text so headlines stay headlines. Variety rule: KPI value + RQ
question use teal; figure caption + figure-unavailable use grey — do
not collapse all four to the same colour. The dark-mode pass swaps
teal-700 → teal-400 (``#2DD4BF``) via ``_LIGHT_TO_DARK_TEXT``; the
audit script's ``_ACCEPTED_DARK_RUN_COLORS`` set knows about both.
Regression test ``test_pptx_no_red_text_runs`` walks every run on a
default-rendered deck and fails if any run uses ``#C0392B``. The red
constant stays in the palette in case a future non-text accent shape
(sparkline, status badge) wants it. Full rule + per-call-site palette
mapping in ``.claude/agents/rules/deck-design.md`` "No red text contract (HARD)".

## Paper Writing Rules (論文撰寫指引)

Thesis / journal / conference paper structure follows the user-supplied
**《論文撰寫指引》**, encoded in full as the `paper_rule` subagent. The
subagent is **multilingual** — every rule is given in English + 繁體中文
(authoritative source) and the canonical section names are tabulated for
all 14 project locales (en, zh-tw, zh-cn, ja, ko, es, fr, de, pt, it, ru,
ar, hi, vi). `paper_rule` auto-detects the user's working language and
responds in it; section numbers (1.1, 2.3, 4.5, …) stay universal for
unambiguous cross-reference. The seven canonical sections —
Abstract, Introduction (1.1 background / 1.2 motivation / 1.3 problem /
1.4 objectives / 1.5 contributions / 1.6 structure), Literature Review
(incl. 2.3 comparison table + 2.4 research gap), Methodology (incl.
3.1 architecture diagram / 3.5 evaluation metrics), Experiment &
Evaluation (incl. 4.4 result charts / 4.5 result analysis / fair
comparison), Conclusion (incl. 5.3 limitations / 5.4 future work),
References (last 5 years preferred; international journals > conferences;
English-dominant) — are the **default skeleton** for any thesis-style
deliverable in this project, regardless of deck locale.

Two places this binds the code:

1. **`PaperSummary` field authoring** (e.g. `paper-summary-author` subagent).
   Each rich-tier field maps to a thesis section: `pain_points` → 1.2,
   `contributions_detailed` (cap 4) → 1.5, `technique_table` → 2.3,
   `system_flow` → 3.1, `method_sections` → 3.2-3.4, `headline_metrics` +
   `evaluation_sections` → 4.4-4.5, `research_questions` + `rq_results` →
   1.3 + 4.5, `core_observation` → 5.1, `limitations` → 5.3, `future_work`
   → 5.4. Full mapping table in `paper_rule`.
2. **Thesis-style `.pptx` completeness audit.** A rich deck that drops the
   Literature Review, Experiment, or Conclusion section is incomplete —
   even if `slide-overflow-check` passes geometrically. Consult `paper_rule`
   before declaring a deck deliverable.

When the user is writing or reviewing their own paper text (not generating
slides), quote the relevant `paper_rule` clause directly (e.g.「依 1.4 應寫
3-5 點研究假設」, 「2.3 缺缺點欄位」).

## Where the detailed rules live

Subagent docs are organised into two subfolders under `.claude/agents/`.
Claude Code scans that directory **recursively**, so the subfolder path does
NOT change how an agent is invoked — identity comes only from each file's
`name:` frontmatter (names are unique across the tree). The split mirrors the
two kinds of subagent this project uses:

- **`rules/`** — read-only rule / reference subagents, consulted inline while
  you work.
- **`tasks/`** — task-running agents, dispatched to *do* work and able to run
  in the background / in parallel (the "multi-tasking" set).

```
.claude/agents/
├── rules/   code-quality-reviewer · compliance-auditor · slide-deck-rules ·
│            deck-design · env-vars · language-vocabulary-check · paper_rule
└── tasks/   dod-verify · paper-summary-author · post-author-audit ·
             slide-overflow-check
```

| Topic | Subagent | File (under `.claude/agents/`) |
|---|---|---|
| Design patterns, SOLID, performance, async, unit tests, full linter rule set | `code-quality-reviewer` | `rules/code-quality-reviewer.md` |
| Core-vs-source-plugin boundary, network safety, browser-automation hard rule, path safety, suppression conventions, bandit skip config | `compliance-auditor` | `rules/compliance-auditor.md` |
| pptx exporter geometry, rendering tiers, truncation caps, semantic shape names, i18n, LLM-as-agent vs Python pipeline | `slide-deck-rules` | `rules/slide-deck-rules.md` |
| pptx visual identity (typography per language, brand palette, accent geometry, master-slide expectations, "looks AI-generated" anti-patterns) | `deck-design` | `rules/deck-design.md` |
| Env vars + Python / `.venv` toolchain reference | `env-vars` | `rules/env-vars.md` |
| Language-correct vocabulary (no S-Chinese loan words in zh-tw, no T-Chinese in zh-cn, etc.) | `language-vocabulary-check` | `rules/language-vocabulary-check.md` |
| Academic paper writing rules (multilingual, all 14 locales) — Abstract / Introduction / Literature Review / Methodology / Experiment / Conclusion / References structure + PaperSummary-to-section mapping | `paper_rule` | `rules/paper_rule.md` |
| Definition-of-Done gate runner | `dod-verify` | `tasks/dod-verify.md` |
| LLM-as-agent thesis-style authoring (PDF → rich PaperSummary) | `paper-summary-author` | `tasks/paper-summary-author.md` |
| URL-fabrication / off-topic audits after authoring | `post-author-audit` | `tasks/post-author-audit.md` |
| Slide-overflow regression check | `slide-overflow-check` | `tasks/slide-overflow-check.md` |
