Guida utente ThesisAgents
============================

Assistente di ricerca articoli guidato da parole chiave. Recupera
risultati da arXiv, Semantic Scholar, OpenAlex, PubMed, ACM, IEEE
Xplore, DBLP, Crossref, OpenAIRE, Springer Nature e Google Scholar; ed
esporta come presentazione PowerPoint stile tesi, cartella di lavoro
Excel e file BibTeX. Tutto da una chiamata CLI o un'invocazione MCP.

.. contents:: Indice
   :depth: 2
   :local:

----

Per agenti IA che pilotano questo progetto
------------------------------------------

**Se sei un LLM (Claude Code, Cursor, Aider, Codex CLI, …) e leggi
questo per capire cosa fare — inizia qui.** Le stesse regole sono
fissate in ``AGENTS.md`` (specchio cross-agent) e ``CLAUDE.md``
(riferimento canonico) nella radice del repo; leggile prima di
cambiamenti non banali.

**Il deliverable di default è un ``.pptx`` arricchito stile tesi per
articolo**, non il deck leggero solo-abstract che la CLI produce di
default. Il leggero è artefatto intermedio — il tuo lavoro è elevarlo.

Albero decisionale
^^^^^^^^^^^^^^^^^^

1. ``ANTHROPIC_API_KEY`` impostata? → esegui la CLI; auto-arricchimento
   via API Anthropic.
2. Senza chiave, LLM pilota → **scrivi il riassunto arricchito tu**.
   Leggi ogni PDF, redigi a mano ``PaperSummary`` con campi rich-tier,
   deposita ``scripts/regen_<query>.py``, esegui. **Non dire
   all'utente di impostare la API key** — sei tu l'LLM.
3. Niente LLM (CI / cron) → leggero accettabile.

Flusso MCP in 6 passi
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   1. (facoltativo) list_sources()
   2. search(keywords, sources, top_tier_only=true, ...)
   3. (facoltativo) download_pdfs(papers, out_dir="./exports/...")
   4. fetch_pdf_text(pdf_url=paper.pdf_url)           # per articolo
   5. (leggi ogni PDF e produci dict di riassunto strutturato)
   6. export(papers=[{...paper, "summary": {...}}], language="it", ...)

Gli 11 strumenti MCP completi: :doc:`/mcp`.

Obbligatorio: verifica URL / DOI prima della consegna
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

I percorsi URL degli editori **non si possono indovinare** — AAAI usa
ID numerici (``v40i5.37389``), IEEE usa ``arnumber`` opaco, ACM usa
DOI opachi. Quando scrivi un ``Paper`` a mano, **copia ``url`` /
``doi`` / ``arxiv_id`` letteralmente dall'xlsx prodotto da questa
ricerca** — mai a memoria, mai costruito dal titolo.

L'xlsx viene scritto in ``exports/<run>/<slug>-<timestamp>.xlsx`` con
colonna 7 = DOI, colonna 8 = URL. Audita il tuo script regen al
termine:

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

Divieti
^^^^^^^

* Non dire all'utente «imposta ``ANTHROPIC_API_KEY``» — sei tu l'LLM.
* Non trattare ``.pptx`` leggero come deliverable.
* Non fermarti quando ``download_pdfs`` finisce.
* Non inventare numeri, RQ, contributi, limiti.
* Non fabbricare URL / DOI / ID arXiv.
* Non lasciare download non pertinenti nella directory di esecuzione.
  La ricerca per parole chiave può portare articoli fuori tema (una
  query «Claude code» ha portato un articolo sul decodificatore
  Viterbi). Elimina ``pdfs/<key>.pdf`` e ``<key>.pptx`` leggeri fuori
  tema; conserva l'xlsx / bib aggregato come registrazione onesta.
  Procedura completa in ``CLAUDE.md`` «Pruning irrelevant downloads».
* Non menzionare «Claude», «Claude Code», «AI-generated», «GPT»,
  «Copilot» o qualsiasi nome di strumento/modello IA in commit, PR,
  codice o documentazione.

Esempi: ``scripts/regen_llm_security_batch.py`` (en, 8 articoli) e
``scripts/regen_llm_security_batch_zh_tw.py`` (zh-tw).

----

Installazione
-------------

Richiede Python **3.12+**.

.. code-block:: bash

   git clone <repo-url>
   cd ThesisAgents
   python -m venv .venv
   .venv\Scripts\Activate.ps1            # Windows PowerShell
   # source .venv/bin/activate           # Linux / macOS
   pip install -e .[dev]

Extras opzionali: ``[mcp]``, ``[intelligence]``, ``[web]``, ``[dev]``.

----

Avvio rapido
------------

.. code-block:: bash

   # Cercare arXiv → deck + workbook + BibTeX
   thesisagents --query "diffusion models" --source arxiv --max 10 \
                  --out ./exports/

   # Un articolo per URL → deck + BibTeX
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --filename-stem attention --out ./exports/

   # Renderizza il deck in italiano
   thesisagents --paper 1706.03762 --lang it --out ./exports/

   # Arricchimento via pipeline Python (richiede chiave Anthropic)
   export ANTHROPIC_API_KEY=sk-ant-...
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --enrich --lang it --out ./exports/

Tabella completa dei flag CLI: :doc:`/cli`.

----

Dove cercare oltre
------------------

* Flag CLI e variabili d'ambiente: :doc:`/cli`
* 11 strumenti del server MCP: :doc:`/mcp`
* Toolkit di editing PPTX: :doc:`/pptx_editing`
* Il file ``readmes/README.it.md`` nella radice del repo contiene l'elenco
  completo delle funzionalità.
* Il riferimento tecnico approfondito (architettura dei plugin,
  policy di sicurezza, Definition of Done, regole SonarQube, …) è
  consolidato nella guida inglese: :doc:`/en/index`.
