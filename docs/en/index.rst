ThesisAgents User Guide
==========================

A keyword-driven paper search assistant that fetches results from
arXiv (and pluggable other sources), normalises them into one record
shape, and exports the deduplicated, ranked set as a PowerPoint deck,
a Markdown summary, a BibTeX file, and a JSON dump — from one CLI
invocation or one MCP tool call.

.. contents:: Table of contents
   :depth: 2
   :local:

----

For AI agents driving this project
----------------------------------

**If you are an LLM (Claude Code, Cursor, Aider, Codex CLI, …) reading
this guide to figure out what to do — start here.** The same rules are
pinned in ``AGENTS.md`` (cross-agent mirror) and ``CLAUDE.md``
(canonical reference) at the repo root; read those before making
non-trivial changes.

**The deliverable is a thesis-style rich PPT per paper, not the
lightweight abstract-only deck the CLI emits by default.** The
lightweight emit is an intermediate artefact — your job is to upgrade
it.

Decision tree
^^^^^^^^^^^^^

1. ``ANTHROPIC_API_KEY`` set? → just run the CLI; it auto-enriches.
2. No key, LLM driving → **you produce the rich summary yourself**.
   Read each PDF, hand-author a ``PaperSummary`` with rich-tier
   fields, drop a ``scripts/regen_<query>.py``, run it. Do NOT tell
   the user to set the API key — you ARE the LLM that would have
   written the summary.
3. No LLM in the loop (CI / cron / unattended) → lightweight is
   acceptable.

6-step MCP workflow
^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   1. (optional) list_sources()                          # which plugins are enabled
   2. search(keywords, sources, top_tier_only=true, ...)
   3. (optional) download_pdfs(papers, out_dir="./exports/...")
   4. fetch_pdf_text(pdf_url=paper.pdf_url)              # per paper
   5. (you read each PDF and produce a structured summary dict)
   6. export(papers=[{..., "summary": {...}}], language="zh-tw", ...)

Twelve MCP tools total; full reference at :doc:`/mcp`.

Mandatory: URL / DOI verification
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Publisher URL paths **cannot be guessed**. AAAI uses numeric IDs
(``v40i5.37389``), IEEE uses an opaque ``arnumber``, ACM uses opaque
DOIs. When you hand-author a ``Paper``, copy ``url`` / ``doi`` /
``arxiv_id`` **verbatim from the search xlsx** — never from memory,
never constructed from the title.

The xlsx is written to ``exports/<run>/<slug>-<timestamp>.xlsx`` with
column 7 = DOI, column 8 = URL. Audit your regen script after running:

.. code-block:: python

   from openpyxl import load_workbook
   from scripts.regen_<run> import ALL_PAPERS
   real = {sh.cell(row=r, column=2).value: sh.cell(row=r, column=8).value
           for sh in [load_workbook("exports/<run>/<slug>-<ts>.xlsx")["Papers"]]
           for r in range(2, sh.max_row + 1)}
   for p in ALL_PAPERS:
       actual = next((u for t, u in real.items() if p.title[:30] in (t or "")), None)
       if actual and not (p.url == actual
                          or p.url.split("v")[0] == actual.split("v")[0]):
           print(f"! {p.bibtex_key()} authored {p.url} vs real {actual}")

Don'ts
^^^^^^

* Don't tell the user "set ``ANTHROPIC_API_KEY`` for a rich deck" —
  you are the LLM.
* Don't treat the lightweight ``.pptx`` as the deliverable.
* Don't stop after ``download_pdfs`` — that's the start of
  rich-authoring.
* Don't invent numbers, RQs, contributions, or limitations.
* Don't fabricate URLs / DOIs / arXiv IDs.
* Don't leave irrelevant downloads in the run directory. Keyword
  search can pull in off-topic papers (a "Claude code" query
  returned a Viterbi-decoder paper). Delete the off-topic
  ``pdfs/<key>.pdf`` and lightweight ``<key>.pptx``; keep the
  aggregate xlsx / bib as the honest record. Full procedure in
  ``CLAUDE.md`` "Pruning irrelevant downloads".
* Don't mention "Claude", "Claude Code", "AI-generated", "GPT",
  "Copilot", or any AI tool / model name in commits, PRs, code
  comments, or documentation.

Worked example: ``scripts/regen_llm_security_batch.py`` (en) and
``scripts/regen_llm_security_batch_zh_tw.py`` (zh-tw) ship 8
hand-authored rich summaries built exactly this way.

----

Installation
------------

ThesisAgents targets Python **3.12+** (developed against 3.14) on
Windows, macOS, and Linux. A project-local virtualenv is recommended:

.. code-block:: bash

   git clone <repo-url>
   cd ThesisAgents
   python -m venv .venv
   .venv\Scripts\Activate.ps1            # Windows PowerShell
   # source .venv/bin/activate           # Linux / macOS

   pip install -e .[dev]

The ``dev`` extra pulls in ``pytest``, ``pytest-asyncio``,
``pytest-httpx``, ``ruff``, ``bandit``, and the ``mcp`` SDK. If you
only need the MCP server, install the lighter ``[mcp]`` extra
instead.

Optional dependency groups
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Extra
     - What it unlocks
   * - ``[mcp]``
     - The ``mcp`` SDK only. Use this for production installs where
       you want the ``thesisagents-mcp`` console script but not the
       test toolchain.
   * - ``[intelligence]``
     - ``pypdf`` + ``anthropic``. Needed for the Python ``--enrich``
       pipeline (PDF text extraction + Anthropic API summary). Not
       needed for the LLM-as-agent flow over MCP — the LLM is the
       agent.
   * - ``[web]``
     - ``fastapi`` + ``uvicorn`` + ``streamlit`` — reserved for a future
       web UI. The CLI and MCP server do not need this.
   * - ``[dev]``
     - The full developer toolchain: pytest, asyncio + httpx test
       plugins, ruff, bandit, the MCP SDK, and the intelligence deps so
       every test can run.

----

CLI
---

``python -m thesisagents`` (also installed as ``thesisagents``) is
the canonical entrypoint. It has two mutually exclusive modes:

Search mode
^^^^^^^^^^^

.. code-block:: bash

   # Default 25 results, default exports (pptx, xlsx, bib)
   thesisagents --query "diffusion models" --source arxiv

   # 10 results, every export format, custom dir
   thesisagents --query "transformer attention" --source arxiv \
                --max 10 --export pptx,xlsx,md,bib,json,ris,csv,csl \
                --out ./exports/

   # Restrict to recent work
   thesisagents --query "graph neural networks drug discovery" \
                --year-from 2022 --year-to 2025 \
                --max 15 --out ./exports/

Single-paper mode
^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # arXiv ID — default exports for single paper are pptx + bib
   thesisagents --paper 1706.03762 --out ./exports/

   # arXiv URL
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                --filename-stem attention --out ./exports/

   # DOI (resolved via Semantic Scholar)
   thesisagents --paper "10.1145/3411764.3445005" --out ./exports/

   # PubMed ID / URL
   thesisagents --paper "https://pubmed.ncbi.nlm.nih.gov/34567890/" \
                --out ./exports/

   # IEEE document URL (default-on via visible Chrome; opt out with
   # THESISAGENTS_DISABLE_IEEE_SCRAPING=1 if you have no Chrome binary)
   thesisagents --paper "https://ieeexplore.ieee.org/document/10965643" \
                --out ./exports/

Available source plugins
^^^^^^^^^^^^^^^^^^^^^^^^

The default mix used when ``--source`` is omitted is every plugin that
needs no paid API key plus ``ieee`` + ``scholar`` (both default-on via
visible Chrome): ``arxiv``, ``semantic_scholar``, ``openalex``,
``pubmed``, ``acm``, ``dblp``, ``crossref``, ``openaire``,
``europepmc``, ``doaj``, ``hal``, ``ieee``, ``scholar`` (15 plugins
total). Two more join when their env var is set (``springer`` and
``core``):

.. list-table::
   :header-rows: 1
   :widths: 18 30 52

   * - Plugin
     - Env var
     - Notes
   * - ``ieee``
     - default-on; ``THESISAGENTS_IEEE_API_KEY`` switches to the
       official Xplore API; ``THESISAGENTS_DISABLE_IEEE_SCRAPING=1``
       opts out entirely
     - Without the API key, the search + document fetch run through
       visible Chrome (selenium). The httpx fallback is a CI / no-Chrome
       safety net.
   * - ``springer``
     - ``THESISAGENTS_SPRINGER_API_KEY``
     - Free key from https://dev.springernature.com/. Covers Nature,
       Scientific Reports, Lecture Notes in CS, all Springer journals.
       The plugin raises ``ConfigError`` at construction without a key,
       which the pipeline silently skips.
   * - ``core``
     - ``THESISAGENTS_CORE_API_KEY``
     - Free key from https://core.ac.uk/services/api. The largest
       open-access aggregator (250M+ works); the same key also drives the
       OA resolver's CORE lookup. Soft-skipped (``ConfigError``) without
       a key, like ``springer``.
   * - ``scholar``
     - default-on; ``THESISAGENTS_DISABLE_SCHOLAR_SCRAPING=1`` opts out
     - SERP fetch runs in visible Chrome. Google ToS forbids automation;
       opt out to avoid captcha / IP-block risk.

Set ``THESISAGENTS_CHROME_PROFILE_DIR`` to a persistent path so
VPN / institutional SSO / Google sign-in survive across runs.

The search pipeline can optionally restrict results to a curated
top-tier venue whitelist (flagship CS conferences + arXiv pass-through);
pass ``--top-tier-only`` to enable it (off by default).

Localised deck + LLM enrichment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Slide template strings in Traditional Chinese
   thesisagents --paper 1706.03762 --lang zh-tw --out ./exports/

   # Python pipeline enrichment (PDF + Anthropic API → thesis-style deck)
   export ANTHROPIC_API_KEY=sk-ant-...
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                --enrich --lang zh-tw --out ./exports/

Full flag table: :doc:`/cli`.

----

Output artefacts
----------------

Each export writes one file into ``--out``. Filenames default to
``{first-32-chars-of-query}-{YYYYMMDD-HHMMSS}.{ext}``; pass
``--filename-stem`` to fix the stem. Defaults are mode-specific:

* ``--query`` → ``pptx`` + ``xlsx`` + ``bib``
* ``--paper`` → ``pptx`` + ``bib`` (a one-row Excel sheet is busy work)

.. code-block:: text

   exports/
   ├── attention.pptx     # 16:9 widescreen deck (see PPTX layout below)
   ├── attention.xlsx     # Papers sheet + Query provenance sheet
   ├── attention.bib      # collision-free citation keys, LaTeX-safe
   ├── attention.md       # full source / title / abstract list (opt-in)
   └── attention.json     # raw payload (opt-in)

The ``.xlsx`` Papers sheet carries two adjacent columns that look
similar but mean different things:

* **Source** (column 5) — the real publication venue, e.g.
  ``IEEE Access``, ``NDSS 2026``, ``Nature Machine Intelligence``.
* **Indexed via** (column 6) — the fetcher plugin that returned the
  metadata, e.g. ``openalex``, ``crossref``, ``arxiv``. This matters
  when one paper is discoverable through several routes — e.g. a
  Nature paper indexed by OpenAlex will show ``Nature`` under Source
  and ``openalex`` under Indexed via.

PPTX layout
^^^^^^^^^^^

16:9 widescreen, page-numbered. Three rendering tiers pick themselves
based on how much information is attached to each paper:

* **Lightweight** — only ``paper.abstract`` available. Cover + agenda
  + per paper (section divider + overview + sentence-bucketed
  Background / Approach / Findings) + references.
* **Enriched-flat** — ``Paper.summary`` has the flat tier populated
  (``motivation`` / ``contributions`` / ``method`` / ``results`` /
  ``limitations`` / ``takeaways``). One slide per non-empty section.
* **Thesis-style** — ``Paper.summary`` has rich-tier fields
  (``pain_points`` quadrant, ``research_question`` callout,
  ``contributions_detailed`` + ``headline_metrics``, technique table,
  literature positioning table, system overview, method details,
  evaluation method, research questions, per-RQ result tables,
  contribution summary, core observation, limitations & future work,
  Q&A, references). 20+ slides per paper.

All template strings (Agenda / References / Paper N of M / footer)
flow through ``thesisagents.exporters.i18n`` and respect ``--lang``.
Supported languages: ``en`` (default), ``zh-tw``, ``zh-cn``, ``ja``,
``es``, ``fr``, ``de``, ``ko``, ``pt``, ``ru``, ``it``, ``vi``, ``hi``,
``id`` — 14 in total. Anything outside that set falls back silently
to ``en``.

Every text box on every slide carries a semantic ``name`` (``title``,
``meta``, ``body``, ``subhead``, ``footer``, ``page_number``, ``kpi``,
``rq_box``, ``rq_question``, ``figure``, ``accent_top``,
``accent_left``) so the editing tools can target shapes without
depending on visual position. See :doc:`/pptx_editing`.

Designed-deck visual identity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The exporter applies three non-invasive post-build passes so a deck
doesn't look like generic ``add_slide()`` output:

* **Per-language typography** — every text run gets both an
  ``<a:latin>`` and ``<a:ea>`` typeface override. Latin defaults to
  Inter; East-Asian to Microsoft JhengHei UI (zh-tw), YaHei UI
  (zh-cn), Yu Gothic UI (ja), Malgun Gothic (ko); Nirmala UI handles
  Devanagari (hi). Setting only the Latin slot leaves CJK glyphs in
  PowerPoint's default East-Asian font — both slots matter.
* **Accent geometry** — every content slide gets a thin navy top bar
  (``accent_top``, full width); the cover slide also carries a left
  vertical band (``accent_left``).
* **Academic-style tables** — the default PowerPoint heavy black grid
  is stripped; the header row gets a solid navy fill + 1.5pt navy
  bottom rule; data rows alternate light blue / white with a 0.5pt
  soft inter-row divider; vertical alignment is middle; the first
  column is bold so row labels read as headers.

Dark mode
^^^^^^^^^

The **light navy-band deck is the default** render path: white
slides, a full-width navy header band with a white title, and a
full-bleed navy cover panel. Opt **in** to dark mode per render with
``--dark-mode`` on the CLI, the **Dark mode** checkbox on the GUI's
Deck tab, or ``ExportOptions(dark_mode=True)`` in Python (over MCP,
pass ``dark_mode: true`` to the ``export`` tool). The dark post-build
pass swaps to a dark deck (slide bg ``#12151B``, body text
``#E5E7EB``, brighter teal accent ``#2DD4BF``) and lightens the navy
band / cover / table fills — designed for OLED projectors and
low-light venues.

Red is **banned as a text colour** in both modes. The sanctioned
emphasis colour is teal ``#0E7490`` (bold + teal for KPI values and
RQ question callouts); grey is for captions / placeholders. Regression
tests in ``tests/test_exporters.py`` pin every contract — no
``rgb=None`` runs, no near-white text on near-white callouts, no
``#C0392B`` text runs.

zh-tw / zh-cn vocabulary guard
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A 244-pattern regex catalogue in
``tests/test_i18n.py::test_zh_tw_files_use_traditional_chinese_vocabulary``
catches Simplified-Chinese loan words rendered in Traditional hanzi
— e.g. ``內存`` (should be ``記憶體``), ``魯棒性`` (``穩健性``),
``軟件`` (``軟體``), ``緩存`` (``快取``). The same guard runs in
reverse for zh-cn strings. Full rule + the regex catalogue live in
``.claude/agents/language-vocabulary-check.md``.

----

MCP server
----------

ThesisAgents ships an MCP server exposing **twelve tools** — source
discovery (``list_sources``), search, single-paper fetch, single-PDF
text extraction (``fetch_pdf_text``), batch PDF download
(``download_pdfs``), export, and five PPTX edit operations. Any
MCP-aware LLM client (Claude Code, Claude Desktop, Cursor, …) can
drive the whole workflow.

Configure your MCP client (Claude Code shown):

.. code-block:: powershell

   claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp

Or hand-edit your settings file:

.. code-block:: json

   {
     "mcpServers": {
       "thesisagents": {
         "command": ".venv\\Scripts\\python.exe",
         "args": ["-m", "thesisagents.mcp"]
       }
     }
   }

Tools at a glance:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Tool
     - Purpose
   * - ``list_sources``
     - Enumerate every plugin and report whether each is enabled in the
       current process. Call this once before ``search`` so the agent
       only passes sources that will actually run.
   * - ``search``
     - Keywords → list of papers (same shape as ``Paper.to_dict()``).
       Accepts ``top_tier_only`` (default ``True``) and
       ``min_citations``; defaults to the full no-API-key source mix
       when ``sources`` is omitted.
   * - ``fetch_paper``
     - arXiv / DOI / PMID / IEEE identifier → single paper.
   * - ``fetch_pdf_text``
     - Download one PDF, return extracted body text. **The MCP
       path to "I read the paper".**
   * - ``download_pdfs``
     - Batch-download a papers list's PDFs into ``{out_dir}/pdfs/``.
       Returns per-paper results keyed by BibTeX key.
   * - ``export``
     - Papers list + formats → writes ``.pptx/.xlsx/.md/.bib/.json/.ris/.csv/.csl.json``.
       Accepts a ``summary`` field per paper that can carry the
       full thesis-style schema; accepts ``language`` for i18n,
       ``max_slides_per_paper`` (default 25; pass ``0`` for unlimited),
       and ``dark_mode`` (default ``true`` — dark deck; pass ``false``
       for the printable light variant).
   * - ``pptx_inspect``
     - Read slide / shape structure of an existing deck.
   * - ``pptx_review``
     - Audit a deck in one call — overflow + colour contracts +
       ``paper_rule`` section completeness. Auto-detects the deck
       language; also the CLI ``python -m thesisagents review``.
   * - ``pptx_update_slide``
     - Replace ``title`` / ``body`` / ``meta`` (by shape name) or
       arbitrary shapes by index.
   * - ``pptx_delete_slide``
     - Remove a slide and its part relationship.
   * - ``pptx_reorder_slides``
     - Permute slides via ``sldIdLst``.
   * - ``pptx_add_slide``
     - Append or insert a new title / body / meta slide.

LLM-as-agent enrichment flow (no Anthropic API key needed):

1. *(Optional)* ``list_sources()`` to discover which plugins are
   enabled in this process.
2. Either ``search(keywords, sources, top_tier_only, ...)`` for a
   multi-paper query, or ``fetch_paper(identifier)`` for one paper.
3. *(Optional)* ``download_pdfs(papers, out_dir)`` to persist every
   paper's PDF on disk in one batch.
4. ``fetch_pdf_text(paper.pdf_url)`` per paper for the body text.
5. The LLM reads the text and produces a structured ``summary`` dict
   in-context.
6. ``export(papers=[{..., "summary": {...}}], language="zh-tw", ...)``.

Full reference: :doc:`/mcp`.

----

Editing a generated deck
------------------------

Once a deck is generated, the ``pptx_*`` tools (or the
``thesisagents.exporters.pptx_edit`` Python module) let you iterate
on it without re-running the search:

.. code-block:: python

   from thesisagents.exporters import pptx_edit

   pptx_edit.update_slide(
       "exports/attention.pptx", slide_index=1,
       title="Attention Is All You Need (Vaswani et al., 2017)",
       body="The Transformer dispenses with recurrence and convolutions...",
   )

   pptx_edit.add_slide(
       "exports/attention.pptx",
       title="Conclusion",
       body="We covered transformers and follow-on work.",
   )

   pptx_edit.reorder_slides("exports/attention.pptx", [0, 2, 1])

Every helper saves in place by default; pass ``out_path=...`` to
write a copy and leave the original alone. Full reference:
:doc:`/pptx_editing`.

----

Packaging as a standalone executable
------------------------------------

To ship a binary that runs on machines without Python installed:

* :doc:`/packaging-pyinstaller` — fast build, larger binary, 2–4 s
  startup. Best for iteration.
* :doc:`/packaging-nuitka` — slow build, smaller binary, sub-second
  startup, some bytecode protection. Best when end users run the
  binary many times.

Both docs cover the project-specific gotcha — the dynamic source
plugins under ``sources/<name>/`` — and provide commands for both
the CLI and MCP server entry points.

----

Architecture
------------

::

   ThesisAgents/
   ├── thesisagents/                 # main package
   │   ├── core/                     # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
   │   ├── fetchers/                 # HTTPS-only http client, token bucket, Fetcher base
   │   ├── exporters/                # pptx (thesis-style + lightweight), xlsx,
   │   │                             #   bibtex, markdown, json + pptx_edit + i18n
   │   ├── intelligence/             # PDF fetch + Anthropic summariser ([intelligence] extra)
   │   ├── mcp/                      # FastMCP server registering 12 tools
   │   ├── utils/                    # logging, path safety
   │   ├── cli.py                    # argparse CLI
   │   └── __main__.py               # `python -m thesisagents`
   ├── sources/                      # per-source plugins (arxiv, semantic_scholar,
   │                                 #   openalex, pubmed, acm, ieee, scholar,
   │                                 #   dblp, crossref, openaire, springer, europepmc, doaj, hal, core)
   ├── tests/                        # pytest suite + recorded fixtures, no live HTTP
   ├── docs/                         # this Sphinx tree (en + zh-tw + zh-cn)
   ├── scripts/                      # one-off regen / fixture-record scripts
   └── pyproject.toml                # metadata + ruff / bandit + optional extras

Core vs source plugins
^^^^^^^^^^^^^^^^^^^^^^

The line between ``thesisagents/`` (core) and ``sources/<name>/``
(plugin) is **dependency surface and failure isolation**, not "any
source-related code goes in a plugin":

* **Core** runs on the default dep set
  (``httpx``, ``pydantic``, ``defusedxml``, ``python-pptx``,
  ``openpyxl``, ``bibtexparser``, ``beautifulsoup4``, ``lxml``,
  ``markdown-it-py``) and covers the everyday workflow that should
  work for every user.
* **Plugin** is anything that needs a heavy / optional runtime
  dependency (``selenium`` for Scholar JS pages, vendor SDKs for
  IEEE / ACM, …) or independent release cadence.

Two enrichment paths
^^^^^^^^^^^^^^^^^^^^

* **LLM-as-agent (no API key)** — preferred when an MCP-aware LLM is
  driving the workflow. ``fetch_paper`` + ``fetch_pdf_text`` give it
  metadata + body text; the LLM writes the structured ``summary`` in
  its own context; ``export`` writes the artefacts.
* **Python pipeline (``--enrich`` CLI flag)** — for unattended
  automation. Requires ``ANTHROPIC_API_KEY`` and the
  ``[intelligence]`` extra. Default model ``claude-opus-4-7``;
  override via ``--llm-model`` or ``THESISAGENTS_LLM_MODEL``.

Network safety
^^^^^^^^^^^^^^

All outbound HTTP goes through
``thesisagents.fetchers.http.get_client(source)`` which returns a
per-source ``httpx.AsyncClient`` wrapped in an HTTPS-only transport.
Plain HTTP requests are refused — even after a redirect. Each source
declares a ``RateLimit`` policy enforced by a token bucket; arXiv
defaults to **1 request per 3 seconds with 0.5s jitter** to match
their published soft limit.

----

Development workflow
--------------------

Definition of Done
^^^^^^^^^^^^^^^^^^

Every change must pass three gates before commit (see ``CLAUDE.md``):

.. code-block:: bash

   .venv\Scripts\python.exe -m pytest tests/
   .venv\Scripts\python.exe -m ruff check .
   .venv\Scripts\python.exe -m bandit -c pyproject.toml -r thesisagents/ sources/

The ``-c`` flag on bandit is **required** — without it bandit ignores
the project skip config and the run will be noisy.

Tests
^^^^^

Tests mirror the package layout: each production module
``thesisagents/<area>/<feature>.py`` has a paired
``tests/test_<feature>.py``. Source plugins live under
``tests/sources/<name>/``.

Tests are **hermetic** — every fetcher test uses a recorded fixture
loaded through a monkeypatched HTTP transport. Recording new
fixtures is a separate manual step
(``scripts/record_fixture.py``) and the recorded file is committed.

Run the whole suite:

.. code-block:: bash

   .venv\Scripts\python.exe -m pytest tests/

89 tests currently pass in ~2 seconds.

Linting + security
^^^^^^^^^^^^^^^^^^

Ruff catches most style issues automatically. The project enforces
SonarQube / Codacy / pylint default rules (complexity ≤ 15,
function length ≤ 75 lines, file length ≤ 1000 lines, no magic
numbers, no bare ``except``, no mutable default args). Bandit scans
for security-relevant patterns (``pickle.load``, ``yaml.load``
without SafeLoader, MD5 / SHA-1 for security, ``shell=True``,
plain-HTTP egress).

----

Troubleshooting
---------------

``error: refusing non-HTTPS request``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A source plugin or test pointed the HTTP client at an ``http://``
URL. Fix the URL — the project never bypasses HTTPS-only egress.

``error: could not classify identifier``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``--paper`` argument was not recognised as an arXiv ID, arXiv
URL, or DOI. Accepted forms:

* ``2401.08741``, ``2401.08741v2``, ``arXiv:2401.08741``
* ``https://arxiv.org/abs/2401.08741`` (with or without ``v<N>`` /
  ``.pdf``)
* ``cs.LG/0001001`` (legacy)
* ``10.1234/example``, ``doi:10.1234/example``,
  ``https://doi.org/10.1234/example``

``error: no source plugin available yet for doi identifiers``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

DOI identifiers parse correctly but the resolver is not yet
implemented. Track the Semantic Scholar / Crossref plugin work, or
use the paper's arXiv mirror if it exists.

``arXiv rate-limit hits``
^^^^^^^^^^^^^^^^^^^^^^^^^

The bundled token bucket already paces requests at 1 / 3s. If
you're still seeing 429s, you may be running multiple ThesisAgents
processes in parallel against the same arXiv endpoint — coordinate
through a single process or lower ``--max``.

----

License + attribution
---------------------

The codebase is **MIT-style**; see ``LICENSE``.

The arXiv API is used under arXiv's `API terms of use
<https://info.arxiv.org/help/api/tou.html>`_. The bundled fetcher
already enforces the 1 request / 3 second soft limit via its token
bucket; do not remove that rate limit when adding new endpoints.
