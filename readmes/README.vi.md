# ThesisAgents

[![CI](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![Python](https://img.shields.io/pypi/pyversions/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/ThesisAgents.svg)](https://github.com/Integration-Automation/ThesisAgents/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/thesisagents/badge/?version=latest)](https://thesisagents.readthedocs.io/en/latest/)

> **Ngôn ngữ**: [English](../README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · **Tiếng Việt** · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **Tài liệu**: [thesisagents.readthedocs.io](https://thesisagents.readthedocs.io/en/latest/)

Trợ lý tìm kiếm bài báo theo từ khóa. Lấy kết quả từ arXiv,
Semantic Scholar, OpenAlex, PubMed, ACM (qua Crossref), IEEE Xplore,
DBLP, Crossref tổng quát, OpenAIRE, Springer Nature, Europe PMC, DOAJ,
HAL, CORE và Google Scholar,
chuẩn hóa chúng về một định dạng bản ghi duy nhất, và xuất tập đã khử
trùng lặp thành **slide PowerPoint phong cách luận văn**, một **sổ Excel** và một
**tệp BibTeX** — tất cả từ một lời gọi CLI hoặc một lời gọi công cụ MCP.
Tùy chọn làm giàu mỗi bài báo bằng cách đọc PDF của nó và tạo một bản
tóm tắt có cấu trúc cho từng bài, hoặc ngay trong ngữ cảnh (luồng
LLM-as-agent) hoặc qua API Anthropic (luồng Python pipeline).

## Dành cho AI agent điều khiển dự án này

**Nếu bạn là một LLM (Claude Code, Cursor, Aider, Codex CLI, …) đang đọc
README này để tìm hiểu cần làm gì — hãy bắt đầu từ đây.** Mọi thứ bên dưới
cũng được ghim trong [`AGENTS.md`](AGENTS.md) (bản phản chiếu cho mọi agent) và
[`CLAUDE.md`](CLAUDE.md) (tham chiếu chính thức); hãy đọc chúng trước khi
thực hiện các thay đổi không tầm thường.

### Điều người dùng thực sự muốn

Sản phẩm bàn giao mặc định là **một `.pptx` phong cách luận văn đầy đủ cho
mỗi bài báo**, không phải bản deck nhẹ chỉ-có-tóm-tắt mà CLI sinh ra theo
mặc định. Bản phát ra nhẹ là một tạo phẩm trung gian — công việc của bạn là
nâng cấp nó.

### Cây quyết định

1. Biến `ANTHROPIC_API_KEY` có được đặt trong môi trường không? → cứ chạy CLI;
   nó tự động làm giàu qua API Anthropic. Bạn đã xong.
2. Không có key, nhưng bạn (một LLM) đang điều khiển phiên → **bạn tự tạo
   bản tóm tắt đầy đủ**. Đọc từng PDF, soạn tay một
   `PaperSummary` với các trường rich-tier (`pain_points`,
   `research_question`, `contributions_detailed`, `headline_metrics`,
   `technique_table`, `method_sections`, `evaluation_sections`,
   `system_flow`, `research_questions`, `rq_results`,
   `core_observation`, `limitations`, `future_work`), đặt một
   `scripts/regen_<query>.py` và chạy nó. **Đừng bảo người dùng đặt
   API key** — bạn chính là LLM lẽ ra đã viết
   bản tóm tắt.
3. Không có LLM trong vòng lặp (CI / cron / không người trông coi) → bản nhẹ
   là chấp nhận được.

### Quy trình MCP 6 bước

```
1. (tùy chọn) list_sources()                              # xem plugin nào đang bật
2. search(keywords, sources, top_tier_only=true, ...)
3. (tùy chọn) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # cho mỗi bài
5. (bạn đọc từng PDF và tạo một dict tóm tắt có cấu trúc)
6. export(papers=[{...paper, "summary": {...}}], language="zh-tw", ...)
```

Cả mười ba công cụ MCP (gồm `list_sources`, `list_exports`,
`download_pdfs`, `pptx_inspect` / `pptx_review` / `pptx_update_slide` /
`pptx_add_slide` / v.v.) đều được
tài liệu hóa trong [`docs/mcp.md`](docs/mcp.md).

### Bắt buộc: xác minh URL / DOI trước khi giao

Đường dẫn URL của nhà xuất bản **không thể đoán được** — AAAI dùng ID số
(`v40i5.37389`), IEEE dùng một `arnumber` mờ, ACM dùng các DOI mờ.
Khi bạn tự tay soạn một `Paper`, **hãy sao chép `url` / `doi` / `arxiv_id`
đúng nguyên văn từ xlsx tìm kiếm đã sinh ra lần chạy này** — không bao giờ
từ trí nhớ, không bao giờ ghép từ tiêu đề.

xlsx được ghi vào `exports/<run>/<slug>-<timestamp>.xlsx` với
cột 7 = DOI, cột 8 = URL. Hãy kiểm toán regen script của bạn khi
hoàn tất:

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

Hai vụ ngụy tạo bị bắt theo cách này trong môi trường sản xuất: sai tập
AAAI (`v39i23.34521` so với thực tế `v39i22.34537`) và đường dẫn slug tác
giả tự bịa (`view/fang2026` thay vì `v40i5.37389`).

### Bắt buộc: loại bỏ các tải xuống không liên quan trước khi giao

Việc so khớp từ khóa tìm kiếm dựa trên từ khóa, nên các bài lạc đề sẽ
lọt vào: một truy vấn "Claude code" đã trả về một bài về bộ giải mã
Viterbi vì cả hai đều chứa "code"; "LLM code review" đã khớp một bài
tổng quan tài liệu về phát hiện đối tượng. Một khi bạn đã đọc các tóm tắt
và phân loại một bài là lạc đề so với ý định thực sự của người dùng, hãy
dọn thư mục chạy:

```python
from pathlib import Path
run = Path("exports/<run>")
irrelevant_keys = ("key-of-off-topic-paper-1", "key-of-off-topic-paper-2")
for key in irrelevant_keys:
    for path in (run / "pdfs" / f"{key}.pdf", run / f"{key}.pptx"):
        if path.exists():
            path.unlink()
```

Xóa `exports/<run>/pdfs/<key>.pdf` + `exports/<run>/<key>.pptx`.
**Giữ lại** `<slug>-<timestamp>.xlsx` / `.bib` tổng hợp — đó là
bản ghi trung thực về những gì tìm kiếm đã trả về. Các trường hợp ranh
giới thì cứ tạo một bản tóm tắt đầy đủ; thà bao gồm quá mức còn hơn âm
thầm bỏ sót một khả năng khớp.

### Ví dụ thực tế

[`scripts/regen_fang2026.py`](scripts/regen_fang2026.py) chứa một bản
tóm tắt rich được soạn tay đúng theo cách này (một bài,
rich-tier, zh-tw, mọi trường rich đều được điền). Một tìm kiếm đa-bài
theo cùng khuôn dạng với một mục `Paper(...summary=PaperSummary(...))`
cho mỗi bài trong tuple `PaperCollection`.

### Những điều không nên

- **Đừng** kết thúc một tìm kiếm đa-bài bằng cách bảo người dùng "hãy đặt
  `ANTHROPIC_API_KEY` để có deck đầy đủ" — bạn chính là LLM lẽ ra
  đã viết các bản tóm tắt.
- **Đừng** coi bản `.pptx` nhẹ từng bài là sản phẩm
  bàn giao.
- **Đừng** dừng lại sau khi `download_pdfs` báo đã lưu N PDF — đó là
  khởi đầu của giai đoạn viết-đầy-đủ, không phải kết thúc.
- **Đừng** bịa số liệu, RQ, đóng góp hoặc hạn chế không có trong
  bài báo.
- **Đừng** ngụy tạo URL / DOI / arXiv ID — xem quy tắc bên trên.
- **Đừng** để lại các tải xuống không liên quan trong thư mục chạy. Việc
  so khớp tìm kiếm theo từ khóa có thể bao gồm các bài lạc đề (một truy
  vấn "Claude code" đã kéo vào một bài về bộ giải mã Viterbi; "LLM code
  review" đã kéo vào một bài tổng quan tài liệu về phát hiện đối tượng).
  Sau khi phân loại các bài là lạc đề, hãy xóa `pdfs/<key>.pdf` và bản
  `<key>.pptx` nhẹ của chúng; giữ lại xlsx / bib tổng hợp như bản ghi
  trung thực về những gì tìm kiếm đã trả về.
- **Đừng** đề cập "Claude", "Claude Code", "AI-generated", "GPT",
  "Copilot", hoặc bất kỳ tên công cụ/mô hình AI nào trong commit message, mô
  tả PR, comment code hoặc tài liệu.

## Tính năng

- **Mười lăm nguồn cắm-ngoài**: `arxiv`, `semantic_scholar`, `openalex`,
  `pubmed`, `acm` (giới hạn phạm vi Crossref), `dblp`, `crossref` (không giới hạn),
  `openaire`, `springer` (cần API key), `europepmc` (mở, không cần key —
  khoa học sự sống + preprint + nông nghiệp), `doaj` (mở, không cần key —
  tạp chí truy cập mở, thường có liên kết PDF trực tiếp), `hal` (mở,
  không cần key — kho CS / toán / vật lý của Pháp với PDF toàn văn),
  `core` (cần API key miễn phí — bộ tổng hợp truy cập mở lớn nhất, 250M+
  công trình), `ieee` (bật mặc định qua Chrome hiển thị; API key thêm API Xplore
  chính thức), `scholar` (bật mặc định qua Chrome hiển thị). Mỗi nguồn nằm trong
  `sources/<name>/` sau một adapter `Fetcher`. Truyền `--top-tier-only` để lọc
  kết quả về các hội nghị/tạp chí CS chủ lực cộng với Nature/Science/PNAS.
  Tìm kiếm mặc định giữ mọi venue.
- **Chế độ bài đơn**: dán một arXiv ID, URL arXiv, DOI, PMID, hoặc URL tài
  liệu IEEE — ThesisAgents giải nó qua nguồn đúng và
  phát ra cùng gói xuất. Hữu ích cho ghi chú đọc bài và chuẩn bị
  bảo vệ luận văn.
- **Chế độ PDF nội bộ** (`--pdf <path>`): truyền một PDF hoặc một thư mục.
  Một bộ trích heuristic lấy **tiêu đề, tác giả, năm, arXiv ID, DOI, và
  tóm tắt thật** ngay từ front matter của mỗi PDF (neo vào
  tiêu đề `Abstract` / `ABSTRACT` / `摘要` tường minh, không phải một
  tiền tố mù). `--title` / `--authors` / `--year` / `--venue` / `--doi` /
  `--arxiv-id` ghi đè trên một lời gọi PDF-đơn; với một thư mục, trích
  xuất theo từng file thắng nên mỗi bài có deck riêng đặt tên theo
  khóa BibTeX của nó.
- **Tám exporter**:
  - `.pptx` — màn rộng 16:9, đánh số trang, ba mức render
    (nhẹ chỉ-tóm-tắt · enriched-flat · **phong cách luận văn** với
    các góc tư điểm-đau, KPI nổi bật, bảng so sánh kỹ thuật,
    bảng kết quả theo RQ, tóm tắt đóng góp, quan sát cốt lõi,
    hạn chế & công việc tương lai, Q&A, tài liệu tham khảo). Mọi chuỗi
    template đều được i18n trên **14 ngôn ngữ**: English, 繁體中文, 简体中文,
    日本語, Español, Français, Deutsch, 한국어, Português, Русский,
    Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia.
  - **Bộ nhận diện hình ảnh được thiết kế cho deck** (không phải vẻ ngoài
    Calibri-trên-nền-trắng mặc định): typography theo từng ngôn ngữ (Inter
    cho Latin, Microsoft JhengHei UI / YaHei UI / Yu Gothic UI / Malgun
    Gothic / Nirmala UI cho CJK + Hindi), accent geometry theo chương
    trình (thanh accent trên cùng ở mọi slide nội dung + dải trái trên
    trang bìa), định dạng bảng kiểu học thuật (bỏ lưới mặc định, đường rule
    navy ở header, divider nhẹ giữa các hàng, sọc hàng xen kẽ, căn dọc
    giữa, nhãn hàng in đậm), và kỷ luật bảng năm màu (navy / teal /
    grey / light / white) với đỏ bị **cấm** dùng cho chữ (thay vào đó dùng
    đậm + teal `#0E7490` để nhấn mạnh).
  - **Chế độ sáng là đường render mặc định.** Truyền `--dark-mode`, bật
    **Dark mode** trong tab Deck của GUI, hoặc đặt
    `ExportOptions(dark_mode=True)` để áp dụng post-pass tối (nền slide
    `#12151B`, chữ thân `#E5E7EB`).
  - `.xlsx` — sheet Papers + sheet nguồn gốc Query, URL / PDF có
    hyperlink, header cố định, độ rộng cột tự động. Cột 5 (**Source**) hiển
    thị venue xuất bản thực (ví dụ "IEEE Access"); cột 6
    (**Indexed via**) cho biết fetcher nào trả metadata
    (ví dụ "openalex"), nên hai mẩu thông tin không bao giờ va nhau.
  - `.md` — danh sách đầy đủ nguồn / tiêu đề / tóm tắt.
  - `.bib` — khóa trích dẫn không xung đột, các trường được escape LaTeX.
  - `.json` — payload thô cho công cụ downstream.
  - `.ris` — trao đổi RIS được nhập bởi Zotero / Mendeley / EndNote /
    RefWorks (người anh em của BibTeX cho các trình quản lý tài liệu tham
    khảo không dùng LaTeX).
  - `.csv` — bảng phẳng một-hàng-mỗi-bài cho bảng tính / phân loại nhanh
    bằng grep (quoting RFC-4180, nên dấu phẩy trong tiêu đề không bao giờ
    dịch cột).
  - `.csl.json` — CSL-JSON cho Pandoc / citeproc; render một danh mục tài
    liệu tham khảo theo bất kỳ kiểu CSL nào (APA, IEEE, Nature, …). Đuôi
    `.csl.json` giữ nó khác biệt với bản dump `.json` thuần.
- **Bộ công cụ chỉnh sửa PPT**: `thesisagents.exporters.pptx_edit`
  (inspect / update_slide / delete_slide / reorder_slides / add_slide)
  làm việc với bất kỳ deck nào exporter sinh ra, cộng với các công cụ MCP
  `pptx_*` tương đương để một LLM agent có thể lặp trên một deck đã sinh.
- **Server MCP**: 13 công cụ — `list_sources` + `list_exports`
  (khám phá), `search`, `fetch_paper`, `fetch_pdf_text`,
  `download_pdfs`, `export`, và sáu công cụ deck `pptx_*`
  (`inspect`, `review`, `update_slide`, `delete_slide`,
  `reorder_slides`, `add_slide`). Cho phép
  bất kỳ LLM tương thích MCP nào
  (Claude Code, Claude Desktop, Cursor, …) điều khiển toàn bộ workflow.
- **Hai lối làm giàu** để vượt ra ngoài tóm tắt và tiến vào một deck
  phong cách luận văn thực sự:
  - **LLM-as-agent (không cần API key)** — LLM gọi đọc văn bản thân bài
    PDF qua `fetch_pdf_text`, viết một bản tóm tắt có cấu trúc trong ngữ
    cảnh, và truyền nó cho `export`.
  - **Pipeline Python (`--enrich`)** — CLI tự gọi API của Anthropic;
    mô hình mặc định `claude-opus-4-7`.
- **Các luồng nhà xuất bản qua Chrome hiển thị**: Scholar SERP, IEEE
  `/rest/search`, và mọi tải xuống PDF-có-paywall (ieeexplore / dl.acm /
  link.springer / sciencedirect / wiley / oup / nature / science / …) chạy
  bên trong một phiên Chrome hiển thị thực qua `selenium`. Người dùng giải
  captcha / hoàn tất SSO trong cửa sổ trực tiếp một lần;
  `THESISAGENTS_CHROME_PROFILE_DIR` duy trì cookie qua các lần chạy.
- **Luồng LLM-as-agent**: các công cụ MCP cung cấp tìm kiếm, tải PDF và
  trích xuất văn bản. `scripts/regen_*.py` chứa các ví dụ tái lập được cho
  việc soạn tay một `PaperSummary` đầy đủ cho mỗi bài.
- **Bộ giải OA PDF**: sau khi khử trùng lặp, mỗi bài không có `pdf_url`
  đi qua Unpaywall → S2 `openAccessPdf` → tìm kiếm tiêu đề trên arXiv →
  CORE.ac.uk (khi các key được đặt). Mức nâng điển hình cho các truy vấn
  nặng IEEE / ACM / Springer / Elsevier: 40-70 điểm phần trăm.
- **An toàn theo mặc định**: transport HTTP chỉ-HTTPS, rate limit theo
  từng nguồn (token bucket), `defusedxml` cho mọi payload XML,
  các đường xuất an-toàn-với-path-traversal, không `eval` / `exec` / `pickle` trên
  input người dùng.
- **Bộ bảo vệ từ vựng zh-tw / zh-cn**: ~244 mẫu regex trong
  `tests/test_i18n.py::test_zh_tw_files_use_traditional_chinese_vocabulary`
  bắt các từ mượn tiếng Trung Giản thể được render bằng chữ Hán Phồn thể
  (ví dụ `內存` → `記憶體`, `魯棒性` → `穩健性`, `軟件` → `軟體`,
  `緩存` → `快取`). Cùng bộ bảo vệ chạy ngược lại cho các chuỗi locale
  zh-cn. Toàn bộ quy tắc + danh mục regex nằm trong
  `.claude/agents/rules/language-vocabulary-check.md`.

## Bắt đầu nhanh

```powershell
git clone <repo-url>
cd ThesisAgents
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Cài kèm dev extras (cũng kéo vào MCP SDK và intelligence deps)
pip install -e .[dev]
```

Tìm arXiv và xuất deck + workbook + BibTeX (mặc định cho `--query`):

```powershell
py -m thesisagents --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

Lấy một bài đơn theo URL — mặc định là `.pptx + .bib` (`.xlsx`
ít ý nghĩa cho một hàng):

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

Render deck bằng 繁體中文:

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --lang zh-tw --out .\exports\
```

Làm giàu bằng LLM-pipeline (Python tự gọi Anthropic — cần API key):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang zh-tw --out .\exports\
```

## Cờ CLI

| Cờ | Mục đích |
|---|---|
| `--query` / `-q` | Từ khóa (bắt buộc trừ khi có `--paper`). |
| `--paper` / `-p` | arXiv ID / URL, DOI, PMID, hoặc URL tài liệu IEEE. Loại trừ lẫn nhau với `--query`. |
| `--source` / `-s` | Danh sách nguồn phân cách bằng dấu phẩy. Mặc định `arxiv`. |
| `--max` / `-n` | Số kết quả tối đa mỗi nguồn (1..200). Mặc định 25. |
| `--year-from` / `--year-to` | Bộ lọc năm bao gồm. |
| `--export` / `-e` | Định dạng: bất kỳ trong `pptx,xlsx,md,bib,json,ris,csv,csl`. Mặc định tùy chế độ (xem bên dưới). |
| `--out` / `-o` | Thư mục đầu ra. Mặc định `./exports`. |
| `--filename-stem` | Ghi đè stem tên file được sinh. |
| `--no-abstract` | Bỏ nội dung tóm tắt khỏi các bản xuất. |
| `--lang` / `-l` | Ngôn ngữ deck: một trong 14 — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. Mặc định `en`. |
| `--enrich` | Biến thể fail-loud của auto-enrich. Cần `ANTHROPIC_API_KEY` và extra `[intelligence]`. (Auto-enrich là mặc định khi key được đặt.) |
| `--lightweight` | Bỏ làm giàu + buộc deck chỉ-tóm-tắt. Chỉ dùng cho các lần chạy nhanh / không người trông coi; **khi một LLM agent đang điều khiển, hãy ưu tiên luồng LLM-as-agent** bên dưới. |
| `--llm-model` | Ghi đè mặc định `claude-opus-4-7` cho việc làm giàu. |
| `--no-pdf` | Bỏ tải PDF tự động. Cũng vô hiệu hóa gate PPT từng bài (không PDF → không nội dung đầy đủ). |
| `--no-oa-resolve` | Bỏ bộ giải OA PDF sau khử trùng lặp (Unpaywall + S2 + arXiv + CORE.ac.uk). |
| `--top-tier-only` | Giới hạn kết quả vào arXiv + một whitelist CS-chủ-lực được tuyển chọn (S&P, CCS, NDSS, USENIX Security, NeurIPS, ICML, ICSE, …). Tắt theo mặc định. |
| `--paywall-threshold` | Tỉ lệ kết quả có paywall kích hoạt prompt xác nhận. Mặc định 0.30. |
| `--yes` | Bỏ qua prompt paywall và tiếp tục. |
| `--max-slides` | Giới hạn slide mỗi bài (mặc định 25; truyền 0 cho không giới hạn). |
| `--dark-mode` | Render pptx với nền tối + chữ gần trắng. Mặc định là deck sáng dải navy. |
| `--quiet` | Tắt in ấn theo từng bài. |

### Biến môi trường

| Biến | Được dùng bởi | Mục đích |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | Xác thực LLM. Không cần cho đường LLM-as-agent qua MCP. |
| `THESISAGENTS_LLM_MODEL` | `--enrich` | Ghi đè mặc định `claude-opus-4-7`. |
| `THESISAGENTS_S2_API_KEY` | Semantic Scholar + bộ giải OA | Rate limit cao hơn; cũng được bước S2 `openAccessPdf` của bộ giải OA dùng. Key miễn phí tại <https://www.semanticscholar.org/product/api>. |
| `THESISAGENTS_NCBI_API_KEY` | PubMed | Nâng giới hạn ẩn danh của NCBI (3/s) lên 10/s. Tùy chọn. |
| `THESISAGENTS_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex, **Unpaywall** | Tag polite-pool + bật bước Unpaywall của bộ giải OA (mức thắng lớn nhất về độ phủ PDF cho các bài IEEE / ACM / Springer / Elsevier có paywall; mức nâng điển hình 40-70 pp). |
| `THESISAGENTS_IEEE_API_KEY` | IEEE (đường API) | API IEEE Xplore chính thức; phơi `pdf_url` cho các bài trong phạm vi. |
| `THESISAGENTS_DISABLE_IEEE_SCRAPING` | IEEE | **IEEE bật mặc định qua Chrome hiển thị.** Đặt `=1` để opt out (ví dụ CI không có Chrome). Nhánh scrape httpx chỉ chạy như phương án dự phòng khi WebRunner không khả dụng. |
| `THESISAGENTS_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Token thuê bao Crossref Plus (header Bearer). Tùy chọn. |
| `THESISAGENTS_SPRINGER_API_KEY` | Springer | Bắt buộc; key miễn phí từ <https://dev.springernature.com/>. Plugin nêu `ConfigError` nếu thiếu. |
| `THESISAGENTS_DISABLE_SCHOLAR_SCRAPING` | Google Scholar | **Scholar bật mặc định qua Chrome hiển thị.** Đặt `=1` để opt out (ToS của Google cấm truy cập tự động — bật mặc định vì độ phủ, opt out để tránh rủi ro captcha / chặn IP). |
| `THESISAGENTS_CHROME_PROFILE_DIR` | Tải Scholar + IEEE + PDF-có-paywall | `--user-data-dir` Chrome bền vững. Đặt cái này và hoàn tất VPN / SSO / đăng nhập Google một lần; các lần chạy sau kế thừa cookie nên IEEE trả metadata có paywall và Scholar phục vụ SERP không bị bóp. |
| `THESISAGENTS_DISABLE_WEBRUNNER` | Tải Scholar + IEEE + PDF-có-paywall | `=1` buộc các đường httpx thay vì điều khiển Chrome thật. Hữu ích cho CI / Docker không có Chrome binary; ngoài ra để trống. |
| `THESISAGENTS_CORE_API_KEY` | Bộ giải OA + nguồn tìm kiếm `core` | Key miễn phí từ <https://core.ac.uk/services/api>. Bật bước tra cứu OA CORE.ac.uk (200M+ mục OA thể chế / khu vực) **và** nguồn tìm kiếm `core`. Không có nó, nguồn `core` bị bỏ qua âm thầm và các chiến lược OA khác (Unpaywall, S2, arXiv) vẫn chạy. |
| `THESISAGENTS_PDF_COOKIES_FILE` | Trình tải PDF | `cookies.txt` định dạng Netscape. Mặc định tắt. Chỉ dùng với các nhà xuất bản bạn có quyền truy cập từ tổ chức. |
| `THESISAGENTS_LOG_LEVEL` | logger | Mặc định `INFO`; `DEBUG` cho trace chi tiết. |

Mặc định: `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. Luôn
có thể ghi đè bằng `--export` tường minh.

## Luồng LLM-as-agent

Khi một LLM trong editor của bạn điều khiển workflow, hãy dùng các công cụ
MCP theo trình tự: `search`, `download_pdfs`, `fetch_pdf_text`, rồi `export`
với một `PaperSummary` đầy đủ được soạn tay. Các file `scripts/regen_*.py`
hiện có là các ví dụ tái lập được cho bước soạn và xuất cuối cùng.

Runbook đầu-cuối đầy đủ (tìm kiếm → deck đầy đủ) nằm trong
`.claude/agents/tasks/paper-summary-author.md` — hãy mở nó trước khi bắt đầu
một truy vấn mới để LLM chạy luồng mà không dừng chờ input người dùng.

## Server MCP

Đăng ký với Claude Code:

```powershell
claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp
```

Hoặc ghi vào file settings của bạn:

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

Công cụ:

| Công cụ | Mục đích |
|---|---|
| `list_sources` | Liệt kê mọi plugin + báo cái nào đang bật trong env hiện tại. Gọi nó một lần trước `search`. |
| `list_exports` | Liệt kê mọi định dạng xuất với mô tả một dòng và việc nó ghi một file tổng hợp hay một file mỗi bài. |
| `search` | Từ khóa → danh sách bài. Nhận `top_tier_only`, `min_citations`; mặc định là tổ hợp nguồn không-cần-API-key đầy đủ. |
| `fetch_paper` | Định danh arXiv / DOI / PMID / IEEE → một bài đơn. |
| `fetch_pdf_text` | Tải một PDF, trả về văn bản thân bài đã trích. **Cổng MCP tới "tôi đã đọc bài".** |
| `download_pdfs` | Tải hàng loạt PDF của một danh sách bài vào `{out_dir}/pdfs/`. Trả về kết quả từng bài có khóa theo khóa BibTeX. |
| `export` | Danh sách bài + định dạng → ghi `.pptx/.xlsx/.md/.bib/.json/.ris/.csv/.csl.json`. Nhận một trường `summary` mỗi bài cho schema phong cách luận văn đầy đủ, `max_slides_per_paper` (mặc định 25), và `dark_mode` (mặc định `false` — mặc định dự án là deck sáng dải navy, truyền `true` cho post-pass tối OLED / thiếu sáng). |
| `pptx_inspect` | Đọc cấu trúc slide / shape của một deck hiện có. |
| `pptx_review` | Kiểm toán một deck trong một lời gọi — overflow + hợp đồng màu + độ đầy đủ mục `paper_rule`. Tự phát hiện ngôn ngữ deck; cũng là CLI `python -m thesisagents review <deck.pptx>`. |
| `pptx_update_slide` | Thay `title` / `body` / `meta` (theo tên shape) hoặc các shape tùy ý theo index. |
| `pptx_delete_slide` | Xóa một slide và part relationship của nó. |
| `pptx_reorder_slides` | Hoán vị các slide qua `sldIdLst`. |
| `pptx_add_slide` | Thêm cuối hoặc chèn một slide title / body / meta mới. |

Luồng LLM-as-agent (không cần `ANTHROPIC_API_KEY` — LLM chính là agent):

```
1. (tùy chọn) list_sources()                       # khám phá plugin đang bật
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (tùy chọn) download_pdfs(papers, out_dir="./exports/...")  # lưu PDF
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # cho mỗi bài
5. (LLM đọc văn bản thân bài, tạo một dict `summary` có cấu trúc)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="zh-tw", formats=["pptx","bib"], dark_mode=true, ...)
```

Tham chiếu đầy đủ trong [`docs/mcp.md`](docs/mcp.md).

## Bố cục dự án

```
ThesisAgents/
├── thesisagents/                 # gói chính
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # client async chỉ-HTTPS, rate limit token bucket
│   ├── exporters/                   # pptx (phong cách luận văn) · xlsx · bib · md · json · ris · csv · csl · pptx_edit · i18n
│   ├── intelligence/                # tải PDF + bộ tóm tắt Anthropic  ([intelligence] extra)
│   ├── evaluation/                  # benchmark chất lượng tìm kiếm offline (docs/search-quality.md)
│   ├── mcp/                         # server FastMCP (13 công cụ)
│   ├── sources/<name>/              # thư mục plugin: arxiv, semantic_scholar,
│   │                                #   openalex, pubmed, acm, ieee, scholar,
│   │                                #   dblp, crossref, openaire, springer,
│   │                                #   europepmc, doaj, hal, core
│   ├── utils/                       # logging, path safety
│   ├── cli.py                       # CLI argparse
│   └── __main__.py
├── tests/                           # bộ pytest + fixture đã ghi (không HTTP trực tiếp)
├── docs/                            # Sphinx (14 cây ngôn ngữ)
├── scripts/                         # script regen dùng một lần
└── pyproject.toml                   # ruff, bandit, build, extras tùy chọn
```

## Definition of Done

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r thesisagents/
```

Cờ `-c` của bandit là bắt buộc — không có nó bandit bỏ qua cấu hình
skip của dự án. Khi đụng tới exporter pptx, hãy chạy thêm một
kiểm tra overflow (xem `CLAUDE.md` "Slide Deck Rules").

## GUI máy tính (PySide6)

Một giao diện máy tính bản địa được đóng gói sau extra `[gui]`:

```powershell
pip install thesisagents[gui]
thesisagents-gui                 # hoặc: thesisagents gui
```

Cửa sổ có bốn tab — **Search**, **Settings** (duy trì API key
qua QSettings), **Enrich** (điều khiển làm giàu LLM-as-agent /
Python-pipeline qua một tín hiệu `collection_ready`), và **Deck** (nút bật
Light mode + slide-cap + max-figures luồng vào
`ExportOptions`). Bản release zip Windows đóng gói bundle được biên dịch
bằng Nuitka kèm sẵn PySide6, nên `thesisagents.exe gui` chạy
mà không cần cài Python riêng.
**Giao diện phát hành đủ 14 ngôn ngữ** (English, 繁體中文, 简体中文,
日本語, Español, Français, Deutsch, 한국어, Português, Русский,
Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia) — lần chạy đầu chọn
ngôn ngữ theo locale OS của bạn, rồi **Settings → Interface
language** cho bạn đổi nó. Ngôn ngữ đầu ra của deck là một dropdown
riêng nên bạn có thể chạy UI ở một ngôn ngữ và phát ra
slide ở ngôn ngữ khác. Bố cục responsive: mọi form nằm trong
một `QScrollArea` và cửa sổ thu nhỏ xuống 900×600 (vẫn vừa
720p), với HiDPI scaling bật theo mặc định.

Tham chiếu đầy đủ: [`docs/gui.md`](docs/gui.md).

## Đóng gói thành file thực thi độc lập

Hai packager được tài liệu hóa để giao một binary một-file chạy
mà không cần cài Python:

- **[`docs/packaging-pyinstaller.md`](docs/packaging-pyinstaller.md)**
  — build nhanh (dưới một phút), đầu ra 200–300 MB, khởi động 2–4 giây.
  Tốt nhất khi bạn lặp trên build script.
- **[`docs/packaging-nuitka.md`](docs/packaging-nuitka.md)** —
  build chậm (5–15 phút), đầu ra 80–150 MB, khởi động dưới một giây,
  có chút bảo vệ bytecode. Tốt nhất khi người dùng cuối chạy binary
  nhiều lần.

Cả hai tài liệu đều bao quát vướng-mắc-riêng-của-dự-án — các plugin
nguồn động dưới `sources/<name>/` — và giao một lệnh đã kiểm chứng cho
các entry point của CLI và server MCP.

## Tích hợp liên tục & phát hành

Hai workflow GitHub Actions nằm trong `.github/workflows/`:

- **`ci.yml`** chạy trên mỗi push và PR vào `main`. Matrix là Ubuntu +
  Windows × Python 3.12 / 3.13 / 3.14 (6 job). Mỗi job chạy
  `ruff check`, `bandit -c pyproject.toml`, và `pytest`.
- **`release.yml`** chờ `ci.yml` hoàn tất trên `main`
  (trigger `workflow_run`). Nó chỉ chạy nếu CI thành công. **Mỗi
  push thành công CI vào `main` là một release** — workflow tự động tăng
  patch version trong `pyproject.toml`, commit lần tăng đó trở lại
  `main` dưới dạng `chore: bump version to X.Y.Z`, và pipeline hóa:
  1. **`bump-version`** — đọc `X.Y.Z` hiện tại từ `pyproject.toml`,
     tăng lên `X.Y.(Z+1)`, commit + push trở lại `main` bằng
     `GITHUB_TOKEN` của workflow. Push đó KHÔNG re-trigger CI (theo
     quy tắc của GitHub rằng các push do `GITHUB_TOKEN` không thể khởi
     động các lần chạy workflow mới), nên chu trình kết thúc tự nhiên.
  2. **`publish-pypi`** — build sdist + wheel, `twine check`,
     `twine upload` qua `PYPI_API_TOKEN`.
  3. **`create-draft-release`** — mở một GitHub release *nháp* tại
     tag `v<version>` với ghi chú tự sinh.
  4. **`build-nuitka`** — biên dịch một bundle Nuitka standalone trên một
     runner Windows (entry point: `python -m thesisagents` qua
     `--python-flag=-m`), smoke-test nó, zip thư mục
     `thesisagents.dist/` kết quả, và đính kèm zip + một checksum `.sha256`
     vào release nháp. Standalone (không phải onefile) theo
     thiết kế: onefile tự giải nén vào `%TEMP%` mỗi lần khởi động,
     thêm độ trễ khởi động và kích hoạt heuristic diệt virus trên các
     máy bị khóa chặt. Cũng chỉ-Windows theo thiết kế: người dùng Linux /
     macOS cài từ PyPI. Cache build khóa trên `pyproject.toml`
     cắt build ấm từ ~85 phút lạnh xuống ~5–10 phút.
  5. **`publish-release`** — bỏ đánh dấu nháp một khi asset Nuitka
     đã được tải lên, nên người dùng không bao giờ thấy một release dở dang.

  **Bỏ qua một release.** Đưa `[skip release]` vào bất kỳ đâu trong
  commit message và lần tăng + mọi job downstream đều bị bỏ qua — dùng
  cái này cho các commit chỉ-tài-liệu / sửa lỗi chính tả / refactor không
  nên tiêu một số phiên bản.

Để bật xuất bản PyPI + file thực thi release:

1. Tạo một API token phạm-vi-dự-án tại
   <https://pypi.org/manage/account/token/>.
2. Trong repo GitHub: `Settings → Secrets and variables → Actions →
   New repository secret`. Đặt tên `PYPI_API_TOKEN` và dán
   giá trị token.
3. Cho phép GitHub Actions push vào `main`: `Settings → Actions →
   General → Workflow permissions → Read and write permissions`.
   Commit tăng phiên bản được push bởi `GITHUB_TOKEN` của workflow.
4. Cắt release bằng cách merge PR vào `main`. Pipeline mất
   ~3–5 phút để xuất bản lên PyPI và ~80–90 phút nữa (lạnh) hoặc ~5–10 phút
   (cache Nuitka ấm) để zip Windows được đính kèm.

Job `publish-pypi` cố ý KHÔNG đính kèm một GitHub
Environment, nên mỗi lần chạy hiện ra như một mục Release (với
`.exe` Nuitka đính kèm) thay vì như một widget sidebar "Deployment"
trên trang chủ repo — các release có trang riêng dành cho chúng
và một mục Deployment ở trên cùng sẽ chỉ là nhiễu thừa.

## Giấy phép

Xem `LICENSE`. API arXiv được dùng theo điều khoản sử dụng API của arXiv
(<https://info.arxiv.org/help/api/tou.html>) — tuân thủ giới hạn mềm 1 request
mỗi 3 giây; fetcher tích hợp đã ép điều này qua
token bucket của nó.
