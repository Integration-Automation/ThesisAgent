# AutoPaperToPPT

[![CI](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![Python](https://img.shields.io/pypi/pyversions/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/AutoPaperToPPT.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/autopapertoppt/badge/?version=latest)](https://autopapertoppt.readthedocs.io/en/latest/)

> **语言**: [English](README.md) · [繁體中文](README.zh-TW.md) · **简体中文** · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **文档**: [autopapertoppt.readthedocs.io](https://autopapertoppt.readthedocs.io/en/latest/)

以关键词驱动的论文搜索助手。从 arXiv、Semantic Scholar、OpenAlex、PubMed、ACM(走 Crossref)、IEEE Xplore、DBLP、通用 Crossref、OpenAIRE、Springer Nature、Google Scholar 抓论文,规范化为统一的 record,并把去重后的结果集导出为 **论文答辩级的 PowerPoint 幻灯片**、**Excel 工作簿**、**BibTeX 文件** —— 一次 CLI 调用或一次 MCP 工具调用即可完成全部。可选让 AI 读 PDF 正文后产出每篇论文的结构化摘要(LLM-as-agent 路径)或通过 Anthropic API 自动产(Python pipeline 路径)。

## 给驱动本项目的 AI agent 看

**如果你是 LLM(Claude Code、Cursor、Aider、Codex CLI …)正在读这份 README 想搞清楚要做什么 —— 从这节开始。** 下面的规则也钉在 [`AGENTS.md`](AGENTS.md)(跨 agent 镜像)与 [`CLAUDE.md`](CLAUDE.md)(权威来源),做非小改动前请先读。

### 用户真正想要的

默认交付物是 **每篇一份论文答辩级的富版 `.pptx`**,不是 CLI 默认出的「只有摘要的轻量版」。轻量 emit 是中间产物,**你的工作就是把它升级**。

### 决策树

1. 环境变量有设 `ANTHROPIC_API_KEY` 吗? → 直接跑 CLI,它会走 Anthropic API 自动产富版。你做完了。
2. 没 key 但你(LLM)正在驱动这次 session → **你自己手写 rich summary**。每篇 PDF 自己读,手写 `PaperSummary` 含 rich-tier 字段(`pain_points`、`research_question`、`contributions_detailed`、`headline_metrics`、`technique_table`、`method_sections`、`evaluation_sections`、`system_flow`、`research_questions`、`rq_results`、`core_observation`、`limitations`、`future_work`),放一份 `scripts/regen_<query>.py`,跑它。**不要叫用户去设 API key** —— 你就是那个会写 summary 的 LLM。
3. 没 LLM(CI / cron / 无人值守)→ 轻量版可以接受。

### MCP 6 步流程

```
1. (可选) list_sources()                              # 看哪些 plugin 已启用
2. search(keywords, sources, top_tier_only=true, ...)
3. (可选) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)              # 每篇都要
5. (你逐篇读 PDF,自己产 structured summary dict)
6. export(papers=[{...paper, "summary": {...}}], language="zh-cn", ...)
```

11 个 MCP 工具(包含 `list_sources`、`download_pdfs`、`pptx_inspect` / `pptx_update_slide` / `pptx_add_slide` 等)的完整参考在 [`docs/mcp.md`](docs/mcp.md)。

### 必做:交付前验证 URL / DOI

出版商的 URL 路径 **不能猜** —— AAAI 用数字 ID(`v40i5.37389`),IEEE 用 opaque `arnumber`,ACM 用 opaque DOI。手写 `Paper` 时,**`url` / `doi` / `arxiv_id` 必须逐字从同一次搜索产生的 xlsx 抄过来** —— 不能凭印象,也不能从标题自己拼。

xlsx 写在 `exports/<run>/<slug>-<timestamp>.xlsx`,第 7 列是 DOI、第 8 列是 URL。Regen script 跑完做这个 audit:

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

这套 audit 抓到过两个 production fabrication:写错 AAAI 卷期(`v39i23.34521` vs 真实的 `v39i22.34537`)、编造作者 slug 路径(`view/fang2026` 而不是 `v40i5.37389`)。

### 必做:交付前剪除不相关下载

搜索是关键词匹配,常会误触不相关论文:"Claude code" 抓到一篇 Viterbi 解码器(因为都含 "code");"LLM code review" 抓到一篇目标检测综述。判定为不相关后,直接剪掉:

```python
from pathlib import Path
run = Path("exports/<run>")
irrelevant_keys = ("key-of-off-topic-paper-1", "key-of-off-topic-paper-2")
for key in irrelevant_keys:
    for path in (run / "pdfs" / f"{key}.pdf", run / f"{key}.pptx"):
        if path.exists():
            path.unlink()
```

删 `exports/<run>/pdfs/<key>.pdf` + `exports/<run>/<key>.pptx`。**保留** aggregate `<slug>-<timestamp>.xlsx` / `.bib` —— 那是搜索的诚实记录。Borderline cases 宁可写 rich summary 也不要默默丢掉可能的命中。

### 示例

[`scripts/regen_llm_security_batch.py`](scripts/regen_llm_security_batch.py) 内有 8 篇手写的 rich summary,完全照这套流程做的。任何多篇论文的搜索都用它当 template。繁中版在 [`scripts/regen_llm_security_batch_zh_tw.py`](scripts/regen_llm_security_batch_zh_tw.py)。

### 禁忌

- **不要** 在多篇搜索结束时告诉用户「设 `ANTHROPIC_API_KEY` 才能拿到富版」—— 你就是那个会写 summary 的 LLM。
- **不要** 把每篇的轻量 `.pptx` 当成交付物。
- **不要** 看到 `download_pdfs` 报告「N 份 PDF 已存」就停 —— 那是 rich-authoring 的开始,不是结束。
- **不要** 编造论文里没有的数字、RQ、贡献、限制。
- **不要** 编造 URL / DOI / arXiv ID —— 见上面那条规则。
- **不要** 把不相关下载留在 run 目录里。搜索是关键词匹配,常会误触不相关论文(例如 "Claude code" 抓到一篇 Viterbi 解码器论文;"LLM code review" 抓到一篇目标检测综述)。判定为不相关后,把 `pdfs/<key>.pdf` 与轻量 `<key>.pptx` 删掉;保留 aggregate xlsx / bib 作为搜索的「诚实记录」。
- **不要** 在 commit message、PR description、代码注释或文档里提到「Claude」、「Claude Code」、「AI-generated」、「GPT」、「Copilot」或任何 AI 工具 / 模型名称。

## 功能

- **十一种可插拔来源**: `arxiv`、`semantic_scholar`、`openalex`、`pubmed`、`acm`(Crossref 限定 ACM)、`dblp`、`crossref`(通用)、`openaire`、`springer`(需 API key)、`ieee`(API key 或 opt-in 爬取)、`scholar`(opt-in 爬取)。每个都在 `sources/<name>/` 后面以 `Fetcher` 接口实现。默认启用「顶级期刊白名单」过滤器,保留旗舰级 CS 会议/期刊 + Nature/Science/PNAS 等;传 `--all-venues` 可关闭。
- **单篇论文模式**: 粘贴 arXiv ID、arXiv URL、DOI、PMID、或 IEEE 文档 URL,AutoPaperToPPT 会走对应 source plugin 拉那一篇并出同一套导出包。适合做论文阅读笔记或答辩准备。
- **本地 PDF 模式** (`--pdf <path>`): 传一个 PDF 或一整个目录。内置启发式抽取器会从每个 PDF 的首页直接抽出 **标题、作者、年份、arXiv ID、DOI、真正的摘要**(以「Abstract」/「ABSTRACT」/「摘要」标题为锚点,而不是随便切前 N 字)。单 PDF 时 `--title` / `--authors` / `--year` / `--venue` / `--doi` / `--arxiv-id` 会覆盖抽取结果;目录模式下以每个文件自己的抽取结果为准,每篇都会输出一份以 BibTeX key 命名的幻灯片。
- **五种导出器**:
  - `.pptx` —— 16:9 宽屏、带页码。三种 rendering tier(轻量摘要 / 扁平结构化 / **论文答辩级 thesis-style**:痛点四宫格、研究问题 callout、KPI 区、技术比较表、文献定位表、系统总览、方法细节、每个 RQ 结果表、贡献总结、核心观察、限制与未来工作、Q&A、参考文献)。所有模板字符串都做 i18n,共 **14 种语言**:English、繁體中文、简体中文、日本語、Español、Français、Deutsch、한국어、Português、Русский、Italiano、Tiếng Việt、हिन्दी、Bahasa Indonesia。
  - `.xlsx` —— Papers 工作表 + Query 出处工作表,URL/PDF 带超链接、首行冻结、列宽自动。第 5 列 **Source** 显示真实刊登来源(例如「IEEE Access」),第 6 列 **Indexed via** 显示是哪个 fetcher 抓到的(例如「openalex」),两个信息不会混在一起。
  - `.md` —— 完整来源/标题/摘要清单。
  - `.bib` —— 不会撞 key、LaTeX 特殊字符已转义。
  - `.json` —— 原始 payload 供下游处理。
- **PPT 编辑工具箱**: `autopapertoppt.exporters.pptx_edit`(inspect / update_slide / delete_slide / reorder_slides / add_slide)能对 exporter 生成的任何幻灯片做编辑,对应的 `pptx_*` MCP 工具也让 LLM agent 能继续对 deck 做迭代。
- **MCP server**: 11 个工具 —— `list_sources`(来源发现)、`search`、`fetch_paper`、`fetch_pdf_text`、`download_pdfs`(批量下载)、`export`,以及五个 `pptx_*` 编辑工具。任何支持 MCP 的 LLM(Claude Code、Claude Desktop、Cursor…)都能驱动整套流程。
- **两条 enrichment 路径** 把 deck 从「只有摘要」升级到「真的读过全文」:
  - **LLM-as-agent(不需要 API key)** —— 调用端的 LLM 通过 `fetch_pdf_text` 拿 PDF 正文,在自己的 context 里产 structured summary,再丢给 `export`。
  - **Python pipeline(`--enrich`)** —— CLI 自己打 Anthropic API,默认模型 `claude-opus-4-7`。
- **默认安全**: HTTPS-only HTTP transport、每个来源 token bucket 限流、任何 XML payload 都走 `defusedxml`、导出路径做 path-traversal 检查、用户输入完全不会碰到 `eval` / `exec` / `pickle`。Scholar 与 IEEE 爬取默认关闭,需 env var 开关。

## 快速开始

```powershell
git clone <repo-url>
cd AutoPaperToPPT
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# 安装 dev extras(会一并拉进 MCP SDK 与 intelligence 依赖)
pip install -e .[dev]
```

搜索 arXiv 并导出 deck + workbook + BibTeX(`--query` 默认):

```powershell
py -m autopapertoppt --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

抓单篇论文 —— 默认只出 `.pptx + .bib`(单篇没必要出 `.xlsx`):

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

把 deck 改成繁体中文:

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --lang zh-tw --out .\exports\
```

LLM-pipeline enrichment(Python 自己打 Anthropic,需要 API key):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang zh-tw --out .\exports\
```

## CLI 参数

| 参数 | 用途 |
|---|---|
| `--query` / `-q` | 关键词(没给 `--paper` 时必填)。 |
| `--paper` / `-p` | arXiv ID / URL、DOI、PMID 或 IEEE 文档 URL,与 `--query` 互斥。 |
| `--source` / `-s` | 用逗号分隔的来源列表。默认 `arxiv`。 |
| `--max` / `-n` | 每个来源的最大结果数(1..200)。默认 25。 |
| `--year-from` / `--year-to` | 年份过滤(含端点)。 |
| `--export` / `-e` | 格式: `pptx,xlsx,md,bib,json` 任意组合。默认依模式不同(见下)。 |
| `--out` / `-o` | 导出目录。默认 `./exports`。 |
| `--filename-stem` | 覆盖自动生成的文件名 stem。 |
| `--no-abstract` | 不把摘要写进导出文件。 |
| `--lang` / `-l` | Deck 语言: `en` / `zh-tw` / `zh-cn` / `ja`,默认 `en`。 |
| `--enrich` | 抓 PDF + 用 Anthropic 产 summary。需要 `ANTHROPIC_API_KEY` 与 `[intelligence]` 包。 |
| `--lightweight` | 即使有 `ANTHROPIC_API_KEY` 也强制走「只用摘要」的轻量版。 |
| `--llm-model` | 覆盖 enrichment 默认的 `claude-opus-4-7`。 |
| `--all-venues` | 关闭顶级期刊白名单(默认只收旗舰级 CS 会议/期刊 + Nature / Science / PNAS / CACM / LNCS)。 |
| `--paywall-threshold` | 多少比例的结果是付费墙才会触发确认提示。默认 0.30。 |
| `--yes` | 跳过付费墙提示。 |
| `--max-slides` | 每篇 PPT 幻灯片上限(默认 25;传 0 表示不限)。 |
| `--quiet` | 不打印每篇论文。 |

默认值: `--query` → `pptx,xlsx,bib`;`--paper` → `pptx,bib`。一律可被 `--export` 覆盖。

### 环境变量

| 变量 | 用于 | 用途 |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | LLM 认证。MCP 上的 LLM-as-agent 路径不需要。 |
| `AUTOPAPERTOPPT_LLM_MODEL` | `--enrich` | 覆盖默认的 `claude-opus-4-7`。 |
| `AUTOPAPERTOPPT_S2_API_KEY` | Semantic Scholar | 提高速率限制,选用。 |
| `AUTOPAPERTOPPT_NCBI_API_KEY` | PubMed | 把 NCBI 匿名限额(3/s)提到 10/s,选用。 |
| `AUTOPAPERTOPPT_CONTACT_EMAIL` | PubMed、ACM、Crossref、OpenAlex | 让 Crossref 等把请求放进「礼貌池」。 |
| `AUTOPAPERTOPPT_IEEE_API_KEY` | IEEE(API 路径) | 切换到官方 Xplore API,订阅范围内会带 `pdf_url`。 |
| `AUTOPAPERTOPPT_ENABLE_IEEE_SCRAPING` | IEEE(爬取路径) | 设 `=1` 才启用爬取。若已设 API key,此变量不需要。 |
| `AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN` | ACM、Crossref | Crossref Plus 订阅 token(Bearer header),选用。 |
| `AUTOPAPERTOPPT_SPRINGER_API_KEY` | Springer | 必填;免费 key 申请 <https://dev.springernature.com/>。没设则该 plugin 会被静默跳过。 |
| `AUTOPAPERTOPPT_ENABLE_SCHOLAR_SCRAPING` | Google Scholar | 设 `=1` 才启用。默认关闭(Scholar ToS 禁止爬取)。 |
| `AUTOPAPERTOPPT_PDF_COOKIES_FILE` | PDF 下载器 | Netscape `cookies.txt`,默认关闭。请只用在你有合法访问权的出版商。 |
| `AUTOPAPERTOPPT_LOG_LEVEL` | logger | 默认 `INFO`;`DEBUG` 可看更详细。 |

## MCP server

注册到 Claude Code:

```powershell
claude mcp add autopapertoppt -- ".venv\Scripts\python.exe" -m autopapertoppt.mcp
```

或写到 settings:

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

工具:

| Tool | 用途 |
|---|---|
| `list_sources` | 列出所有 plugin + 报告当前 env 下哪些已启用。`search` 之前先调一次。 |
| `search` | 关键词 → 论文列表。可带 `top_tier_only`、`min_citations`;省略 `sources` 时默认扫所有不需要 API key 的来源。 |
| `fetch_paper` | arXiv / DOI / PMID / IEEE 标识符 → 单篇论文。 |
| `fetch_pdf_text` | 抓单个 PDF 并返回提取的正文。**MCP 路径下「让我读过论文」的入口。** |
| `download_pdfs` | 批量把一组论文的 PDF 下载到 `{out_dir}/pdfs/`。返回以 BibTeX key 为索引的逐篇结果。 |
| `export` | 论文列表 + 格式 → 写出 `.pptx/.xlsx/.md/.bib/.json`。每篇可附 `summary` 走 thesis-style;支持 `max_slides_per_paper`(默认 25)。 |
| `pptx_inspect` | 读已有幻灯片文件的 slide / shape 结构。 |
| `pptx_update_slide` | 替换 `title` / `body` / `meta`(通过 shape name)或任意 shape(通过 index)。 |
| `pptx_delete_slide` | 删除一张 slide 及其 part relationship。 |
| `pptx_reorder_slides` | 通过 `sldIdLst` 重排幻灯片。 |
| `pptx_add_slide` | 在末尾追加或在指定 position 插入一张新的 title / body / meta slide。 |

LLM-as-agent 流程(不需要 `ANTHROPIC_API_KEY`,因为 LLM 本身就是 agent):

```
1. (可选) list_sources()                            # 先看哪些 plugin 开着
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (可选) download_pdfs(papers, out_dir="./exports/...")  # 把 PDF 存到本地
4. fetch_pdf_text(pdf_url=paper.pdf_url)            # 每篇都做一次
5. (LLM 读正文,自己产 structured summary dict)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="zh-tw", formats=["pptx","bib"], ...)
```

完整参考: [`docs/mcp.md`](docs/mcp.md)。

## 项目结构

```
AutoPaperToPPT/
├── autopapertoppt/                 # 主包
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # HTTPS-only async client、token-bucket 限流
│   ├── exporters/                   # pptx(thesis-style)/ xlsx / bib / md / json / pptx_edit / i18n
│   ├── intelligence/                # PDF 抓取 + Anthropic 摘要器([intelligence] extra)
│   ├── mcp/                         # FastMCP server(11 个工具)
│   ├── utils/                       # logging、path safety
│   ├── cli.py                       # argparse CLI
│   └── __main__.py
├── sources/                         # plugin 目录: arxiv、semantic_scholar、
│                                    #   openalex、pubmed、acm、ieee、scholar、
│                                    #   dblp、crossref、openaire、springer
├── tests/                           # pytest suite + 录制 fixture(不打活 HTTP)
├── docs/                            # Sphinx(en + zh-tw + zh-cn)
├── scripts/                         # 一次性 regen 脚本
└── pyproject.toml                   # ruff、bandit、build、optional extras
```

## Definition of Done

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r autopapertoppt/ sources/
```

bandit 的 `-c` 标志是必需的 —— 没有它 bandit 不会读项目 skip 配置。动到 pptx exporter 时,还要跑 overflow check(见 `CLAUDE.md` 的「Slide Deck Rules」一节)。

## 许可

见 `LICENSE`。arXiv API 的使用受 arXiv API 服务条款约束(<https://info.arxiv.org/help/api/tou.html>) —— 请遵守每 3 秒 1 次的软限制;内置的 fetcher 已通过 token bucket 强制此速率。
