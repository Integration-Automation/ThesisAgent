"""Parse the artefacts left by _llm_driven_search.py.

Run after _llm_driven_search.py finishes. Reads the captured Scholar
HTML + IEEE JSON, runs the project's parsers, merges + de-dupes via the
existing core helpers, and writes a small markdown + xlsx the LLM can
hand the user.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Mirror the runtime injection that autopapertoppt/fetchers/base.py performs
# at load time so `from ieee.parser import ...` resolves.
_SOURCES = Path(__file__).resolve().parents[1] / "sources"
if str(_SOURCES) not in sys.path:
    sys.path.insert(0, str(_SOURCES))

from ieee.parser import parse_search_record  # noqa: E402  # sources/ path injection above
from scholar.parser import parse_serp  # noqa: E402  # sources/ path injection above

from autopapertoppt.core.dedup import dedupe  # noqa: E402  # after sys.path injection
from autopapertoppt.core.models import ExportOptions, PaperCollection, Query  # noqa: E402
from autopapertoppt.core.ranking import rank  # noqa: E402
from autopapertoppt.exporters.markdown import MarkdownExporter  # noqa: E402
from autopapertoppt.exporters.xlsx import XlsxExporter  # noqa: E402

ROOT = Path(r"D:\Codes\AutoPaperToPPT\exports\_llm_scratch")
QUERY_STR = "test-time compute scaling reasoning LLM"


def _load_scholar() -> list:
    html = (ROOT / "scholar.html").read_text(encoding="utf-8")
    return parse_serp(html)


def _load_ieee() -> list:
    data = json.loads((ROOT / "ieee_search.json").read_text(encoding="utf-8"))
    return [parse_search_record(r) for r in (data.get("records") or [])]


def main() -> None:
    scholar_papers = _load_scholar()
    ieee_papers = _load_ieee()
    print(f"scholar parsed: {len(scholar_papers)}")
    print(f"ieee parsed:    {len(ieee_papers)}")

    merged = dedupe(scholar_papers + ieee_papers)
    ranked = rank(merged)
    print(f"after dedup+rank: {len(ranked)}")

    query = Query(
        keywords=QUERY_STR,
        max_results=25,
        sources=("scholar", "ieee"),
    )
    collection = PaperCollection(query=query, papers=tuple(ranked[:25]))

    options = ExportOptions(
        formats=("xlsx", "md"),
        out_dir=str(ROOT),
        filename_stem="llm_driven",
        include_abstract=True,
    )
    xlsx_path = XlsxExporter().export(collection, options)
    md_path = MarkdownExporter().export(collection, options)
    print(f"xlsx: {xlsx_path}")
    print(f"md:   {md_path}")

    print("\n--- Top 10 ---")
    for i, p in enumerate(ranked[:10], 1):
        title = (p.title or "")[:78]
        via = p.source or "?"
        print(f"  [{i:>2}] ({p.year}) {title}  [via {via}]")


if __name__ == "__main__":
    main()
