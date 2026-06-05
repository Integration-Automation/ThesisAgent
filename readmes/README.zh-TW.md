# ThesisAgents

[![CI](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![Python](https://img.shields.io/pypi/pyversions/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/ThesisAgents.svg)](https://github.com/Integration-Automation/ThesisAgents/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/thesisagents/badge/?version=latest)](https://thesisagents.readthedocs.io/en/latest/)

> **語言**: [English](../README.md) · **繁體中文** · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **文件**: [thesisagents.readthedocs.io](https://thesisagents.readthedocs.io/en/latest/)

以關鍵字驅動的論文搜尋助手。從 arXiv、Semantic Scholar、OpenAlex、PubMed、ACM(走 Crossref)、IEEE Xplore、DBLP、通用 Crossref、OpenAIRE、Springer Nature、Google Scholar 抓論文,正規化成統一的 record,並把去重後的結果集匯出為 **論文口試級的 PowerPoint 投影片**、**Excel 工作簿**、**BibTeX 檔** —— 一次 CLI 呼叫或一次 MCP 工具呼叫即可完成全部。另可選擇讓 AI 讀 PDF 本文後產出每篇論文的結構化摘要(LLM-as-agent 路徑)或透過 Anthropic API 自動產(Python pipeline 路徑)。

## 給驅動本專案的 AI agent 看

**如果你是 LLM(Claude Code、Cursor、Aider、Codex CLI …)正在讀這份 README 想搞清楚要做什麼 —— 從這節開始。** 下面的規則也釘在 [`AGENTS.md`](AGENTS.md)(跨 agent 鏡像)與 [`CLAUDE.md`](CLAUDE.md)(權威來源),做非小改動前請先讀。

### 使用者真正想要的

預設交付物是 **每篇一份論文口試級的富版 `.pptx`**,不是 CLI 預設出的「只有摘要的輕量版」。輕量 emit 是中間產物,**你的工作就是把它升級**。

### 決策樹

1. 環境變數有設 `ANTHROPIC_API_KEY` 嗎? → 直接跑 CLI,它會走 Anthropic API 自動產富版。你做完了。
2. 沒 key 但你(LLM)正在驅動這次 session → **你自己手寫 rich summary**。每篇 PDF 自己讀,手寫 `PaperSummary` 含 rich-tier 欄位(`pain_points`、`research_question`、`contributions_detailed`、`headline_metrics`、`technique_table`、`method_sections`、`evaluation_sections`、`system_flow`、`research_questions`、`rq_results`、`core_observation`、`limitations`、`future_work`),放一份 `scripts/regen_<query>.py`,跑它。**不要叫使用者去設 API key** —— 你就是那個會寫 summary 的 LLM。
3. 沒 LLM(CI / cron / 無人值守)→ 輕量版可以接受。

### MCP 6 步驟流程

```
1. (選) list_sources()                                # 看哪些 plugin 已啟用
2. search(keywords, sources, top_tier_only=true, ...)
3. (選) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)              # 每篇都要
5. (你逐篇讀 PDF,自己產 structured summary dict)
6. export(papers=[{...paper, "summary": {...}}], language="zh-tw", ...)
```

11 個 MCP 工具(包含 `list_sources`、`download_pdfs`、`pptx_inspect` / `pptx_update_slide` / `pptx_add_slide` 等)的完整參考在 [`docs/mcp.md`](docs/mcp.md)。

### 必做:交付前驗證 URL / DOI

出版商的 URL 路徑 **不能用猜的** —— AAAI 用數字 ID(`v40i5.37389`),IEEE 用 opaque `arnumber`,ACM 用 opaque DOI。手寫 `Paper` 時,**`url` / `doi` / `arxiv_id` 必須逐字從同一次搜尋產生的 xlsx 抄過來** —— 不能憑印象,也不能從標題自己拼。

xlsx 寫在 `exports/<run>/<slug>-<timestamp>.xlsx`,第 7 欄是 DOI、第 8 欄是 URL。Regen script 跑完做這個 audit:

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

過去這套 audit 抓到兩個 production fabrication:寫錯 AAAI 卷期(`v39i23.34521` vs 真實的 `v39i22.34537`)、編造作者 slug 路徑(`view/fang2026` 而不是 `v40i5.37389`)。

### 必做:交付前剪除不相關下載

搜尋是關鍵字比對,常會誤觸不相關論文:"Claude code" 抓到一篇 Viterbi 解碼器(因為都含 "code");"LLM code review" 抓到一篇物件偵測綜述。判定為不相關後,直接剪掉:

```python
from pathlib import Path
run = Path("exports/<run>")
irrelevant_keys = ("key-of-off-topic-paper-1", "key-of-off-topic-paper-2")
for key in irrelevant_keys:
    for path in (run / "pdfs" / f"{key}.pdf", run / f"{key}.pptx"):
        if path.exists():
            path.unlink()
```

刪 `exports/<run>/pdfs/<key>.pdf` + `exports/<run>/<key>.pptx`。**保留** aggregate `<slug>-<timestamp>.xlsx` / `.bib` —— 那是搜尋的誠實紀錄。Borderline cases 寧可寫 rich summary 也不要默默丟掉可能的命中。

### 範例

[`scripts/regen_llm_security_batch.py`](scripts/regen_llm_security_batch.py) 內有 8 篇手寫的 rich summary,完全照這套流程做的。任何多篇論文的搜尋都用它當 template。繁中版在 [`scripts/regen_llm_security_batch_zh_tw.py`](scripts/regen_llm_security_batch_zh_tw.py)。

### 禁忌

- **不要** 在多篇搜尋結束時告訴使用者「設 `ANTHROPIC_API_KEY` 才能拿到富版」—— 你就是那個會寫 summary 的 LLM。
- **不要** 把每篇的輕量 `.pptx` 當成交付物。
- **不要** 看到 `download_pdfs` 回報「N 份 PDF 已存」就停 —— 那是 rich-authoring 的開始,不是結束。
- **不要** 編造論文裡沒有的數字、RQ、貢獻、限制。
- **不要** 編造 URL / DOI / arXiv ID —— 見上面那條規則。
- **不要** 把不相關下載留在 run 目錄裡。搜尋是關鍵字比對,常會誤觸到不相關的論文(例如 "Claude code" 帶到一篇 Viterbi 解碼器論文;"LLM code review" 帶到一篇物件偵測綜述)。判定為不相關後,把 `pdfs/<key>.pdf` 與輕量 `<key>.pptx` 刪掉;保留 aggregate xlsx / bib 作為搜尋的「誠實紀錄」。
- **不要** 在 commit message、PR description、程式註解或文件裡提到「Claude」、「Claude Code」、「AI-generated」、「GPT」、「Copilot」或任何 AI 工具 / 模型名稱。

## 功能

- **十一種可外掛來源**: `arxiv`、`semantic_scholar`、`openalex`、`pubmed`、`acm`(Crossref 限縮 ACM)、`dblp`、`crossref`(通用)、`openaire`、`springer`(需 API key)、`ieee`(API key 或 opt-in 爬取)、`scholar`(opt-in 爬取)。每個都在 `sources/<name>/` 後面以 `Fetcher` 介面實作。預設啟用「頂級期刊白名單」過濾器,保留旗艦級 CS 會議/期刊 + Nature/Science/PNAS 等;傳 `--all-venues` 可關閉。
- **單篇論文模式**: 貼上 arXiv ID、arXiv URL、DOI、PMID、或 IEEE 文件 URL,ThesisAgents 會走對應 source plugin 拉那一篇並出同一套匯出包。適合做論文閱讀筆記或口試準備。
- **本機 PDF 模式** (`--pdf <path>`): 傳一個 PDF 或一整個資料夾。內建啟發式抽取器會從每個 PDF 的首頁直接撈出 **標題、作者、年份、arXiv ID、DOI、真正的摘要**(以「Abstract」/「ABSTRACT」/「摘要」標題為錨點,不是隨便切前 N 字)。單一 PDF 時 `--title` / `--authors` / `--year` / `--venue` / `--doi` / `--arxiv-id` 會覆寫抽取結果;資料夾模式下以每個檔自己的抽取結果為準,每篇都會出一份以 BibTeX key 命名的投影片。
- **五種匯出器**:
  - `.pptx` —— 16:9 寬螢幕、附頁碼。三種 rendering tier(輕量摘要 / 扁平結構化 / **論文口試級 thesis-style**:痛點四宮格、研究問題 callout、KPI 區、技術比較表、文獻定位表、系統總覽、方法細節、每題 RQ 結果表、貢獻總結、核心觀察、限制與未來工作、Q&A、參考文獻)。所有樣板字串都做 i18n,共 **14 種語言**:English、繁體中文、简体中文、日本語、Español、Français、Deutsch、한국어、Português、Русский、Italiano、Tiếng Việt、हिन्दी、Bahasa Indonesia。
  - **設計過的視覺識別**(不是預設 Calibri-on-white 的樣子):每語言字體 pass(Latin 用 Inter,CJK + Hindi 用 Microsoft JhengHei UI / YaHei UI / Yu Gothic UI / Malgun Gothic / Nirmala UI)、程式化的 accent geometry(每張內容投影片頂端的 accent bar + 封面的左側帶)、學術風表格(去掉預設黑色 grid、navy header rule、淡色 inter-row divider、交替 row stripe、置中對齊、首欄粗體標籤),搭配五色 palette 紀律(navy / teal / grey / light / white) —— 紅色文字被禁用,強調用 **粗體 + teal `#0E7490`** 取代。
  - **暗色模式為預設**。先用 light palette 建構 deck,再用 post-build pass 把 text + fill + cell-border 的 RGB 換成暗色版本(slide bg `#12151B`、body text `#E5E7EB`、teal accent 換成更亮的 `#2DD4BF`)。OLED 投影機與昏暗會場直接拿到暗版本,作者不用思考;若要列印或在明亮場地用,加 `--light-mode`(CLI)、勾掉 GUI Deck 分頁的 **Light mode**、或在程式中傳 `ExportOptions(dark_mode=False)`。
  - `.xlsx` —— Papers 工作表 + Query 出處工作表,URL/PDF 帶超連結、首列凍結、欄寬自動。第 5 欄 **Source** 顯示真實刊登來源(例如「IEEE Access」),第 6 欄 **Indexed via** 顯示是哪個 fetcher 抓到的(例如「openalex」),兩個資訊不會混在一起。
  - `.md` —— 完整來源/標題/摘要清單。
  - `.bib` —— 不會撞 key、LaTeX 特殊字元已跳脫。
  - `.json` —— 原始 payload 供下游處理。
- **PPT 編輯工具箱**: `thesisagents.exporters.pptx_edit`(inspect / update_slide / delete_slide / reorder_slides / add_slide)能對 exporter 產生的任何投影片做編輯,對應的 `pptx_*` MCP 工具也讓 LLM agent 能繼續對 deck 做迭代。
- **MCP server**: 11 個工具 —— `list_sources`(來源探索)、`search`、`fetch_paper`、`fetch_pdf_text`、`download_pdfs`(批次下載)、`export`,以及五個 `pptx_*` 編輯工具。任何支援 MCP 的 LLM(Claude Code、Claude Desktop、Cursor…)都能驅動整套流程。
- **兩條 enrichment 路徑** 把 deck 從「只有摘要」升級到「真的讀過全文」:
  - **LLM-as-agent(不需要 API key)** —— 呼叫端的 LLM 透過 `fetch_pdf_text` 拿 PDF 本文,在自己 context 裡產 structured summary,再丟給 `export`。
  - **Python pipeline(`--enrich`)** —— CLI 自己打 Anthropic API,預設模型 `claude-opus-4-7`。
- **預設安全**: HTTPS-only HTTP transport、每來源 token bucket 限流、任何 XML payload 都走 `defusedxml`、匯出路徑做 path-traversal 檢查、使用者輸入完全不會碰到 `eval` / `exec` / `pickle`。Scholar 與 IEEE 爬取預設關閉,需 env var 開關。

## 快速開始

```powershell
git clone <repo-url>
cd ThesisAgents
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# 安裝 dev extras(會一併拉進 MCP SDK 與 intelligence 相依)
pip install -e .[dev]
```

搜尋 arXiv 並輸出 deck + workbook + BibTeX(`--query` 預設):

```powershell
py -m thesisagents --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

抓單篇論文 —— 預設只出 `.pptx + .bib`(單篇沒必要出 `.xlsx`):

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

把 deck 改成繁體中文:

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --lang zh-tw --out .\exports\
```

LLM-pipeline enrichment(Python 自己打 Anthropic,需要 API key):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang zh-tw --out .\exports\
```

## CLI 參數

| 參數 | 用途 |
|---|---|
| `--query` / `-q` | 關鍵字(沒給 `--paper` 時必填)。 |
| `--paper` / `-p` | arXiv ID / URL、DOI、PMID 或 IEEE 文件 URL,與 `--query` 互斥。 |
| `--source` / `-s` | 用逗號分隔的來源列表。預設 `arxiv`。 |
| `--max` / `-n` | 每個來源的最大結果數(1..200)。預設 25。 |
| `--year-from` / `--year-to` | 年份過濾(含端點)。 |
| `--export` / `-e` | 格式: `pptx,xlsx,md,bib,json` 任意組合。預設依模式不同(見下)。 |
| `--out` / `-o` | 匯出目錄。預設 `./exports`。 |
| `--filename-stem` | 蓋掉自動產生的檔名 stem。 |
| `--no-abstract` | 不要把摘要寫進匯出檔。 |
| `--lang` / `-l` | Deck 語言: `en` / `zh-tw` / `zh-cn` / `ja`,預設 `en`。 |
| `--enrich` | 抓 PDF + 用 Anthropic 產 summary。需要 `ANTHROPIC_API_KEY` 與 `[intelligence]` 套件。 |
| `--lightweight` | 即使有 `ANTHROPIC_API_KEY` 也強制走「只用摘要」的輕量版。 |
| `--llm-model` | 蓋掉 enrichment 預設的 `claude-opus-4-7`。 |
| `--all-venues` | 關閉頂級期刊白名單(預設只收旗艦級 CS 會議/期刊 + Nature / Science / PNAS / CACM / LNCS)。 |
| `--paywall-threshold` | 多少比例的結果是付費牆才會觸發確認提示。預設 0.30。 |
| `--yes` | 跳過付費牆提示。 |
| `--max-slides` | 每篇 PPT 投影片上限(預設 25;傳 0 表示不限)。 |
| `--light-mode` | 用白底 + navy 文字 render 投影片。**暗色模式才是預設** —— 加這個 flag 是在明亮會場投影或要列印時使用。 |
| `--quiet` | 不要列印每篇論文。 |

預設值: `--query` → `pptx,xlsx,bib`;`--paper` → `pptx,bib`。一律可被 `--export` 覆寫。

### 環境變數

| 變數 | 用於 | 用途 |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | LLM 認證。MCP 上的 LLM-as-agent 路徑不需要。 |
| `THESISAGENTS_LLM_MODEL` | `--enrich` | 蓋掉預設的 `claude-opus-4-7`。 |
| `THESISAGENTS_S2_API_KEY` | Semantic Scholar | 提高速率限制,選用。 |
| `THESISAGENTS_NCBI_API_KEY` | PubMed | 把 NCBI 匿名限額(3/s)拉到 10/s,選用。 |
| `THESISAGENTS_CONTACT_EMAIL` | PubMed、ACM、Crossref、OpenAlex | 讓 Crossref 等把請求放進「客氣池」。 |
| `THESISAGENTS_IEEE_API_KEY` | IEEE(API 路徑) | 切換到官方 Xplore API,訂閱範圍內會帶 `pdf_url`。 |
| `THESISAGENTS_DISABLE_IEEE_SCRAPING` | IEEE(爬取路徑) | 設 `=1` 才會啟用爬取。若已設 API key,此變數不需要。 |
| `THESISAGENTS_CROSSREF_PLUS_TOKEN` | ACM、Crossref | Crossref Plus 訂閱 token(Bearer header),選用。 |
| `THESISAGENTS_SPRINGER_API_KEY` | Springer | 必填;免費 key 申請 <https://dev.springernature.com/>。沒設則該 plugin 會被靜默跳過。 |
| `THESISAGENTS_CHROME_PROFILE_DIR` | Scholar + IEEE + paywalled-PDF downloads | Persistent Chrome `--user-data-dir`. Set this and complete VPN / SSO once; subsequent runs inherit the cookies. |
| `THESISAGENTS_DISABLE_WEBRUNNER` | Scholar + IEEE + paywalled-PDF downloads | `=1` forces the httpx paths instead of driving real Chrome. For CI / Docker without a Chrome binary. |
| `THESISAGENTS_CORE_API_KEY` | OA resolver | Free key from <https://core.ac.uk/services/api>. Enables the CORE.ac.uk lookup step in the OA PDF resolver. |
| `THESISAGENTS_DISABLE_SCHOLAR_SCRAPING` | Google Scholar | 設 `=1` 才會啟用。預設關閉(Scholar ToS 禁止爬取)。 |
| `THESISAGENTS_PDF_COOKIES_FILE` | PDF 下載器 | Netscape `cookies.txt`,預設關閉。請只用在你有合法存取權的出版商。 |
| `THESISAGENTS_LOG_LEVEL` | logger | 預設 `INFO`;`DEBUG` 可看更詳細。 |

## MCP server

註冊到 Claude Code:

```powershell
claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp
```

或寫到 settings:

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

| Tool | 用途 |
|---|---|
| `list_sources` | 列出所有 plugin + 回報目前 env 下哪些已啟用。`search` 之前先呼叫這個。 |
| `search` | 關鍵字 → 論文列表。可帶 `top_tier_only`、`min_citations`;省略 `sources` 時預設掃所有不需要 API key 的來源。 |
| `fetch_paper` | arXiv / DOI / PMID / IEEE 識別碼 → 單篇論文。 |
| `fetch_pdf_text` | 抓單一 PDF 並回傳擷取的本文。**MCP 路徑下「讓我讀過論文」的入口。** |
| `download_pdfs` | 批次把一組論文的 PDF 下載到 `{out_dir}/pdfs/`。回傳以 BibTeX key 為索引的逐篇結果。 |
| `export` | 論文列表 + 格式 → 寫出 `.pptx/.xlsx/.md/.bib/.json`。每篇可附 `summary` 欄位走 thesis-style;支援 `max_slides_per_paper`(預設 25)。 |
| `pptx_inspect` | 讀既有投影片檔的 slide / shape 結構。 |
| `pptx_update_slide` | 取代 `title` / `body` / `meta`(透過 shape name)或任意 shape(透過 index)。 |
| `pptx_delete_slide` | 刪掉一張 slide 以及它的 part relationship。 |
| `pptx_reorder_slides` | 透過 `sldIdLst` 重排投影片。 |
| `pptx_add_slide` | 在尾端 append 或在指定 position 插入一張新的 title / body / meta slide。 |

LLM-as-agent 流程(不需要 `ANTHROPIC_API_KEY`,因為 LLM 自己就是 agent):

```
1. (選) list_sources()                              # 先看哪些 plugin 開著
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (選) download_pdfs(papers, out_dir="./exports/...")  # 把 PDF 存到本機
4. fetch_pdf_text(pdf_url=paper.pdf_url)            # 每篇都做一次
5. (LLM 讀本文,自己產 structured summary dict)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="zh-tw", formats=["pptx","bib"], ...)
```

完整參考: [`docs/mcp.md`](docs/mcp.md)。

## 專案結構

```
ThesisAgents/
├── thesisagents/                 # 主套件
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # HTTPS-only async client、token-bucket 限流
│   ├── exporters/                   # pptx(thesis-style)/ xlsx / bib / md / json / pptx_edit / i18n
│   ├── intelligence/                # PDF 抓取 + Anthropic 摘要器([intelligence] extra)
│   ├── mcp/                         # FastMCP server(11 個工具)
│   ├── utils/                       # logging、path safety
│   ├── cli.py                       # argparse CLI
│   └── __main__.py
├── sources/                         # plugin 資料夾: arxiv、semantic_scholar、
│                                    #   openalex、pubmed、acm、ieee、scholar、
│                                    #   dblp、crossref、openaire、springer
├── tests/                           # pytest suite + 錄製 fixture(不打活 HTTP)
├── docs/                            # Sphinx(en + zh-tw + zh-cn)
├── scripts/                         # 一次性 regen 腳本
└── pyproject.toml                   # ruff、bandit、build、optional extras
```

## Definition of Done

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r thesisagents/ sources/
```

bandit 的 `-c` 旗標是必要的 —— 沒有它 bandit 不會讀專案 skip 設定。動到 pptx exporter 時,還要跑 overflow check(見 `CLAUDE.md` 的「Slide Deck Rules」一節)。

## 授權

見 `LICENSE`。arXiv API 的使用受 arXiv API 服務條款規範(<https://info.arxiv.org/help/api/tou.html>)—— 請遵守每 3 秒 1 次的軟限制;內建的 fetcher 已透過 token bucket 強制此速率。
