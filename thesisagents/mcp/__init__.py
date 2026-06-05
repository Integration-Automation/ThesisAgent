"""MCP server exposing ThesisAgents search/export/pptx-edit tools.

Optional — install via `pip install thesisagents[mcp]` (the `mcp` SDK is the
only extra dependency).
"""

from thesisagents.mcp.server import build_server

__all__ = ["build_server"]
