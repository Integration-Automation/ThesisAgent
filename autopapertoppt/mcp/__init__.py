"""MCP server exposing AutoPaperToPPT search/export/pptx-edit tools.

Optional — install via `pip install autopapertoppt[mcp]` (the `mcp` SDK is the
only extra dependency).
"""

from autopapertoppt.mcp.server import build_server

__all__ = ["build_server"]
