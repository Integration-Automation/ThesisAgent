Guía de usuario de ThesisAgents
==================================

Asistente de búsqueda de artículos guiado por palabras clave. Recupera
resultados de arXiv, Semantic Scholar, OpenAlex, PubMed, ACM, IEEE
Xplore, DBLP, Crossref, OpenAIRE, Springer Nature, Europe PMC, DOAJ, HAL, CORE y Google Scholar; y
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

18 herramientas MCP en total: descubrimiento (``list_sources``,
``list_exports``), ``search``, ``snowball``, ``library_add``, ``library_search``, ``library_stats``, ``fetch_paper``, ``fetch_pdf_text``,
``download_pdfs``, ``pptx_validate_template``, ``export`` y seis operaciones de deck ``pptx_*``
(``pptx_inspect``, ``pptx_review``, ``pptx_update_slide``,
``pptx_delete_slide``, ``pptx_reorder_slides``, ``pptx_add_slide``).
Referencia completa: :doc:`/mcp`.

**Para detectar resultados fuera de tema, empiece por el consejo de la
propia herramienta.** ``--diagnostics`` (CLI) o ``diagnostics=true`` en
la herramienta MCP ``search`` explica la clasificación: la puntuación de
cada artículo dividida en relevancia, actualidad y citas, los términos
de la consulta que coincidieron y una recomendación ``keep`` /
``review`` / ``prune`` con el umbral que la motivó. La CLI también
escribe el desglose completo en ``diagnostics.json`` dentro del
directorio de salida. Las recomendaciones son orientativas y no se
elimina nada por usted, así que lea los resúmenes de los artículos
``review`` y ``prune`` antes de borrar algo.

**Compruebe qué fuentes respondieron.** Cada respuesta de ``search``
incluye ``source_stats``: para cada fuente, cuántos registros devolvió,
cuántos artículos únicos se le atribuyen tras la deduplicación y un
``status`` que vale ``ok``, ``failed``, ``rate_limited`` o ``disabled``.
Una fuente que falla se omite sin detener la búsqueda, así que lea estos
recuentos antes de concluir que un tema tiene pocos artículos. La CLI
imprime la misma tabla tras cada búsqueda ``--query``.

**Siga las citas.** ``--snowball both`` (CLI) o la herramienta
``snowball`` amplía los primeros resultados siguiendo sus enlaces de
citación: ``references`` añade lo que citan y ``cited_by`` añade lo que
los cita. Encuentra trabajos que una búsqueda por palabras clave pierde
porque los autores usaron otros términos. La ampliación está acotada (un
paso por defecto), cada artículo descubierto conserva el camino que lo
alcanzó, y todos se puntúan frente a sus palabras clave, de modo que un
artículo no se conserva solo por ser muy citado.

**Conserve lo que encuentra.** ``--library thesis.db --library-add``
(CLI) o la herramienta ``library_add`` guarda los artículos de una
ejecución en una biblioteca de literatura, un único archivo SQLite que
sobrevive a la sesión. Añadir de nuevo la misma búsqueda no duplica
nada: un artículo se reconoce por su DOI, su ID de arXiv o su título, y
la nueva observación se fusiona con el registro guardado. Después
``library_search`` encuentra los artículos guardados sin tocar la red, y
los DOI y URL ya verificados no se vuelven a comprobar durante 30 días.

**Use su propia plantilla.** ``--pptx-template thesis.pptx`` (CLI) o
``pptx_template`` en la herramienta ``export`` construye la presentación
sobre una plantilla de PowerPoint, de modo que el fondo, el logotipo y
los diseños son los suyos. Ejecute antes ``thesisagents
validate-template thesis.pptx`` (o la herramienta
``pptx_validate_template``): lista qué diseño usaría cada tipo de
diapositiva y le dice qué corregir. Una plantilla necesita diapositivas
16:9 y un diseño para el contenido, y un pequeño archivo de
configuración puede asignar diseños, fuentes y colores.

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

**La exportación lo comprueba en tiempo de ejecución.** Antes de
escribir nada, la CLI, la herramienta MCP ``export`` y la pestaña Deck
de la GUI consultan el DOI de cada artículo en doi.org y solicitan cada
URL una vez. Un DOI no registrado, una URL que responde 404 o un host
inalcanzable detienen la exportación e indican el artículo y el
identificador. La comprobación demuestra que un identificador existe, no
que pertenezca a este artículo, por lo que la regla de copiar desde el
xlsx y la auditoría anterior siguen siendo necesarias. Sin conexión, use
``--no-verify-identifiers`` (CLI) o ``verify_identifiers=false`` (MCP).

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

Ejemplo trabajado: ``scripts/regen_fang2026.py`` incluye un resumen
enriquecido escrito a mano exactamente de esta manera (un solo
artículo, rich-tier, zh-tw). Un lote multi-artículo sigue la misma
forma, con una entrada por artículo en la tupla ``PaperCollection``.

----

Instalación
-----------

Requiere Python **3.12+**.

.. code-block:: bash

   git clone <repo-url>
   cd ThesisAgents
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
   thesisagents --query "diffusion models" --source arxiv --max 10 \
                  --out ./exports/

   # Un solo artículo por URL → deck + BibTeX
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --filename-stem attention --out ./exports/

   # Renderizar deck en español
   thesisagents --paper 1706.03762 --lang es --out ./exports/

   # Enriquecimiento Python pipeline (requiere API key Anthropic)
   export ANTHROPIC_API_KEY=sk-ant-...
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --enrich --lang es --out ./exports/

Tabla completa de flags CLI: :doc:`/cli`.

----

Dónde buscar más
----------------

* Flags CLI y variables de entorno: :doc:`/cli`
* 18 herramientas del servidor MCP: :doc:`/mcp`
* Kit de edición PPTX: :doc:`/pptx_editing`
* El archivo ``readmes/README.es.md`` en la raíz del repo tiene la lista
  completa de funcionalidades del proyecto.
* La referencia técnica profunda (arquitectura de plugins, políticas
  de seguridad, Definition of Done, reglas SonarQube, …) está
  consolidada en la guía inglesa: :doc:`/en/index`.
