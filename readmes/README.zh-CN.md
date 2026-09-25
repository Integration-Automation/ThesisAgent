# ThesisAgents

[![CI](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![Python](https://img.shields.io/pypi/pyversions/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/ThesisAgents.svg)](https://github.com/Integration-Automation/ThesisAgents/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/thesisagents/badge/?version=latest)](https://thesisagents.readthedocs.io/en/latest/)

> **语言**: [English](../README.md) · [繁體中文](README.zh-TW.md) · **简体中文** · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **文档**: [thesisagents.readthedocs.io](https://thesisagents.readthedocs.io/en/latest/)

以关键字驱动的论文搜索助手,从 arXiv、Semantic Scholar、OpenAlex、
PubMed、ACM(经 Crossref)、IEEE Xplore、DBLP、通用 Crossref、
OpenAIRE、Springer Nature、Europe PMC、DOAJ、HAL、CORE 与 Google Scholar
抓取结果,把它们规范化成单一 record 形状,并将去重后的结果集导出为
**论文答辩级的 PowerPoint 幻灯片**、**Excel 工作簿**与
**BibTeX 文件** —— 全部只需一次 CLI 调用或一次 MCP 工具调用即可完成。可选择性地
让系统读取每篇论文的 PDF、生成每篇的结构化摘要,方式可以是就地(LLM-as-agent
路径)或经由 Anthropic API(Python pipeline 路径)。

## 给驱动本项目的 AI agent 看

**如果你是一个 LLM(Claude Code、Cursor、Aider、Codex CLI …)正在读这份
README 想搞清楚要做什么 —— 从这里开始。** 下面的所有内容也都钉在
[`AGENTS.md`](../AGENTS.md)(跨 agent 镜像)与 [`CLAUDE.md`](../CLAUDE.md)
(权威参考)里;做非小改动之前请先读那两份。

### 用户真正想要的

默认交付物是**每篇论文一份论文答辩级的丰富 `.pptx`**,而不是 CLI 默认
产出的那种只有摘要的轻量幻灯片。轻量产出只是一个中间产物 —— 你的
工作就是把它升级。

### 决策树

1. 环境里有设 `ANTHROPIC_API_KEY` 吗? → 直接跑 CLI 就好;它会经由
   Anthropic API 自动增强。你完成了。
2. 没有密钥,但你(一个 LLM)正在驱动这个 session → **你自己产出丰富
   摘要**。读每一份 PDF,亲手撰写一份带有丰富层字段的 `PaperSummary`
   (`pain_points`、`research_question`、`contributions_detailed`、
   `headline_metrics`、`technique_table`、`method_sections`、
   `evaluation_sections`、`system_flow`、`research_questions`、
   `rq_results`、`core_observation`、`limitations`、`future_work`),
   放一个 `scripts/regen_<query>.py`,运行它。**不要叫用户去设置 API
   密钥** —— 你就是那个本来会写出摘要的 LLM。
3. 循环里没有 LLM(CI / cron / 无人值守)→ 轻量版可以接受。

### 6 步 MCP 工作流程

```
1. (optional) list_sources()                              # see which plugins are enabled
2. search(keywords, sources, top_tier_only=true, ...)
3. (optional) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # per paper
5. (you read each PDF and produce a structured summary dict)
6. export(papers=[{...paper, "summary": {...}}], language="zh-tw", ...)
```

全部十三个 MCP 工具(包含 `list_sources`、`list_exports`、
`download_pdfs`、`pptx_inspect` / `pptx_review` / `pptx_update_slide` /
`pptx_add_slide` / 等等)都记载于 [`docs/mcp.md`](../docs/mcp.md)。

### 必办:发货前先验证 URL / DOI

出版商的 URL 路径**猜不出来** —— AAAI 用数字 ID
(`v40i5.37389`)、IEEE 用一组不透明的 `arnumber`、ACM 用不透明的 DOI。
当你亲手撰写一个 `Paper` 时,**要从生成这次运行的那份搜索 xlsx 逐字
复制 `url` / `doi` / `arxiv_id`** —— 绝不要凭记忆,也绝不要从标题拼出来。

那份 xlsx 会写到 `exports/<run>/<slug>-<timestamp>.xlsx`,第 7 列是
DOI、第 8 列是 URL。完成时审核你的 regen 脚本:

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

在生产环境里用这个方法抓到过两起捏造:错误的 AAAI 卷号
(`v39i23.34521` vs 真实 `v39i22.34537`),以及发明出来的作者 slug 路径
(`view/fang2026` 而非 `v40i5.37389`)。

### 必办:发货前先剔除不相关的下载

搜索是以关键字匹配的,所以离题论文一定会混进来:一次「Claude code」
查询带回了一篇 Viterbi 解码器论文,因为两者都含有「code」;
「LLM code review」匹配到一篇目标检测的文献综述。一旦你读了摘要、
判定某篇论文对用户的真正意图离题,就从运行目录剔除它:

```python
from pathlib import Path
run = Path("exports/<run>")
irrelevant_keys = ("key-of-off-topic-paper-1", "key-of-off-topic-paper-2")
for key in irrelevant_keys:
    for path in (run / "pdfs" / f"{key}.pdf", run / f"{key}.pptx"):
        if path.exists():
            path.unlink()
```

删掉 `exports/<run>/pdfs/<key>.pdf` 与 `exports/<run>/<key>.pptx`。
**保留**汇总的 `<slug>-<timestamp>.xlsx` / `.bib` —— 那些是搜索实际
返回了什么的诚实记录。边界情况就给它一份丰富摘要;宁可多收也不要
默默漏掉一个可能的匹配。

### 实作范例

[`scripts/regen_fang2026.py`](../scripts/regen_fang2026.py) 附了一份正是
以这种方式亲手撰写的丰富摘要(单篇论文、丰富层、zh-tw、每个丰富字段
都填满)。多篇论文的搜索遵循同样的形状,在 `PaperCollection` tuple
里每篇论文一个 `Paper(...summary=PaperSummary(...))` 条目。

### 不要做的事

- **不要**在多篇论文搜索结束时告诉用户「设 `ANTHROPIC_API_KEY` 就能
  得到丰富幻灯片」—— 你就是那个本来能写出摘要的 LLM。
- **不要**把每篇论文的轻量 `.pptx` 当成交付物。
- **不要**在 `download_pdfs` 报告存了 N 份 PDF 后就停手 —— 那是丰富
  撰写阶段的开始,不是结束。
- **不要**发明论文里没有的数字、RQ、贡献或限制。
- **不要**捏造 URL / DOI / arXiv ID —— 见上面的规则。
- **不要**把不相关下载留在运行目录里。关键字搜索的匹配可能包含离题
  论文(一次「Claude code」查询拉进了一篇 Viterbi 解码器论文;
  「LLM code review」拉进了一篇目标检测文献综述)。判定论文离题后,
  删掉它们的 `pdfs/<key>.pdf` 与轻量 `<key>.pptx`;保留汇总 xlsx / bib
  作为搜索实际返回内容的诚实记录。
- **不要**在 commit 消息、PR 描述、代码注释或文档里提到「Claude」、
  「Claude Code」、「AI-generated」、「GPT」、「Copilot」或任何 AI 工具 /
  模型名称。

## 功能特性

- **十五个可插拔来源**:`arxiv`、`semantic_scholar`、`openalex`、
  `pubmed`、`acm`(Crossref 范围化)、`dblp`、`crossref`(未范围化)、
  `openaire`、`springer`(需要 API 密钥)、`europepmc`(开放、免密钥 ——
  生命科学 + preprint + 农业)、`doaj`(开放、免密钥 —— 开放获取期刊,
  通常带直接 PDF 链接)、`hal`(开放、免密钥 —— 法国的计算机 / 数学 /
  物理典藏,附全文 PDF)、`core`(需要免费 API 密钥 —— 最大的开放获取
  聚合站,2.5 亿+ 件作品)、`ieee`(经可见 Chrome 默认开启;API 密钥
  会加上官方 Xplore API)、`scholar`(经可见 Chrome 默认开启)。每个
  都住在 `sources/<name>/` 里、藏在一个 `Fetcher` 适配器后面。传
  `--top-tier-only` 可把结果筛选到旗舰级计算机会议 / 期刊外加
  Nature/Science/PNAS。默认搜索保留所有发表场所。
- **单篇论文模式**:粘贴一个 arXiv ID、arXiv URL、DOI、PMID 或 IEEE
  文档 URL —— ThesisAgents 会经由对应来源解析它,并输出同一套导出组合。
  对论文阅读笔记与论文答辩准备很有用。
- **本地 PDF 模式**(`--pdf <path>`):传入一份 PDF 或一个目录。一个
  启发式提取器会直接从每份 PDF 的前置页抽出**标题、作者、年份、
  arXiv ID、DOI 与真正的摘要**(锚定在明确的 `Abstract` / `ABSTRACT` /
  `摘要` 标头上,而非盲目截取前缀)。单一 PDF 调用时 `--title` /
  `--authors` / `--year` / `--venue` / `--doi` / `--arxiv-id` 会覆盖;
  对一个目录则以每文件提取为准,让每篇论文都得到一份以其 BibTeX 键命名的
  幻灯片。
- **八个导出器**:
  - `.pptx` —— 16:9 宽屏、有页码、三种渲染层级(只有摘要的轻量 ·
    增强扁平 · **论文答辩级**,附痛点四象限、KPI 标注、技术比较表、
    每个 RQ 的结果表、贡献摘要、核心观察、限制与未来工作、Q&A、参考
    文献)。所有模板字符串都跨 **14 种语言**做了 i18n:English、繁體中文、
    简体中文、日本語、Español、Français、Deutsch、한국어、Português、
    Русский、Italiano、Tiếng Việt、हिन्दी、Bahasa Indonesia。
  - **设计过的幻灯片视觉标识**(不是默认的 Calibri-on-white 样貌):
    按语言的字体(拉丁文用 Inter,CJK + 印地文用 Microsoft JhengHei
    UI / YaHei UI / Yu Gothic UI / Malgun Gothic / Nirmala UI)、
    程序化的装饰几何(每张内容页顶端一条装饰条 + 封面左侧色带)、
    学术风格的表格排版(去掉默认网格、深蓝表头横线、柔和的行间分隔、
    交替行底纹、垂直居中对齐、粗体行标签),以及五色调色板纪律
    (深蓝 / 蓝绿 / 灰 / 浅 / 白),文字**禁用**红色(改用粗体 + 蓝绿
    `#0E7490` 来强调)。
  - **浅色模式是默认的渲染路径。** 传 `--dark-mode`、在 GUI Deck 选项卡
    启用 **Dark mode**,或设 `ExportOptions(dark_mode=True)`,即可套用
    深色后处理(幻灯片背景 `#12151B`、正文 `#E5E7EB`)。
  - `.xlsx` —— Papers 工作表 + Query 出处工作表、超链接的 URL / PDF、
    冻结表头、自动列宽。第 5 列(**Source**)显示真正的发表场所
    (例如「IEEE Access」);第 6 列(**Indexed via**)显示是哪个
    fetcher 返回了元数据(例如「openalex」),所以这两项信息绝不
    相撞。
  - `.md` —— 完整的来源 / 标题 / 摘要清单。
  - `.bib` —— 无碰撞的引用键、经 LaTeX 转义的字段。
  - `.json` —— 给下游工具用的原始 payload。
  - `.ris` —— 由 Zotero / Mendeley / EndNote / RefWorks 导入的 RIS
    交换格式(给非 LaTeX 文献管理器用的 BibTeX 手足)。
  - `.csv` —— 给电子表格 / 快速 grep 分类用的每篇论文一行的扁平表格
    (RFC-4180 引号规则,所以标题里的逗号绝不会错位列)。
  - `.csl.json` —— 给 Pandoc / citeproc 用的 CSL-JSON;可以用任何 CSL
    样式(APA、IEEE、Nature …)渲染参考文献。`.csl.json` 扩展名让它跟
    纯 `.json` dump 有所区别。
- **PPT 编辑工具组**:`thesisagents.exporters.pptx_edit`
  (inspect / update_slide / delete_slide / reorder_slides / add_slide)
  可对导出器产出的任何幻灯片运作,加上对应的 `pptx_*` MCP 工具,好让
  一个 LLM agent 能在产出的幻灯片上反复迭代。
- **MCP 服务器**:13 个工具 —— `list_sources` + `list_exports`
  (发现)、`search`、`fetch_paper`、`fetch_pdf_text`、`download_pdfs`、
  `export`,以及六个 `pptx_*` 幻灯片工具(`inspect`、`review`、
  `update_slide`、`delete_slide`、`reorder_slides`、`add_slide`)。让任何
  懂 MCP 的 LLM(Claude Code、Claude Desktop、Cursor …)驱动整个工作
  流程。
- **两条增强路径**,用来超越摘要、进入真正的论文答辩级幻灯片:
  - **LLM-as-agent(免 API 密钥)** —— 调用端 LLM 经由
    `fetch_pdf_text` 读 PDF 正文,就地写出一份结构化摘要,再传给
    `export`。
  - **Python pipeline(`--enrich`)** —— CLI 自己调用 Anthropic 的 API;
    默认模型 `claude-opus-4-7`。
- **可见 Chrome 的出版商流程**:Scholar SERP、IEEE `/rest/search`,以及
  每一次付费墙 PDF 下载(ieeexplore / dl.acm / link.springer /
  sciencedirect / wiley / oup / nature / science / …)都在一个真实可见的
  Chrome session 里经由 `selenium` 运行。用户在那个实时窗口里解一次
  captcha / 完成 SSO;`THESISAGENTS_CHROME_PROFILE_DIR` 会跨运行保存
  cookie。
- **LLM-as-agent 流程**:MCP 工具提供搜索、PDF 下载与文本提取。
  `scripts/regen_*.py` 内含可复现的范例,示范如何为每篇论文亲手撰写
  一份丰富的 `PaperSummary`。
- **OA PDF 解析器**:去重之后,每篇没有 `pdf_url` 的论文都会走
  Unpaywall → S2 `openAccessPdf` → arXiv 标题搜索 → CORE.ac.uk(在有设
  密钥时)。在 IEEE / ACM / Springer / Elsevier 为主的查询上典型的
  提升:40-70 个百分点。
- **默认就安全**:仅 HTTPS 的 HTTP 传输、每来源速率限制(token bucket)、
  对任何 XML payload 用 `defusedxml`、防路径穿越的导出路径、不对
  用户输入用 `eval` / `exec` / `pickle`。
- **zh-tw / zh-cn 词汇卫士**:`tests/test_i18n.py::test_zh_tw_files_use_traditional_chinese_vocabulary`
  里约 244 条正则表达式会抓出用繁体汉字写成的简体中文外来词
  (例如 `內存` → `記憶體`、`魯棒性` → `穩健性`、`軟件` → `軟體`、
  `緩存` → `快取`)。同一套卫士也反向地跑在 zh-cn 语系字符串上。完整规则
  与正则表达式目录住在
  `.claude/agents/rules/language-vocabulary-check.md`。

## 快速开始

```powershell
git clone <repo-url>
cd ThesisAgents
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Install with dev extras (also pulls in MCP SDK and intelligence deps)
pip install -e .[dev]
```

搜索 arXiv 并导出幻灯片 + 工作簿 + BibTeX(`--query` 的默认):

```powershell
py -m thesisagents --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

用 URL 抓单篇论文 —— 默认是 `.pptx + .bib`(对只有一行的数据,`.xlsx`
比较没意义):

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

用繁体中文渲染幻灯片:

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --lang zh-tw --out .\exports\
```

LLM-pipeline 增强(Python 自己调用 Anthropic —— 需要 API 密钥):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang zh-tw --out .\exports\
```

## CLI 标志

| 标志 | 用途 |
|---|---|
| `--query` / `-q` | 关键字(除非用 `--paper`,否则必填)。 |
| `--paper` / `-p` | arXiv ID / URL、DOI、PMID 或 IEEE 文档 URL。与 `--query` 互斥。 |
| `--source` / `-s` | 逗号分隔的来源清单。默认 `arxiv`。 |
| `--max` / `-n` | 每来源最多结果数(1..200)。默认 25。 |
| `--year-from` / `--year-to` | 含边界的年份筛选。 |
| `--export` / `-e` | 格式:`pptx,xlsx,md,bib,json,ris,csv,csl` 之任意组合。默认依模式而定(见下)。 |
| `--out` / `-o` | 输出目录。默认 `./exports`。 |
| `--filename-stem` | 覆盖生成的文件名主干。 |
| `--no-abstract` | 从导出中省略摘要内容。 |
| `--lang` / `-l` | 幻灯片语言:14 种之一 —— `en`、`zh-tw`、`zh-cn`、`ja`、`es`、`fr`、`de`、`ko`、`pt`、`ru`、`it`、`vi`、`hi`、`id`。默认 `en`。 |
| `--enrich` | 自动增强的失败即报变体。需要 `ANTHROPIC_API_KEY` 与 `[intelligence]` extra。(设了密钥时自动增强是默认。) |
| `--lightweight` | 跳过增强 + 强制只有摘要的幻灯片。只用于快速 / 无人值守的运行;**当有 LLM agent 在驱动时,优先用下面的 LLM-as-agent 流程**。 |
| `--llm-model` | 覆盖增强用的默认 `claude-opus-4-7`。 |
| `--no-pdf` | 跳过自动 PDF 下载。也会禁用每篇论文的 PPT 闸(没 PDF → 没完整内容)。 |
| `--no-oa-resolve` | 跳过去重后的 OA PDF 解析器(Unpaywall + S2 + arXiv + CORE.ac.uk)。 |
| `--top-tier-only` | 把结果限制到 arXiv + 一份精选的计算机旗舰白名单(S&P、CCS、NDSS、USENIX Security、NeurIPS、ICML、ICSE …)。默认关闭。 |
| `--paywall-threshold` | 触发确认提示的付费墙结果比例。默认 0.30。 |
| `--yes` | 跳过付费墙提示直接进行。 |
| `--max-slides` | 每篇论文的幻灯片上限(默认 25;传 0 表示无上限)。 |
| `--dark-mode` | 以深色背景 + 近白文本渲染 pptx。默认是浅色深蓝带幻灯片。 |
| `--quiet` | 抑制每篇论文的打印输出。 |

### 环境变量

| 变量 | 使用者 | 用途 |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | LLM 认证。走 MCP 的 LLM-as-agent 路径不需要。 |
| `THESISAGENTS_LLM_MODEL` | `--enrich` | 覆盖默认的 `claude-opus-4-7`。 |
| `THESISAGENTS_S2_API_KEY` | Semantic Scholar + OA 解析器 | 更高的速率限制;也被 OA 解析器的 S2 `openAccessPdf` 步骤使用。免费密钥在 <https://www.semanticscholar.org/product/api>。 |
| `THESISAGENTS_NCBI_API_KEY` | PubMed | 把 NCBI 的匿名限制(3/s)提高到 10/s。可选。 |
| `THESISAGENTS_CONTACT_EMAIL` | PubMed、ACM、Crossref、OpenAlex、**Unpaywall** | 礼貌池标记 + 启用 OA 解析器的 Unpaywall 步骤(对 IEEE / ACM / Springer / Elsevier 付费墙论文的 PDF 覆盖率提升最大;典型提升 40-70 pp)。 |
| `THESISAGENTS_IEEE_API_KEY` | IEEE(API 路径) | 官方 IEEE Xplore API;为范围内论文带出 `pdf_url`。 |
| `THESISAGENTS_DISABLE_IEEE_SCRAPING` | IEEE | **IEEE 经可见 Chrome 默认开启。** 设 `=1` 可退出(例如没有 Chrome 的 CI)。httpx 抓取分支只在 WebRunner 不可用时作为后备运行。 |
| `THESISAGENTS_CROSSREF_PLUS_TOKEN` | ACM、Crossref | Crossref Plus 订阅者 token(Bearer 标头)。可选。 |
| `THESISAGENTS_SPRINGER_API_KEY` | Springer | 必填;免费密钥来自 <https://dev.springernature.com/>。没有它插件会抛 `ConfigError`。 |
| `THESISAGENTS_DISABLE_SCHOLAR_SCRAPING` | Google Scholar | **Scholar 经可见 Chrome 默认开启。** 设 `=1` 可退出(Google 的 ToS 禁止自动化访问 —— 为覆盖率而默认开启,退出以避免 captcha / IP 封锁风险)。 |
| `THESISAGENTS_CHROME_PROFILE_DIR` | Scholar + IEEE + 付费墙 PDF 下载 | 持久的 Chrome `--user-data-dir`。设好它并完成一次 VPN / SSO / Google 登录;后续运行会继承 cookie,让 IEEE 返回付费墙元数据、Scholar 提供不被限流的 SERP。 |
| `THESISAGENTS_DISABLE_WEBRUNNER` | Scholar + IEEE + 付费墙 PDF 下载 | `=1` 强制走 httpx 路径而非驱动真实 Chrome。对没有 Chrome 二进制文件的 CI / Docker 有用;否则请保持不设。 |
| `THESISAGENTS_CORE_API_KEY` | OA 解析器 + `core` 搜索来源 | 免费密钥来自 <https://core.ac.uk/services/api>。启用 CORE.ac.uk 的 OA 查找步骤(2 亿+ 机构 / 区域 OA 项目)**以及** `core` 搜索来源。没有它,`core` 来源会被默默跳过,其他 OA 策略(Unpaywall、S2、arXiv)仍会运行。 |
| `THESISAGENTS_PDF_COOKIES_FILE` | PDF 下载器 | Netscape `cookies.txt`。默认关闭。只对你有机构权利的出版商使用。 |
| `THESISAGENTS_LOG_LEVEL` | logger | 默认 `INFO`;`DEBUG` 用于冗长追踪。 |

默认:`--query` → `pptx,xlsx,bib`。`--paper` → `pptx,bib`。永远可用明确的
`--export` 覆盖。

## LLM-as-agent 流程

当你编辑器里的 LLM 在驱动这个工作流程时,依序使用 MCP 工具:
`search`、`download_pdfs`、`fetch_pdf_text`,然后用一份亲手撰写的丰富
`PaperSummary` 调用 `export`。既有的 `scripts/regen_*.py` 文件就是最终
撰写与导出步骤的可复现范例。

完整的端到端运行手册(搜索 → 丰富幻灯片)住在
`.claude/agents/tasks/paper-summary-author.md` —— 开一个新查询前先打开它,
好让 LLM 能运行整个流程而不必停下来等用户输入。

## MCP 服务器

向 Claude Code 注册:

```powershell
claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp
```

或写进你的设置文件:

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

工具:

| 工具 | 用途 |
|---|---|
| `list_sources` | 列举每个插件 + 报告各自在当前环境下是否启用。在 `search` 前调用一次。 |
| `list_exports` | 列举每种导出格式,附一行描述,并说明它写一个汇总文件还是每篇论文一文件。 |
| `search` | 关键字 → 论文清单。接受 `top_tier_only`、`min_citations`;默认走完整的免 API 密钥来源组合。 |
| `fetch_paper` | arXiv / DOI / PMID / IEEE 标识符 → 单篇论文。 |
| `fetch_pdf_text` | 下载一份 PDF,返回提取出的正文文本。**这是「我读了论文」的 MCP 路径。** |
| `download_pdfs` | 批量把一份论文清单的 PDF 下载到 `{out_dir}/pdfs/`。返回以 BibTeX 键为索引的每篇论文结果。 |
| `export` | 论文清单 + 格式 → 写出 `.pptx/.xlsx/.md/.bib/.json/.ris/.csv/.csl.json`。每篇论文可接受一个 `summary` 字段,用于丰富论文答辩级 schema、`max_slides_per_paper`(默认 25)与 `dark_mode`(默认 `false` —— 项目默认是浅色深蓝带幻灯片,传 `true` 走深色 OLED / 低光后处理)。 |
| `pptx_inspect` | 读取既有幻灯片的 slide / shape 结构。 |
| `pptx_review` | 一次调用审核一份幻灯片 —— 溢出 + 颜色契约 + `paper_rule` 章节完整度。自动检测幻灯片语言;也是 CLI `python -m thesisagents review <deck.pptx>`。 |
| `pptx_update_slide` | 替换 `title` / `body` / `meta`(按 shape 名称)或按索引替换任意 shape。 |
| `pptx_delete_slide` | 移除一张幻灯片与它的 part 关系。 |
| `pptx_reorder_slides` | 经由 `sldIdLst` 重排幻灯片。 |
| `pptx_add_slide` | 追加或插入一张新的 title / body / meta 幻灯片。 |

LLM-as-agent 流程(不需要 `ANTHROPIC_API_KEY` —— LLM 就是那个 agent):

```
1. (optional) list_sources()                       # discover enabled plugins
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (optional) download_pdfs(papers, out_dir="./exports/...")  # persist PDFs
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # per paper
5. (the LLM reads body text, produces a structured `summary` dict)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="zh-tw", formats=["pptx","bib"], dark_mode=true, ...)
```

完整参考在 [`docs/mcp.md`](../docs/mcp.md)。

## 项目结构

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

## 完成定义(Definition of Done)

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r thesisagents/
```

bandit 上的 `-c` 标志是必要的 —— 没有它 bandit 会忽略项目的 skip 配置。
碰到 pptx 导出器时,也要跑一次溢出检查(见 `CLAUDE.md`「Slide Deck
Rules」)。

## 桌面 GUI(PySide6)

一个原生桌面界面藏在 `[gui]` extra 后面发货:

```powershell
pip install thesisagents[gui]
thesisagents-gui                 # or: thesisagents gui
```

窗口有四个选项卡 —— **Search**、**Settings**(经由 QSettings 保存 API
密钥)、**Enrich**(经由一个 `collection_ready` 信号驱动 LLM-as-agent /
Python-pipeline 增强),以及 **Deck**(浅色模式切换 + 幻灯片上限 +
最大图数控件会流向 `ExportOptions`)。Windows 发行版 zip 发货的是
Nuitka 编译的包,已含 PySide6,所以 `thesisagents.exe gui` 不必另外
装 Python 就能运作。
**UI 以全部 14 种语言发货**(English、繁體中文、简体中文、日本語、
Español、Français、Deutsch、한국어、Português、Русский、Italiano、
Tiếng Việt、हिन्दी、Bahasa Indonesia)—— 首次运行会从你的 OS 语系挑选
语言,之后 **Settings → Interface language** 让你更改它。幻灯片输出语言
是一个独立的下拉菜单,所以你可以用一种语言跑 UI、用另一种语言产出
幻灯片。布局是响应式的:每个表单都坐在一个 `QScrollArea` 里,窗口可以
缩小到 900×600(仍容得下 720p),并默认开启 HiDPI 缩放。

完整参考:[`docs/gui.md`](../docs/gui.md)。

## 打包成独立可执行文件

记载了两个打包器,用来发货一个不必安装 Python 就能跑的单文件二进制:

- **[`docs/packaging-pyinstaller.md`](../docs/packaging-pyinstaller.md)**
  —— 快速构建(不到一分钟)、输出 200–300 MB、启动 2–4 秒。当你在
  迭代构建脚本时最合适。
- **[`docs/packaging-nuitka.md`](../docs/packaging-nuitka.md)** ——
  缓慢构建(5–15 分钟)、输出 80–150 MB、亚秒级启动,带一些字节码
  保护。当终端用户会多次运行二进制时最合适。

两份文档都涵盖了项目特有的陷阱 —— `sources/<name>/` 下的动态来源
插件 —— 并附上一个经验证、涵盖 CLI 与 MCP 服务器入口点的命令。

## 持续集成与发行

`.github/workflows/` 下住着两个 GitHub Actions 工作流程:

- **`ci.yml`** 在每次推送与对 `main` 的 PR 上运行。矩阵是 Ubuntu +
  Windows × Python 3.12 / 3.13 / 3.14(6 个 job)。每个 job 跑
  `ruff check`、`bandit -c pyproject.toml` 与 `pytest`。
- **`release.yml`** 等待 `ci.yml` 在 `main` 上完成(`workflow_run`
  触发)。它只在 CI 成功时运行。**每一次 CI 成功推送到 `main` 都是一次
  发行** —— 工作流程会自动升 `pyproject.toml` 的 patch 版本、把版本升号
  以 `chore: bump version to X.Y.Z` commit 回 `main`,并进行流水线:
  1. **`bump-version`** —— 从 `pyproject.toml` 读出当前的 `X.Y.Z`,
     递增到 `X.Y.(Z+1)`,用工作流程的 `GITHUB_TOKEN` commit + push 回
     `main`。那次推送**不会**重新触发 CI(依 GitHub 规则,
     `GITHUB_TOKEN` 驱动的推送无法启动新的 workflow run),所以这个
     循环会自然终止。
  2. **`publish-pypi`** —— 构建 sdist + wheel、`twine check`、经由
     `PYPI_API_TOKEN` `twine upload`。
  3. **`create-draft-release`** —— 在 tag `v<version>` 开一个*草稿*
     GitHub release,附自动生成的说明。
  4. **`build-nuitka`** —— 在一个 Windows runner 上编译一个 Nuitka
     standalone 包(入口点:经由 `--python-flag=-m` 的
     `python -m thesisagents`)、冒烟测试它、把产出的
     `thesisagents.dist/` 文件夹打包成 zip,并把 zip + 一个 `.sha256`
     校验和附到草稿 release。刻意设计成 standalone(不是 onefile):
     onefile 每次启动都会自解压到 `%TEMP%`,增加启动延迟并在锁死的
     机器上触发杀毒启发式。也刻意只支持 Windows:Linux / macOS 用户
     从 PyPI 安装。以 `pyproject.toml` 为键的构建缓存把暖构建从约 85 分
     冷构建削减到约 5–10 分。
  5. **`publish-release`** —— 一旦 Nuitka 资产上传完成就取消草稿标记,
     让用户永远不会看到一个做到一半的 release。

  **跳过一次发行。** 在 commit 消息任何地方包含 `[skip release]`,升号
  加上每个下游 job 都会被跳过 —— 对不该烧掉一个版本号的纯文档 / 错字 /
  重构 commit 使用它。

要启用 PyPI 发布 + 发行可执行文件:

1. 在 <https://pypi.org/manage/account/token/> 生成一个项目范围的 API
   token。
2. 在 GitHub repo 里:`Settings → Secrets and variables → Actions →
   New repository secret`。命名为 `PYPI_API_TOKEN` 并粘贴 token 值。
3. 允许 GitHub Actions 推送到 `main`:`Settings → Actions →
   General → Workflow permissions → Read and write permissions`。升号
   commit 由工作流程的 `GITHUB_TOKEN` 推送。
4. 经由把 PR 并入 `main` 来发行。流水线需要约 3–5 分钟发布到 PyPI,再
   约 80–90 分钟(冷)或约 5–10 分钟(暖 Nuitka 缓存)让 Windows zip
   附上。

`publish-pypi` job 刻意**不**附加一个 GitHub Environment,所以每次运行
都以 Release 条目(附它的 Nuitka `.exe`)呈现,而非以 repo 首页上的
「Deployment」侧边栏小部件呈现 —— release 有自己专属的页面,上头再加一个
Deployment 条目只会是多余的噪声。

## 许可证

见 `LICENSE`。arXiv API 依 arXiv 的 API 使用条款
(<https://info.arxiv.org/help/api/tou.html>)使用 —— 遵守每 3 秒 1 次
请求的软性限制;随附的 fetcher 已经由它的 token bucket 强制此限制。
