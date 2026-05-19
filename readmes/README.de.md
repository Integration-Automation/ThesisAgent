# AutoPaperToPPT

[![CI](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![Python](https://img.shields.io/pypi/pyversions/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/AutoPaperToPPT.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/autopapertoppt/badge/?version=latest)](https://autopapertoppt.readthedocs.io/en/latest/)

> **Sprachen**: [English](../README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · **Deutsch** · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **Dokumentation**: [autopapertoppt.readthedocs.io](https://autopapertoppt.readthedocs.io/en/latest/)

Stichwortgesteuerter Paper-Such-Assistent, der Ergebnisse von arXiv, Semantic Scholar, OpenAlex, PubMed, ACM (via Crossref), IEEE Xplore, DBLP, generischem Crossref, OpenAIRE, Springer Nature und Google Scholar abruft, in ein einheitliches Datensatzformat normalisiert und die deduplizierte Ergebnismenge als **Paper-Review PowerPoint im Thesis-Stil**, **Excel-Arbeitsmappe** und **BibTeX-Datei** exportiert — alles aus einem CLI-Aufruf oder einem MCP-Tool-Aufruf. Kann optional jedes Paper anreichern, indem es das PDF liest und eine strukturierte Zusammenfassung erstellt, entweder im Kontext (LLM-as-agent-Pfad) oder über die Anthropic-API (Python-Pipeline-Pfad).

## Für KI-Agenten, die dieses Projekt steuern

**Wenn Sie ein LLM (Claude Code, Cursor, Aider, Codex CLI, …) sind und diese README lesen, um herauszufinden, was zu tun ist — fangen Sie hier an.** Die gleichen Regeln sind in [`AGENTS.md`](AGENTS.md) (agentenübergreifender Spiegel) und [`CLAUDE.md`](CLAUDE.md) (kanonische Referenz) fixiert; lesen Sie diese vor nicht-trivialen Änderungen.

### Was der Benutzer wirklich will

Das Standard-Ergebnis ist **ein angereichertes `.pptx` im Thesis-Stil pro Paper**, nicht das auf das Abstract beschränkte Light-Deck, das die CLI standardmäßig erzeugt. Der Light-Output ist ein Zwischenartefakt — Ihre Aufgabe ist es, ihn aufzuwerten.

### Entscheidungsbaum

1. Ist `ANTHROPIC_API_KEY` in der Umgebung gesetzt? → führen Sie einfach die CLI aus; sie reichert über die Anthropic-API automatisch an. Fertig.
2. Kein Schlüssel, aber Sie (ein LLM) steuern die Session → **Sie erzeugen die angereicherte Zusammenfassung selbst**. Lesen Sie jedes PDF, verfassen Sie von Hand ein `PaperSummary` mit Rich-Tier-Feldern (`pain_points`, `research_question`, `contributions_detailed`, `headline_metrics`, `technique_table`, `method_sections`, `evaluation_sections`, `system_flow`, `research_questions`, `rq_results`, `core_observation`, `limitations`, `future_work`), legen Sie ein `scripts/regen_<query>.py` an und führen Sie es aus. **Sagen Sie dem Benutzer nicht, er solle den API-Schlüssel setzen** — Sie sind das LLM, das die Zusammenfassung geschrieben hätte.
3. Kein LLM beteiligt (CI / cron / unbeaufsichtigt) → Light-Output ist akzeptabel.

### MCP-Workflow in 6 Schritten

```
1. (optional) list_sources()                              # welche Plugins aktiv sind
2. search(keywords, sources, top_tier_only=true, ...)
3. (optional) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # pro Paper
5. (Sie lesen jedes PDF und erzeugen ein strukturiertes Summary-Dict)
6. export(papers=[{...paper, "summary": {...}}], language="de", ...)
```

Alle elf MCP-Tools (inklusive `list_sources`, `download_pdfs`, `pptx_inspect` / `pptx_update_slide` / `pptx_add_slide` / etc.) sind in [`docs/mcp.md`](docs/mcp.md) dokumentiert.

### Pflicht: URL / DOI-Verifikation vor Auslieferung

Verlags-URL-Pfade **lassen sich nicht raten** — AAAI nutzt numerische IDs (`v40i5.37389`), IEEE nutzt eine opake `arnumber`, ACM nutzt opake DOIs. Wenn Sie ein `Paper` von Hand verfassen, **kopieren Sie `url` / `doi` / `arxiv_id` wortgetreu aus dem xlsx, das diese Suche erzeugt hat** — niemals aus dem Gedächtnis, niemals aus dem Titel konstruiert.

Das xlsx wird unter `exports/<run>/<slug>-<timestamp>.xlsx` mit Spalte 7 = DOI, Spalte 8 = URL geschrieben. Auditieren Sie Ihr Regen-Script am Ende:

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

Zwei in der Produktion so entdeckte Fabrikationen: falsche AAAI-Ausgabe (`v39i23.34521` vs. echte `v39i22.34537`) und erfundener Autor-Slug-Pfad (`view/fang2026` statt `v40i5.37389`).

### Vorbild

[`scripts/regen_llm_security_batch.py`](scripts/regen_llm_security_batch.py) liefert 8 nach diesem Verfahren handgeschriebene angereicherte Zusammenfassungen. Nutzen Sie es als Vorlage für jede Multi-Paper-Suche. Das zh-tw-Pendant liegt unter [`scripts/regen_llm_security_batch_zh_tw.py`](scripts/regen_llm_security_batch_zh_tw.py).

### Verbote

- **Nicht** eine Multi-Paper-Suche damit beenden, dem Benutzer zu sagen „setze `ANTHROPIC_API_KEY` für ein angereichertes Deck" — Sie sind das LLM, das die Zusammenfassungen schreiben könnte.
- **Nicht** das per-Paper-Light-`.pptx` als das Ergebnis behandeln.
- **Nicht** stoppen, wenn `download_pdfs` „N PDFs gespeichert" meldet — das ist der Beginn der Rich-Authoring-Phase, nicht das Ende.
- **Nicht** Zahlen, RQs, Beiträge oder Einschränkungen erfinden, die nicht im Paper stehen.
- **Nicht** URLs / DOIs / arXiv-IDs fabrizieren — siehe obige Regel.
- **Nicht** irrelevante Downloads im Lauf-Verzeichnis liegen lassen. Stichwortsuche zieht manchmal themenfremde Paper heran (eine Abfrage „Claude code" lieferte ein Viterbi-Decoder-Paper; „LLM code review" lieferte einen Object-Detection-Review). Nach Klassifizierung als themenfremd löschen Sie deren `pdfs/<key>.pdf` und das leichte `<key>.pptx`; das aggregierte xlsx / bib bleibt als ehrliches Protokoll der Suche erhalten.
- **Nicht** „Claude", „Claude Code", „AI-generated", „GPT", „Copilot" oder andere KI-Tool-/Modellnamen in Commit-Nachrichten, PR-Beschreibungen, Code-Kommentaren oder Dokumentation erwähnen.

## Funktionen

- **Elf einsteckbare Quellen**: `arxiv`, `semantic_scholar`, `openalex`, `pubmed`, `acm` (ACM-beschränkt via Crossref), `dblp`, `crossref` (generisch), `openaire`, `springer` (API-Schlüssel erforderlich), `ieee` (API-Schlüssel oder Scraping-Opt-In), `scholar` (Scraping-Opt-In). Jede liegt unter `sources/<name>/` hinter einem `Fetcher`-Adapter. Eine Whitelist erstklassiger Venues filtert die Ergebnisse standardmäßig auf führende CS-Konferenzen/Zeitschriften plus Nature/Science/PNAS; `--all-venues` deaktiviert sie.
- **Einzel-Paper-Modus**: fügen Sie eine arXiv-ID, arXiv-URL, DOI, PMID oder eine IEEE-Dokument-URL ein — AutoPaperToPPT löst sie über die passende Quelle auf und erzeugt dasselbe Export-Bundle. Nützlich für Leseskizzen und Verteidigungsvorbereitung.
- **Lokaler PDF-Modus** (`--pdf <pfad>`): geben Sie ein PDF oder ein Verzeichnis an. Ein heuristischer Extractor zieht **Titel, Autoren, Jahr, arXiv-ID, DOI und das echte Abstract** direkt aus dem Vorspann jedes PDFs (verankert am expliziten `Abstract` / `ABSTRACT` / `摘要`-Header, nicht an einem blinden Präfix). `--title` / `--authors` / `--year` / `--venue` / `--doi` / `--arxiv-id` überschreiben bei einem Einzel-PDF-Aufruf; im Verzeichnismodus gewinnt die per-File-Extraktion, sodass jedes Paper ein eigenes Deck mit seinem BibTeX-Schlüssel als Namen erhält.
- **Fünf Exporter**:
  - `.pptx` — 16:9-Breitformat, mit Seitenzahlen, drei Rendering-Stufen (light nur-Abstract · enriched-flat · **Thesis-Stil** mit Pain-Point-Quadranten, KPI-Callouts, Technik-Vergleichstabellen, RQ-spezifischen Ergebnistabellen, Beitragszusammenfassung, Kernbeobachtung, Einschränkungen & Künftige Arbeiten, Q&A, Literatur). Alle Template-Strings sind in **14 Sprachen** i18n: English, 繁體中文, 简体中文, 日本語, Español, Français, Deutsch, 한국어, Português, Русский, Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia.
  - `.xlsx` — Papers-Blatt + Query-Herkunftsblatt, URL / PDF verlinkt, fixierte Kopfzeile, automatische Spaltenbreiten. Spalte 5 (**Source**) zeigt den realen Publikationsort (z. B. „IEEE Access"); Spalte 6 (**Indexed via**) zeigt, welcher Fetcher die Metadaten geliefert hat (z. B. „openalex"), sodass die beiden Informationen nicht verwechselt werden.
  - `.md` — vollständige Quelle / Titel / Abstract-Liste.
  - `.bib` — kollisionsfreie Zitierschlüssel, LaTeX-escapte Felder.
  - `.json` — Rohpayload für nachgelagertes Tooling.
- **PPT-Edit-Toolkit**: `autopapertoppt.exporters.pptx_edit` (inspect / update_slide / delete_slide / reorder_slides / add_slide) arbeitet mit jedem vom Exporter erzeugten Deck, plus die äquivalenten `pptx_*` MCP-Tools, mit denen ein LLM-Agent über ein erzeugtes Deck iterieren kann.
- **MCP-Server**: 11 Tools — `list_sources` (Discovery), `search`, `fetch_paper`, `fetch_pdf_text`, `download_pdfs`, `export` und die fünf `pptx_*`-Edit-Tools. Erlaubt jedem MCP-fähigen LLM (Claude Code, Claude Desktop, Cursor, …) den gesamten Workflow zu steuern.
- **Zwei Anreicherungspfade**, um über das Abstract hinaus zu einem echten Thesis-Stil-Deck zu kommen:
  - **LLM-as-agent (kein API-Schlüssel)** — das aufrufende LLM liest den PDF-Text via `fetch_pdf_text`, schreibt eine strukturierte Zusammenfassung im Kontext und übergibt sie an `export`.
  - **Python-Pipeline (`--enrich`)** — die CLI ruft Anthropic selbst auf; Standardmodell `claude-opus-4-7`.
- **Sicher per Default**: HTTPS-only HTTP-Transport, Rate-Limit pro Quelle (Token Bucket), `defusedxml` für jedes XML-Payload, path-traversal-sichere Export-Pfade, kein `eval` / `exec` / `pickle` auf Nutzereingaben. Scholar- und IEEE-Scraping per Default deaktiviert (Opt-In über Umgebungsvariable).

## Schnellstart

```powershell
git clone <repo-url>
cd AutoPaperToPPT
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Installation mit dev-Extras (zieht auch MCP SDK und intelligence-Deps)
pip install -e .[dev]
```

arXiv durchsuchen und Deck + Workbook + BibTeX exportieren (Default für `--query`):

```powershell
py -m autopapertoppt --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

Einzelnes Paper per URL holen — Default `.pptx + .bib` (ein einzeiliges `.xlsx` ist wenig sinnvoll):

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

Deck auf Deutsch rendern:

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --lang de --out .\exports\
```

LLM-Pipeline-Anreicherung (Python ruft Anthropic — API-Schlüssel erforderlich):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang de --out .\exports\
```

## CLI-Flags

| Flag | Zweck |
|---|---|
| `--query` / `-q` | Stichwörter (Pflicht, außer wenn `--paper`). |
| `--paper` / `-p` | arXiv-ID / URL, DOI, PMID oder IEEE-Dokument-URL. Exklusiv zu `--query`. |
| `--source` / `-s` | Komma-getrennte Quellenliste. Default `arxiv`. |
| `--max` / `-n` | Max. Ergebnisse pro Quelle (1..200). Default 25. |
| `--year-from` / `--year-to` | Jahresfilter inklusive. |
| `--export` / `-e` | Formate: beliebige aus `pptx,xlsx,md,bib,json`. Default je nach Modus (siehe unten). |
| `--out` / `-o` | Ausgabeverzeichnis. Default `./exports`. |
| `--filename-stem` | Überschreibt den generierten Datei-Stem. |
| `--no-abstract` | Lässt Abstract-Inhalt in Exporten weg. |
| `--lang` / `-l` | Deck-Sprache: eine aus 14 — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. Default `en`. |
| `--enrich` | PDF herunterladen + Anthropic-Zusammenfassung. Benötigt `ANTHROPIC_API_KEY` und das Extra `[intelligence]`. |
| `--lightweight` | Erzwingt das Light-Deck auch wenn `ANTHROPIC_API_KEY` gesetzt ist. |
| `--llm-model` | Überschreibt das Standardmodell `claude-opus-4-7`. |
| `--all-venues` | Deaktiviert die Top-Tier-Whitelist (Default behält führende CS-Venues + Nature / Science / PNAS / CACM / LNCS). |
| `--paywall-threshold` | Anteil paywall-belasteter Ergebnisse, der die Bestätigungsabfrage auslöst. Default 0.30. |
| `--yes` | Überspringt die Paywall-Abfrage. |
| `--max-slides` | Folien-Obergrenze pro Paper (Default 25; 0 für unbegrenzt). |
| `--quiet` | Unterdrückt die Per-Paper-Ausgabe. |

### Umgebungsvariablen

| Variable | Verwendet von | Zweck |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | LLM-Auth. Nicht nötig für den LLM-as-agent-Pfad über MCP. |
| `AUTOPAPERTOPPT_LLM_MODEL` | `--enrich` | Überschreibt das Standardmodell `claude-opus-4-7`. |
| `AUTOPAPERTOPPT_S2_API_KEY` | Semantic Scholar | Höheres Rate-Limit. Optional. |
| `AUTOPAPERTOPPT_NCBI_API_KEY` | PubMed | Erhöht NCBIs anonymes Limit (3/s) auf 10/s. Optional. |
| `AUTOPAPERTOPPT_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex | Setzt Anfragen in Crossrefs „Polite Pool". |
| `AUTOPAPERTOPPT_IEEE_API_KEY` | IEEE (API-Pfad) | Offizielle IEEE-Xplore-API; legt `pdf_url` für abgedeckte Paper offen. |
| `AUTOPAPERTOPPT_ENABLE_IEEE_SCRAPING` | IEEE (Scraping-Pfad) | `=1` aktiviert Scraping. Nicht nötig, wenn der API-Schlüssel gesetzt ist. |
| `AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Crossref-Plus-Abonnement-Token (Bearer-Header). Optional. |
| `AUTOPAPERTOPPT_SPRINGER_API_KEY` | Springer | Pflicht; kostenloser Schlüssel über <https://dev.springernature.com/>. Ohne Schlüssel wird das Plugin still übersprungen. |
| `AUTOPAPERTOPPT_ENABLE_SCHOLAR_SCRAPING` | Google Scholar | `=1` aktiviert Scraping. Default aus — Scholars ToS verbietet Scraping. |
| `AUTOPAPERTOPPT_PDF_COOKIES_FILE` | PDF-Downloader | `cookies.txt` im Netscape-Format. Default aus. Nur bei Verlagen verwenden, für die Sie institutionelle Zugriffsrechte haben. |
| `AUTOPAPERTOPPT_LOG_LEVEL` | Logger | `INFO` als Default; `DEBUG` für verbose Traces. |

Defaults: `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. Immer mit explizitem `--export` überschreibbar.

## MCP-Server

In Claude Code registrieren:

```powershell
claude mcp add autopapertoppt -- ".venv\Scripts\python.exe" -m autopapertoppt.mcp
```

Oder die Settings-Datei manuell bearbeiten:

```json
{
  "mcpServers": {
    "autopapertoppt": {
      "command": ".venv\\Scripts\\python.exe",
      "args": ["-m", "autopapertoppt.mcp"]
    }
  }
}
```

Tools:

| Tool | Zweck |
|---|---|
| `list_sources` | Listet jedes Plugin auf + meldet, welche im aktuellen Env aktiv sind. Vor `search` einmal aufrufen. |
| `search` | Stichwörter → Paper-Liste. Akzeptiert `top_tier_only`, `min_citations`; Default ist die volle API-Key-freie Quellenmischung. |
| `fetch_paper` | arXiv / DOI / PMID / IEEE-Identifier → einzelnes Paper. |
| `fetch_pdf_text` | Lädt ein PDF, gibt extrahierten Body-Text zurück. **Der MCP-Pfad zum „Paper gelesen".** |
| `download_pdfs` | Lädt PDFs einer Paper-Liste gesammelt nach `{out_dir}/pdfs/`. Liefert Per-Paper-Ergebnisse, indiziert nach BibTeX-Schlüssel. |
| `export` | Paper-Liste + Formate → schreibt `.pptx/.xlsx/.md/.bib/.json`. Akzeptiert ein `summary`-Feld pro Paper für das angereicherte Thesis-Stil-Schema sowie `max_slides_per_paper` (Default 25). |
| `pptx_inspect` | Liest Slide- / Shape-Struktur eines vorhandenen Decks. |
| `pptx_update_slide` | Ersetzt `title` / `body` / `meta` (über Shape-Name) oder beliebige Shapes nach Index. |
| `pptx_delete_slide` | Entfernt eine Folie und ihre Part-Relationship. |
| `pptx_reorder_slides` | Sortiert Folien um über `sldIdLst`. |
| `pptx_add_slide` | Hängt an oder fügt an Position eine neue title / body / meta-Folie ein. |

LLM-as-agent-Flow (kein `ANTHROPIC_API_KEY` nötig — das LLM ist der Agent):

```
1. (optional) list_sources()                       # aktive Plugins entdecken
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (optional) download_pdfs(papers, out_dir="./exports/...")  # PDFs persistieren
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # pro Paper
5. (LLM liest den Text, erzeugt ein strukturiertes `summary`-Dict)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="de", formats=["pptx","bib"], ...)
```

Vollständige Referenz in [`docs/mcp.md`](docs/mcp.md).

## Projektstruktur

```
AutoPaperToPPT/
├── autopapertoppt/                 # Hauptpaket
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # HTTPS-only async client, token-bucket Rate-Limit
│   ├── exporters/                   # pptx (Thesis-Stil) · xlsx · bib · md · json · pptx_edit · i18n
│   ├── intelligence/                # PDF-Download + Anthropic-Summariser ([intelligence] extra)
│   ├── mcp/                         # FastMCP-Server (11 Tools)
│   ├── utils/                       # Logging, Path Safety
│   ├── cli.py                       # argparse CLI
│   └── __main__.py
├── sources/                         # Plugin-Verzeichnisse: arxiv, semantic_scholar,
│                                    #   openalex, pubmed, acm, ieee, scholar,
│                                    #   dblp, crossref, openaire, springer
├── tests/                           # pytest-Suite + aufgezeichnete Fixtures (kein Live-HTTP)
├── docs/                            # Sphinx (14 Sprachbäume)
├── scripts/                         # Einmalige Regen-Skripte
└── pyproject.toml                   # ruff, bandit, build, Extras
```

## Definition of Done

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r autopapertoppt/ sources/
```

Das `-c`-Flag bei bandit ist obligatorisch — ohne es ignoriert bandit die Skip-Konfiguration des Projekts. Beim Bearbeiten des pptx-Exporters auch eine Overflow-Prüfung laufen lassen (siehe `CLAUDE.md` „Slide Deck Rules").

## Lizenz

Siehe `LICENSE`. Die arXiv-API wird unter ihren Nutzungsbedingungen verwendet (<https://info.arxiv.org/help/api/tou.html>) — bitte das Soft-Limit von 1 Anfrage pro 3 Sekunden beachten; der mitgelieferte Fetcher erzwingt diese Rate bereits über sein Token Bucket.
