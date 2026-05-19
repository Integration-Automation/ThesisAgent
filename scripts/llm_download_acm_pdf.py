"""LLM-driven ACM Digital Library PDF download (visible Chrome).

Thin CLI wrapper around `scripts._pdf_downloaders.download_acm`.

Usage:
    .venv\\Scripts\\python.exe -m scripts.llm_download_acm_pdf <doi>

The DOI is the bare publisher DOI (e.g. ``10.1145/3618257.3624845``),
NOT a full URL. The script navigates to ``https://dl.acm.org/doi/<doi>``
first to set ACM's session cookies, then to ``/doi/pdf/<doi>`` which
streams the PDF directly when the user has institutional access. Falls
back to iframe-src extraction when ACM wraps the PDF.

Exit code 0 = PDF saved, 1 = no PDF, 2 = bad arg.

For a batch over an xlsx, see ``scripts.llm_download_pdfs``.
"""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path

from autopapertoppt.fetchers import webrunner_browser
from scripts._pdf_downloaders import download_acm

OUT_DIR = Path(r"D:\Codes\AutoPaperToPPT\exports\_llm_scratch\pdfs")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _run(doi: str) -> int:
    print(f"[boot] visible Chrome with download_dir={OUT_DIR}", flush=True)
    driver = webrunner_browser.make_driver(download_dir=str(OUT_DIR))
    try:
        result = download_acm(driver, doi, OUT_DIR)
        return 0 if result is not None else 1
    finally:
        with contextlib.suppress(Exception):
            driver.quit()


if __name__ == "__main__":
    if len(sys.argv) != 2 or "/" not in sys.argv[1]:
        print("usage: python -m scripts.llm_download_acm_pdf <doi>")
        sys.exit(2)
    sys.exit(_run(sys.argv[1]))
