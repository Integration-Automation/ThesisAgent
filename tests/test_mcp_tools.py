"""MCP tool layer: hit each tool through the FastMCP-registered handler."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from thesisagents import mcp as mcp_pkg
from thesisagents.core.exceptions import ThesisAgentsError
from thesisagents.core.models import PaperCollection, Query
from thesisagents.mcp.server import ToolError, _as_tool_error


@pytest.fixture()
def server():
    return mcp_pkg.build_server()


async def _call(server, name: str, **kwargs):
    """Invoke a registered FastMCP tool by name and return the parsed payload."""
    result = await server.call_tool(name, kwargs)
    text = _first_text(result)
    return json.loads(text)


def _first_text(result):
    # The 1.x SDK returns a list[Content] or a tuple (contents, structured);
    # 2.x returns a CallToolResult whose ``content`` is that list.
    if isinstance(result, tuple):
        result = result[0]
    result = getattr(result, "content", result)
    for block in result:
        text = getattr(block, "text", None)
        if text is not None:
            return text
    raise AssertionError("MCP tool result contained no text block")


def test_search_tool(monkeypatch, server, sample_papers):
    async def fake_run_search(query, **_kwargs):
        return PaperCollection(query=query, papers=tuple(sample_papers))

    async def fake_shutdown():
        return None

    monkeypatch.setattr("thesisagents.mcp.server.run_search", fake_run_search)
    monkeypatch.setattr("thesisagents.mcp.server.shutdown_clients", fake_shutdown)
    payload = asyncio.run(
        _call(server, "search", keywords="attention", sources=["arxiv"], max_results=5)
    )
    assert payload["count"] == 2
    assert payload["papers"][0]["title"] == "Sample Paper on Attention"


def test_fetch_pdf_text_tool(monkeypatch, server):
    """fetch_pdf_text wraps intelligence.pdf.fetch_and_extract for MCP callers."""
    from thesisagents.intelligence.pdf import ExtractedPdf

    async def fake_fetch(pdf_url, source="intelligence"):
        return ExtractedPdf(
            url=pdf_url, page_count=12, chars=500, text="full paper body text"
        )

    monkeypatch.setattr(
        "thesisagents.intelligence.pdf.fetch_and_extract", fake_fetch
    )
    payload = asyncio.run(
        _call(server, "fetch_pdf_text", pdf_url="https://arxiv.org/pdf/x")
    )
    assert payload["page_count"] == 12
    assert payload["chars"] == 500
    assert payload["text"].startswith("full paper")


def test_fetch_paper_tool(monkeypatch, server, sample_papers):
    async def fake_single(identifier):
        return PaperCollection(
            query=Query(keywords=identifier.value, sources=("arxiv",), max_results=1),
            papers=(sample_papers[0],),
        )

    async def fake_shutdown():
        return None

    monkeypatch.setattr("thesisagents.mcp.server.run_single_paper", fake_single)
    monkeypatch.setattr("thesisagents.mcp.server.shutdown_clients", fake_shutdown)
    payload = asyncio.run(_call(server, "fetch_paper", identifier="2401.08741"))
    assert payload["paper"]["title"] == "Sample Paper on Attention"
    assert payload["identifier"]["kind"] == "arxiv"


def test_export_tool(server, sample_papers, tmp_path):
    papers = [p.to_dict() for p in sample_papers]
    payload = asyncio.run(
        _call(
            server,
            "export",
            papers=papers,
            keywords="attention",
            formats=["xlsx", "bib", "pptx"],
            out_dir=str(tmp_path),
            filename_stem="mcp-test",
        )
    )
    assert Path(payload["written"]["xlsx"]).exists()
    assert Path(payload["written"]["bib"]).exists()
    assert Path(payload["written"]["pptx"]).exists()
    assert payload["pptx_path"] == payload["written"]["pptx"]


def test_pptx_inspect_and_update_via_mcp(server, sample_papers, tmp_path):
    papers = [p.to_dict() for p in sample_papers]
    written = asyncio.run(
        _call(
            server,
            "export",
            papers=papers,
            keywords="attention",
            formats=["pptx"],
            out_dir=str(tmp_path),
            filename_stem="mcp-edit",
            include_abstract=False,
        )
    )
    pptx_path = written["written"]["pptx"]

    inspected = asyncio.run(_call(server, "pptx_inspect", path=pptx_path))
    # cover + agenda + (divider+overview)*2 + references = 7
    assert inspected["slide_count"] == 7

    asyncio.run(
        _call(
            server,
            "pptx_update_slide",
            path=pptx_path,
            slide_index=3,
            title="MCP-Edited Title",
        )
    )
    re_inspected = asyncio.run(_call(server, "pptx_inspect", path=pptx_path))
    assert re_inspected["slides"][3]["title"] == "MCP-Edited Title"


def test_list_sources_tool(server, monkeypatch):
    """list_sources reports every plugin + reflects current env-var state."""
    # Clear every gating var so the default-on / opt-in semantics are
    # exercised without contamination from the host shell.
    for var in (
        "THESISAGENTS_IEEE_API_KEY",
        "THESISAGENTS_DISABLE_IEEE_SCRAPING",
        "THESISAGENTS_SPRINGER_API_KEY",
        "THESISAGENTS_DISABLE_SCHOLAR_SCRAPING",
        "THESISAGENTS_CORE_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)
    payload = asyncio.run(_call(server, "list_sources"))
    names = {entry["name"]: entry for entry in payload["sources"]}
    # Every plugin we ship must appear.
    for required in (
        "arxiv", "semantic_scholar", "openalex", "pubmed",
        "acm", "dblp", "crossref", "openaire",
        "ieee", "springer", "scholar", "europepmc", "doaj", "hal", "core",
    ):
        assert required in names, f"list_sources missing {required!r}"
    # Plugins that need no env var must be enabled.
    assert names["arxiv"]["enabled"] is True
    assert names["dblp"]["enabled"] is True
    # IEEE + Scholar are now default-ON (no opt-out env var set).
    assert names["ieee"]["enabled"] is True
    assert names["ieee"]["opt_out_env_var"] == ["THESISAGENTS_DISABLE_IEEE_SCRAPING"]
    assert names["scholar"]["enabled"] is True
    assert names["scholar"]["opt_out_env_var"] == ["THESISAGENTS_DISABLE_SCHOLAR_SCRAPING"]
    # Springer still opt-IN — without the API key it is disabled.
    assert names["springer"]["enabled"] is False
    assert names["springer"]["opt_in_env_var"] == ["THESISAGENTS_SPRINGER_API_KEY"]
    # CORE is opt-IN too — disabled without its key.
    assert names["core"]["enabled"] is False
    assert names["core"]["opt_in_env_var"] == ["THESISAGENTS_CORE_API_KEY"]
    assert "default_sources" in payload
    # Default mix now includes scholar (alongside ieee + the others).
    assert "scholar" in payload["default_sources"]
    assert "ieee" in payload["default_sources"]


def test_list_exports_tool(server):
    """list_exports reports every registered format with a description."""
    from thesisagents.core.constants import ALL_EXPORTS

    payload = asyncio.run(_call(server, "list_exports"))
    by_format = {entry["format"]: entry for entry in payload["formats"]}
    # Every format the exporter layer knows about must be advertised.
    for fmt in ALL_EXPORTS:
        assert fmt in by_format, f"list_exports missing {fmt!r}"
        assert by_format[fmt]["description"]
    # The new interchange formats are present and flagged as aggregate.
    assert by_format["ris"]["aggregate"] is True
    assert by_format["csv"]["aggregate"] is True
    # pptx + pdf are per-paper, not aggregate.
    assert by_format["pptx"]["aggregate"] is False
    assert by_format["pdf"]["aggregate"] is False


def test_list_sources_reflects_springer_key(server, monkeypatch):
    monkeypatch.setenv("THESISAGENTS_SPRINGER_API_KEY", "test-key")
    payload = asyncio.run(_call(server, "list_sources"))
    by_name = {entry["name"]: entry for entry in payload["sources"]}
    assert by_name["springer"]["enabled"] is True


def test_search_passes_top_tier_and_min_citations(monkeypatch, server, sample_papers):
    """top_tier_only + min_citations flow from the MCP tool into the Query."""
    captured = {}

    async def fake_run_search(query, **_kwargs):
        captured["query"] = query
        return PaperCollection(query=query, papers=tuple(sample_papers))

    async def fake_shutdown():
        return None

    monkeypatch.setattr("thesisagents.mcp.server.run_search", fake_run_search)
    monkeypatch.setattr("thesisagents.mcp.server.shutdown_clients", fake_shutdown)
    asyncio.run(
        _call(
            server,
            "search",
            keywords="x",
            sources=["arxiv"],
            max_results=3,
            top_tier_only=False,
            min_citations=10,
        )
    )
    assert captured["query"].top_tier_only is False
    assert captured["query"].min_citations == 10


def test_search_exclude_sources_prunes_mix(monkeypatch, server, sample_papers):
    """exclude_sources is subtracted from the resolved mix before the Query."""
    from thesisagents.core.constants import DEFAULT_SOURCES

    captured = {}

    async def fake_run_search(query, **_kwargs):
        captured["query"] = query
        return PaperCollection(query=query, papers=tuple(sample_papers))

    async def fake_shutdown():
        return None

    monkeypatch.setattr("thesisagents.mcp.server.run_search", fake_run_search)
    monkeypatch.setattr("thesisagents.mcp.server.shutdown_clients", fake_shutdown)
    asyncio.run(_call(server, "search", keywords="x", exclude_sources=["ieee"]))
    assert "ieee" not in captured["query"].sources
    assert captured["query"].sources == tuple(
        s for s in DEFAULT_SOURCES if s != "ieee"
    )


def test_search_exclude_all_sources_errors(monkeypatch, server):
    """Excluding the only requested source surfaces a clean error."""
    async def fake_shutdown():  # NOSONAR async stub
        return None

    monkeypatch.setattr("thesisagents.mcp.server.shutdown_clients", fake_shutdown)
    with pytest.raises(ToolError, match="exclude_sources removed every source"):
        asyncio.run(
            _call(
                server,
                "search",
                keywords="x",
                sources=["arxiv"],
                exclude_sources=["arxiv"],
            )
        )


def test_search_defaults_to_full_source_mix(monkeypatch, server, sample_papers):
    """When sources is omitted, the search defaults to DEFAULT_SOURCES."""
    from thesisagents.core.constants import DEFAULT_SOURCES

    captured = {}

    async def fake_run_search(query, **_kwargs):  # NOSONAR async stub
        captured["query"] = query
        return PaperCollection(query=query, papers=tuple(sample_papers))

    async def fake_shutdown():  # NOSONAR async stub
        return None

    monkeypatch.setattr("thesisagents.mcp.server.run_search", fake_run_search)
    monkeypatch.setattr("thesisagents.mcp.server.shutdown_clients", fake_shutdown)
    asyncio.run(_call(server, "search", keywords="x"))
    assert captured["query"].sources == DEFAULT_SOURCES


def test_export_respects_max_slides_per_paper(server, sample_papers, tmp_path):
    """A small cap must shrink the produced deck to at most that many slides."""
    from pptx import Presentation

    papers = [p.to_dict() for p in sample_papers]
    payload = asyncio.run(
        _call(
            server,
            "export",
            papers=papers,
            keywords="x",
            formats=["pptx"],
            out_dir=str(tmp_path),
            filename_stem="capped",
            include_abstract=False,
            max_slides_per_paper=3,
        )
    )
    prs = Presentation(payload["written"]["pptx"])
    # Cover + agenda + references are kept; with cap=3 per paper for 2
    # sample_papers, the deck must stay well under the uncapped baseline.
    assert len(prs.slides) <= 3 + 3 + 2  # safety bound


def test_export_treats_zero_as_unlimited(server, sample_papers, tmp_path):
    """Passing 0 must mean "no cap" so an agent doesn't truncate by accident."""
    papers = [p.to_dict() for p in sample_papers]
    capped = asyncio.run(
        _call(
            server,
            "export",
            papers=papers,
            keywords="x",
            formats=["pptx"],
            out_dir=str(tmp_path),
            filename_stem="cap-zero",
            include_abstract=True,
            max_slides_per_paper=0,
        )
    )
    natural = asyncio.run(
        _call(
            server,
            "export",
            papers=papers,
            keywords="x",
            formats=["pptx"],
            out_dir=str(tmp_path),
            filename_stem="cap-none",
            include_abstract=True,
            max_slides_per_paper=None,
        )
    )
    # Both should produce the same slide count — neither truncates.
    from pptx import Presentation
    assert len(Presentation(capped["written"]["pptx"]).slides) == len(
        Presentation(natural["written"]["pptx"]).slides
    )


def test_download_pdfs_tool(monkeypatch, server, sample_papers, tmp_path):
    """download_pdfs forwards to core.pdf_download and returns per-paper results."""
    from thesisagents.core.pdf_download import PdfDownloadResult

    async def fake_download(collection, out_dir):
        return [
            PdfDownloadResult(
                paper_key=p.bibtex_key(),
                path=Path(out_dir) / "pdfs" / f"{p.bibtex_key()}.pdf"
                if p.pdf_url
                else None,
                skipped_reason=None if p.pdf_url else "no_pdf_url",
            )
            for p in collection.papers
        ]

    async def fake_shutdown():
        return None

    monkeypatch.setattr(
        "thesisagents.mcp.server.core_download_pdfs", fake_download
    )
    monkeypatch.setattr("thesisagents.mcp.server.shutdown_clients", fake_shutdown)
    papers = [p.to_dict() for p in sample_papers]
    payload = asyncio.run(
        _call(
            server,
            "download_pdfs",
            papers=papers,
            out_dir=str(tmp_path),
        )
    )
    assert payload["out_dir"] == str(tmp_path)
    # sample_papers[0] has pdf_url, sample_papers[1] does not.
    assert payload["saved"] == 1
    assert payload["skipped"] == 1
    assert any(r["reason"] == "no_pdf_url" for r in payload["results"])
    assert all(("path" in r and "reason" in r) for r in payload["results"])


def test_pptx_delete_reorder_add_via_mcp(server, sample_papers, tmp_path):
    papers = [p.to_dict() for p in sample_papers]
    written = asyncio.run(
        _call(
            server,
            "export",
            papers=papers,
            keywords="x",
            formats=["pptx"],
            out_dir=str(tmp_path),
            filename_stem="ops",
            include_abstract=False,
        )
    )
    pptx_path = written["written"]["pptx"]
    baseline = asyncio.run(_call(server, "pptx_inspect", path=pptx_path))
    baseline_count = baseline["slide_count"]

    asyncio.run(_call(server, "pptx_add_slide", path=pptx_path, title="Added", body="b"))
    after_add = asyncio.run(_call(server, "pptx_inspect", path=pptx_path))
    assert after_add["slide_count"] == baseline_count + 1

    new_order = [after_add["slide_count"] - 1] + list(range(after_add["slide_count"] - 1))
    asyncio.run(_call(server, "pptx_reorder_slides", path=pptx_path, new_order=new_order))
    after_reorder = asyncio.run(_call(server, "pptx_inspect", path=pptx_path))
    assert after_reorder["slides"][0]["title"] == "Added"

    asyncio.run(_call(server, "pptx_delete_slide", path=pptx_path, slide_index=0))
    after_delete = asyncio.run(_call(server, "pptx_inspect", path=pptx_path))
    assert after_delete["slide_count"] == baseline_count


def test_export_ignores_the_pdf_pseudo_format(server, sample_papers, tmp_path):
    """``pdf`` appears in list_exports but names the download stage.

    An agent that copies the list_exports format list wholesale used to get
    "no exporter registered for this format" and lose every other format in the
    same call. It must now be dropped and the real formats still written.
    """
    papers = [p.to_dict() for p in sample_papers]
    payload = asyncio.run(
        _call(
            server,
            "export",
            papers=papers,
            keywords="attention",
            formats=["pdf", "bib"],
            out_dir=str(tmp_path),
            filename_stem="pdf-mixed",
        )
    )
    assert Path(payload["written"]["bib"]).exists()
    assert "pdf" not in payload["written"]


def test_export_with_only_pdf_points_at_the_download_tool(server, sample_papers, tmp_path):
    """``formats=["pdf"]`` alone has nothing to render — say so, by name."""
    papers = [p.to_dict() for p in sample_papers]
    with pytest.raises(ToolError, match="download_pdfs"):
        asyncio.run(
            _call(
                server,
                "export",
                papers=papers,
                keywords="attention",
                formats=["pdf"],
                out_dir=str(tmp_path),
            )
        )


def test_export_accepts_more_papers_than_the_page_size_cap(server, sample_papers, tmp_path):
    """A 250-paper export must not die on the per-source page-size validator.

    ``export`` builds a synthetic Query only to satisfy ``PaperCollection``;
    its ``max_results`` describes nothing the caller set, so feeding it the raw
    paper count used to raise "max_results must be in [1, 200]".
    """
    template = sample_papers[0].to_dict()
    papers = []
    for index in range(250):
        entry = dict(template)
        entry["source_id"] = f"paper-{index}"
        entry["title"] = f"Paper Number {index}"
        entry["doi"] = f"10.5555/n{index}"
        papers.append(entry)
    payload = asyncio.run(
        _call(
            server,
            "export",
            papers=papers,
            keywords="bulk",
            formats=["bib"],
            out_dir=str(tmp_path),
            filename_stem="bulk",
        )
    )
    assert Path(payload["written"]["bib"]).exists()


def test_as_tool_error_turns_a_sync_tool_error_into_tool_error():
    def failing():
        raise ThesisAgentsError("nothing to render")

    with pytest.raises(ToolError, match="nothing to render") as caught:
        _as_tool_error(failing)()
    assert isinstance(caught.value.__cause__, ThesisAgentsError)


def test_as_tool_error_turns_an_async_tool_error_into_tool_error():
    async def failing():
        raise ThesisAgentsError("no paper found")

    with pytest.raises(ToolError, match="no paper found"):
        asyncio.run(_as_tool_error(failing)())


def test_as_tool_error_passes_results_and_other_errors_through():
    async def ok(value):
        return {"value": value}

    def broken():
        raise KeyError("bug")

    assert asyncio.run(_as_tool_error(ok)(3)) == {"value": 3}
    with pytest.raises(KeyError):
        _as_tool_error(broken)()


# ---------------------------------------------------------------------------
# export: identifier preflight
# ---------------------------------------------------------------------------


def test_export_reports_the_verification_it_ran(server, sample_papers, tmp_path):
    papers = [p.to_dict() for p in sample_papers]
    payload = asyncio.run(
        _call(
            server, "export", papers=papers, keywords="attention",
            formats=["bib"], out_dir=str(tmp_path), filename_stem="verified",
        )
    )
    verification = payload["verification"]
    assert verification["enabled"] is True
    assert verification["ok"] is True
    assert verification["counts"]["ok"] == 3  # two URLs + one DOI
    assert {check["kind"] for check in verification["checks"]} == {"doi", "url"}
    assert verification["checks"][0]["paper_key"] == sample_papers[0].bibtex_key()


def test_export_fails_on_a_bad_identifier_and_writes_nothing(
    server, sample_papers, tmp_path
):
    """The error text must name the paper and the identifier, since an MCP
    client only ever sees the message."""
    papers = [p.to_dict() for p in sample_papers]
    papers[1]["doi"] = "10.x/composed-by-hand"
    with pytest.raises(ToolError) as raised:
        asyncio.run(
            _call(
                server, "export", papers=papers, keywords="attention",
                formats=["bib", "json"], out_dir=str(tmp_path),
            )
        )
    message = str(raised.value)
    assert "identifier verification failed" in message
    assert "10.x/composed-by-hand is invalid" in message
    assert sample_papers[1].bibtex_key() in message
    assert "verify_identifiers=False" in message
    assert list(tmp_path.iterdir()) == []


def test_export_can_skip_verification(server, sample_papers, tmp_path):
    papers = [p.to_dict() for p in sample_papers]
    papers[1]["doi"] = "10.x/composed-by-hand"
    payload = asyncio.run(
        _call(
            server, "export", papers=papers, keywords="attention",
            formats=["bib"], out_dir=str(tmp_path), verify_identifiers=False,
        )
    )
    assert payload["verification"] == {"enabled": False}
    assert Path(payload["written"]["bib"]).exists()


# ---------------------------------------------------------------------------
# search: diagnostics
# ---------------------------------------------------------------------------


def _diagnosed_collection(query, papers) -> PaperCollection:
    """A collection the way ``run_search`` returns it: ranked, with diagnostics."""
    from thesisagents.core import pipeline
    from thesisagents.core.ranking import rank_with_scores

    ranked = rank_with_scores(papers, query.keywords, current_year=2026)
    return PaperCollection(
        query=query,
        papers=tuple(entry.paper for entry in ranked),
        diagnostics=pipeline._diagnose(ranked),  # noqa: SLF001
    )


def test_search_without_the_flag_has_no_diagnostics_block(
    monkeypatch, server, sample_papers
):
    """``source_stats`` is always there. The score breakdown is opt-in."""

    async def fake_run_search(query, **_kwargs):
        return _diagnosed_collection(query, sample_papers)

    async def fake_shutdown():
        return None

    monkeypatch.setattr("thesisagents.mcp.server.run_search", fake_run_search)
    monkeypatch.setattr("thesisagents.mcp.server.shutdown_clients", fake_shutdown)
    payload = asyncio.run(_call(server, "search", keywords="attention", sources=["arxiv"]))

    assert set(payload) == {"query", "count", "papers", "source_stats"}
    assert set(payload["papers"][0]) == set(sample_papers[0].to_dict())


def test_search_diagnostics_explain_the_ranking(monkeypatch, server, sample_papers):
    async def fake_run_search(query, **_kwargs):
        return _diagnosed_collection(query, sample_papers)

    async def fake_shutdown():
        return None

    monkeypatch.setattr("thesisagents.mcp.server.run_search", fake_run_search)
    monkeypatch.setattr("thesisagents.mcp.server.shutdown_clients", fake_shutdown)
    payload = asyncio.run(
        _call(server, "search", keywords="attention", sources=["arxiv"], diagnostics=True)
    )

    report = payload["diagnostics"]
    assert report["advisory"] is True
    assert report["summary"] == {"keep": 1, "review": 0, "prune": 1}
    assert payload["count"] == 2  # advice only: both papers are still returned
    on_topic, off_topic = report["papers"]
    assert on_topic["title"] == "Sample Paper on Attention"
    assert on_topic["bibtex_key"] == sample_papers[0].bibtex_key()
    assert on_topic["score"]["matched_terms"] == ["attention"]
    assert on_topic["recommendation"]["action"] == "keep"
    assert off_topic["recommendation"]["action"] == "prune"
    assert off_topic["recommendation"]["threshold"] == "prune_below_relevance=0.10"
    assert [p["rank"] for p in report["papers"]] == [1, 2]


def test_search_diagnostics_tolerate_a_collection_without_any(
    monkeypatch, server, sample_papers
):
    async def fake_run_search(query, **_kwargs):
        return PaperCollection(query=query, papers=tuple(sample_papers))

    async def fake_shutdown():
        return None

    monkeypatch.setattr("thesisagents.mcp.server.run_search", fake_run_search)
    monkeypatch.setattr("thesisagents.mcp.server.shutdown_clients", fake_shutdown)
    payload = asyncio.run(
        _call(server, "search", keywords="attention", sources=["arxiv"], diagnostics=True)
    )

    assert [p["score"] for p in payload["diagnostics"]["papers"]] == [None, None]


# ---------------------------------------------------------------------------
# search: source_stats
# ---------------------------------------------------------------------------


def _collection_with_stats(query, papers) -> PaperCollection:
    from thesisagents.core.diagnostics import (
        SearchDiagnostics,
        SourceStat,
        SourceStatus,
    )

    stats = (
        SourceStat("arxiv", requested=5, returned=2, after_dedup=2),
        SourceStat(
            "ieee", requested=5, returned=0, after_dedup=0,
            status=SourceStatus.FAILED, detail="[ieee] blocked",
        ),
    )
    return PaperCollection(
        query=query, papers=tuple(papers),
        diagnostics=SearchDiagnostics(source_stats=stats),
    )


def test_search_reports_what_each_source_returned(monkeypatch, server, sample_papers):
    async def fake_run_search(query, **_kwargs):
        return _collection_with_stats(query, sample_papers)

    async def fake_shutdown():
        return None

    monkeypatch.setattr("thesisagents.mcp.server.run_search", fake_run_search)
    monkeypatch.setattr("thesisagents.mcp.server.shutdown_clients", fake_shutdown)
    payload = asyncio.run(
        _call(server, "search", keywords="attention", sources=["arxiv", "ieee"], max_results=5)
    )

    assert payload["source_stats"] == [
        {"source": "arxiv", "requested": 5, "returned": 2, "after_dedup": 2,
         "status": "ok", "detail": ""},
        {"source": "ieee", "requested": 5, "returned": 0, "after_dedup": 0,
         "status": "failed", "detail": "[ieee] blocked"},
    ]
    # The papers are exactly what they were before the stats existed.
    assert payload["papers"] == [paper.to_dict() for paper in sample_papers]
    assert payload["count"] == 2


def test_search_source_stats_is_an_empty_list_without_diagnostics(
    monkeypatch, server, sample_papers
):
    async def fake_run_search(query, **_kwargs):
        return PaperCollection(query=query, papers=tuple(sample_papers))

    async def fake_shutdown():
        return None

    monkeypatch.setattr("thesisagents.mcp.server.run_search", fake_run_search)
    monkeypatch.setattr("thesisagents.mcp.server.shutdown_clients", fake_shutdown)
    payload = asyncio.run(_call(server, "search", keywords="attention", sources=["arxiv"]))

    assert payload["source_stats"] == []


def test_search_diagnostics_block_repeats_the_source_stats(
    monkeypatch, server, sample_papers
):
    async def fake_run_search(query, **_kwargs):
        return _collection_with_stats(query, sample_papers)

    async def fake_shutdown():
        return None

    monkeypatch.setattr("thesisagents.mcp.server.run_search", fake_run_search)
    monkeypatch.setattr("thesisagents.mcp.server.shutdown_clients", fake_shutdown)
    payload = asyncio.run(
        _call(server, "search", keywords="attention", sources=["arxiv"], diagnostics=True)
    )

    assert payload["diagnostics"]["source_stats"] == payload["source_stats"]


def test_list_sources_carries_no_query_state(server):
    """Discovery only: per-query counts belong to ``search``."""
    payload = asyncio.run(_call(server, "list_sources"))

    assert set(payload) == {"sources", "default_sources"}
    assert set(payload["sources"][0]) == {
        "name", "in_default_mix", "opt_in_env_var", "opt_out_env_var", "enabled",
    }


# ---------------------------------------------------------------------------
# snowball tool + search(snowball=...)
# ---------------------------------------------------------------------------


class _GraphProvider:
    """Citation provider answering from a dict keyed by ``(source_id, direction)``."""

    def __init__(self, graph, name="graph", fail_with=None):
        self.name = name
        self._graph = graph
        self._fail_with = fail_with
        self.calls: list[tuple[str, str, int]] = []

    async def _answer(self, paper, direction, limit):
        self.calls.append((paper.source_id, direction, limit))
        if self._fail_with is not None:
            raise self._fail_with
        return list(self._graph.get((paper.source_id, direction), []))

    async def references(self, paper, limit):
        return await self._answer(paper, "references", limit)

    async def cited_by(self, paper, limit):
        return await self._answer(paper, "cited_by", limit)


def _found(sid: str, title: str):
    from thesisagents.core.models import Paper

    return Paper(
        source="openalex", source_id=sid, title=title, authors=("Ada Author",),
        year=2024, venue=None, abstract="", url=f"https://example.org/{sid}",
        doi=f"10.1000/{sid}",
    )


@pytest.fixture()
def citation_graph(monkeypatch, sample_papers):
    """Install an in-memory citation provider as the only default provider."""
    seed_id = sample_papers[0].source_id
    provider = _GraphProvider(
        {
            (seed_id, "references"): [_found("r1", "Attention Mechanisms Reviewed")],
            (seed_id, "cited_by"): [
                _found("c1", "Sparse Attention at Scale"),
                _found("c2", "Cooking With Gas"),
            ],
        }
    )
    monkeypatch.setattr(
        "thesisagents.core.snowball._default_providers", lambda: [provider]
    )

    async def fake_shutdown():
        return None

    monkeypatch.setattr("thesisagents.mcp.server.shutdown_clients", fake_shutdown)
    return provider


def test_snowball_tool_returns_discovered_papers_with_their_path(
    server, sample_papers, citation_graph
):
    seed = sample_papers[0]
    payload = asyncio.run(
        _call(server, "snowball", papers=[seed.to_dict()], keywords="attention")
    )

    assert payload["seed_count"] == 1
    assert payload["discovered_count"] == 3
    assert payload["truncated"] is False
    assert payload["errors"] == []
    titles = [entry["paper"]["title"] for entry in payload["discovered"]]
    assert titles[-1] == "Cooking With Gas"          # scored last: off topic
    assert set(titles[:2]) == {"Attention Mechanisms Reviewed", "Sparse Attention at Scale"}
    by_title = {entry["paper"]["title"]: entry for entry in payload["discovered"]}
    assert by_title["Attention Mechanisms Reviewed"]["found_by"] == {
        "source_key": seed.dedup_key(), "target_key": "doi:10.1000/r1",
        "relation": "references", "provider": "graph", "depth": 1,
    }
    assert by_title["Cooking With Gas"]["score"]["relevance"] == 0.0
    # ``papers`` is the same list as plain paper dicts, ready for export.
    assert [paper["title"] for paper in payload["papers"]] == titles
    assert len(payload["relations"]) == 3


def test_snowball_tool_passes_its_bounds_through(server, sample_papers, citation_graph):
    payload = asyncio.run(
        _call(
            server, "snowball", papers=[sample_papers[0].to_dict()],
            direction="cited_by", max_per_seed=7, max_total=1,
        )
    )

    assert citation_graph.calls == [(sample_papers[0].source_id, "cited_by", 7)]
    assert payload["discovered_count"] == 1
    assert payload["truncated"] is True
    assert payload["discovered"][0]["score"] is None   # no keywords, no score


def test_snowball_tool_does_not_rediscover_known_papers(
    server, sample_papers, citation_graph
):
    known = _found("c1", "Sparse Attention at Scale").to_dict()
    payload = asyncio.run(
        _call(
            server, "snowball", papers=[sample_papers[0].to_dict()],
            direction="cited_by", known=[known],
        )
    )

    assert [entry["paper"]["source_id"] for entry in payload["discovered"]] == ["c2"]
    assert len(payload["relations"]) == 2   # the link to the known paper is kept


def test_snowball_tool_reports_a_bad_bound_as_a_tool_error(
    server, sample_papers, citation_graph
):
    with pytest.raises(ToolError, match=r"depth must be in \[1, 3\]"):
        asyncio.run(
            _call(server, "snowball", papers=[sample_papers[0].to_dict()], depth=9)
        )
    assert citation_graph.calls == []


def test_snowball_tool_needs_a_seed(server, citation_graph):
    with pytest.raises(ToolError, match="at least one seed paper"):
        asyncio.run(_call(server, "snowball", papers=[]))


def test_snowball_tool_reports_provider_errors_without_failing(
    server, sample_papers, monkeypatch
):
    from thesisagents.core.exceptions import SourceUnavailableError

    broken = _GraphProvider({}, name="openalex",
                            fail_with=SourceUnavailableError("openalex", "HTTP 503"))
    monkeypatch.setattr("thesisagents.core.snowball._default_providers", lambda: [broken])

    async def fake_shutdown():
        return None

    monkeypatch.setattr("thesisagents.mcp.server.shutdown_clients", fake_shutdown)
    payload = asyncio.run(
        _call(server, "snowball", papers=[sample_papers[0].to_dict()], direction="references")
    )

    assert payload["discovered"] == []
    assert len(payload["errors"]) == 1
    assert "openalex references lookup failed" in payload["errors"][0]


def test_search_without_snowball_has_no_snowball_block(
    monkeypatch, server, sample_papers, citation_graph
):
    async def fake_run_search(query, **_kwargs):
        return PaperCollection(query=query, papers=tuple(sample_papers))

    monkeypatch.setattr("thesisagents.mcp.server.run_search", fake_run_search)
    payload = asyncio.run(_call(server, "search", keywords="attention", sources=["arxiv"]))

    assert "snowball" not in payload
    assert citation_graph.calls == []


def test_search_snowball_expands_the_top_results_and_leaves_papers_alone(
    monkeypatch, server, sample_papers, citation_graph
):
    async def fake_run_search(query, **_kwargs):
        return PaperCollection(query=query, papers=tuple(sample_papers))

    monkeypatch.setattr("thesisagents.mcp.server.run_search", fake_run_search)
    payload = asyncio.run(
        _call(
            server, "search", keywords="attention", sources=["arxiv"],
            snowball="both", snowball_seeds=1, snowball_max_per_seed=9,
        )
    )

    assert payload["count"] == 2
    assert payload["papers"] == [paper.to_dict() for paper in sample_papers]
    block = payload["snowball"]
    assert block["seed_count"] == 1
    assert block["discovered_count"] == 3
    assert block["discovered"][0]["score"] is not None   # scored against the keywords
    seed_id = sample_papers[0].source_id
    assert citation_graph.calls == [(seed_id, "references", 9), (seed_id, "cited_by", 9)]


def test_search_snowball_knows_the_whole_result_not_only_the_seeds(
    monkeypatch, server, sample_papers
):
    """The second search result is not a seed. Found again through a citation
    link, it must not come back as a new paper."""
    second = sample_papers[1]
    provider = _GraphProvider(
        {(sample_papers[0].source_id, "references"): [second, _found("r9", "A New Paper")]}
    )
    monkeypatch.setattr("thesisagents.core.snowball._default_providers", lambda: [provider])

    async def fake_run_search(query, **_kwargs):
        return PaperCollection(query=query, papers=tuple(sample_papers))

    async def fake_shutdown():
        return None

    monkeypatch.setattr("thesisagents.mcp.server.run_search", fake_run_search)
    monkeypatch.setattr("thesisagents.mcp.server.shutdown_clients", fake_shutdown)
    payload = asyncio.run(
        _call(
            server, "search", keywords="attention", sources=["arxiv"],
            snowball="references", snowball_seeds=1,
        )
    )

    found = [entry["paper"]["source_id"] for entry in payload["snowball"]["discovered"]]
    assert found == ["r9"]


def test_search_snowball_bad_direction_is_a_tool_error(
    monkeypatch, server, sample_papers, citation_graph
):
    async def fake_run_search(query, **_kwargs):
        return PaperCollection(query=query, papers=tuple(sample_papers))

    monkeypatch.setattr("thesisagents.mcp.server.run_search", fake_run_search)
    with pytest.raises(ToolError, match="direction must be one of"):
        asyncio.run(
            _call(server, "search", keywords="attention", sources=["arxiv"],
                  snowball="sideways")
        )
