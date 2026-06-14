"""Manual dark-mode text auditor CLI (thin wrapper).

The implementation now lives in ``thesisagents.exporters.audit`` so the MCP
``pptx_review`` tool, the CLI ``review`` subcommand, the ``review_deck`` audit,
and this script all share one auditor. This file stays as the documented
command-line entry point:

    .venv/Scripts/python.exe scripts/_audit_dark_text.py exports/<deck>.pptx [more.pptx ...]

Exit code is the number of decks with at least one hard issue (checks 1-3); the
off-palette warning alone does not fail a deck. Importable: ``audit_deck(path)``.
"""
from __future__ import annotations

import sys

from thesisagents.exporters.audit import Issue, audit_deck, main  # re-exported

__all__ = ["Issue", "audit_deck", "main"]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
