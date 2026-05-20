# Project Guidelines

> **Other agents:** `AGENTS.md` mirrors the cross-agent must-knows. Codex CLI,
> recent Aider, and several other tools auto-load `AGENTS.md`; keep them in
> sync when you change rules. Detailed rules now live in `.claude/agents/`
> as subagents (`code-quality-reviewer`, `compliance-auditor`,
> `slide-deck-rules`, `deck-design`, `env-vars`, `language-vocabulary-check`,
> plus the task-running agents `dod-verify`, `paper-summary-author`,
> `post-author-audit`, `slide-overflow-check`).

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
├── autopapertoppt/                  # main package
│   ├── core/                         # Paper / PaperSummary / Query models, dedup, ranking, pipeline
│   ├── fetchers/                     # HTTPS-only shared client, token-bucket rate limit, WebRunner browser
│   ├── exporters/                    # pptx (rich + lightweight), xlsx, bibtex, markdown, json + pptx_edit + i18n
│   ├── intelligence/                 # PDF fetch/extract + Anthropic summariser ([intelligence] extra)
│   ├── mcp/                          # FastMCP server registering all tools
│   ├── utils/                        # logging, path safety, async helpers
│   ├── cli.py                        # argparse CLI
│   └── __main__.py
├── sources/<name>/                   # per-source plugins (arxiv/, semantic_scholar/, openalex/, pubmed/,
│                                     # ieee/, acm/, scholar/, dblp/, crossref/, openaire/, springer/)
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

1. **Python pipeline** — IEEE / Scholar plugins call their own `webrunner_backend`
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
two-layer defence rationale live in `.claude/agents/deck-design.md`
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
to AI-generated KPI emphasis. Use **bold + ``_BRAND_DARK``** instead.
Regression test ``test_pptx_no_red_text_runs`` walks every run on a
default-rendered deck and fails if any run uses ``#C0392B``. The
constant stays in the palette in case a future non-text accent shape
(sparkline, status badge) wants it. Full rule in
``.claude/agents/deck-design.md`` "No red text contract (HARD)".

## Where the detailed rules live

| Topic | Subagent (in `.claude/agents/`) |
|---|---|
| Design patterns, SOLID, performance, async, unit tests, full linter rule set | `code-quality-reviewer` |
| Core-vs-source-plugin boundary, network safety, browser-automation hard rule, path safety, suppression conventions, bandit skip config | `compliance-auditor` |
| pptx exporter geometry, rendering tiers, truncation caps, semantic shape names, i18n, LLM-as-agent vs Python pipeline | `slide-deck-rules` |
| pptx visual identity (typography per language, brand palette, accent geometry, master-slide expectations, "looks AI-generated" anti-patterns) | `deck-design` |
| Env vars + Python / `.venv` toolchain reference | `env-vars` |
| Definition-of-Done gate runner | `dod-verify` |
| LLM-as-agent thesis-style authoring (PDF → rich PaperSummary) | `paper-summary-author` |
| URL-fabrication / off-topic audits after authoring | `post-author-audit` |
| Slide-overflow regression check | `slide-overflow-check` |
| Language-correct vocabulary (no S-Chinese loan words in zh-tw, no T-Chinese in zh-cn, etc.) | `language-vocabulary-check` |
