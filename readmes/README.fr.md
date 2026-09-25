# ThesisAgents

[![CI](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![Python](https://img.shields.io/pypi/pyversions/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/ThesisAgents.svg)](https://github.com/Integration-Automation/ThesisAgents/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/thesisagents/badge/?version=latest)](https://thesisagents.readthedocs.io/en/latest/)

> **Langues** : [English](../README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · **Français** · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **Documentation** : [thesisagents.readthedocs.io](https://thesisagents.readthedocs.io/en/latest/)

Un assistant de recherche d'articles piloté par mots-clés qui récupère des
résultats depuis arXiv, Semantic Scholar, OpenAlex, PubMed, ACM (via Crossref),
IEEE Xplore, DBLP, Crossref générique, OpenAIRE, Springer Nature, Europe PMC,
DOAJ, HAL, CORE et Google Scholar,
les normalise en une forme d'enregistrement unique, et exporte l'ensemble
dédupliqué sous forme de **présentation PowerPoint de style thèse**, de
**classeur Excel** et de **fichier BibTeX** — le tout à partir d'un seul appel
CLI ou d'un seul appel d'outil MCP. En option, enrichit chaque article en
lisant son PDF et en produisant un résumé structuré par article, soit
en contexte (flux LLM-as-agent), soit via l'API Anthropic (flux pipeline
Python).

## Pour les agents IA qui pilotent ce projet

**Si vous êtes un LLM (Claude Code, Cursor, Aider, Codex CLI, …) en train de
lire ce README pour comprendre quoi faire — commencez ici.** Tout ce qui suit
est aussi épinglé dans [`AGENTS.md`](AGENTS.md) (miroir inter-agents) et
[`CLAUDE.md`](CLAUDE.md) (référence canonique) ; lisez-les avant de faire des
changements non triviaux.

### Ce que l'utilisateur veut réellement

Le livrable par défaut est **un `.pptx` riche de style thèse par article**, et
non la présentation légère basée uniquement sur le résumé que la CLI produit par
défaut. L'émission légère est un artefact intermédiaire — votre travail est de
l'améliorer.

### Arbre de décision

1. `ANTHROPIC_API_KEY` est-il défini dans l'environnement ? → exécutez
   simplement la CLI ; elle enrichit automatiquement via l'API Anthropic. Vous
   avez terminé.
2. Pas de clé, mais vous (un LLM) pilotez la session → **vous produisez
   vous-même le résumé riche**. Lisez chaque PDF, rédigez à la main une
   `PaperSummary` avec les champs de niveau riche (`pain_points`,
   `research_question`, `contributions_detailed`, `headline_metrics`,
   `technique_table`, `method_sections`, `evaluation_sections`,
   `system_flow`, `research_questions`, `rq_results`,
   `core_observation`, `limitations`, `future_work`), déposez un
   `scripts/regen_<query>.py`, exécutez-le. **Ne dites pas à l'utilisateur de
   définir la clé API** — vous êtes le LLM qui aurait écrit le résumé.
3. Pas de LLM dans la boucle (CI / cron / sans surveillance) → le léger est
   acceptable.

### Workflow MCP en 6 étapes

```
1. (optional) list_sources()                              # see which plugins are enabled
2. search(keywords, sources, top_tier_only=true, ...)
3. (optional) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # per paper
5. (you read each PDF and produce a structured summary dict)
6. export(papers=[{...paper, "summary": {...}}], language="zh-tw", ...)
```

Les treize outils MCP (y compris `list_sources`, `list_exports`,
`download_pdfs`, `pptx_inspect` / `pptx_review` / `pptx_update_slide` /
`pptx_add_slide` / etc.) sont
documentés dans [`docs/mcp.md`](docs/mcp.md).

### Obligatoire : vérification URL / DOI avant la livraison

Les chemins d'URL des éditeurs **ne peuvent pas être devinés** — AAAI utilise
des ID numériques (`v40i5.37389`), IEEE utilise un `arnumber` opaque, ACM
utilise des DOI opaques. Lorsque vous rédigez un `Paper` à la main, **copiez
`url` / `doi` / `arxiv_id` textuellement depuis le xlsx de recherche qui a
produit cette exécution** — jamais de mémoire, jamais construit à partir du
titre.

Le xlsx est écrit dans `exports/<run>/<slug>-<timestamp>.xlsx` avec la
colonne 7 = DOI, colonne 8 = URL. Auditez votre script de regen quand vous avez
terminé :

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

Deux fabrications détectées ainsi en production : mauvais volume AAAI
(`v39i23.34521` au lieu du réel `v39i22.34537`) et chemin de slug d'auteur
inventé (`view/fang2026` au lieu de `v40i5.37389`).

### Obligatoire : élaguer les téléchargements non pertinents avant la livraison

La correspondance des mots-clés de recherche est basée sur les mots-clés, donc
des articles hors sujet se glisseront : une requête « Claude code » a renvoyé un
article sur un décodeur de Viterbi parce que les deux contiennent « code » ;
« LLM code review » a fait correspondre une revue de littérature sur la
détection d'objets. Une fois que vous avez lu les résumés et classé un article
comme hors sujet par rapport à l'intention réelle de l'utilisateur, élaguez le
répertoire d'exécution :

```python
from pathlib import Path
run = Path("exports/<run>")
irrelevant_keys = ("key-of-off-topic-paper-1", "key-of-off-topic-paper-2")
for key in irrelevant_keys:
    for path in (run / "pdfs" / f"{key}.pdf", run / f"{key}.pptx"):
        if path.exists():
            path.unlink()
```

Supprimez `exports/<run>/pdfs/<key>.pdf` + `exports/<run>/<key>.pptx`.
**Conservez** le `<slug>-<timestamp>.xlsx` / `.bib` agrégé — ce sont
l'enregistrement honnête de ce que la recherche a renvoyé. Les cas limites
reçoivent un résumé riche ; mieux vaut trop inclure que d'écarter
silencieusement une correspondance possible.

### Exemple travaillé

[`scripts/regen_fang2026.py`](scripts/regen_fang2026.py) fournit un résumé riche
rédigé à la main construit exactement de cette manière (article unique, niveau
riche, zh-tw, chaque champ riche renseigné). Une recherche multi-articles suit
la même forme avec une entrée `Paper(...summary=PaperSummary(...))` par article
dans le tuple `PaperCollection`.

### À ne pas faire

- **Ne terminez pas** une recherche multi-articles en disant à l'utilisateur de
  « définir `ANTHROPIC_API_KEY` pour une présentation riche » — vous êtes le
  LLM qui aurait pu écrire les résumés.
- **Ne traitez pas** le `.pptx` léger par article comme le livrable.
- **Ne vous arrêtez pas** après que `download_pdfs` signale N PDF enregistrés —
  c'est le début de la phase de rédaction riche, pas la fin.
- **N'inventez pas** de chiffres, RQ, contributions ou limitations qui ne
  figurent pas dans l'article.
- **Ne fabriquez pas** d'URL / DOI / ID arXiv — voir la règle ci-dessus.
- **Ne laissez pas** de téléchargements non pertinents dans le répertoire
  d'exécution. Les correspondances de la recherche par mots-clés peuvent inclure
  des articles hors sujet (une requête « Claude code » a ramené un article sur
  un décodeur de Viterbi ; « LLM code review » a ramené une revue de littérature
  sur la détection d'objets). Après avoir classé les articles comme hors sujet,
  supprimez leurs `pdfs/<key>.pdf` et `<key>.pptx` légers ; conservez le xlsx /
  bib agrégé comme enregistrement honnête de ce que la recherche a renvoyé.
- **Ne mentionnez pas** « Claude », « Claude Code », « AI-generated », « GPT »,
  « Copilot » ou tout autre nom d'outil/modèle d'IA dans les messages de commit,
  les descriptions de PR, les commentaires de code ou la documentation.

## Fonctionnalités

- **Quinze sources enfichables** : `arxiv`, `semantic_scholar`, `openalex`,
  `pubmed`, `acm` (limité à Crossref), `dblp`, `crossref` (non limité),
  `openaire`, `springer` (nécessite une clé API), `europepmc` (ouvert, sans clé
  — sciences de la vie + préprints + agriculture), `doaj` (ouvert, sans clé —
  revues en accès libre, généralement avec un lien PDF direct), `hal` (ouvert,
  sans clé — l'archive française d'informatique / maths / physique avec PDF en
  texte intégral), `core` (nécessite une clé API gratuite — le plus grand
  agrégateur en accès libre, 250 M+ de travaux), `ieee` (activé par défaut via
  Chrome visible ; une clé API ajoute l'API Xplore officielle), `scholar`
  (activé par défaut via Chrome visible). Chacune réside dans `sources/<name>/`
  derrière un adaptateur `Fetcher`. Passez `--top-tier-only` pour filtrer les
  résultats vers les conférences/revues phares en informatique plus
  Nature/Science/PNAS. La recherche par défaut conserve tous les lieux de
  publication.
- **Mode article unique** : collez un ID arXiv, une URL arXiv, un DOI, un PMID
  ou une URL de document IEEE — ThesisAgents le résout via la bonne source et
  émet le même paquet d'export. Utile pour les notes de lecture d'articles et la
  préparation de la soutenance de thèse.
- **Mode PDF local** (`--pdf <path>`) : passez un PDF ou un répertoire.
  Un extracteur heuristique tire **titre, auteurs, année, ID arXiv, DOI et le
  vrai résumé** directement de la première partie de chaque PDF (ancré sur
  l'en-tête explicite `Abstract` / `ABSTRACT` / `摘要`, et non sur un préfixe
  aveugle). `--title` / `--authors` / `--year` / `--venue` / `--doi` /
  `--arxiv-id` priment sur un appel PDF unique ; sur un répertoire,
  l'extraction fichier par fichier l'emporte, de sorte que chaque article
  obtient sa propre présentation nommée d'après sa clé BibTeX.
- **Huit exporteurs** :
  - `.pptx` — grand écran 16:9, paginé, trois niveaux de rendu
    (léger résumé seul · enrichi-plat · **style thèse** avec des quadrants de
    points de douleur, des encadrés KPI, des tableaux de comparaison de
    techniques, des tableaux de résultats par RQ, un résumé des contributions,
    l'observation centrale, les limitations & travaux futurs, Q&R, références).
    Toutes les chaînes de gabarit sont i18n sur **14 langues** : English, 繁體中文,
    简体中文, 日本語, Español, Français, Deutsch, 한국어, Português, Русский,
    Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia.
  - **Identité visuelle de présentation conçue** (pas le look par défaut Calibri
    sur blanc) : typographie par langue (Inter pour le latin, Microsoft JhengHei
    UI / YaHei UI / Yu Gothic UI / Malgun Gothic / Nirmala UI pour CJK + hindi),
    géométrie d'accent programmatique (barre d'accent en haut de chaque
    diapositive de contenu + bande gauche sur la couverture), formatage de
    tableau de style académique (grille par défaut supprimée, ligne d'en-tête
    bleu marine, séparateurs inter-lignes doux, bande de ligne alternée,
    alignement médian vertical, étiquettes de ligne en gras), et une discipline
    de palette à cinq couleurs (bleu marine / sarcelle / gris / clair / blanc)
    avec le rouge **interdit** pour le texte (utilisez plutôt gras + sarcelle
    `#0E7490` pour la mise en valeur).
  - **Le mode clair est le chemin de rendu par défaut.** Passez `--dark-mode`,
    activez **Dark mode** dans l'onglet Deck de l'interface, ou définissez
    `ExportOptions(dark_mode=True)` pour appliquer la passe sombre
    (arrière-plan de diapositive `#12151B`, texte du corps `#E5E7EB`).
  - `.xlsx` — feuille Papers + feuille de provenance de la requête, URL / PDF
    hyperliés, en-tête figé, largeurs de colonnes automatiques. La colonne 5
    (**Source**) affiche le lieu de publication réel (p. ex. « IEEE Access ») ;
    la colonne 6 (**Indexed via**) affiche quel fetcher a renvoyé les métadonnées
    (p. ex. « openalex »), de sorte que les deux informations n'entrent jamais
    en collision.
  - `.md` — liste complète source / titre / résumé.
  - `.bib` — clés de citation sans collision, champs échappés pour LaTeX.
  - `.json` — charge utile brute pour l'outillage en aval.
  - `.ris` — échange RIS importé par Zotero / Mendeley / EndNote / RefWorks (le
    pendant BibTeX pour les gestionnaires de références non-LaTeX).
  - `.csv` — tableau plat d'une ligne par article pour les tableurs / le triage
    grep rapide (guillemets RFC-4180, de sorte que les virgules dans les titres
    ne décalent jamais les colonnes).
  - `.csl.json` — CSL-JSON pour Pandoc / citeproc ; rendez une bibliographie
    dans n'importe quel style CSL (APA, IEEE, Nature, …). L'extension `.csl.json`
    la garde distincte du simple export `.json`.
- **Boîte à outils d'édition PPT** : `thesisagents.exporters.pptx_edit`
  (inspect / update_slide / delete_slide / reorder_slides / add_slide)
  fonctionne avec toute présentation produite par l'exporteur, plus les outils
  MCP `pptx_*` équivalents afin qu'un agent LLM puisse itérer sur une
  présentation générée.
- **Serveur MCP** : 13 outils — `list_sources` + `list_exports`
  (découverte), `search`, `fetch_paper`, `fetch_pdf_text`,
  `download_pdfs`, `export` et les six outils de deck `pptx_*`
  (`inspect`, `review`, `update_slide`, `delete_slide`,
  `reorder_slides`, `add_slide`). Permet à
  tout LLM compatible MCP
  (Claude Code, Claude Desktop, Cursor, …) de piloter tout le workflow.
- **Deux chemins d'enrichissement** pour aller au-delà du résumé vers une vraie
  présentation de style thèse :
  - **LLM-as-agent (sans clé API)** — le LLM appelant lit le texte du corps du
    PDF via `fetch_pdf_text`, écrit un résumé structuré en contexte et le passe
    à `export`.
  - **Pipeline Python (`--enrich`)** — la CLI appelle elle-même l'API
    d'Anthropic ; modèle par défaut `claude-opus-4-7`.
- **Flux d'éditeurs à Chrome visible** : SERP Scholar, IEEE `/rest/search` et
  chaque téléchargement de PDF payant (ieeexplore / dl.acm / link.springer /
  sciencedirect / wiley / oup / nature / science / …) s'exécutent dans une vraie
  session Chrome visible via `selenium`. L'utilisateur résout le captcha /
  termine le SSO dans la fenêtre en direct une fois ;
  `THESISAGENTS_CHROME_PROFILE_DIR` persiste les cookies entre les exécutions.
- **Flux LLM-as-agent** : les outils MCP fournissent recherche, téléchargement
  de PDF et extraction de texte. `scripts/regen_*.py` contient des exemples
  reproductibles pour rédiger à la main une `PaperSummary` riche par article.
- **Résolveur de PDF OA** : après la déduplication, chaque article sans
  `pdf_url` passe par Unpaywall → S2 `openAccessPdf` → recherche par titre arXiv
  → CORE.ac.uk (quand les clés sont définies). Gain typique sur les requêtes à
  forte densité IEEE / ACM / Springer / Elsevier : 40 à 70 points de pourcentage.
- **Sûr par défaut** : transport HTTP uniquement HTTPS, limite de débit par
  source (token bucket), `defusedxml` pour toute charge utile XML, chemins
  d'export résistants à la traversée de répertoire, pas d'`eval` / `exec` /
  `pickle` sur les entrées utilisateur.
- **Garde de vocabulaire zh-tw / zh-cn** : ~244 motifs regex dans
  `tests/test_i18n.py::test_zh_tw_files_use_traditional_chinese_vocabulary`
  attrapent les mots d'emprunt du chinois simplifié rendus en hanzi traditionnel
  (p. ex. `內存` → `記憶體`, `魯棒性` → `穩健性`, `軟件` → `軟體`,
  `緩存` → `快取`). La même garde s'exécute en sens inverse pour les chaînes de
  locale zh-cn. La règle complète + le catalogue regex se trouvent dans
  `.claude/agents/rules/language-vocabulary-check.md`.

## Démarrage rapide

```powershell
git clone <repo-url>
cd ThesisAgents
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Install with dev extras (also pulls in MCP SDK and intelligence deps)
pip install -e .[dev]
```

Recherchez dans arXiv et exportez présentation + classeur + BibTeX (par défaut
pour `--query`) :

```powershell
py -m thesisagents --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

Récupérez un seul article par URL — par défaut `.pptx + .bib` (le `.xlsx` a
moins de sens pour une seule ligne) :

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

Rendez la présentation en 繁體中文 :

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --lang zh-tw --out .\exports\
```

Enrichissement par pipeline LLM (Python appelle Anthropic lui-même — nécessite
une clé API) :

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang zh-tw --out .\exports\
```

## Flags de la CLI

| Flag | Objectif |
|---|---|
| `--query` / `-q` | Mots-clés (requis sauf si `--paper`). |
| `--paper` / `-p` | ID / URL arXiv, DOI, PMID ou URL de document IEEE. Mutuellement exclusif avec `--query`. |
| `--source` / `-s` | Liste de sources séparées par des virgules. Défaut `arxiv`. |
| `--max` / `-n` | Résultats max par source (1..200). Défaut 25. |
| `--year-from` / `--year-to` | Filtre d'année inclusif. |
| `--export` / `-e` | Formats : l'un de `pptx,xlsx,md,bib,json,ris,csv,csl`. Le défaut dépend du mode (voir ci-dessous). |
| `--out` / `-o` | Répertoire de sortie. Défaut `./exports`. |
| `--filename-stem` | Remplace le radical de nom de fichier généré. |
| `--no-abstract` | Omet le contenu du résumé des exports. |
| `--lang` / `-l` | Langue de la présentation : l'une des 14 — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. Défaut `en`. |
| `--enrich` | Variante fail-loud de l'auto-enrichissement. Nécessite `ANTHROPIC_API_KEY` et l'extra `[intelligence]`. (L'auto-enrichissement est le défaut quand la clé est définie.) |
| `--lightweight` | Saute l'enrichissement + force la présentation résumé-seul. À utiliser uniquement pour des exécutions rapides / sans surveillance ; **quand un agent LLM pilote, préférez le flux LLM-as-agent** ci-dessous. |
| `--llm-model` | Remplace le modèle par défaut `claude-opus-4-7` pour l'enrichissement. |
| `--no-pdf` | Saute le téléchargement PDF automatique. Désactive aussi le gate PPT par article (pas de PDF → pas de contenu complet). |
| `--no-oa-resolve` | Saute le résolveur de PDF OA post-déduplication (Unpaywall + S2 + arXiv + CORE.ac.uk). |
| `--top-tier-only` | Restreint les résultats à arXiv + une liste blanche organisée de références en informatique (S&P, CCS, NDSS, USENIX Security, NeurIPS, ICML, ICSE, …). Désactivé par défaut. |
| `--paywall-threshold` | Fraction de résultats payants qui déclenche l'invite de confirmation. Défaut 0.30. |
| `--yes` | Saute l'invite de paywall et continue. |
| `--max-slides` | Plafond de diapositives par article (défaut 25 ; passez 0 pour illimité). |
| `--dark-mode` | Rend la pptx avec un arrière-plan sombre + texte presque blanc. Le défaut est la présentation claire à bande bleu marine. |
| `--quiet` | Supprime l'affichage par article. |

### Variables d'environnement

| Variable | Utilisée par | Objectif |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | Auth LLM. Pas nécessaire pour le chemin LLM-as-agent via MCP. |
| `THESISAGENTS_LLM_MODEL` | `--enrich` | Remplace le modèle par défaut `claude-opus-4-7`. |
| `THESISAGENTS_S2_API_KEY` | Semantic Scholar + résolveur OA | Limite de débit plus élevée ; utilisée aussi par l'étape S2 `openAccessPdf` du résolveur OA. Clé gratuite sur <https://www.semanticscholar.org/product/api>. |
| `THESISAGENTS_NCBI_API_KEY` | PubMed | Élève la limite anonyme de NCBI (3/s) à 10/s. Optionnel. |
| `THESISAGENTS_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex, **Unpaywall** | Étiquette polite-pool + active l'étape Unpaywall du résolveur OA (le plus grand gain de couverture PDF pour les articles payants IEEE / ACM / Springer / Elsevier ; gain typique 40–70 pp). |
| `THESISAGENTS_IEEE_API_KEY` | IEEE (chemin API) | API officielle IEEE Xplore ; fait remonter `pdf_url` pour les articles dans le périmètre. |
| `THESISAGENTS_DISABLE_IEEE_SCRAPING` | IEEE | **IEEE est activé par défaut via Chrome visible.** Définissez `=1` pour vous désabonner (p. ex. CI sans Chrome). La branche de scraping httpx ne s'exécute qu'en repli quand WebRunner est indisponible. |
| `THESISAGENTS_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Token d'abonné Crossref Plus (en-tête Bearer). Optionnel. |
| `THESISAGENTS_SPRINGER_API_KEY` | Springer | Requis ; clé gratuite depuis <https://dev.springernature.com/>. Le plugin lève `ConfigError` sans elle. |
| `THESISAGENTS_DISABLE_SCHOLAR_SCRAPING` | Google Scholar | **Scholar est activé par défaut via Chrome visible.** Définissez `=1` pour vous désabonner (les CGU de Google interdisent l'accès automatisé — activé par défaut pour la couverture, désabonnement pour éviter le risque de captcha / blocage IP). |
| `THESISAGENTS_CHROME_PROFILE_DIR` | Scholar + IEEE + téléchargements de PDF payants | `--user-data-dir` Chrome persistant. Définissez-le et complétez VPN / SSO / connexion Google une fois ; les exécutions suivantes héritent des cookies afin qu'IEEE renvoie des métadonnées payantes et que Scholar serve des SERP non bridées. |
| `THESISAGENTS_DISABLE_WEBRUNNER` | Scholar + IEEE + téléchargements de PDF payants | `=1` force les chemins httpx au lieu de piloter le vrai Chrome. Utile pour CI / Docker sans binaire Chrome ; sinon laissez non défini. |
| `THESISAGENTS_CORE_API_KEY` | Résolveur OA + source de recherche `core` | Clé gratuite depuis <https://core.ac.uk/services/api>. Active l'étape de recherche OA CORE.ac.uk (200 M+ d'éléments OA institutionnels / régionaux) **et** la source de recherche `core`. Sans elle, la source `core` est silencieusement sautée et les autres stratégies OA (Unpaywall, S2, arXiv) s'exécutent toujours. |
| `THESISAGENTS_PDF_COOKIES_FILE` | Téléchargeur de PDF | `cookies.txt` Netscape. Désactivé par défaut. À utiliser uniquement avec les éditeurs pour lesquels vous avez des droits institutionnels. |
| `THESISAGENTS_LOG_LEVEL` | logger | `INFO` par défaut ; `DEBUG` pour un traçage verbeux. |

Défauts : `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. Toujours
remplaçable avec un `--export` explicite.

## Flux LLM-as-agent

Quand un LLM dans votre éditeur pilote le workflow, utilisez les outils MCP en
séquence : `search`, `download_pdfs`, `fetch_pdf_text`, puis `export` avec une
`PaperSummary` riche rédigée à la main. Les fichiers `scripts/regen_*.py`
existants sont des exemples reproductibles pour l'étape finale de rédaction et
d'export.

Le runbook complet de bout en bout (recherche → présentation riche) se trouve
dans `.claude/agents/tasks/paper-summary-author.md` — ouvrez-le avant de
commencer une nouvelle requête afin que le LLM puisse exécuter le flux sans
faire de pause pour une entrée utilisateur.

## Serveur MCP

Enregistrer avec Claude Code :

```powershell
claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp
```

Ou écrire dans votre fichier de paramètres :

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

Outils :

| Outil | Objectif |
|---|---|
| `list_sources` | Énumère chaque plugin + indique si chacun est activé dans l'environnement actuel. Appelez ceci une fois avant `search`. |
| `list_exports` | Énumère chaque format d'export avec sa description en une ligne et s'il écrit un fichier agrégé ou un fichier par article. |
| `search` | Mots-clés → liste d'articles. Accepte `top_tier_only`, `min_citations` ; par défaut le mix complet de sources sans clé API. |
| `fetch_paper` | Identifiant arXiv / DOI / PMID / IEEE → article unique. |
| `fetch_pdf_text` | Télécharge un PDF, renvoie le texte du corps extrait. **Le chemin MCP vers « j'ai lu l'article ».** |
| `download_pdfs` | Télécharge par lot les PDF d'une liste d'articles dans `{out_dir}/pdfs/`. Renvoie des résultats par article indexés par clé BibTeX. |
| `export` | Liste d'articles + formats → écrit `.pptx/.xlsx/.md/.bib/.json/.ris/.csv/.csl.json`. Accepte un champ `summary` par article pour le schéma riche de style thèse, `max_slides_per_paper` (défaut 25) et `dark_mode` (défaut `false` — le défaut du projet est la présentation claire à bande bleu marine, passez `true` pour la passe sombre OLED / faible luminosité). |
| `pptx_inspect` | Lit la structure des diapositives / formes d'une présentation existante. |
| `pptx_review` | Audite une présentation en un appel — débordement + contrats de couleur + complétude des sections `paper_rule`. Détecte automatiquement la langue de la présentation ; aussi la CLI `python -m thesisagents review <deck.pptx>`. |
| `pptx_update_slide` | Remplace `title` / `body` / `meta` (par nom de forme) ou des formes arbitraires par index. |
| `pptx_delete_slide` | Supprime une diapositive et sa relation de partie. |
| `pptx_reorder_slides` | Permute les diapositives via `sldIdLst`. |
| `pptx_add_slide` | Ajoute ou insère une nouvelle diapositive titre / corps / méta. |

Flux LLM-as-agent (pas besoin d'`ANTHROPIC_API_KEY` — le LLM est l'agent) :

```
1. (optional) list_sources()                       # discover enabled plugins
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (optional) download_pdfs(papers, out_dir="./exports/...")  # persist PDFs
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # per paper
5. (the LLM reads body text, produces a structured `summary` dict)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="zh-tw", formats=["pptx","bib"], dark_mode=true, ...)
```

Référence complète dans [`docs/mcp.md`](docs/mcp.md).

## Structure du projet

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

Le flag `-c` sur bandit est requis — sans lui, bandit ignore la configuration de
saut du projet. Quand vous touchez à l'exporteur pptx, exécutez aussi une
vérification de débordement (voir `CLAUDE.md` « Slide Deck Rules »).

## GUI de bureau (PySide6)

Une interface de bureau native est livrée derrière l'extra `[gui]` :

```powershell
pip install thesisagents[gui]
thesisagents-gui                 # or: thesisagents gui
```

La fenêtre a quatre onglets — **Search**, **Settings** (persiste les clés API
via QSettings), **Enrich** (pilote l'enrichissement LLM-as-agent / pipeline
Python via un signal `collection_ready`) et **Deck** (le bouton Light mode + les
contrôles de plafond de diapositives + max-figures se répercutent dans
`ExportOptions`). Le zip de release Windows livre le bundle compilé par Nuitka
avec PySide6 inclus, de sorte que `thesisagents.exe gui` fonctionne sans
installation Python séparée.
**L'interface est livrée dans les 14 langues** (English, 繁體中文, 简体中文,
日本語, Español, Français, Deutsch, 한국어, Português, Русский,
Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia) — le premier lancement choisit
la langue depuis la locale de votre OS, puis **Settings → Interface language**
vous permet de la changer. La langue de sortie de la présentation est un menu
déroulant séparé, de sorte que vous pouvez exécuter l'interface dans une langue
et émettre des diapositives dans une autre. La mise en page est responsive :
chaque formulaire se trouve dans une `QScrollArea` et la fenêtre se redimensionne
jusqu'à 900×600 (tient encore en 720p), avec la mise à l'échelle HiDPI activée
par défaut.

Référence complète : [`docs/gui.md`](docs/gui.md).

## Empaquetage en exécutable autonome

Deux empaqueteurs sont documentés pour livrer un binaire mono-fichier qui
s'exécute sans Python installé :

- **[`docs/packaging-pyinstaller.md`](docs/packaging-pyinstaller.md)**
  — build rapide (moins d'une minute), sortie de 200–300 Mo, démarrage de
  2–4 s. Idéal quand vous itérez sur le script de build.
- **[`docs/packaging-nuitka.md`](docs/packaging-nuitka.md)** —
  build lent (5–15 minutes), sortie de 80–150 Mo, démarrage sous la seconde,
  une certaine protection du bytecode. Idéal quand les utilisateurs finaux
  exécutent le binaire de nombreuses fois.

Les deux documents couvrent le piège spécifique au projet — les plugins de
source dynamiques sous `sources/<name>/` — et livrent une commande vérifiée
pour les points d'entrée CLI et serveur MCP.

## Intégration continue & releases

Deux workflows GitHub Actions résident sous `.github/workflows/` :

- **`ci.yml`** s'exécute à chaque push et PR vers `main`. La matrice est Ubuntu +
  Windows × Python 3.12 / 3.13 / 3.14 (6 jobs). Chaque job exécute
  `ruff check`, `bandit -c pyproject.toml` et `pytest`.
- **`release.yml`** attend que `ci.yml` se termine sur `main` (déclencheur
  `workflow_run`). Il ne s'exécute que si le CI a réussi. **Chaque push
  CI-réussi vers `main` est une release** — le workflow incrémente
  automatiquement la version de patch dans `pyproject.toml`, committe
  l'incrément vers `main` sous forme de `chore: bump version to X.Y.Z`, et
  enchaîne :
  1. **`bump-version`** — lit la `X.Y.Z` actuelle depuis `pyproject.toml`,
     incrémente à `X.Y.(Z+1)`, committe + pousse vers `main` en utilisant le
     `GITHUB_TOKEN` du workflow. Ce push ne re-déclenche PAS le CI (selon la
     règle de GitHub selon laquelle les pushes pilotés par `GITHUB_TOKEN` ne
     peuvent pas démarrer de nouvelles exécutions de workflow), de sorte que le
     cycle se termine naturellement.
  2. **`publish-pypi`** — construit sdist + wheel, `twine check`,
     `twine upload` via `PYPI_API_TOKEN`.
  3. **`create-draft-release`** — ouvre une release GitHub en *brouillon* au
     tag `v<version>` avec des notes générées automatiquement.
  4. **`build-nuitka`** — compile un bundle autonome Nuitka sur un runner
     Windows (point d'entrée : `python -m thesisagents` via
     `--python-flag=-m`), le teste à la fumée, zippe le dossier
     `thesisagents.dist/` résultant, et attache le zip + une somme de contrôle
     `.sha256` à la release en brouillon. Autonome (pas onefile) par
     conception : onefile s'auto-extrait dans `%TEMP%` à chaque lancement,
     ajoutant de la latence de démarrage et déclenchant les heuristiques
     antivirus sur les machines verrouillées. Windows uniquement par conception
     aussi : les utilisateurs Linux / macOS installent depuis PyPI. Le cache de
     build indexé sur `pyproject.toml` réduit les builds à chaud de ~85 min à
     froid à ~5–10 min.
  5. **`publish-release`** — retire la marque brouillon une fois l'asset Nuitka
     téléversé, de sorte que les utilisateurs ne voient jamais une release à
     moitié terminée.

  **Sauter une release.** Incluez `[skip release]` n'importe où dans le message
  de commit et l'incrément + chaque job en aval est sauté — utilisez ceci pour
  les commits de docs uniquement / typo / refactor qui ne devraient pas brûler
  un numéro de version.

Pour activer la publication PyPI + les exécutables de release :

1. Générez un token API à portée de projet sur
   <https://pypi.org/manage/account/token/>.
2. Dans le dépôt GitHub : `Settings → Secrets and variables → Actions →
   New repository secret`. Nommez-le `PYPI_API_TOKEN` et collez la valeur du
   token.
3. Autorisez GitHub Actions à pousser vers `main` : `Settings → Actions →
   General → Workflow permissions → Read and write permissions`. Le commit
   d'incrément est poussé par le `GITHUB_TOKEN` du workflow.
4. Créez des releases en fusionnant des PR dans `main`. La pipeline prend
   ~3–5 min pour publier vers PyPI et ~80–90 min de plus (à froid) ou ~5–10 min
   (cache Nuitka chaud) pour que le zip Windows soit attaché.

Le job `publish-pypi` n'attache intentionnellement PAS d'Environment GitHub, de
sorte que chaque exécution apparaît comme une entrée de Release (avec son `.exe`
Nuitka attaché) plutôt que comme un widget « Deployment » dans la barre latérale
de la page d'accueil du dépôt — les releases obtiennent leur propre page dédiée
et une entrée de Deployment par-dessus ne serait que du bruit redondant.

## Licence

Voir `LICENSE`. L'API arXiv est utilisée selon les conditions d'utilisation de
l'API d'arXiv (<https://info.arxiv.org/help/api/tou.html>) — respectez la limite
souple de 1 requête toutes les 3 secondes ; le fetcher fourni l'applique déjà
via son token bucket.
