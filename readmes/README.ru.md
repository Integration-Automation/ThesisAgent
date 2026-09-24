# ThesisAgents

[![CI](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![Python](https://img.shields.io/pypi/pyversions/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/ThesisAgents.svg)](https://github.com/Integration-Automation/ThesisAgents/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/thesisagents/badge/?version=latest)](https://thesisagents.readthedocs.io/en/latest/)

> **Языки**: [English](../README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · **Русский** · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **Документация**: [thesisagents.readthedocs.io](https://thesisagents.readthedocs.io/en/latest/)

Поисковый ассистент статей, управляемый ключевыми словами. Получает результаты из arXiv,
Semantic Scholar, OpenAlex, PubMed, ACM (через Crossref), IEEE Xplore,
DBLP, общего Crossref, OpenAIRE, Springer Nature, Europe PMC, DOAJ,
HAL, CORE и Google Scholar,
нормализует их в единый формат записи и экспортирует дедуплицированный набор
как **слайды PowerPoint в стиле дипломной презентации**, **книгу Excel** и
**файл BibTeX** — всё за один вызов CLI или один вызов MCP-инструмента. Опционально
обогащает каждую статью, читая её PDF и порождая структурированную
посписьменную сводку либо в контексте (поток LLM-as-agent), либо через
API Anthropic (поток Python pipeline).

## Для ИИ-агентов, управляющих этим проектом

**Если вы — LLM (Claude Code, Cursor, Aider, Codex CLI, …), читающий
этот README, чтобы понять, что делать, — начните здесь.** Всё, что ниже,
также закреплено в [`AGENTS.md`](AGENTS.md) (кросс-агентное зеркало) и
[`CLAUDE.md`](CLAUDE.md) (канонический справочник); прочтите их перед
внесением нетривиальных изменений.

### Что на самом деле нужно пользователю

Итоговый результат по умолчанию — **насыщенный `.pptx` в стиле дипломной
презентации на каждую статью**, а не облегчённый дек только с аннотацией,
который CLI выдаёт по умолчанию. Облегчённый вывод — промежуточный
артефакт; ваша задача — довести его до полного вида.

### Дерево решений

1. Задана ли `ANTHROPIC_API_KEY` в окружении? → просто запустите CLI;
   он автоматически обогатит через API Anthropic. На этом всё.
2. Ключа нет, но сессией управляете вы (LLM) → **вы сами создаёте
   насыщенную сводку**. Прочитайте каждый PDF, вручную составьте
   `PaperSummary` с полями насыщенного уровня (`pain_points`,
   `research_question`, `contributions_detailed`, `headline_metrics`,
   `technique_table`, `method_sections`, `evaluation_sections`,
   `system_flow`, `research_questions`, `rq_results`,
   `core_observation`, `limitations`, `future_work`), положите
   `scripts/regen_<query>.py` и запустите его. **Не советуйте пользователю
   задавать ключ API** — вы и есть тот LLM, который написал бы
   сводку.
3. В цепочке нет LLM (CI / cron / без присмотра) → облегчённый вывод
   допустим.

### Рабочий процесс MCP из 6 шагов

```
1. (optional) list_sources()                              # see which plugins are enabled
2. search(keywords, sources, top_tier_only=true, ...)
3. (optional) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # per paper
5. (you read each PDF and produce a structured summary dict)
6. export(papers=[{...paper, "summary": {...}}], language="zh-tw", ...)
```

Все тринадцать MCP-инструментов (включая `list_sources`, `list_exports`,
`download_pdfs`, `pptx_inspect` / `pptx_review` / `pptx_update_slide` /
`pptx_add_slide` / и т. д.)
задокументированы в [`docs/mcp.md`](docs/mcp.md).

### Обязательно: проверка URL / DOI перед выпуском

Пути URL издателей **невозможно угадать** — AAAI использует числовые ID
(`v40i5.37389`), IEEE — непрозрачный `arnumber`, ACM — непрозрачные DOI.
Когда вы вручную составляете `Paper`, **копируйте `url` / `doi` / `arxiv_id`
дословно из поискового xlsx, породившего этот запуск** — никогда по
памяти, никогда не конструируйте из заголовка.

Файл xlsx записывается в `exports/<run>/<slug>-<timestamp>.xlsx`, где
столбец 7 = DOI, столбец 8 = URL. Проверьте свой скрипт regen по
завершении:

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

Две подделки, пойманные так в продакшене: неверный том AAAI
(`v39i23.34521` вместо реального `v39i22.34537`) и выдуманный путь по
слагу автора (`view/fang2026` вместо `v40i5.37389`).

### Обязательно: отсеять нерелевантные загрузки перед выпуском

Сопоставление по ключевым словам основано на ключевых словах, поэтому
не по теме статьи будут просачиваться: запрос «Claude code» вернул
статью о декодере Витерби, потому что в обеих есть «code»; «LLM code
review» совпал с обзором литературы по детекции объектов. Как только
вы прочитаете аннотации и отнесёте статью к не относящимся к реальному
намерению пользователя, вычистите каталог запуска:

```python
from pathlib import Path
run = Path("exports/<run>")
irrelevant_keys = ("key-of-off-topic-paper-1", "key-of-off-topic-paper-2")
for key in irrelevant_keys:
    for path in (run / "pdfs" / f"{key}.pdf", run / f"{key}.pptx"):
        if path.exists():
            path.unlink()
```

Удалите `exports/<run>/pdfs/<key>.pdf` + `exports/<run>/<key>.pptx`.
**Сохраните** сводный `<slug>-<timestamp>.xlsx` / `.bib` — это
честная запись того, что вернул поиск. Пограничным случаям — насыщенную
сводку; лучше включить лишнее, чем молча отбросить возможное
совпадение.

### Разобранный пример

[`scripts/regen_fang2026.py`](scripts/regen_fang2026.py) поставляется с
вручную составленной насыщенной сводкой, построенной именно так (одна
статья, насыщенный уровень, zh-tw, каждое насыщенное поле заполнено).
Поиск по нескольким статьям следует той же форме с одной записью
`Paper(...summary=PaperSummary(...))` на статью в кортеже
`PaperCollection`.

### Чего не делать

- **Не** завершайте поиск по нескольким статьям советом пользователю
  «задать `ANTHROPIC_API_KEY` для насыщенного дека» — вы и есть тот
  LLM, который мог бы написать сводки.
- **Не** считайте облегчённый `.pptx` на каждую статью итоговым
  результатом.
- **Не** останавливайтесь после того, как `download_pdfs` сообщит о
  сохранённых N PDF — это начало фазы насыщенного составления, а не
  конец.
- **Не** выдумывайте числа, RQ, вклады или ограничения, которых нет в
  статье.
- **Не** фабрикуйте URL / DOI / arXiv ID — см. правило выше.
- **Не** оставляйте нерелевантные загрузки в каталоге запуска.
  Совпадения по ключевым словам могут включать не по теме статьи
  (запрос «Claude code» притянул статью о декодере Витерби; «LLM code
  review» притянул обзор литературы по детекции объектов). После
  классификации статей как не по теме удалите их `pdfs/<key>.pdf` и
  облегчённый `<key>.pptx`; сохраните сводный xlsx / bib как честную
  запись того, что вернул поиск.
- **Не** упоминайте «Claude», «Claude Code», «AI-generated», «GPT»,
  «Copilot» или любое название ИИ-инструмента/модели в сообщениях
  коммитов, описаниях PR, комментариях к коду или документации.

## Возможности

- **Пятнадцать подключаемых источников**: `arxiv`, `semantic_scholar`, `openalex`,
  `pubmed`, `acm` (в рамках Crossref), `dblp`, `crossref` (без ограничения),
  `openaire`, `springer` (нужен ключ API), `europepmc` (открытый, без ключа —
  науки о жизни + препринты + сельское хозяйство), `doaj` (открытый, без ключа —
  журналы открытого доступа, обычно с прямой ссылкой на PDF), `hal` (открытый,
  без ключа — французский архив по CS / математике / физике с полнотекстовыми PDF),
  `core` (нужен бесплатный ключ API — крупнейший агрегатор открытого доступа, 250M+
  работ), `ieee` (включён по умолчанию через видимый Chrome; ключ API добавляет официальный
  Xplore API), `scholar` (включён по умолчанию через видимый Chrome). Каждый живёт в
  `sources/<name>/` за адаптером `Fetcher`.
  Передайте `--top-tier-only`, чтобы отфильтровать результаты до флагманских CS-
  конференций/журналов плюс Nature/Science/PNAS. Поиск по умолчанию
  сохраняет все площадки.
- **Режим одной статьи**: вставьте arXiv ID, URL arXiv, DOI, PMID или URL
  документа IEEE — ThesisAgents разрешит его через нужный источник и
  выдаст тот же комплект экспорта. Полезно для заметок по чтению статей и
  подготовки к защите диплома.
- **Режим локального PDF** (`--pdf <path>`): передайте один PDF или каталог.
  Эвристический экстрактор вытягивает **заголовок, авторов, год, arXiv ID, DOI и
  настоящую аннотацию** прямо из титульной части каждого PDF (привязка к
  явному заголовку `Abstract` / `ABSTRACT` / `摘要`, а не по слепому
  префиксу). `--title` / `--authors` / `--year` / `--venue` / `--doi` /
  `--arxiv-id` переопределяют при вызове с одним PDF; на каталоге
  извлечение по каждому файлу побеждает, так что каждая статья получает свой
  дек, названный по своему ключу BibTeX.
- **Восемь экспортёров**:
  - `.pptx` — 16:9 широкоэкранный, с нумерацией страниц, три уровня отрисовки
    (облегчённый только с аннотацией · обогащённый-плоский · **в стиле дипломной
    презентации** с квадрантами болевых точек, KPI-выносками, таблицами сравнения
    техник, таблицами результатов по каждому RQ, сводкой вкладов, ключевым
    наблюдением, ограничениями и будущей работой, Q&A, ссылками). Все строки
    шаблонов интернационализированы на **14 языках**: English, 繁體中文, 简体中文,
    日本語, Español, Français, Deutsch, 한국어, Português, Русский,
    Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia.
  - **Визуальная идентичность оформленного дека** (не стандартный вид Calibri-на-
    белом): типографика по языку (Inter для латиницы, Microsoft JhengHei
    UI / YaHei UI / Yu Gothic UI / Malgun Gothic / Nirmala UI для CJK
    + хинди), программная акцентная геометрия (верхняя акцентная полоса на каждом
    контентном слайде + левая полоса на обложке), таблицы в академическом стиле
    (стандартная сетка убрана, тёмно-синяя линия заголовка, мягкие межстрочные
    разделители, чередующаяся полоса строк, выравнивание по средней вертикали, жирные
    метки строк) и дисциплина палитры из пяти цветов (тёмно-синий / бирюзовый / серый /
    светлый / белый), где красный **запрещён** для текста (для акцента используйте
    жирный + бирюзовый `#0E7490`).
  - **Светлый режим — путь отрисовки по умолчанию.** Передайте `--dark-mode`, включите
    **Dark mode** во вкладке Deck графического интерфейса или задайте
    `ExportOptions(dark_mode=True)`, чтобы применить тёмный пост-проход (фон
    слайда `#12151B`, основной текст `#E5E7EB`).
  - `.xlsx` — лист Papers + лист происхождения Query, гиперссылки URL /
    PDF, закреплённый заголовок, авто-ширина столбцов. Столбец 5 (**Source**) показывает
    настоящую площадку публикации (например «IEEE Access»); столбец 6
    (**Indexed via**) показывает, какой фетчер вернул метаданные
    (например «openalex»), так что две части информации никогда не смешиваются.
  - `.md` — полный список источник / заголовок / аннотация.
  - `.bib` — бесконфликтные ключи цитирования, поля с экранированием LaTeX.
  - `.json` — сырой payload для нижестоящих инструментов.
  - `.ris` — обмен RIS, импортируемый Zotero / Mendeley / EndNote /
    RefWorks (аналог BibTeX для не-LaTeX менеджеров ссылок).
  - `.csv` — плоская таблица одна-строка-на-статью для таблиц / быстрого grep-
    отбора (кавычки по RFC-4180, так что запятые в заголовках никогда не сдвигают столбцы).
  - `.csl.json` — CSL-JSON для Pandoc / citeproc; отрисуйте библиографию
    в любом стиле CSL (APA, IEEE, Nature, …). Расширение `.csl.json`
    отличает его от простого дампа `.json`.
- **Набор инструментов редактирования PPT**: `thesisagents.exporters.pptx_edit`
  (inspect / update_slide / delete_slide / reorder_slides / add_slide)
  работает с любым деком, произведённым экспортёром, плюс эквивалентные
  MCP-инструменты `pptx_*`, чтобы LLM-агент мог итеративно дорабатывать
  сгенерированный дек.
- **MCP-сервер**: 13 инструментов — `list_sources` + `list_exports`
  (обнаружение), `search`, `fetch_paper`, `fetch_pdf_text`,
  `download_pdfs`, `export` и шесть инструментов дека `pptx_*`
  (`inspect`, `review`, `update_slide`, `delete_slide`,
  `reorder_slides`, `add_slide`). Позволяет
  любому MCP-совместимому LLM
  (Claude Code, Claude Desktop, Cursor, …) управлять всем рабочим процессом.
- **Два пути обогащения** для выхода за пределы аннотации к настоящему
  деку в стиле дипломной презентации:
  - **LLM-as-agent (без ключа API)** — вызывающий LLM читает текст тела
    PDF через `fetch_pdf_text`, пишет структурированную сводку в контексте
    и передаёт её в `export`.
  - **Python pipeline (`--enrich`)** — CLI сам вызывает API Anthropic;
    модель по умолчанию `claude-opus-4-7`.
- **Потоки издателей через видимый Chrome**: SERP Scholar, IEEE `/rest/search`
  и каждая загрузка PDF из-за пейвола (ieeexplore / dl.acm / link.springer
  / sciencedirect / wiley / oup / nature / science / …) выполняются внутри
  реальной видимой сессии Chrome через `selenium`. Пользователь один раз решает
  captcha / завершает SSO в живом окне; `THESISAGENTS_CHROME_PROFILE_DIR`
  сохраняет cookie между запусками.
- **Поток LLM-as-agent**: MCP-инструменты предоставляют поиск, загрузку PDF и
  извлечение текста. `scripts/regen_*.py` содержит воспроизводимые примеры
  ручного составления насыщенного `PaperSummary` на каждую статью.
- **Резолвер OA PDF**: после дедупликации каждая статья без `pdf_url`
  проходит через Unpaywall → S2 `openAccessPdf` → поиск по заголовку arXiv →
  CORE.ac.uk (когда заданы ключи). Типичный прирост на запросах, богатых IEEE / ACM /
  Springer / Elsevier: 40-70 процентных пунктов.
- **Безопасность по умолчанию**: только HTTPS-транспорт HTTP, ограничение
  скорости по каждому источнику (token bucket), `defusedxml` для любого XML-payload,
  пути экспорта, защищённые от обхода каталогов, никакого `eval` / `exec` / `pickle` на
  пользовательском вводе.
- **Проверка словаря zh-tw / zh-cn**: ~244 regex-паттерна в
  `tests/test_i18n.py::test_zh_tw_files_use_traditional_chinese_vocabulary`
  ловят заимствованные слова упрощённого китайского, записанные традиционными
  иероглифами (например `內存` → `記憶體`, `魯棒性` → `穩健性`, `軟件` → `軟體`,
  `緩存` → `快取`). Та же проверка работает в обратную сторону для строк локали zh-cn.
  Полное правило + каталог regex живут в
  `.claude/agents/rules/language-vocabulary-check.md`.

## Быстрый старт

```powershell
git clone <repo-url>
cd ThesisAgents
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Install with dev extras (also pulls in MCP SDK and intelligence deps)
pip install -e .[dev]
```

Поиск в arXiv и экспорт дека + книги + BibTeX (по умолчанию для `--query`):

```powershell
py -m thesisagents --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

Получить одну статью по URL — по умолчанию `.pptx + .bib` (файл `.xlsx`
имеет меньше смысла для одной строки):

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

Отрисовать дек на 繁體中文:

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --lang zh-tw --out .\exports\
```

Обогащение через LLM-pipeline (Python сам вызывает Anthropic — нужен ключ API):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang zh-tw --out .\exports\
```

## Флаги CLI

| Флаг | Назначение |
|---|---|
| `--query` / `-q` | Ключевые слова (обязательно, если нет `--paper`). |
| `--paper` / `-p` | arXiv ID / URL, DOI, PMID или URL документа IEEE. Взаимоисключающе с `--query`. |
| `--source` / `-s` | Список источников через запятую. По умолчанию `arxiv`. |
| `--max` / `-n` | Макс. результатов на источник (1..200). По умолчанию 25. |
| `--year-from` / `--year-to` | Фильтр по годам включительно. |
| `--export` / `-e` | Форматы: любые из `pptx,xlsx,md,bib,json,ris,csv,csl`. По умолчанию зависит от режима (см. ниже). |
| `--out` / `-o` | Каталог вывода. По умолчанию `./exports`. |
| `--filename-stem` | Переопределить сгенерированную основу имени файла. |
| `--no-abstract` | Опустить содержимое аннотации из экспорта. |
| `--lang` / `-l` | Язык дека: один из 14 — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. По умолчанию `en`. |
| `--enrich` | Явно-падающий вариант авто-обогащения. Нужны `ANTHROPIC_API_KEY` и extra `[intelligence]`. (Авто-обогащение по умолчанию, когда ключ задан.) |
| `--lightweight` | Пропустить обогащение + принудительно дек только с аннотацией. Используйте только для быстрых / без присмотра запусков; **когда управляет LLM-агент, предпочитайте поток LLM-as-agent** ниже. |
| `--llm-model` | Переопределить модель по умолчанию `claude-opus-4-7` для обогащения. |
| `--no-pdf` | Пропустить автоматическую загрузку PDF. Также отключает гейт PPT на каждую статью (нет PDF → нет полного содержимого). |
| `--no-oa-resolve` | Пропустить пост-дедупликационный резолвер OA PDF (Unpaywall + S2 + arXiv + CORE.ac.uk). |
| `--top-tier-only` | Ограничить результаты arXiv + курируемым белым списком CS-флагманов (S&P, CCS, NDSS, USENIX Security, NeurIPS, ICML, ICSE, …). Выключено по умолчанию. |
| `--paywall-threshold` | Доля результатов из-за пейвола, запускающая запрос на подтверждение. По умолчанию 0.30. |
| `--yes` | Пропустить запрос про пейвол и продолжить. |
| `--max-slides` | Ограничение слайдов на статью (по умолчанию 25; передайте 0 для без лимита). |
| `--dark-mode` | Отрисовать pptx с тёмным фоном + почти белым текстом. По умолчанию — светлый дек с тёмно-синей полосой. |
| `--quiet` | Подавить построчную печать по каждой статье. |

### Переменные окружения

| Переменная | Используется | Назначение |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | Аутентификация LLM. Не нужна для пути LLM-as-agent через MCP. |
| `THESISAGENTS_LLM_MODEL` | `--enrich` | Переопределить модель по умолчанию `claude-opus-4-7`. |
| `THESISAGENTS_S2_API_KEY` | Semantic Scholar + резолвер OA | Более высокий лимит скорости; также используется шагом `openAccessPdf` S2 резолвера OA. Бесплатный ключ на <https://www.semanticscholar.org/product/api>. |
| `THESISAGENTS_NCBI_API_KEY` | PubMed | Поднимает анонимный лимит NCBI (3/с) до 10/с. Опционально. |
| `THESISAGENTS_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex, **Unpaywall** | Тег polite-pool + включает шаг Unpaywall резолвера OA (наибольший выигрыш по покрытию PDF для статей из-за пейвола IEEE / ACM / Springer / Elsevier; типичный прирост 40-70 пп). |
| `THESISAGENTS_IEEE_API_KEY` | IEEE (путь API) | Официальный IEEE Xplore API; выявляет `pdf_url` для статей в области действия. |
| `THESISAGENTS_DISABLE_IEEE_SCRAPING` | IEEE | **IEEE включён по умолчанию через видимый Chrome.** Задайте `=1`, чтобы отказаться (например CI без Chrome). Ветка httpx-скрейпа запускается только как запасной вариант, когда WebRunner недоступен. |
| `THESISAGENTS_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Токен подписчика Crossref Plus (заголовок Bearer). Опционально. |
| `THESISAGENTS_SPRINGER_API_KEY` | Springer | Обязательно; бесплатный ключ с <https://dev.springernature.com/>. Плагин выбрасывает `ConfigError` без него. |
| `THESISAGENTS_DISABLE_SCHOLAR_SCRAPING` | Google Scholar | **Scholar включён по умолчанию через видимый Chrome.** Задайте `=1`, чтобы отказаться (ToS Google запрещает автоматический доступ — включён по умолчанию для покрытия, отказ — чтобы избежать риска captcha / блокировки IP). |
| `THESISAGENTS_CHROME_PROFILE_DIR` | Scholar + IEEE + загрузки PDF из-за пейвола | Постоянный `--user-data-dir` Chrome. Задайте это и один раз завершите VPN / SSO / вход в Google; последующие запуски наследуют cookie, так что IEEE возвращает метаданные из-за пейвола, а Scholar выдаёт SERP без троттлинга. |
| `THESISAGENTS_DISABLE_WEBRUNNER` | Scholar + IEEE + загрузки PDF из-за пейвола | `=1` принудительно включает пути httpx вместо управления реальным Chrome. Полезно для CI / Docker без бинарника Chrome; иначе оставьте неустановленным. |
| `THESISAGENTS_CORE_API_KEY` | Резолвер OA + источник поиска `core` | Бесплатный ключ с <https://core.ac.uk/services/api>. Включает шаг OA-поиска CORE.ac.uk (200M+ институциональных / региональных OA-элементов) **и** источник поиска `core`. Без него источник `core` молча пропускается, а другие стратегии OA (Unpaywall, S2, arXiv) всё равно работают. |
| `THESISAGENTS_PDF_COOKIES_FILE` | Загрузчик PDF | Netscape `cookies.txt`. Выключено по умолчанию. Используйте только с издателями, на которых у вас есть институциональные права. |
| `THESISAGENTS_LOG_LEVEL` | логгер | `INFO` по умолчанию; `DEBUG` для подробной трассировки. |

По умолчанию: `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. Всегда
переопределяется явным `--export`.

## Поток LLM-as-agent

Когда LLM в вашем редакторе управляет рабочим процессом, используйте
MCP-инструменты по порядку: `search`, `download_pdfs`, `fetch_pdf_text`, затем `export` с
вручную составленным насыщенным `PaperSummary`. Существующие файлы `scripts/regen_*.py` —
воспроизводимые примеры для финального шага составления и экспорта.

Полный сквозной runbook (поиск → насыщенный дек) живёт в
`.claude/agents/tasks/paper-summary-author.md` — откройте его перед началом
нового запроса, чтобы LLM мог выполнить поток без пауз на пользовательский ввод.

## MCP-сервер

Зарегистрировать в Claude Code:

```powershell
claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp
```

Или запишите в свой файл настроек:

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

Инструменты:

| Инструмент | Назначение |
|---|---|
| `list_sources` | Перечислить каждый плагин + сообщить, включён ли каждый в текущем окружении. Вызовите это один раз перед `search`. |
| `list_exports` | Перечислить каждый формат экспорта с однострочным описанием и тем, пишет ли он один сводный файл или один файл на статью. |
| `search` | Ключевые слова → список статей. Принимает `top_tier_only`, `min_citations`; по умолчанию — полный набор источников без ключа API. |
| `fetch_paper` | Идентификатор arXiv / DOI / PMID / IEEE → одна статья. |
| `fetch_pdf_text` | Загрузить один PDF, вернуть извлечённый текст тела. **MCP-путь к «я прочитал статью».** |
| `download_pdfs` | Пакетно загрузить PDF из списка статей в `{out_dir}/pdfs/`. Возвращает результаты по каждой статье с ключами по ключу BibTeX. |
| `export` | Список статей + форматы → пишет `.pptx/.xlsx/.md/.bib/.json/.ris/.csv/.csl.json`. Принимает поле `summary` на статью для насыщенной схемы в стиле дипломной презентации, `max_slides_per_paper` (по умолчанию 25) и `dark_mode` (по умолчанию `false` — по умолчанию проекта светлый дек с тёмно-синей полосой, передайте `true` для тёмного пост-прохода OLED / при слабом свете). |
| `pptx_inspect` | Прочитать структуру слайдов / фигур существующего дека. |
| `pptx_review` | Проверить дек за один вызов — переполнение + цветовые контракты + полнота секций `paper_rule`. Автоопределяет язык дека; также CLI `python -m thesisagents review <deck.pptx>`. |
| `pptx_update_slide` | Заменить `title` / `body` / `meta` (по имени фигуры) или произвольные фигуры по индексу. |
| `pptx_delete_slide` | Удалить слайд и его связь части. |
| `pptx_reorder_slides` | Переставить слайды через `sldIdLst`. |
| `pptx_add_slide` | Добавить в конец или вставить новый слайд title / body / meta. |

Поток LLM-as-agent (не нужен `ANTHROPIC_API_KEY` — LLM и есть агент):

```
1. (optional) list_sources()                       # discover enabled plugins
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (optional) download_pdfs(papers, out_dir="./exports/...")  # persist PDFs
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # per paper
5. (the LLM reads body text, produces a structured `summary` dict)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="zh-tw", formats=["pptx","bib"], dark_mode=true, ...)
```

Полный справочник в [`docs/mcp.md`](docs/mcp.md).

## Структура проекта

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

## Определение готовности (Definition of Done)

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r thesisagents/
```

Флаг `-c` у bandit обязателен — без него bandit игнорирует
конфигурацию пропусков проекта. При правках экспортёра pptx также запустите
проверку переполнения (см. `CLAUDE.md` «Slide Deck Rules»).

## Настольный GUI (PySide6)

Нативный настольный интерфейс поставляется за extra `[gui]`:

```powershell
pip install thesisagents[gui]
thesisagents-gui                 # or: thesisagents gui
```

У окна четыре вкладки — **Search**, **Settings** (сохраняет ключи API
через QSettings), **Enrich** (управляет обогащением LLM-as-agent / Python-pipeline
через сигнал `collection_ready`) и **Deck** (переключатель Light
mode + ограничение слайдов + контролы max-figures проходят в
`ExportOptions`). Windows-релизный zip поставляет скомпилированный Nuitka
бандл с включённым PySide6, так что `thesisagents.exe gui` работает
без отдельной установки Python.
**UI поставляется на всех 14 языках** (English, 繁體中文, 简体中文,
日本語, Español, Français, Deutsch, 한국어, Português, Русский,
Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia) — при первом запуске язык
выбирается по локали ОС, затем **Settings → Interface
language** позволяет его сменить. Язык вывода дека — отдельный
выпадающий список, так что можно запускать UI на одном языке, а выдавать
слайды на другом. Раскладка адаптивная: каждая форма сидит в
`QScrollArea`, а окно уменьшается до 900×600 (всё ещё помещается в
720p), с масштабированием HiDPI, включённым по умолчанию.

Полный справочник: [`docs/gui.md`](docs/gui.md).

## Упаковка в автономный исполняемый файл

Задокументированы два упаковщика для поставки однофайлового бинарника,
который работает без установленного Python:

- **[`docs/packaging-pyinstaller.md`](docs/packaging-pyinstaller.md)**
  — быстрая сборка (менее минуты), вывод 200–300 МБ, запуск 2–4 с.
  Лучше всего, когда вы итерируете по сборочному скрипту.
- **[`docs/packaging-nuitka.md`](docs/packaging-nuitka.md)** —
  медленная сборка (5–15 минут), вывод 80–150 МБ, запуск менее секунды,
  некоторая защита байткода. Лучше всего, когда конечные пользователи
  запускают бинарник много раз.

Оба документа покрывают специфичную для проекта загвоздку — динамические
плагины источников под `sources/<name>/` — и поставляют проверенную команду
для точек входа CLI и MCP-сервера.

## Непрерывная интеграция и релизы

Два workflow GitHub Actions живут под `.github/workflows/`:

- **`ci.yml`** запускается на каждый push и PR в `main`. Матрица — Ubuntu +
  Windows × Python 3.12 / 3.13 / 3.14 (6 задач). Каждая задача запускает
  `ruff check`, `bandit -c pyproject.toml` и `pytest`.
- **`release.yml`** ждёт завершения `ci.yml` на `main`
  (триггер `workflow_run`). Он запускается, только если CI прошёл. **Каждый
  push с успешным CI в `main` — это релиз** — workflow авто-инкрементирует
  patch-версию в `pyproject.toml`, коммитит инкремент обратно в
  `main` как `chore: bump version to X.Y.Z` и запускает конвейер:
  1. **`bump-version`** — прочитать текущую `X.Y.Z` из `pyproject.toml`,
     увеличить до `X.Y.(Z+1)`, закоммитить + запушить обратно в `main`, используя
     `GITHUB_TOKEN` workflow. Этот push НЕ пере-запускает CI (по
     правилу GitHub, что push’и от `GITHUB_TOKEN` не могут запускать новые
     прогоны workflow), так что цикл завершается естественно.
  2. **`publish-pypi`** — собрать sdist + wheel, `twine check`,
     `twine upload` через `PYPI_API_TOKEN`.
  3. **`create-draft-release`** — открыть *черновой* релиз GitHub на
     теге `v<version>` с авто-сгенерированными заметками.
  4. **`build-nuitka`** — скомпилировать автономный бандл Nuitka на
     Windows-раннере (точка входа: `python -m thesisagents` через
     `--python-flag=-m`), провести smoke-тест, заархивировать получившуюся
     папку `thesisagents.dist/`, прикрепить zip + контрольную сумму `.sha256`
     к черновому релизу. Автономный (не onefile) по
     замыслу: onefile само-распаковывается в `%TEMP%` при каждом запуске,
     добавляя задержку старта и провоцируя эвристики антивируса на
     заблокированных машинах. Только для Windows тоже по замыслу: пользователи
     Linux / macOS ставят с PyPI. Кэш сборки, ключом по `pyproject.toml`,
     сокращает тёплые сборки с ~70 мин холодной до ~5–10 мин.
  5. **`publish-release`** — снять пометку черновика, как только загружен
     артефакт Nuitka, чтобы пользователи никогда не видели наполовину
     готовый релиз.

  **Пропуск релиза.** Включите `[skip release]` где угодно в
  сообщении коммита — и инкремент + каждая нижестоящая задача пропускаются; используйте
  это для коммитов только-документация / опечатка / рефакторинг, которые не должны сжигать
  номер версии.

Чтобы включить публикацию на PyPI + релизные исполняемые файлы:

1. Сгенерируйте токен API с областью проекта на
   <https://pypi.org/manage/account/token/>.
2. В репозитории GitHub: `Settings → Secrets and variables → Actions →
   New repository secret`. Назовите его `PYPI_API_TOKEN` и вставьте
   значение токена.
3. Разрешите GitHub Actions пушить в `main`: `Settings → Actions →
   General → Workflow permissions → Read and write permissions`. Коммит
   инкремента пушится через `GITHUB_TOKEN` workflow.
4. Выпускайте релизы, вливая PR в `main`. Конвейеру нужно
   ~3–5 мин, чтобы опубликовать на PyPI, и ещё ~50–70 мин (холодно) или ~5–10 мин
   (тёплый кэш Nuitka), чтобы прикрепить Windows-zip.

Задача `publish-pypi` намеренно НЕ прикрепляет GitHub
Environment, так что каждый прогон отображается как запись Release (с прикреплённым
`.exe` Nuitka), а не как виджет «Deployment» в боковой панели на
домашней странице репозитория — релизы получают свою выделенную страницу,
а запись Deployment сверху была бы просто избыточным шумом.

## Лицензия

См. `LICENSE`. API arXiv используется в соответствии с условиями использования API arXiv
(<https://info.arxiv.org/help/api/tou.html>) — соблюдайте мягкий лимит 1 запрос
в 3 секунды; поставляемый фетчер уже обеспечивает это через
свой token bucket.
