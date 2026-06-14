"""Canonical slide-overflow inspector CLI (thin wrapper).

The implementation now lives in ``thesisagents.exporters.overflow`` so the MCP
``pptx_review`` tool, the CLI ``review`` subcommand, the ``review_deck`` audit,
the regression test, and this script all share one inspector. This file stays as
the documented command-line entry point:

    .venv/Scripts/python.exe scripts/check_overflow.py exports/<deck>.pptx [more.pptx ...]

Exit code is the number of decks that FAILED (0 = all clean), so CI / a test can
assert on it. Importable: ``check_pptx(path) -> list[Violation]``.
"""
from __future__ import annotations

import sys

from thesisagents.exporters.overflow import (  # re-exported for callers/tests
    Violation,
    check_pptx,
    check_pptx_from_prs,
    main,
)

__all__ = ["Violation", "check_pptx", "check_pptx_from_prs", "main"]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
