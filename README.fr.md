# AutoPaperToPPT

> **Langues** : [English](README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · **Français** · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **Documentation** : [autopapertoppt.readthedocs.io](https://autopapertoppt.readthedocs.io/en/latest/)

Assistant de recherche d'articles piloté par mots-clés. Il interroge arXiv, Semantic Scholar, OpenAlex, PubMed, ACM (via Crossref), IEEE Xplore, DBLP, Crossref générique, OpenAIRE, Springer Nature et Google Scholar ; normalise les résultats en un format de fiche unique ; et exporte l'ensemble dédupliqué en **présentation PowerPoint de style thèse**, **classeur Excel** et **fichier BibTeX** — le tout par un seul appel CLI ou un seul appel MCP. Peut également enrichir chaque article en lisant son PDF pour produire un résumé structuré, soit en contexte (flux LLM-as-agent), soit via l'API Anthropic (flux Python pipeline).

## Pour les agents IA pilotant ce projet

**Si vous êtes un LLM (Claude Code, Cursor, Aider, Codex CLI, …) lisant ce README pour comprendre quoi faire — commencez ici.** Les mêmes règles sont épinglées dans [`AGENTS.md`](AGENTS.md) (miroir inter-agents) et [`CLAUDE.md`](CLAUDE.md) (référence canonique) ; lisez-les avant tout changement non trivial.

### Ce que l'utilisateur attend vraiment

Le livrable par défaut est **un `.pptx` enrichi style thèse par article**, pas la version légère limitée au résumé que la CLI produit par défaut. Le rendu léger est un artefact intermédiaire — votre travail est de l'enrichir.

### Arbre de décision

1. La variable `ANTHROPIC_API_KEY` est-elle définie ? → lancez la CLI ; elle s'enrichit automatiquement via l'API Anthropic. Terminé.
2. Pas de clé, mais vous (un LLM) pilotez la session → **vous produisez le résumé enrichi vous-même**. Lisez chaque PDF, rédigez à la main un `PaperSummary` avec les champs niveau enrichi (`pain_points`, `research_question`, `contributions_detailed`, `headline_metrics`, `technique_table`, `method_sections`, `evaluation_sections`, `system_flow`, `research_questions`, `rq_results`, `core_observation`, `limitations`, `future_work`), déposez un `scripts/regen_<query>.py` et exécutez-le. **Ne dites pas à l'utilisateur de configurer la clé API** — c'est vous, le LLM, qui auriez écrit le résumé.
3. Pas de LLM (CI / cron / non surveillé) → le rendu léger est acceptable.

### Workflow MCP en 6 étapes

```
1. (optionnel) list_sources()                             # quels plugins sont activés
2. search(keywords, sources, top_tier_only=true, ...)
3. (optionnel) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # par article
5. (vous lisez chaque PDF et produisez un dict de résumé structuré)
6. export(papers=[{...paper, "summary": {...}}], language="fr", ...)
```

Les onze outils MCP (incluant `list_sources`, `download_pdfs`, `pptx_inspect` / `pptx_update_slide` / `pptx_add_slide` / etc.) sont documentés dans [`docs/mcp.md`](docs/mcp.md).

### Obligatoire : vérification URL / DOI avant livraison

Les chemins d'URL des éditeurs **ne peuvent pas être devinés** — AAAI utilise des identifiants numériques (`v40i5.37389`), IEEE utilise un `arnumber` opaque, ACM utilise des DOIs opaques. Quand vous rédigez un `Paper` à la main, **copiez `url` / `doi` / `arxiv_id` mot pour mot depuis le xlsx produit par cette recherche** — jamais de mémoire, jamais construit à partir du titre.

Le xlsx est écrit dans `exports/<run>/<slug>-<timestamp>.xlsx` avec colonne 7 = DOI, colonne 8 = URL. Auditez votre script regen à la fin :

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

Deux fabrications attrapées ainsi en production : mauvais volume AAAI (`v39i23.34521` vs le vrai `v39i22.34537`) et chemin avec slug d'auteur inventé (`view/fang2026` au lieu de `v40i5.37389`).

### Exemple complet

[`scripts/regen_llm_security_batch.py`](scripts/regen_llm_security_batch.py) livre 8 résumés enrichis rédigés à la main selon ce processus. Utilisez-le comme modèle pour toute recherche multi-articles. Le pendant zh-tw est dans [`scripts/regen_llm_security_batch_zh_tw.py`](scripts/regen_llm_security_batch_zh_tw.py).

### À ne pas faire

- **Ne pas** clôturer une recherche multi-articles en disant à l'utilisateur « définissez `ANTHROPIC_API_KEY` pour avoir le rendu enrichi » — vous êtes le LLM qui aurait écrit les résumés.
- **Ne pas** considérer le `.pptx` léger par article comme le livrable.
- **Ne pas** s'arrêter quand `download_pdfs` signale N PDFs sauvegardés — c'est le début de la phase d'écriture enrichie, pas la fin.
- **Ne pas** inventer chiffres, RQ, contributions ou limites absents du papier.
- **Ne pas** fabriquer d'URL / DOI / IDs arXiv — voir règle ci-dessus.
- **Ne pas** laisser des téléchargements non pertinents dans le répertoire d'exécution. La recherche par mots-clés ramène parfois des articles hors sujet (la requête « Claude code » a ramené un article sur le décodeur Viterbi ; « LLM code review » a ramené une revue sur la détection d'objets). Après classement comme hors sujet, supprimez le `pdfs/<key>.pdf` et le `<key>.pptx` léger ; conservez le xlsx / bib agrégé comme trace fidèle de ce que la recherche a retourné.
- **Ne pas** mentionner « Claude », « Claude Code », « AI-generated », « GPT », « Copilot » ni aucun nom d'outil / modèle d'IA dans les messages de commit, descriptions de PR, commentaires de code ou documentation.

## Fonctionnalités

- **Onze sources branchables** : `arxiv`, `semantic_scholar`, `openalex`, `pubmed`, `acm` (limité à ACM via Crossref), `dblp`, `crossref` (générique), `openaire`, `springer` (clé API requise), `ieee` (clé API ou scraping opt-in), `scholar` (scraping opt-in). Chacune vit sous `sources/<name>/` derrière un adaptateur `Fetcher`. Une liste blanche de revues prestigieuses filtre les résultats sur les conférences/revues CS phares plus Nature/Science/PNAS par défaut ; `--all-venues` désactive le filtre.
- **Mode article unique** : collez un ID arXiv, une URL arXiv, un DOI, un PMID ou une URL document IEEE — AutoPaperToPPT le résout via la bonne source et produit le même paquet d'exports. Utile pour notes de lecture et préparation de soutenance.
- **Mode PDF local** (`--pdf <chemin>`) : passez un PDF ou un répertoire. Un extracteur heuristique tire **titre, auteurs, année, ID arXiv, DOI et le vrai résumé** depuis le début de chaque PDF (ancré sur l'en-tête explicite `Abstract` / `ABSTRACT` / `摘要`, pas sur un préfixe aveugle). `--title` / `--authors` / `--year` / `--venue` / `--doi` / `--arxiv-id` surchargent en mode PDF unique ; en mode répertoire, l'extraction par fichier gagne, et chaque article obtient sa propre présentation nommée d'après sa clé BibTeX.
- **Cinq exporteurs** :
  - `.pptx` — écran large 16:9, numéroté, trois niveaux de rendu (léger résumé seul · enrichi-plat · **style thèse** avec quadrants de douleurs, KPIs encadrés, tables comparatives de techniques, tables de résultats par RQ, synthèse des contributions, observation centrale, limites et travaux futurs, Q&R, références). Toutes les chaînes de gabarit sont i18n sur **14 langues** : English, 繁體中文, 简体中文, 日本語, Español, Français, Deutsch, 한국어, Português, Русский, Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia.
  - `.xlsx` — feuille Papers + feuille de provenance Query, URL / PDF hyperliés, en-tête figé, largeurs auto. La colonne 5 (**Source**) montre le lieu de publication réel (par ex. « IEEE Access ») ; la colonne 6 (**Indexed via**) montre quel fetcher a renvoyé les métadonnées (par ex. « openalex »), pour éviter la confusion entre les deux informations.
  - `.md` — liste complète source / titre / résumé.
  - `.bib` — clés de citation sans collision, champs échappés LaTeX.
  - `.json` — payload brut pour outillage en aval.
- **Boîte à outils d'édition PPT** : `autopapertoppt.exporters.pptx_edit` (inspect / update_slide / delete_slide / reorder_slides / add_slide) fonctionne sur toute présentation produite par l'exporteur, plus les outils MCP équivalents `pptx_*` permettant à un agent LLM d'itérer sur une présentation générée.
- **Serveur MCP** : 11 outils — `list_sources` (découverte), `search`, `fetch_paper`, `fetch_pdf_text`, `download_pdfs`, `export` et les cinq outils d'édition `pptx_*`. Permet à tout LLM compatible MCP (Claude Code, Claude Desktop, Cursor, …) de piloter l'ensemble du workflow.
- **Deux voies d'enrichissement** pour aller au-delà du résumé vers une présentation style thèse :
  - **LLM-as-agent (sans clé API)** — le LLM appelant lit le texte du PDF via `fetch_pdf_text`, écrit un résumé structuré en contexte et le passe à `export`.
  - **Pipeline Python (`--enrich`)** — la CLI appelle l'API Anthropic elle-même ; modèle par défaut `claude-opus-4-7`.
- **Sûr par défaut** : transport HTTP en HTTPS uniquement, limitation de débit par source (token bucket), `defusedxml` pour tout payload XML, chemins d'export sécurisés contre path-traversal, pas d'`eval` / `exec` / `pickle` sur entrée utilisateur. Scraping Scholar et IEEE désactivés par défaut (opt-in via variable d'environnement).

## Démarrage rapide

```powershell
git clone <repo-url>
cd AutoPaperToPPT
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Installation avec extras dev (inclut aussi le SDK MCP et les deps intelligence)
pip install -e .[dev]
```

Rechercher arXiv et exporter présentation + classeur + BibTeX (default pour `--query`) :

```powershell
py -m autopapertoppt --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

Récupérer un seul article par URL — default `.pptx + .bib` (un `.xlsx` d'une ligne a peu de sens) :

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

Rendre la présentation en français :

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --lang fr --out .\exports\
```

Enrichissement pipeline LLM (Python appelle Anthropic — clé API requise) :

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang fr --out .\exports\
```

## Flags CLI

| Flag | Rôle |
|---|---|
| `--query` / `-q` | Mots-clés (obligatoire sauf si `--paper`). |
| `--paper` / `-p` | ID / URL arXiv, DOI, PMID ou URL document IEEE. Exclusif avec `--query`. |
| `--source` / `-s` | Liste de sources séparées par virgule. Default `arxiv`. |
| `--max` / `-n` | Résultats max par source (1..200). Default 25. |
| `--year-from` / `--year-to` | Filtre d'année inclusif. |
| `--export` / `-e` | Formats : tout sous-ensemble de `pptx,xlsx,md,bib,json`. Default selon le mode (voir ci-dessous). |
| `--out` / `-o` | Répertoire de sortie. Default `./exports`. |
| `--filename-stem` | Surcharge le stem généré. |
| `--no-abstract` | Omet les résumés dans les exports. |
| `--lang` / `-l` | Langue de la présentation : une des 14 — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. Default `en`. |
| `--enrich` | Télécharge le PDF + résumé Anthropic. Nécessite `ANTHROPIC_API_KEY` et l'extra `[intelligence]`. |
| `--lightweight` | Force le rendu léger même si `ANTHROPIC_API_KEY` est définie. |
| `--llm-model` | Surcharge le modèle par défaut `claude-opus-4-7`. |
| `--all-venues` | Désactive la liste blanche (default conserve les lieux CS phares + Nature / Science / PNAS / CACM / LNCS). |
| `--paywall-threshold` | Fraction de résultats sous paywall déclenchant la confirmation. Default 0.30. |
| `--yes` | Saute l'invite paywall. |
| `--max-slides` | Plafond de diapos par article (default 25 ; 0 pour illimité). |
| `--quiet` | Supprime l'affichage par article. |

### Variables d'environnement

| Variable | Utilisée par | Rôle |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | Auth LLM. Non nécessaire pour la voie LLM-as-agent via MCP. |
| `AUTOPAPERTOPPT_LLM_MODEL` | `--enrich` | Surcharge le default `claude-opus-4-7`. |
| `AUTOPAPERTOPPT_S2_API_KEY` | Semantic Scholar | Limite de débit plus élevée. Optionnel. |
| `AUTOPAPERTOPPT_NCBI_API_KEY` | PubMed | Élève la limite anonyme de NCBI (3/s) à 10/s. Optionnel. |
| `AUTOPAPERTOPPT_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex | Place les requêtes dans le pool poli de Crossref. |
| `AUTOPAPERTOPPT_IEEE_API_KEY` | IEEE (voie API) | API officielle IEEE Xplore ; expose `pdf_url` pour les articles couverts. |
| `AUTOPAPERTOPPT_ENABLE_IEEE_SCRAPING` | IEEE (voie scraping) | `=1` active le scraping. Inutile quand la clé API est définie. |
| `AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Jeton abonné Crossref Plus (en-tête Bearer). Optionnel. |
| `AUTOPAPERTOPPT_SPRINGER_API_KEY` | Springer | Obligatoire ; clé gratuite sur <https://dev.springernature.com/>. Le plugin est silencieusement ignoré sinon. |
| `AUTOPAPERTOPPT_ENABLE_SCHOLAR_SCRAPING` | Google Scholar | `=1` active le scraping. Désactivé par défaut — les CGU de Scholar interdisent le scraping. |
| `AUTOPAPERTOPPT_PDF_COOKIES_FILE` | Téléchargeur PDF | `cookies.txt` au format Netscape. Désactivé par défaut. Utilisez uniquement avec des éditeurs pour lesquels vous avez des droits institutionnels. |
| `AUTOPAPERTOPPT_LOG_LEVEL` | logger | `INFO` par défaut ; `DEBUG` pour traces verbeuses. |

Defaults : `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. Toujours surclassable par `--export` explicite.

## Serveur MCP

Enregistrement avec Claude Code :

```powershell
claude mcp add autopapertoppt -- ".venv\Scripts\python.exe" -m autopapertoppt.mcp
```

Ou éditer manuellement le fichier de configuration :

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

Outils :

| Outil | Rôle |
|---|---|
| `list_sources` | Énumère chaque plugin + indique lesquels sont activés dans l'env courant. À appeler une fois avant `search`. |
| `search` | Mots-clés → liste d'articles. Accepte `top_tier_only`, `min_citations` ; par défaut le mix complet sans clé API. |
| `fetch_paper` | Identifiant arXiv / DOI / PMID / IEEE → un seul article. |
| `fetch_pdf_text` | Télécharge un PDF, renvoie le texte extrait. **La voie MCP pour « j'ai lu le papier ».** |
| `download_pdfs` | Téléchargement en lot des PDFs d'une liste d'articles vers `{out_dir}/pdfs/`. Renvoie les résultats par article, indexés par clé BibTeX. |
| `export` | Liste d'articles + formats → écrit `.pptx/.xlsx/.md/.bib/.json`. Accepte un champ `summary` par article pour le schéma style thèse enrichi et `max_slides_per_paper` (default 25). |
| `pptx_inspect` | Lit la structure slides / shapes d'une présentation existante. |
| `pptx_update_slide` | Remplace `title` / `body` / `meta` (par nom de shape) ou des shapes arbitraires par index. |
| `pptx_delete_slide` | Supprime une diapo et sa part relationship. |
| `pptx_reorder_slides` | Réordonne les diapos via `sldIdLst`. |
| `pptx_add_slide` | Ajoute en fin ou insère une nouvelle diapo title / body / meta. |

Flux LLM-as-agent (sans `ANTHROPIC_API_KEY` — le LLM est l'agent) :

```
1. (optionnel) list_sources()                      # découvrir les plugins activés
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (optionnel) download_pdfs(papers, out_dir="./exports/...")  # persiste les PDFs
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # par article
5. (le LLM lit le texte, produit un dict `summary` structuré)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="fr", formats=["pptx","bib"], ...)
```

Référence complète : [`docs/mcp.md`](docs/mcp.md).

## Structure du projet

```
AutoPaperToPPT/
├── autopapertoppt/                 # paquet principal
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # client async HTTPS uniquement, rate-limit token bucket
│   ├── exporters/                   # pptx (style thèse) · xlsx · bib · md · json · pptx_edit · i18n
│   ├── intelligence/                # téléchargement PDF + résumeur Anthropic ([intelligence] extra)
│   ├── mcp/                         # serveur FastMCP (11 outils)
│   ├── utils/                       # logging, path safety
│   ├── cli.py                       # CLI argparse
│   └── __main__.py
├── sources/                         # dossiers plugin : arxiv, semantic_scholar,
│                                    #   openalex, pubmed, acm, ieee, scholar,
│                                    #   dblp, crossref, openaire, springer
├── tests/                           # suite pytest + fixtures enregistrés (pas de HTTP live)
├── docs/                            # Sphinx (14 arbres de langues)
├── scripts/                         # scripts regen uniques
└── pyproject.toml                   # ruff, bandit, build, extras optionnels
```

## Definition of Done

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r autopapertoppt/ sources/
```

Le flag `-c` de bandit est obligatoire — sans lui, bandit ignore la configuration skip du projet. Si vous touchez à l'exporteur pptx, lancez aussi un contrôle de débordement (voir `CLAUDE.md` « Slide Deck Rules »).

## Licence

Voir `LICENSE`. L'API arXiv est utilisée selon ses conditions (<https://info.arxiv.org/help/api/tou.html>) — respectez la limite soft de 1 requête toutes les 3 secondes ; le fetcher livré l'applique déjà via son token bucket.
