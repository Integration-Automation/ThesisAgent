# ThesisAgents

[![CI](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![Python](https://img.shields.io/pypi/pyversions/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/ThesisAgents.svg)](https://github.com/Integration-Automation/ThesisAgents/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/thesisagents/badge/?version=latest)](https://thesisagents.readthedocs.io/en/latest/)

> **語言**: [English](../README.md) · **繁體中文** · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **文件**: [thesisagents.readthedocs.io](https://thesisagents.readthedocs.io/en/latest/)

以關鍵字驅動的論文搜尋助手,從 arXiv、Semantic Scholar、OpenAlex、
PubMed、ACM(走 Crossref)、IEEE Xplore、DBLP、通用 Crossref、
OpenAIRE、Springer Nature、Europe PMC、DOAJ、HAL、CORE 與 Google Scholar
抓取結果,把它們正規化成單一 record 形狀,並將去重後的結果集匯出為
**論文口試級的 PowerPoint 投影片**、**Excel 工作簿**與
**BibTeX 檔** —— 全部只需一次 CLI 呼叫或一次 MCP 工具呼叫即可完成。可選擇性地
讓系統讀取每篇論文的 PDF、產生每篇的結構化摘要,方式可以是就地(LLM-as-agent
路徑)或透過 Anthropic API(Python pipeline 路徑)。

## 給驅動本專案的 AI agent 看

**如果你是一個 LLM(Claude Code、Cursor、Aider、Codex CLI …)正在讀這份
README 想搞清楚要做什麼 —— 從這裡開始。** 底下的所有內容也都釘在
[`AGENTS.md`](AGENTS.md)(跨 agent 鏡像)與 [`CLAUDE.md`](CLAUDE.md)
(權威參考)裡;做非小改動之前請先讀那兩份。

### 使用者真正想要的

預設交付物是**每篇論文一份論文口試級的豐富 `.pptx`**,而不是 CLI 預設
產出的那種只有摘要的輕量投影片。輕量產出只是一個中間產物 —— 你的
工作就是把它升級。

### 決策樹

1. 環境裡有設 `ANTHROPIC_API_KEY` 嗎? → 直接跑 CLI 就好;它會透過
   Anthropic API 自動加值。你完成了。
2. 沒有金鑰,但你(一個 LLM)正在驅動這個 session → **你自己產出豐富
   摘要**。讀每一份 PDF,親手撰寫一份帶有豐富層欄位的 `PaperSummary`
   (`pain_points`、`research_question`、`contributions_detailed`、
   `headline_metrics`、`technique_table`、`method_sections`、
   `evaluation_sections`、`system_flow`、`research_questions`、
   `rq_results`、`core_observation`、`limitations`、`future_work`),
   放一支 `scripts/regen_<query>.py`,執行它。**不要叫使用者去設定 API
   金鑰** —— 你就是那個本來會寫出摘要的 LLM。
3. 迴圈裡沒有 LLM(CI / cron / 無人值守)→ 輕量版可以接受。

### 6 步 MCP 工作流程

```
1. (optional) list_sources()                              # see which plugins are enabled
2. search(keywords, sources, top_tier_only=true, ...)
3. (optional) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # per paper
5. (you read each PDF and produce a structured summary dict)
6. export(papers=[{...paper, "summary": {...}}], language="zh-tw", ...)
```

全部十三個 MCP 工具(包含 `list_sources`、`list_exports`、
`download_pdfs`、`pptx_inspect` / `pptx_review` / `pptx_update_slide` /
`pptx_add_slide` / 等等)都記載於 [`docs/mcp.md`](docs/mcp.md)。

### 必辦:出貨前先驗證 URL / DOI

出版商的 URL 路徑**猜不出來** —— AAAI 用數字 ID
(`v40i5.37389`)、IEEE 用一組不透明的 `arnumber`、ACM 用不透明的 DOI。
當你親手撰寫一個 `Paper` 時,**要從產生這次執行的那份搜尋 xlsx 逐字
複製 `url` / `doi` / `arxiv_id`** —— 絕不要憑記憶,也絕不要從標題湊出來。

那份 xlsx 會寫到 `exports/<run>/<slug>-<timestamp>.xlsx`,第 7 欄是
DOI、第 8 欄是 URL。完成時審核你的 regen 腳本:

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

在正式環境裡用這個方法抓到過兩起捏造:錯誤的 AAAI 卷號
(`v39i23.34521` vs 真實 `v39i22.34537`),以及發明出來的作者 slug 路徑
(`view/fang2026` 而非 `v40i5.37389`)。

### 必辦:出貨前先剔除不相關的下載

搜尋是以關鍵字比對的,所以離題論文一定會混進來:一次「Claude code」
查詢帶回了一篇 Viterbi 解碼器論文,因為兩者都含有「code」;
「LLM code review」比對到一篇物件偵測的文獻回顧。一旦你讀了摘要、
判定某篇論文對使用者的真正意圖離題,就從執行目錄剔除它:

```python
from pathlib import Path
run = Path("exports/<run>")
irrelevant_keys = ("key-of-off-topic-paper-1", "key-of-off-topic-paper-2")
for key in irrelevant_keys:
    for path in (run / "pdfs" / f"{key}.pdf", run / f"{key}.pptx"):
        if path.exists():
            path.unlink()
```

刪掉 `exports/<run>/pdfs/<key>.pdf` 與 `exports/<run>/<key>.pptx`。
**保留**彙總的 `<slug>-<timestamp>.xlsx` / `.bib` —— 那些是搜尋實際
回傳了什麼的誠實紀錄。邊界案例就給它一份豐富摘要;寧可多收也不要
默默漏掉一個可能的匹配。

### 實作範例

[`scripts/regen_fang2026.py`](scripts/regen_fang2026.py) 附了一份正是
以這種方式親手撰寫的豐富摘要(單篇論文、豐富層、zh-tw、每個豐富欄位
都填滿)。多篇論文的搜尋遵循同樣的形狀,在 `PaperCollection` tuple
裡每篇論文一個 `Paper(...summary=PaperSummary(...))` 條目。

### 不要做的事

- **不要**在多篇論文搜尋結束時告訴使用者「設 `ANTHROPIC_API_KEY` 就能
  得到豐富投影片」—— 你就是那個本來能寫出摘要的 LLM。
- **不要**把每篇論文的輕量 `.pptx` 當成交付物。
- **不要**在 `download_pdfs` 回報存了 N 份 PDF 後就停手 —— 那是豐富
  撰寫階段的開始,不是結束。
- **不要**發明論文裡沒有的數字、RQ、貢獻或限制。
- **不要**捏造 URL / DOI / arXiv ID —— 見上面的規則。
- **不要**把不相關的下載留在執行目錄裡。關鍵字搜尋的比對可能包含離題
  論文(一次「Claude code」查詢拉進了一篇 Viterbi 解碼器論文;
  「LLM code review」拉進了一篇物件偵測文獻回顧)。判定論文離題後,
  刪掉它們的 `pdfs/<key>.pdf` 與輕量 `<key>.pptx`;保留彙總 xlsx / bib
  作為搜尋實際回傳內容的誠實紀錄。
- **不要**在 commit 訊息、PR 描述、程式註解或文件裡提到「Claude」、
  「Claude Code」、「AI-generated」、「GPT」、「Copilot」或任何 AI 工具 /
  模型名稱。

## 功能特色

- **十五個可插拔來源**:`arxiv`、`semantic_scholar`、`openalex`、
  `pubmed`、`acm`(Crossref 範圍化)、`dblp`、`crossref`(未範圍化)、
  `openaire`、`springer`(需要 API 金鑰)、`europepmc`(開放、免金鑰 ——
  生命科學 + preprint + 農業)、`doaj`(開放、免金鑰 —— 開放取用期刊,
  通常帶直接 PDF 連結)、`hal`(開放、免金鑰 —— 法國的資工 / 數學 /
  物理典藏,附全文 PDF)、`core`(需要免費 API 金鑰 —— 最大的開放取用
  彙整站,2.5 億+ 件作品)、`ieee`(透過可見 Chrome 預設開啟;API 金鑰
  會加上官方 Xplore API)、`scholar`(透過可見 Chrome 預設開啟)。每個
  都住在 `sources/<name>/` 裡、藏在一個 `Fetcher` 轉接器後面。傳
  `--top-tier-only` 可把結果篩選到旗艦級資工會議 / 期刊外加
  Nature/Science/PNAS。預設搜尋保留所有場館。
- **單篇論文模式**:貼上一個 arXiv ID、arXiv URL、DOI、PMID 或 IEEE
  文件 URL —— ThesisAgents 會透過對應來源解析它,並輸出同一套匯出組合。
  對論文閱讀筆記與論文口試準備很有用。
- **本機 PDF 模式**(`--pdf <path>`):傳入一份 PDF 或一個目錄。一個
  啟發式擷取器會直接從每份 PDF 的前置頁抽出**標題、作者、年份、
  arXiv ID、DOI 與真正的摘要**(錨定在明確的 `Abstract` / `ABSTRACT` /
  `摘要` 標頭上,而非盲目截取前綴)。單一 PDF 呼叫時 `--title` /
  `--authors` / `--year` / `--venue` / `--doi` / `--arxiv-id` 會覆寫;
  對一個目錄則以每檔擷取為準,讓每篇論文都得到一份以其 BibTeX 鍵命名的
  投影片。
- **八個匯出器**:
  - `.pptx` —— 16:9 寬螢幕、有頁碼、三種渲染層級(只有摘要的輕量 ·
    加值扁平 · **論文口試級**,附痛點四象限、KPI 標註、技術比較表、
    每個 RQ 的結果表、貢獻摘要、核心觀察、限制與未來工作、Q&A、參考
    文獻)。所有模板字串都跨 **14 種語言**做了 i18n:English、繁體中文、
    简体中文、日本語、Español、Français、Deutsch、한국어、Português、
    Русский、Italiano、Tiếng Việt、हिन्दी、Bahasa Indonesia。
  - **設計過的投影片視覺識別**(不是預設的 Calibri-on-white 樣貌):
    依語言的字體(拉丁文用 Inter,CJK + 印地文用 Microsoft JhengHei
    UI / YaHei UI / Yu Gothic UI / Malgun Gothic / Nirmala UI)、
    程式化的裝飾幾何(每張內容頁頂端一條裝飾條 + 封面左側色帶)、
    學術風格的表格排版(拿掉預設格線、深藍表頭橫線、柔和的列間分隔、
    交替列底紋、垂直置中對齊、粗體列標籤),以及五色調色盤紀律
    (深藍 / 藍綠 / 灰 / 淺 / 白),文字**禁用**紅色(改用粗體 + 藍綠
    `#0E7490` 來強調)。
  - **淺色模式是預設的渲染路徑。** 傳 `--dark-mode`、在 GUI Deck 分頁
    啟用 **Dark mode**,或設 `ExportOptions(dark_mode=True)`,即可套用
    深色後製處理(投影片背景 `#12151B`、內文 `#E5E7EB`)。
  - `.xlsx` —— Papers 工作表 + Query 出處工作表、超連結的 URL / PDF、
    凍結表頭、自動欄寬。第 5 欄(**Source**)顯示真正的發表場館
    (例如「IEEE Access」);第 6 欄(**Indexed via**)顯示是哪個
    fetcher 回傳了 metadata(例如「openalex」),所以這兩項資訊絕不
    相撞。
  - `.md` —— 完整的來源 / 標題 / 摘要清單。
  - `.bib` —— 無碰撞的引用鍵、經 LaTeX 跳脫的欄位。
  - `.json` —— 給下游工具用的原始 payload。
  - `.ris` —— 由 Zotero / Mendeley / EndNote / RefWorks 匯入的 RIS
    交換格式(給非 LaTeX 參考文獻管理器用的 BibTeX 手足)。
  - `.csv` —— 給試算表 / 快速 grep 分類用的每篇論文一列的扁平表格
    (RFC-4180 引號規則,所以標題裡的逗號絕不會位移欄位)。
  - `.csl.json` —— 給 Pandoc / citeproc 用的 CSL-JSON;可以用任何 CSL
    樣式(APA、IEEE、Nature …)渲染參考文獻。`.csl.json` 副檔名讓它跟
    純 `.json` dump 有所區別。
- **PPT 編輯工具組**:`thesisagents.exporters.pptx_edit`
  (inspect / update_slide / delete_slide / reorder_slides / add_slide)
  可對匯出器產出的任何投影片運作,加上對應的 `pptx_*` MCP 工具,好讓
  一個 LLM agent 能在產出的投影片上反覆迭代。
- **MCP 伺服器**:13 個工具 —— `list_sources` + `list_exports`
  (探索)、`search`、`fetch_paper`、`fetch_pdf_text`、`download_pdfs`、
  `export`,以及六個 `pptx_*` 投影片工具(`inspect`、`review`、
  `update_slide`、`delete_slide`、`reorder_slides`、`add_slide`)。讓任何
  懂 MCP 的 LLM(Claude Code、Claude Desktop、Cursor …)驅動整個工作
  流程。
- **兩條加值路徑**,用來超越摘要、進入真正的論文口試級投影片:
  - **LLM-as-agent(免 API 金鑰)** —— 呼叫端 LLM 透過
    `fetch_pdf_text` 讀 PDF 本文,就地寫出一份結構化摘要,再傳給
    `export`。
  - **Python pipeline(`--enrich`)** —— CLI 自己呼叫 Anthropic 的 API;
    預設模型 `claude-opus-4-7`。
- **可見 Chrome 的出版商流程**:Scholar SERP、IEEE `/rest/search`,以及
  每一次付費牆 PDF 下載(ieeexplore / dl.acm / link.springer /
  sciencedirect / wiley / oup / nature / science / …)都在一個真實可見的
  Chrome session 裡透過 `selenium` 執行。使用者在那個實況視窗裡解一次
  captcha / 完成 SSO;`THESISAGENTS_CHROME_PROFILE_DIR` 會跨執行保存
  cookie。
- **LLM-as-agent 流程**:MCP 工具提供搜尋、PDF 下載與文字擷取。
  `scripts/regen_*.py` 內含可重現的範例,示範如何為每篇論文親手撰寫
  一份豐富的 `PaperSummary`。
- **OA PDF 解析器**:去重之後,每篇沒有 `pdf_url` 的論文都會走
  Unpaywall → S2 `openAccessPdf` → arXiv 標題搜尋 → CORE.ac.uk(在有設
  金鑰時)。在 IEEE / ACM / Springer / Elsevier 為主的查詢上典型的
  提升:40-70 個百分點。
- **預設就安全**:僅 HTTPS 的 HTTP 傳輸、每來源速率限制(token bucket)、
  對任何 XML payload 用 `defusedxml`、防路徑穿越的匯出路徑、不對
  使用者輸入用 `eval` / `exec` / `pickle`。
- **zh-tw / zh-cn 詞彙守衛**:`tests/test_i18n.py::test_zh_tw_files_use_traditional_chinese_vocabulary`
  裡約 244 條正規表達式會抓出用繁體漢字寫成的簡體中文外來詞
  (例如 `內存` → `記憶體`、`魯棒性` → `穩健性`、`軟件` → `軟體`、
  `緩存` → `快取`)。同一套守衛也反向地跑在 zh-cn 語系字串上。完整規則
  與正規表達式目錄住在
  `.claude/agents/rules/language-vocabulary-check.md`。

## 快速上手

```powershell
git clone <repo-url>
cd ThesisAgents
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Install with dev extras (also pulls in MCP SDK and intelligence deps)
pip install -e .[dev]
```

搜尋 arXiv 並匯出投影片 + 工作簿 + BibTeX(`--query` 的預設):

```powershell
py -m thesisagents --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

用 URL 抓單篇論文 —— 預設是 `.pptx + .bib`(對只有一列的資料,`.xlsx`
比較沒意義):

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

用繁體中文渲染投影片:

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --lang zh-tw --out .\exports\
```

LLM-pipeline 加值(Python 自己呼叫 Anthropic —— 需要 API 金鑰):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang zh-tw --out .\exports\
```

## CLI 旗標

| 旗標 | 用途 |
|---|---|
| `--query` / `-q` | 關鍵字(除非用 `--paper`,否則必填)。 |
| `--paper` / `-p` | arXiv ID / URL、DOI、PMID 或 IEEE 文件 URL。與 `--query` 互斥。 |
| `--source` / `-s` | 逗號分隔的來源清單。預設 `arxiv`。 |
| `--max` / `-n` | 每來源最多結果數(1..200)。預設 25。 |
| `--year-from` / `--year-to` | 含邊界的年份篩選。 |
| `--export` / `-e` | 格式:`pptx,xlsx,md,bib,json,ris,csv,csl` 之任意組合。預設依模式而定(見下)。 |
| `--out` / `-o` | 輸出目錄。預設 `./exports`。 |
| `--filename-stem` | 覆寫產生的檔名主幹。 |
| `--no-abstract` | 從匯出中省略摘要內容。 |
| `--lang` / `-l` | 投影片語言:14 種之一 —— `en`、`zh-tw`、`zh-cn`、`ja`、`es`、`fr`、`de`、`ko`、`pt`、`ru`、`it`、`vi`、`hi`、`id`。預設 `en`。 |
| `--enrich` | 自動加值的失敗即報變體。需要 `ANTHROPIC_API_KEY` 與 `[intelligence]` extra。(設了金鑰時自動加值是預設。) |
| `--lightweight` | 跳過加值 + 強制只有摘要的投影片。只用於快速 / 無人值守的執行;**當有 LLM agent 在驅動時,偏好下面的 LLM-as-agent 流程**。 |
| `--llm-model` | 覆寫加值用的預設 `claude-opus-4-7`。 |
| `--no-pdf` | 跳過自動 PDF 下載。也會停用每篇論文的 PPT 閘(沒 PDF → 沒完整內容)。 |
| `--no-oa-resolve` | 跳過去重後的 OA PDF 解析器(Unpaywall + S2 + arXiv + CORE.ac.uk)。 |
| `--top-tier-only` | 把結果限制到 arXiv + 一份精選的資工旗艦白名單(S&P、CCS、NDSS、USENIX Security、NeurIPS、ICML、ICSE …)。預設關閉。 |
| `--paywall-threshold` | 觸發確認提示的付費牆結果比例。預設 0.30。 |
| `--yes` | 跳過付費牆提示直接進行。 |
| `--max-slides` | 每篇論文的投影片上限(預設 25;傳 0 表示無上限)。 |
| `--dark-mode` | 以深色背景 + 近白文字渲染 pptx。預設是淺色深藍帶投影片。 |
| `--quiet` | 抑制每篇論文的列印輸出。 |

### 環境變數

| 變數 | 使用者 | 用途 |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | LLM 認證。走 MCP 的 LLM-as-agent 路徑不需要。 |
| `THESISAGENTS_LLM_MODEL` | `--enrich` | 覆寫預設的 `claude-opus-4-7`。 |
| `THESISAGENTS_S2_API_KEY` | Semantic Scholar + OA 解析器 | 更高的速率限制;也被 OA 解析器的 S2 `openAccessPdf` 步驟使用。免費金鑰在 <https://www.semanticscholar.org/product/api>。 |
| `THESISAGENTS_NCBI_API_KEY` | PubMed | 把 NCBI 的匿名限制(3/s)提高到 10/s。選用。 |
| `THESISAGENTS_CONTACT_EMAIL` | PubMed、ACM、Crossref、OpenAlex、**Unpaywall** | 禮貌池標記 + 啟用 OA 解析器的 Unpaywall 步驟(對 IEEE / ACM / Springer / Elsevier 付費牆論文的 PDF 覆蓋率提升最大;典型提升 40-70 pp)。 |
| `THESISAGENTS_IEEE_API_KEY` | IEEE(API 路徑) | 官方 IEEE Xplore API;為範圍內論文帶出 `pdf_url`。 |
| `THESISAGENTS_DISABLE_IEEE_SCRAPING` | IEEE | **IEEE 透過可見 Chrome 預設開啟。** 設 `=1` 可退出(例如沒有 Chrome 的 CI)。httpx 抓取分支只在 WebRunner 不可用時作為後備執行。 |
| `THESISAGENTS_CROSSREF_PLUS_TOKEN` | ACM、Crossref | Crossref Plus 訂閱者 token(Bearer 標頭)。選用。 |
| `THESISAGENTS_SPRINGER_API_KEY` | Springer | 必填;免費金鑰來自 <https://dev.springernature.com/>。沒有它外掛會丟 `ConfigError`。 |
| `THESISAGENTS_DISABLE_SCHOLAR_SCRAPING` | Google Scholar | **Scholar 透過可見 Chrome 預設開啟。** 設 `=1` 可退出(Google 的 ToS 禁止自動化存取 —— 為覆蓋率而預設開啟,退出以避免 captcha / IP 封鎖風險)。 |
| `THESISAGENTS_CHROME_PROFILE_DIR` | Scholar + IEEE + 付費牆 PDF 下載 | 持久的 Chrome `--user-data-dir`。設好它並完成一次 VPN / SSO / Google 登入;後續執行會繼承 cookie,讓 IEEE 回傳付費牆 metadata、Scholar 提供不被限流的 SERP。 |
| `THESISAGENTS_DISABLE_WEBRUNNER` | Scholar + IEEE + 付費牆 PDF 下載 | `=1` 強制走 httpx 路徑而非驅動真實 Chrome。對沒有 Chrome 二進位檔的 CI / Docker 有用;否則請保持不設。 |
| `THESISAGENTS_CORE_API_KEY` | OA 解析器 + `core` 搜尋來源 | 免費金鑰來自 <https://core.ac.uk/services/api>。啟用 CORE.ac.uk 的 OA 查找步驟(2 億+ 機構 / 區域 OA 項目)**以及** `core` 搜尋來源。沒有它,`core` 來源會被默默跳過,其他 OA 策略(Unpaywall、S2、arXiv)仍會執行。 |
| `THESISAGENTS_PDF_COOKIES_FILE` | PDF 下載器 | Netscape `cookies.txt`。預設關閉。只對你有機構權利的出版商使用。 |
| `THESISAGENTS_LOG_LEVEL` | logger | 預設 `INFO`;`DEBUG` 用於冗長追蹤。 |

預設:`--query` → `pptx,xlsx,bib`。`--paper` → `pptx,bib`。永遠可用明確的
`--export` 覆寫。

## LLM-as-agent 流程

當你編輯器裡的 LLM 在驅動這個工作流程時,依序使用 MCP 工具:
`search`、`download_pdfs`、`fetch_pdf_text`,然後用一份親手撰寫的豐富
`PaperSummary` 呼叫 `export`。既有的 `scripts/regen_*.py` 檔案就是最終
撰寫與匯出步驟的可重現範例。

完整的端到端執行手冊(搜尋 → 豐富投影片)住在
`.claude/agents/tasks/paper-summary-author.md` —— 開一個新查詢前先打開它,
好讓 LLM 能執行整個流程而不必停下來等使用者輸入。

## MCP 伺服器

向 Claude Code 註冊:

```powershell
claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp
```

或寫進你的設定檔:

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
| `list_sources` | 列舉每個外掛 + 回報各自在目前環境下是否啟用。在 `search` 前呼叫一次。 |
| `list_exports` | 列舉每種匯出格式,附一行描述,並說明它寫一個彙總檔還是每篇論文一檔。 |
| `search` | 關鍵字 → 論文清單。接受 `top_tier_only`、`min_citations`;預設走完整的免 API 金鑰來源組合。 |
| `fetch_paper` | arXiv / DOI / PMID / IEEE 識別碼 → 單篇論文。 |
| `fetch_pdf_text` | 下載一份 PDF,回傳擷取出的本文文字。**這是「我讀了論文」的 MCP 路徑。** |
| `download_pdfs` | 批次把一份論文清單的 PDF 下載到 `{out_dir}/pdfs/`。回傳以 BibTeX 鍵為索引的每篇論文結果。 |
| `export` | 論文清單 + 格式 → 寫出 `.pptx/.xlsx/.md/.bib/.json/.ris/.csv/.csl.json`。每篇論文可接受一個 `summary` 欄位,用於豐富論文口試級 schema、`max_slides_per_paper`(預設 25)與 `dark_mode`(預設 `false` —— 專案預設是淺色深藍帶投影片,傳 `true` 走深色 OLED / 低光後製)。 |
| `pptx_inspect` | 讀取既有投影片的 slide / shape 結構。 |
| `pptx_review` | 一次呼叫審核一份投影片 —— 溢位 + 顏色契約 + `paper_rule` 章節完整度。自動偵測投影片語言;也是 CLI `python -m thesisagents review <deck.pptx>`。 |
| `pptx_update_slide` | 替換 `title` / `body` / `meta`(依 shape 名稱)或依索引替換任意 shape。 |
| `pptx_delete_slide` | 移除一張投影片與它的 part 關係。 |
| `pptx_reorder_slides` | 透過 `sldIdLst` 重排投影片。 |
| `pptx_add_slide` | 附加或插入一張新的 title / body / meta 投影片。 |

LLM-as-agent 流程(不需要 `ANTHROPIC_API_KEY` —— LLM 就是那個 agent):

```
1. (optional) list_sources()                       # discover enabled plugins
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (optional) download_pdfs(papers, out_dir="./exports/...")  # persist PDFs
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # per paper
5. (the LLM reads body text, produces a structured `summary` dict)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="zh-tw", formats=["pptx","bib"], dark_mode=true, ...)
```

完整參考在 [`docs/mcp.md`](docs/mcp.md)。

## 專案結構

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

## 完成定義(Definition of Done)

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r thesisagents/
```

bandit 上的 `-c` 旗標是必要的 —— 沒有它 bandit 會忽略專案的 skip 設定。
碰到 pptx 匯出器時,也要跑一次溢位檢查(見 `CLAUDE.md`「Slide Deck
Rules」)。

## 桌面 GUI(PySide6)

一個原生桌面介面藏在 `[gui]` extra 後面出貨:

```powershell
pip install thesisagents[gui]
thesisagents-gui                 # or: thesisagents gui
```

視窗有四個分頁 —— **Search**、**Settings**(透過 QSettings 保存 API
金鑰)、**Enrich**(透過一個 `collection_ready` 訊號驅動 LLM-as-agent /
Python-pipeline 加值),以及 **Deck**(淺色模式切換 + 投影片上限 +
最大圖數控制項會流向 `ExportOptions`)。Windows 發行版 zip 出貨的是
Nuitka 編譯的套件,已含 PySide6,所以 `thesisagents.exe gui` 不必另外
裝 Python 就能運作。
**UI 以全部 14 種語言出貨**(English、繁體中文、简体中文、日本語、
Español、Français、Deutsch、한국어、Português、Русский、Italiano、
Tiếng Việt、हिन्दी、Bahasa Indonesia)—— 首次執行會從你的 OS 語系挑選
語言,之後 **Settings → Interface language** 讓你更改它。投影片輸出語言
是一個獨立的下拉選單,所以你可以用一種語言跑 UI、用另一種語言產出
投影片。版面是響應式的:每個表單都坐在一個 `QScrollArea` 裡,視窗可以
縮小到 900×600(仍容得下 720p),並預設開啟 HiDPI 縮放。

完整參考:[`docs/gui.md`](docs/gui.md)。

## 打包成獨立執行檔

記載了兩個打包器,用來出貨一個不必安裝 Python 就能跑的單檔二進位檔:

- **[`docs/packaging-pyinstaller.md`](docs/packaging-pyinstaller.md)**
  —— 快速建置(不到一分鐘)、輸出 200–300 MB、啟動 2–4 秒。當你在
  迭代建置腳本時最合適。
- **[`docs/packaging-nuitka.md`](docs/packaging-nuitka.md)** ——
  緩慢建置(5–15 分鐘)、輸出 80–150 MB、次秒級啟動,帶一些位元碼
  保護。當終端使用者會多次執行二進位檔時最合適。

兩份文件都涵蓋了專案特有的陷阱 —— `sources/<name>/` 下的動態來源
外掛 —— 並附上一個經驗證、涵蓋 CLI 與 MCP 伺服器進入點的指令。

## 持續整合與發行

`.github/workflows/` 下住著兩個 GitHub Actions 工作流程:

- **`ci.yml`** 在每次推送與對 `main` 的 PR 上執行。矩陣是 Ubuntu +
  Windows × Python 3.12 / 3.13 / 3.14(6 個 job)。每個 job 跑
  `ruff check`、`bandit -c pyproject.toml` 與 `pytest`。
- **`release.yml`** 等待 `ci.yml` 在 `main` 上完成(`workflow_run`
  觸發)。它只在 CI 成功時執行。**每一次 CI 成功推送到 `main` 都是一次
  發行** —— 工作流程會自動升 `pyproject.toml` 的 patch 版本、把版本升號
  以 `chore: bump version to X.Y.Z` commit 回 `main`,並進行流水線:
  1. **`bump-version`** —— 從 `pyproject.toml` 讀出目前的 `X.Y.Z`,
     遞增到 `X.Y.(Z+1)`,用工作流程的 `GITHUB_TOKEN` commit + push 回
     `main`。那次推送**不會**重新觸發 CI(依 GitHub 規則,
     `GITHUB_TOKEN` 驅動的推送無法啟動新的 workflow run),所以這個
     循環會自然終止。
  2. **`publish-pypi`** —— 建置 sdist + wheel、`twine check`、透過
     `PYPI_API_TOKEN` `twine upload`。
  3. **`create-draft-release`** —— 在 tag `v<version>` 開一個*草稿*
     GitHub release,附自動產生的說明。
  4. **`build-nuitka`** —— 在一個 Windows runner 上編譯一個 Nuitka
     standalone 套件(進入點:透過 `--python-flag=-m` 的
     `python -m thesisagents`)、煙霧測試它、把產出的
     `thesisagents.dist/` 資料夾打包成 zip,並把 zip + 一個 `.sha256`
     校驗碼附到草稿 release。刻意設計成 standalone(不是 onefile):
     onefile 每次啟動都會自解壓到 `%TEMP%`,增加啟動延遲並在鎖死的
     機器上觸發防毒啟發式。也刻意只支援 Windows:Linux / macOS 使用者
     從 PyPI 安裝。以 `pyproject.toml` 為鍵的建置快取把暖建置從約 70 分
     冷建置削減到約 5–10 分。
  5. **`publish-release`** —— 一旦 Nuitka 資產上傳完成就取消草稿標記,
     讓使用者永遠不會看到一個做到一半的 release。

  **跳過一次發行。** 在 commit 訊息任何地方包含 `[skip release]`,升號
  加上每個下游 job 都會被跳過 —— 對不該燒掉一個版本號的純文件 / 錯字 /
  重構 commit 使用它。

要啟用 PyPI 發布 + 發行執行檔:

1. 在 <https://pypi.org/manage/account/token/> 產生一個專案範圍的 API
   token。
2. 在 GitHub repo 裡:`Settings → Secrets and variables → Actions →
   New repository secret`。命名為 `PYPI_API_TOKEN` 並貼上 token 值。
3. 允許 GitHub Actions 推送到 `main`:`Settings → Actions →
   General → Workflow permissions → Read and write permissions`。升號
   commit 由工作流程的 `GITHUB_TOKEN` 推送。
4. 透過把 PR 併入 `main` 來發行。流水線需要約 3–5 分鐘發布到 PyPI,再
   約 50–70 分鐘(冷)或約 5–10 分鐘(暖 Nuitka 快取)讓 Windows zip
   附上。

`publish-pypi` job 刻意**不**附加一個 GitHub Environment,所以每次執行
都以 Release 條目(附它的 Nuitka `.exe`)呈現,而非以 repo 首頁上的
「Deployment」側邊欄小工具呈現 —— release 有自己專屬的頁面,上頭再加一個
Deployment 條目只會是多餘的雜訊。

## 授權

見 `LICENSE`。arXiv API 依 arXiv 的 API 使用條款
(<https://info.arxiv.org/help/api/tou.html>)使用 —— 遵守每 3 秒 1 次
請求的軟性限制;隨附的 fetcher 已透過它的 token bucket 強制此限制。
