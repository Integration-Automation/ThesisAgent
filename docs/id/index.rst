Panduan Pengguna ThesisAgents
================================

Asisten pencarian makalah berbasis kata kunci. Mengambil hasil dari
arXiv, Semantic Scholar, OpenAlex, PubMed, ACM, IEEE Xplore, DBLP,
Crossref, OpenAIRE, Springer Nature, dan Google Scholar; dan mengekspor
sebagai presentasi PowerPoint gaya tesis, buku kerja Excel, dan berkas
BibTeX. Semua dari satu panggilan CLI atau satu panggilan tool MCP.

.. contents:: Daftar Isi
   :depth: 2
   :local:

----

Untuk agen AI yang menjalankan proyek ini
-----------------------------------------

**Jika Anda LLM (Claude Code, Cursor, Aider, Codex CLI, …) yang membaca
dokumen ini untuk tahu apa yang harus dilakukan — mulailah di sini.**
Aturan yang sama disematkan di ``AGENTS.md`` (cermin lintas-agen) dan
``CLAUDE.md`` (referensi resmi) di akar repo; baca itu sebelum
perubahan non-sepele.

**Deliverable default adalah satu ``.pptx`` gaya tesis yang diperkaya
per makalah**, bukan deck ringan hanya-abstrak yang dihasilkan CLI
secara default. Output ringan adalah artefak antara — tugas Anda
adalah meningkatkannya.

Pohon keputusan
^^^^^^^^^^^^^^^

1. ``ANTHROPIC_API_KEY`` di-set? → jalankan CLI; otomatis memperkaya via
   API Anthropic.
2. Tanpa key, LLM menjalankan → **tulis ringkasan diperkaya sendiri**.
   Baca tiap PDF, tulis tangan ``PaperSummary`` dengan field
   rich-tier, letakkan ``scripts/regen_<query>.py``, jalankan. **Jangan
   suruh pengguna men-set API key** — Andalah LLM-nya.
3. Tanpa LLM (CI / cron) → ringan dapat diterima.

Alur MCP 6 langkah
^^^^^^^^^^^^^^^^^^

.. code-block:: text

   1. (opsional) list_sources()
   2. search(keywords, sources, top_tier_only=true, ...)
   3. (opsional) download_pdfs(papers, out_dir="./exports/...")
   4. fetch_pdf_text(pdf_url=paper.pdf_url)           # per makalah
   5. (Anda membaca tiap PDF dan menghasilkan dict ringkasan terstruktur)
   6. export(papers=[{...paper, "summary": {...}}], language="id", ...)

11 tool MCP lengkap: :doc:`/mcp`.

Wajib: verifikasi URL / DOI sebelum penyerahan
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Jalur URL penerbit **tidak dapat ditebak** — AAAI memakai ID numerik
(``v40i5.37389``), IEEE memakai ``arnumber`` opak, ACM memakai DOI
opak. Saat menulis tangan ``Paper``, **salin ``url`` / ``doi`` /
``arxiv_id`` apa adanya dari xlsx yang dihasilkan pencarian ini** —
jangan pernah dari ingatan, jangan disusun dari judul.

xlsx ditulis ke ``exports/<run>/<slug>-<timestamp>.xlsx`` dengan kolom
7 = DOI, kolom 8 = URL. Audit script regen Anda saat selesai:

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

Larangan
^^^^^^^^

* Jangan suruh pengguna "set ``ANTHROPIC_API_KEY``" — Anda LLM-nya.
* Jangan perlakukan ``.pptx`` ringan sebagai deliverable.
* Jangan berhenti saat ``download_pdfs`` selesai.
* Jangan mengarang angka, RQ, kontribusi, keterbatasan.
* Jangan memfabrikasi URLs / DOIs / arXiv IDs.
* Jangan tinggalkan unduhan tidak relevan di direktori run.
  Pencarian kata kunci kadang membawa makalah tidak terkait (kueri
  "Claude code" membawa makalah tentang decoder Viterbi). Hapus
  ``pdfs/<key>.pdf`` dan ``<key>.pptx`` ringan yang tidak relevan;
  pertahankan xlsx / bib agregat sebagai catatan jujur. Prosedur
  lengkap di ``CLAUDE.md`` "Pruning irrelevant downloads".
* Jangan menyebut "Claude", "Claude Code", "AI-generated", "GPT",
  "Copilot", atau nama tool/model AI lain di commit, PR, kode, atau
  dokumentasi.

Contoh: ``scripts/regen_llm_security_batch.py`` (en, 8 makalah) dan
``scripts/regen_llm_security_batch_zh_tw.py`` (zh-tw).

----

Instalasi
---------

Perlu Python **3.12+**.

.. code-block:: bash

   git clone <repo-url>
   cd ThesisAgents
   python -m venv .venv
   .venv\Scripts\Activate.ps1            # Windows PowerShell
   # source .venv/bin/activate           # Linux / macOS
   pip install -e .[dev]

Extras opsional: ``[mcp]``, ``[intelligence]``, ``[web]``, ``[dev]``.

----

Mulai cepat
-----------

.. code-block:: bash

   # Cari arXiv → deck + workbook + BibTeX
   thesisagents --query "diffusion models" --source arxiv --max 10 \
                  --out ./exports/

   # Satu makalah by URL → deck + BibTeX
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --filename-stem attention --out ./exports/

   # Render deck dalam Bahasa Indonesia
   thesisagents --paper 1706.03762 --lang id --out ./exports/

   # Pengayaan Python pipeline (butuh key Anthropic)
   export ANTHROPIC_API_KEY=sk-ant-...
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --enrich --lang id --out ./exports/

Tabel flag CLI lengkap: :doc:`/cli`.

----

Bacaan lebih lanjut
-------------------

* Flag CLI dan variabel lingkungan: :doc:`/cli`
* 11 tool server MCP: :doc:`/mcp`
* Toolkit edit PPTX: :doc:`/pptx_editing`
* Berkas ``readmes/README.id.md`` di akar repo berisi daftar fitur lengkap.
* Referensi teknis mendalam (arsitektur plugin, kebijakan keamanan,
  Definition of Done, aturan SonarQube, …) terkonsolidasi di panduan
  Inggris: :doc:`/en/index`.
