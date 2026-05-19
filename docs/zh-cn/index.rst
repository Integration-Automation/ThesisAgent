AutoPaperToPPT 使用手册
========================

以关键词驱动的论文搜索助手。从 arXiv(以及可插拔的其他来源)抓取结果,
规范化为统一的 record,并把去重、排序后的结果集导出为 PowerPoint 幻灯片、
Markdown 摘要、BibTeX 文件、与 JSON 原始数据 —— 一次 CLI 调用或一次 MCP
工具调用即可完成。

.. contents:: 目录
   :depth: 2
   :local:

----

给驱动本项目的 AI agent 看
--------------------------

**如果你是 LLM(Claude Code、Cursor、Aider、Codex CLI …)正在读这份
指南想搞清楚要做什么 —— 从这节开始。** 同一套规则也钉在 repo 根目录
的 ``AGENTS.md``\ (跨 agent 镜像)与 ``CLAUDE.md``\ (权威来源),
做非小改动前请先读。

**交付物是每篇一份论文答辩级的富版 PPT,不是 CLI 默认出的只有摘要的
轻量版。** 轻量 emit 是中间产物 —— 你的工作就是把它升级。

决策树
^^^^^^

1. 环境有 ``ANTHROPIC_API_KEY`` 吗? → 直接跑 CLI,它会自动 enrich。
2. 没 key,但你(LLM)正在驱动 → **你自己手写 rich summary**。每篇
   PDF 自己读,手写 ``PaperSummary`` 含 rich-tier 字段,放
   ``scripts/regen_<query>.py``,跑它。不要叫用户去设 API key ——
   你就是那个会写 summary 的 LLM。
3. 没 LLM(CI / cron / 无人值守)→ 轻量版可以接受。

MCP 6 步流程
^^^^^^^^^^^^

.. code-block:: text

   1. (可选) list_sources()                              # 看哪些 plugin 已启用
   2. search(keywords, sources, top_tier_only=true, ...)
   3. (可选) download_pdfs(papers, out_dir="./exports/...")
   4. fetch_pdf_text(pdf_url=paper.pdf_url)              # 每篇都要
   5. (你逐篇读 PDF,自己产 structured summary dict)
   6. export(papers=[{..., "summary": {...}}], language="zh-cn", ...)

共 11 个 MCP 工具,完整参考见 :doc:`/mcp`。

必做:交付前验证 URL / DOI
^^^^^^^^^^^^^^^^^^^^^^^^^^

出版商的 URL 路径 **不能猜**\ 。AAAI 用数字 ID(``v40i5.37389``),
IEEE 用 opaque ``arnumber``,ACM 用 opaque DOI。手写 ``Paper`` 时,
``url`` / ``doi`` / ``arxiv_id`` 必须\ **逐字从同一次搜索产生的
xlsx 抄** —— 不能凭印象,也不能从标题自己拼。

xlsx 写在 ``exports/<run>/<slug>-<timestamp>.xlsx``\ ,第 7 列是 DOI、
第 8 列是 URL。Regen 跑完做这个 audit:

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

* 不要告诉用户「设 ``ANTHROPIC_API_KEY`` 才能拿到富版」—— 你就是那个 LLM。
* 不要把轻量 ``.pptx`` 当交付物。
* 不要看到 ``download_pdfs`` 报告「N 份 PDF 已存」就停。
* 不要编造论文里没有的数字、RQ、贡献、限制。
* 不要编造 URL / DOI / arXiv ID。
* 不要把不相关下载留在 run 目录里。关键词搜索会带到无关论文
  (例如「Claude code」抓到 Viterbi 解码器论文)。把无关论文的
  ``pdfs/<key>.pdf`` 与轻量 ``<key>.pptx`` 删掉,aggregate xlsx / bib
  保留作为「诚实记录」。完整流程见 ``CLAUDE.md`` 的「Pruning
  irrelevant downloads」。
* 不要在 commit message、PR description、代码注释或文档提到
  「Claude」、「Claude Code」、「AI-generated」、「GPT」、「Copilot」
  或任何 AI 工具 / 模型名称。

示例:\ ``scripts/regen_llm_security_batch.py``\ (en)与
``scripts/regen_llm_security_batch_zh_tw.py``\ (zh-tw)里有 8 篇照
这套流程手写的 rich summary,当 template 用。

----

安装
----

AutoPaperToPPT 锁定 Python **3.12+**\ (以 3.14 开发),支持 Windows、
macOS、Linux。建议使用项目内的 virtualenv:

.. code-block:: bash

   git clone <repo-url>
   cd AutoPaperToPPT
   python -m venv .venv
   .venv\Scripts\Activate.ps1            # Windows PowerShell
   # source .venv/bin/activate           # Linux / macOS

   pip install -e .[dev]

``dev``\ extra 会拉进 ``pytest``\ 、``pytest-asyncio``\ 、``pytest-httpx``\ 、
``ruff``\ 、``bandit``\ 与 ``mcp``\ SDK。如果只需要 MCP server,可以装更轻的
``[mcp]``\ 。

可选依赖组
^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Extra
     - 解锁什么
   * - ``[mcp]``
     - 只装 ``mcp``\ SDK。用于 production 安装 ——
       想要 ``autopapertoppt-mcp``\ 但不想要测试工具链时。
   * - ``[intelligence]``
     - ``pypdf``\ + ``anthropic``\ 。Python ``--enrich``\ 路径用
       (抓 PDF + 打 Anthropic API)。**MCP 上的 LLM-as-agent 流程
       不需要这个** —— LLM 自己就是 agent。
   * - ``[web]``
     - ``fastapi``\ + ``uvicorn``\ + ``streamlit``\ —— 预留给后续的网页 UI。
       CLI 与 MCP server 不需要这个。
   * - ``[dev]``
     - 完整开发工具链: pytest、asyncio + httpx 测试插件、ruff、bandit、
       MCP SDK 与 intelligence 依赖(让所有测试能跑)。

----

CLI
---

``python -m autopapertoppt``\ (也安装为 ``autopapertoppt``)是入口程序。
有两个互斥的模式:

搜索模式
^^^^^^^^

.. code-block:: bash

   # 默认 25 条结果,默认导出(pptx、xlsx、bib)
   autopapertoppt --query "diffusion models" --source arxiv

   # 10 条结果,全部导出格式,自定义目录
   autopapertoppt --query "transformer attention" --source arxiv \
                --max 10 --export pptx,xlsx,md,bib,json \
                --out ./exports/

   # 限制在近年论文
   autopapertoppt --query "graph neural networks drug discovery" \
                --year-from 2022 --year-to 2025 \
                --max 15 --out ./exports/

单篇论文模式
^^^^^^^^^^^^

.. code-block:: bash

   # arXiv ID —— 单篇默认只出 pptx + bib
   autopapertoppt --paper 1706.03762 --out ./exports/

   # arXiv URL
   autopapertoppt --paper "https://arxiv.org/abs/1706.03762" \
                --filename-stem attention --out ./exports/

   # DOI(通过 Semantic Scholar resolve)
   autopapertoppt --paper "10.1145/3411764.3445005" --out ./exports/

   # PubMed PMID / URL
   autopapertoppt --paper "https://pubmed.ncbi.nlm.nih.gov/34567890/" \
                --out ./exports/

   # IEEE document URL(需 opt-in env var)
   AUTOPAPERTOPPT_DISABLE_IEEE_SCRAPING=1 \
   autopapertoppt --paper "https://ieeexplore.ieee.org/document/10965643" \
                --out ./exports/

可用的 source plugin
^^^^^^^^^^^^^^^^^^^^

不传 ``--source`` 时的默认组合是「所有不需要 API key 的 plugin」:
``arxiv``、``semantic_scholar``、``openalex``、``pubmed``、``acm``、
``dblp``、``crossref``、``openaire``。设下面三个 env var 之一,对应
plugin 也会加入:

.. list-table::
   :header-rows: 1
   :widths: 18 30 52

   * - Plugin
     - Env var
     - 备注
   * - ``ieee``
     - ``AUTOPAPERTOPPT_IEEE_API_KEY``\ (建议)**或**\
       ``AUTOPAPERTOPPT_DISABLE_IEEE_SCRAPING=1``
     - 官方 Xplore API 在订阅范围内会带 ``pdf_url``;没 key 时可用
       fallback 爬取路径。
   * - ``springer``
     - ``AUTOPAPERTOPPT_SPRINGER_API_KEY``
     - 免费 key 申请 https://dev.springernature.com/。
       涵盖 Nature、Scientific Reports、LNCS 等 Springer 全系。
       没 key 时 plugin 会在构造时抛 ``ConfigError``,被 pipeline
       静默跳过。
   * - ``scholar``
     - ``AUTOPAPERTOPPT_DISABLE_SCHOLAR_SCRAPING=1``
     - Google Scholar ToS 禁止爬取,默认关闭。

搜索流水线默认套用「顶级期刊白名单」(旗舰级 CS 会议 + Nature / Science /
PNAS / CACM / LNCS);传 ``--all-venues`` 可关闭。

本地化 deck 与 LLM enrichment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # 把幻灯片模板字符串改成繁体中文
   autopapertoppt --paper 1706.03762 --lang zh-tw --out ./exports/

   # Python pipeline 走 enrichment(PDF + Anthropic API → thesis-style)
   export ANTHROPIC_API_KEY=sk-ant-...
   autopapertoppt --paper "https://arxiv.org/abs/1706.03762" \
                --enrich --lang zh-tw --out ./exports/

完整参数表: :doc:`/cli`。

----

输出文件
--------

每种导出会在 ``--out``\ 写一个文件。默认文件名为
``{关键词前 32 字}-{YYYYMMDD-HHMMSS}.{扩展名}``;用
``--filename-stem``\ 固定 stem。默认值依模式不同:

* ``--query`` → ``pptx`` + ``xlsx`` + ``bib``
* ``--paper`` → ``pptx`` + ``bib``\ (单篇出 Excel 是浪费)

.. code-block:: text

   exports/
   ├── attention.pptx     # 16:9 宽屏幻灯片(布局见下)
   ├── attention.xlsx     # Papers 工作表 + Query 出处工作表
   ├── attention.bib      # 不会撞 key,LaTeX 特殊字符已转义
   ├── attention.md       # 完整来源 / 标题 / 摘要列表(opt-in)
   └── attention.json     # 原始 payload(opt-in)

``.xlsx`` 的 Papers 工作表有两个外观相近但含义不同的相邻列:

* **Source**\ (第 5 列)—— 真实刊登出处,例如\ ``IEEE Access``\ 、
  ``NDSS 2026``\ 、``Nature Machine Intelligence``\ 。
* **Indexed via**\ (第 6 列)—— 是哪个 fetcher 抓到这条 metadata,
  例如\ ``openalex``\ 、``crossref``\ 、``arxiv``\ 。当同一篇论文可以
  从多条路径抓到时,这个分列很重要 —— 例如一篇 Nature 论文经 OpenAlex
  索引时,Source 显示\ ``Nature``\ ,Indexed via 显示\ ``openalex``\ 。

PPTX 布局
^^^^^^^^^

16:9 宽屏、带页码。三种 rendering tier 依数据多寡自动挑:

* **轻量**\ —— 只有 ``paper.abstract``\ 。封面 + agenda + 每篇
  (section divider + overview + 句子切片的 Background / Approach
  / Findings)+ references。
* **扁平结构化**\ —— ``Paper.summary``\ 的扁平 tier 有值
  (``motivation`` / ``contributions`` / ``method`` /
  ``results`` / ``limitations`` / ``takeaways``)。一张幻灯片
  对应一个非空 section。
* **thesis-style 答辩级**\ —— ``Paper.summary``\ 有 rich-tier 字段
  (``pain_points``\ 四宫格、研究问题 callout、``contributions_detailed``
  + ``headline_metrics``\ 、技术比较表、文献定位表、系统总览、
  方法细节、评估方法、研究问题、每个 RQ 结果表、贡献总结、
  核心观察、限制与未来工作、Q&A、参考文献)。每篇 20+ 张幻灯片。

所有模板字符串(议程 / 参考文献 / 第 N 篇 / 页脚)都走
``autopapertoppt.exporters.i18n``\ ,跟 ``--lang``\ 联动。支持的语言:
``en``\ (默认)、``zh-tw``\ 、``zh-cn``\ 、``ja``\ 、``es``\ 、
``fr``\ 、``de``\ 、``ko``\ 、``pt``\ 、``ru``\ 、``it``\ 、``vi``\ 、
``hi``\ 、``id``\ ,共 14 种。传其他值会静默 fallback 到 ``en``\ 。

每张幻灯片上的每个文本框都带有语义 ``name``\ (``title``\ 、
``meta``\ 、``body``\ 、``subhead``\ 、``footer``\ 、``page_number``\ 、
``kpi``\ 、``rq_box``),编辑工具可以靠 name 定位 shape,不必依赖视觉位置。
详见 :doc:`/pptx_editing`。

----

MCP server
----------

AutoPaperToPPT 附带一个暴露 **11 个工具** 的 MCP server —— 来源发现
(``list_sources``)、搜索、单篇抓取、单个 PDF 正文提取
(``fetch_pdf_text``)、批量 PDF 下载(``download_pdfs``)、导出,
以及 5 个 PPTX 编辑操作。任何支持 MCP 的 LLM client(Claude Code、
Claude Desktop、Cursor …)都能驱动整套流程。

配置 MCP client(以 Claude Code 为例):

.. code-block:: powershell

   claude mcp add autopapertoppt -- ".venv\Scripts\python.exe" -m autopapertoppt.mcp

或直接编辑 settings 文件:

.. code-block:: json

   {
     "mcpServers": {
       "autopapertoppt": {
         "command": ".venv\\Scripts\\python.exe",
         "args": ["-m", "autopapertoppt.mcp"]
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
     - 列出所有 plugin + 报告当前 process 下哪些已启用。``search``
       前先调一次,agent 才知道要传什么 ``sources``。
   * - ``search``
     - 关键词 → 论文列表(shape 同 ``Paper.to_dict()``)。可带
       ``top_tier_only``\ (默认 ``True``\ )与 ``min_citations``\ ;
       省略 ``sources`` 时默认扫所有不需要 API key 的来源。
   * - ``fetch_paper``
     - arXiv / DOI / PMID / IEEE 标识符 → 单篇论文。
   * - ``fetch_pdf_text``
     - 抓单个 PDF 并返回提取的正文。**MCP 路径下「让我读过论文」的入口。**
   * - ``download_pdfs``
     - 把一组论文的 PDF 批量下载到 ``{out_dir}/pdfs/``\ 。返回以
       BibTeX key 为索引的逐篇结果。
   * - ``export``
     - 论文列表 + 格式 → 写出 ``.pptx/.xlsx/.md/.bib/.json``\ 。每篇
       论文可附 ``summary``\ 字段走 thesis-style;支持 ``language``\
       走 i18n,以及 ``max_slides_per_paper``\ (默认 25;传 ``0``\
       代表不限)。
   * - ``pptx_inspect``
     - 读已有幻灯片文件的 slide / shape 结构。
   * - ``pptx_update_slide``
     - 替换 ``title``/ ``body``/ ``meta``\ (通过 shape name)或
       任意 shape(通过 index)。
   * - ``pptx_delete_slide``
     - 删除一张 slide 及其 part relationship。
   * - ``pptx_reorder_slides``
     - 通过 ``sldIdLst``\ 重排幻灯片。
   * - ``pptx_add_slide``
     - 在末尾追加或在指定 position 插入一张新的 title /
       body / meta slide。

LLM-as-agent enrichment 流程(不需要 Anthropic API key):

1. (可选)\ ``list_sources()``\ 看当前 process 下哪些 plugin 已启用。
2. ``search(keywords, sources, top_tier_only, ...)``\ 多篇,或
   ``fetch_paper(identifier)``\ 抓单篇。
3. (可选)\ ``download_pdfs(papers, out_dir)``\ 把每篇 PDF 批量存到
   本地。
4. ``fetch_pdf_text(paper.pdf_url)``\ 逐篇拿正文。
5. LLM 在自己 context 里读正文,产 structured ``summary``\ dict。
6. ``export(papers=[{..., "summary": {...}}], language="zh-tw", ...)``\ 。

完整参考: :doc:`/mcp`。

----

编辑生成好的幻灯片
------------------

幻灯片生成后,``pptx_*``\ 工具(或 ``autopapertoppt.exporters.pptx_edit``
Python 模块)让你在不重跑搜索的情况下继续对它做迭代:

.. code-block:: python

   from autopapertoppt.exporters import pptx_edit

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

每个 helper 默认原地存盘;传 ``out_path=...``\ 可以另存,原文件不动。
完整参考: :doc:`/pptx_editing`。

----

架构
----

::

   AutoPaperToPPT/
   ├── autopapertoppt/                 # 主包
   │   ├── core/                     # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
   │   ├── fetchers/                 # HTTPS-only http client、token bucket、Fetcher base
   │   ├── exporters/                # pptx(thesis-style + lightweight)、xlsx、
   │   │                             #   bibtex、markdown、json + pptx_edit + i18n
   │   ├── intelligence/             # PDF 抓取 + Anthropic 摘要器([intelligence] extra)
   │   ├── mcp/                      # 注册 11 个工具的 FastMCP server
   │   ├── utils/                    # logging、path safety
   │   ├── cli.py                    # argparse CLI
   │   └── __main__.py               # `python -m autopapertoppt`
   ├── sources/                      # 各来源 plugin(arxiv、semantic_scholar、
   │                                 #   openalex、pubmed、acm、ieee、scholar、
   │                                 #   dblp、crossref、openaire、springer)
   ├── tests/                        # pytest suite + 录制 fixture,不打活 HTTP
   ├── docs/                         # 这份 Sphinx 文档(en + zh-tw + zh-cn)
   ├── scripts/                      # 一次性 regen / fixture-record 脚本
   └── pyproject.toml                # metadata + ruff / bandit + optional extras

核心 vs 来源插件
^^^^^^^^^^^^^^^^

``autopapertoppt/``\ (核心)与 ``sources/<name>/``\ (插件)的分界线是
**依赖负担与失败隔离**,不是"跟来源有关的东西全丢插件":

* **核心**\ 跑在默认依赖集
  (``httpx``\ 、``pydantic``\ 、``defusedxml``\ 、``python-pptx``\ 、
  ``openpyxl``\ 、``bibtexparser``\ 、``beautifulsoup4``\ 、``lxml``\ 、
  ``markdown-it-py``),覆盖所有用户都应默认可用的流程。
* **插件**\ 是任何需要重 / 可选 runtime 依赖(``selenium``\ 处理 Scholar
  的 JS 页面、IEEE / ACM 厂商 SDK …)或独立发版节奏的东西。

两条 enrichment 路径
^^^^^^^^^^^^^^^^^^^^

* **LLM-as-agent(不需要 API key)**\ —— 由 MCP-aware 的 LLM 驱动。
  ``fetch_paper``\ + ``fetch_pdf_text``\ 给它 metadata + 正文;LLM 在自己
  context 里产 structured ``summary``\ ;``export``\ 写出文件。
* **Python pipeline(``--enrich``\ )** —— 给没有 LLM 在外面的自动化用。
  需要 ``ANTHROPIC_API_KEY``\ 与 ``[intelligence]``\ extra,默认模型
  ``claude-opus-4-7``\ ,可用 ``--llm-model``\ 或
  ``AUTOPAPERTOPPT_LLM_MODEL``\ 覆盖。

网络安全
^^^^^^^^

所有对外的 HTTP 都走 ``autopapertoppt.fetchers.http.get_client(source)``,
返回一个用 HTTPS-only transport 包起来的 per-source ``httpx.AsyncClient``\ 。
纯 HTTP 请求一律被拒(包括 redirect 后变 HTTP)。每个来源声明自己的
``RateLimit``\ 策略,由 token bucket 强制执行;arXiv 默认为
**每 3 秒 1 次、抖动 0.5s**,对应它的官方软限制。

----

开发流程
--------

Definition of Done
^^^^^^^^^^^^^^^^^^

每次变更都要过三道闸才能 commit(见 ``CLAUDE.md``):

.. code-block:: bash

   .venv\Scripts\python.exe -m pytest tests/
   .venv\Scripts\python.exe -m ruff check .
   .venv\Scripts\python.exe -m bandit -c pyproject.toml -r autopapertoppt/ sources/

bandit 的 ``-c``\ 标志是 **必需的**\ —— 没它 bandit 不会读项目 skip 配置,
跑出来会充满假警报。

测试
^^^^

测试结构镜像 production: 每个 production 模块
``autopapertoppt/<area>/<feature>.py``\ 都有一个对应的
``tests/test_<feature>.py``\ 。来源插件测试在 ``tests/sources/<name>/``\ 。

测试是 **hermetic**\ —— 每个 fetcher 测试都通过 monkeypatched HTTP
transport 载入录制好的 fixture。录新的 fixture 是独立的手动步骤
(``scripts/record_fixture.py``),录完的文件要 commit 进去。

跑整个 suite:

.. code-block:: bash

   .venv\Scripts\python.exe -m pytest tests/

目前 89 个测试,约 2 秒跑完。

Lint + 安全
^^^^^^^^^^^

ruff 会自动抓掉大部分风格问题。项目执行 SonarQube / Codacy / pylint 的
默认规则(复杂度 ≤ 15、函数长度 ≤ 75 行、文件 ≤ 1000 行、不要 magic
number、不要 bare ``except``\ 、不要 mutable default arg)。bandit 扫
安全相关 pattern(``pickle.load``\ 、没有 SafeLoader 的 ``yaml.load``\ 、
拿 MD5 / SHA-1 做安全用途、``shell=True``\ 、纯 HTTP 对外)。

----

故障排查
--------

``error: refusing non-HTTPS request``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

某个来源插件或测试把 HTTP client 指到 ``http://``\ URL。修 URL ——
项目不会绕过 HTTPS-only egress。

``error: could not classify identifier``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``--paper``\ 给的值没被识别为 arXiv ID、arXiv URL 或 DOI。可接受的形式:

* ``2401.08741``\ 、``2401.08741v2``\ 、``arXiv:2401.08741``
* ``https://arxiv.org/abs/2401.08741``\ (带不带 ``v<N>``/ ``.pdf``\ 都行)
* ``cs.LG/0001001``\ (旧 arXiv)
* ``10.1234/example``\ 、``doi:10.1234/example``\ 、
  ``https://doi.org/10.1234/example``

``error: no source plugin available yet for doi identifiers``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

DOI 能被解析但 resolver 还没接上。等 Semantic Scholar / Crossref
插件,或先用该论文的 arXiv 镜像 ID。

``arXiv rate-limit hits``
^^^^^^^^^^^^^^^^^^^^^^^^^

内置 token bucket 已限制在 1/3s。如果还是被 429,可能是同时跑了多个
AutoPaperToPPT process 对同一个 arXiv endpoint —— 统一走一个 process,
或调低 ``--max``\ 。

----

授权与致谢
----------

主程序采 **MIT-style**\ 授权;详见 ``LICENSE``\ 。

arXiv API 的使用受 arXiv 的 `API 服务条款
<https://info.arxiv.org/help/api/tou.html>`_ 约束。内置 fetcher 已通过
token bucket 强制每 3 秒 1 次的软限制 —— 新增 endpoint 时不要把这个
限速拿掉。
