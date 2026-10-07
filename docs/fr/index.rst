Guide utilisateur ThesisAgents
=================================

Assistant de recherche d'articles piloté par mots-clés. Interroge arXiv,
Semantic Scholar, OpenAlex, PubMed, ACM, IEEE Xplore, DBLP, Crossref,
OpenAIRE, Springer Nature, Europe PMC, DOAJ, HAL, CORE et Google Scholar ; exporte en présentation
PowerPoint style thèse, classeur Excel et fichier BibTeX. Le tout
depuis un seul appel CLI ou un seul appel d'outil MCP.

.. contents:: Sommaire
   :depth: 2
   :local:

----

Pour les agents IA pilotant ce projet
-------------------------------------

**Si vous êtes un LLM (Claude Code, Cursor, Aider, Codex CLI, …) lisant
ceci pour savoir quoi faire — commencez ici.** Les mêmes règles sont
épinglées dans ``AGENTS.md`` (miroir inter-agents) et ``CLAUDE.md``
(référence canonique) à la racine du repo ; lisez-les avant tout
changement non trivial.

**Le livrable par défaut est un ``.pptx`` enrichi style thèse par
article**, pas la présentation légère limitée au résumé que la CLI
produit par défaut. Le rendu léger est un artefact intermédiaire —
votre travail est de l'enrichir.

Arbre de décision
^^^^^^^^^^^^^^^^^

1. ``ANTHROPIC_API_KEY`` définie ? → lancez la CLI ; auto-enrichissement
   via API Anthropic.
2. Pas de clé, LLM pilote → **vous rédigez le résumé enrichi
   vous-même**. Lisez chaque PDF, rédigez un ``PaperSummary`` avec les
   champs rich-tier, déposez ``scripts/regen_<query>.py``, exécutez.
   **Ne dites pas à l'utilisateur de configurer la clé API** — vous
   êtes le LLM.
3. Pas de LLM (CI / cron) → rendu léger acceptable.

Workflow MCP en 6 étapes
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   1. (optionnel) list_sources()
   2. search(keywords, sources, top_tier_only=true, ...)
   3. (optionnel) download_pdfs(papers, out_dir="./exports/...")
   4. fetch_pdf_text(pdf_url=paper.pdf_url)           # par article
   5. (vous lisez chaque PDF et produisez un dict de résumé structuré)
   6. export(papers=[{...paper, "summary": {...}}], language="fr", ...)

17 outils MCP au total : découverte (``list_sources``,
``list_exports``), ``search``, ``snowball``, ``library_add``, ``library_search``, ``library_stats``, ``fetch_paper``, ``fetch_pdf_text``,
``download_pdfs``, ``export`` et six opérations de deck ``pptx_*``
(``pptx_inspect``, ``pptx_review``, ``pptx_update_slide``,
``pptx_delete_slide``, ``pptx_reorder_slides``, ``pptx_add_slide``).
Référence complète : :doc:`/mcp`.

**Pour repérer les résultats hors sujet, partez des conseils de l'outil
lui-même.** ``--diagnostics`` (CLI) ou ``diagnostics=true`` sur l'outil
MCP ``search`` explique le classement : le score de chaque article
réparti en pertinence, récence et citations, les termes de la requête
qui correspondent, et une recommandation ``keep`` / ``review`` /
``prune`` avec le seuil qui l'a déclenchée. La CLI écrit aussi le détail
complet dans ``diagnostics.json`` dans le répertoire de sortie. Les
recommandations sont indicatives et rien n'est supprimé à votre place,
lisez donc les résumés des articles ``review`` et ``prune`` avant de
supprimer quoi que ce soit.

**Vérifiez quelles sources ont répondu.** Chaque réponse de ``search``
contient ``source_stats`` : pour chaque source, combien
d'enregistrements elle a renvoyés, combien d'articles uniques lui sont
attribués après déduplication, et un ``status`` valant ``ok``,
``failed``, ``rate_limited`` ou ``disabled``. Une source en échec est
ignorée sans arrêter la recherche, lisez donc ces chiffres avant de
conclure qu'un sujet compte peu d'articles. La CLI affiche le même
tableau après chaque recherche ``--query``.

**Suivez les citations.** ``--snowball both`` (CLI) ou l'outil
``snowball`` étend les premiers résultats en suivant leurs liens de
citation : ``references`` ajoute ce qu'ils citent et ``cited_by`` ajoute
ce qui les cite. Cela trouve des travaux qu'une recherche par mots-clés
manque parce que les auteurs ont employé d'autres termes. L'extension
est bornée (une étape par défaut), chaque article découvert garde le
chemin qui l'a atteint, et tous sont notés par rapport à vos mots-clés,
si bien qu'un article n'est pas conservé au seul motif qu'il est souvent
cité.

**Conservez ce que vous trouvez.** ``--library thesis.db --library-add``
(CLI) ou l'outil ``library_add`` enregistre les articles d'une exécution
dans une bibliothèque de littérature, un seul fichier SQLite qui survit
à la session. Ajouter de nouveau la même recherche ne duplique rien : un
article est reconnu par son DOI, son identifiant arXiv ou son titre, et
la nouvelle observation est fusionnée dans l'enregistrement conservé.
Ensuite ``library_search`` retrouve les articles conservés sans toucher
au réseau, et les DOI et URL déjà vérifiés ne sont pas revérifiés
pendant 30 jours.

Obligatoire : vérification URL / DOI avant livraison
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Les chemins URL des éditeurs **ne peuvent pas être devinés** — AAAI
utilise des IDs numériques (``v40i5.37389``), IEEE utilise un
``arnumber`` opaque, ACM utilise des DOIs opaques. Quand vous rédigez
un ``Paper`` à la main, **copiez ``url`` / ``doi`` / ``arxiv_id`` mot
pour mot depuis le xlsx produit par cette recherche** — jamais de
mémoire, jamais construit à partir du titre.

Le xlsx est écrit dans ``exports/<run>/<slug>-<timestamp>.xlsx`` avec
colonne 7 = DOI, colonne 8 = URL. Auditez votre script regen à la fin :

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

**L'export le vérifie à l'exécution.** Avant toute écriture, la CLI,
l'outil MCP ``export`` et l'onglet Deck de la GUI interrogent doi.org
pour le DOI de chaque article et demandent chaque URL une fois. Un DOI
non enregistré, une URL qui répond 404 ou un hôte injoignable arrêtent
l'export et indiquent l'article et l'identifiant concernés. Le contrôle
prouve qu'un identifiant existe, pas qu'il appartient à cet article,
donc la règle de copie depuis le xlsx et l'audit ci-dessus restent
nécessaires. Hors ligne, passez ``--no-verify-identifiers`` (CLI) ou
``verify_identifiers=false`` (MCP).

À ne pas faire
^^^^^^^^^^^^^^

* Ne dites pas à l'utilisateur « définissez ``ANTHROPIC_API_KEY`` » —
  vous êtes le LLM.
* Ne considérez pas le ``.pptx`` léger comme livrable.
* Ne vous arrêtez pas quand ``download_pdfs`` finit.
* N'inventez pas chiffres, RQ, contributions, limites.
* Ne fabriquez pas URLs / DOIs / IDs arXiv.
* Ne laissez pas de téléchargements non pertinents dans le répertoire
  d'exécution. La recherche par mots-clés peut ramener des articles
  hors sujet (une requête « Claude code » a ramené un article sur le
  décodeur Viterbi). Supprimez les ``pdfs/<key>.pdf`` et
  ``<key>.pptx`` légers hors sujet ; conservez le xlsx / bib agrégé
  comme trace fidèle. Procédure complète dans ``CLAUDE.md`` « Pruning
  irrelevant downloads ».
* Ne mentionnez pas « Claude », « Claude Code », « AI-generated »,
  « GPT », « Copilot » ni aucun nom d'outil / modèle IA dans les
  commits, PRs, code ou docs.

Exemple travaillé : ``scripts/regen_fang2026.py`` contient un résumé
enrichi rédigé à la main exactement de cette façon (un seul article,
rich-tier, zh-tw). Un lot multi-articles suit la même forme, avec une
entrée par article dans le tuple ``PaperCollection``.

----

Installation
------------

Python **3.12+** requis.

.. code-block:: bash

   git clone <repo-url>
   cd ThesisAgents
   python -m venv .venv
   .venv\Scripts\Activate.ps1            # Windows PowerShell
   # source .venv/bin/activate           # Linux / macOS
   pip install -e .[dev]

Extras optionnels : ``[mcp]``, ``[intelligence]``, ``[web]``, ``[dev]``.

----

Démarrage rapide
----------------

.. code-block:: bash

   # Rechercher arXiv → deck + classeur + BibTeX
   thesisagents --query "diffusion models" --source arxiv --max 10 \
                  --out ./exports/

   # Un seul article par URL → deck + BibTeX
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --filename-stem attention --out ./exports/

   # Rendre la présentation en français
   thesisagents --paper 1706.03762 --lang fr --out ./exports/

   # Enrichissement via pipeline Python (clé Anthropic requise)
   export ANTHROPIC_API_KEY=sk-ant-...
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --enrich --lang fr --out ./exports/

Tableau complet des flags CLI : :doc:`/cli`.

----

Où chercher plus loin
---------------------

* Flags CLI + variables d'environnement : :doc:`/cli`
* 17 outils du serveur MCP : :doc:`/mcp`
* Boîte à outils d'édition PPTX : :doc:`/pptx_editing`
* Le fichier ``readmes/README.fr.md`` à la racine du repo donne la liste
  complète des fonctionnalités.
* La référence technique approfondie (architecture de plugins,
  politique de sécurité, Definition of Done, règles SonarQube, …)
  est consolidée dans le guide anglais : :doc:`/en/index`.
