Guida utente ThesisAgents
============================

Assistente di ricerca articoli guidato da parole chiave. Recupera
risultati da arXiv, Semantic Scholar, OpenAlex, PubMed, ACM, IEEE
Xplore, DBLP, Crossref, OpenAIRE, Springer Nature, Europe PMC, DOAJ, HAL, CORE e Google Scholar; ed
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

I 18 strumenti MCP completi: :doc:`/mcp`.

**Per individuare i risultati fuori tema, parti dai consigli dello
strumento stesso.** ``--diagnostics`` (CLI) o ``diagnostics=true`` sullo
strumento MCP ``search`` spiega la classifica: il punteggio di ogni
articolo suddiviso in rilevanza, attualità e citazioni, i termini della
query che corrispondono e una raccomandazione ``keep`` / ``review`` /
``prune`` con la soglia che l'ha attivata. La CLI scrive inoltre il
dettaglio completo in ``diagnostics.json`` nella directory di output. Le
raccomandazioni sono indicative e nulla viene rimosso al posto tuo,
quindi leggi gli abstract degli articoli ``review`` e ``prune`` prima di
eliminare qualcosa.

**Controlla quali fonti hanno risposto.** Ogni risposta di ``search``
contiene ``source_stats``: per ciascuna fonte, quanti record ha
restituito, quanti articoli unici le sono attribuiti dopo la
deduplicazione e uno ``status`` con valore ``ok``, ``failed``,
``rate_limited`` o ``disabled``. Una fonte che fallisce viene saltata
senza fermare la ricerca, quindi leggi questi numeri prima di concludere
che un tema ha pochi articoli. La CLI stampa la stessa tabella dopo ogni
ricerca ``--query``.

**Segui le citazioni.** ``--snowball both`` (CLI) o lo strumento
``snowball`` estende i primi risultati seguendo i loro collegamenti di
citazione: ``references`` aggiunge ciò che citano e ``cited_by``
aggiunge ciò che li cita. Trova lavori che una ricerca per parole chiave
perde perché gli autori hanno usato altri termini. L'estensione è
limitata (un passo per impostazione predefinita), ogni articolo scoperto
conserva il percorso che lo ha raggiunto, e tutti sono valutati rispetto
alle tue parole chiave, quindi un articolo non viene tenuto solo perché
è citato spesso.

**Conserva ciò che trovi.** ``--library thesis.db --library-add`` (CLI)
o lo strumento ``library_add`` salva gli articoli di un'esecuzione in
una biblioteca della letteratura, un unico file SQLite che sopravvive
alla sessione. Aggiungere di nuovo la stessa ricerca non duplica nulla:
un articolo viene riconosciuto dal suo DOI, dal suo ID arXiv o dal
titolo, e la nuova osservazione viene unita al record conservato. Poi
``library_search`` trova gli articoli conservati senza toccare la rete,
e i DOI e gli URL già verificati non vengono ricontrollati per 30
giorni.

**Usa il tuo modello.** ``--pptx-template thesis.pptx`` (CLI) o
``pptx_template`` sullo strumento ``export`` costruisce la presentazione
su un modello PowerPoint, così lo sfondo, il logo e i layout sono i
tuoi. Esegui prima ``thesisagents validate-template thesis.pptx`` (o lo
strumento ``pptx_validate_template``): elenca quale layout userebbe ogni
tipo di diapositiva e ti dice che cosa correggere. Un modello ha bisogno
di diapositive 16:9 e di un layout per il contenuto, e un piccolo file
di configurazione può assegnare layout, caratteri e colori.

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

**L'esportazione lo verifica in fase di esecuzione.** Prima di scrivere
qualsiasi cosa, la CLI, lo strumento MCP ``export`` e la scheda Deck
della GUI cercano il DOI di ogni articolo su doi.org e richiedono ogni
URL una volta. Un DOI non registrato, un URL che risponde 404 o un host
irraggiungibile fermano l'esportazione e indicano l'articolo e
l'identificatore. Il controllo dimostra che un identificatore esiste,
non che appartiene a questo articolo, quindi la regola di copiare
dall'xlsx e l'audit qui sopra restano necessari. Offline, passa
``--no-verify-identifiers`` (CLI) o ``verify_identifiers=false`` (MCP).

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

Esempio pratico: ``scripts/regen_fang2026.py`` contiene un riassunto
arricchito scritto a mano esattamente in questo modo (un solo articolo,
rich-tier, zh-tw). Un lotto multi-articolo segue la stessa forma, con
una voce per articolo nella tupla ``PaperCollection``.

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
* 18 strumenti del server MCP: :doc:`/mcp`
* Toolkit di editing PPTX: :doc:`/pptx_editing`
* Il file ``readmes/README.it.md`` nella radice del repo contiene l'elenco
  completo delle funzionalità.
* Il riferimento tecnico approfondito (architettura dei plugin,
  policy di sicurezza, Definition of Done, regole SonarQube, …) è
  consolidato nella guida inglese: :doc:`/en/index`.
