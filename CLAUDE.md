# Project Guidelines

> **Other agents:** `AGENTS.md` mirrors the cross-agent must-knows. Codex CLI,
> recent Aider, and several other tools auto-load `AGENTS.md`; keep them in
> sync when you change rules. Detailed rules now live in `.claude/agents/`
> as subagents (`code-quality-reviewer`, `compliance-auditor`,
> `slide-deck-rules`, `env-vars`, plus the task-running agents `dod-verify`,
> `paper-summary-author`, `post-author-audit`, `slide-overflow-check`).

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

## Where the detailed rules live

| Topic | Subagent (in `.claude/agents/`) |
|---|---|
| Design patterns, SOLID, performance, async, unit tests, full linter rule set | `code-quality-reviewer` |
| Core-vs-source-plugin boundary, network safety, browser-automation hard rule, path safety, suppression conventions, bandit skip config | `compliance-auditor` |
| pptx exporter geometry, rendering tiers, truncation caps, semantic shape names, i18n, LLM-as-agent vs Python pipeline | `slide-deck-rules` |
| Env vars + Python / `.venv` toolchain reference | `env-vars` |
| Definition-of-Done gate runner | `dod-verify` |
| LLM-as-agent thesis-style authoring (PDF → rich PaperSummary) | `paper-summary-author` |
| URL-fabrication / off-topic audits after authoring | `post-author-audit` |
| Slide-overflow regression check | `slide-overflow-check` |
