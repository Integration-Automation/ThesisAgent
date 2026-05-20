"""Render every figure region of the 4 speculative-decoding PDFs.

Drops PNGs into ``exports/speculative-decoding-zh-tw/figures/<key>/``,
matching the directory layout the regen script expects (mirrors the
older ``regen_llm_security_batch_zh_tw.py`` pattern).
"""
from __future__ import annotations

from pathlib import Path

from autopapertoppt.intelligence.pdf_assets import extract_figures

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "exports" / "_llm_scratch" / "pdfs"
OUT_ROOT = ROOT / "exports" / "speculative-decoding-zh-tw" / "figures"

# (paper_key, pdf_filename) — paper_key matches Paper.source_id in the
# regen script, so the regen's _fig() helper can resolve PNGs by key.
PAPERS: tuple[tuple[str, str], ...] = (
    ("xia2024speculative", "acl-2024_findings-acl_456.pdf"),
    ("spector2023staged", "arxiv-2308_04623.pdf"),
    ("xu2024edgellm", "10812936.pdf"),
    ("svirschevski2024specexec", "neurips-2024-1d91d5689e25.pdf"),
)


def main() -> None:
    for key, fname in PAPERS:
        pdf = PDF_DIR / fname
        out = OUT_ROOT / key
        if not pdf.is_file():
            print(f"[skip] {key}: {pdf} not found")
            continue
        figures = extract_figures(pdf, out)
        print(f"[ok]   {key}: {len(figures)} figures -> {out}")
        for f in figures:
            print(f"        p{f.page_number:02d}  {f.image_path.name}  {f.caption[:60]}")


if __name__ == "__main__":
    main()
