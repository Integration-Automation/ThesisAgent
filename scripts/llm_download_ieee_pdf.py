"""LLM-driven IEEE PDF download (visible Chrome, no headless).

Thin CLI wrapper around `scripts._pdf_downloaders.download_ieee`.

Usage:
    .venv\\Scripts\\python.exe -m scripts.llm_download_ieee_pdf <arnumber>

Output: ``exports/_llm_scratch/pdfs/<arnumber>.pdf`` on success.
Exit code 0 = PDF saved, 1 = no PDF, 2 = bad arg.

For a batch over an xlsx, see ``scripts.llm_download_pdfs``.
"""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path

from autopapertoppt.fetchers import webrunner_browser
from scripts._pdf_downloaders import download_ieee

OUT_DIR = Path(r"D:\Codes\AutoPaperToPPT\exports\_llm_scratch\pdfs")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _run(arnumber: str) -> int:
    print(f"[boot] visible Chrome with download_dir={OUT_DIR}", flush=True)
    driver = webrunner_browser.make_driver(download_dir=str(OUT_DIR))
    try:
        result = download_ieee(driver, arnumber, OUT_DIR)
        return 0 if result is not None else 1
    finally:
        with contextlib.suppress(Exception):
            driver.quit()


if __name__ == "__main__":
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        print("usage: python -m scripts.llm_download_ieee_pdf <arnumber>")
        sys.exit(2)
    sys.exit(_run(sys.argv[1]))
