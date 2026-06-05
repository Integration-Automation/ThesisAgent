Руководство пользователя ThesisAgents
========================================

Поисковый ассистент статей, управляемый ключевыми словами. Получает
результаты из arXiv, Semantic Scholar, OpenAlex, PubMed, ACM, IEEE
Xplore, DBLP, Crossref, OpenAIRE, Springer Nature и Google Scholar; и
экспортирует как презентацию PowerPoint в стиле дипломной работы,
книгу Excel и файл BibTeX. Всё за один CLI-вызов или один вызов
MCP-инструмента.

.. contents:: Содержание
   :depth: 2
   :local:

----

Для ИИ-агентов, управляющих этим проектом
-----------------------------------------

**Если вы LLM (Claude Code, Cursor, Aider, Codex CLI, …) и читаете это,
чтобы понять, что делать — начните здесь.** Те же правила закреплены
в ``AGENTS.md`` (зеркало для всех агентов) и ``CLAUDE.md`` (канонический
справочник) в корне репозитория; прочитайте их перед нетривиальными
изменениями.

**Целевой результат — обогащённый ``.pptx`` в стиле дипломной по каждой
статье**, а не легковесный дек только-аннотация, который CLI выдаёт по
умолчанию. Легковесная выдача — промежуточный артефакт; ваша задача
повысить её уровень.

Дерево решений
^^^^^^^^^^^^^^

1. ``ANTHROPIC_API_KEY`` задана? → запустите CLI; автоматическое
   обогащение через API Anthropic.
2. Ключа нет, ведёт LLM → **пишете обогащённую сводку вы сами**.
   Прочитайте каждый PDF, вручную составьте ``PaperSummary`` с полями
   rich-tier, положите ``scripts/regen_<query>.py``, запустите. **Не
   говорите пользователю «установите API-ключ»** — вы и есть LLM.
3. LLM нет (CI / cron) → легковесная выдача допустима.

MCP в 6 шагов
^^^^^^^^^^^^^

.. code-block:: text

   1. (опц.) list_sources()
   2. search(keywords, sources, top_tier_only=true, ...)
   3. (опц.) download_pdfs(papers, out_dir="./exports/...")
   4. fetch_pdf_text(pdf_url=paper.pdf_url)           # по каждой статье
   5. (вы читаете каждый PDF и составляете структурированный dict сводки)
   6. export(papers=[{...paper, "summary": {...}}], language="ru", ...)

Все 11 MCP-инструментов: :doc:`/mcp`.

Обязательно: проверка URL / DOI перед сдачей
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

URL-пути издателей **нельзя угадать** — AAAI использует числовые ID
(``v40i5.37389``), IEEE использует непрозрачный ``arnumber``, ACM —
непрозрачные DOI. При ручной сборке ``Paper`` **копируйте ``url`` /
``doi`` / ``arxiv_id`` дословно из xlsx, который сгенерировал этот
поиск** — никогда по памяти, никогда из заголовка.

xlsx пишется в ``exports/<run>/<slug>-<timestamp>.xlsx``, столбец 7 =
DOI, столбец 8 = URL. Прогоните аудит после regen-скрипта:

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

Запреты
^^^^^^^

* Не говорите пользователю «установите ``ANTHROPIC_API_KEY``» — вы и
  есть LLM.
* Не считайте легковесный ``.pptx`` итогом.
* Не останавливайтесь после ``download_pdfs``.
* Не выдумывайте числа, RQ, вклады, ограничения.
* Не фабрикуйте URLs / DOIs / arXiv ID.
* Не оставляйте нерелевантные загрузки в рабочем каталоге. Поиск по
  ключевым словам может подтянуть статьи не по теме (запрос «Claude
  code» вернул статью про декодер Витерби). Удалите нерелевантные
  ``pdfs/<key>.pdf`` и легковесные ``<key>.pptx``; сохраняйте
  сводный xlsx / bib как честную запись. Полный порядок в
  ``CLAUDE.md`` «Pruning irrelevant downloads».
* Не упоминайте «Claude», «Claude Code», «AI-generated», «GPT»,
  «Copilot» и любые имена ИИ-инструментов/моделей в коммитах, PR,
  комментариях кода или документации.

Примеры: ``scripts/regen_llm_security_batch.py`` (en, 8 статей) и
``scripts/regen_llm_security_batch_zh_tw.py`` (zh-tw).

----

Установка
---------

Требуется Python **3.12+**.

.. code-block:: bash

   git clone <repo-url>
   cd ThesisAgents
   python -m venv .venv
   .venv\Scripts\Activate.ps1            # Windows PowerShell
   # source .venv/bin/activate           # Linux / macOS
   pip install -e .[dev]

Опциональные extras: ``[mcp]``, ``[intelligence]``, ``[web]``, ``[dev]``.

----

Быстрый старт
-------------

.. code-block:: bash

   # Поиск по arXiv → дек + workbook + BibTeX
   thesisagents --query "diffusion models" --source arxiv --max 10 \
                  --out ./exports/

   # Одна статья по URL → дек + BibTeX
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --filename-stem attention --out ./exports/

   # Рендер дека на русском
   thesisagents --paper 1706.03762 --lang ru --out ./exports/

   # Обогащение через Python pipeline (нужен ключ Anthropic)
   export ANTHROPIC_API_KEY=sk-ant-...
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --enrich --lang ru --out ./exports/

Полная таблица флагов CLI: :doc:`/cli`.

----

Где искать дальше
-----------------

* Флаги CLI и переменные окружения: :doc:`/cli`
* 11 инструментов MCP-сервера: :doc:`/mcp`
* Инструменты редактирования PPTX: :doc:`/pptx_editing`
* В файле ``readmes/README.ru.md`` в корне репозитория есть полный список
  возможностей проекта.
* Глубокий технический справочник (архитектура плагинов, политики
  безопасности, Definition of Done, правила SonarQube, …)
  консолидирован в английском руководстве: :doc:`/en/index`.
