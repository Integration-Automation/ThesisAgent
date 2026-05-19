"""LLM-driven SpringerLink PDF download (visible Chrome).

Thin CLI wrapper around `scripts._pdf_downloaders.download_springer`.

Usage:
    .venv\\Scripts\\python.exe -m scripts.llm_download_springer_pdf <doi>

The DOI is the bare publisher DOI (e.g. ``10.1007/978-981-96-1024-2_8``).
The script tries ``/article/<doi>`` first, falls back to
``/chapter/<doi>`` when the article path 404s (book chapters live under
``/chapter/``), then navigates to ``/content/pdf/<doi>.pdf`` which
streams the PDF when the user's network has institutional access.

Exit code 0 = PDF saved, 1 = no PDF, 2 = bad arg.

For a batch over an xlsx, see ``scripts.llm_download_pdfs``.
"""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path

from autopapertoppt.fetchers import webrunner_browser
from scripts._pdf_downloaders import download_springer

OUT_DIR = Path(r"D:\Codes\AutoPaperToPPT\exports\_llm_scratch\pdfs")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _run(doi: str) -> int:
    print(f"[boot] visible Chrome with download_dir={OUT_DIR}", flush=True)
    driver = webrunner_browser.make_driver(download_dir=str(OUT_DIR))
    try:
        result = download_springer(driver, doi, OUT_DIR)
        return 0 if result is not None else 1
    finally:
        with contextlib.suppress(Exception):
            driver.quit()


if __name__ == "__main__":
    if len(sys.argv) != 2 or "/" not in sys.argv[1]:
        print("usage: python -m scripts.llm_download_springer_pdf <doi>")
        sys.exit(2)
    sys.exit(_run(sys.argv[1]))
