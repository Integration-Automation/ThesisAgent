# ThesisAgents

[![CI](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![Python](https://img.shields.io/pypi/pyversions/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/ThesisAgents.svg)](https://github.com/Integration-Automation/ThesisAgents/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/thesisagents/badge/?version=latest)](https://thesisagents.readthedocs.io/en/latest/)

> **Lingue**: [English](../README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · **Italiano** · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **Documentazione**: [thesisagents.readthedocs.io](https://thesisagents.readthedocs.io/en/latest/)

Assistente di ricerca di articoli guidato da parole chiave. Recupera risultati da arXiv, Semantic Scholar, OpenAlex, PubMed, ACM (via Crossref), IEEE Xplore, DBLP, Crossref generico, OpenAIRE, Springer Nature, Europe PMC, DOAJ, HAL, CORE e Google Scholar; li normalizza in un unico formato di record; ed esporta l'insieme deduplicato come **presentazione PowerPoint stile tesi**, **cartella di lavoro Excel** e **file BibTeX** — tutto da una chiamata CLI o un'invocazione MCP. Può arricchire ciascun articolo leggendone il PDF e producendo un riassunto strutturato, sia in-contesto (flusso LLM-as-agent) sia tramite API Anthropic (flusso Python pipeline).

## Per agenti IA che pilotano questo progetto

**Se sei un LLM (Claude Code, Cursor, Aider, Codex CLI, …) e leggi questo README per capire cosa fare — inizia qui.** Le stesse regole sono fissate in [`AGENTS.md`](AGENTS.md) (specchio cross-agent) e [`CLAUDE.md`](CLAUDE.md) (riferimento canonico); leggile prima di cambiamenti non banali.

### Cosa vuole davvero l'utente

Il deliverable predefinito è **un `.pptx` arricchito stile tesi per articolo**, non il deck leggero solo-abstract che la CLI produce di default. L'output leggero è un artefatto intermedio — il tuo lavoro è elevarlo.

### Albero decisionale

1. `ANTHROPIC_API_KEY` impostata nell'ambiente? → esegui la CLI; si auto-arricchisce via API Anthropic. Fatto.
2. Senza chiave, ma tu (LLM) stai pilotando la sessione → **scrivi il riassunto arricchito tu stesso**. Leggi ogni PDF, redigi a mano un `PaperSummary` con i campi rich-tier (`pain_points`, `research_question`, `contributions_detailed`, `headline_metrics`, `technique_table`, `method_sections`, `evaluation_sections`, `system_flow`, `research_questions`, `rq_results`, `core_observation`, `limitations`, `future_work`), deposita uno `scripts/regen_<query>.py` ed eseguilo. **Non dire all'utente di impostare la API key** — sei tu l'LLM che avrebbe scritto il riassunto.
3. Nessun LLM nel loop (CI / cron / non presidiato) → l'output leggero è accettabile.

### Flusso MCP in 6 passi

```
1. (facoltativo) list_sources()                           # quali plugin sono attivi
2. search(keywords, sources, top_tier_only=true, ...)
3. (facoltativo) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # per articolo
5. (leggi ogni PDF e produci un dict di riassunto strutturato)
6. export(papers=[{...paper, "summary": {...}}], language="it", ...)
```

I dodici strumenti MCP (inclusi `list_sources`, `list_exports`, `download_pdfs`, `pptx_inspect` / `pptx_update_slide` / `pptx_add_slide` / ecc.) sono documentati in [`docs/mcp.md`](docs/mcp.md).

### Obbligatorio: verifica URL / DOI prima della consegna

I percorsi URL degli editori **non si possono indovinare** — AAAI usa ID numerici (`v40i5.37389`), IEEE usa un `arnumber` opaco, ACM usa DOI opachi. Quando scrivi un `Paper` a mano, **copia `url` / `doi` / `arxiv_id` letteralmente dall'xlsx prodotto da questa ricerca** — mai a memoria, mai costruito dal titolo.

L'xlsx viene scritto in `exports/<run>/<slug>-<timestamp>.xlsx` con colonna 7 = DOI, colonna 8 = URL. Audita il tuo script regen al termine:

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

Due fabbricazioni colte così in produzione: volume AAAI errato (`v39i23.34521` vs il reale `v39i22.34537`) e percorso con slug d'autore inventato (`view/fang2026` invece di `v40i5.37389`).

### Esempio funzionante

[`scripts/regen_llm_security_batch.py`](scripts/regen_llm_security_batch.py) include 8 riassunti arricchiti scritti a mano esattamente con questo procedimento. Usalo come template per qualsiasi ricerca multi-articolo. La controparte zh-tw è in [`scripts/regen_llm_security_batch_zh_tw.py`](scripts/regen_llm_security_batch_zh_tw.py).

### Divieti

- **Non** terminare una ricerca multi-articolo dicendo all'utente «imposta `ANTHROPIC_API_KEY` per il deck arricchito» — sei tu l'LLM che avrebbe scritto i riassunti.
- **Non** trattare il `.pptx` leggero per articolo come deliverable.
- **Non** fermarti quando `download_pdfs` segnala «N PDF salvati» — è l'inizio della fase di scrittura rich, non la fine.
- **Non** inventare numeri, RQ, contributi o limiti assenti dall'articolo.
- **Non** fabbricare URL / DOI / ID arXiv — vedi la regola sopra.
- **Non** lasciare download non pertinenti nella directory di esecuzione. La ricerca per parole chiave a volte include articoli fuori tema (una query «Claude code» ha portato un articolo sul decodificatore Viterbi; «LLM code review» ha portato una rassegna sulla rilevazione di oggetti). Dopo aver classificato un articolo come fuori tema, elimina il suo `pdfs/<key>.pdf` e il `<key>.pptx` leggero; conserva l'xlsx / bib aggregato come registrazione onesta di ciò che la ricerca ha restituito.
- **Non** menzionare «Claude», «Claude Code», «AI-generated», «GPT», «Copilot» o qualsiasi nome di strumento/modello IA in messaggi di commit, descrizioni di PR, commenti di codice o documentazione.

## Funzionalità

- **Quindici sorgenti plug-in**: `arxiv`, `semantic_scholar`, `openalex`, `pubmed`, `acm` (limitato ad ACM via Crossref), `dblp`, `crossref` (generico), `openaire`, `europepmc`, `doaj`, `hal`, `core`, `springer` (richiede API key), `ieee` (API key o scraping opt-in), `scholar` (scraping opt-in). Ognuna vive sotto `sources/<name>/` dietro un adattatore `Fetcher`. Una whitelist di sedi di primo livello filtra i risultati su conferenze/riviste CS di punta + Nature/Science/PNAS per default; `--all-venues` la disattiva.
- **Modalità articolo singolo**: incolla un ID arXiv, URL arXiv, DOI, PMID o URL documento IEEE — ThesisAgents lo risolve tramite la sorgente giusta ed emette lo stesso bundle di esportazione. Utile per appunti di lettura e preparazione difesa.
- **Modalità PDF locale** (`--pdf <percorso>`): passa un PDF o una directory. Un estrattore euristico tira fuori **titolo, autori, anno, ID arXiv, DOI e l'abstract reale** dall'inizio di ciascun PDF (ancorato all'intestazione esplicita `Abstract` / `ABSTRACT` / `摘要`, non a un prefisso cieco). `--title` / `--authors` / `--year` / `--venue` / `--doi` / `--arxiv-id` sovrascrivono nel caso singolo PDF; in modalità directory vince l'estrazione per file — ogni articolo ha il proprio deck nominato con la sua chiave BibTeX.
- **Cinque esportatori**:
  - `.pptx` — 16:9 widescreen, numerato, tre livelli di rendering (leggero solo-abstract · enriched-flat · **stile tesi** con quadranti dei punti di dolore, KPI in evidenza, tabelle comparative di tecniche, tabelle risultati per RQ, sintesi dei contributi, osservazione centrale, limiti & lavori futuri, Q&A, bibliografia). Tutte le stringhe template sono i18n in **14 lingue**: English, 繁體中文, 简体中文, 日本語, Español, Français, Deutsch, 한국어, Português, Русский, Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia.
  - `.xlsx` — foglio Papers + foglio provenienza Query, URL / PDF con hyperlink, intestazione fissata, larghezze auto. La colonna 5 (**Source**) mostra il luogo di pubblicazione reale (es. «IEEE Access»); la colonna 6 (**Indexed via**) mostra quale fetcher ha restituito i metadati (es. «openalex»), così le due informazioni non si confondono.
  - `.md` — elenco completo sorgente / titolo / abstract.
  - `.bib` — chiavi di citazione senza collisioni, campi LaTeX-escapati.
  - `.json` — payload grezzo per tooling downstream.
  - **Identità visiva progettata** (non il look predefinito Calibri-on-white): tipografia per lingua (Inter per il Latin; Microsoft JhengHei UI / YaHei UI / Yu Gothic UI / Malgun Gothic / Nirmala UI per CJK + Hindi), geometria di accento programmatica (barra superiore su ogni slide di contenuto + banda sinistra sulla copertina), tabelle in stile accademico (griglia nera rimossa, regola navy nell'intestazione, divisori soft tra le righe, strisce alternate, allineamento verticale centrato, prima colonna in grassetto). Palette a 5 colori (navy / teal / grey / light / white) — il rosso è **vietato** come colore di testo; usa **grassetto + teal `#0E7490`** per enfasi.
  - **Modalità scura di default**. Si costruisce con la palette chiara e poi un post-pass cambia gli RGB di testo + riempimento + bordo cella in modalità scura (sfondo `#12151B`, testo `#E5E7EB`, teal più luminoso `#2DD4BF`). Pensato per proiettori OLED e sale poco illuminate. Per stampare o sale illuminate, usa `--light-mode` (CLI), togli la spunta a **Light mode** nella tab Deck della GUI, o passa `ExportOptions(dark_mode=False)` in Python.
- **Toolkit di editing PPT**: `thesisagents.exporters.pptx_edit` (inspect / update_slide / delete_slide / reorder_slides / add_slide) funziona su qualsiasi deck prodotto dall'esportatore, più gli strumenti MCP equivalenti `pptx_*` per consentire a un agente LLM di iterare su un deck già generato.
- **Server MCP**: 12 strumenti — `list_sources` (discovery), `search`, `fetch_paper`, `fetch_pdf_text`, `download_pdfs`, `export` e i cinque di editing `pptx_*`. Permette a qualsiasi LLM MCP-compatibile (Claude Code, Claude Desktop, Cursor, …) di pilotare l'intero workflow.
- **Due percorsi di arricchimento** per superare l'abstract verso un deck vero stile tesi:
  - **LLM-as-agent (nessuna API key)** — l'LLM chiamante legge il testo del PDF via `fetch_pdf_text`, scrive un riassunto strutturato in contesto e lo passa a `export`.
  - **Pipeline Python (`--enrich`)** — la CLI chiama direttamente l'API Anthropic; modello di default `claude-opus-4-7`.
- **Sicuro per default**: trasporto HTTP solo-HTTPS, rate limit per sorgente (token bucket), `defusedxml` per ogni payload XML, percorsi di export sicuri contro path-traversal, niente `eval` / `exec` / `pickle` su input utente. Scraping Scholar e IEEE disabilitato per default (opt-in via env var).

## Avvio rapido

```powershell
git clone <repo-url>
cd ThesisAgents
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Installazione con extras dev (include anche SDK MCP e deps intelligence)
pip install -e .[dev]
```

Cerca arXiv ed esporta deck + workbook + BibTeX (default per `--query`):

```powershell
py -m thesisagents --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

Recupera un singolo articolo per URL — default `.pptx + .bib` (`.xlsx` di una sola riga ha poco senso):

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

Renderizza il deck in italiano:

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --lang it --out .\exports\
```

Arricchimento via pipeline LLM (Python chiama Anthropic — richiede API key):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang it --out .\exports\
```

## Flag CLI

| Flag | Scopo |
|---|---|
| `--query` / `-q` | Parole chiave (obbligatorio salvo se c'è `--paper`). |
| `--paper` / `-p` | ID/URL arXiv, DOI, PMID o URL documento IEEE. Mutuamente esclusivo con `--query`. |
| `--source` / `-s` | Lista di sorgenti separate da virgola. Default `arxiv`. |
| `--max` / `-n` | Risultati max per sorgente (1..200). Default 25. |
| `--year-from` / `--year-to` | Filtro anno inclusivo. |
| `--export` / `-e` | Formati: qualsiasi sottoinsieme di `pptx,xlsx,md,bib,json,ris,csv,csl`. Default dipende dalla modalità (vedi sotto). |
| `--out` / `-o` | Directory di output. Default `./exports`. |
| `--filename-stem` | Sovrascrive lo stem generato. |
| `--no-abstract` | Omette contenuto dell'abstract negli export. |
| `--lang` / `-l` | Lingua deck: una su 14 — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. Default `en`. |
| `--enrich` | Scarica PDF + riassume con Anthropic. Richiede `ANTHROPIC_API_KEY` e l'extra `[intelligence]`. |
| `--lightweight` | Forza deck leggero anche con `ANTHROPIC_API_KEY` impostata. |
| `--llm-model` | Sovrascrive il modello di default `claude-opus-4-7`. |
| `--all-venues` | Disabilita la whitelist top-tier (default mantiene sedi CS di punta + Nature / Science / PNAS / CACM / LNCS). |
| `--paywall-threshold` | Frazione di risultati paywall che attiva la conferma. Default 0.30. |
| `--yes` | Salta il prompt paywall. |
| `--max-slides` | Tetto slide per articolo (default 25; 0 per illimitato). |
| `--quiet` | Sopprime la stampa per articolo. |

### Variabili d'ambiente

| Variabile | Usata da | Scopo |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | Auth LLM. Non serve per il percorso LLM-as-agent via MCP. |
| `THESISAGENTS_LLM_MODEL` | `--enrich` | Sovrascrive il default `claude-opus-4-7`. |
| `THESISAGENTS_S2_API_KEY` | Semantic Scholar | Rate limit più alto. Opzionale. |
| `THESISAGENTS_NCBI_API_KEY` | PubMed | Alza il limite anonimo NCBI (3/s) a 10/s. Opzionale. |
| `THESISAGENTS_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex | Mette le richieste nel polite pool di Crossref. |
| `THESISAGENTS_IEEE_API_KEY` | IEEE (via API) | API ufficiale IEEE Xplore; espone `pdf_url` per articoli coperti. |
| `THESISAGENTS_DISABLE_IEEE_SCRAPING` | IEEE (via scraping) | `=1` abilita scraping. Non serve se la API key è impostata. |
| `THESISAGENTS_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Token abbonato Crossref Plus (header Bearer). Opzionale. |
| `THESISAGENTS_SPRINGER_API_KEY` | Springer | Obbligatoria; chiave gratuita su <https://dev.springernature.com/>. Senza chiave il plugin viene saltato silenziosamente. |
| `THESISAGENTS_CHROME_PROFILE_DIR` | Scholar + IEEE + paywalled-PDF downloads | Persistent Chrome `--user-data-dir`. Set this and complete VPN / SSO once; subsequent runs inherit the cookies. |
| `THESISAGENTS_DISABLE_WEBRUNNER` | Scholar + IEEE + paywalled-PDF downloads | `=1` forces the httpx paths instead of driving real Chrome. For CI / Docker without a Chrome binary. |
| `THESISAGENTS_CORE_API_KEY` | OA resolver | Free key from <https://core.ac.uk/services/api>. Enables the CORE.ac.uk lookup step in the OA PDF resolver. |
| `THESISAGENTS_DISABLE_SCHOLAR_SCRAPING` | Google Scholar | `=1` abilita scraping. Default disabilitato — i ToS di Scholar lo vietano. |
| `THESISAGENTS_PDF_COOKIES_FILE` | Downloader PDF | `cookies.txt` formato Netscape. Default disabilitato. Usa solo con editori per cui hai diritti istituzionali. |
| `THESISAGENTS_LOG_LEVEL` | logger | `INFO` di default; `DEBUG` per trace verbose. |

Default: `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. Sempre sovrascrivibile con `--export` esplicito.

## Server MCP

Registra con Claude Code:

```powershell
claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp
```

Oppure modifica il file di configurazione:

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
| `list_sources` | Enumera ogni plugin + riporta quali sono abilitati nell'env corrente. Chiamare una volta prima di `search`. |
| `search` | Parole chiave → lista articoli. Accetta `top_tier_only`, `min_citations`; per default usa il mix completo senza API key. |
| `fetch_paper` | Identificatore arXiv / DOI / PMID / IEEE → articolo singolo. |
| `fetch_pdf_text` | Scarica un PDF, restituisce il testo estratto. **Il percorso MCP per «ho letto l'articolo».** |
| `download_pdfs` | Scarica in lotto i PDF di una lista articoli in `{out_dir}/pdfs/`. Restituisce risultati per articolo indicizzati per chiave BibTeX. |
| `export` | Lista articoli + formati → scrive `.pptx/.xlsx/.md/.bib/.json/.ris/.csv/.csl.json`. Accetta `summary` per articolo (rich thesis-style) e `max_slides_per_paper` (default 25). |
| `pptx_inspect` | Legge struttura slide / shape di un deck esistente. |
| `pptx_update_slide` | Sostituisce `title` / `body` / `meta` (per nome shape) o shape arbitrari per indice. |
| `pptx_delete_slide` | Rimuove una slide e la sua part relationship. |
| `pptx_reorder_slides` | Riordina le slide via `sldIdLst`. |
| `pptx_add_slide` | Aggiunge in coda o inserisce una nuova slide title / body / meta. |

Flusso LLM-as-agent (senza `ANTHROPIC_API_KEY` — l'LLM è l'agente):

```
1. (facoltativo) list_sources()                    # scopri i plugin abilitati
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (facoltativo) download_pdfs(papers, out_dir="./exports/...")  # persisti PDF
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # per articolo
5. (l'LLM legge il testo, produce un dict `summary` strutturato)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="it", formats=["pptx","bib"], ...)
```

Riferimento completo in [`docs/mcp.md`](docs/mcp.md).

## Struttura del progetto

```
ThesisAgents/
├── thesisagents/                 # pacchetto principale
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # client async solo-HTTPS, rate limit token bucket
│   ├── exporters/                   # pptx (stile tesi) · xlsx · bib · md · json · ris · csv · csl · pptx_edit · i18n
│   ├── intelligence/                # download PDF + riassuntore Anthropic ([intelligence] extra)
│   ├── mcp/                         # server FastMCP (12 strumenti)
│   ├── utils/                       # logging, path safety
│   ├── cli.py                       # CLI argparse
│   └── __main__.py
├── sources/                         # cartelle plugin: arxiv, semantic_scholar,
│                                    #   openalex, pubmed, acm, ieee, scholar,
│                                    #   dblp, crossref, openaire, springer, europepmc, doaj, hal, core
├── tests/                           # suite pytest + fixture registrati (no HTTP live)
├── docs/                            # Sphinx (14 alberi di lingua)
├── scripts/                         # script regen una tantum
└── pyproject.toml                   # ruff, bandit, build, extras opzionali
```

## Definition of Done

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r thesisagents/ sources/
```

Il flag `-c` di bandit è obbligatorio — senza, bandit ignora la configurazione skip del progetto. Quando tocchi l'esportatore pptx, esegui anche un controllo di overflow (vedi `CLAUDE.md` «Slide Deck Rules»).

## Licenza

Vedi `LICENSE`. L'API arXiv è usata secondo i suoi termini (<https://info.arxiv.org/help/api/tou.html>) — rispetta il limite soft di 1 richiesta ogni 3 secondi; il fetcher incluso lo impone già via token bucket.
