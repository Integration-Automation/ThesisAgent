"""Throwaway: dump a PDF's body text so the LLM can read it via the Read tool.

Usage:
    .venv\\Scripts\\python.exe -m scripts._dump_pdf_text <pdf_path>

Writes ``<pdf_path>.txt`` next to the PDF and prints the first 2 KB.
"""
import sys
from pathlib import Path

from autopapertoppt.intelligence.pdf import _extract_text

pdf = Path(sys.argv[1])
body = pdf.read_bytes()
text, pages = _extract_text(body, str(pdf))
out = pdf.with_suffix(".txt")
out.write_text(text, encoding="utf-8")
print(f"pdf={pdf.name} pages={pages} chars={len(text)} -> {out}")
print("--- HEAD ---")
print(text[:2000])
