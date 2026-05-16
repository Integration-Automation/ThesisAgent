# AutoPaperToPPT

[![CI](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![Python](https://img.shields.io/pypi/pyversions/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/AutoPaperToPPT.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/autopapertoppt/badge/?version=latest)](https://autopapertoppt.readthedocs.io/en/latest/)

> **Bahasa**: [English](README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · **Bahasa Indonesia**
> **Dokumentasi**: [autopapertoppt.readthedocs.io](https://autopapertoppt.readthedocs.io/en/latest/)

Asisten pencarian makalah berbasis kata kunci. Mengambil hasil dari arXiv, Semantic Scholar, OpenAlex, PubMed, ACM (via Crossref), IEEE Xplore, DBLP, Crossref umum, OpenAIRE, Springer Nature, dan Google Scholar; menormalkannya ke satu format catatan; dan mengekspor kumpulan yang telah dideduplikasi sebagai **slide PowerPoint gaya tesis**, **buku kerja Excel**, dan **berkas BibTeX** — semua dari satu panggilan CLI atau satu panggilan tool MCP. Opsional, dapat memperkaya setiap makalah dengan membaca PDF-nya dan menghasilkan ringkasan terstruktur, baik dalam konteks (alur LLM-as-agent) atau via API Anthropic (alur Python pipeline).

## Untuk agen AI yang menjalankan proyek ini

**Jika Anda LLM (Claude Code, Cursor, Aider, Codex CLI, …) yang membaca README ini untuk mengetahui apa yang harus dilakukan — mulailah di sini.** Aturan yang sama juga disematkan di [`AGENTS.md`](AGENTS.md) (cermin lintas-agen) dan [`CLAUDE.md`](CLAUDE.md) (referensi resmi); baca itu sebelum perubahan non-sepele.

### Apa yang sebenarnya diinginkan pengguna

Deliverable default adalah **satu `.pptx` gaya tesis yang diperkaya per makalah**, bukan deck ringan yang hanya-abstrak yang dihasilkan CLI secara default. Output ringan adalah artefak antara — tugas Anda adalah meningkatkannya.

### Pohon keputusan

1. Apakah `ANTHROPIC_API_KEY` di-set di environment? → cukup jalankan CLI; ia otomatis memperkaya via API Anthropic. Selesai.
2. Tanpa key, tapi Anda (LLM) menjalankan sesi → **Anda menyusun ringkasan diperkaya sendiri**. Baca setiap PDF, tulis tangan `PaperSummary` dengan field rich-tier (`pain_points`, `research_question`, `contributions_detailed`, `headline_metrics`, `technique_table`, `method_sections`, `evaluation_sections`, `system_flow`, `research_questions`, `rq_results`, `core_observation`, `limitations`, `future_work`), letakkan `scripts/regen_<query>.py` dan jalankan. **Jangan suruh pengguna men-set API key** — Andalah LLM yang seharusnya menulis ringkasan.
3. Tanpa LLM di loop (CI / cron / tanpa pengawasan) → output ringan dapat diterima.

### Alur MCP 6 langkah

```
1. (opsional) list_sources()                              # plugin mana yang aktif
2. search(keywords, sources, top_tier_only=true, ...)
3. (opsional) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # per makalah
5. (Anda membaca setiap PDF dan menghasilkan dict ringkasan terstruktur)
6. export(papers=[{...paper, "summary": {...}}], language="id", ...)
```

Sebelas tool MCP (termasuk `list_sources`, `download_pdfs`, `pptx_inspect` / `pptx_update_slide` / `pptx_add_slide` dll.) didokumentasikan di [`docs/mcp.md`](docs/mcp.md).

### Wajib: verifikasi URL / DOI sebelum penyerahan

Jalur URL penerbit **tidak dapat ditebak** — AAAI memakai ID numerik (`v40i5.37389`), IEEE memakai `arnumber` opak, ACM memakai DOI opak. Saat menulis tangan `Paper`, **salin `url` / `doi` / `arxiv_id` apa adanya dari xlsx yang dihasilkan pencarian ini** — jangan pernah dari ingatan, jangan disusun dari judul.

xlsx ditulis ke `exports/<run>/<slug>-<timestamp>.xlsx` dengan kolom 7 = DOI, kolom 8 = URL. Audit script regen Anda saat selesai:

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

Dua fabrikasi yang tertangkap dengan cara ini di produksi: volume AAAI salah (`v39i23.34521` vs sebenarnya `v39i22.34537`) dan jalur slug penulis yang direka (`view/fang2026` alih-alih `v40i5.37389`).

### Contoh kerja

[`scripts/regen_llm_security_batch.py`](scripts/regen_llm_security_batch.py) memuat 8 ringkasan diperkaya yang ditulis tangan persis dengan proses ini. Gunakan sebagai template untuk pencarian multi-makalah. Pasangan zh-tw ada di [`scripts/regen_llm_security_batch_zh_tw.py`](scripts/regen_llm_security_batch_zh_tw.py).

### Larangan

- **Jangan** akhiri pencarian multi-makalah dengan menyuruh pengguna "set `ANTHROPIC_API_KEY` untuk deck diperkaya" — Andalah LLM yang dapat menulis ringkasan.
- **Jangan** perlakukan `.pptx` ringan per makalah sebagai deliverable.
- **Jangan** berhenti saat `download_pdfs` melaporkan "N PDF disimpan" — itu awal fase penulisan rich, bukan akhir.
- **Jangan** mengarang angka, RQ, kontribusi, atau keterbatasan yang tidak ada di makalah.
- **Jangan** memfabrikasi URLs / DOIs / arXiv IDs — lihat aturan di atas.
- **Jangan** meninggalkan unduhan tidak relevan di direktori run. Pencarian kata kunci kadang menyertakan makalah yang tidak terkait dengan topik (kueri "Claude code" membawa makalah tentang decoder Viterbi; "LLM code review" membawa tinjauan literatur object detection). Setelah mengklasifikasikan sebagai tidak relevan, hapus `pdfs/<key>.pdf` dan `<key>.pptx` ringannya; pertahankan xlsx / bib agregat sebagai catatan jujur tentang apa yang dikembalikan pencarian.
- **Jangan** menyebut "Claude", "Claude Code", "AI-generated", "GPT", "Copilot", atau nama tool/model AI lain dalam pesan commit, deskripsi PR, komentar kode, atau dokumentasi.

## Fitur

- **Sebelas sumber pluggable**: `arxiv`, `semantic_scholar`, `openalex`, `pubmed`, `acm` (dibatasi ACM via Crossref), `dblp`, `crossref` (umum), `openaire`, `springer` (perlu API key), `ieee` (API key atau scraping opt-in), `scholar` (scraping opt-in). Masing-masing berada di `sources/<name>/` di balik adapter `Fetcher`. Whitelist venue tingkat-atas menyaring hasil ke konferensi/jurnal CS unggulan + Nature/Science/PNAS secara default; `--all-venues` menonaktifkannya.
- **Mode makalah tunggal**: tempel arXiv ID, URL arXiv, DOI, PMID, atau URL dokumen IEEE — AutoPaperToPPT menyelesaikannya via sumber yang tepat dan menghasilkan bundle ekspor yang sama. Berguna untuk catatan bacaan dan persiapan sidang.
- **Mode PDF lokal** (`--pdf <path>`): teruskan satu PDF atau direktori. Ekstraktor heuristik menarik **judul, penulis, tahun, arXiv ID, DOI, dan abstrak nyata** langsung dari awal setiap PDF (terikat ke header eksplisit `Abstract` / `ABSTRACT` / `摘要`, bukan prefiks buta). `--title` / `--authors` / `--year` / `--venue` / `--doi` / `--arxiv-id` meng-override pada panggilan PDF tunggal; di mode direktori, ekstraksi per-file menang — setiap makalah mendapat deck-nya sendiri dengan nama kunci BibTeX-nya.
- **Lima eksportir**:
  - `.pptx` — 16:9 lebar, bernomor halaman, tiga tingkatan render (ringan hanya-abstrak · enriched-flat · **gaya tesis** dengan kuadran titik nyeri, KPI menonjol, tabel perbandingan teknik, tabel hasil per RQ, ringkasan kontribusi, observasi inti, keterbatasan & pekerjaan masa depan, Q&A, referensi). Semua string template di-i18n ke **14 bahasa**: English, 繁體中文, 简体中文, 日本語, Español, Français, Deutsch, 한국어, Português, Русский, Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia.
  - `.xlsx` — sheet Papers + sheet asal Query, URL / PDF dengan hyperlink, header dibekukan, lebar kolom otomatis. Kolom 5 (**Source**) menunjukkan tempat publikasi sebenarnya (mis. "IEEE Access"); kolom 6 (**Indexed via**) menunjukkan fetcher mana yang mengembalikan metadata (mis. "openalex"), agar kedua informasi tidak tertukar.
  - `.md` — daftar lengkap sumber / judul / abstrak.
  - `.bib` — kunci sitasi bebas tabrakan, field dengan escape LaTeX.
  - `.json` — payload mentah untuk tooling hilir.
- **Toolkit edit PPT**: `autopapertoppt.exporters.pptx_edit` (inspect / update_slide / delete_slide / reorder_slides / add_slide) bekerja terhadap deck apa pun yang dihasilkan eksportir, plus tool MCP setara `pptx_*` agar agen LLM dapat beriterasi di atas deck yang sudah dibuat.
- **Server MCP**: 11 tool — `list_sources` (discovery), `search`, `fetch_paper`, `fetch_pdf_text`, `download_pdfs`, `export`, dan lima tool edit `pptx_*`. Memungkinkan LLM apa pun yang kompatibel MCP (Claude Code, Claude Desktop, Cursor, …) menjalankan seluruh alur.
- **Dua jalur pengayaan** untuk melampaui abstrak menuju deck gaya tesis sejati:
  - **LLM-as-agent (tanpa API key)** — LLM pemanggil membaca teks PDF via `fetch_pdf_text`, menulis ringkasan terstruktur dalam konteks, dan meneruskannya ke `export`.
  - **Pipeline Python (`--enrich`)** — CLI memanggil API Anthropic sendiri; model default `claude-opus-4-7`.
- **Aman secara default**: transport HTTP hanya-HTTPS, rate limit per sumber (token bucket), `defusedxml` untuk payload XML apa pun, jalur ekspor aman dari path-traversal, tanpa `eval` / `exec` / `pickle` pada input pengguna. Scraping Scholar dan IEEE nonaktif secara default (opt-in via env var).

## Mulai cepat

```powershell
git clone <repo-url>
cd AutoPaperToPPT
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Pasang dengan dev extras (juga membawa SDK MCP dan deps intelligence)
pip install -e .[dev]
```

Cari arXiv dan ekspor deck + workbook + BibTeX (default untuk `--query`):

```powershell
py -m autopapertoppt --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

Ambil satu makalah by URL — default `.pptx + .bib` (`.xlsx` satu baris kurang masuk akal):

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

Render deck dalam Bahasa Indonesia:

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --lang id --out .\exports\
```

Pengayaan via pipeline LLM (Python memanggil Anthropic — perlu API key):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang id --out .\exports\
```

## Flag CLI

| Flag | Tujuan |
|---|---|
| `--query` / `-q` | Kata kunci (wajib kecuali `--paper`). |
| `--paper` / `-p` | ID/URL arXiv, DOI, PMID, atau URL dokumen IEEE. Eksklusif dengan `--query`. |
| `--source` / `-s` | Daftar sumber dipisah koma. Default `arxiv`. |
| `--max` / `-n` | Hasil maksimum per sumber (1..200). Default 25. |
| `--year-from` / `--year-to` | Filter tahun inklusif. |
| `--export` / `-e` | Format: kombinasi dari `pptx,xlsx,md,bib,json`. Default bergantung mode (lihat bawah). |
| `--out` / `-o` | Direktori output. Default `./exports`. |
| `--filename-stem` | Override stem nama file yang dihasilkan. |
| `--no-abstract` | Hilangkan konten abstrak dari ekspor. |
| `--lang` / `-l` | Bahasa deck: salah satu dari 14 — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. Default `en`. |
| `--enrich` | Unduh PDF + ringkasan Anthropic. Butuh `ANTHROPIC_API_KEY` dan extra `[intelligence]`. |
| `--lightweight` | Paksa deck ringan walau `ANTHROPIC_API_KEY` di-set. |
| `--llm-model` | Override model default `claude-opus-4-7`. |
| `--all-venues` | Nonaktifkan whitelist tingkat-atas (default tetap venue CS unggulan + Nature / Science / PNAS / CACM / LNCS). |
| `--paywall-threshold` | Fraksi hasil paywall yang memicu konfirmasi. Default 0.30. |
| `--yes` | Lewati prompt paywall. |
| `--max-slides` | Batas slide per makalah (default 25; 0 untuk tanpa batas). |
| `--quiet` | Tekan output per makalah. |

### Variabel lingkungan

| Variabel | Dipakai oleh | Tujuan |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | Auth LLM. Tidak perlu untuk jalur LLM-as-agent via MCP. |
| `AUTOPAPERTOPPT_LLM_MODEL` | `--enrich` | Override default `claude-opus-4-7`. |
| `AUTOPAPERTOPPT_S2_API_KEY` | Semantic Scholar | Rate limit lebih tinggi. Opsional. |
| `AUTOPAPERTOPPT_NCBI_API_KEY` | PubMed | Menaikkan limit anonim NCBI (3/s) ke 10/s. Opsional. |
| `AUTOPAPERTOPPT_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex | Menempatkan permintaan ke polite pool Crossref. |
| `AUTOPAPERTOPPT_IEEE_API_KEY` | IEEE (jalur API) | API resmi IEEE Xplore; mengekspos `pdf_url` untuk makalah dalam cakupan. |
| `AUTOPAPERTOPPT_ENABLE_IEEE_SCRAPING` | IEEE (jalur scraping) | `=1` mengaktifkan scraping. Tidak perlu saat API key sudah diset. |
| `AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Token pelanggan Crossref Plus (header Bearer). Opsional. |
| `AUTOPAPERTOPPT_SPRINGER_API_KEY` | Springer | Wajib; kunci gratis di <https://dev.springernature.com/>. Tanpa kunci, plugin dilewati diam-diam. |
| `AUTOPAPERTOPPT_ENABLE_SCHOLAR_SCRAPING` | Google Scholar | `=1` mengaktifkan scraping. Default mati — ToS Scholar melarang scraping. |
| `AUTOPAPERTOPPT_PDF_COOKIES_FILE` | Pengunduh PDF | `cookies.txt` format Netscape. Default mati. Gunakan hanya dengan penerbit yang Anda miliki hak institusi. |
| `AUTOPAPERTOPPT_LOG_LEVEL` | logger | Default `INFO`; `DEBUG` untuk jejak verbose. |

Default: `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. Selalu dapat di-override dengan `--export` eksplisit.

## Server MCP

Daftarkan ke Claude Code:

```powershell
claude mcp add autopapertoppt -- ".venv\Scripts\python.exe" -m autopapertoppt.mcp
```

Atau ubah berkas pengaturan:

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

Tool:

| Tool | Tujuan |
|---|---|
| `list_sources` | Mendaftar setiap plugin + melaporkan yang aktif di env saat ini. Panggil sekali sebelum `search`. |
| `search` | Kata kunci → daftar makalah. Menerima `top_tier_only`, `min_citations`; default ke campuran sumber tanpa-API-key penuh. |
| `fetch_paper` | Identifier arXiv / DOI / PMID / IEEE → satu makalah. |
| `fetch_pdf_text` | Unduh satu PDF, kembalikan teks tubuh hasil ekstraksi. **Jalur MCP menuju "saya membaca makalahnya".** |
| `download_pdfs` | Unduh PDF daftar makalah secara batch ke `{out_dir}/pdfs/`. Mengembalikan hasil per makalah berindeks kunci BibTeX. |
| `export` | Daftar makalah + format → menulis `.pptx/.xlsx/.md/.bib/.json`. Menerima field `summary` per makalah (skema gaya tesis kaya) dan `max_slides_per_paper` (default 25). |
| `pptx_inspect` | Membaca struktur slide / shape deck yang ada. |
| `pptx_update_slide` | Mengganti `title` / `body` / `meta` (berdasarkan nama shape) atau shape sembarang berdasarkan indeks. |
| `pptx_delete_slide` | Menghapus slide dan part relationship-nya. |
| `pptx_reorder_slides` | Mengubah urutan slide via `sldIdLst`. |
| `pptx_add_slide` | Menambahkan ke akhir atau menyisipkan slide title / body / meta baru. |

Alur LLM-as-agent (tanpa `ANTHROPIC_API_KEY` — LLM-nya sendiri yang menjadi agen):

```
1. (opsional) list_sources()                       # temukan plugin yang aktif
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (opsional) download_pdfs(papers, out_dir="./exports/...")  # persistkan PDF
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # per makalah
5. (LLM membaca teks, menghasilkan dict `summary` terstruktur)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="id", formats=["pptx","bib"], ...)
```

Referensi lengkap di [`docs/mcp.md`](docs/mcp.md).

## Tata letak proyek

```
AutoPaperToPPT/
├── autopapertoppt/                 # paket utama
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # client async HTTPS-only, rate limit token bucket
│   ├── exporters/                   # pptx (gaya tesis) · xlsx · bib · md · json · pptx_edit · i18n
│   ├── intelligence/                # unduh PDF + summarizer Anthropic ([intelligence] extra)
│   ├── mcp/                         # server FastMCP (11 tool)
│   ├── utils/                       # logging, path safety
│   ├── cli.py                       # CLI argparse
│   └── __main__.py
├── sources/                         # folder plugin: arxiv, semantic_scholar,
│                                    #   openalex, pubmed, acm, ieee, scholar,
│                                    #   dblp, crossref, openaire, springer
├── tests/                           # suite pytest + fixture terekam (tanpa HTTP langsung)
├── docs/                            # Sphinx (14 pohon bahasa)
├── scripts/                         # skrip regen sekali pakai
└── pyproject.toml                   # ruff, bandit, build, extras opsional
```

## Definition of Done

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r autopapertoppt/ sources/
```

Flag `-c` pada bandit wajib — tanpa itu, bandit mengabaikan konfigurasi skip proyek. Saat mengubah eksportir pptx, jalankan juga pemeriksaan overflow (lihat `CLAUDE.md` "Slide Deck Rules").

## Lisensi

Lihat `LICENSE`. API arXiv digunakan menurut ketentuan (<https://info.arxiv.org/help/api/tou.html>) — patuhi batas lunak 1 permintaan per 3 detik; fetcher bawaan sudah menerapkan tarif ini via token bucket.
