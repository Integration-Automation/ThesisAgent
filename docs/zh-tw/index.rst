ThesisAgents 使用手冊
========================

以關鍵字驅動的論文搜尋助手。從 arXiv(以及可外掛的其他來源)抓取結果,
正規化成統一的 record,並把去重、排序後的結果集匯出為 PowerPoint 投影片、
Markdown 摘要、BibTeX 檔、與 JSON 原始資料 —— 一次 CLI 呼叫或一次 MCP
工具呼叫即可完成。

.. contents:: 目錄
   :depth: 2
   :local:

----

給驅動本專案的 AI agent 看
--------------------------

**如果你是 LLM(Claude Code、Cursor、Aider、Codex CLI …)正在讀這份指南
想搞清楚要做什麼 —— 從這節開始。** 同一套規則也釘在 repo 根目錄的
``AGENTS.md``\ (跨 agent 鏡像)與 ``CLAUDE.md``\ (權威來源),做
非小改動前請先讀。

**交付物是每篇一份論文口試級的富版 PPT,不是 CLI 預設出的只有摘要的
輕量版。** 輕量 emit 是中間產物 —— 你的工作就是把它升級。

決策樹
^^^^^^

1. 環境有 ``ANTHROPIC_API_KEY`` 嗎? → 直接跑 CLI,它會自動 enrich。
2. 沒 key,但你(LLM)正在驅動 → **你自己手寫 rich summary**。每篇
   PDF 自己讀,手寫 ``PaperSummary`` 含 rich-tier 欄位,放
   ``scripts/regen_<query>.py``,跑它。不要叫使用者去設 API key ——
   你就是那個會寫 summary 的 LLM。
3. 沒 LLM(CI / cron / 無人值守)→ 輕量版可以接受。

MCP 6 步流程
^^^^^^^^^^^^

.. code-block:: text

   1. (選) list_sources()                                # 看哪些 plugin 已啟用
   2. search(keywords, sources, top_tier_only=true, ...)
   3. (選) download_pdfs(papers, out_dir="./exports/...")
   4. fetch_pdf_text(pdf_url=paper.pdf_url)              # 每篇都要
   5. (你逐篇讀 PDF,自己產 structured summary dict)
   6. export(papers=[{..., "summary": {...}}], language="zh-tw", ...)

共 11 個 MCP 工具,完整參考見 :doc:`/mcp`。

必做:交付前驗證 URL / DOI
^^^^^^^^^^^^^^^^^^^^^^^^^^

出版商的 URL 路徑 **不能用猜的**\ 。AAAI 用數字 ID
(``v40i5.37389``),IEEE 用 opaque ``arnumber``,ACM 用 opaque DOI。
手寫 ``Paper`` 時,``url`` / ``doi`` / ``arxiv_id`` 必須\ **逐字
從同一次搜尋產生的 xlsx 抄** —— 不能憑印象,也不能從標題自己拼。

xlsx 寫在 ``exports/<run>/<slug>-<timestamp>.xlsx``\ ,第 7 欄是 DOI、
第 8 欄是 URL。Regen 跑完做這個 audit:

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

禁忌
^^^^

* 不要告訴使用者「設 ``ANTHROPIC_API_KEY`` 才能拿到富版」—— 你就是那個 LLM。
* 不要把輕量 ``.pptx`` 當交付物。
* 不要看到 ``download_pdfs`` 回報「N 份 PDF 已存」就停。
* 不要編造論文裡沒有的數字、RQ、貢獻、限制。
* 不要編造 URL / DOI / arXiv ID。
* 不要把不相關下載留在 run 目錄裡。關鍵字搜尋會帶到無關論文
  (例如「Claude code」抓到 Viterbi 解碼器論文)。把無關論文的
  ``pdfs/<key>.pdf`` 與輕量 ``<key>.pptx`` 刪掉,aggregate xlsx / bib
  保留作為「誠實紀錄」。完整流程見 ``CLAUDE.md`` 的「Pruning
  irrelevant downloads」。
* 不要在 commit message、PR description、程式註解或文件提到
  「Claude」、「Claude Code」、「AI-generated」、「GPT」、「Copilot」
  或任何 AI 工具 / 模型名稱。

範例:\ ``scripts/regen_llm_security_batch.py``\ (en)與
``scripts/regen_llm_security_batch_zh_tw.py``\ (zh-tw)裡有 8 篇照
這套流程手寫的 rich summary,當 template 用。

----

安裝
----

ThesisAgents 鎖定 Python **3.12+**\ (以 3.14 開發),支援 Windows、
macOS、Linux。建議使用專案內的 virtualenv:

.. code-block:: bash

   git clone <repo-url>
   cd ThesisAgents
   python -m venv .venv
   .venv\Scripts\Activate.ps1            # Windows PowerShell
   # source .venv/bin/activate           # Linux / macOS

   pip install -e .[dev]

``dev``\ extra 會拉進 ``pytest``\ 、``pytest-asyncio``\ 、``pytest-httpx``\ 、
``ruff``\ 、``bandit``\ 與 ``mcp``\ SDK。若只需要 MCP server,可以裝較輕的
``[mcp]``\ 。

可選相依群組
^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Extra
     - 解鎖什麼
   * - ``[mcp]``
     - 只裝 ``mcp``\ SDK。用在 production 安裝 ——
       想要 ``thesisagents-mcp``\ 但不想要測試工具鏈時。
   * - ``[intelligence]``
     - ``pypdf``\ + ``anthropic``\ 。Python ``--enrich``\ 路徑用
       (抓 PDF + 打 Anthropic API)。**MCP 上的 LLM-as-agent 流程
       不需要這個** —— LLM 自己就是 agent。
   * - ``[web]``
     - ``fastapi``\ + ``uvicorn``\ + ``streamlit``\ —— 預留給之後的網頁 UI。
       CLI 跟 MCP server 不需要這個。
   * - ``[dev]``
     - 完整開發工具鏈: pytest、asyncio + httpx 測試外掛、ruff、bandit、
       MCP SDK 與 intelligence 相依(讓所有測試能跑)。

----

CLI
---

``python -m thesisagents``\ (也安裝為 ``thesisagents``)是入口程式。
有兩個互斥的模式:

搜尋模式
^^^^^^^^

.. code-block:: bash

   # 預設 25 筆結果,預設匯出(pptx、xlsx、bib)
   thesisagents --query "diffusion models" --source arxiv

   # 10 筆結果,全部匯出格式,自訂目錄
   thesisagents --query "transformer attention" --source arxiv \
                --max 10 --export pptx,xlsx,md,bib,json \
                --out ./exports/

   # 限制在近年論文
   thesisagents --query "graph neural networks drug discovery" \
                --year-from 2022 --year-to 2025 \
                --max 15 --out ./exports/

單篇論文模式
^^^^^^^^^^^^

.. code-block:: bash

   # arXiv ID —— 單篇預設只出 pptx + bib
   thesisagents --paper 1706.03762 --out ./exports/

   # arXiv URL
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                --filename-stem attention --out ./exports/

   # DOI(透過 Semantic Scholar resolve)
   thesisagents --paper "10.1145/3411764.3445005" --out ./exports/

   # PubMed PMID / URL
   thesisagents --paper "https://pubmed.ncbi.nlm.nih.gov/34567890/" \
                --out ./exports/

   # IEEE document URL(需 opt-in env var)
   THESISAGENTS_DISABLE_IEEE_SCRAPING=1 \
   thesisagents --paper "https://ieeexplore.ieee.org/document/10965643" \
                --out ./exports/

可用的 source plugin
^^^^^^^^^^^^^^^^^^^^

沒給 ``--source`` 時的預設組合是「所有不需要 API key 的 plugin」:
``arxiv``、``semantic_scholar``、``openalex``、``pubmed``、``acm``、
``dblp``、``crossref``、``openaire``。設下面三個 env var 之一,對應
plugin 也會加進來:

.. list-table::
   :header-rows: 1
   :widths: 18 30 52

   * - Plugin
     - Env var
     - 備註
   * - ``ieee``
     - ``THESISAGENTS_IEEE_API_KEY``\ (建議)**或**\
       ``THESISAGENTS_DISABLE_IEEE_SCRAPING=1``
     - 官方 Xplore API 在訂閱範圍內會帶 ``pdf_url``;沒 key 時可用
       fallback 爬取路徑。
   * - ``springer``
     - ``THESISAGENTS_SPRINGER_API_KEY``
     - 免費 key 申請 https://dev.springernature.com/。
       涵蓋 Nature、Scientific Reports、LNCS 等 Springer 全系。
       沒 key 時 plugin 會在建構時拋 ``ConfigError``,被 pipeline
       靜默跳過。
   * - ``scholar``
     - ``THESISAGENTS_DISABLE_SCHOLAR_SCRAPING=1``
     - Google Scholar ToS 禁止爬取,預設關閉。

搜尋管線預設套用「頂級期刊白名單」(旗艦級 CS 會議 + Nature / Science /
PNAS / CACM / LNCS);傳 ``--all-venues`` 可關閉。

在地化 deck 與 LLM enrichment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # 把投影片樣板字串改成繁體中文
   thesisagents --paper 1706.03762 --lang zh-tw --out ./exports/

   # Python pipeline 走 enrichment(PDF + Anthropic API → thesis-style)
   export ANTHROPIC_API_KEY=sk-ant-...
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                --enrich --lang zh-tw --out ./exports/

完整參數表: :doc:`/cli`。

----

輸出檔
------

每種匯出會在 ``--out``\ 寫一個檔。預設檔名為
``{關鍵字前 32 字}-{YYYYMMDD-HHMMSS}.{副檔名}``;用
``--filename-stem``\ 固定 stem。預設值依模式不同:

* ``--query`` → ``pptx`` + ``xlsx`` + ``bib``
* ``--paper`` → ``pptx`` + ``bib``\ (單篇出 Excel 是浪費)

.. code-block:: text

   exports/
   ├── attention.pptx     # 16:9 寬螢幕投影片(配置見下)
   ├── attention.xlsx     # Papers 工作表 + Query 出處工作表
   ├── attention.bib      # 不會撞 key,LaTeX 特殊字元已跳脫
   ├── attention.md       # 完整來源 / 標題 / 摘要列表(opt-in)
   └── attention.json     # 原始 payload(opt-in)

``.xlsx`` 的 Papers 工作表有兩個外觀類似但意義不同的相鄰欄位:

* **Source**\ (第 5 欄)—— 真實刊登出處,例如\ ``IEEE Access``\ 、
  ``NDSS 2026``\ 、``Nature Machine Intelligence``\ 。
* **Indexed via**\ (第 6 欄)—— 是哪個 fetcher 抓到這筆 metadata,
  例如\ ``openalex``\ 、``crossref``\ 、``arxiv``\ 。當同一篇論文可以
  從多條路徑抓到時,這個分欄很重要 —— 例如一篇 Nature 論文透過
  OpenAlex 索引時,Source 顯示\ ``Nature``\ ,Indexed via 會顯示
  ``openalex``\ 。

PPTX 配置
^^^^^^^^^

16:9 寬螢幕、附頁碼。三種 rendering tier 依資料多寡自動挑:

* **輕量**\ —— 只有 ``paper.abstract``\ 。封面 + agenda + 每篇
  (section divider + overview + 句子切片的 Background / Approach
  / Findings) + references。
* **扁平結構化**\ —— ``Paper.summary``\ 的扁平 tier 有值
  (``motivation`` / ``contributions`` / ``method`` /
  ``results`` / ``limitations`` / ``takeaways``)。一張投影片
  對應一個非空 section。
* **thesis-style 口試級**\ —— ``Paper.summary``\ 有 rich-tier 欄位
  (``pain_points``\ 四宮格、研究問題 callout、``contributions_detailed``
  + ``headline_metrics``\ 、技術比較表、文獻定位表、系統總覽、
  方法細節、評估方法、研究問題、每題 RQ 結果表、貢獻總結、
  核心觀察、限制與未來工作、Q&A、參考文獻)。每篇 20+ 張投影片。

所有樣板字串(議程 / 參考文獻 / 第 N 篇 / 頁尾)都走
``thesisagents.exporters.i18n``\ ,跟 ``--lang``\ 連動。支援的語言:
``en``\ (預設)、``zh-tw``\ 、``zh-cn``\ 、``ja``\ 、``es``\ 、
``fr``\ 、``de``\ 、``ko``\ 、``pt``\ 、``ru``\ 、``it``\ 、``vi``\ 、
``hi``\ 、``id``\ ,共 14 種。傳其他值會靜默 fallback 到 ``en``\ 。

每張投影片上的每個文字框都帶有語義 ``name``\ (``title``\ 、
``meta``\ 、``body``\ 、``subhead``\ 、``footer``\ 、``page_number``\ 、
``kpi``\ 、``rq_box``),編輯工具可以靠 name 定位 shape,不必依賴視覺位置。
詳見 :doc:`/pptx_editing`。

----

MCP server
----------

ThesisAgents 附帶一個暴露 **11 個工具** 的 MCP server —— 來源探索
(``list_sources``)、搜尋、單篇抓取、單一 PDF 本文擷取
(``fetch_pdf_text``)、批次 PDF 下載(``download_pdfs``)、匯出,
以及 5 個 PPTX 編輯操作。任何支援 MCP 的 LLM client(Claude Code、
Claude Desktop、Cursor …)都能驅動整套流程。

設定 MCP client(以 Claude Code 為例):

.. code-block:: powershell

   claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp

或直接編輯 settings 檔:

.. code-block:: json

   {
     "mcpServers": {
       "thesisagents": {
         "command": ".venv\\Scripts\\python.exe",
         "args": ["-m", "thesisagents.mcp"]
       }
     }
   }

工具速查:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Tool
     - 用途
   * - ``list_sources``
     - 列出所有 plugin + 回報目前 process 下哪些已啟用。
       ``search`` 前先呼叫,agent 才知道要傳什麼 ``sources``。
   * - ``search``
     - 關鍵字 → 論文列表(shape 同 ``Paper.to_dict()``)。可帶
       ``top_tier_only``\ (預設 ``True``\ )與 ``min_citations``\ ;
       省略 ``sources`` 時預設掃所有不需要 API key 的來源。
   * - ``fetch_paper``
     - arXiv / DOI / PMID / IEEE 識別碼 → 單篇論文。
   * - ``fetch_pdf_text``
     - 抓單一 PDF 並回傳擷取的本文。**MCP 路徑下「讓我讀過論文」的入口。**
   * - ``download_pdfs``
     - 把一組論文的 PDF 批次下載到 ``{out_dir}/pdfs/``\ 。回傳以
       BibTeX key 為索引的逐篇結果。
   * - ``export``
     - 論文列表 + 格式 → 寫出 ``.pptx/.xlsx/.md/.bib/.json``\ 。每篇
       論文可附 ``summary``\ 欄位走 thesis-style;支援 ``language``\
       走 i18n,以及 ``max_slides_per_paper``\ (預設 25;傳 ``0``\
       代表不限)。
   * - ``pptx_inspect``
     - 讀既有投影片檔的 slide / shape 結構。
   * - ``pptx_update_slide``
     - 取代 ``title``/ ``body``/ ``meta``\ (透過 shape name)或
       任意 shape(透過 index)。
   * - ``pptx_delete_slide``
     - 刪掉一張 slide 以及它的 part relationship。
   * - ``pptx_reorder_slides``
     - 透過 ``sldIdLst``\ 重排投影片。
   * - ``pptx_add_slide``
     - 在尾端 append 或在指定 position 插入一張新的 title /
       body / meta slide。

LLM-as-agent enrichment 流程(不需要 Anthropic API key):

1. (選)\ ``list_sources()``\ 看目前 process 下哪些 plugin 已啟用。
2. ``search(keywords, sources, top_tier_only, ...)``\ 多篇,或
   ``fetch_paper(identifier)``\ 抓單篇。
3. (選)\ ``download_pdfs(papers, out_dir)``\ 把每篇 PDF 批次存到
   本機。
4. ``fetch_pdf_text(paper.pdf_url)``\ 逐篇拿本文。
5. LLM 在自己 context 裡讀本文,產 structured ``summary``\ dict。
6. ``export(papers=[{..., "summary": {...}}], language="zh-tw", ...)``\ 。

完整參考: :doc:`/mcp`。

----

編輯產生好的投影片
------------------

投影片產出後,``pptx_*``\ 工具(或 ``thesisagents.exporters.pptx_edit``
Python 模組)讓你在不重跑搜尋的情況下繼續對它做迭代:

.. code-block:: python

   from thesisagents.exporters import pptx_edit

   pptx_edit.update_slide(
       "exports/attention.pptx", slide_index=1,
       title="Attention Is All You Need (Vaswani et al., 2017)",
       body="The Transformer dispenses with recurrence and convolutions...",
   )

   pptx_edit.add_slide(
       "exports/attention.pptx",
       title="Conclusion",
       body="We covered transformers and follow-on work.",
   )

   pptx_edit.reorder_slides("exports/attention.pptx", [0, 2, 1])

每個 helper 預設原地存檔;傳 ``out_path=...``\ 可以另存,原檔不動。
完整參考: :doc:`/pptx_editing`。

----

架構
----

::

   ThesisAgents/
   ├── thesisagents/                 # 主套件
   │   ├── core/                     # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
   │   ├── fetchers/                 # HTTPS-only http client、token bucket、Fetcher base
   │   ├── exporters/                # pptx(thesis-style + lightweight)、xlsx、
   │   │                             #   bibtex、markdown、json + pptx_edit + i18n
   │   ├── intelligence/             # PDF 抓取 + Anthropic 摘要器([intelligence] extra)
   │   ├── mcp/                      # 註冊 11 個工具的 FastMCP server
   │   ├── utils/                    # logging、path safety
   │   ├── cli.py                    # argparse CLI
   │   └── __main__.py               # `python -m thesisagents`
   ├── sources/                      # 各來源 plugin(arxiv、semantic_scholar、
   │                                 #   openalex、pubmed、acm、ieee、scholar、
   │                                 #   dblp、crossref、openaire、springer)
   ├── tests/                        # pytest suite + 錄製 fixture,不打活 HTTP
   ├── docs/                         # 這份 Sphinx 文件(en + zh-tw + zh-cn)
   ├── scripts/                      # 一次性 regen / fixture-record 腳本
   └── pyproject.toml                # metadata + ruff / bandit + optional extras

核心 vs 來源外掛
^^^^^^^^^^^^^^^^

``thesisagents/``\ (核心)與 ``sources/<name>/``\ (外掛)的分界線是
**相依負擔與失敗隔離**,不是「跟來源有關的東西全丟外掛」:

* **核心**\ 跑在預設相依集
  (``httpx``\ 、``pydantic``\ 、``defusedxml``\ 、``python-pptx``\ 、
  ``openpyxl``\ 、``bibtexparser``\ 、``beautifulsoup4``\ 、``lxml``\ 、
  ``markdown-it-py``),涵蓋所有使用者都該預設可用的流程。
* **外掛**\ 是任何需要重 / 可選 runtime 相依(``selenium``\ 處理 Scholar
  的 JS 頁面、IEEE / ACM 廠商 SDK …)或獨立發版節奏的東西。

兩條 enrichment 路徑
^^^^^^^^^^^^^^^^^^^^

* **LLM-as-agent(不需要 API key)**\ —— 由 MCP-aware 的 LLM 驅動。
  ``fetch_paper``\ + ``fetch_pdf_text``\ 給它 metadata + 本文;LLM 在自己
  context 裡產 structured ``summary``\ ;``export``\ 寫出檔案。
* **Python pipeline(``--enrich``\ )** —— 給沒有 LLM 在外面的自動化用。
  需要 ``ANTHROPIC_API_KEY``\ 與 ``[intelligence]``\ extra,預設模型
  ``claude-opus-4-7``\ ,可用 ``--llm-model``\ 或
  ``THESISAGENTS_LLM_MODEL``\ 蓋掉。

網路安全
^^^^^^^^

所有對外的 HTTP 都走 ``thesisagents.fetchers.http.get_client(source)``,
回傳一個用 HTTPS-only transport 包起來的 per-source ``httpx.AsyncClient``\ 。
純 HTTP 請求一律被拒(包括 redirect 後變 HTTP)。每個來源宣告自己的
``RateLimit``\ 政策,由 token bucket 強制執行;arXiv 預設為
**每 3 秒 1 次、抖動 0.5s**,對應它的官方軟限制。

----

開發流程
--------

Definition of Done
^^^^^^^^^^^^^^^^^^

每次變更都要過三道閘才能 commit(見 ``CLAUDE.md``):

.. code-block:: bash

   .venv\Scripts\python.exe -m pytest tests/
   .venv\Scripts\python.exe -m ruff check .
   .venv\Scripts\python.exe -m bandit -c pyproject.toml -r thesisagents/ sources/

bandit 的 ``-c``\ 旗標是 **必要的**\ —— 沒它 bandit 不會讀專案 skip 設定,
跑出來會充滿假警報。

測試
^^^^

測試結構鏡像 production: 每個 production 模組
``thesisagents/<area>/<feature>.py``\ 都有一個對應的
``tests/test_<feature>.py``\ 。來源外掛測試在 ``tests/sources/<name>/``\ 。

測試是 **hermetic**\ —— 每個 fetcher 測試都透過 monkeypatched HTTP
transport 載入錄製好的 fixture。錄新的 fixture 是獨立的手動步驟
(``scripts/record_fixture.py``),錄完的檔要 commit 進去。

跑整個 suite:

.. code-block:: bash

   .venv\Scripts\python.exe -m pytest tests/

目前 89 個測試,約 2 秒跑完。

Lint + 安全
^^^^^^^^^^^

ruff 會自動抓掉大部分風格問題。專案執行 SonarQube / Codacy / pylint 的
預設規則(複雜度 ≤ 15、函式長度 ≤ 75 行、檔案 ≤ 1000 行、不要 magic
number、不要 bare ``except``\ 、不要 mutable default arg)。bandit 掃
安全相關 pattern(``pickle.load``\ 、沒有 SafeLoader 的 ``yaml.load``\ 、
拿 MD5 / SHA-1 做安全用途、``shell=True``\ 、純 HTTP 對外)。

----

疑難排解
--------

``error: refusing non-HTTPS request``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

某個來源外掛或測試把 HTTP client 指到 ``http://``\ URL。修 URL ——
專案不會繞過 HTTPS-only egress。

``error: could not classify identifier``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``--paper``\ 給的值沒被認出來是 arXiv ID、arXiv URL 或 DOI。可接受的形式:

* ``2401.08741``\ 、``2401.08741v2``\ 、``arXiv:2401.08741``
* ``https://arxiv.org/abs/2401.08741``\ (有沒有 ``v<N>``/ ``.pdf``\ 都行)
* ``cs.LG/0001001``\ (舊 arXiv)
* ``10.1234/example``\ 、``doi:10.1234/example``\ 、
  ``https://doi.org/10.1234/example``

``error: no source plugin available yet for doi identifiers``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

DOI 可以被解析但 resolver 還沒接上。等 Semantic Scholar / Crossref
外掛,或先用該論文的 arXiv 鏡像 ID。

``arXiv rate-limit hits``
^^^^^^^^^^^^^^^^^^^^^^^^^

內建 token bucket 已限制在 1/3s。如果還是被 429,可能是同時跑了多個
ThesisAgents process 對同一個 arXiv endpoint —— 統一走一個 process,
或調低 ``--max``\ 。

----

授權與致謝
----------

主程式採 **MIT-style**\ 授權;詳見 ``LICENSE``\ 。

arXiv API 的使用受 arXiv 的 `API 服務條款
<https://info.arxiv.org/help/api/tou.html>`_ 約束。內建 fetcher 已透過
token bucket 強制每 3 秒 1 次的軟限制 —— 新增 endpoint 時不要把這個
限速拿掉。
