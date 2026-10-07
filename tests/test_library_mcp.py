"""The MCP library tools, called through the registered handlers."""

from __future__ import annotations

import asyncio
import json

import pytest

from thesisagents import mcp as mcp_pkg
from thesisagents.core.export_validation import Verdict, VerificationStatus
from thesisagents.library import Library
from thesisagents.mcp.server import ToolError


@pytest.fixture()
def server():
    return mcp_pkg.build_server()


@pytest.fixture()
def library_path(tmp_path) -> str:
    return str(tmp_path / "thesis.db")


def _call(server, name: str, **kwargs):
    result = asyncio.run(server.call_tool(name, kwargs))
    if isinstance(result, tuple):
        result = result[0]
    result = getattr(result, "content", result)
    return json.loads(next(block.text for block in result if getattr(block, "text", None)))


def _add(server, library_path, papers, **kwargs):
    return _call(
        server, "library_add", library=library_path,
        papers=[paper.to_dict() for paper in papers], **kwargs,
    )


def test_the_three_library_tools_are_registered(server):
    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert {"library_add", "library_search", "library_stats"} <= names
    assert len(names) == 17


def test_library_add_then_search_round_trip(server, library_path, sample_papers):
    added = _add(server, library_path, sample_papers, keywords="attention")
    assert (added["added"], added["merged"], added["total"]) == (2, 0, 2)
    assert added["library"] == library_path

    found = _call(server, "library_search", library=library_path, query="attention")

    assert (found["total"], found["count"]) == (2, 1)
    assert found["papers"] == [sample_papers[0].to_dict()]
    entry = found["entries"][0]
    assert entry["paper_key"] == sample_papers[0].dedup_key()
    assert entry["bibtex_key"] == sample_papers[0].bibtex_key()
    assert (entry["times_seen"], entry["sources"]) == (1, ["arxiv"])
    assert entry["score"]["relevance"] > 0


def test_library_add_is_a_merge(server, library_path, sample_papers):
    _add(server, library_path, sample_papers)
    again = _add(server, library_path, sample_papers)
    assert (again["added"], again["merged"], again["total"]) == (0, 2, 2)


def test_library_add_stores_the_relations_snowball_returns(server, library_path, sample_papers):
    first, second = sample_papers
    relation = {
        "source_key": first.dedup_key(), "target_key": second.dedup_key(),
        "relation": "references", "provider": "openalex", "depth": 1,
    }
    added = _add(server, library_path, sample_papers, relations=[relation])
    assert (added["relations_added"], added["relations_skipped"]) == (1, 0)
    assert _call(server, "library_stats", library=library_path)["relations"] == 1


@pytest.mark.parametrize(
    ("relation", "message"),
    [
        (
            {"source_key": "doi:10.1/a"},
            "relation is missing field(s): target_key, relation, provider, depth",
        ),
        (
            {"source_key": "a", "target_key": "b", "relation": "mentions",
             "provider": "openalex", "depth": 1},
            "'relation' must be 'references' or 'cited_by'",
        ),
    ],
)
def test_library_add_names_what_is_wrong_with_a_relation(
    server, library_path, sample_papers, relation, message
):
    with pytest.raises(ToolError) as raised:
        _add(server, library_path, sample_papers, relations=[relation])
    assert message in str(raised.value)


def test_library_add_requires_papers(server, library_path):
    with pytest.raises(ToolError, match="requires at least one paper"):
        _call(server, "library_add", library=library_path, papers=[])


def test_library_search_lists_recent_papers_for_an_empty_query(
    server, library_path, sample_papers
):
    _add(server, library_path, sample_papers)
    found = _call(server, "library_search", library=library_path, limit=1)
    assert (found["count"], found["total"]) == (1, 2)
    assert found["entries"][0]["score"] is None


def test_library_search_rejects_a_limit_out_of_range(server, library_path, sample_papers):
    _add(server, library_path, sample_papers)
    with pytest.raises(ToolError, match=r"limit must be in \[1, 200\]"):
        _call(server, "library_search", library=library_path, limit=0)


@pytest.mark.parametrize("tool", ["library_search", "library_stats"])
def test_reading_a_missing_library_is_a_tool_error(server, tmp_path, tool):
    missing = tmp_path / "typo.db"
    with pytest.raises(ToolError, match="no library at"):
        _call(server, tool, library=str(missing))
    assert not missing.exists()


def test_library_stats_reports_size_and_recent_runs(server, library_path, sample_papers):
    _add(server, library_path, sample_papers, keywords="attention")
    stats = _call(server, "library_stats", library=library_path)

    assert (stats["papers"], stats["runs"], stats["relations"]) == (2, 1, 0)
    assert stats["sources"] == {"arxiv": 2}
    assert (stats["year_min"], stats["year_max"]) == (2023, 2024)
    assert stats["recent_runs"] == [
        {
            "run_id": 1, "started_at": stats["last_run"], "kind": "mcp",
            "keywords": "attention", "papers": 2,
        }
    ]


def test_export_remembers_verdicts_in_the_library(
    server, library_path, sample_papers, tmp_path, monkeypatch
):
    from thesisagents.core import export_validation

    asked: list[int] = []

    async def _recording(targets):
        asked.append(len(targets))
        return {target: Verdict(VerificationStatus.OK) for target in targets}

    monkeypatch.setattr(export_validation, "_resolve_targets", _recording)
    arguments = {
        "papers": [paper.to_dict() for paper in sample_papers], "keywords": "attention",
        "formats": ["bib"], "out_dir": str(tmp_path / "out"), "library": library_path,
    }
    first = _call(server, "export", **arguments)
    second = _call(server, "export", **arguments)

    assert first["verification"]["ok"] is True and second["verification"]["ok"] is True
    assert asked[0] == 3
    assert sum(asked[1:]) == 0                         # the second call asked nothing
    with Library(library_path) as library:
        assert library.stats().verifications == {"ok": 3}
        assert len(library) == 0                       # export stores verdicts, not papers
