"""The MCP server on the 1.x SDK, driven over stdio the way an MCP host drives it.

mcp 2.x (2026-07-28) renamed ``mcp.server.fastmcp.FastMCP``, which
``thesisagents/mcp/server.py`` imports, so an unpinned install broke the
server and every test that imports it.
"""

from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from packaging.requirements import Requirement

from thesisagents.mcp import build_server

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_mcp_requirements_stay_on_the_1x_sdk():
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        extras = tomllib.load(handle)["project"]["optional-dependencies"]
    specs = [Requirement(spec) for name in ("mcp", "dev") for spec in extras[name]]
    pins = [requirement for requirement in specs if requirement.name == "mcp"]
    assert len(pins) == 2
    for requirement in pins:
        assert not requirement.specifier.contains("2.0.0")
        assert requirement.specifier.contains("1.30.0")


async def test_stdio_round_trip_lists_every_registered_tool(tmp_path):
    expected = {tool.name for tool in await build_server().list_tools()}
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(REPO_ROOT), env.get("PYTHONPATH")]))
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "thesisagents.mcp"], env=env, cwd=str(tmp_path))
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        listed = {tool.name for tool in (await session.list_tools()).tools}
    assert listed == expected
    assert len(listed) >= 10
