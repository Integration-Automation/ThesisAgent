"""`python -m autopapertoppt.mcp` — run the MCP server over stdio."""

from __future__ import annotations

import sys

from autopapertoppt.mcp.server import build_server


def main(argv: list[str] | None = None) -> int:
    _ = argv  # reserved for future flags
    server = build_server()
    server.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
