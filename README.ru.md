# AutoPaperToPPT

[![CI](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![Python](https://img.shields.io/pypi/pyversions/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/AutoPaperToPPT.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/autopapertoppt/badge/?version=latest)](https://autopapertoppt.readthedocs.io/en/latest/)

> **Языки**: [English](README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · **Русский** · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **Документация**: [autopapertoppt.readthedocs.io](https://autopapertoppt.readthedocs.io/en/latest/)

Поисковый ассистент статей, управляемый ключевыми словами. Получает результаты из arXiv, Semantic Scholar, OpenAlex, PubMed, ACM (через Crossref), IEEE Xplore, DBLP, общего Crossref, OpenAIRE, Springer Nature и Google Scholar; нормализует в единый формат записи; и экспортирует дедуплицированный набор как **слайды PowerPoint в стиле дипломной презентации**, **книгу Excel** и **файл BibTeX** — всё за один CLI-вызов или один вызов MCP-инструмента. Опционально обогащает каждую статью, читая её PDF и порождая структурированную сводку — либо в контексте (поток LLM-as-agent), либо через API Anthropic (Python pipeline).

## Для ИИ-агентов, управляющих этим проектом

**Если вы LLM (Claude Code, Cursor, Aider, Codex CLI, …), читающий этот README, чтобы понять, что делать — начните здесь.** Те же правила закреплены в [`AGENTS.md`](AGENTS.md) (зеркало для всех агентов) и [`CLAUDE.md`](CLAUDE.md) (канонический справочник); прочитайте их перед нетривиальными изменениями.

### Что на самом деле нужно пользователю

Целевой результат по умолчанию — **обогащённый `.pptx` в стиле дипломной презентации на каждую статью**, а не легковесный дек только с аннотацией, который CLI выдаёт по умолчанию. Легковесная выдача — промежуточный артефакт; ваша задача — повысить её уровень.

### Дерево решений

1. Установлена ли `ANTHROPIC_API_KEY` в окружении? → просто запустите CLI; она автоматически обогащает через API Anthropic. Готово.
2. Ключа нет, но вы (LLM) ведёте сессию → **обогащённую сводку пишете вы сами**. Прочитайте каждый PDF, вручную составьте `PaperSummary` с полями rich-tier (`pain_points`, `research_question`, `contributions_detailed`, `headline_metrics`, `technique_table`, `method_sections`, `evaluation_sections`, `system_flow`, `research_questions`, `rq_results`, `core_observation`, `limitations`, `future_work`), положите `scripts/regen_<query>.py` и запустите. **Не говорите пользователю «установите API-ключ»** — вы и есть тот LLM, который должен был написать сводку.
3. LLM нет (CI / cron / без присмотра) → легковесная выдача допустима.

### MCP-процесс в 6 шагов

```
1. (опц.) list_sources()                                  # какие плагины активны
2. search(keywords, sources, top_tier_only=true, ...)
3. (опц.) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # по каждой статье
5. (вы читаете каждый PDF и составляете структурированный dict сводки)
6. export(papers=[{...paper, "summary": {...}}], language="ru", ...)
```

Все одиннадцать MCP-инструментов (включая `list_sources`, `download_pdfs`, `pptx_inspect` / `pptx_update_slide` / `pptx_add_slide` / т. д.) задокументированы в [`docs/mcp.md`](docs/mcp.md).

### Обязательно: проверка URL / DOI перед сдачей

URL-пути издателей **нельзя угадать** — AAAI использует числовые ID (`v40i5.37389`), IEEE использует непрозрачный `arnumber`, ACM — непрозрачные DOI. При ручной сборке `Paper` **копируйте `url` / `doi` / `arxiv_id` дословно из xlsx, который сгенерировал этот поиск** — никогда по памяти, никогда из заголовка.

xlsx пишется в `exports/<run>/<slug>-<timestamp>.xlsx`, столбец 7 = DOI, столбец 8 = URL. Прогоните аудит после regen-скрипта:

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

Два случая подделки, пойманные так в продакшене: неверный том AAAI (`v39i23.34521` vs реальный `v39i22.34537`) и выдуманный путь с автор-слагом (`view/fang2026` вместо `v40i5.37389`).

### Образец

В [`scripts/regen_llm_security_batch.py`](scripts/regen_llm_security_batch.py) лежат 8 написанных вручную обогащённых сводок ровно по этому процессу. Используйте как шаблон для любого многостатейного поиска. Парный zh-tw — в [`scripts/regen_llm_security_batch_zh_tw.py`](scripts/regen_llm_security_batch_zh_tw.py).

### Запреты

- **Не** заканчивайте многостатейный поиск словами «установите `ANTHROPIC_API_KEY` для обогащённого дека» — вы и есть LLM, который мог бы написать сводки.
- **Не** считайте легковесный `.pptx` итогом.
- **Не** останавливайтесь после сообщения `download_pdfs` «N PDF сохранено» — это начало фазы написания, а не конец.
- **Не** выдумывайте числа, RQ, вклады или ограничения, отсутствующие в статье.
- **Не** фабрикуйте URL / DOI / arXiv ID — см. правило выше.
- **Не** оставляйте нерелевантные загрузки в рабочем каталоге. Поиск по ключевым словам иногда подтягивает статьи не по теме (запрос «Claude code» вернул статью про декодер Витерби; «LLM code review» — обзор по детекции объектов). После классификации как нерелевантной удалите её `pdfs/<key>.pdf` и легковесный `<key>.pptx`; сохраняйте сводный xlsx / bib как честную запись того, что вернул поиск.
- **Не** упоминайте «Claude», «Claude Code», «AI-generated», «GPT», «Copilot» и любые имена ИИ-инструментов/моделей в commit-сообщениях, описаниях PR, комментариях кода или документации.

## Возможности

- **Одиннадцать подключаемых источников**: `arxiv`, `semantic_scholar`, `openalex`, `pubmed`, `acm` (ограничен ACM через Crossref), `dblp`, `crossref` (общий), `openaire`, `springer` (нужен API-ключ), `ieee` (API-ключ или scraping-opt-in), `scholar` (scraping-opt-in). Каждый лежит под `sources/<name>/` за адаптером `Fetcher`. Whitelist топовых площадок фильтрует результаты до флагманских CS-конференций/журналов + Nature/Science/PNAS по умолчанию; `--all-venues` отключает.
- **Режим одной статьи**: вставьте arXiv ID, arXiv URL, DOI, PMID или URL документа IEEE — AutoPaperToPPT разрешит через нужный источник и выдаст тот же экспорт-пакет. Полезно для заметок чтения и подготовки защиты.
- **Локальный PDF-режим** (`--pdf <путь>`): передайте один PDF или каталог. Эвристический экстрактор вытаскивает **заголовок, авторов, год, arXiv ID, DOI и настоящую аннотацию** прямо из начала каждого PDF (привязка к явному заголовку `Abstract` / `ABSTRACT` / `摘要`, а не слепому префиксу). `--title` / `--authors` / `--year` / `--venue` / `--doi` / `--arxiv-id` переопределяют при одиночном PDF; в режиме каталога побеждает per-file извлечение — каждая статья получает свой дек, названный по её BibTeX-ключу.
- **Пять экспортёров**:
  - `.pptx` — 16:9 широкоэкранный, с нумерацией, три уровня рендеринга (легкий только-аннотация · enriched-flat · **стиль дипломной**: квадранты болевых точек, KPI-выноски, сравнительные таблицы техник, таблицы результатов по RQ, сводка вкладов, ключевое наблюдение, ограничения и будущая работа, Q&A, литература). Все шаблонные строки i18n на **14 языках**: English, 繁體中文, 简体中文, 日本語, Español, Français, Deutsch, 한국어, Português, Русский, Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia.
  - `.xlsx` — лист Papers + лист происхождения Query, URL / PDF гиперссылками, закреплённая шапка, авторазмеры столбцов. Столбец 5 (**Source**) показывает реальное место публикации (напр. «IEEE Access»); столбец 6 (**Indexed via**) — какой fetcher вернул метаданные (напр. «openalex»), чтобы эти две сущности не путались.
  - `.md` — полный список источник / заголовок / аннотация.
  - `.bib` — ключи цитирования без коллизий, поля с LaTeX-эскейпами.
  - `.json` — сырой payload для downstream-инструментов.
- **Инструменты редактирования PPT**: `autopapertoppt.exporters.pptx_edit` (inspect / update_slide / delete_slide / reorder_slides / add_slide) работает с любым деком, созданным экспортёром, плюс эквивалентные MCP-инструменты `pptx_*` для итераций над сгенерированным деком LLM-агентом.
- **MCP-сервер**: 11 инструментов — `list_sources` (discovery), `search`, `fetch_paper`, `fetch_pdf_text`, `download_pdfs`, `export`, и пять `pptx_*`-инструментов. Любой MCP-совместимый LLM (Claude Code, Claude Desktop, Cursor, …) может управлять всем процессом.
- **Два пути обогащения** для выхода за пределы аннотации к настоящему деку в стиле дипломной:
  - **LLM-as-agent (без API-ключа)** — вызывающий LLM читает текст PDF через `fetch_pdf_text`, пишет структурированную сводку в контексте и передаёт её в `export`.
  - **Python pipeline (`--enrich`)** — CLI сама вызывает API Anthropic; модель по умолчанию `claude-opus-4-7`.
- **Безопасность по умолчанию**: HTTP-транспорт только-HTTPS, rate limit на каждый источник (token bucket), `defusedxml` для любого XML-payload, безопасные от path-traversal экспорт-пути, без `eval` / `exec` / `pickle` на пользовательском вводе. Scraping Scholar и IEEE по умолчанию выключен (opt-in через env-var).

## Быстрый старт

```powershell
git clone <repo-url>
cd AutoPaperToPPT
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Установка с dev extras (также подтягивает MCP SDK и intelligence deps)
pip install -e .[dev]
```

Поиск по arXiv с экспортом дека + книги + BibTeX (default для `--query`):

```powershell
py -m autopapertoppt --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

Загрузить одну статью по URL — default `.pptx + .bib` (`.xlsx` для одной строки малоосмыслен):

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

Сгенерировать дек на русском:

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --lang ru --out .\exports\
```

Обогащение через LLM-pipeline (Python вызывает Anthropic — нужен API-ключ):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang ru --out .\exports\
```

## Флаги CLI

| Флаг | Назначение |
|---|---|
| `--query` / `-q` | Ключевые слова (обязателен, если нет `--paper`). |
| `--paper` / `-p` | arXiv ID/URL, DOI, PMID или URL документа IEEE. Взаимоисключающий с `--query`. |
| `--source` / `-s` | Список источников через запятую. Default `arxiv`. |
| `--max` / `-n` | Макс. результатов на источник (1..200). Default 25. |
| `--year-from` / `--year-to` | Включающий фильтр по году. |
| `--export` / `-e` | Форматы: любое подмножество `pptx,xlsx,md,bib,json`. Default зависит от режима (см. ниже). |
| `--out` / `-o` | Каталог выхода. Default `./exports`. |
| `--filename-stem` | Переопределяет сгенерированный stem имени файла. |
| `--no-abstract` | Не включать содержимое аннотации в экспорт. |
| `--lang` / `-l` | Язык дека: один из 14 — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. Default `en`. |
| `--enrich` | Скачать PDF + сводка Anthropic. Нужны `ANTHROPIC_API_KEY` и extra `[intelligence]`. |
| `--lightweight` | Принудительно лёгкий дек, даже если `ANTHROPIC_API_KEY` задана. |
| `--llm-model` | Переопределить модель по умолчанию `claude-opus-4-7`. |
| `--all-venues` | Отключить топовую whitelist (default сохраняет флагманские CS-площадки + Nature / Science / PNAS / CACM / LNCS). |
| `--paywall-threshold` | Доля paywall-результатов, при которой появляется prompt подтверждения. Default 0.30. |
| `--yes` | Пропустить paywall-prompt. |
| `--max-slides` | Лимит слайдов на статью (default 25; 0 — без лимита). |
| `--quiet` | Подавить вывод по каждой статье. |

### Переменные окружения

| Переменная | Используется | Назначение |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | Auth для LLM. Не нужна для пути LLM-as-agent через MCP. |
| `AUTOPAPERTOPPT_LLM_MODEL` | `--enrich` | Переопределяет модель по умолчанию `claude-opus-4-7`. |
| `AUTOPAPERTOPPT_S2_API_KEY` | Semantic Scholar | Более высокий rate-limit. Опционально. |
| `AUTOPAPERTOPPT_NCBI_API_KEY` | PubMed | Поднимает анонимный лимит NCBI (3/с) до 10/с. Опционально. |
| `AUTOPAPERTOPPT_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex | Помещает запросы в polite pool Crossref. |
| `AUTOPAPERTOPPT_IEEE_API_KEY` | IEEE (API-путь) | Официальное API IEEE Xplore; выдаёт `pdf_url` для статей в области подписки. |
| `AUTOPAPERTOPPT_ENABLE_IEEE_SCRAPING` | IEEE (scraping-путь) | `=1` включает scraping. Не нужна, когда задан API-ключ. |
| `AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Токен подписчика Crossref Plus (Bearer-заголовок). Опционально. |
| `AUTOPAPERTOPPT_SPRINGER_API_KEY` | Springer | Обязательна; бесплатный ключ на <https://dev.springernature.com/>. Без неё плагин тихо пропускается. |
| `AUTOPAPERTOPPT_ENABLE_SCHOLAR_SCRAPING` | Google Scholar | `=1` включает scraping. По умолчанию выключен — ToS Scholar запрещают scraping. |
| `AUTOPAPERTOPPT_PDF_COOKIES_FILE` | PDF-загрузчик | `cookies.txt` в формате Netscape. По умолчанию выключен. Используйте только с теми издателями, к которым имеете институциональные права. |
| `AUTOPAPERTOPPT_LOG_LEVEL` | logger | `INFO` по умолчанию; `DEBUG` для подробных трасс. |

Defaults: `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. Всегда переопределяется явным `--export`.

## MCP-сервер

Регистрация в Claude Code:

```powershell
claude mcp add autopapertoppt -- ".venv\Scripts\python.exe" -m autopapertoppt.mcp
```

Или вручную в settings-файле:

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

Инструменты:

| Инструмент | Назначение |
|---|---|
| `list_sources` | Перечисляет каждый плагин + сообщает, какие активны в текущем окружении. Вызывайте один раз до `search`. |
| `search` | Ключевые слова → список статей. Принимает `top_tier_only`, `min_citations`; по умолчанию — полный набор источников без API-ключа. |
| `fetch_paper` | Идентификатор arXiv / DOI / PMID / IEEE → одна статья. |
| `fetch_pdf_text` | Скачать один PDF, вернуть извлечённый текст. **Точка входа MCP для «я прочитал статью».** |
| `download_pdfs` | Пакетная загрузка PDF из списка статей в `{out_dir}/pdfs/`. Возвращает результаты по каждой статье, индексированные BibTeX-ключом. |
| `export` | Список статей + форматы → пишет `.pptx/.xlsx/.md/.bib/.json`. Принимает поле `summary` (rich thesis-style schema) и `max_slides_per_paper` (default 25). |
| `pptx_inspect` | Читает структуру слайдов/шейпов существующего дека. |
| `pptx_update_slide` | Заменяет `title` / `body` / `meta` (по имени шейпа) или произвольные шейпы по индексу. |
| `pptx_delete_slide` | Удаляет слайд и его part relationship. |
| `pptx_reorder_slides` | Переставляет слайды через `sldIdLst`. |
| `pptx_add_slide` | Добавляет в конец или вставляет в заданную позицию новый title / body / meta слайд. |

Поток LLM-as-agent (без `ANTHROPIC_API_KEY` — LLM сам и есть агент):

```
1. (опц.) list_sources()                           # обнаружить активные плагины
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (опц.) download_pdfs(papers, out_dir="./exports/...")  # сохранить PDF
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # по каждой статье
5. (LLM читает текст, выдаёт структурированный `summary` dict)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="ru", formats=["pptx","bib"], ...)
```

Полный справочник: [`docs/mcp.md`](docs/mcp.md).

## Структура проекта

```
AutoPaperToPPT/
├── autopapertoppt/                 # основной пакет
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # async-клиент только-HTTPS, rate limit token bucket
│   ├── exporters/                   # pptx (стиль дипломной) · xlsx · bib · md · json · pptx_edit · i18n
│   ├── intelligence/                # загрузка PDF + сумматор Anthropic ([intelligence] extra)
│   ├── mcp/                         # сервер FastMCP (11 инструментов)
│   ├── utils/                       # logging, path safety
│   ├── cli.py                       # CLI argparse
│   └── __main__.py
├── sources/                         # папки плагинов: arxiv, semantic_scholar,
│                                    #   openalex, pubmed, acm, ieee, scholar,
│                                    #   dblp, crossref, openaire, springer
├── tests/                           # pytest-сьют + записанные fixture (без живого HTTP)
├── docs/                            # Sphinx (14 языковых деревьев)
├── scripts/                         # одноразовые regen-скрипты
└── pyproject.toml                   # ruff, bandit, build, опциональные extras
```

## Definition of Done

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r autopapertoppt/ sources/
```

Флаг `-c` у bandit обязателен — без него bandit игнорирует skip-конфигурацию проекта. Когда трогаете pptx-экспортёр, запускайте также проверку overflow (см. `CLAUDE.md` «Slide Deck Rules»).

## Лицензия

См. `LICENSE`. API arXiv используется по его условиям (<https://info.arxiv.org/help/api/tou.html>) — соблюдайте мягкий лимит 1 запрос в 3 секунды; встроенный fetcher уже навязывает эту ставку через token bucket.
