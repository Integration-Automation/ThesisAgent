# ThesisAgents

[![CI](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![Python](https://img.shields.io/pypi/pyversions/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/ThesisAgents.svg)](https://github.com/Integration-Automation/ThesisAgents/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/thesisagents/badge/?version=latest)](https://thesisagents.readthedocs.io/en/latest/)

> **Bahasa**: [English](../README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · **Bahasa Indonesia**
> **Dokumentasi**: [thesisagents.readthedocs.io](https://thesisagents.readthedocs.io/en/latest/)

Asisten pencarian makalah berbasis kata kunci yang mengambil hasil dari arXiv,
Semantic Scholar, OpenAlex, PubMed, ACM (via Crossref), IEEE Xplore,
DBLP, Crossref umum, OpenAIRE, Springer Nature, Europe PMC, DOAJ,
HAL, CORE, dan Google Scholar,
menormalkannya ke dalam satu bentuk catatan, dan mengekspor kumpulan
yang telah dideduplikasi sebagai **slide PowerPoint gaya tesis**, **buku
kerja Excel**, dan **berkas BibTeX** — semua dari satu panggilan CLI atau
satu panggilan tool MCP. Opsional, dapat memperkaya setiap makalah dengan
membaca PDF-nya dan menghasilkan ringkasan terstruktur per makalah, baik
dalam konteks (alur LLM-as-agent) maupun via API Anthropic (alur Python
pipeline).

## Untuk agen AI yang menjalankan proyek ini

**Jika Anda LLM (Claude Code, Cursor, Aider, Codex CLI, …) yang membaca
README ini untuk mengetahui apa yang harus dilakukan — mulailah di sini.**
Semua yang di bawah ini juga disematkan di [`AGENTS.md`](AGENTS.md) (cermin
lintas-agen) dan [`CLAUDE.md`](CLAUDE.md) (referensi kanonik); baca itu
sebelum melakukan perubahan non-sepele.

### Apa yang sebenarnya diinginkan pengguna

Deliverable default adalah **satu `.pptx` gaya tesis yang kaya per
makalah**, bukan deck ringan yang hanya-abstrak yang dihasilkan CLI secara
default. Output ringan adalah artefak antara — tugas Anda adalah
meningkatkannya.

### Pohon keputusan

1. Apakah `ANTHROPIC_API_KEY` di-set di environment? → cukup jalankan CLI;
   ia otomatis memperkaya via API Anthropic. Selesai.
2. Tanpa key, tapi Anda (LLM) yang menjalankan sesi → **Anda sendiri yang
   menghasilkan ringkasan kaya**. Baca setiap PDF, tulis-tangan sebuah
   `PaperSummary` dengan field rich-tier (`pain_points`,
   `research_question`, `contributions_detailed`, `headline_metrics`,
   `technique_table`, `method_sections`, `evaluation_sections`,
   `system_flow`, `research_questions`, `rq_results`,
   `core_observation`, `limitations`, `future_work`), letakkan sebuah
   `scripts/regen_<query>.py`, jalankan. **Jangan suruh pengguna men-set
   API key** — Andalah LLM yang seharusnya menulis ringkasan itu.
3. Tanpa LLM di dalam loop (CI / cron / tanpa pengawasan) → output ringan
   dapat diterima.

### Alur MCP 6 langkah

```
1. (opsional) list_sources()                              # lihat plugin mana yang aktif
2. search(keywords, sources, top_tier_only=true, ...)
3. (opsional) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # per makalah
5. (Anda membaca setiap PDF dan menghasilkan dict ringkasan terstruktur)
6. export(papers=[{...paper, "summary": {...}}], language="zh-tw", ...)
```

Ketiga belas tool MCP (termasuk `list_sources`, `list_exports`,
`download_pdfs`, `pptx_inspect` / `pptx_review` / `pptx_update_slide` /
`pptx_add_slide` / dll.)
didokumentasikan di [`docs/mcp.md`](docs/mcp.md).

### Wajib: verifikasi URL / DOI sebelum penyerahan

Jalur URL penerbit **tidak dapat ditebak** — AAAI memakai ID numerik
(`v40i5.37389`), IEEE memakai `arnumber` yang opak, ACM memakai DOI opak.
Saat Anda menulis-tangan sebuah `Paper`, **salin `url` / `doi` / `arxiv_id`
apa adanya dari xlsx pencarian yang menghasilkan run ini** — jangan pernah
dari ingatan, jangan disusun dari judul.

xlsx ditulis ke `exports/<run>/<slug>-<timestamp>.xlsx` dengan
kolom 7 = DOI, kolom 8 = URL. Audit script regen Anda saat Anda
selesai:

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

Dua fabrikasi yang tertangkap dengan cara ini di produksi: volume AAAI
salah (`v39i23.34521` vs sebenarnya `v39i22.34537`) dan jalur slug penulis
yang direka (`view/fang2026` alih-alih `v40i5.37389`).

### Wajib: pangkas unduhan tidak relevan sebelum penyerahan

Pencocokan kata kunci pencarian bersifat berbasis kata kunci, jadi makalah
di luar topik akan menyelinap masuk: kueri "Claude code" mengembalikan
makalah decoder Viterbi karena keduanya mengandung "code"; "LLM code
review" mencocokkan sebuah tinjauan literatur object-detection. Setelah
Anda membaca abstraknya dan mengklasifikasikan sebuah makalah sebagai di
luar topik untuk maksud sebenarnya pengguna, pangkas direktori run:

```python
from pathlib import Path
run = Path("exports/<run>")
irrelevant_keys = ("key-of-off-topic-paper-1", "key-of-off-topic-paper-2")
for key in irrelevant_keys:
    for path in (run / "pdfs" / f"{key}.pdf", run / f"{key}.pptx"):
        if path.exists():
            path.unlink()
```

Hapus `exports/<run>/pdfs/<key>.pdf` + `exports/<run>/<key>.pptx`.
**Pertahankan** `<slug>-<timestamp>.xlsx` / `.bib` agregat — itulah catatan
jujur tentang apa yang dikembalikan pencarian. Kasus ambang mendapat
ringkasan kaya; lebih baik terlalu banyak menyertakan daripada diam-diam
menjatuhkan kemungkinan kecocokan.

### Contoh kerja

[`scripts/regen_fang2026.py`](scripts/regen_fang2026.py) memuat sebuah
ringkasan kaya yang ditulis-tangan persis dengan cara ini (satu makalah,
rich-tier, zh-tw, setiap field rich terisi). Pencarian multi-makalah
mengikuti bentuk yang sama, dengan satu entri
`Paper(...summary=PaperSummary(...))` per makalah di dalam tuple
`PaperCollection`.

### Larangan

- **Jangan** akhiri pencarian multi-makalah dengan menyuruh pengguna "set
  `ANTHROPIC_API_KEY` untuk deck yang kaya" — Andalah LLM yang dapat
  menulis ringkasan itu.
- **Jangan** perlakukan `.pptx` ringan per makalah sebagai
  deliverable.
- **Jangan** berhenti setelah `download_pdfs` melaporkan N PDF disimpan —
  itu awal fase penulisan-kaya, bukan akhir.
- **Jangan** mengarang angka, RQ, kontribusi, atau keterbatasan yang tidak
  ada di makalah.
- **Jangan** memfabrikasi URL / DOI / arXiv ID — lihat aturan di atas.
- **Jangan** meninggalkan unduhan tidak relevan di direktori run.
  Kecocokan pencarian kata kunci dapat menyertakan makalah di luar topik
  (kueri "Claude code" membawa masuk makalah decoder Viterbi; "LLM code
  review" membawa masuk sebuah tinjauan literatur object-detection).
  Setelah mengklasifikasikan makalah sebagai di luar topik, hapus
  `pdfs/<key>.pdf` dan `<key>.pptx` ringannya; pertahankan xlsx / bib
  agregat sebagai catatan jujur tentang apa yang dikembalikan pencarian.
- **Jangan** menyebut "Claude", "Claude Code", "AI-generated", "GPT",
  "Copilot", atau nama tool/model AI apa pun dalam pesan commit, deskripsi
  PR, komentar kode, atau dokumentasi.

## Fitur

- **Lima belas sumber pluggable**: `arxiv`, `semantic_scholar`, `openalex`,
  `pubmed`, `acm` (dibatasi Crossref), `dblp`, `crossref` (umum),
  `openaire`, `springer` (perlu API key), `europepmc` (terbuka, tanpa key —
  ilmu hayati + pracetak + pertanian), `doaj` (terbuka, tanpa key —
  jurnal akses terbuka, biasanya dengan tautan PDF langsung), `hal`
  (terbuka, tanpa key — arsip CS / matematika / fisika Prancis dengan PDF
  teks-penuh), `core` (perlu API key gratis — agregator akses-terbuka
  terbesar, 250 juta+ karya), `ieee` (aktif secara default via Chrome yang
  terlihat; API key menambahkan API Xplore resmi), `scholar` (aktif secara
  default via Chrome yang terlihat). Masing-masing berada di
  `sources/<name>/` di balik adapter `Fetcher`. Berikan `--top-tier-only`
  untuk menyaring hasil ke konferensi/jurnal CS unggulan plus
  Nature/Science/PNAS. Pencarian default mempertahankan semua venue.
- **Mode makalah tunggal**: tempel sebuah arXiv ID, URL arXiv, DOI, PMID,
  atau URL dokumen IEEE — ThesisAgents menyelesaikannya via sumber yang
  tepat dan menghasilkan bundle ekspor yang sama. Berguna untuk catatan
  bacaan makalah dan persiapan sidang tesis.
- **Mode PDF lokal** (`--pdf <path>`): teruskan satu PDF atau sebuah
  direktori. Ekstraktor heuristik menarik **judul, penulis, tahun, arXiv
  ID, DOI, dan abstrak nyata** langsung dari halaman awal setiap PDF
  (terikat pada header eksplisit `Abstract` / `ABSTRACT` / `摘要`, bukan
  prefiks buta). `--title` / `--authors` / `--year` / `--venue` / `--doi` /
  `--arxiv-id` meng-override pada panggilan PDF tunggal; pada sebuah
  direktori, ekstraksi per-file menang sehingga setiap makalah mendapat
  deck-nya sendiri yang dinamai sesuai kunci BibTeX-nya.
- **Delapan eksportir**:
  - `.pptx` — layar lebar 16:9, bernomor halaman, tiga tingkatan render
    (ringan hanya-abstrak · enriched-flat · **gaya tesis** dengan
    kuadran titik-nyeri, sorotan KPI, tabel perbandingan-teknik,
    tabel hasil per-RQ, ringkasan kontribusi, observasi inti,
    keterbatasan & pekerjaan masa depan, Q&A, referensi). Semua string
    template di-i18n ke **14 bahasa**: English, 繁體中文, 简体中文,
    日本語, Español, Français, Deutsch, 한국어, Português, Русский,
    Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia.
  - **Identitas visual deck-yang-dirancang** (bukan tampilan default
    Calibri-di-putih): tipografi per bahasa (Inter untuk Latin, Microsoft
    JhengHei UI / YaHei UI / Yu Gothic UI / Malgun Gothic / Nirmala UI
    untuk CJK + Hindi), geometri aksen secara programatik (bar aksen atas
    di setiap slide konten + band kiri pada sampul), pemformatan tabel
    bergaya akademik (grid default dihapus, aturan header navy, divider
    antar-baris lembut, strip baris bergantian, alignment vertikal-tengah,
    label baris tebal), dan disiplin palet lima warna (navy / teal /
    grey / light / white) dengan merah **dilarang** untuk teks (gunakan
    bold + teal `#0E7490` untuk penekanan sebagai gantinya).
  - **Mode terang adalah jalur render default.** Berikan `--dark-mode`,
    aktifkan **Dark mode** di tab Deck GUI, atau set
    `ExportOptions(dark_mode=True)` untuk menerapkan post-pass gelap (latar
    slide `#12151B`, teks body `#E5E7EB`).
  - `.xlsx` — sheet Papers + sheet asal-usul Query, URL / PDF dengan
    hyperlink, header dibekukan, lebar kolom otomatis. Kolom 5
    (**Source**) menunjukkan venue publikasi sebenarnya (mis. "IEEE
    Access"); kolom 6 (**Indexed via**) menunjukkan fetcher mana yang
    mengembalikan metadata (mis. "openalex"), sehingga kedua informasi itu
    tidak pernah bertabrakan.
  - `.md` — daftar lengkap sumber / judul / abstrak.
  - `.bib` — kunci sitasi bebas-tabrakan, field dengan escape LaTeX.
  - `.json` — payload mentah untuk tooling hilir.
  - `.ris` — pertukaran RIS yang diimpor oleh Zotero / Mendeley / EndNote /
    RefWorks (saudara BibTeX untuk pengelola referensi non-LaTeX).
  - `.csv` — tabel datar satu-baris-per-makalah untuk spreadsheet / triase
    grep cepat (pengutipan RFC-4180, jadi koma dalam judul tidak pernah
    menggeser kolom).
  - `.csl.json` — CSL-JSON untuk Pandoc / citeproc; render bibliografi
    dalam gaya CSL apa pun (APA, IEEE, Nature, …). Ekstensi `.csl.json`
    membuatnya tetap berbeda dari dump `.json` biasa.
- **Toolkit edit PPT**: `thesisagents.exporters.pptx_edit`
  (inspect / update_slide / delete_slide / reorder_slides / add_slide)
  bekerja terhadap deck apa pun yang dihasilkan eksportir, plus tool MCP
  `pptx_*` setara sehingga agen LLM dapat beriterasi di atas deck yang
  telah dibuat.
- **Server MCP**: 13 tool — `list_sources` + `list_exports`
  (discovery), `search`, `fetch_paper`, `fetch_pdf_text`,
  `download_pdfs`, `export`, dan enam tool deck `pptx_*`
  (`inspect`, `review`, `update_slide`, `delete_slide`,
  `reorder_slides`, `add_slide`). Memungkinkan
  LLM apa pun yang sadar-MCP
  (Claude Code, Claude Desktop, Cursor, …) menjalankan seluruh alur.
- **Dua jalur pengayaan** untuk melampaui abstrak menuju deck gaya tesis
  sejati:
  - **LLM-as-agent (tanpa API key)** — LLM pemanggil membaca teks tubuh
    PDF via `fetch_pdf_text`, menulis ringkasan terstruktur dalam konteks,
    dan meneruskannya ke `export`.
  - **Pipeline Python (`--enrich`)** — CLI memanggil API Anthropic
    sendiri; model default `claude-opus-4-7`.
- **Alur publisher via-Chrome yang terlihat**: SERP Scholar, IEEE
  `/rest/search`, dan setiap unduhan PDF-berbayar (ieeexplore / dl.acm /
  link.springer / sciencedirect / wiley / oup / nature / science / …)
  berjalan di dalam sesi Chrome nyata yang terlihat via `selenium`.
  Pengguna menyelesaikan captcha / menyelesaikan SSO di jendela langsung
  sekali; `THESISAGENTS_CHROME_PROFILE_DIR` mempertahankan cookie lintas
  run.
- **Alur LLM-as-agent**: tool MCP menyediakan pencarian, unduhan PDF, dan
  ekstraksi teks. `scripts/regen_*.py` memuat contoh reproducible untuk
  menulis-tangan sebuah `PaperSummary` kaya per makalah.
- **Resolver PDF OA**: pasca-dedup, setiap makalah tanpa `pdf_url`
  melalui Unpaywall → S2 `openAccessPdf` → pencarian judul arXiv →
  CORE.ac.uk (bila key di-set). Peningkatan tipikal pada kueri yang padat
  IEEE / ACM / Springer / Elsevier: 40-70 poin persentase.
- **Aman secara default**: transport HTTP hanya-HTTPS, rate limit per
  sumber (token bucket), `defusedxml` untuk payload XML apa pun,
  jalur ekspor aman dari path-traversal, tanpa `eval` / `exec` / `pickle`
  pada input pengguna.
- **Penjaga kosakata zh-tw / zh-cn**: ~244 pola regex di
  `tests/test_i18n.py::test_zh_tw_files_use_traditional_chinese_vocabulary`
  menangkap kata pinjaman Tionghoa-Sederhana yang dirender dengan hanzi
  Tradisional (mis. `內存` → `記憶體`, `魯棒性` → `穩健性`, `軟件` → `軟體`,
  `緩存` → `快取`). Penjaga yang sama berjalan terbalik untuk string
  lokal zh-cn. Aturan lengkap + katalog regex ada di
  `.claude/agents/rules/language-vocabulary-check.md`.

## Mulai cepat

```powershell
git clone <repo-url>
cd ThesisAgents
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Pasang dengan dev extras (juga membawa SDK MCP dan deps intelligence)
pip install -e .[dev]
```

Cari arXiv dan ekspor deck + workbook + BibTeX (default untuk `--query`):

```powershell
py -m thesisagents --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

Ambil satu makalah berdasarkan URL — default `.pptx + .bib` (`.xlsx`
kurang masuk akal untuk satu baris):

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

Render deck dalam 繁體中文:

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --lang zh-tw --out .\exports\
```

Pengayaan via pipeline LLM (Python memanggil Anthropic sendiri — perlu API key):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang zh-tw --out .\exports\
```

## Flag CLI

| Flag | Tujuan |
|---|---|
| `--query` / `-q` | Kata kunci (wajib kecuali `--paper`). |
| `--paper` / `-p` | ID / URL arXiv, DOI, PMID, atau URL dokumen IEEE. Eksklusif dengan `--query`. |
| `--source` / `-s` | Daftar sumber dipisah koma. Default `arxiv`. |
| `--max` / `-n` | Hasil maksimum per sumber (1..200). Default 25. |
| `--year-from` / `--year-to` | Filter tahun inklusif. |
| `--export` / `-e` | Format: kombinasi dari `pptx,xlsx,md,bib,json,ris,csv,csl`. Default bergantung mode (lihat bawah). |
| `--out` / `-o` | Direktori output. Default `./exports`. |
| `--filename-stem` | Override stem nama berkas yang dihasilkan. |
| `--no-abstract` | Hilangkan konten abstrak dari ekspor. |
| `--lang` / `-l` | Bahasa deck: salah satu dari 14 — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. Default `en`. |
| `--enrich` | Varian fail-loud dari auto-enrich. Butuh `ANTHROPIC_API_KEY` dan extra `[intelligence]`. (Auto-enrich adalah default saat key di-set.) |
| `--lightweight` | Lewati pengayaan + paksa deck hanya-abstrak. Gunakan hanya untuk run cepat / tanpa-pengawasan; **saat agen LLM yang menjalankan, utamakan alur LLM-as-agent** di bawah. |
| `--llm-model` | Override default `claude-opus-4-7` untuk pengayaan. |
| `--no-pdf` | Lewati unduhan PDF otomatis. Juga menonaktifkan gate PPT per-makalah (tanpa PDF → tanpa konten penuh). |
| `--no-oa-resolve` | Lewati resolver PDF OA pasca-dedup (Unpaywall + S2 + arXiv + CORE.ac.uk). |
| `--top-tier-only` | Batasi hasil ke arXiv + whitelist CS-unggulan terkurasi (S&P, CCS, NDSS, USENIX Security, NeurIPS, ICML, ICSE, …). Nonaktif secara default. |
| `--paywall-threshold` | Fraksi hasil berbayar yang memicu prompt konfirmasi. Default 0.30. |
| `--yes` | Lewati prompt paywall dan lanjutkan. |
| `--max-slides` | Batas slide per-makalah (default 25; berikan 0 untuk tanpa batas). |
| `--dark-mode` | Render pptx dengan latar gelap + teks hampir-putih. Default adalah deck terang band-navy. |
| `--quiet` | Tekan cetakan per-makalah. |

### Variabel lingkungan

| Variabel | Dipakai oleh | Tujuan |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | Auth LLM. Tidak perlu untuk jalur LLM-as-agent via MCP. |
| `THESISAGENTS_LLM_MODEL` | `--enrich` | Override default `claude-opus-4-7`. |
| `THESISAGENTS_S2_API_KEY` | Semantic Scholar + resolver OA | Rate limit lebih tinggi; juga dipakai langkah S2 `openAccessPdf` pada resolver OA. Key gratis di <https://www.semanticscholar.org/product/api>. |
| `THESISAGENTS_NCBI_API_KEY` | PubMed | Menaikkan limit anonim NCBI (3/s) ke 10/s. Opsional. |
| `THESISAGENTS_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex, **Unpaywall** | Tag polite-pool + mengaktifkan langkah Unpaywall pada resolver OA (kemenangan cakupan-PDF terbesar untuk makalah berbayar IEEE / ACM / Springer / Elsevier; peningkatan tipikal 40-70 pp). |
| `THESISAGENTS_IEEE_API_KEY` | IEEE (jalur API) | API IEEE Xplore resmi; memunculkan `pdf_url` untuk makalah dalam cakupan. |
| `THESISAGENTS_DISABLE_IEEE_SCRAPING` | IEEE | **IEEE aktif secara default via Chrome yang terlihat.** Set `=1` untuk opt out (mis. CI tanpa Chrome). Cabang scrape httpx hanya berjalan sebagai fallback saat WebRunner tidak tersedia. |
| `THESISAGENTS_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Token pelanggan Crossref Plus (header Bearer). Opsional. |
| `THESISAGENTS_SPRINGER_API_KEY` | Springer | Wajib; key gratis dari <https://dev.springernature.com/>. Plugin memunculkan `ConfigError` tanpa itu. |
| `THESISAGENTS_DISABLE_SCHOLAR_SCRAPING` | Google Scholar | **Scholar aktif secara default via Chrome yang terlihat.** Set `=1` untuk opt out (ToS Google melarang akses otomatis — default-aktif demi cakupan, opt-out untuk menghindari risiko captcha / blokir-IP). |
| `THESISAGENTS_CHROME_PROFILE_DIR` | Unduhan Scholar + IEEE + PDF-berbayar | `--user-data-dir` Chrome yang persisten. Set ini dan selesaikan VPN / SSO / sign-in Google sekali; run berikutnya mewarisi cookie sehingga IEEE mengembalikan metadata berbayar dan Scholar menyajikan SERP tanpa-throttle. |
| `THESISAGENTS_DISABLE_WEBRUNNER` | Unduhan Scholar + IEEE + PDF-berbayar | `=1` memaksa jalur httpx alih-alih menggerakkan Chrome nyata. Berguna untuk CI / Docker tanpa biner Chrome; jika tidak, biarkan tak-diset. |
| `THESISAGENTS_CORE_API_KEY` | Resolver OA + sumber pencarian `core` | Key gratis dari <https://core.ac.uk/services/api>. Mengaktifkan langkah OA-lookup CORE.ac.uk (200 juta+ item OA institusional / regional) **dan** sumber pencarian `core`. Tanpa itu, sumber `core` dilewati diam-diam dan strategi OA lain (Unpaywall, S2, arXiv) tetap berjalan. |
| `THESISAGENTS_PDF_COOKIES_FILE` | Pengunduh PDF | `cookies.txt` format Netscape. Default mati. Gunakan hanya dengan penerbit yang atasnya Anda punya hak institusi. |
| `THESISAGENTS_LOG_LEVEL` | logger | Default `INFO`; `DEBUG` untuk jejak verbose. |

Default: `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. Selalu
dapat di-override dengan `--export` eksplisit.

## Alur LLM-as-agent

Saat LLM di editor Anda menjalankan alur, gunakan tool MCP secara
berurutan: `search`, `download_pdfs`, `fetch_pdf_text`, lalu `export`
dengan sebuah `PaperSummary` kaya yang ditulis-tangan. Berkas
`scripts/regen_*.py` yang ada adalah contoh reproducible untuk langkah
penulisan dan ekspor akhir.

Runbook end-to-end lengkap (pencarian → deck kaya) ada di
`.claude/agents/tasks/paper-summary-author.md` — buka itu sebelum memulai
kueri baru sehingga LLM dapat menjalankan alur tanpa jeda menunggu input
pengguna.

## Server MCP

Daftarkan ke Claude Code:

```powershell
claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp
```

Atau tulis ke berkas pengaturan Anda:

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

Tool:

| Tool | Tujuan |
|---|---|
| `list_sources` | Mendaftar setiap plugin + melaporkan apakah masing-masing aktif di env saat ini. Panggil ini sekali sebelum `search`. |
| `list_exports` | Mendaftar setiap format ekspor dengan deskripsi satu-barisnya dan apakah ia menulis satu berkas agregat atau satu berkas per makalah. |
| `search` | Kata kunci → daftar makalah. Menerima `top_tier_only`, `min_citations`; default ke campuran sumber tanpa-API-key penuh. |
| `fetch_paper` | Identifier arXiv / DOI / PMID / IEEE → satu makalah. |
| `fetch_pdf_text` | Unduh satu PDF, kembalikan teks tubuh hasil ekstraksi. **Jalur MCP menuju "saya membaca makalahnya".** |
| `download_pdfs` | Unduh PDF daftar makalah secara batch ke `{out_dir}/pdfs/`. Mengembalikan hasil per-makalah berindeks kunci BibTeX. |
| `export` | Daftar makalah + format → menulis `.pptx/.xlsx/.md/.bib/.json/.ris/.csv/.csl.json`. Menerima field `summary` per makalah untuk skema gaya-tesis yang kaya, `max_slides_per_paper` (default 25), dan `dark_mode` (default `false` — default proyek adalah deck terang band-navy, berikan `true` untuk post-pass gelap OLED / minim-cahaya). |
| `pptx_inspect` | Membaca struktur slide / shape dari deck yang ada. |
| `pptx_review` | Audit deck dalam satu panggilan — overflow + kontrak warna + kelengkapan bagian `paper_rule`. Mendeteksi bahasa deck secara otomatis; juga CLI `python -m thesisagents review <deck.pptx>`. |
| `pptx_update_slide` | Mengganti `title` / `body` / `meta` (berdasarkan nama shape) atau shape sembarang berdasarkan indeks. |
| `pptx_delete_slide` | Menghapus slide dan part relationship-nya. |
| `pptx_reorder_slides` | Mempermutasi slide via `sldIdLst`. |
| `pptx_add_slide` | Menambahkan ke akhir atau menyisipkan slide title / body / meta baru. |

Alur LLM-as-agent (tanpa `ANTHROPIC_API_KEY` — LLM-nya sendiri yang menjadi agen):

```
1. (opsional) list_sources()                       # temukan plugin yang aktif
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (opsional) download_pdfs(papers, out_dir="./exports/...")  # persistkan PDF
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # per makalah
5. (LLM membaca teks tubuh, menghasilkan dict `summary` terstruktur)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="zh-tw", formats=["pptx","bib"], dark_mode=true, ...)
```

Referensi lengkap di [`docs/mcp.md`](docs/mcp.md).

## Tata letak proyek

```
ThesisAgents/
├── thesisagents/                 # paket utama
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # client async HTTPS-only, rate limit token-bucket
│   ├── exporters/                   # pptx (gaya tesis) · xlsx · bib · md · json · ris · csv · csl · pptx_edit · i18n
│   ├── intelligence/                # unduh PDF + summarizer Anthropic  (extra [intelligence])
│   ├── evaluation/                  # benchmark kualitas-pencarian offline (docs/search-quality.md)
│   ├── mcp/                         # server FastMCP (13 tool)
│   ├── sources/<name>/              # folder plugin: arxiv, semantic_scholar,
│   │                                #   openalex, pubmed, acm, ieee, scholar,
│   │                                #   dblp, crossref, openaire, springer,
│   │                                #   europepmc, doaj, hal, core
│   ├── utils/                       # logging, keamanan path
│   ├── cli.py                       # CLI argparse
│   └── __main__.py
├── tests/                           # suite pytest + fixture terekam (tanpa HTTP langsung)
├── docs/                            # Sphinx (14 pohon bahasa)
├── scripts/                         # skrip regen sekali-pakai
└── pyproject.toml                   # ruff, bandit, build, extras opsional
```

## Definition of Done

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r thesisagents/
```

Flag `-c` pada bandit wajib — tanpa itu bandit mengabaikan konfigurasi skip
proyek. Saat menyentuh eksportir pptx, jalankan juga pemeriksaan overflow
(lihat `CLAUDE.md` "Slide Deck Rules").

## GUI Desktop (PySide6)

Antarmuka desktop native tersedia di balik extra `[gui]`:

```powershell
pip install thesisagents[gui]
thesisagents-gui                 # atau: thesisagents gui
```

Jendela memiliki empat tab — **Search**, **Settings** (mempertahankan API
key via QSettings), **Enrich** (menggerakkan pengayaan LLM-as-agent /
Python-pipeline lewat sinyal `collection_ready`), dan **Deck** (kontrol
toggle mode Terang + batas-slide + max-figures mengalir ke
`ExportOptions`). Zip rilis Windows memuat bundle terkompilasi-Nuitka
dengan PySide6 disertakan, jadi `thesisagents.exe gui` bekerja tanpa
instalasi Python terpisah.
**UI hadir dalam semua 14 bahasa** (English, 繁體中文, 简体中文,
日本語, Español, Français, Deutsch, 한국어, Português, Русский,
Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia) — run pertama memilih
bahasa dari locale OS Anda, lalu **Settings → Interface language**
memungkinkan Anda mengubahnya. Bahasa output deck adalah dropdown
terpisah sehingga Anda dapat menjalankan UI dalam satu bahasa dan
menghasilkan slide dalam bahasa lain. Tata letaknya responsif: setiap
form berada dalam sebuah `QScrollArea` dan jendela mengecil hingga
900×600 (masih muat 720p), dengan penskalaan HiDPI aktif secara default.

Referensi lengkap: [`docs/gui.md`](docs/gui.md).

## Pemaketan sebagai executable mandiri

Dua packager didokumentasikan untuk mengirim biner satu-berkas yang
berjalan tanpa Python terpasang:

- **[`docs/packaging-pyinstaller.md`](docs/packaging-pyinstaller.md)**
  — build cepat (di bawah satu menit), output 200–300 MB, startup 2–4 s.
  Terbaik saat Anda beriterasi pada skrip build.
- **[`docs/packaging-nuitka.md`](docs/packaging-nuitka.md)** —
  build lambat (5–15 menit), output 80–150 MB, startup sub-detik,
  ada proteksi bytecode. Terbaik saat pengguna akhir menjalankan biner
  berkali-kali.

Kedua dokumen membahas jebakan spesifik-proyek — plugin sumber dinamis di
bawah `sources/<name>/` — dan menyertakan perintah terverifikasi untuk
titik masuk CLI dan server MCP.

## Continuous integration & rilis

Dua workflow GitHub Actions ada di bawah `.github/workflows/`:

- **`ci.yml`** berjalan pada setiap push dan PR ke `main`. Matriks-nya
  Ubuntu + Windows × Python 3.12 / 3.13 / 3.14 (6 job). Setiap job
  menjalankan `ruff check`, `bandit -c pyproject.toml`, dan `pytest`.
- **`release.yml`** menunggu `ci.yml` selesai di `main`
  (pemicu `workflow_run`). Ia berjalan hanya jika CI berhasil. **Setiap
  push CI-berhasil ke `main` adalah sebuah rilis** — workflow otomatis
  menaikkan versi patch di `pyproject.toml`, meng-commit kenaikan itu
  kembali ke `main` sebagai `chore: bump version to X.Y.Z`, dan
  mem-pipeline:
  1. **`bump-version`** — baca `X.Y.Z` saat ini dari `pyproject.toml`,
     naikkan ke `X.Y.(Z+1)`, commit + push kembali ke `main` menggunakan
     `GITHUB_TOKEN` workflow. Push itu TIDAK memicu ulang CI (sesuai
     aturan GitHub bahwa push yang digerakkan `GITHUB_TOKEN` tidak dapat
     memulai run workflow baru), sehingga siklus berakhir secara alami.
  2. **`publish-pypi`** — build sdist + wheel, `twine check`,
     `twine upload` via `PYPI_API_TOKEN`.
  3. **`create-draft-release`** — buka sebuah rilis GitHub *draft* pada
     tag `v<version>` dengan catatan yang dibuat otomatis.
  4. **`build-nuitka`** — kompilasi bundle standalone Nuitka pada runner
     Windows (titik masuk: `python -m thesisagents` via
     `--python-flag=-m`), smoke-test, zip folder `thesisagents.dist/`
     hasilnya, dan lampirkan zip + checksum `.sha256` ke rilis draft.
     Standalone (bukan onefile) secara desain: onefile mengekstraksi-diri
     ke `%TEMP%` pada setiap peluncuran, menambah latensi startup dan
     memicu heuristik antivirus pada mesin yang terkunci. Windows-saja
     juga secara desain: pengguna Linux / macOS memasang dari PyPI.
     Cache build berkunci pada `pyproject.toml` memangkas build hangat
     dari ~85 menit dingin menjadi ~5–10 menit.
  5. **`publish-release`** — batalkan tanda draft begitu aset Nuitka
     terunggah, sehingga pengguna tidak pernah melihat rilis
     setengah-jadi.

  **Melewati sebuah rilis.** Sertakan `[skip release]` di mana pun dalam
  pesan commit dan kenaikan + setiap job hilir dilewati — gunakan ini
  untuk commit khusus-docs / typo / refactor yang tidak seharusnya
  membakar nomor versi.

Untuk mengaktifkan publikasi PyPI + executable rilis:

1. Buat token API bercakupan-proyek di
   <https://pypi.org/manage/account/token/>.
2. Di repo GitHub: `Settings → Secrets and variables → Actions →
   New repository secret`. Namai `PYPI_API_TOKEN` dan tempel nilai
   token-nya.
3. Izinkan GitHub Actions mem-push ke `main`: `Settings → Actions →
   General → Workflow permissions → Read and write permissions`. Commit
   kenaikan di-push oleh `GITHUB_TOKEN` workflow.
4. Potong rilis dengan me-merge PR ke `main`. Pipeline memakan
   ~3–5 menit untuk publikasi ke PyPI dan ~80–90 menit lagi (dingin) atau
   ~5–10 menit (cache Nuitka hangat) agar zip Windows terlampir.

Job `publish-pypi` sengaja TIDAK melampirkan sebuah GitHub Environment,
jadi setiap run muncul sebagai entri Release (dengan `.exe` Nuitka-nya
terlampir) alih-alih sebagai widget sidebar "Deployment" di beranda repo
— rilis mendapat halaman khusus tersendiri dan sebuah entri Deployment
di atasnya hanya akan menjadi kebisingan yang berlebihan.

## Lisensi

Lihat `LICENSE`. API arXiv digunakan menurut ketentuan penggunaan API
arXiv (<https://info.arxiv.org/help/api/tou.html>) — patuhi batas lunak
1 permintaan per 3 detik; fetcher bawaan sudah menerapkannya via
token bucket-nya.
