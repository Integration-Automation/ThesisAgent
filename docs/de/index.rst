ThesisAgents Benutzerhandbuch
================================

Stichwortgesteuerter Paper-Such-Assistent. Ruft Ergebnisse von arXiv,
Semantic Scholar, OpenAlex, PubMed, ACM, IEEE Xplore, DBLP, Crossref,
OpenAIRE, Springer Nature, Europe PMC, DOAJ, HAL, CORE und Google Scholar ab; exportiert als
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

Insgesamt 18 MCP-Tools: Discovery (``list_sources``, ``list_exports``),
``search``, ``snowball``, ``library_add``, ``library_search``, ``library_stats``, ``fetch_paper``, ``fetch_pdf_text``, ``download_pdfs``, ``pptx_validate_template``,
``export`` und sechs ``pptx_*``-Deck-Operationen (``pptx_inspect``,
``pptx_review``, ``pptx_update_slide``, ``pptx_delete_slide``,
``pptx_reorder_slides``, ``pptx_add_slide``). Vollständige Referenz:
:doc:`/mcp`.

**Um themenfremde Ergebnisse zu erkennen, beginnen Sie mit den Hinweisen
des Werkzeugs selbst.** ``--diagnostics`` (CLI) oder
``diagnostics=true`` beim MCP-Tool ``search`` erklärt das Ranking: die
Punktzahl jedes Papers, aufgeteilt in Relevanz, Aktualität und
Zitationen, die übereinstimmenden Suchbegriffe und eine Empfehlung
``keep`` / ``review`` / ``prune`` mit dem auslösenden Schwellenwert. Die
CLI schreibt die vollständige Aufschlüsselung außerdem in
``diagnostics.json`` im Ausgabeverzeichnis. Die Empfehlungen sind
Hinweise und es wird nichts für Sie entfernt, lesen Sie daher die
Abstracts der ``review``- und ``prune``-Papers, bevor Sie etwas löschen.

**Prüfen Sie, welche Quellen geantwortet haben.** Jede Antwort von
``search`` enthält ``source_stats``: für jede Quelle, wie viele
Datensätze sie geliefert hat, wie viele eindeutige Papers ihr nach der
Deduplizierung zugerechnet werden, und einen ``status`` mit dem Wert
``ok``, ``failed``, ``rate_limited`` oder ``disabled``. Eine fehlerhafte
Quelle wird übersprungen, ohne die Suche anzuhalten, lesen Sie diese
Zahlen daher, bevor Sie schließen, dass es zu einem Thema wenige Papers
gibt. Die CLI gibt dieselbe Tabelle nach jeder ``--query``-Suche aus.

**Folgen Sie den Zitationen.** ``--snowball both`` (CLI) oder das Tool
``snowball`` erweitert die obersten Ergebnisse entlang ihrer
Zitationsverknüpfungen: ``references`` ergänzt, was sie zitieren, und
``cited_by`` ergänzt, was sie zitiert. So finden sich Arbeiten, die eine
Stichwortsuche übersieht, weil die Autoren andere Begriffe verwendet
haben. Die Erweiterung ist begrenzt (standardmäßig ein Schritt), jedes
gefundene Paper behält den Weg, der zu ihm führte, und alle werden gegen
Ihre Stichwörter bewertet, sodass ein Paper nicht allein deshalb bleibt,
weil es häufig zitiert wird.

**Bewahren Sie auf, was Sie finden.** ``--library thesis.db
--library-add`` (CLI) oder das Tool ``library_add`` speichert die Papers
eines Laufs in einer Literaturbibliothek, einer einzigen SQLite-Datei,
die die Sitzung überdauert. Dieselbe Suche erneut hinzuzufügen
dupliziert nichts: Ein Paper wird an seiner DOI, seiner arXiv-ID oder
seinem Titel erkannt, und die neue Sichtung wird in den gespeicherten
Datensatz zusammengeführt. Danach findet ``library_search`` gespeicherte
Papers ohne Netzwerkzugriff, und bereits bestätigte DOIs und URLs werden
30 Tage lang nicht erneut geprüft.

**Verwenden Sie Ihre eigene Vorlage.** ``--pptx-template thesis.pptx``
(CLI) oder ``pptx_template`` beim Tool ``export`` baut das Deck auf
einer PowerPoint-Vorlage auf, sodass Hintergrund, Logo und Layouts Ihre
eigenen sind. Führen Sie zuerst ``thesisagents validate-template
thesis.pptx`` aus (oder das Tool ``pptx_validate_template``): Es listet
auf, welches Layout jede Folienart verwenden würde, und sagt, was zu
korrigieren ist. Eine Vorlage braucht 16:9-Folien und ein Layout für den
Folieninhalt, und eine kleine Konfigurationsdatei kann Layouts,
Schriftarten und Farben zuordnen.

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

**Der Export prüft das zur Laufzeit.** Bevor etwas geschrieben wird,
schlagen die CLI, das MCP-Tool ``export`` und der Deck-Tab der GUI die
DOI jedes Papers bei doi.org nach und rufen jede URL einmal ab. Eine
nicht registrierte DOI, eine URL, die 404 antwortet, oder ein nicht
erreichbarer Host stoppen den Export und nennen das Paper und den
Bezeichner. Die Prüfung belegt, dass ein Bezeichner existiert, nicht
dass er zu diesem Paper gehört, daher gelten die Regel zum Kopieren aus
der xlsx und das Audit oben weiterhin. Offline übergeben Sie
``--no-verify-identifiers`` (CLI) oder ``verify_identifiers=false``
(MCP).

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

Ausgearbeitetes Beispiel: ``scripts/regen_fang2026.py`` enthält eine
genau auf diese Weise von Hand verfasste angereicherte Zusammenfassung
(ein einzelnes Paper, Rich-Tier, zh-tw). Ein Mehr-Paper-Batch folgt
derselben Form, mit einem Eintrag pro Paper im
``PaperCollection``-Tupel.

----

Installation
------------

Python **3.12+** erforderlich.

.. code-block:: bash

   git clone <repo-url>
   cd ThesisAgents
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
   thesisagents --query "diffusion models" --source arxiv --max 10 \
                  --out ./exports/

   # Einzelnes Paper per URL → Deck + BibTeX
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --filename-stem attention --out ./exports/

   # Deck auf Deutsch rendern
   thesisagents --paper 1706.03762 --lang de --out ./exports/

   # Python-Pipeline-Anreicherung (Anthropic-Schlüssel erforderlich)
   export ANTHROPIC_API_KEY=sk-ant-...
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --enrich --lang de --out ./exports/

Vollständige CLI-Flag-Tabelle: :doc:`/cli`.

----

Weiterführende Quellen
----------------------

* CLI-Flags und Umgebungsvariablen: :doc:`/cli`
* 18 MCP-Server-Tools: :doc:`/mcp`
* PPTX-Edit-Toolkit: :doc:`/pptx_editing`
* Die Datei ``readmes/README.de.md`` im Repo-Root enthält die vollständige
  Feature-Liste.
* Die tiefe technische Referenz (Plugin-Architektur,
  Sicherheitsrichtlinien, Definition of Done, SonarQube-Regeln, …)
  ist in der englischen Anleitung konsolidiert: :doc:`/en/index`.
