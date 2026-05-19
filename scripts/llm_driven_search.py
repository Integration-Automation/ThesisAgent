"""LLM-driven search: visible Chrome, the LLM picks URLs.

The CLI's built-in WebRunner backend (`sources/ieee/webrunner_backend.py`,
`sources/scholar/webrunner_backend.py`) is the *Python pipeline* path —
it boots Chrome from inside `asyncio.gather`, captures HTML/JSON, and
hands it to the parsers. That works for unattended CI but burns the
LLM's ability to make per-step decisions (which paper to dig into,
which page to scroll, when to give up on a captcha).

This script is the *LLM-as-agent* path: the LLM in a Claude Code session
invokes this script via Bash, the script opens a visible Chrome window
(no headless), navigates to Scholar + IEEE for a chosen query, captures
the SERP HTML and `/rest/search` JSON to disk, and quits. The LLM then
calls `llm_parse_results.py` to merge / dedup / rank / export.

The split exists because Selenium sessions don't survive across Bash
invocations — once Chrome quits, state is gone. Keeping capture and
parse in separate scripts means the LLM can inspect each capture
(via the Read tool on the dumped HTML/JSON) before deciding next steps,
e.g. "the SERP returned a captcha, ask the user to solve it and re-run."

Usage:
    .venv\\Scripts\\python.exe -m scripts.llm_driven_search "your query"

Output: ``exports/_llm_scratch/scholar.html`` and
``exports/_llm_scratch/ieee_search.json``.
"""

from __future__ import annotations

import contextlib
import json
import sys
import time
from pathlib import Path

from autopapertoppt.fetchers import webrunner_browser

OUT_DIR = Path(r"D:\Codes\AutoPaperToPPT\exports\_llm_scratch")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _drive(query: str) -> None:
    print("[boot] launching visible Chrome ...", flush=True)
    driver = webrunner_browser.make_driver()
    try:
        # ---- Scholar ----
        scholar_url = (
            "https://scholar.google.com/scholar"
            f"?q={query.replace(' ', '+')}&hl=en&num=10"
        )
        print(f"[scholar] navigate {scholar_url}", flush=True)
        driver.get(scholar_url)
        time.sleep(4)
        webrunner_browser.wait_for_captcha_solved(driver, max_wait_seconds=300.0)
        scholar_html_path = OUT_DIR / "scholar.html"
        scholar_html_path.write_text(driver.page_source, encoding="utf-8")
        print(
            f"[scholar] page_source bytes={len(driver.page_source)} "
            f"-> {scholar_html_path}",
            flush=True,
        )

        # ---- IEEE Xplore: land on home so REST cookies are set,
        #      then JS-fetch the /rest/search endpoint from the IEEE origin.
        print("[ieee] navigate https://ieeexplore.ieee.org/Xplore/home.jsp", flush=True)
        driver.get("https://ieeexplore.ieee.org/Xplore/home.jsp")
        time.sleep(4)
        webrunner_browser.wait_for_captcha_solved(driver, max_wait_seconds=300.0)
        driver.set_script_timeout(30)
        rest_body = {
            "queryText": query,
            "highlight": False,
            "returnFacets": ["ALL"],
            "returnType": "SEARCH",
            "matchPubs": True,
            "pageNumber": 1,
            "rowsPerPage": 10,
        }
        js = (
            "const url=arguments[0], body=arguments[1], cb=arguments[2];"
            "fetch(url,{method:'POST',headers:{"
            "'Accept':'application/json,text/plain,*/*',"
            "'Content-Type':'application/json',"
            "'Origin':'https://ieeexplore.ieee.org',"
            "'Referer':'https://ieeexplore.ieee.org/search/searchresult.jsp'"
            "},credentials:'include',body:body})"
            ".then(r=>r.json()).then(j=>cb(j))"
            ".catch(e=>cb({_error:String(e)}));"
        )
        result = driver.execute_async_script(
            js, "https://ieeexplore.ieee.org/rest/search", json.dumps(rest_body)
        )
        ieee_json_path = OUT_DIR / "ieee_search.json"
        ieee_json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(
            f"[ieee] records={len((result or {}).get('records') or [])} "
            f"-> {ieee_json_path}",
            flush=True,
        )
    finally:
        with contextlib.suppress(Exception):
            driver.quit()
        print("[done] chrome quit", flush=True)


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "test-time compute scaling reasoning LLM"
    _drive(q)
