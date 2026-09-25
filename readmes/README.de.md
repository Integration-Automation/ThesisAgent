# ThesisAgents

[![CI](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![Python](https://img.shields.io/pypi/pyversions/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/ThesisAgents.svg)](https://github.com/Integration-Automation/ThesisAgents/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/thesisagents/badge/?version=latest)](https://thesisagents.readthedocs.io/en/latest/)

> **Sprachen**: [English](../README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · **Deutsch** · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **Dokumentation**: [thesisagents.readthedocs.io](https://thesisagents.readthedocs.io/en/latest/)

Ein schlagwortgesteuerter Assistent für die Paper-Suche, der Ergebnisse von
arXiv, Semantic Scholar, OpenAlex, PubMed, ACM (über Crossref), IEEE Xplore,
DBLP, generischem Crossref, OpenAIRE, Springer Nature, Europe PMC, DOAJ,
HAL, CORE und Google Scholar abruft,
sie in ein einheitliches Datensatzformat normalisiert und die deduplizierte
Menge als **PowerPoint-Foliensatz im Thesis-Stil**, **Excel-Arbeitsmappe**
und **BibTeX-Datei** exportiert — alles aus einem einzigen CLI-Aufruf oder
einem einzigen MCP-Tool-Aufruf. Optional reichert er jedes Paper an, indem er
dessen PDF liest und eine strukturierte Zusammenfassung pro Paper erzeugt,
entweder im Kontext (LLM-as-agent-Ablauf) oder über die Anthropic-API
(Python-Pipeline-Ablauf).

## Für KI-Agenten, die dieses Projekt steuern

**Wenn du ein LLM bist (Claude Code, Cursor, Aider, Codex CLI, …) und diese
README liest, um herauszufinden, was zu tun ist — beginne hier.** Alles
Folgende ist auch in [`AGENTS.md`](../AGENTS.md) (agentübergreifendes Spiegelbild)
und [`CLAUDE.md`](../CLAUDE.md) (kanonische Referenz) verankert; lies diese, bevor
du nicht-triviale Änderungen vornimmst.

### Was der Nutzer tatsächlich will

Das Standard-Deliverable ist **ein reichhaltiges `.pptx` im Thesis-Stil pro
Paper**, nicht der leichtgewichtige, nur auf dem Abstract basierende Foliensatz,
den die CLI standardmäßig erzeugt. Der leichtgewichtige Output ist ein
Zwischenartefakt — deine Aufgabe ist es, ihn aufzuwerten.

### Entscheidungsbaum

1. Ist `ANTHROPIC_API_KEY` in der Umgebung gesetzt? → Führe einfach die CLI
   aus; sie reichert automatisch über die Anthropic-API an. Du bist fertig.
2. Kein Schlüssel, aber du (ein LLM) steuerst die Sitzung → **du erstellst die
   reichhaltige Zusammenfassung selbst**. Lies jedes PDF, verfasse von Hand
   eine `PaperSummary` mit den Feldern der reichhaltigen Stufe (`pain_points`,
   `research_question`, `contributions_detailed`, `headline_metrics`,
   `technique_table`, `method_sections`, `evaluation_sections`,
   `system_flow`, `research_questions`, `rq_results`,
   `core_observation`, `limitations`, `future_work`), lege ein
   `scripts/regen_<query>.py` ab und führe es aus. **Sage dem Nutzer nicht, er
   solle den API-Schlüssel setzen** — du bist das LLM, das die Zusammenfassung
   geschrieben hätte.
3. Kein LLM in der Schleife (CI / Cron / unbeaufsichtigt) → leichtgewichtig ist
   akzeptabel.

### 6-Schritt-MCP-Workflow

```
1. (optional) list_sources()                              # see which plugins are enabled
2. search(keywords, sources, top_tier_only=true, ...)
3. (optional) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # per paper
5. (you read each PDF and produce a structured summary dict)
6. export(papers=[{...paper, "summary": {...}}], language="zh-tw", ...)
```

Alle dreizehn MCP-Tools (einschließlich `list_sources`, `list_exports`,
`download_pdfs`, `pptx_inspect` / `pptx_review` / `pptx_update_slide` /
`pptx_add_slide` / etc.) sind
in [`docs/mcp.md`](../docs/mcp.md) dokumentiert.

### Pflicht: URL-/DOI-Verifikation vor der Auslieferung

Verlags-URL-Pfade **können nicht erraten werden** — AAAI verwendet numerische
IDs (`v40i5.37389`), IEEE verwendet eine undurchsichtige `arnumber`, ACM
verwendet undurchsichtige DOIs. Wenn du ein `Paper` von Hand verfasst, **kopiere
`url` / `doi` / `arxiv_id` wortwörtlich aus der Such-xlsx, die diesen Lauf
erzeugt hat** — niemals aus dem Gedächtnis, niemals aus dem Titel konstruiert.

Die xlsx wird nach `exports/<run>/<slug>-<timestamp>.xlsx` geschrieben, mit
Spalte 7 = DOI, Spalte 8 = URL. Prüfe dein Regen-Skript, wenn du fertig bist:

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

Zwei auf diese Weise in der Produktion entdeckte Fabrikationen: falscher
AAAI-Band (`v39i23.34521` statt echt `v39i22.34537`) und erfundener
Autoren-Slug-Pfad (`view/fang2026` statt `v40i5.37389`).

### Pflicht: irrelevante Downloads vor der Auslieferung aussortieren

Der Abgleich der Suchschlüsselwörter ist schlagwortbasiert, daher rutschen
themenfremde Paper mit hinein: Eine Suche nach „Claude code" lieferte ein Paper
über einen Viterbi-Decoder, weil beide „code" enthalten; „LLM code review"
traf ein Literaturüberblick zur Objekterkennung. Sobald du die Abstracts
gelesen und ein Paper als themenfremd für die tatsächliche Absicht des Nutzers
eingestuft hast, bereinige das Lauf-Verzeichnis:

```python
from pathlib import Path
run = Path("exports/<run>")
irrelevant_keys = ("key-of-off-topic-paper-1", "key-of-off-topic-paper-2")
for key in irrelevant_keys:
    for path in (run / "pdfs" / f"{key}.pdf", run / f"{key}.pptx"):
        if path.exists():
            path.unlink()
```

Lösche `exports/<run>/pdfs/<key>.pdf` + `exports/<run>/<key>.pptx`.
**Behalte** die aggregierte `<slug>-<timestamp>.xlsx` / `.bib` — das ist die
ehrliche Aufzeichnung dessen, was die Suche zurückgegeben hat. Grenzfälle
erhalten eine reichhaltige Zusammenfassung; besser zu viel aufnehmen als
stillschweigend einen möglichen Treffer fallen zu lassen.

### Durchgearbeitetes Beispiel

[`scripts/regen_fang2026.py`](../scripts/regen_fang2026.py) liefert eine von Hand
verfasste reichhaltige Zusammenfassung, die genau auf diese Weise erstellt wurde
(einzelnes Paper, reichhaltige Stufe, zh-tw, jedes reichhaltige Feld befüllt).
Eine Suche über mehrere Paper folgt derselben Form mit einem
`Paper(...summary=PaperSummary(...))`-Eintrag pro Paper im
`PaperCollection`-Tupel.

### Was du NICHT tun solltest

- **Beende** eine Suche über mehrere Paper **nicht**, indem du dem Nutzer sagst,
  er solle `ANTHROPIC_API_KEY` „für einen reichhaltigen Foliensatz" setzen — du
  bist das LLM, das die Zusammenfassungen hätte schreiben können.
- **Behandle** das leichtgewichtige `.pptx` pro Paper **nicht** als das
  Deliverable.
- **Höre nicht auf**, nachdem `download_pdfs` N gespeicherte PDFs meldet — das
  ist der Beginn der reichhaltigen Verfassungsphase, nicht das Ende.
- **Erfinde keine** Zahlen, RQs, Beiträge oder Einschränkungen, die nicht im
  Paper stehen.
- **Fabriziere keine** URLs / DOIs / arXiv-IDs — siehe die Regel oben.
- **Lasse keine** irrelevanten Downloads im Lauf-Verzeichnis. Treffer der
  Schlagwortsuche können themenfremde Paper einschließen (eine Suche nach
  „Claude code" zog ein Viterbi-Decoder-Paper herein; „LLM code review" zog
  einen Literaturüberblick zur Objekterkennung herein). Nachdem du Paper als
  themenfremd eingestuft hast, lösche deren `pdfs/<key>.pdf` und
  leichtgewichtige `<key>.pptx`; behalte die aggregierte xlsx / bib als
  ehrliche Aufzeichnung dessen, was die Suche zurückgegeben hat.
- **Erwähne** „Claude", „Claude Code", „AI-generated", „GPT", „Copilot" oder
  einen anderen KI-Tool-/Modellnamen **nicht** in Commit-Nachrichten,
  PR-Beschreibungen, Code-Kommentaren oder Dokumentation.

## Funktionen

- **Fünfzehn einsteckbare Quellen**: `arxiv`, `semantic_scholar`, `openalex`,
  `pubmed`, `acm` (Crossref-begrenzt), `dblp`, `crossref` (unbegrenzt),
  `openaire`, `springer` (benötigt API-Schlüssel), `europepmc` (offen, kein
  Schlüssel — Biowissenschaften + Preprints + Landwirtschaft), `doaj` (offen,
  kein Schlüssel — Open-Access-Zeitschriften, meist mit direktem PDF-Link),
  `hal` (offen, kein Schlüssel — Frankreichs CS-/Mathe-/Physik-Archiv mit
  Volltext-PDFs), `core` (benötigt kostenlosen API-Schlüssel — größter
  Open-Access-Aggregator, 250 Mio.+ Werke), `ieee` (standardmäßig aktiv über
  sichtbares Chrome; API-Schlüssel fügt die offizielle Xplore-API hinzu),
  `scholar` (standardmäßig aktiv über sichtbares Chrome). Jede lebt in
  `sources/<name>/` hinter einem `Fetcher`-Adapter. Übergib `--top-tier-only`,
  um die Ergebnisse auf führende CS-Konferenzen/-Zeitschriften plus
  Nature/Science/PNAS zu filtern. Die Standardsuche behält alle Publikationsorte.
- **Einzel-Paper-Modus**: Füge eine arXiv-ID, arXiv-URL, DOI, PMID oder
  IEEE-Dokument-URL ein — ThesisAgents löst sie über die richtige Quelle auf
  und erzeugt dasselbe Export-Bündel. Nützlich für Paper-Lesenotizen und die
  Vorbereitung der Thesis-Verteidigung.
- **Lokaler PDF-Modus** (`--pdf <path>`): Übergib ein PDF oder ein Verzeichnis.
  Ein heuristischer Extraktor zieht **Titel, Autoren, Jahr, arXiv-ID, DOI und
  das echte Abstract** direkt aus dem Vorspann jedes PDFs (verankert am
  expliziten `Abstract` / `ABSTRACT` / `摘要`-Header, nicht an einem blinden
  Präfix). `--title` / `--authors` / `--year` / `--venue` / `--doi` /
  `--arxiv-id` überschreiben bei einem Einzel-PDF-Aufruf; bei einem Verzeichnis
  gewinnt die datei-weise Extraktion, sodass jedes Paper seinen eigenen, nach
  seinem BibTeX-Schlüssel benannten Foliensatz erhält.
- **Acht Exporter**:
  - `.pptx` — 16:9-Breitbild, mit Seitenzahlen, drei Rendering-Stufen
    (leichtgewichtig nur Abstract · angereichert-flach · **Thesis-Stil** mit
    Pain-Point-Quadranten, KPI-Callouts, Technik-Vergleichstabellen,
    Ergebnistabellen pro RQ, Beitragszusammenfassung, Kernbeobachtung,
    Einschränkungen & zukünftige Arbeit, Q&A, Referenzen). Alle
    Vorlagentexte sind über **14 Sprachen** i18n-lokalisiert: English, 繁體中文,
    简体中文, 日本語, Español, Français, Deutsch, 한국어, Português, Русский,
    Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia.
  - **Visuelle Identität des gestalteten Foliensatzes** (nicht der
    Standard-Look mit Calibri auf Weiß): sprachspezifische Typografie (Inter
    für Latein, Microsoft JhengHei UI / YaHei UI / Yu Gothic UI / Malgun Gothic
    / Nirmala UI für CJK + Hindi), programmatische Akzentgeometrie
    (Akzentbalken oben auf jeder Inhaltsfolie + linkes Band auf dem Deckblatt),
    Tabellenformatierung im akademischen Stil (Standardraster entfernt,
    marineblaue Kopfzeilenlinie, weiche Zwischenzeilentrenner, abwechselnder
    Zeilenstreifen, vertikal mittige Ausrichtung, fette Zeilenbeschriftungen)
    und eine Fünf-Farben-Paletten-Disziplin (Marineblau / Petrol / Grau /
    Hell / Weiß), wobei Rot für Text **verboten** ist (verwende stattdessen
    fett + Petrol `#0E7490` zur Betonung).
  - **Der Hell-Modus ist der Standard-Rendering-Pfad.** Übergib `--dark-mode`,
    aktiviere **Dark mode** im GUI-Tab „Deck" oder setze
    `ExportOptions(dark_mode=True)`, um den Dunkel-Nachlauf anzuwenden
    (Folienhintergrund `#12151B`, Fließtext `#E5E7EB`).
  - `.xlsx` — Papers-Blatt + Blatt zur Query-Provenienz, verlinkte URL /
    PDF, fixierte Kopfzeile, automatische Spaltenbreiten. Spalte 5 (**Source**)
    zeigt den echten Publikationsort (z. B. „IEEE Access"); Spalte 6
    (**Indexed via**) zeigt, welcher Fetcher die Metadaten zurückgegeben hat
    (z. B. „openalex"), sodass die beiden Informationen niemals kollidieren.
  - `.md` — vollständige Liste aus Quelle / Titel / Abstract.
  - `.bib` — kollisionsfreie Zitierschlüssel, LaTeX-escapte Felder.
  - `.json` — Rohdaten für nachgelagerte Tools.
  - `.ris` — RIS-Austauschformat, das von Zotero / Mendeley / EndNote /
    RefWorks importiert wird (das BibTeX-Pendant für Nicht-LaTeX-Literaturverwaltungen).
  - `.csv` — flache Tabelle mit einer Zeile pro Paper für Tabellenkalkulationen
    / schnelles Grep-Triage (RFC-4180-Quoting, sodass Kommas in Titeln niemals
    Spalten verschieben).
  - `.csl.json` — CSL-JSON für Pandoc / citeproc; rendere eine Bibliografie in
    jedem CSL-Stil (APA, IEEE, Nature, …). Die Erweiterung `.csl.json` hält es
    vom einfachen `.json`-Dump getrennt.
- **PPT-Bearbeitungs-Toolkit**: `thesisagents.exporters.pptx_edit`
  (inspect / update_slide / delete_slide / reorder_slides / add_slide)
  funktioniert mit jedem Foliensatz, den der Exporter erzeugt, plus den
  äquivalenten `pptx_*`-MCP-Tools, sodass ein LLM-Agent an einem erzeugten
  Foliensatz iterieren kann.
- **MCP-Server**: 13 Tools — `list_sources` + `list_exports`
  (Discovery), `search`, `fetch_paper`, `fetch_pdf_text`,
  `download_pdfs`, `export` und die sechs `pptx_*`-Deck-Tools
  (`inspect`, `review`, `update_slide`, `delete_slide`,
  `reorder_slides`, `add_slide`). Lässt jedes
  MCP-fähige LLM
  (Claude Code, Claude Desktop, Cursor, …) den gesamten Workflow steuern.
- **Zwei Anreicherungspfade**, um über das Abstract hinaus zu einem echten
  Foliensatz im Thesis-Stil zu gelangen:
  - **LLM-as-agent (kein API-Schlüssel)** — das aufrufende LLM liest den
    PDF-Fließtext über `fetch_pdf_text`, schreibt eine strukturierte
    Zusammenfassung im Kontext und übergibt sie an `export`.
  - **Python-Pipeline (`--enrich`)** — die CLI ruft die API von Anthropic
    selbst auf; Standardmodell `claude-opus-4-7`.
- **Sichtbare-Chrome-Verlagsabläufe**: Scholar-SERP, IEEE `/rest/search` und
  jeder Download eines kostenpflichtigen PDFs (ieeexplore / dl.acm / link.springer
  / sciencedirect / wiley / oup / nature / science / …) laufen in einer echten,
  sichtbaren Chrome-Sitzung über `selenium`. Der Nutzer löst Captcha /
  vervollständigt SSO im Live-Fenster einmal; `THESISAGENTS_CHROME_PROFILE_DIR`
  behält die Cookies über Läufe hinweg bei.
- **LLM-as-agent-Ablauf**: MCP-Tools bieten Suche, PDF-Download und
  Textextraktion. `scripts/regen_*.py` enthält reproduzierbare Beispiele für das
  händische Verfassen einer reichhaltigen `PaperSummary` pro Paper.
- **OA-PDF-Resolver**: Nach der Deduplizierung durchläuft jedes Paper ohne
  `pdf_url` Unpaywall → S2 `openAccessPdf` → arXiv-Titelsuche →
  CORE.ac.uk (wenn Schlüssel gesetzt sind). Typischer Zuwachs bei
  IEEE-/ACM-/Springer-/Elsevier-lastigen Suchen: 40–70 Prozentpunkte.
- **Standardmäßig sicher**: Nur-HTTPS-HTTP-Transport, quellenweise
  Ratenbegrenzung (Token-Bucket), `defusedxml` für jede XML-Nutzlast,
  pfadtraversierungssichere Exportpfade, kein `eval` / `exec` / `pickle` auf
  Nutzereingaben.
- **zh-tw-/zh-cn-Vokabular-Wächter**: ~244 Regex-Muster in
  `tests/test_i18n.py::test_zh_tw_files_use_traditional_chinese_vocabulary`
  fangen vereinfachte-chinesische Lehnwörter ab, die mit traditionellen Hanzi
  gerendert werden (z. B. `內存` → `記憶體`, `魯棒性` → `穩健性`, `軟件` → `軟體`,
  `緩存` → `快取`). Derselbe Wächter läuft umgekehrt für zh-cn-Locale-Strings.
  Die vollständige Regel + der Regex-Katalog stehen in
  `.claude/agents/rules/language-vocabulary-check.md`.

## Schnellstart

```powershell
git clone <repo-url>
cd ThesisAgents
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Install with dev extras (also pulls in MCP SDK and intelligence deps)
pip install -e .[dev]
```

Suche in arXiv und exportiere Foliensatz + Arbeitsmappe + BibTeX (Standard für
`--query`):

```powershell
py -m thesisagents --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

Rufe ein einzelnes Paper per URL ab — standardmäßig `.pptx + .bib` (die `.xlsx`
ergibt für eine einzelne Zeile weniger Sinn):

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

Rendere den Foliensatz in 繁體中文:

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --lang zh-tw --out .\exports\
```

Anreicherung über die LLM-Pipeline (Python ruft Anthropic selbst auf — benötigt
API-Schlüssel):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang zh-tw --out .\exports\
```

## CLI-Flags

| Flag | Zweck |
|---|---|
| `--query` / `-q` | Schlagwörter (erforderlich, außer bei `--paper`). |
| `--paper` / `-p` | arXiv-ID / URL, DOI, PMID oder IEEE-Dokument-URL. Schließt `--query` gegenseitig aus. |
| `--source` / `-s` | Kommaseparierte Quellenliste. Standard `arxiv`. |
| `--max` / `-n` | Max. Ergebnisse pro Quelle (1..200). Standard 25. |
| `--year-from` / `--year-to` | Inklusiver Jahresfilter. |
| `--export` / `-e` | Formate: beliebige aus `pptx,xlsx,md,bib,json,ris,csv,csl`. Standard hängt vom Modus ab (siehe unten). |
| `--out` / `-o` | Ausgabeverzeichnis. Standard `./exports`. |
| `--filename-stem` | Überschreibt den generierten Dateinamensstamm. |
| `--no-abstract` | Lässt Abstract-Inhalt aus den Exporten weg. |
| `--lang` / `-l` | Foliensatzsprache: eine von 14 — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. Standard `en`. |
| `--enrich` | Fail-loud-Variante der Auto-Anreicherung. Benötigt `ANTHROPIC_API_KEY` und das `[intelligence]`-Extra. (Auto-Anreicherung ist Standard, wenn der Schlüssel gesetzt ist.) |
| `--lightweight` | Überspringt Anreicherung + erzwingt den Nur-Abstract-Foliensatz. Nur für schnelle / unbeaufsichtigte Läufe verwenden; **wenn ein LLM-Agent steuert, bevorzuge den LLM-as-agent-Ablauf** unten. |
| `--llm-model` | Überschreibt das Standardmodell `claude-opus-4-7` für die Anreicherung. |
| `--no-pdf` | Überspringt den automatischen PDF-Download. Deaktiviert außerdem das Per-Paper-PPT-Gate (kein PDF → kein vollständiger Inhalt). |
| `--no-oa-resolve` | Überspringt den OA-PDF-Resolver nach der Deduplizierung (Unpaywall + S2 + arXiv + CORE.ac.uk). |
| `--top-tier-only` | Beschränkt Ergebnisse auf arXiv + eine kuratierte CS-Flaggschiff-Whitelist (S&P, CCS, NDSS, USENIX Security, NeurIPS, ICML, ICSE, …). Standardmäßig aus. |
| `--paywall-threshold` | Anteil kostenpflichtiger Ergebnisse, der die Bestätigungsabfrage auslöst. Standard 0.30. |
| `--yes` | Überspringt die Paywall-Abfrage und fährt fort. |
| `--max-slides` | Folienobergrenze pro Paper (Standard 25; übergib 0 für unbegrenzt). |
| `--dark-mode` | Rendert die pptx mit dunklem Hintergrund + fast weißem Text. Standard ist der helle Foliensatz mit marineblauem Band. |
| `--quiet` | Unterdrückt die Ausgabe pro Paper. |

### Umgebungsvariablen

| Variable | Verwendet von | Zweck |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | LLM-Auth. Nicht nötig für den LLM-as-agent-Pfad über MCP. |
| `THESISAGENTS_LLM_MODEL` | `--enrich` | Überschreibt das Standardmodell `claude-opus-4-7`. |
| `THESISAGENTS_S2_API_KEY` | Semantic Scholar + OA-Resolver | Höheres Ratenlimit; wird auch vom S2-`openAccessPdf`-Schritt des OA-Resolvers verwendet. Kostenloser Schlüssel unter <https://www.semanticscholar.org/product/api>. |
| `THESISAGENTS_NCBI_API_KEY` | PubMed | Hebt NCBIs anonymes Limit (3/s) auf 10/s an. Optional. |
| `THESISAGENTS_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex, **Unpaywall** | Polite-Pool-Tag + aktiviert den Unpaywall-Schritt des OA-Resolvers (größter PDF-Abdeckungsgewinn für IEEE-/ACM-/Springer-/Elsevier-kostenpflichtige Paper; typischer Zuwachs 40–70 Pp). |
| `THESISAGENTS_IEEE_API_KEY` | IEEE (API-Pfad) | Offizielle IEEE-Xplore-API; liefert `pdf_url` für in-scope-Paper. |
| `THESISAGENTS_DISABLE_IEEE_SCRAPING` | IEEE | **IEEE ist standardmäßig AN über sichtbares Chrome.** Setze `=1` zum Deaktivieren (z. B. CI ohne Chrome). Der httpx-Scrape-Zweig läuft nur als Fallback, wenn WebRunner nicht verfügbar ist. |
| `THESISAGENTS_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Crossref-Plus-Abonnenten-Token (Bearer-Header). Optional. |
| `THESISAGENTS_SPRINGER_API_KEY` | Springer | Erforderlich; kostenloser Schlüssel von <https://dev.springernature.com/>. Das Plugin wirft `ConfigError` ohne ihn. |
| `THESISAGENTS_DISABLE_SCHOLAR_SCRAPING` | Google Scholar | **Scholar ist standardmäßig AN über sichtbares Chrome.** Setze `=1` zum Deaktivieren (Googles ToS verbieten automatisierten Zugriff — standardmäßig an für die Abdeckung, Opt-out zur Vermeidung von Captcha-/IP-Block-Risiko). |
| `THESISAGENTS_CHROME_PROFILE_DIR` | Scholar + IEEE + kostenpflichtige-PDF-Downloads | Persistentes Chrome-`--user-data-dir`. Setze dies und vervollständige VPN / SSO / Google-Anmeldung einmal; nachfolgende Läufe erben die Cookies, sodass IEEE kostenpflichtige Metadaten zurückgibt und Scholar ungedrosselte SERPs liefert. |
| `THESISAGENTS_DISABLE_WEBRUNNER` | Scholar + IEEE + kostenpflichtige-PDF-Downloads | `=1` erzwingt die httpx-Pfade statt echtes Chrome zu steuern. Nützlich für CI / Docker ohne Chrome-Binary; ansonsten nicht setzen. |
| `THESISAGENTS_CORE_API_KEY` | OA-Resolver + `core`-Suchquelle | Kostenloser Schlüssel von <https://core.ac.uk/services/api>. Aktiviert den CORE.ac.uk-OA-Lookup-Schritt (200 Mio.+ institutionelle / regionale OA-Elemente) **und** die `core`-Suchquelle. Ohne ihn wird die `core`-Quelle stillschweigend übersprungen und die anderen OA-Strategien (Unpaywall, S2, arXiv) laufen weiterhin. |
| `THESISAGENTS_PDF_COOKIES_FILE` | PDF-Downloader | Netscape-`cookies.txt`. Standardmäßig aus. Nur mit Verlagen verwenden, an denen du institutionelle Rechte hast. |
| `THESISAGENTS_LOG_LEVEL` | Logger | `INFO` Standard; `DEBUG` für ausführliches Tracing. |

Standardwerte: `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. Immer mit
explizitem `--export` überschreibbar.

## LLM-as-agent-Ablauf

Wenn ein LLM in deinem Editor den Workflow steuert, verwende die MCP-Tools in
Reihenfolge: `search`, `download_pdfs`, `fetch_pdf_text`, dann `export` mit
einer von Hand verfassten reichhaltigen `PaperSummary`. Die vorhandenen
`scripts/regen_*.py`-Dateien sind reproduzierbare Beispiele für den finalen
Verfassungs- und Exportschritt.

Das vollständige End-to-End-Runbook (Suche → reichhaltiger Foliensatz) steht in
`.claude/agents/tasks/paper-summary-author.md` — öffne es, bevor du eine neue
Query beginnst, damit das LLM den Ablauf ohne Pause für Nutzereingaben
durchführen kann.

## MCP-Server

Bei Claude Code registrieren:

```powershell
claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp
```

Oder in deine Einstellungsdatei schreiben:

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

Tools:

| Tool | Zweck |
|---|---|
| `list_sources` | Zählt jedes Plugin auf + meldet, ob es in der aktuellen Umgebung aktiviert ist. Rufe dies einmal vor `search` auf. |
| `list_exports` | Zählt jedes Exportformat mit seiner einzeiligen Beschreibung auf und ob es eine aggregierte Datei oder eine Datei pro Paper schreibt. |
| `search` | Schlagwörter → Liste von Papern. Akzeptiert `top_tier_only`, `min_citations`; nutzt standardmäßig den vollständigen Quellenmix ohne API-Schlüssel. |
| `fetch_paper` | arXiv / DOI / PMID / IEEE-Identifikator → einzelnes Paper. |
| `fetch_pdf_text` | Lädt ein PDF herunter, gibt extrahierten Fließtext zurück. **Der MCP-Pfad zu „Ich habe das Paper gelesen".** |
| `download_pdfs` | Lädt die PDFs einer Paper-Liste stapelweise nach `{out_dir}/pdfs/` herunter. Gibt Ergebnisse pro Paper zurück, indiziert nach BibTeX-Schlüssel. |
| `export` | Paper-Liste + Formate → schreibt `.pptx/.xlsx/.md/.bib/.json/.ris/.csv/.csl.json`. Akzeptiert ein `summary`-Feld pro Paper für das reichhaltige Thesis-Stil-Schema, `max_slides_per_paper` (Standard 25) und `dark_mode` (Standard `false` — der Projektstandard ist der helle Foliensatz mit marineblauem Band, übergib `true` für den dunklen OLED-/Schwachlicht-Nachlauf). |
| `pptx_inspect` | Liest die Folien-/Shape-Struktur eines vorhandenen Foliensatzes. |
| `pptx_review` | Prüft einen Foliensatz in einem Aufruf — Überlauf + Farbverträge + `paper_rule`-Abschnittsvollständigkeit. Erkennt die Foliensatzsprache automatisch; auch die CLI `python -m thesisagents review <deck.pptx>`. |
| `pptx_update_slide` | Ersetzt `title` / `body` / `meta` (nach Shape-Name) oder beliebige Shapes nach Index. |
| `pptx_delete_slide` | Entfernt eine Folie und ihre Part-Beziehung. |
| `pptx_reorder_slides` | Permutiert Folien über `sldIdLst`. |
| `pptx_add_slide` | Hängt eine neue Titel-/Body-/Meta-Folie an oder fügt sie ein. |

LLM-as-agent-Ablauf (kein `ANTHROPIC_API_KEY` nötig — das LLM ist der Agent):

```
1. (optional) list_sources()                       # discover enabled plugins
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (optional) download_pdfs(papers, out_dir="./exports/...")  # persist PDFs
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # per paper
5. (the LLM reads body text, produces a structured `summary` dict)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="zh-tw", formats=["pptx","bib"], dark_mode=true, ...)
```

Vollständige Referenz in [`docs/mcp.md`](../docs/mcp.md).

## Projektstruktur

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

Das `-c`-Flag bei bandit ist erforderlich — ohne es ignoriert bandit die
Skip-Konfiguration des Projekts. Wenn du den pptx-Exporter anfasst, führe auch
eine Überlaufprüfung durch (siehe `CLAUDE.md` „Slide Deck Rules").

## Desktop-GUI (PySide6)

Eine native Desktop-Oberfläche wird hinter dem `[gui]`-Extra ausgeliefert:

```powershell
pip install thesisagents[gui]
thesisagents-gui                 # or: thesisagents gui
```

Das Fenster hat vier Tabs — **Search**, **Settings** (persistiert API-Schlüssel
über QSettings), **Enrich** (steuert die LLM-as-agent-/Python-Pipeline-Anreicherung
über ein `collection_ready`-Signal) und **Deck** (der Light-mode-Umschalter +
die Folienobergrenze- und Max-Figures-Steuerungen fließen in `ExportOptions`
ein). Das Windows-Release-Zip liefert das mit Nuitka kompilierte Bündel mit
enthaltenem PySide6, sodass `thesisagents.exe gui` ohne separate
Python-Installation funktioniert.
**Die UI wird in allen 14 Sprachen ausgeliefert** (English, 繁體中文, 简体中文,
日本語, Español, Français, Deutsch, 한국어, Português, Русский,
Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia) — der erste Start wählt die
Sprache aus deiner OS-Locale, danach kannst du sie über **Settings → Interface
language** ändern. Die Ausgabesprache des Foliensatzes ist ein separates
Dropdown, sodass du die UI in einer Sprache betreiben und Folien in einer
anderen erzeugen kannst. Das Layout ist responsiv: Jedes Formular sitzt in
einer `QScrollArea` und das Fenster lässt sich bis auf 900×600 verkleinern
(passt noch auf 720p), mit standardmäßig aktivierter HiDPI-Skalierung.

Vollständige Referenz: [`docs/gui.md`](../docs/gui.md).

## Paketierung als eigenständige ausführbare Datei

Zwei Packager sind dokumentiert, um eine einzelne Binärdatei auszuliefern, die
ohne installiertes Python läuft:

- **[`docs/packaging-pyinstaller.md`](../docs/packaging-pyinstaller.md)**
  — schneller Build (unter einer Minute), 200–300 MB Output, 2–4 s Startzeit.
  Am besten, wenn du am Build-Skript iterierst.
- **[`docs/packaging-nuitka.md`](../docs/packaging-nuitka.md)** —
  langsamer Build (5–15 Minuten), 80–150 MB Output, Startzeit unter einer
  Sekunde, etwas Bytecode-Schutz. Am besten, wenn Endnutzer die Binärdatei
  viele Male ausführen.

Beide Dokumente behandeln den projektspezifischen Fallstrick — die dynamischen
Quell-Plugins unter `sources/<name>/` — und liefern einen verifizierten Befehl
für die CLI- und die MCP-Server-Einstiegspunkte.

## Continuous Integration & Releases

Zwei GitHub-Actions-Workflows leben unter `.github/workflows/`:

- **`ci.yml`** läuft bei jedem Push und PR nach `main`. Die Matrix ist Ubuntu +
  Windows × Python 3.12 / 3.13 / 3.14 (6 Jobs). Jeder Job führt
  `ruff check`, `bandit -c pyproject.toml` und `pytest` aus.
- **`release.yml`** wartet, bis `ci.yml` auf `main` abgeschlossen ist
  (`workflow_run`-Trigger). Es läuft nur, wenn CI erfolgreich war. **Jeder
  CI-erfolgreiche Push nach `main` ist ein Release** — der Workflow erhöht
  automatisch die Patch-Version in `pyproject.toml`, committet die Erhöhung
  zurück nach `main` als `chore: bump version to X.Y.Z` und pipelinet:
  1. **`bump-version`** — liest die aktuelle `X.Y.Z` aus `pyproject.toml`,
     erhöht auf `X.Y.(Z+1)`, committet + pusht zurück nach `main` mit dem
     Workflow-`GITHUB_TOKEN`. Dieser Push löst KEINE erneute CI aus (gemäß
     GitHubs Regel, dass `GITHUB_TOKEN`-getriebene Pushes keine neuen
     Workflow-Läufe starten können), sodass der Zyklus natürlich endet.
  2. **`publish-pypi`** — baut sdist + wheel, `twine check`,
     `twine upload` über `PYPI_API_TOKEN`.
  3. **`create-draft-release`** — öffnet ein *Entwurfs*-GitHub-Release beim
     Tag `v<version>` mit automatisch generierten Notizen.
  4. **`build-nuitka`** — kompiliert ein eigenständiges Nuitka-Bündel auf einem
     Windows-Runner (Einstiegspunkt: `python -m thesisagents` über
     `--python-flag=-m`), führt einen Smoke-Test durch, zippt den resultierenden
     `thesisagents.dist/`-Ordner und hängt das Zip + eine `.sha256`-Prüfsumme
     an das Entwurfs-Release an. Eigenständig (nicht onefile) nach Design:
     onefile entpackt sich bei jedem Start selbst nach `%TEMP%`, was
     Startlatenz hinzufügt und Antiviren-Heuristiken auf gesperrten Maschinen
     auslöst. Auch nur Windows nach Design: Linux-/macOS-Nutzer installieren
     von PyPI. Der auf `pyproject.toml` verschlüsselte Build-Cache reduziert
     warme Builds von ~85 min kalt auf ~5–10 min.
  5. **`publish-release`** — entfernt die Entwurfsmarkierung, sobald das
     Nuitka-Asset hochgeladen ist, sodass Nutzer nie ein halbfertiges Release
     sehen.

  **Ein Release überspringen.** Füge `[skip release]` irgendwo in die
  Commit-Nachricht ein, und die Erhöhung + jeder nachgelagerte Job wird
  übersprungen — verwende dies für reine Doku-/Tippfehler-/Refactoring-Commits,
  die keine Versionsnummer verbrauchen sollten.

Um PyPI-Publishing + Release-Executables zu aktivieren:

1. Generiere ein projektbezogenes API-Token unter
   <https://pypi.org/manage/account/token/>.
2. Im GitHub-Repo: `Settings → Secrets and variables → Actions →
   New repository secret`. Nenne es `PYPI_API_TOKEN` und füge den Token-Wert
   ein.
3. Erlaube GitHub Actions, nach `main` zu pushen: `Settings → Actions →
   General → Workflow permissions → Read and write permissions`. Der
   Bump-Commit wird vom `GITHUB_TOKEN` des Workflows gepusht.
4. Erstelle Releases durch das Mergen von PRs in `main`. Die Pipeline benötigt
   ~3–5 min, um zu PyPI zu publizieren, und ~80–90 min mehr (kalt) oder ~5–10 min
   (warmer Nuitka-Cache), damit das Windows-Zip angehängt wird.

Der `publish-pypi`-Job hängt absichtlich KEINE GitHub-Environment an, sodass
jeder Lauf als Release-Eintrag erscheint (mit angehängter Nuitka-`.exe`) statt
als „Deployment"-Sidebar-Widget auf der Repo-Startseite — Releases erhalten
ihre eigene dedizierte Seite und ein Deployment-Eintrag obendrauf wäre nur
redundantes Rauschen.

## Lizenz

Siehe `LICENSE`. Die arXiv-API wird gemäß arXivs API-Nutzungsbedingungen
(<https://info.arxiv.org/help/api/tou.html>) verwendet — beachte das Soft-Limit
von 1 Anfrage pro 3 Sekunden; der mitgelieferte Fetcher erzwingt dies bereits
über seinen Token-Bucket.
