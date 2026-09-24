# ThesisAgents

[![CI](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![Python](https://img.shields.io/pypi/pyversions/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/ThesisAgents.svg)](https://github.com/Integration-Automation/ThesisAgents/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/thesisagents/badge/?version=latest)](https://thesisagents.readthedocs.io/en/latest/)

> **Idiomas**: [English](../README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · **Español** · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **Documentación**: [thesisagents.readthedocs.io](https://thesisagents.readthedocs.io/en/latest/)

Un asistente de búsqueda de artículos guiado por palabras clave que recupera
resultados de arXiv, Semantic Scholar, OpenAlex, PubMed, ACM (vía Crossref),
IEEE Xplore, DBLP, Crossref genérico, OpenAIRE, Springer Nature, Europe PMC,
DOAJ, HAL, CORE y Google Scholar,
los normaliza a un único formato de registro y exporta el conjunto
deduplicado como una **presentación PowerPoint estilo tesis**, un **libro de
Excel** y un **archivo BibTeX** — todo desde una sola llamada CLI o una sola
llamada de herramienta MCP. Opcionalmente enriquece cada artículo leyendo su
PDF y produciendo un resumen estructurado por artículo, ya sea en contexto
(flujo LLM-as-agent) o mediante la API de Anthropic (flujo Python pipeline).

## Para agentes de IA que dirigen este proyecto

**Si usted es un LLM (Claude Code, Cursor, Aider, Codex CLI, …) leyendo este
README para entender qué hacer — empiece aquí.** Todo lo siguiente también
está fijado en [`AGENTS.md`](AGENTS.md) (espejo entre agentes) y
[`CLAUDE.md`](CLAUDE.md) (referencia canónica); léalos antes de hacer cambios
no triviales.

### Lo que el usuario realmente quiere

El entregable por defecto es **un `.pptx` enriquecido estilo tesis por
artículo**, no la presentación ligera basada solo en el resumen que la CLI
produce por defecto. La salida ligera es un artefacto intermedio — su trabajo
es elevarlo.

### Árbol de decisión

1. ¿Está `ANTHROPIC_API_KEY` configurada en el entorno? → simplemente ejecute
   la CLI; se auto-enriquece vía la API de Anthropic. Ha terminado.
2. Sin clave, pero usted (un LLM) dirige la sesión → **usted produce el
   resumen enriquecido**. Lea cada PDF, redacte a mano un `PaperSummary` con
   campos de nivel enriquecido (`pain_points`, `research_question`,
   `contributions_detailed`, `headline_metrics`, `technique_table`,
   `method_sections`, `evaluation_sections`, `system_flow`,
   `research_questions`, `rq_results`, `core_observation`, `limitations`,
   `future_work`), deje un `scripts/regen_<query>.py` y ejecútelo. **No le diga
   al usuario que configure la API key** — usted es el LLM que habría escrito
   el resumen.
3. Sin LLM en el bucle (CI / cron / desatendido) → la salida ligera es
   aceptable.

### Flujo MCP de 6 pasos

```
1. (optional) list_sources()                              # see which plugins are enabled
2. search(keywords, sources, top_tier_only=true, ...)
3. (optional) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # per paper
5. (you read each PDF and produce a structured summary dict)
6. export(papers=[{...paper, "summary": {...}}], language="zh-tw", ...)
```

Las trece herramientas MCP (incluyendo `list_sources`, `list_exports`,
`download_pdfs`, `pptx_inspect` / `pptx_review` / `pptx_update_slide` /
`pptx_add_slide` / etc.) están
documentadas en [`docs/mcp.md`](docs/mcp.md).

### Obligatorio: verificación de URL / DOI antes de entregar

Las rutas de URL de las editoriales **no pueden adivinarse** — AAAI usa
identificadores numéricos (`v40i5.37389`), IEEE usa un `arnumber` opaco, ACM
usa DOIs opacos. Al redactar un `Paper` a mano, **copie `url` / `doi` /
`arxiv_id` literalmente desde el xlsx de búsqueda que produjo esta
ejecución** — nunca de memoria, nunca construido desde el título.

El xlsx se escribe en `exports/<run>/<slug>-<timestamp>.xlsx` con la
columna 7 = DOI, columna 8 = URL. Audite su script de regen cuando
termine:

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

Dos fabricaciones detectadas así en producción: volumen AAAI incorrecto
(`v39i23.34521` vs. el real `v39i22.34537`) y ruta inventada con slug de autor
(`view/fang2026` en lugar de `v40i5.37389`).

### Obligatorio: podar las descargas irrelevantes antes de entregar

La coincidencia de la búsqueda se basa en palabras clave, así que artículos
fuera de tema se colarán: una consulta «Claude code» devolvió un artículo
sobre un decodificador de Viterbi porque ambos contienen «code»; «LLM code
review» coincidió con una revisión de literatura sobre detección de objetos.
Una vez que haya leído los resúmenes y clasifique un artículo como fuera de
tema respecto a la intención real del usuario, pode el directorio de
ejecución:

```python
from pathlib import Path
run = Path("exports/<run>")
irrelevant_keys = ("key-of-off-topic-paper-1", "key-of-off-topic-paper-2")
for key in irrelevant_keys:
    for path in (run / "pdfs" / f"{key}.pdf", run / f"{key}.pptx"):
        if path.exists():
            path.unlink()
```

Elimine `exports/<run>/pdfs/<key>.pdf` + `exports/<run>/<key>.pptx`.
**Conserve** el `<slug>-<timestamp>.xlsx` / `.bib` agregado — esos son el
registro honesto de lo que devolvió la búsqueda. Los casos límite reciben un
resumen enriquecido; es mejor incluir de más que descartar silenciosamente una
posible coincidencia.

### Ejemplo trabajado

[`scripts/regen_fang2026.py`](scripts/regen_fang2026.py) incluye un resumen
enriquecido escrito a mano construido exactamente de esta manera (un solo
artículo, nivel rico, zh-tw, cada campo rico rellenado). Una búsqueda
multi-artículo sigue la misma forma con una entrada
`Paper(...summary=PaperSummary(...))` por artículo en la tupla
`PaperCollection`.

### Prohibiciones

- **No** termine una búsqueda multi-artículo diciéndole al usuario «configura
  `ANTHROPIC_API_KEY` para una presentación enriquecida» — usted es el LLM que
  habría escrito los resúmenes.
- **No** trate el `.pptx` ligero por artículo como el entregable.
- **No** se detenga cuando `download_pdfs` informe N PDFs guardados — ese es el
  inicio de la fase de redacción enriquecida, no el final.
- **No** invente números, RQs, contribuciones o limitaciones que no estén en el
  artículo.
- **No** fabrique URLs / DOIs / IDs de arXiv — vea la regla de arriba.
- **No** deje descargas irrelevantes en el directorio de ejecución. La
  búsqueda por palabras clave a veces incluye artículos fuera de tema (una
  consulta «Claude code» trajo un artículo sobre un decodificador de Viterbi;
  «LLM code review» trajo una revisión de literatura sobre detección de
  objetos). Tras clasificar artículos como fuera de tema, elimine sus
  `pdfs/<key>.pdf` y el `<key>.pptx` ligero; conserve el xlsx / bib agregado
  como el registro honesto de lo que devolvió la búsqueda.
- **No** mencione «Claude», «Claude Code», «AI-generated», «GPT», «Copilot» ni
  ningún nombre de herramienta/modelo de IA en mensajes de commit,
  descripciones de PR, comentarios de código o documentación.

## Funcionalidades

- **Quince fuentes conectables**: `arxiv`, `semantic_scholar`, `openalex`,
  `pubmed`, `acm` (limitado a Crossref), `dblp`, `crossref` (sin límite),
  `openaire`, `springer` (necesita clave API), `europepmc` (abierto, sin clave
  — ciencias de la vida + preprints + agricultura), `doaj` (abierto, sin clave
  — revistas de acceso abierto, normalmente con un enlace directo al PDF),
  `hal` (abierto, sin clave — el archivo francés de informática / matemáticas /
  física con PDFs de texto completo), `core` (necesita clave API gratuita — el
  mayor agregador de acceso abierto, más de 250 M de obras), `ieee` (activo por
  defecto vía Chrome visible; una clave API añade la API oficial de Xplore),
  `scholar` (activo por defecto vía Chrome visible). Cada una vive en
  `sources/<name>/` detrás de un adaptador `Fetcher`. Pase `--top-tier-only`
  para filtrar los resultados a conferencias/revistas bandera de informática
  más Nature/Science/PNAS. La búsqueda por defecto conserva todas las sedes.
- **Modo de artículo único**: pegue un ID arXiv, una URL arXiv, un DOI, un PMID
  o una URL de documento IEEE — ThesisAgents lo resuelve vía la fuente correcta
  y emite el mismo paquete de exportación. Útil para notas de lectura de
  artículos y preparación de la defensa de tesis.
- **Modo PDF local** (`--pdf <path>`): pase un PDF o un directorio.
  Un extractor heurístico obtiene **título, autores, año, ID arXiv, DOI y el
  resumen real** directamente del prefacio de cada PDF (anclado en el
  encabezado explícito `Abstract` / `ABSTRACT` / `摘要`, no en un prefijo
  ciego). `--title` / `--authors` / `--year` / `--venue` / `--doi` /
  `--arxiv-id` sobrescriben en una llamada de un solo PDF; en un directorio, la
  extracción por archivo gana, así cada artículo obtiene su propia presentación
  nombrada con su clave BibTeX.
- **Ocho exportadores**:
  - `.pptx` — pantalla ancha 16:9, con números de página, tres niveles de
    renderizado (ligero solo-resumen · enriquecido-plano · **estilo tesis** con
    cuadrantes de puntos de dolor, KPIs destacados, tablas de comparación de
    técnicas, tablas de resultados por RQ, resumen de contribuciones,
    observación central, limitaciones y trabajo futuro, Q&A, referencias).
    Todas las cadenas de plantilla están i18n en **14 idiomas**: English, 繁體中文,
    简体中文, 日本語, Español, Français, Deutsch, 한국어, Português, Русский,
    Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia.
  - **Identidad visual de presentación diseñada** (no la apariencia por defecto
    Calibri sobre blanco): tipografía por idioma (Inter para el latino,
    Microsoft JhengHei UI / YaHei UI / Yu Gothic UI / Malgun Gothic / Nirmala
    UI para CJK + hindi), geometría de acento programática (barra de acento
    superior en cada diapositiva de contenido + banda izquierda en la portada),
    formato de tabla de estilo académico (rejilla por defecto eliminada, regla
    de cabecera azul marino, separadores suaves entre filas, franja de filas
    alternas, alineación vertical centrada, etiquetas de fila en negrita), y una
    disciplina de paleta de cinco colores (azul marino / turquesa / gris / claro
    / blanco) con el rojo **prohibido** para el texto (use en su lugar negrita +
    turquesa `#0E7490` para enfatizar).
  - **El modo claro es la ruta de renderizado por defecto.** Pase `--dark-mode`,
    active **Dark mode** en la pestaña Deck de la GUI, o configure
    `ExportOptions(dark_mode=True)` para aplicar el post-pass oscuro (fondo de
    diapositiva `#12151B`, texto de cuerpo `#E5E7EB`).
  - `.xlsx` — hoja Papers + hoja de procedencia de la Query, URL / PDF con
    hipervínculos, cabecera fija, anchos de columna automáticos. La columna 5
    (**Source**) muestra el lugar real de publicación (p. ej. «IEEE Access»); la
    columna 6 (**Indexed via**) muestra qué fetcher devolvió los metadatos
    (p. ej. «openalex»), de modo que los dos datos nunca se confundan.
  - `.md` — lista completa de fuente / título / resumen.
  - `.bib` — claves de cita sin colisión, campos con escape para LaTeX.
  - `.json` — payload bruto para herramientas downstream.
  - `.ris` — intercambio RIS importado por Zotero / Mendeley / EndNote /
    RefWorks (el hermano de BibTeX para gestores de referencias no-LaTeX).
  - `.csv` — tabla plana de una fila por artículo para hojas de cálculo / triaje
    rápido con grep (comillas RFC-4180, de modo que las comas en los títulos
    nunca desplacen columnas).
  - `.csl.json` — CSL-JSON para Pandoc / citeproc; renderice una bibliografía en
    cualquier estilo CSL (APA, IEEE, Nature, …). La extensión `.csl.json` la
    mantiene distinta del volcado `.json` simple.
- **Kit de edición PPT**: `thesisagents.exporters.pptx_edit`
  (inspect / update_slide / delete_slide / reorder_slides / add_slide)
  funciona contra cualquier presentación que el exportador produzca, más las
  herramientas MCP `pptx_*` equivalentes para que un agente LLM pueda iterar
  sobre una presentación generada.
- **Servidor MCP**: 13 herramientas — `list_sources` + `list_exports`
  (descubrimiento), `search`, `fetch_paper`, `fetch_pdf_text`,
  `download_pdfs`, `export`, y las seis herramientas de deck `pptx_*`
  (`inspect`, `review`, `update_slide`, `delete_slide`,
  `reorder_slides`, `add_slide`). Permite a
  cualquier LLM compatible con MCP
  (Claude Code, Claude Desktop, Cursor, …) dirigir todo el flujo.
- **Dos rutas de enriquecimiento** para ir más allá del resumen hacia una
  auténtica presentación estilo tesis:
  - **LLM-as-agent (sin clave API)** — el LLM que llama lee el texto del cuerpo
    del PDF vía `fetch_pdf_text`, escribe un resumen estructurado en contexto y
    lo pasa a `export`.
  - **Pipeline Python (`--enrich`)** — la CLI llama a la API de Anthropic
    directamente; modelo por defecto `claude-opus-4-7`.
- **Flujos de editoriales con Chrome visible**: la SERP de Scholar, el
  `/rest/search` de IEEE y cada descarga de PDF de pago (ieeexplore / dl.acm /
  link.springer / sciencedirect / wiley / oup / nature / science / …) se
  ejecutan dentro de una sesión real y visible de Chrome vía `selenium`. El
  usuario resuelve el captcha / completa el SSO en la ventana en vivo una vez;
  `THESISAGENTS_CHROME_PROFILE_DIR` persiste las cookies entre ejecuciones.
- **Flujo LLM-as-agent**: las herramientas MCP proporcionan búsqueda, descarga
  de PDF y extracción de texto. `scripts/regen_*.py` contiene ejemplos
  reproducibles para redactar a mano un `PaperSummary` enriquecido por artículo.
- **Resolvedor de PDF OA**: tras la deduplicación, cada artículo sin `pdf_url`
  pasa por Unpaywall → S2 `openAccessPdf` → búsqueda por título en arXiv →
  CORE.ac.uk (cuando las claves están configuradas). Ganancia típica en
  consultas con mucho IEEE / ACM / Springer / Elsevier: 40 a 70 puntos
  porcentuales.
- **Seguridad por defecto**: transporte HTTP solo-HTTPS, límite de tasa por
  fuente (token bucket), `defusedxml` para cualquier payload XML, rutas de
  exportación seguras frente a path-traversal, sin `eval` / `exec` / `pickle`
  sobre la entrada del usuario.
- **Guarda de vocabulario zh-tw / zh-cn**: ~244 patrones regex en
  `tests/test_i18n.py::test_zh_tw_files_use_traditional_chinese_vocabulary`
  atrapan las palabras prestadas del chino simplificado renderizadas con hanzi
  tradicional (p. ej. `內存` → `記憶體`, `魯棒性` → `穩健性`, `軟件` → `軟體`,
  `緩存` → `快取`). La misma guarda se ejecuta a la inversa para las cadenas de
  la locale zh-cn. La regla completa + el catálogo regex viven en
  `.claude/agents/rules/language-vocabulary-check.md`.

## Inicio rápido

```powershell
git clone <repo-url>
cd ThesisAgents
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Install with dev extras (also pulls in MCP SDK and intelligence deps)
pip install -e .[dev]
```

Busque en arXiv y exporte presentación + libro + BibTeX (por defecto para
`--query`):

```powershell
py -m thesisagents --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

Recupere un solo artículo por URL — por defecto `.pptx + .bib` (el `.xlsx`
tiene menos sentido para una sola fila):

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

Renderice la presentación en 繁體中文:

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --lang zh-tw --out .\exports\
```

Enriquecimiento por pipeline LLM (Python llama a Anthropic directamente —
necesita clave API):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang zh-tw --out .\exports\
```

## Flags de la CLI

| Flag | Propósito |
|---|---|
| `--query` / `-q` | Palabras clave (obligatorio salvo con `--paper`). |
| `--paper` / `-p` | ID / URL arXiv, DOI, PMID o URL de documento IEEE. Mutuamente excluyente con `--query`. |
| `--source` / `-s` | Lista de fuentes separadas por coma. Default `arxiv`. |
| `--max` / `-n` | Resultados máximos por fuente (1..200). Default 25. |
| `--year-from` / `--year-to` | Filtro de año inclusivo. |
| `--export` / `-e` | Formatos: cualquiera de `pptx,xlsx,md,bib,json,ris,csv,csl`. El default depende del modo (ver abajo). |
| `--out` / `-o` | Directorio de salida. Default `./exports`. |
| `--filename-stem` | Sobrescribe el stem de nombre de archivo generado. |
| `--no-abstract` | Omite el contenido del resumen de las exportaciones. |
| `--lang` / `-l` | Idioma de la presentación: uno de 14 — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. Default `en`. |
| `--enrich` | Variante fail-loud del auto-enriquecimiento. Necesita `ANTHROPIC_API_KEY` y el extra `[intelligence]`. (El auto-enriquecimiento es el default cuando la clave está configurada.) |
| `--lightweight` | Salta el enriquecimiento + fuerza la presentación solo-resumen. Úselo solo para ejecuciones rápidas / desatendidas; **cuando un agente LLM dirige, prefiera el flujo LLM-as-agent** de abajo. |
| `--llm-model` | Sobrescribe el modelo por defecto `claude-opus-4-7` para el enriquecimiento. |
| `--no-pdf` | Salta la descarga automática del PDF. También desactiva el gate de PPT por artículo (sin PDF → sin contenido completo). |
| `--no-oa-resolve` | Salta el resolvedor de PDF OA post-deduplicación (Unpaywall + S2 + arXiv + CORE.ac.uk). |
| `--top-tier-only` | Restringe los resultados a arXiv + una lista blanca curada de referentes de informática (S&P, CCS, NDSS, USENIX Security, NeurIPS, ICML, ICSE, …). Desactivado por defecto. |
| `--paywall-threshold` | Fracción de resultados con paywall que dispara el prompt de confirmación. Default 0.30. |
| `--yes` | Salta el prompt de paywall y continúa. |
| `--max-slides` | Tope de diapositivas por artículo (default 25; pase 0 para ilimitado). |
| `--dark-mode` | Renderiza el pptx con un fondo oscuro + texto casi blanco. El default es la presentación clara con banda azul marino. |
| `--quiet` | Suprime la impresión por artículo. |

### Variables de entorno

| Variable | Usada por | Propósito |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | Auth del LLM. No necesaria para la ruta LLM-as-agent vía MCP. |
| `THESISAGENTS_LLM_MODEL` | `--enrich` | Sobrescribe el modelo por defecto `claude-opus-4-7`. |
| `THESISAGENTS_S2_API_KEY` | Semantic Scholar + resolvedor OA | Límite de tasa más alto; usada también por el paso S2 `openAccessPdf` del resolvedor OA. Clave gratuita en <https://www.semanticscholar.org/product/api>. |
| `THESISAGENTS_NCBI_API_KEY` | PubMed | Eleva el límite anónimo de NCBI (3/s) a 10/s. Opcional. |
| `THESISAGENTS_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex, **Unpaywall** | Etiqueta de polite-pool + habilita el paso Unpaywall del resolvedor OA (la mayor ganancia de cobertura de PDF para artículos con paywall de IEEE / ACM / Springer / Elsevier; ganancia típica de 40–70 pp). |
| `THESISAGENTS_IEEE_API_KEY` | IEEE (ruta API) | API oficial de IEEE Xplore; expone `pdf_url` para artículos dentro del alcance. |
| `THESISAGENTS_DISABLE_IEEE_SCRAPING` | IEEE | **IEEE está activo por defecto vía Chrome visible.** Configure `=1` para desactivarlo (p. ej. CI sin Chrome). La rama de scraping httpx solo se ejecuta como fallback cuando WebRunner no está disponible. |
| `THESISAGENTS_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Token de suscriptor de Crossref Plus (cabecera Bearer). Opcional. |
| `THESISAGENTS_SPRINGER_API_KEY` | Springer | Obligatoria; clave gratuita en <https://dev.springernature.com/>. El plugin lanza `ConfigError` sin ella. |
| `THESISAGENTS_DISABLE_SCHOLAR_SCRAPING` | Google Scholar | **Scholar está activo por defecto vía Chrome visible.** Configure `=1` para desactivarlo (los ToS de Google prohíben el acceso automatizado — activo por defecto por cobertura, opt-out para evitar el riesgo de captcha / bloqueo de IP). |
| `THESISAGENTS_CHROME_PROFILE_DIR` | Descargas de Scholar + IEEE + PDF con paywall | `--user-data-dir` de Chrome persistente. Configúrelo y complete VPN / SSO / inicio de sesión de Google una vez; las ejecuciones posteriores heredan las cookies para que IEEE devuelva metadatos con paywall y Scholar sirva SERPs sin throttling. |
| `THESISAGENTS_DISABLE_WEBRUNNER` | Descargas de Scholar + IEEE + PDF con paywall | `=1` fuerza las rutas httpx en lugar de dirigir Chrome real. Útil para CI / Docker sin un binario de Chrome; de lo contrario déjelo sin configurar. |
| `THESISAGENTS_CORE_API_KEY` | Resolvedor OA + fuente de búsqueda `core` | Clave gratuita en <https://core.ac.uk/services/api>. Habilita el paso de búsqueda OA de CORE.ac.uk (más de 200 M de ítems OA institucionales / regionales) **y** la fuente de búsqueda `core`. Sin ella, la fuente `core` se salta silenciosamente y las demás estrategias OA (Unpaywall, S2, arXiv) siguen ejecutándose. |
| `THESISAGENTS_PDF_COOKIES_FILE` | Descargador de PDF | `cookies.txt` en formato Netscape. Desactivado por defecto. Úselo solo con editoriales para las que tenga derechos institucionales. |
| `THESISAGENTS_LOG_LEVEL` | logger | `INFO` por defecto; `DEBUG` para trazas verbosas. |

Defaults: `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. Siempre
sobrescribibles con un `--export` explícito.

## Flujo LLM-as-agent

Cuando un LLM en su editor dirige el flujo de trabajo, use las herramientas MCP
en secuencia: `search`, `download_pdfs`, `fetch_pdf_text`, luego `export` con
un `PaperSummary` enriquecido redactado a mano. Los archivos existentes
`scripts/regen_*.py` son ejemplos reproducibles para el paso final de redacción
y exportación.

El runbook completo de extremo a extremo (búsqueda → presentación enriquecida)
vive en `.claude/agents/tasks/paper-summary-author.md` — ábralo antes de
comenzar una nueva consulta para que el LLM pueda ejecutar el flujo sin
detenerse a esperar entrada del usuario.

## Servidor MCP

Registrar con Claude Code:

```powershell
claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp
```

O escribir en su archivo de configuración:

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

Herramientas:

| Herramienta | Propósito |
|---|---|
| `list_sources` | Enumera cada plugin + reporta si cada uno está habilitado en el entorno actual. Llame esto una vez antes de `search`. |
| `list_exports` | Enumera cada formato de exportación con su descripción de una línea y si escribe un archivo agregado o un archivo por artículo. |
| `search` | Palabras clave → lista de artículos. Acepta `top_tier_only`, `min_citations`; por defecto la mezcla completa de fuentes sin clave API. |
| `fetch_paper` | Identificador arXiv / DOI / PMID / IEEE → un solo artículo. |
| `fetch_pdf_text` | Descarga un PDF, devuelve el texto del cuerpo extraído. **La ruta MCP hacia «leí el artículo».** |
| `download_pdfs` | Descarga por lotes los PDFs de una lista de artículos en `{out_dir}/pdfs/`. Devuelve resultados por artículo indexados por clave BibTeX. |
| `export` | Lista de artículos + formatos → escribe `.pptx/.xlsx/.md/.bib/.json/.ris/.csv/.csl.json`. Acepta un campo `summary` por artículo para el schema enriquecido estilo tesis, `max_slides_per_paper` (default 25) y `dark_mode` (default `false` — el default del proyecto es la presentación clara con banda azul marino, pase `true` para el post-pass oscuro OLED / de poca luz). |
| `pptx_inspect` | Lee la estructura de diapositivas / formas de una presentación existente. |
| `pptx_review` | Audita una presentación en una sola llamada — overflow + contratos de color + completitud de secciones `paper_rule`. Detecta automáticamente el idioma de la presentación; también la CLI `python -m thesisagents review <deck.pptx>`. |
| `pptx_update_slide` | Reemplaza `title` / `body` / `meta` (por nombre de forma) o formas arbitrarias por índice. |
| `pptx_delete_slide` | Elimina una diapositiva y su relación de parte. |
| `pptx_reorder_slides` | Permuta las diapositivas vía `sldIdLst`. |
| `pptx_add_slide` | Añade al final o inserta una nueva diapositiva título / cuerpo / meta. |

Flujo LLM-as-agent (sin necesidad de `ANTHROPIC_API_KEY` — el LLM es el
agente):

```
1. (optional) list_sources()                       # discover enabled plugins
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (optional) download_pdfs(papers, out_dir="./exports/...")  # persist PDFs
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # per paper
5. (the LLM reads body text, produces a structured `summary` dict)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="zh-tw", formats=["pptx","bib"], dark_mode=true, ...)
```

Referencia completa en [`docs/mcp.md`](docs/mcp.md).

## Estructura del proyecto

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

El flag `-c` de bandit es obligatorio — sin él, bandit ignora la configuración
de saltos del proyecto. Al tocar el exportador pptx, ejecute también una
comprobación de desbordamiento (ver `CLAUDE.md` «Slide Deck Rules»).

## GUI de escritorio (PySide6)

Una interfaz de escritorio nativa se distribuye tras el extra `[gui]`:

```powershell
pip install thesisagents[gui]
thesisagents-gui                 # or: thesisagents gui
```

La ventana tiene cuatro pestañas — **Search**, **Settings** (persiste las
claves API vía QSettings), **Enrich** (dirige el enriquecimiento LLM-as-agent /
pipeline Python sobre una señal `collection_ready`) y **Deck** (el toggle de
modo claro + los controles de tope de diapositivas + máximo de figuras fluyen a
`ExportOptions`). El zip de release de Windows trae el paquete compilado con
Nuitka con PySide6 incluido, de modo que `thesisagents.exe gui` funciona sin
una instalación de Python separada.
**La UI se distribuye en los 14 idiomas** (English, 繁體中文, 简体中文,
日本語, Español, Français, Deutsch, 한국어, Português, Русский,
Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia) — la primera ejecución elige el
idioma desde la locale de su SO, luego **Settings → Interface language** le
permite cambiarlo. El idioma de salida de la presentación es un desplegable
separado, así que puede ejecutar la UI en un idioma y emitir diapositivas en
otro. La disposición es responsive: cada formulario está en un `QScrollArea` y
la ventana se redimensiona hasta 900×600 (aún cabe en 720p), con escalado HiDPI
activado por defecto.

Referencia completa: [`docs/gui.md`](docs/gui.md).

## Empaquetado como ejecutable independiente

Dos empaquetadores están documentados para distribuir un binario de archivo
único que se ejecuta sin Python instalado:

- **[`docs/packaging-pyinstaller.md`](docs/packaging-pyinstaller.md)**
  — build rápido (menos de un minuto), salida de 200–300 MB, arranque de
  2–4 s. Ideal cuando itera sobre el script de build.
- **[`docs/packaging-nuitka.md`](docs/packaging-nuitka.md)** —
  build lento (5–15 minutos), salida de 80–150 MB, arranque en menos de un
  segundo, cierta protección del bytecode. Ideal cuando los usuarios finales
  ejecutan el binario muchas veces.

Ambos documentos cubren la trampa específica del proyecto — los plugins de
fuente dinámicos en `sources/<name>/` — y traen un comando verificado para los
puntos de entrada de la CLI y del servidor MCP.

## Integración continua & releases

Dos workflows de GitHub Actions viven en `.github/workflows/`:

- **`ci.yml`** se ejecuta en cada push y PR hacia `main`. La matriz es Ubuntu +
  Windows × Python 3.12 / 3.13 / 3.14 (6 jobs). Cada job ejecuta
  `ruff check`, `bandit -c pyproject.toml` y `pytest`.
- **`release.yml`** espera a que `ci.yml` se complete en `main`
  (disparador `workflow_run`). Solo se ejecuta si el CI tuvo éxito. **Cada push
  con CI exitoso hacia `main` es un release** — el workflow incrementa
  automáticamente la versión de parche en `pyproject.toml`, comitea el
  incremento de vuelta a `main` como `chore: bump version to X.Y.Z`, y
  encadena:
  1. **`bump-version`** — lee la `X.Y.Z` actual de `pyproject.toml`,
     incrementa a `X.Y.(Z+1)`, comitea + hace push de vuelta a `main` usando el
     `GITHUB_TOKEN` del workflow. Ese push NO re-dispara el CI (según la regla
     de GitHub de que los pushes dirigidos por `GITHUB_TOKEN` no pueden iniciar
     nuevas ejecuciones de workflow), de modo que el ciclo termina
     naturalmente.
  2. **`publish-pypi`** — construye sdist + wheel, `twine check`,
     `twine upload` vía `PYPI_API_TOKEN`.
  3. **`create-draft-release`** — abre un release de GitHub en *borrador* en el
     tag `v<version>` con notas generadas automáticamente.
  4. **`build-nuitka`** — compila un paquete standalone de Nuitka en un runner
     de Windows (punto de entrada: `python -m thesisagents` vía
     `--python-flag=-m`), lo somete a smoke-test, comprime la carpeta
     `thesisagents.dist/` resultante, y adjunta el zip + un checksum `.sha256`
     al release en borrador. Standalone (no onefile) por diseño: onefile se
     autoextrae a `%TEMP%` en cada arranque, añadiendo latencia de arranque y
     disparando las heurísticas de antivirus en máquinas bloqueadas.
     Solo-Windows por diseño también: los usuarios de Linux / macOS instalan
     desde PyPI. La caché de build indexada por `pyproject.toml` recorta los
     builds en caliente de ~70 min en frío a ~5–10 min.
  5. **`publish-release`** — quita la marca de borrador una vez que el asset de
     Nuitka está subido, de modo que los usuarios nunca vean un release a
     medio terminar.

  **Saltar un release.** Incluya `[skip release]` en cualquier parte del mensaje
  de commit y el incremento + cada job downstream se saltan — use esto para
  commits solo de docs / typo / refactor que no deban quemar un número de
  versión.

Para habilitar la publicación en PyPI + los ejecutables de release:

1. Genere un token API con alcance de proyecto en
   <https://pypi.org/manage/account/token/>.
2. En el repositorio de GitHub: `Settings → Secrets and variables → Actions →
   New repository secret`. Nómbrelo `PYPI_API_TOKEN` y pegue el valor del
   token.
3. Permita que GitHub Actions haga push a `main`: `Settings → Actions →
   General → Workflow permissions → Read and write permissions`. El commit de
   incremento es enviado por el `GITHUB_TOKEN` del workflow.
4. Corte releases fusionando PRs en `main`. El pipeline tarda ~3–5 min en
   publicar en PyPI y ~50–70 min más (en frío) o ~5–10 min (caché de Nuitka en
   caliente) para que el zip de Windows se adjunte.

El job `publish-pypi` intencionalmente NO adjunta un Environment de GitHub, de
modo que cada ejecución aparece como una entrada de Release (con su `.exe` de
Nuitka adjunto) en lugar de como un widget de «Deployment» en la barra lateral
de la página de inicio del repo — los releases obtienen su propia página
dedicada y una entrada de Deployment encima sería solo ruido redundante.

## Licencia

Ver `LICENSE`. La API de arXiv se usa bajo los términos de uso de la API de
arXiv (<https://info.arxiv.org/help/api/tou.html>) — respete el límite suave de
1 petición cada 3 segundos; el fetcher incluido ya lo impone vía su token
bucket.
