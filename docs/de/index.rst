AutoPaperToPPT Benutzerhandbuch
================================

Stichwortgesteuerter Paper-Such-Assistent. Ruft Ergebnisse von arXiv,
Semantic Scholar, OpenAlex, PubMed, ACM, IEEE Xplore, DBLP, Crossref,
OpenAIRE, Springer Nature und Google Scholar ab; exportiert als
PowerPoint-Präsentation im Thesis-Stil, Excel-Arbeitsmappe und
BibTeX-Datei. Alles aus einem CLI-Aufruf oder einem MCP-Tool-Aufruf.

.. contents:: Inhalt
   :depth: 2
   :local:

----

Für KI-Agenten, die dieses Projekt steuern
------------------------------------------

**Wenn Sie ein LLM (Claude Code, Cursor, Aider, Codex CLI, …) sind und
das hier lesen, um zu verstehen, was zu tun ist — fangen Sie hier an.**
Die gleichen Regeln sind in ``AGENTS.md`` (agentenübergreifender
Spiegel) und ``CLAUDE.md`` (kanonische Referenz) im Repo-Root fixiert;
lesen Sie diese vor nicht-trivialen Änderungen.

**Das Standard-Ergebnis ist ein angereichertes ``.pptx`` im Thesis-Stil
pro Paper**, nicht das auf das Abstract beschränkte Light-Deck, das die
CLI standardmäßig erzeugt. Light ist ein Zwischenartefakt — Ihre
Aufgabe ist es, ihn aufzuwerten.

Entscheidungsbaum
^^^^^^^^^^^^^^^^^

1. ``ANTHROPIC_API_KEY`` gesetzt? → CLI ausführen; auto-Anreicherung
   über Anthropic-API.
2. Kein Schlüssel, LLM steuert → **angereicherte Zusammenfassung
   selbst verfassen**. Jedes PDF lesen, ``PaperSummary`` mit
   Rich-Tier-Feldern von Hand schreiben, ``scripts/regen_<query>.py``
   ablegen, ausführen. **Den Nutzer nicht bitten, den API-Schlüssel zu
   setzen** — Sie sind das LLM.
3. Kein LLM (CI / cron) → Light akzeptabel.

MCP-Workflow in 6 Schritten
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   1. (optional) list_sources()
   2. search(keywords, sources, top_tier_only=true, ...)
   3. (optional) download_pdfs(papers, out_dir="./exports/...")
   4. fetch_pdf_text(pdf_url=paper.pdf_url)           # pro Paper
   5. (Sie lesen jedes PDF und erzeugen strukturierten Summary-Dict)
   6. export(papers=[{...paper, "summary": {...}}], language="de", ...)

Alle 11 MCP-Tools: :doc:`/mcp`.

Pflicht: URL / DOI-Verifikation vor Auslieferung
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Verlags-URL-Pfade **lassen sich nicht raten** — AAAI nutzt numerische
IDs (``v40i5.37389``), IEEE nutzt opake ``arnumber``, ACM nutzt opake
DOIs. Beim handschriftlichen Erstellen eines ``Paper``\ , ``url`` /
``doi`` / ``arxiv_id`` **wortgetreu aus dem xlsx kopieren, das diese
Suche erzeugt hat** — niemals aus dem Gedächtnis, niemals aus dem
Titel konstruiert.

Das xlsx wird unter ``exports/<run>/<slug>-<timestamp>.xlsx`` mit
Spalte 7 = DOI, Spalte 8 = URL geschrieben. Auditieren Sie Ihr
Regen-Script am Ende:

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

Verbote
^^^^^^^

* Nicht dem Nutzer sagen „setze ``ANTHROPIC_API_KEY``" — Sie sind das
  LLM.
* Light ``.pptx`` nicht als Ergebnis behandeln.
* Nicht stoppen, wenn ``download_pdfs`` fertig ist.
* Keine Zahlen, RQs, Beiträge oder Einschränkungen erfinden.
* Keine URLs / DOIs / arXiv-IDs fabrizieren.
* Keine irrelevanten Downloads im Lauf-Verzeichnis liegen lassen.
  Stichwortsuche kann themenfremde Paper liefern (eine Abfrage
  „Claude code" lieferte ein Viterbi-Decoder-Paper). Löschen Sie
  themenfremde ``pdfs/<key>.pdf`` und leichte ``<key>.pptx``;
  bewahren Sie das aggregierte xlsx / bib als ehrliches Protokoll.
  Vollständige Anleitung in ``CLAUDE.md`` „Pruning irrelevant
  downloads".
* Keine „Claude", „Claude Code", „AI-generated", „GPT", „Copilot"
  oder andere KI-Tool-/Modellnamen in Commits, PRs, Code oder Docs.

Beispiele: ``scripts/regen_llm_security_batch.py`` (en, 8 Paper) und
``scripts/regen_llm_security_batch_zh_tw.py`` (zh-tw).

----

Installation
------------

Python **3.12+** erforderlich.

.. code-block:: bash

   git clone <repo-url>
   cd AutoPaperToPPT
   python -m venv .venv
   .venv\Scripts\Activate.ps1            # Windows PowerShell
   # source .venv/bin/activate           # Linux / macOS
   pip install -e .[dev]

Optionale Extras: ``[mcp]``, ``[intelligence]``, ``[web]``, ``[dev]``.

----

Schnellstart
------------

.. code-block:: bash

   # arXiv durchsuchen → Deck + Workbook + BibTeX
   autopapertoppt --query "diffusion models" --source arxiv --max 10 \
                  --out ./exports/

   # Einzelnes Paper per URL → Deck + BibTeX
   autopapertoppt --paper "https://arxiv.org/abs/1706.03762" \
                  --filename-stem attention --out ./exports/

   # Deck auf Deutsch rendern
   autopapertoppt --paper 1706.03762 --lang de --out ./exports/

   # Python-Pipeline-Anreicherung (Anthropic-Schlüssel erforderlich)
   export ANTHROPIC_API_KEY=sk-ant-...
   autopapertoppt --paper "https://arxiv.org/abs/1706.03762" \
                  --enrich --lang de --out ./exports/

Vollständige CLI-Flag-Tabelle: :doc:`/cli`.

----

Weiterführende Quellen
----------------------

* CLI-Flags und Umgebungsvariablen: :doc:`/cli`
* 11 MCP-Server-Tools: :doc:`/mcp`
* PPTX-Edit-Toolkit: :doc:`/pptx_editing`
* Die Datei ``readmes/README.de.md`` im Repo-Root enthält die vollständige
  Feature-Liste.
* Die tiefe technische Referenz (Plugin-Architektur,
  Sicherheitsrichtlinien, Definition of Done, SonarQube-Regeln, …)
  ist in der englischen Anleitung konsolidiert: :doc:`/en/index`.
