# AutoPaperToPPT

[![CI](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![Python](https://img.shields.io/pypi/pyversions/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/AutoPaperToPPT.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/autopapertoppt/badge/?version=latest)](https://autopapertoppt.readthedocs.io/en/latest/)

> **Ngôn ngữ**: [English](README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · **Tiếng Việt** · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **Tài liệu**: [autopapertoppt.readthedocs.io](https://autopapertoppt.readthedocs.io/en/latest/)

Trợ lý tìm kiếm bài báo theo từ khóa. Lấy kết quả từ arXiv, Semantic Scholar, OpenAlex, PubMed, ACM (qua Crossref), IEEE Xplore, DBLP, Crossref tổng quát, OpenAIRE, Springer Nature và Google Scholar; chuẩn hóa về một định dạng bản ghi duy nhất; và xuất tập đã khử trùng lặp thành **slide PowerPoint phong cách luận văn**, **sổ Excel** và **tệp BibTeX** — tất cả từ một lệnh CLI hoặc một lời gọi công cụ MCP. Có thể làm giàu mỗi bài báo bằng cách đọc PDF và tạo bản tóm tắt có cấu trúc, ngay trong ngữ cảnh (luồng LLM-as-agent) hoặc qua API Anthropic (luồng Python pipeline).

## Dành cho AI agent điều khiển dự án này

**Nếu bạn là một LLM (Claude Code, Cursor, Aider, Codex CLI, …) đang đọc README này để hiểu cần làm gì — bắt đầu từ đây.** Cùng các quy tắc đó cũng được ghim trong [`AGENTS.md`](AGENTS.md) (bản phản chiếu cho mọi agent) và [`CLAUDE.md`](CLAUDE.md) (tham chiếu chính thức); hãy đọc chúng trước khi thay đổi đáng kể.

### Điều người dùng thực sự muốn

Sản phẩm mặc định là **một `.pptx` phong cách luận văn, đầy đủ cho mỗi bài**, không phải bản deck nhẹ chỉ-tóm-tắt mà CLI sinh mặc định. Bản nhẹ là tạo phẩm trung gian — nhiệm vụ của bạn là nâng cấp nó.

### Cây quyết định

1. Biến môi trường `ANTHROPIC_API_KEY` đã đặt chưa? → chạy CLI; nó tự làm giàu qua API Anthropic. Xong.
2. Không có key, nhưng bạn (LLM) đang điều khiển phiên → **bạn tự viết bản tóm tắt đầy đủ**. Đọc từng PDF, soạn tay `PaperSummary` với các trường rich-tier (`pain_points`, `research_question`, `contributions_detailed`, `headline_metrics`, `technique_table`, `method_sections`, `evaluation_sections`, `system_flow`, `research_questions`, `rq_results`, `core_observation`, `limitations`, `future_work`), đặt một `scripts/regen_<query>.py` và chạy nó. **Đừng bảo người dùng đặt API key** — bạn chính là LLM lẽ ra phải viết tóm tắt.
3. Không có LLM trong vòng lặp (CI / cron / không người trông coi) → bản nhẹ chấp nhận được.

### Quy trình MCP 6 bước

```
1. (tùy chọn) list_sources()                              # plugin nào đang bật
2. search(keywords, sources, top_tier_only=true, ...)
3. (tùy chọn) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # cho từng bài
5. (bạn đọc từng PDF và tạo dict tóm tắt có cấu trúc)
6. export(papers=[{...paper, "summary": {...}}], language="vi", ...)
```

Mười một công cụ MCP (gồm `list_sources`, `download_pdfs`, `pptx_inspect` / `pptx_update_slide` / `pptx_add_slide` v.v.) được tài liệu hóa tại [`docs/mcp.md`](docs/mcp.md).

### Bắt buộc: xác minh URL / DOI trước khi giao

Đường dẫn URL của nhà xuất bản **không thể đoán** — AAAI dùng ID số (`v40i5.37389`), IEEE dùng `arnumber` mờ, ACM dùng DOI mờ. Khi tự tay tạo `Paper`, **sao chép `url` / `doi` / `arxiv_id` đúng nguyên văn từ xlsx do lần tìm kiếm này tạo ra** — không bao giờ nhớ từ trí nhớ, không bao giờ ghép từ tiêu đề.

xlsx được ghi vào `exports/<run>/<slug>-<timestamp>.xlsx` với cột 7 = DOI, cột 8 = URL. Kiểm toán regen script sau khi chạy xong:

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

Hai trường hợp ngụy tạo bị bắt theo cách này trong sản xuất: sai tập AAAI (`v39i23.34521` so với thực tế `v39i22.34537`) và đường dẫn slug tác giả tự bịa (`view/fang2026` thay vì `v40i5.37389`).

### Ví dụ thực tế

[`scripts/regen_llm_security_batch.py`](scripts/regen_llm_security_batch.py) chứa 8 bản tóm tắt rich được soạn tay đúng theo quy trình này. Dùng làm template cho mọi tìm kiếm đa-bài. Phiên bản zh-tw tại [`scripts/regen_llm_security_batch_zh_tw.py`](scripts/regen_llm_security_batch_zh_tw.py).

### Cấm

- **Đừng** kết thúc tìm kiếm đa-bài bằng cách nói với người dùng "đặt `ANTHROPIC_API_KEY` để có deck đầy đủ" — bạn chính là LLM lẽ ra viết tóm tắt.
- **Đừng** coi `.pptx` nhẹ từng bài là sản phẩm bàn giao.
- **Đừng** dừng khi `download_pdfs` báo "đã lưu N PDF" — đó là bắt đầu giai đoạn viết, không phải kết thúc.
- **Đừng** bịa số, RQ, đóng góp hoặc hạn chế không có trong bài.
- **Đừng** ngụy tạo URL / DOI / arXiv ID — xem quy tắc trên.
- **Đừng** để các tải xuống không liên quan trong thư mục chạy. Tìm kiếm theo từ khóa đôi khi đưa vào các bài báo lạc đề (truy vấn "Claude code" đã đưa vào bài về bộ giải mã Viterbi; "LLM code review" đưa vào bài tổng quan về phát hiện đối tượng). Sau khi phân loại lạc đề, hãy xóa `pdfs/<key>.pdf` và `<key>.pptx` nhẹ của nó; giữ lại xlsx / bib tổng hợp như bản ghi trung thực về những gì tìm kiếm trả về.
- **Đừng** đề cập "Claude", "Claude Code", "AI-generated", "GPT", "Copilot" hoặc bất kỳ tên công cụ/mô hình AI nào trong commit message, mô tả PR, comment code hoặc tài liệu.

## Tính năng

- **Mười một nguồn cắm-ngoài**: `arxiv`, `semantic_scholar`, `openalex`, `pubmed`, `acm` (giới hạn ACM qua Crossref), `dblp`, `crossref` (tổng quát), `openaire`, `springer` (cần API key), `ieee` (API key hoặc opt-in scraping), `scholar` (opt-in scraping). Mỗi nguồn nằm dưới `sources/<name>/` sau adapter `Fetcher`. Danh sách trắng venue top-tier lọc kết quả về các hội nghị/tạp chí CS chủ lực + Nature/Science/PNAS mặc định; `--all-venues` tắt nó.
- **Chế độ bài đơn**: dán arXiv ID, URL arXiv, DOI, PMID hoặc URL tài liệu IEEE — AutoPaperToPPT giải qua nguồn đúng và phát ra cùng gói xuất. Hữu ích cho ghi chú đọc và chuẩn bị bảo vệ.
- **Chế độ PDF nội bộ** (`--pdf <đường-dẫn>`): truyền một PDF hoặc thư mục. Bộ trích heuristic lấy **tiêu đề, tác giả, năm, arXiv ID, DOI và tóm tắt thật** ngay từ đầu mỗi PDF (neo vào tiêu đề rõ ràng `Abstract` / `ABSTRACT` / `摘要`, không phải tiền tố mù). `--title` / `--authors` / `--year` / `--venue` / `--doi` / `--arxiv-id` ghi đè khi gọi một PDF; với thư mục, trích xuất từng file thắng — mỗi bài có deck riêng tên theo khóa BibTeX của nó.
- **Năm exporter**:
  - `.pptx` — màn rộng 16:9, đánh số trang, ba mức render (nhẹ chỉ-tóm-tắt · enriched-flat · **phong cách luận văn** với góc tư điểm đau, KPI nổi bật, bảng so sánh kỹ thuật, bảng kết quả theo RQ, tổng kết đóng góp, quan sát cốt lõi, hạn chế & công việc tương lai, Q&A, tài liệu tham khảo). Mọi chuỗi template được i18n trên **14 ngôn ngữ**: English, 繁體中文, 简体中文, 日本語, Español, Français, Deutsch, 한국어, Português, Русский, Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia.
  - `.xlsx` — sheet Papers + sheet Query nguồn gốc, URL / PDF có hyperlink, header cố định, độ rộng cột tự động. Cột 5 (**Source**) hiển thị nơi xuất bản thực (ví dụ "IEEE Access"); cột 6 (**Indexed via**) cho biết fetcher nào trả metadata (ví dụ "openalex"), tránh nhầm lẫn hai thông tin.
  - `.md` — danh sách đầy đủ nguồn / tiêu đề / tóm tắt.
  - `.bib` — khóa trích dẫn không xung đột, các trường đã escape LaTeX.
  - `.json` — payload thô cho công cụ downstream.
- **Bộ chỉnh sửa PPT**: `autopapertoppt.exporters.pptx_edit` (inspect / update_slide / delete_slide / reorder_slides / add_slide) làm việc với bất kỳ deck nào exporter sinh ra, cộng với các công cụ MCP `pptx_*` tương đương để LLM agent lặp trên deck đã sinh.
- **Server MCP**: 11 công cụ — `list_sources` (khám phá), `search`, `fetch_paper`, `fetch_pdf_text`, `download_pdfs`, `export` và năm công cụ chỉnh sửa `pptx_*`. Cho phép bất kỳ LLM tương thích MCP (Claude Code, Claude Desktop, Cursor, …) điều khiển toàn bộ workflow.
- **Hai lối làm giàu** để vượt qua tóm tắt đến deck phong cách luận văn thực sự:
  - **LLM-as-agent (không cần API key)** — LLM gọi đọc văn bản PDF qua `fetch_pdf_text`, viết tóm tắt có cấu trúc trong ngữ cảnh và truyền cho `export`.
  - **Pipeline Python (`--enrich`)** — CLI tự gọi API Anthropic; mô hình mặc định `claude-opus-4-7`.
- **An toàn theo mặc định**: transport HTTP chỉ-HTTPS, rate limit từng nguồn (token bucket), `defusedxml` cho mọi payload XML, đường xuất tránh path-traversal, không `eval` / `exec` / `pickle` trên input người dùng. Scraping Scholar và IEEE tắt mặc định (opt-in qua env var).

## Bắt đầu nhanh

```powershell
git clone <repo-url>
cd AutoPaperToPPT
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Cài kèm dev extras (kéo theo cả MCP SDK và intelligence deps)
pip install -e .[dev]
```

Tìm arXiv và xuất deck + workbook + BibTeX (mặc định cho `--query`):

```powershell
py -m autopapertoppt --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

Lấy một bài theo URL — mặc định `.pptx + .bib` (`.xlsx` một hàng ít ý nghĩa):

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

Render deck bằng tiếng Việt:

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --lang vi --out .\exports\
```

Làm giàu qua LLM pipeline (Python gọi Anthropic — cần API key):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang vi --out .\exports\
```

## Cờ CLI

| Cờ | Mục đích |
|---|---|
| `--query` / `-q` | Từ khóa (bắt buộc trừ khi có `--paper`). |
| `--paper` / `-p` | arXiv ID/URL, DOI, PMID hoặc URL tài liệu IEEE. Loại trừ với `--query`. |
| `--source` / `-s` | Danh sách nguồn phân cách dấu phẩy. Mặc định `arxiv`. |
| `--max` / `-n` | Số kết quả tối đa mỗi nguồn (1..200). Mặc định 25. |
| `--year-from` / `--year-to` | Bộ lọc năm bao gồm. |
| `--export` / `-e` | Định dạng: tổ hợp bất kỳ của `pptx,xlsx,md,bib,json`. Mặc định tùy chế độ (xem dưới). |
| `--out` / `-o` | Thư mục đầu ra. Mặc định `./exports`. |
| `--filename-stem` | Ghi đè stem tên file tự sinh. |
| `--no-abstract` | Bỏ nội dung tóm tắt khỏi xuất. |
| `--lang` / `-l` | Ngôn ngữ deck: một trong 14 — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. Mặc định `en`. |
| `--enrich` | Tải PDF + tóm tắt Anthropic. Cần `ANTHROPIC_API_KEY` và extra `[intelligence]`. |
| `--lightweight` | Buộc deck nhẹ kể cả khi `ANTHROPIC_API_KEY` đã đặt. |
| `--llm-model` | Ghi đè mô hình mặc định `claude-opus-4-7`. |
| `--all-venues` | Tắt danh sách trắng top-tier (mặc định giữ venue CS chủ lực + Nature / Science / PNAS / CACM / LNCS). |
| `--paywall-threshold` | Tỉ lệ kết quả có paywall kích hoạt prompt xác nhận. Mặc định 0.30. |
| `--yes` | Bỏ qua prompt paywall. |
| `--max-slides` | Giới hạn slide mỗi bài (mặc định 25; 0 = không giới hạn). |
| `--quiet` | Tắt in từng bài. |

### Biến môi trường

| Biến | Dùng bởi | Mục đích |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | Xác thực LLM. Không cần cho LLM-as-agent qua MCP. |
| `AUTOPAPERTOPPT_LLM_MODEL` | `--enrich` | Ghi đè mặc định `claude-opus-4-7`. |
| `AUTOPAPERTOPPT_S2_API_KEY` | Semantic Scholar | Rate limit cao hơn. Tùy chọn. |
| `AUTOPAPERTOPPT_NCBI_API_KEY` | PubMed | Nâng giới hạn ẩn danh NCBI (3/s) lên 10/s. Tùy chọn. |
| `AUTOPAPERTOPPT_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex | Đưa request vào polite pool của Crossref. |
| `AUTOPAPERTOPPT_IEEE_API_KEY` | IEEE (đường API) | API chính thức IEEE Xplore; phơi `pdf_url` cho bài thuộc phạm vi đăng ký. |
| `AUTOPAPERTOPPT_ENABLE_IEEE_SCRAPING` | IEEE (đường scraping) | `=1` bật scraping. Không cần khi đã có API key. |
| `AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Token thuê bao Crossref Plus (header Bearer). Tùy chọn. |
| `AUTOPAPERTOPPT_SPRINGER_API_KEY` | Springer | Bắt buộc; key miễn phí tại <https://dev.springernature.com/>. Plugin bị bỏ qua âm thầm nếu thiếu. |
| `AUTOPAPERTOPPT_ENABLE_SCHOLAR_SCRAPING` | Google Scholar | `=1` bật scraping. Mặc định tắt — ToS Scholar cấm scraping. |
| `AUTOPAPERTOPPT_PDF_COOKIES_FILE` | Trình tải PDF | `cookies.txt` định dạng Netscape. Mặc định tắt. Chỉ dùng với nhà xuất bản bạn có quyền truy cập tổ chức. |
| `AUTOPAPERTOPPT_LOG_LEVEL` | logger | Mặc định `INFO`; `DEBUG` cho trace chi tiết. |

Mặc định: `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. Luôn có thể ghi đè bằng `--export` rõ ràng.

## Server MCP

Đăng ký với Claude Code:

```powershell
claude mcp add autopapertoppt -- ".venv\Scripts\python.exe" -m autopapertoppt.mcp
```

Hoặc sửa file settings:

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

Công cụ:

| Công cụ | Mục đích |
|---|---|
| `list_sources` | Liệt kê mọi plugin + báo cái nào đang bật trong env hiện tại. Gọi một lần trước `search`. |
| `search` | Từ khóa → danh sách bài. Nhận `top_tier_only`, `min_citations`; mặc định dùng đầy đủ nguồn không cần API key. |
| `fetch_paper` | Định danh arXiv / DOI / PMID / IEEE → một bài. |
| `fetch_pdf_text` | Tải một PDF, trả về văn bản đã trích. **Cổng MCP để "tôi đã đọc bài".** |
| `download_pdfs` | Tải hàng loạt PDF của danh sách bài vào `{out_dir}/pdfs/`. Trả về kết quả từng bài có khóa BibTeX. |
| `export` | Danh sách bài + định dạng → ghi `.pptx/.xlsx/.md/.bib/.json`. Nhận `summary` mỗi bài (schema phong cách luận văn) và `max_slides_per_paper` (mặc định 25). |
| `pptx_inspect` | Đọc cấu trúc slide / shape của deck hiện có. |
| `pptx_update_slide` | Thay `title` / `body` / `meta` (theo tên shape) hoặc shape bất kỳ theo index. |
| `pptx_delete_slide` | Xóa một slide và part relationship của nó. |
| `pptx_reorder_slides` | Đảo thứ tự slide qua `sldIdLst`. |
| `pptx_add_slide` | Thêm cuối hoặc chèn tại vị trí slide title / body / meta mới. |

Luồng LLM-as-agent (không cần `ANTHROPIC_API_KEY` — LLM chính là agent):

```
1. (tùy chọn) list_sources()                       # khám phá plugin đang bật
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (tùy chọn) download_pdfs(papers, out_dir="./exports/...")  # lưu PDF
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # mỗi bài
5. (LLM đọc văn bản, tạo dict `summary` có cấu trúc)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="vi", formats=["pptx","bib"], ...)
```

Tham chiếu đầy đủ tại [`docs/mcp.md`](docs/mcp.md).

## Bố cục dự án

```
AutoPaperToPPT/
├── autopapertoppt/                 # gói chính
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # client async chỉ-HTTPS, rate limit token bucket
│   ├── exporters/                   # pptx (phong cách luận văn) · xlsx · bib · md · json · pptx_edit · i18n
│   ├── intelligence/                # tải PDF + bộ tóm tắt Anthropic ([intelligence] extra)
│   ├── mcp/                         # server FastMCP (11 công cụ)
│   ├── utils/                       # logging, path safety
│   ├── cli.py                       # CLI argparse
│   └── __main__.py
├── sources/                         # thư mục plugin: arxiv, semantic_scholar,
│                                    #   openalex, pubmed, acm, ieee, scholar,
│                                    #   dblp, crossref, openaire, springer
├── tests/                           # bộ pytest + fixture đã ghi (không HTTP trực tiếp)
├── docs/                            # Sphinx (14 cây ngôn ngữ)
├── scripts/                         # script regen dùng một lần
└── pyproject.toml                   # ruff, bandit, build, extras tùy chọn
```

## Definition of Done

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r autopapertoppt/ sources/
```

Cờ `-c` của bandit là bắt buộc — không có nó, bandit bỏ qua cấu hình skip của dự án. Khi đụng đến exporter pptx, hãy chạy thêm kiểm tra overflow (xem `CLAUDE.md` "Slide Deck Rules").

## Giấy phép

Xem `LICENSE`. API arXiv được dùng theo điều khoản (<https://info.arxiv.org/help/api/tou.html>) — tuân thủ giới hạn mềm 1 request mỗi 3 giây; fetcher tích hợp đã ép tỉ lệ này qua token bucket.
