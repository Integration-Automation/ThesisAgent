Hướng dẫn người dùng ThesisAgents
====================================

Trợ lý tìm kiếm bài báo theo từ khóa. Lấy kết quả từ arXiv, Semantic
Scholar, OpenAlex, PubMed, ACM, IEEE Xplore, DBLP, Crossref, OpenAIRE,
Springer Nature, Europe PMC, DOAJ, HAL, CORE và Google Scholar; xuất
thành slide PowerPoint phong
cách luận văn, sổ Excel và tệp BibTeX. Tất cả từ một lệnh CLI hoặc một
lời gọi công cụ MCP.

.. contents:: Mục lục
   :depth: 2
   :local:

----

Dành cho AI agent điều khiển dự án này
---------------------------------------

**Nếu bạn là một LLM (Claude Code, Cursor, Aider, Codex CLI, …) đọc
tài liệu này để biết cần làm gì — hãy bắt đầu từ đây.** Cùng các quy
tắc đó được ghim trong ``AGENTS.md`` (cermin liên-agent) và
``CLAUDE.md`` (tham chiếu chính thức) ở gốc repo; hãy đọc chúng trước
khi thay đổi đáng kể.

**Sản phẩm mặc định là một ``.pptx`` phong cách luận văn cho mỗi bài**,
không phải bản deck nhẹ chỉ-tóm-tắt mà CLI sinh mặc định. Bản nhẹ là
tạo phẩm trung gian — nhiệm vụ của bạn là nâng cấp nó.

Cây quyết định
^^^^^^^^^^^^^^

1. ``ANTHROPIC_API_KEY`` đã đặt? → chạy CLI; tự động làm giàu qua API
   Anthropic.
2. Không có key, LLM điều khiển → **viết bản tóm tắt đầy đủ tự
   mình**. Đọc từng PDF, soạn tay ``PaperSummary`` với trường
   rich-tier, đặt ``scripts/regen_<query>.py``, chạy. **Đừng bảo
   người dùng đặt API key** — bạn chính là LLM.
3. Không LLM (CI / cron) → bản nhẹ chấp nhận được.

Quy trình MCP 6 bước
^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   1. (tùy chọn) list_sources()
   2. search(keywords, sources, top_tier_only=true, ...)
   3. (tùy chọn) download_pdfs(papers, out_dir="./exports/...")
   4. fetch_pdf_text(pdf_url=paper.pdf_url)           # mỗi bài
   5. (bạn đọc mỗi PDF và tạo dict tóm tắt có cấu trúc)
   6. export(papers=[{...paper, "summary": {...}}], language="vi", ...)

14 công cụ MCP đầy đủ: :doc:`/mcp`.

**Để tìm các kết quả lạc đề, hãy bắt đầu từ gợi ý của chính công cụ.**
``--diagnostics`` (CLI) hoặc ``diagnostics=true`` trên công cụ MCP
``search`` giải thích thứ hạng: điểm của từng bài báo được tách thành độ
liên quan, độ mới và số trích dẫn, các từ khóa truy vấn đã khớp, cùng
một khuyến nghị ``keep`` / ``review`` / ``prune`` kèm ngưỡng đã kích
hoạt nó. CLI cũng ghi bảng phân tích đầy đủ vào ``diagnostics.json``
trong thư mục đầu ra. Các khuyến nghị chỉ mang tính tham khảo và không
có gì bị xóa thay bạn, vì vậy hãy đọc tóm tắt của các bài ``review`` và
``prune`` trước khi xóa bất cứ thứ gì.

**Hãy kiểm tra nguồn nào đã trả lời.** Mọi phản hồi của ``search`` đều
kèm ``source_stats``: với từng nguồn, số bản ghi nguồn đó trả về, số bài
báo duy nhất được tính cho nguồn đó sau khi khử trùng lặp, và một
``status`` có giá trị ``ok``, ``failed``, ``rate_limited`` hoặc
``disabled``. Một nguồn bị lỗi sẽ được bỏ qua mà không dừng việc tìm
kiếm, vì vậy hãy đọc các con số này trước khi kết luận rằng một chủ đề
có ít bài báo. CLI cũng in cùng bảng đó sau mỗi lần tìm ``--query``.

**Hãy lần theo trích dẫn.** ``--snowball both`` (CLI) hoặc công cụ
``snowball`` mở rộng các kết quả đứng đầu theo liên kết trích dẫn:
``references`` thêm những gì chúng trích dẫn và ``cited_by`` thêm những
gì trích dẫn chúng. Cách này tìm ra các công trình mà tìm kiếm theo từ
khóa bỏ sót vì tác giả dùng thuật ngữ khác. Việc mở rộng có giới hạn
(mặc định một bước), mỗi bài tìm được giữ lại đường đã dẫn tới nó, và
tất cả đều được chấm điểm theo từ khóa của bạn, nên một bài không được
giữ chỉ vì được trích dẫn nhiều.

Bắt buộc: xác minh URL / DOI trước khi giao
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Đường URL của nhà xuất bản **không thể đoán** — AAAI dùng ID số
(``v40i5.37389``), IEEE dùng ``arnumber`` mờ, ACM dùng DOI mờ. Khi tự
tay tạo ``Paper``, **sao chép ``url`` / ``doi`` / ``arxiv_id`` đúng
nguyên văn từ xlsx do lần tìm kiếm này tạo ra** — không bao giờ từ
trí nhớ, không bao giờ ghép từ tiêu đề.

xlsx được ghi vào ``exports/<run>/<slug>-<timestamp>.xlsx`` với cột 7
= DOI, cột 8 = URL. Kiểm toán regen script sau khi xong:

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

**Bước xuất kiểm tra điều này khi chạy.** Trước khi ghi bất cứ thứ gì,
CLI, công cụ MCP ``export`` và tab Deck của GUI tra cứu DOI của từng bài
báo tại doi.org và gửi một yêu cầu tới từng URL. Một DOI chưa đăng ký,
một URL trả về 404 hoặc một máy chủ không thể kết nối sẽ dừng việc xuất
và nêu rõ bài báo cùng mã định danh. Phép kiểm tra chứng minh rằng mã
định danh tồn tại, không chứng minh nó thuộc về bài báo này, nên quy tắc
chép từ xlsx và bước kiểm toán ở trên vẫn cần thực hiện. Khi làm việc
ngoại tuyến, hãy truyền ``--no-verify-identifiers`` (CLI) hoặc
``verify_identifiers=false`` (MCP).

Cấm
^^^

* Đừng nói với người dùng "đặt ``ANTHROPIC_API_KEY``" — bạn chính là LLM.
* Đừng coi ``.pptx`` nhẹ là sản phẩm.
* Đừng dừng khi ``download_pdfs`` xong.
* Đừng bịa số, RQ, đóng góp, hạn chế.
* Đừng ngụy tạo URL / DOI / arXiv ID.
* Đừng để các tải xuống không liên quan trong thư mục chạy. Tìm kiếm
  theo từ khóa có thể đưa vào các bài lạc đề (truy vấn "Claude code"
  đã đưa vào bài về bộ giải mã Viterbi). Xóa ``pdfs/<key>.pdf`` và
  ``<key>.pptx`` nhẹ lạc đề; giữ lại xlsx / bib tổng hợp như bản ghi
  trung thực. Quy trình đầy đủ trong ``CLAUDE.md`` "Pruning
  irrelevant downloads".
* Đừng đề cập "Claude", "Claude Code", "AI-generated", "GPT", "Copilot"
  hoặc tên công cụ/mô hình AI nào trong commit, PR, code hay tài liệu.

Ví dụ thực tế: ``scripts/regen_fang2026.py`` chứa một bản tóm tắt
phong phú được viết tay đúng theo cách này (một bài, rich-tier, zh-tw).
Một lô nhiều bài theo cùng dạng, mỗi bài một mục trong tuple
``PaperCollection``.

----

Cài đặt
-------

Yêu cầu Python **3.12+**.

.. code-block:: bash

   git clone <repo-url>
   cd ThesisAgents
   python -m venv .venv
   .venv\Scripts\Activate.ps1            # Windows PowerShell
   # source .venv/bin/activate           # Linux / macOS
   pip install -e .[dev]

Extras tùy chọn: ``[mcp]``, ``[intelligence]``, ``[web]``, ``[dev]``.

----

Bắt đầu nhanh
-------------

.. code-block:: bash

   # Tìm arXiv → deck + workbook + BibTeX
   thesisagents --query "diffusion models" --source arxiv --max 10 \
                  --out ./exports/

   # Một bài theo URL → deck + BibTeX
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --filename-stem attention --out ./exports/

   # Render deck bằng tiếng Việt
   thesisagents --paper 1706.03762 --lang vi --out ./exports/

   # Làm giàu Python pipeline (cần key Anthropic)
   export ANTHROPIC_API_KEY=sk-ant-...
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --enrich --lang vi --out ./exports/

Bảng cờ CLI đầy đủ: :doc:`/cli`.

----

Tìm hiểu thêm
-------------

* Cờ CLI và biến môi trường: :doc:`/cli`
* 14 công cụ máy chủ MCP: :doc:`/mcp`
* Toolkit chỉnh sửa PPTX: :doc:`/pptx_editing`
* Tệp ``readmes/README.vi.md`` ở gốc repo có danh sách đầy đủ tính năng.
* Tham chiếu kỹ thuật sâu (kiến trúc plugin, chính sách bảo mật,
  Definition of Done, luật SonarQube, …) được tập trung trong hướng
  dẫn tiếng Anh: :doc:`/en/index`.
