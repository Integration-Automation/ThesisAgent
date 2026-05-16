# AutoPaperToPPT

> **Idiomas**: [English](README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · **Español** · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **Documentación**: [autopapertoppt.readthedocs.io](https://autopapertoppt.readthedocs.io/en/latest/)

Asistente de búsqueda de artículos guiado por palabras clave que recupera resultados de arXiv, Semantic Scholar, OpenAlex, PubMed, ACM (vía Crossref), IEEE Xplore, DBLP, Crossref genérico, OpenAIRE, Springer Nature y Google Scholar; los normaliza a un único formato de registro y exporta el conjunto deduplicado como una **presentación PowerPoint estilo tesis**, un **libro Excel** y un **archivo BibTeX** — todo desde una llamada CLI o una llamada de herramienta MCP. Opcionalmente enriquece cada artículo leyendo su PDF y produciendo un resumen estructurado, ya sea en contexto (flujo LLM-as-agent) o mediante la API de Anthropic (flujo Python pipeline).

## Para agentes de IA que dirigen este proyecto

**Si usted es un LLM (Claude Code, Cursor, Aider, Codex CLI, …) leyendo este README para entender qué hacer — empiece aquí.** Todo lo siguiente también está fijado en [`AGENTS.md`](AGENTS.md) (espejo entre agentes) y [`CLAUDE.md`](CLAUDE.md) (referencia canónica); léalos antes de hacer cambios no triviales.

### Lo que el usuario realmente quiere

El entregable por defecto es **un `.pptx` enriquecido estilo tesis por artículo**, no la presentación ligera basada solo en el resumen que la CLI produce por defecto. La salida ligera es un artefacto intermedio — su trabajo es elevarlo.

### Árbol de decisión

1. ¿Está `ANTHROPIC_API_KEY` configurada en el entorno? → ejecute la CLI; se auto-enriquece vía la API de Anthropic. Listo.
2. Sin clave, pero usted (un LLM) dirige la sesión → **usted produce el resumen enriquecido**. Lea cada PDF, redacte a mano un `PaperSummary` con campos de nivel enriquecido (`pain_points`, `research_question`, `contributions_detailed`, `headline_metrics`, `technique_table`, `method_sections`, `evaluation_sections`, `system_flow`, `research_questions`, `rq_results`, `core_observation`, `limitations`, `future_work`), deje un `scripts/regen_<query>.py` y ejecútelo. **No le diga al usuario que configure la API key** — usted es el LLM que habría escrito el resumen.
3. Sin LLM en el bucle (CI / cron / desatendido) → la salida ligera es aceptable.

### Flujo MCP de 6 pasos

```
1. (opcional) list_sources()                              # qué plugins están habilitados
2. search(keywords, sources, top_tier_only=true, ...)
3. (opcional) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # por artículo
5. (usted lee cada PDF y produce un dict de resumen estructurado)
6. export(papers=[{...paper, "summary": {...}}], language="es", ...)
```

Las once herramientas MCP (incluyendo `list_sources`, `download_pdfs`, `pptx_inspect` / `pptx_update_slide` / `pptx_add_slide` / etc.) están documentadas en [`docs/mcp.md`](docs/mcp.md).

### Obligatorio: verificación de URL / DOI antes de entregar

Las rutas de URL de las editoriales **no pueden adivinarse** — AAAI usa identificadores numéricos (`v40i5.37389`), IEEE usa un opaco `arnumber`, ACM usa DOIs opacos. Al redactar un `Paper` a mano, **copie `url` / `doi` / `arxiv_id` literalmente desde el xlsx que esta búsqueda produjo** — nunca de memoria, nunca construido desde el título.

El xlsx se escribe en `exports/<run>/<slug>-<timestamp>.xlsx` con columna 7 = DOI, columna 8 = URL. Audite su script regen al terminar:

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

Dos fabricaciones detectadas así en producción: volumen AAAI incorrecto (`v39i23.34521` vs. el real `v39i22.34537`) y ruta inventada con slug de autor (`view/fang2026` en lugar de `v40i5.37389`).

### Ejemplo trabajado

[`scripts/regen_llm_security_batch.py`](scripts/regen_llm_security_batch.py) incluye 8 resúmenes enriquecidos escritos a mano siguiendo este proceso. Úselo como plantilla para cualquier búsqueda multi-artículo. La versión zh-tw está en [`scripts/regen_llm_security_batch_zh_tw.py`](scripts/regen_llm_security_batch_zh_tw.py).

### Prohibiciones

- **No** termine una búsqueda multi-artículo diciéndole al usuario "configura `ANTHROPIC_API_KEY` para una presentación enriquecida" — usted es el LLM que habría escrito los resúmenes.
- **No** trate el `.pptx` ligero por artículo como el entregable.
- **No** se detenga cuando `download_pdfs` informe N PDFs guardados — ese es el inicio de la fase de redacción enriquecida, no el final.
- **No** invente números, RQs, contribuciones o limitaciones que no estén en el artículo.
- **No** fabrique URLs / DOIs / IDs de arXiv — vea la regla arriba.
- **No** deje descargas irrelevantes en el directorio de ejecución. La búsqueda por palabras clave a veces incluye artículos fuera de tema (una consulta "Claude code" trajo un artículo sobre el decodificador Viterbi; "LLM code review" trajo una revisión sobre detección de objetos). Tras clasificar artículos como fuera de tema, elimine sus `pdfs/<key>.pdf` y el `<key>.pptx` ligero; conserve el xlsx / bib agregado como registro honesto de lo que devolvió la búsqueda.
- **No** mencione "Claude", "Claude Code", "AI-generated", "GPT", "Copilot" ni ningún nombre de herramienta/modelo de IA en mensajes de commit, descripciones de PR, comentarios de código o documentación.

## Funcionalidades

- **Once fuentes pluggables**: `arxiv`, `semantic_scholar`, `openalex`, `pubmed`, `acm` (limitado a ACM vía Crossref), `dblp`, `crossref` (genérico), `openaire`, `springer` (requiere API key), `ieee` (API key o scraping opt-in), `scholar` (scraping opt-in). Cada una vive bajo `sources/<name>/` detrás de un adaptador `Fetcher`. Una lista blanca de revistas de primer nivel filtra los resultados a conferencias/revistas CS bandera más Nature/Science/PNAS por defecto; pase `--all-venues` para desactivar.
- **Modo de artículo único**: pegue un ID arXiv, URL arXiv, DOI, PMID o URL de documento IEEE — AutoPaperToPPT lo resuelve vía la fuente correcta y emite el mismo paquete de exportación. Útil para notas de lectura y preparación de defensa.
- **Modo PDF local** (`--pdf <path>`): pase un PDF o un directorio. Un extractor heurístico obtiene **título, autores, año, ID arXiv, DOI y el resumen real** directamente del prefacio de cada PDF (anclado en el encabezado explícito `Abstract` / `ABSTRACT` / `摘要`, no en un prefijo ciego). `--title` / `--authors` / `--year` / `--venue` / `--doi` / `--arxiv-id` sobrescriben en una llamada de un solo PDF; en modo directorio, la extracción por archivo gana, así cada artículo obtiene su propia presentación nombrada con su clave BibTeX.
- **Cinco exportadores**:
  - `.pptx` — pantalla ancha 16:9, numerada, tres niveles de renderizado (ligero solo-resumen · enriquecido-plano · **estilo tesis** con cuadrantes de puntos de dolor, KPIs destacados, tablas de comparación de técnicas, tablas de resultados por RQ, resumen de contribuciones, observación central, limitaciones y trabajo futuro, Q&A, referencias). Todas las cadenas de plantilla están i18n en **14 idiomas**: English, 繁體中文, 简体中文, 日本語, Español, Français, Deutsch, 한국어, Português, Русский, Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia.
  - `.xlsx` — hoja Papers + hoja de procedencia Query, URL/PDF con hipervínculos, cabecera fija, anchos de columna auto. La columna 5 (**Source**) muestra el lugar real de publicación (p. ej. "IEEE Access"); la columna 6 (**Indexed via**) muestra qué fetcher devolvió los metadatos (p. ej. "openalex"), evitando que los dos datos se confundan.
  - `.md` — lista completa fuente / título / resumen.
  - `.bib` — claves de cita sin colisión, campos con escape LaTeX.
  - `.json` — payload bruto para herramientas downstream.
- **Kit de edición PPT**: `autopapertoppt.exporters.pptx_edit` (inspect / update_slide / delete_slide / reorder_slides / add_slide) funciona contra cualquier presentación que el exportador produzca, más las herramientas MCP equivalentes `pptx_*` para que un agente LLM pueda iterar sobre la presentación.
- **Servidor MCP**: 11 herramientas — `list_sources` (descubrimiento), `search`, `fetch_paper`, `fetch_pdf_text`, `download_pdfs`, `export` y las cinco de edición `pptx_*`. Permite a cualquier LLM compatible con MCP (Claude Code, Claude Desktop, Cursor, …) dirigir el flujo completo.
- **Dos rutas de enriquecimiento** para ir más allá del resumen hacia una presentación auténtica estilo tesis:
  - **LLM-as-agent (sin API key)** — el LLM que llama lee el texto del PDF vía `fetch_pdf_text`, escribe un resumen estructurado en contexto y lo pasa a `export`.
  - **Pipeline Python (`--enrich`)** — la CLI llama a la API de Anthropic directamente; modelo por defecto `claude-opus-4-7`.
- **Seguridad por defecto**: transporte HTTP solo-HTTPS, límite de tasa por fuente (token bucket), `defusedxml` para cualquier payload XML, rutas de exportación seguras frente a path-traversal, sin `eval` / `exec` / `pickle` sobre entrada del usuario. Scraping de Scholar e IEEE deshabilitado por defecto (opt-in vía env var).

## Inicio rápido

```powershell
git clone <repo-url>
cd AutoPaperToPPT
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Instalar con extras dev (también incluye SDK MCP y dependencias intelligence)
pip install -e .[dev]
```

Buscar arXiv y exportar presentación + libro + BibTeX (default para `--query`):

```powershell
py -m autopapertoppt --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

Recuperar un solo artículo por URL — default `.pptx + .bib` (un `.xlsx` de una fila no tiene mucho sentido):

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

Renderizar la presentación en español:

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --lang es --out .\exports\
```

Enriquecimiento pipeline LLM (Python llama a Anthropic — requiere API key):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang es --out .\exports\
```

## Flags CLI

| Flag | Propósito |
|---|---|
| `--query` / `-q` | Palabras clave (obligatorio salvo con `--paper`). |
| `--paper` / `-p` | ID/URL arXiv, DOI, PMID o URL de documento IEEE. Excluyente con `--query`. |
| `--source` / `-s` | Lista de fuentes separadas por coma. Default `arxiv`. |
| `--max` / `-n` | Resultados máximos por fuente (1..200). Default 25. |
| `--year-from` / `--year-to` | Filtro de año inclusivo. |
| `--export` / `-e` | Formatos: cualquiera de `pptx,xlsx,md,bib,json`. Default depende del modo (ver abajo). |
| `--out` / `-o` | Directorio de salida. Default `./exports`. |
| `--filename-stem` | Sobrescribe el stem de nombre generado. |
| `--no-abstract` | Omite contenido del resumen en las exportaciones. |
| `--lang` / `-l` | Idioma de la presentación: uno de 14 — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. Default `en`. |
| `--enrich` | Descarga PDF + resumen por Anthropic. Requiere `ANTHROPIC_API_KEY` y el extra `[intelligence]`. |
| `--lightweight` | Fuerza la presentación ligera aunque `ANTHROPIC_API_KEY` esté configurada. |
| `--llm-model` | Sobrescribe el modelo por defecto `claude-opus-4-7`. |
| `--all-venues` | Desactiva la lista blanca de revistas (default conserva sedes CS bandera + Nature / Science / PNAS / CACM / LNCS). |
| `--paywall-threshold` | Fracción de resultados con paywall que dispara el prompt de confirmación. Default 0.30. |
| `--yes` | Salta el prompt de paywall. |
| `--max-slides` | Tope de diapositivas por artículo (default 25; pase 0 para ilimitado). |
| `--quiet` | Suprime la impresión por artículo. |

### Variables de entorno

| Variable | Usada por | Propósito |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | Auth del LLM. No necesaria para la ruta LLM-as-agent vía MCP. |
| `AUTOPAPERTOPPT_LLM_MODEL` | `--enrich` | Sobrescribe el default `claude-opus-4-7`. |
| `AUTOPAPERTOPPT_S2_API_KEY` | Semantic Scholar | Límite de tasa más alto. Opcional. |
| `AUTOPAPERTOPPT_NCBI_API_KEY` | PubMed | Eleva el límite anónimo de NCBI (3/s) a 10/s. Opcional. |
| `AUTOPAPERTOPPT_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex | Pone las peticiones en el pool cortés de Crossref. |
| `AUTOPAPERTOPPT_IEEE_API_KEY` | IEEE (ruta API) | API oficial IEEE Xplore; expone `pdf_url` para artículos en el alcance de la subscripción. |
| `AUTOPAPERTOPPT_ENABLE_IEEE_SCRAPING` | IEEE (ruta scraping) | `=1` activa scraping. No necesaria cuando la API key está configurada. |
| `AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Token de subscriptor Crossref Plus (cabecera Bearer). Opcional. |
| `AUTOPAPERTOPPT_SPRINGER_API_KEY` | Springer | Obligatoria; clave gratuita en <https://dev.springernature.com/>. El plugin se omite silenciosamente sin ella. |
| `AUTOPAPERTOPPT_ENABLE_SCHOLAR_SCRAPING` | Google Scholar | `=1` activa scraping. Por defecto deshabilitado — los ToS de Scholar prohíben scraping. |
| `AUTOPAPERTOPPT_PDF_COOKIES_FILE` | Descargador PDF | `cookies.txt` formato Netscape. Por defecto deshabilitado. Use solo con editoriales para las que tenga derechos institucionales. |
| `AUTOPAPERTOPPT_LOG_LEVEL` | logger | `INFO` por defecto; `DEBUG` para trazas verbosas. |

Defaults: `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. Siempre sobrescribibles con `--export` explícito.

## Servidor MCP

Registrar con Claude Code:

```powershell
claude mcp add autopapertoppt -- ".venv\Scripts\python.exe" -m autopapertoppt.mcp
```

O editar el archivo de configuración:

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

Herramientas:

| Herramienta | Propósito |
|---|---|
| `list_sources` | Enumera cada plugin + reporta si cada uno está habilitado en el entorno actual. Llamar una vez antes de `search`. |
| `search` | Palabras clave → lista de artículos. Acepta `top_tier_only`, `min_citations`; por defecto la mezcla completa sin API key. |
| `fetch_paper` | Identificador arXiv / DOI / PMID / IEEE → un solo artículo. |
| `fetch_pdf_text` | Descarga un PDF, retorna el texto extraído. **La ruta MCP para "leí el artículo".** |
| `download_pdfs` | Descarga por lotes los PDFs de una lista de artículos a `{out_dir}/pdfs/`. Retorna resultados por artículo indexados por clave BibTeX. |
| `export` | Lista de artículos + formatos → escribe `.pptx/.xlsx/.md/.bib/.json`. Acepta un campo `summary` por artículo para el schema estilo tesis enriquecido y `max_slides_per_paper` (default 25). |
| `pptx_inspect` | Lee la estructura de slide / shape de una presentación existente. |
| `pptx_update_slide` | Reemplaza `title` / `body` / `meta` (por nombre de shape) o shapes arbitrarios por índice. |
| `pptx_delete_slide` | Elimina una diapositiva y su part relationship. |
| `pptx_reorder_slides` | Reordena diapositivas vía `sldIdLst`. |
| `pptx_add_slide` | Añade al final o inserta una nueva diapositiva title / body / meta. |

Flujo LLM-as-agent (sin `ANTHROPIC_API_KEY` — el LLM es el agente):

```
1. (opcional) list_sources()                       # descubre plugins habilitados
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (opcional) download_pdfs(papers, out_dir="./exports/...")  # persiste PDFs
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # por artículo
5. (el LLM lee el texto, produce un dict `summary` estructurado)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="es", formats=["pptx","bib"], ...)
```

Referencia completa en [`docs/mcp.md`](docs/mcp.md).

## Estructura del proyecto

```
AutoPaperToPPT/
├── autopapertoppt/                 # paquete principal
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # cliente async solo-HTTPS, rate limit token bucket
│   ├── exporters/                   # pptx (estilo tesis) · xlsx · bib · md · json · pptx_edit · i18n
│   ├── intelligence/                # descarga PDF + resumidor Anthropic ([intelligence] extra)
│   ├── mcp/                         # servidor FastMCP (11 herramientas)
│   ├── utils/                       # logging, path safety
│   ├── cli.py                       # CLI argparse
│   └── __main__.py
├── sources/                         # carpetas plugin: arxiv, semantic_scholar,
│                                    #   openalex, pubmed, acm, ieee, scholar,
│                                    #   dblp, crossref, openaire, springer
├── tests/                           # suite pytest + fixtures grabadas (sin HTTP vivo)
├── docs/                            # Sphinx (14 árboles de idiomas)
├── scripts/                         # scripts regen únicos
└── pyproject.toml                   # ruff, bandit, build, extras opcionales
```

## Definition of Done

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r autopapertoppt/ sources/
```

El flag `-c` de bandit es obligatorio — sin él, bandit ignora la configuración skip del proyecto. Al tocar el exportador pptx, ejecute también una comprobación de desbordamiento (ver `CLAUDE.md` "Slide Deck Rules").

## Licencia

Ver `LICENSE`. La API de arXiv se usa bajo sus términos (<https://info.arxiv.org/help/api/tou.html>) — respete el límite soft de 1 petición por 3 segundos; el fetcher incluido ya lo impone vía su token bucket.
