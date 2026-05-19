Guía de usuario de AutoPaperToPPT
==================================

Asistente de búsqueda de artículos guiado por palabras clave. Recupera
resultados de arXiv, Semantic Scholar, OpenAlex, PubMed, ACM, IEEE
Xplore, DBLP, Crossref, OpenAIRE, Springer Nature y Google Scholar; y
los exporta como presentación PowerPoint estilo tesis, libro Excel y
archivo BibTeX. Todo desde una llamada CLI o una llamada de
herramienta MCP.

.. contents:: Índice
   :depth: 2
   :local:

----

Para agentes de IA que dirigen este proyecto
--------------------------------------------

**Si usted es un LLM (Claude Code, Cursor, Aider, Codex CLI, …) leyendo
esto para entender qué hacer — empiece aquí.** Las mismas reglas están
fijadas en ``AGENTS.md`` (espejo entre agentes) y ``CLAUDE.md``
(referencia canónica) en la raíz del repo; léalos antes de cambios no
triviales.

**El entregable por defecto es un ``.pptx`` enriquecido estilo tesis por
artículo**, no el deck ligero solo-resumen que la CLI produce por
defecto. La salida ligera es un artefacto intermedio — su trabajo es
elevarlo.

Árbol de decisión
^^^^^^^^^^^^^^^^^

1. ¿``ANTHROPIC_API_KEY`` configurada? → ejecute la CLI; se
   auto-enriquece vía API Anthropic.
2. Sin clave, LLM dirige → **usted escribe el resumen enriquecido a
   mano**. Lea cada PDF, redacte ``PaperSummary`` con campos
   rich-tier, deje ``scripts/regen_<query>.py``, ejecute. **No le diga
   al usuario que configure la API key** — usted es el LLM.
3. Sin LLM (CI / cron) → ligero aceptable.

Flujo MCP de 6 pasos
^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   1. (opcional) list_sources()
   2. search(keywords, sources, top_tier_only=true, ...)
   3. (opcional) download_pdfs(papers, out_dir="./exports/...")
   4. fetch_pdf_text(pdf_url=paper.pdf_url)           # por artículo
   5. (lee cada PDF y produce dict summary estructurado)
   6. export(papers=[{...paper, "summary": {...}}], language="es", ...)

Las 11 herramientas MCP completas están en :doc:`/mcp`.

Obligatorio: verificación URL / DOI antes de entregar
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Las rutas URL de las editoriales **no se pueden adivinar** — AAAI usa
IDs numéricos (``v40i5.37389``), IEEE usa ``arnumber`` opaco, ACM usa
DOIs opacos. Al escribir un ``Paper`` a mano, **copie ``url`` /
``doi`` / ``arxiv_id`` literalmente del xlsx que produjo esta
búsqueda** — nunca de memoria, nunca construido desde el título.

El xlsx se escribe en ``exports/<run>/<slug>-<timestamp>.xlsx`` con
columna 7 = DOI, columna 8 = URL. Audite su script regen al terminar:

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

Prohibiciones
^^^^^^^^^^^^^

* No le diga al usuario "configura ``ANTHROPIC_API_KEY``" — usted es el
  LLM.
* No trate el ``.pptx`` ligero como entregable.
* No se detenga cuando ``download_pdfs`` termine.
* No invente números, RQs, contribuciones, limitaciones.
* No fabrique URLs / DOIs / IDs arXiv.
* No deje descargas irrelevantes en el directorio de ejecución. La
  búsqueda por palabras clave puede incluir artículos fuera de tema
  (una consulta "Claude code" trajo un artículo sobre el decodificador
  Viterbi). Elimine ``pdfs/<key>.pdf`` y ``<key>.pptx`` ligeros fuera
  de tema; conserve el xlsx / bib agregado como registro honesto.
  Procedimiento completo en ``CLAUDE.md`` "Pruning irrelevant
  downloads".
* No mencione "Claude", "Claude Code", "AI-generated", "GPT",
  "Copilot" ni ningún nombre de herramienta/modelo IA en commits,
  PRs, código o docs.

Ejemplos: ``scripts/regen_llm_security_batch.py`` (en, 8 artículos) y
``scripts/regen_llm_security_batch_zh_tw.py`` (zh-tw).

----

Instalación
-----------

Requiere Python **3.12+**.

.. code-block:: bash

   git clone <repo-url>
   cd AutoPaperToPPT
   python -m venv .venv
   .venv\Scripts\Activate.ps1            # Windows PowerShell
   # source .venv/bin/activate           # Linux / macOS
   pip install -e .[dev]

Extras opcionales: ``[mcp]``, ``[intelligence]``, ``[web]``, ``[dev]``.

----

Inicio rápido
-------------

.. code-block:: bash

   # Buscar arXiv → deck + workbook + BibTeX
   autopapertoppt --query "diffusion models" --source arxiv --max 10 \
                  --out ./exports/

   # Un solo artículo por URL → deck + BibTeX
   autopapertoppt --paper "https://arxiv.org/abs/1706.03762" \
                  --filename-stem attention --out ./exports/

   # Renderizar deck en español
   autopapertoppt --paper 1706.03762 --lang es --out ./exports/

   # Enriquecimiento Python pipeline (requiere API key Anthropic)
   export ANTHROPIC_API_KEY=sk-ant-...
   autopapertoppt --paper "https://arxiv.org/abs/1706.03762" \
                  --enrich --lang es --out ./exports/

Tabla completa de flags CLI: :doc:`/cli`.

----

Dónde buscar más
----------------

* Flags CLI y variables de entorno: :doc:`/cli`
* 11 herramientas del servidor MCP: :doc:`/mcp`
* Kit de edición PPTX: :doc:`/pptx_editing`
* El archivo ``readmes/README.es.md`` en la raíz del repo tiene la lista
  completa de funcionalidades del proyecto.
* La referencia técnica profunda (arquitectura de plugins, políticas
  de seguridad, Definition of Done, reglas SonarQube, …) está
  consolidada en la guía inglesa: :doc:`/en/index`.
