# ThesisAgents

[![CI](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![Python](https://img.shields.io/pypi/pyversions/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/ThesisAgents.svg)](https://github.com/Integration-Automation/ThesisAgents/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/thesisagents/badge/?version=latest)](https://thesisagents.readthedocs.io/en/latest/)

> **Lingue**: [English](../README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · **Italiano** · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **Documentazione**: [thesisagents.readthedocs.io](https://thesisagents.readthedocs.io/en/latest/)

Un assistente di ricerca di articoli guidato da parole chiave che recupera
risultati da arXiv, Semantic Scholar, OpenAlex, PubMed, ACM (via Crossref),
IEEE Xplore, DBLP, Crossref generico, OpenAIRE, Springer Nature, Europe PMC,
DOAJ, HAL, CORE e Google Scholar,
li normalizza in un unico formato di record ed esporta l'insieme deduplicato
come **presentazione PowerPoint stile tesi**, **cartella di lavoro Excel** e
**file BibTeX** — tutto da una sola chiamata CLI o una sola invocazione di
strumento MCP. Facoltativamente arricchisce ciascun articolo leggendone il PDF
e producendo un riassunto strutturato per articolo, sia in contesto (flusso
LLM-as-agent) sia tramite l'API Anthropic (flusso Python pipeline).

## Per agenti IA che pilotano questo progetto

**Se sei un LLM (Claude Code, Cursor, Aider, Codex CLI, …) e leggi questo README
per capire cosa fare — inizia qui.** Tutto ciò che segue è fissato anche in
[`AGENTS.md`](AGENTS.md) (specchio cross-agent) e [`CLAUDE.md`](CLAUDE.md)
(riferimento canonico); leggili prima di apportare cambiamenti non banali.

### Cosa vuole davvero l'utente

Il deliverable predefinito è **un `.pptx` arricchito stile tesi per articolo**,
non il deck leggero solo-abstract che la CLI produce di default. L'output
leggero è un artefatto intermedio — il tuo lavoro è elevarlo.

### Albero decisionale

1. `ANTHROPIC_API_KEY` è impostata nell'ambiente? → esegui semplicemente la
   CLI; si auto-arricchisce via API Anthropic. Hai finito.
2. Senza chiave, ma tu (un LLM) stai pilotando la sessione → **produci tu
   stesso il riassunto arricchito**. Leggi ogni PDF, redigi a mano un
   `PaperSummary` con i campi di livello rich (`pain_points`,
   `research_question`, `contributions_detailed`, `headline_metrics`,
   `technique_table`, `method_sections`, `evaluation_sections`, `system_flow`,
   `research_questions`, `rq_results`, `core_observation`, `limitations`,
   `future_work`), deposita uno `scripts/regen_<query>.py` ed eseguilo. **Non
   dire all'utente di impostare la API key** — sei tu l'LLM che avrebbe scritto
   il riassunto.
3. Nessun LLM nel loop (CI / cron / non presidiato) → l'output leggero è
   accettabile.

### Flusso MCP in 6 passi

```
1. (optional) list_sources()                              # see which plugins are enabled
2. search(keywords, sources, top_tier_only=true, ...)
3. (optional) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # per paper
5. (you read each PDF and produce a structured summary dict)
6. export(papers=[{...paper, "summary": {...}}], language="zh-tw", ...)
```

I tredici strumenti MCP (inclusi `list_sources`, `list_exports`,
`download_pdfs`, `pptx_inspect` / `pptx_review` / `pptx_update_slide` /
`pptx_add_slide` / ecc.) sono
documentati in [`docs/mcp.md`](docs/mcp.md).

### Obbligatorio: verifica URL / DOI prima della consegna

I percorsi URL degli editori **non si possono indovinare** — AAAI usa ID
numerici (`v40i5.37389`), IEEE usa un `arnumber` opaco, ACM usa DOI opachi.
Quando redigi un `Paper` a mano, **copia `url` / `doi` / `arxiv_id`
letteralmente dall'xlsx di ricerca che ha prodotto questa esecuzione** — mai a
memoria, mai costruito dal titolo.

L'xlsx viene scritto in `exports/<run>/<slug>-<timestamp>.xlsx` con la
colonna 7 = DOI, colonna 8 = URL. Audita il tuo script regen quando hai
finito:

```python
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
```

Due fabbricazioni colte così in produzione: volume AAAI errato
(`v39i23.34521` invece del reale `v39i22.34537`) e percorso con slug d'autore
inventato (`view/fang2026` invece di `v40i5.37389`).

### Obbligatorio: rimuovi i download non pertinenti prima della consegna

La corrispondenza della ricerca è basata su parole chiave, quindi articoli
fuori tema si infiltreranno: una query «Claude code» ha restituito un articolo
su un decodificatore di Viterbi perché entrambi contengono «code»; «LLM code
review» ha corrisposto a una rassegna della letteratura sulla rilevazione di
oggetti. Una volta letti gli abstract e classificato un articolo come fuori
tema rispetto all'intento reale dell'utente, ripulisci la directory di
esecuzione:

```python
from pathlib import Path
run = Path("exports/<run>")
irrelevant_keys = ("key-of-off-topic-paper-1", "key-of-off-topic-paper-2")
for key in irrelevant_keys:
    for path in (run / "pdfs" / f"{key}.pdf", run / f"{key}.pptx"):
        if path.exists():
            path.unlink()
```

Elimina `exports/<run>/pdfs/<key>.pdf` + `exports/<run>/<key>.pptx`.
**Conserva** il `<slug>-<timestamp>.xlsx` / `.bib` aggregato — sono la
registrazione onesta di ciò che la ricerca ha restituito. I casi limite
ricevono un riassunto rich; meglio includere troppo che scartare
silenziosamente una possibile corrispondenza.

### Esempio funzionante

[`scripts/regen_fang2026.py`](scripts/regen_fang2026.py) include un riassunto
rich scritto a mano costruito esattamente in questo modo (articolo singolo,
livello rich, zh-tw, ogni campo rich compilato). Una ricerca multi-articolo
segue la stessa forma con una voce `Paper(...summary=PaperSummary(...))` per
articolo nella tupla `PaperCollection`.

### Divieti

- **Non** terminare una ricerca multi-articolo dicendo all'utente «imposta
  `ANTHROPIC_API_KEY` per un deck arricchito» — sei tu l'LLM che avrebbe potuto
  scrivere i riassunti.
- **Non** trattare il `.pptx` leggero per articolo come il deliverable.
- **Non** fermarti dopo che `download_pdfs` segnala N PDF salvati — è l'inizio
  della fase di scrittura rich, non la fine.
- **Non** inventare numeri, RQ, contributi o limiti che non sono
  nell'articolo.
- **Non** fabbricare URL / DOI / ID arXiv — vedi la regola sopra.
- **Non** lasciare download non pertinenti nella directory di esecuzione. Le
  corrispondenze della ricerca per parole chiave possono includere articoli
  fuori tema (una query «Claude code» ha portato un articolo su un
  decodificatore di Viterbi; «LLM code review» ha portato una rassegna della
  letteratura sulla rilevazione di oggetti). Dopo aver classificato gli
  articoli come fuori tema, elimina i loro `pdfs/<key>.pdf` e il `<key>.pptx`
  leggero; conserva l'xlsx / bib aggregato come registrazione onesta di ciò che
  la ricerca ha restituito.
- **Non** menzionare «Claude», «Claude Code», «AI-generated», «GPT», «Copilot»
  o qualsiasi nome di strumento/modello IA nei messaggi di commit, nelle
  descrizioni di PR, nei commenti di codice o nella documentazione.

## Funzionalità

- **Quindici sorgenti plug-in**: `arxiv`, `semantic_scholar`, `openalex`,
  `pubmed`, `acm` (limitato a Crossref), `dblp`, `crossref` (non limitato),
  `openaire`, `springer` (richiede chiave API), `europepmc` (aperto, senza
  chiave — scienze della vita + preprint + agricoltura), `doaj` (aperto, senza
  chiave — riviste ad accesso aperto, di solito con un link diretto al PDF),
  `hal` (aperto, senza chiave — l'archivio francese di informatica / matematica
  / fisica con PDF a testo integrale), `core` (richiede chiave API gratuita —
  il più grande aggregatore ad accesso aperto, oltre 250 milioni di opere),
  `ieee` (attivo di default via Chrome visibile; una chiave API aggiunge l'API
  ufficiale Xplore), `scholar` (attivo di default via Chrome visibile). Ognuna
  vive in `sources/<name>/` dietro un adattatore `Fetcher`. Passa
  `--top-tier-only` per filtrare i risultati sulle conferenze/riviste di punta
  dell'informatica più Nature/Science/PNAS. La ricerca di default mantiene
  tutte le sedi.
- **Modalità articolo singolo**: incolla un ID arXiv, un URL arXiv, un DOI, un
  PMID o un URL di documento IEEE — ThesisAgents lo risolve tramite la sorgente
  giusta ed emette lo stesso bundle di esportazione. Utile per appunti di
  lettura degli articoli e preparazione della difesa della tesi.
- **Modalità PDF locale** (`--pdf <path>`): passa un PDF o una directory. Un
  estrattore euristico tira fuori **titolo, autori, anno, ID arXiv, DOI e
  l'abstract reale** direttamente dalla parte iniziale di ciascun PDF (ancorato
  all'intestazione esplicita `Abstract` / `ABSTRACT` / `摘要`, non a un prefisso
  cieco). `--title` / `--authors` / `--year` / `--venue` / `--doi` /
  `--arxiv-id` prevalgono in una chiamata a PDF singolo; in una directory,
  l'estrazione file per file vince, così ogni articolo ottiene il proprio deck
  nominato con la sua chiave BibTeX.
- **Otto esportatori**:
  - `.pptx` — widescreen 16:9, numerato, tre livelli di rendering (leggero
    solo-abstract · enriched-flat · **stile tesi** con quadranti dei punti di
    dolore, KPI in evidenza, tabelle comparative di tecniche, tabelle dei
    risultati per RQ, sintesi dei contributi, osservazione centrale, limiti &
    lavori futuri, Q&A, bibliografia). Tutte le stringhe template sono i18n in
    **14 lingue**: English, 繁體中文, 简体中文, 日本語, Español, Français, Deutsch,
    한국어, Português, Русский, Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia.
  - **Identità visiva del deck progettata** (non il look predefinito Calibri su
    bianco): tipografia per lingua (Inter per il Latin, Microsoft JhengHei UI /
    YaHei UI / Yu Gothic UI / Malgun Gothic / Nirmala UI per CJK + Hindi),
    geometria di accento programmatica (barra di accento superiore su ogni slide
    di contenuto + banda sinistra sulla copertina), formattazione tabellare in
    stile accademico (griglia predefinita rimossa, regola d'intestazione navy,
    divisori soft tra le righe, striscia di righe alternate, allineamento
    verticale centrato, etichette di riga in grassetto) e una disciplina di
    palette a cinque colori (navy / teal / grigio / chiaro / bianco) con il
    rosso **vietato** per il testo (usa invece grassetto + teal `#0E7490` per
    l'enfasi).
  - **La modalità chiara è il percorso di rendering di default.** Passa
    `--dark-mode`, attiva **Dark mode** nella tab Deck della GUI, o imposta
    `ExportOptions(dark_mode=True)` per applicare il post-pass scuro (sfondo
    slide `#12151B`, testo del corpo `#E5E7EB`).
  - `.xlsx` — foglio Papers + foglio di provenienza della Query, URL / PDF con
    hyperlink, intestazione bloccata, larghezze di colonna automatiche. La
    colonna 5 (**Source**) mostra la sede di pubblicazione reale (es. «IEEE
    Access»); la colonna 6 (**Indexed via**) mostra quale fetcher ha restituito
    i metadati (es. «openalex»), così le due informazioni non collidono mai.
  - `.md` — elenco completo sorgente / titolo / abstract.
  - `.bib` — chiavi di citazione senza collisioni, campi con escape per LaTeX.
  - `.json` — payload grezzo per il tooling a valle.
  - `.ris` — interscambio RIS importato da Zotero / Mendeley / EndNote /
    RefWorks (il fratello di BibTeX per i gestori di riferimenti non-LaTeX).
  - `.csv` — tabella piatta di una riga per articolo per fogli di calcolo /
    triage rapido con grep (quoting RFC-4180, così le virgole nei titoli non
    spostano mai le colonne).
  - `.csl.json` — CSL-JSON per Pandoc / citeproc; renderizza una bibliografia in
    qualsiasi stile CSL (APA, IEEE, Nature, …). L'estensione `.csl.json` la
    mantiene distinta dal dump `.json` semplice.
- **Toolkit di editing PPT**: `thesisagents.exporters.pptx_edit`
  (inspect / update_slide / delete_slide / reorder_slides / add_slide)
  funziona su qualsiasi deck prodotto dall'esportatore, più gli strumenti MCP
  `pptx_*` equivalenti così che un agente LLM possa iterare su un deck
  generato.
- **Server MCP**: 13 strumenti — `list_sources` + `list_exports`
  (discovery), `search`, `fetch_paper`, `fetch_pdf_text`,
  `download_pdfs`, `export` e i sei strumenti deck `pptx_*`
  (`inspect`, `review`, `update_slide`, `delete_slide`,
  `reorder_slides`, `add_slide`). Permette a
  qualsiasi LLM MCP-compatibile
  (Claude Code, Claude Desktop, Cursor, …) di pilotare l'intero workflow.
- **Due percorsi di arricchimento** per andare oltre l'abstract verso un vero
  deck stile tesi:
  - **LLM-as-agent (nessuna chiave API)** — l'LLM chiamante legge il testo del
    corpo del PDF via `fetch_pdf_text`, scrive un riassunto strutturato in
    contesto e lo passa a `export`.
  - **Pipeline Python (`--enrich`)** — la CLI chiama direttamente l'API di
    Anthropic; modello di default `claude-opus-4-7`.
- **Flussi di editore con Chrome visibile**: la SERP di Scholar, il
  `/rest/search` di IEEE e ogni download di PDF a pagamento (ieeexplore /
  dl.acm / link.springer / sciencedirect / wiley / oup / nature / science / …)
  vengono eseguiti dentro una sessione Chrome reale e visibile via `selenium`.
  L'utente risolve il captcha / completa l'SSO nella finestra dal vivo una
  volta; `THESISAGENTS_CHROME_PROFILE_DIR` persiste i cookie tra le esecuzioni.
- **Flusso LLM-as-agent**: gli strumenti MCP forniscono ricerca, download di
  PDF ed estrazione di testo. `scripts/regen_*.py` contiene esempi riproducibili
  per redigere a mano un `PaperSummary` rich per articolo.
- **Risolutore di PDF OA**: dopo la deduplicazione, ogni articolo senza
  `pdf_url` passa per Unpaywall → S2 `openAccessPdf` → ricerca per titolo su
  arXiv → CORE.ac.uk (quando le chiavi sono impostate). Guadagno tipico su query
  a forte densità IEEE / ACM / Springer / Elsevier: da 40 a 70 punti
  percentuali.
- **Sicuro per default**: trasporto HTTP solo-HTTPS, rate limit per sorgente
  (token bucket), `defusedxml` per ogni payload XML, percorsi di esportazione
  sicuri contro path-traversal, niente `eval` / `exec` / `pickle` su input
  utente.
- **Guardia di vocabolario zh-tw / zh-cn**: ~244 pattern regex in
  `tests/test_i18n.py::test_zh_tw_files_use_traditional_chinese_vocabulary`
  catturano le parole prese in prestito dal cinese semplificato rese con hanzi
  tradizionale (es. `內存` → `記憶體`, `魯棒性` → `穩健性`, `軟件` → `軟體`,
  `緩存` → `快取`). La stessa guardia gira al contrario per le stringhe della
  locale zh-cn. La regola completa + il catalogo regex vivono in
  `.claude/agents/rules/language-vocabulary-check.md`.

## Avvio rapido

```powershell
git clone <repo-url>
cd ThesisAgents
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Install with dev extras (also pulls in MCP SDK and intelligence deps)
pip install -e .[dev]
```

Cerca su arXiv ed esporta deck + workbook + BibTeX (default per `--query`):

```powershell
py -m thesisagents --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

Recupera un singolo articolo per URL — default `.pptx + .bib` (l'`.xlsx` ha
meno senso per una sola riga):

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

Renderizza il deck in 繁體中文:

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --lang zh-tw --out .\exports\
```

Arricchimento via pipeline LLM (Python chiama Anthropic direttamente —
richiede chiave API):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang zh-tw --out .\exports\
```

## Flag della CLI

| Flag | Scopo |
|---|---|
| `--query` / `-q` | Parole chiave (obbligatorio salvo `--paper`). |
| `--paper` / `-p` | ID / URL arXiv, DOI, PMID o URL di documento IEEE. Mutuamente esclusivo con `--query`. |
| `--source` / `-s` | Lista di sorgenti separate da virgola. Default `arxiv`. |
| `--max` / `-n` | Risultati max per sorgente (1..200). Default 25. |
| `--year-from` / `--year-to` | Filtro anno inclusivo. |
| `--export` / `-e` | Formati: uno qualsiasi di `pptx,xlsx,md,bib,json,ris,csv,csl`. Il default dipende dalla modalità (vedi sotto). |
| `--out` / `-o` | Directory di output. Default `./exports`. |
| `--filename-stem` | Sovrascrive lo stem del nome file generato. |
| `--no-abstract` | Omette il contenuto dell'abstract dagli export. |
| `--lang` / `-l` | Lingua del deck: una su 14 — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. Default `en`. |
| `--enrich` | Variante fail-loud dell'auto-arricchimento. Richiede `ANTHROPIC_API_KEY` e l'extra `[intelligence]`. (L'auto-arricchimento è il default quando la chiave è impostata.) |
| `--lightweight` | Salta l'arricchimento + forza il deck solo-abstract. Da usare solo per esecuzioni rapide / non presidiate; **quando un agente LLM sta pilotando, preferisci il flusso LLM-as-agent** qui sotto. |
| `--llm-model` | Sovrascrive il modello di default `claude-opus-4-7` per l'arricchimento. |
| `--no-pdf` | Salta il download automatico del PDF. Disattiva anche il gate PPT per articolo (niente PDF → niente contenuto completo). |
| `--no-oa-resolve` | Salta il risolutore di PDF OA post-deduplicazione (Unpaywall + S2 + arXiv + CORE.ac.uk). |
| `--top-tier-only` | Limita i risultati ad arXiv + una whitelist curata di riferimenti dell'informatica (S&P, CCS, NDSS, USENIX Security, NeurIPS, ICML, ICSE, …). Disattivato di default. |
| `--paywall-threshold` | Frazione di risultati con paywall che attiva il prompt di conferma. Default 0.30. |
| `--yes` | Salta il prompt di paywall e prosegue. |
| `--max-slides` | Tetto di slide per articolo (default 25; passa 0 per illimitato). |
| `--dark-mode` | Renderizza il pptx con sfondo scuro + testo quasi bianco. Il default è il deck chiaro con banda navy. |
| `--quiet` | Sopprime la stampa per articolo. |

### Variabili d'ambiente

| Variabile | Usata da | Scopo |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | Auth LLM. Non serve per il percorso LLM-as-agent via MCP. |
| `THESISAGENTS_LLM_MODEL` | `--enrich` | Sovrascrive il default `claude-opus-4-7`. |
| `THESISAGENTS_S2_API_KEY` | Semantic Scholar + risolutore OA | Rate limit più alto; usata anche dal passo S2 `openAccessPdf` del risolutore OA. Chiave gratuita su <https://www.semanticscholar.org/product/api>. |
| `THESISAGENTS_NCBI_API_KEY` | PubMed | Alza il limite anonimo di NCBI (3/s) a 10/s. Opzionale. |
| `THESISAGENTS_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex, **Unpaywall** | Etichetta polite-pool + abilita il passo Unpaywall del risolutore OA (il maggior guadagno di copertura PDF per articoli con paywall di IEEE / ACM / Springer / Elsevier; guadagno tipico 40–70 pp). |
| `THESISAGENTS_IEEE_API_KEY` | IEEE (via API) | API ufficiale IEEE Xplore; espone `pdf_url` per gli articoli in ambito. |
| `THESISAGENTS_DISABLE_IEEE_SCRAPING` | IEEE | **IEEE è attivo di default via Chrome visibile.** Imposta `=1` per disattivarlo (es. CI senza Chrome). Il ramo di scraping httpx gira solo come fallback quando WebRunner non è disponibile. |
| `THESISAGENTS_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Token abbonato Crossref Plus (header Bearer). Opzionale. |
| `THESISAGENTS_SPRINGER_API_KEY` | Springer | Obbligatoria; chiave gratuita da <https://dev.springernature.com/>. Il plugin solleva `ConfigError` senza di essa. |
| `THESISAGENTS_DISABLE_SCHOLAR_SCRAPING` | Google Scholar | **Scholar è attivo di default via Chrome visibile.** Imposta `=1` per disattivarlo (i ToS di Google vietano l'accesso automatizzato — attivo di default per la copertura, opt-out per evitare il rischio di captcha / blocco IP). |
| `THESISAGENTS_CHROME_PROFILE_DIR` | Download di Scholar + IEEE + PDF con paywall | `--user-data-dir` di Chrome persistente. Impostalo e completa VPN / SSO / accesso Google una volta; le esecuzioni successive ereditano i cookie così IEEE restituisce metadati con paywall e Scholar serve SERP non limitate. |
| `THESISAGENTS_DISABLE_WEBRUNNER` | Download di Scholar + IEEE + PDF con paywall | `=1` forza i percorsi httpx invece di pilotare Chrome reale. Utile per CI / Docker senza un binario di Chrome; altrimenti lascialo non impostato. |
| `THESISAGENTS_CORE_API_KEY` | Risolutore OA + sorgente di ricerca `core` | Chiave gratuita da <https://core.ac.uk/services/api>. Abilita il passo di ricerca OA di CORE.ac.uk (oltre 200 milioni di elementi OA istituzionali / regionali) **e** la sorgente di ricerca `core`. Senza di essa, la sorgente `core` viene saltata silenziosamente e le altre strategie OA (Unpaywall, S2, arXiv) girano comunque. |
| `THESISAGENTS_PDF_COOKIES_FILE` | Downloader di PDF | `cookies.txt` in formato Netscape. Disattivato di default. Usalo solo con editori per cui hai diritti istituzionali. |
| `THESISAGENTS_LOG_LEVEL` | logger | `INFO` di default; `DEBUG` per tracciamento verboso. |

Default: `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. Sempre
sovrascrivibile con un `--export` esplicito.

## Flusso LLM-as-agent

Quando un LLM nel tuo editor pilota il workflow, usa gli strumenti MCP in
sequenza: `search`, `download_pdfs`, `fetch_pdf_text`, poi `export` con un
`PaperSummary` rich scritto a mano. I file `scripts/regen_*.py` esistenti sono
esempi riproducibili per il passo finale di scrittura ed esportazione.

Il runbook completo end-to-end (ricerca → deck rich) vive in
`.claude/agents/tasks/paper-summary-author.md` — aprilo prima di iniziare una
nuova query così che l'LLM possa eseguire il flusso senza fermarsi per input
dell'utente.

## Server MCP

Registra con Claude Code:

```powershell
claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp
```

Oppure scrivi nel tuo file di configurazione:

```json
{
  "mcpServers": {
    "thesisagents": {
      "command": ".venv\\Scripts\\python.exe",
      "args": ["-m", "thesisagents.mcp"]
    }
  }
}
```

Strumenti:

| Strumento | Scopo |
|---|---|
| `list_sources` | Enumera ogni plugin + riporta se ciascuno è abilitato nell'ambiente corrente. Chiamalo una volta prima di `search`. |
| `list_exports` | Enumera ogni formato di esportazione con la sua descrizione di una riga e se scrive un file aggregato o un file per articolo. |
| `search` | Parole chiave → lista di articoli. Accetta `top_tier_only`, `min_citations`; per default usa il mix completo di sorgenti senza chiave API. |
| `fetch_paper` | Identificatore arXiv / DOI / PMID / IEEE → articolo singolo. |
| `fetch_pdf_text` | Scarica un PDF, restituisce il testo del corpo estratto. **Il percorso MCP verso «ho letto l'articolo».** |
| `download_pdfs` | Scarica in lotto i PDF di una lista di articoli in `{out_dir}/pdfs/`. Restituisce risultati per articolo indicizzati per chiave BibTeX. |
| `export` | Lista di articoli + formati → scrive `.pptx/.xlsx/.md/.bib/.json/.ris/.csv/.csl.json`. Accetta un campo `summary` per articolo per lo schema rich stile tesi, `max_slides_per_paper` (default 25) e `dark_mode` (default `false` — il default del progetto è il deck chiaro con banda navy, passa `true` per il post-pass scuro OLED / a bassa luminosità). |
| `pptx_inspect` | Legge la struttura di slide / shape di un deck esistente. |
| `pptx_review` | Verifica un deck in una sola chiamata — overflow + contratti colore + completezza delle sezioni `paper_rule`. Rileva automaticamente la lingua del deck; anche la CLI `python -m thesisagents review <deck.pptx>`. |
| `pptx_update_slide` | Sostituisce `title` / `body` / `meta` (per nome di shape) o shape arbitrari per indice. |
| `pptx_delete_slide` | Rimuove una slide e la sua part relationship. |
| `pptx_reorder_slides` | Permuta le slide via `sldIdLst`. |
| `pptx_add_slide` | Aggiunge in coda o inserisce una nuova slide title / body / meta. |

Flusso LLM-as-agent (nessuna `ANTHROPIC_API_KEY` necessaria — l'LLM è
l'agente):

```
1. (optional) list_sources()                       # discover enabled plugins
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (optional) download_pdfs(papers, out_dir="./exports/...")  # persist PDFs
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # per paper
5. (the LLM reads body text, produces a structured `summary` dict)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="zh-tw", formats=["pptx","bib"], dark_mode=true, ...)
```

Riferimento completo in [`docs/mcp.md`](docs/mcp.md).

## Struttura del progetto

```
ThesisAgents/
├── thesisagents/                 # main package
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # HTTPS-only async client, token-bucket rate limit
│   ├── exporters/                   # pptx (thesis-style) · xlsx · bib · md · json · ris · csv · csl · pptx_edit · i18n
│   ├── intelligence/                # PDF fetch + Anthropic summariser  ([intelligence] extra)
│   ├── evaluation/                  # offline search-quality benchmark (docs/search-quality.md)
│   ├── mcp/                         # FastMCP server (13 tools)
│   ├── sources/<name>/              # plugin folders: arxiv, semantic_scholar,
│   │                                #   openalex, pubmed, acm, ieee, scholar,
│   │                                #   dblp, crossref, openaire, springer,
│   │                                #   europepmc, doaj, hal, core
│   ├── utils/                       # logging, path safety
│   ├── cli.py                       # argparse CLI
│   └── __main__.py
├── tests/                           # pytest suite + recorded fixtures (no live HTTP)
├── docs/                            # Sphinx (14 language trees)
├── scripts/                         # one-off regen scripts
└── pyproject.toml                   # ruff, bandit, build, optional extras
```

## Definition of Done

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r thesisagents/
```

Il flag `-c` di bandit è obbligatorio — senza di esso bandit ignora la
configurazione di skip del progetto. Quando tocchi l'esportatore pptx, esegui
anche un controllo di overflow (vedi `CLAUDE.md` «Slide Deck Rules»).

## GUI desktop (PySide6)

Un'interfaccia desktop nativa è distribuita dietro l'extra `[gui]`:

```powershell
pip install thesisagents[gui]
thesisagents-gui                 # or: thesisagents gui
```

La finestra ha quattro tab — **Search**, **Settings** (persiste le chiavi API
via QSettings), **Enrich** (pilota l'arricchimento LLM-as-agent / pipeline
Python su un segnale `collection_ready`) e **Deck** (il toggle della modalità
chiara + i controlli di tetto slide + max figure confluiscono in
`ExportOptions`). Lo zip di release per Windows porta il bundle compilato con
Nuitka con PySide6 incluso, così `thesisagents.exe gui` funziona senza una
installazione separata di Python.
**La UI è distribuita in tutte le 14 lingue** (English, 繁體中文, 简体中文,
日本語, Español, Français, Deutsch, 한국어, Português, Русский,
Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia) — il primo avvio sceglie la
lingua dalla locale del tuo SO, poi **Settings → Interface language** ti
permette di cambiarla. La lingua di output del deck è un menu a tendina
separato, così puoi eseguire la UI in una lingua ed emettere le slide in
un'altra. Il layout è responsive: ogni form sta in una `QScrollArea` e la
finestra si ridimensiona fino a 900×600 (sta ancora in 720p), con lo scaling
HiDPI attivo di default.

Riferimento completo: [`docs/gui.md`](docs/gui.md).

## Pacchettizzazione come eseguibile standalone

Due packager sono documentati per distribuire un binario a file singolo che
gira senza Python installato:

- **[`docs/packaging-pyinstaller.md`](docs/packaging-pyinstaller.md)**
  — build veloce (meno di un minuto), output di 200–300 MB, avvio in 2–4 s.
  Ideale quando iteri sullo script di build.
- **[`docs/packaging-nuitka.md`](docs/packaging-nuitka.md)** —
  build lento (5–15 minuti), output di 80–150 MB, avvio sotto il secondo, una
  certa protezione del bytecode. Ideale quando gli utenti finali eseguono il
  binario molte volte.

Entrambi i documenti coprono l'insidia specifica del progetto — i plugin di
sorgente dinamici in `sources/<name>/` — e portano un comando verificato per i
punti di ingresso della CLI e del server MCP.

## Integrazione continua & release

Due workflow di GitHub Actions vivono in `.github/workflows/`:

- **`ci.yml`** gira su ogni push e PR verso `main`. La matrice è Ubuntu +
  Windows × Python 3.12 / 3.13 / 3.14 (6 job). Ogni job esegue
  `ruff check`, `bandit -c pyproject.toml` e `pytest`.
- **`release.yml`** attende che `ci.yml` si completi su `main` (trigger
  `workflow_run`). Gira solo se il CI ha avuto successo. **Ogni push con CI
  riuscito verso `main` è una release** — il workflow incrementa
  automaticamente la versione di patch in `pyproject.toml`, committa
  l'incremento di ritorno su `main` come `chore: bump version to X.Y.Z`, e
  concatena:
  1. **`bump-version`** — legge la `X.Y.Z` attuale da `pyproject.toml`,
     incrementa a `X.Y.(Z+1)`, committa + fa push di ritorno su `main` usando il
     `GITHUB_TOKEN` del workflow. Quel push NON ri-attiva il CI (per la regola di
     GitHub secondo cui i push pilotati da `GITHUB_TOKEN` non possono avviare
     nuove esecuzioni di workflow), così il ciclo termina naturalmente.
  2. **`publish-pypi`** — costruisce sdist + wheel, `twine check`,
     `twine upload` via `PYPI_API_TOKEN`.
  3. **`create-draft-release`** — apre una release GitHub in *bozza* al tag
     `v<version>` con note generate automaticamente.
  4. **`build-nuitka`** — compila un bundle standalone Nuitka su un runner
     Windows (punto di ingresso: `python -m thesisagents` via
     `--python-flag=-m`), lo sottopone a smoke-test, comprime la cartella
     `thesisagents.dist/` risultante e allega lo zip + un checksum `.sha256`
     alla release in bozza. Standalone (non onefile) per progettazione: onefile
     si auto-estrae in `%TEMP%` a ogni avvio, aggiungendo latenza di avvio e
     facendo scattare le euristiche antivirus sulle macchine bloccate. Solo
     Windows per progettazione anche: gli utenti Linux / macOS installano da
     PyPI. La cache di build indicizzata su `pyproject.toml` taglia i build a
     caldo da ~85 min a freddo a ~5–10 min.
  5. **`publish-release`** — toglie il contrassegno di bozza una volta caricato
     l'asset Nuitka, così che gli utenti non vedano mai una release a metà.

  **Saltare una release.** Includi `[skip release]` ovunque nel messaggio di
  commit e l'incremento + ogni job a valle vengono saltati — usalo per i commit
  solo-docs / typo / refactor che non dovrebbero bruciare un numero di
  versione.

Per abilitare la pubblicazione su PyPI + gli eseguibili di release:

1. Genera un token API con ambito di progetto su
   <https://pypi.org/manage/account/token/>.
2. Nel repository GitHub: `Settings → Secrets and variables → Actions →
   New repository secret`. Nominalo `PYPI_API_TOKEN` e incolla il valore del
   token.
3. Consenti a GitHub Actions di fare push su `main`: `Settings → Actions →
   General → Workflow permissions → Read and write permissions`. Il commit di
   incremento è inviato dal `GITHUB_TOKEN` del workflow.
4. Taglia le release fondendo le PR in `main`. La pipeline impiega ~3–5 min per
   pubblicare su PyPI e ~80–90 min in più (a freddo) o ~5–10 min (cache Nuitka
   a caldo) perché lo zip di Windows venga allegato.

Il job `publish-pypi` intenzionalmente NON allega un Environment di GitHub, così
ogni esecuzione appare come una voce di Release (con il suo `.exe` Nuitka
allegato) invece che come un widget «Deployment» nella barra laterale della home
del repo — le release ottengono la propria pagina dedicata e una voce di
Deployment in cima sarebbe solo rumore ridondante.

## Licenza

Vedi `LICENSE`. L'API arXiv è usata secondo i termini di utilizzo dell'API di
arXiv (<https://info.arxiv.org/help/api/tou.html>) — rispetta il limite soft di
1 richiesta ogni 3 secondi; il fetcher incluso lo impone già via il suo token
bucket.
