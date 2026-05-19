"""MCP tool surface for AutoPaperToPPT.

Tools:
- list_sources() -> {sources: [...]}
  Discovery tool: report every plugin name, whether it needs an API key,
  whether it is currently enabled by env vars, and the env-var the agent
  would have to set to enable it.
- search(keywords, sources, max_results, year_from, year_to,
         top_tier_only, min_citations) -> {papers: [...]}
- fetch_paper(identifier) -> {paper: {...}}
- fetch_pdf_text(pdf_url) -> {text, page_count, chars}
- download_pdfs(papers, out_dir) -> {results: [...]}
  Batch-download a list of papers' PDFs into ``{out_dir}/pdfs/`` so an
  LLM agent can drive the PDF retrieval step before authoring rich
  summaries.
- export(papers, keywords, formats, out_dir, filename_stem, include_abstract,
         language, max_slides_per_paper) -> {written: {fmt: path}}
  formats may be any of: pptx, xlsx, md, bib, json
  papers[*].summary may include rich fields (pain_points, research_question,
  headline_metrics, technique_table, literature_table, method_sections,
  research_questions, rq_results, …) — when present, the PPT switches to
  thesis-style layout.
- pptx_inspect(path) -> {slides: [...]}
- pptx_update_slide(path, slide_index, title?, body?, meta?, shape_updates?) -> {path}
- pptx_delete_slide(path, slide_index) -> {path}
- pptx_reorder_slides(path, new_order) -> {path}
- pptx_add_slide(path, title, body, meta, position?) -> {path}

For an LLM-as-agent flow (no Anthropic API key needed):
  1. list_sources() — pick the source mix
  2. search(keywords, sources, ...) — find candidates
  3. download_pdfs(papers, out_dir) — pull the PDFs locally
  4. fetch_pdf_text(paper.pdf_url) per paper
  5. (the LLM reads each PDF, produces a structured summary in-context)
  6. export([{...paper, "summary": {...rich fields...}}], language="zh-tw", ...)
"""

from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from autopapertoppt.core.constants import ALL_SOURCES, DEFAULT_SOURCES, EXPORT_PPTX
from autopapertoppt.core.exceptions import AutoPaperToPPTError
from autopapertoppt.core.identifiers import parse_identifier
from autopapertoppt.core.models import ExportOptions, Paper, PaperCollection, Query
from autopapertoppt.core.pdf_download import download_pdfs as core_download_pdfs
from autopapertoppt.core.pipeline import run_search, run_single_paper
from autopapertoppt.core.query import normalize_query
from autopapertoppt.exporters import export_collection, pptx_edit
from autopapertoppt.fetchers.http import shutdown_clients
from autopapertoppt.utils.logging import get_logger

_LOG = get_logger(__name__)

# Plugins gated by an env var.
#  - ``"opt_in"`` plugins refuse to load WITHOUT the env var (e.g. Springer
#    needs an API key).
#  - ``"opt_out"`` plugins refuse to load WITH the env var set (e.g. IEEE
#    and Scholar are default-on; their respective DISABLE env vars flip
#    them off).
# list_sources reports enablement without round-tripping through
# load_fetcher (which would raise on disabled plugins).
_PLUGIN_OPT_IN_ENV: dict[str, tuple[str, ...]] = {
    "springer": ("AUTOPAPERTOPPT_SPRINGER_API_KEY",),
}
_PLUGIN_OPT_OUT_ENV: dict[str, tuple[str, ...]] = {
    "ieee": ("AUTOPAPERTOPPT_DISABLE_IEEE_SCRAPING",),
    "scholar": ("AUTOPAPERTOPPT_DISABLE_SCHOLAR_SCRAPING",),
}


def build_server() -> FastMCP:
    """Build and register all tools on a FastMCP instance."""
    server = FastMCP("autopapertoppt")
    _register_discovery_tools(server)
    _register_search_tools(server)
    _register_export_tool(server)
    _register_pdf_tool(server)
    _register_pdf_download_tool(server)
    _register_pptx_tools(server)
    return server


def _register_discovery_tools(server: FastMCP) -> None:
    @server.tool()
    def list_sources() -> dict[str, Any]:
        """Report every available source plugin and whether it is currently enabled.

        Plugin gating today:

        - **ieee** — default-ON. Set ``AUTOPAPERTOPPT_DISABLE_IEEE_SCRAPING=1``
          to opt out, or ``AUTOPAPERTOPPT_IEEE_API_KEY`` for the official
          Xplore API (better metadata + pdf_url for subscribers).
        - **scholar** — default-ON. Set ``AUTOPAPERTOPPT_DISABLE_SCHOLAR_SCRAPING=1``
          to opt out (Google's ToS forbids automated access; default-on
          for coverage, accept the risk).
        - **springer** — opt-IN via ``AUTOPAPERTOPPT_SPRINGER_API_KEY``.
          Free key from https://dev.springernature.com/.

        Agents should call this once before ``search`` so they pass only
        enabled sources — disabled plugins are silently skipped by the
        pipeline but the agent has no other way to know about them.
        """
        entries: list[dict[str, Any]] = []
        for name in ALL_SOURCES:
            opt_in_vars = _PLUGIN_OPT_IN_ENV.get(name, ())
            opt_out_vars = _PLUGIN_OPT_OUT_ENV.get(name, ())
            opted_in = (not opt_in_vars) or any(
                _env_var_set(var) for var in opt_in_vars
            )
            opted_out = any(_env_var_truthy(var) for var in opt_out_vars)
            enabled = opted_in and not opted_out
            entries.append(
                {
                    "name": name,
                    "in_default_mix": name in DEFAULT_SOURCES,
                    "opt_in_env_var": list(opt_in_vars),
                    "opt_out_env_var": list(opt_out_vars),
                    "enabled": enabled,
                }
            )
        return {
            "sources": entries,
            "default_sources": list(DEFAULT_SOURCES),
        }


def _env_var_set(name: str) -> bool:
    """True when the env var has any non-empty value."""
    return bool((os.environ.get(name) or "").strip())


def _env_var_truthy(name: str) -> bool:
    """True when the env var is set to exactly ``"1"`` — the convention
    for DISABLE flags. Loose values like ``"true"`` are intentionally
    NOT honoured so a user has to be deliberate about flipping a default
    off."""
    return (os.environ.get(name) or "").strip() == "1"


def _register_pdf_tool(server: FastMCP) -> None:
    @server.tool()
    async def fetch_pdf_text(pdf_url: str, source: str = "intelligence") -> dict[str, Any]:
        """Download a paper's PDF over HTTPS-only and extract its body text.

        Use this when you (an LLM agent) want to produce an enriched
        ``PaperSummary`` yourself: call ``fetch_paper`` for metadata, then
        ``fetch_pdf_text`` for the body text, then write the structured
        summary in-context and pass it to ``export`` via the paper's
        ``summary`` field.

        No Anthropic API call — the extraction is local. The Python
        ``--enrich`` flow is a separate convenience for non-agent users.
        """
        from autopapertoppt.intelligence.pdf import fetch_and_extract

        extracted = await fetch_and_extract(pdf_url, source=source)
        return {
            "url": extracted.url,
            "page_count": extracted.page_count,
            "chars": extracted.chars,
            "text": extracted.text,
        }


def _register_pdf_download_tool(server: FastMCP) -> None:
    @server.tool()
    async def download_pdfs(
        papers: list[dict[str, Any]], out_dir: str
    ) -> dict[str, Any]:
        """Download every paper's PDF into ``{out_dir}/pdfs/``.

        Wraps ``autopapertoppt.core.pdf_download.download_pdfs``. Skips
        papers with no ``pdf_url`` (reported as ``no_pdf_url``) and reports
        any HTTP / content-type failures by reason. Each result is keyed
        by the paper's ``bibtex_key()`` so an agent can match results back
        to the ``papers`` list it passed in.

        Use this between ``search`` and ``fetch_pdf_text`` when you need
        the PDFs persisted on disk (e.g. for later re-reading or for
        embedding into the rich PPT via figure extraction).
        """
        if not papers:
            raise AutoPaperToPPTError("download_pdfs requires at least one paper")
        paper_objs = tuple(Paper.from_dict(p) for p in papers)
        synthetic_query = Query(
            keywords="download",
            sources=tuple({p.source for p in paper_objs}) or ("arxiv",),
            max_results=max(len(paper_objs), 1),
        )
        collection = PaperCollection(query=synthetic_query, papers=paper_objs)
        try:
            results = await core_download_pdfs(collection, out_dir)
        finally:
            await shutdown_clients()
        saved = sum(1 for r in results if r.path is not None)
        return {
            "out_dir": out_dir,
            "saved": saved,
            "skipped": len(results) - saved,
            "results": [
                {
                    "paper_key": r.paper_key,
                    "path": str(r.path) if r.path is not None else None,
                    "reason": r.skipped_reason,
                }
                for r in results
            ],
        }


def _register_search_tools(server: FastMCP) -> None:
    @server.tool()
    async def search(
        keywords: str,
        sources: list[str] | None = None,
        max_results: int = 10,
        year_from: int | None = None,
        year_to: int | None = None,
        top_tier_only: bool = True,
        min_citations: int | None = None,
    ) -> dict[str, Any]:
        """Search papers by keywords across one or more sources.

        Defaults to the project's full default source mix (all plugins
        that need no API key) when ``sources`` is omitted — call
        ``list_sources`` first if you want to narrow the search.

        ``top_tier_only`` (default ``True``) keeps only papers whose
        venue matches the curated top-tier whitelist (flagship CS
        conferences + Nature / Science / PNAS / CACM / LNCS). arXiv
        preprints always pass through. Pass ``False`` for a broader net.

        ``min_citations`` filters out papers below the threshold; pass
        ``None`` for no minimum.

        Returns a JSON-serialisable dict with a `papers` list. Each paper has
        the same fields as Paper.to_dict() — pass the list straight to `export`.
        """
        normalised = normalize_query(keywords)
        chosen = tuple(sources) if sources else DEFAULT_SOURCES
        query = Query(
            keywords=normalised,
            sources=chosen,
            max_results=max_results,
            year_from=year_from,
            year_to=year_to,
            top_tier_only=top_tier_only,
            min_citations=min_citations,
        )
        try:
            collection = await run_search(query)
        finally:
            await shutdown_clients()
        return _collection_to_payload(collection)

    @server.tool()
    async def fetch_paper(identifier: str) -> dict[str, Any]:
        """Fetch a single paper by identifier (arXiv ID/URL or DOI)."""
        parsed = parse_identifier(identifier)
        try:
            collection = await run_single_paper(parsed)
        finally:
            await shutdown_clients()
        if not collection.papers:
            raise AutoPaperToPPTError(f"no paper found for identifier {identifier!r}")
        return {
            "paper": collection.papers[0].to_dict(),
            "identifier": {"kind": parsed.kind.value, "value": parsed.value},
        }


def _register_export_tool(server: FastMCP) -> None:
    @server.tool()
    def export(
        papers: list[dict[str, Any]],
        keywords: str,
        formats: list[str],
        out_dir: str,
        filename_stem: str | None = None,
        include_abstract: bool = True,
        language: str = "en",
        max_slides_per_paper: int | None = 25,
    ) -> dict[str, Any]:
        """Export a list of papers (from search / fetch_paper) to disk.

        Each paper dict may carry a ``summary`` field — when populated with
        the rich-tier shape (pain_points, research_question, headline_metrics,
        technique_table, literature_table, method_sections, research_questions,
        rq_results, …), the PPT exporter switches to thesis-style layout.
        ``language`` accepts en / zh-tw / zh-cn / ja.

        ``max_slides_per_paper`` caps the per-paper slide count after the
        priority-based trim (cover/references/contributions are kept,
        Q&A/figure slides drop first). Default 25; pass ``0`` (or
        ``None``) for unlimited.
        """
        if not papers:
            raise AutoPaperToPPTError("export requires at least one paper")
        paper_objs = tuple(Paper.from_dict(p) for p in papers)
        query = Query(
            keywords=normalize_query(keywords),
            sources=("arxiv",),
            max_results=max(len(paper_objs), 1),
        )
        collection = PaperCollection(query=query, papers=paper_objs)
        # 0 from the wire means "unlimited" — match the CLI semantics.
        slide_cap = (
            None if max_slides_per_paper in (None, 0) else int(max_slides_per_paper)
        )
        options = ExportOptions(
            formats=tuple(formats),
            out_dir=out_dir,
            filename_stem=filename_stem,
            include_abstract=include_abstract,
            language=language,
            max_slides_per_paper=slide_cap,
        )
        written = export_collection(collection, options)
        return {
            "written": {fmt: str(path) for fmt, path in written.items()},
            "pptx_path": str(written[EXPORT_PPTX]) if EXPORT_PPTX in written else None,
        }


def _register_pptx_tools(server: FastMCP) -> None:
    @server.tool()
    def pptx_inspect(path: str) -> dict[str, Any]:
        """Return slide-by-slide structure (index, title, every text frame)."""
        slides = pptx_edit.inspect(path)
        return {
            "path": path,
            "slide_count": len(slides),
            "slides": [
                {
                    "index": s.index,
                    "title": s.title,
                    "shapes": [
                        {"index": shape.index, "name": shape.name, "text": shape.text}
                        for shape in s.shapes
                    ],
                }
                for s in slides
            ],
        }

    @server.tool()
    def pptx_update_slide(
        path: str,
        slide_index: int,
        title: str | None = None,
        body: str | None = None,
        meta: str | None = None,
        shape_updates: dict[int, str] | None = None,
        out_path: str | None = None,
    ) -> dict[str, Any]:
        """Update text on a slide.

        Use title/body/meta when shapes are named; otherwise pass
        `shape_updates={shape_index: new_text}`.
        """
        clean_updates = _coerce_shape_updates(shape_updates)
        written = pptx_edit.update_slide(
            path,
            slide_index,
            title=title,
            body=body,
            meta=meta,
            shape_updates=clean_updates,
            out_path=out_path,
        )
        return {"path": str(written), "slide_index": slide_index}

    @server.tool()
    def pptx_delete_slide(
        path: str, slide_index: int, out_path: str | None = None
    ) -> dict[str, Any]:
        """Delete the slide at `slide_index` and save."""
        written = pptx_edit.delete_slide(path, slide_index, out_path=out_path)
        return {"path": str(written), "deleted": slide_index}

    @server.tool()
    def pptx_reorder_slides(
        path: str, new_order: list[int], out_path: str | None = None
    ) -> dict[str, Any]:
        """Reorder slides so new index i comes from old index new_order[i]."""
        written = pptx_edit.reorder_slides(path, new_order, out_path=out_path)
        return {"path": str(written), "new_order": new_order}

    @server.tool()
    def pptx_add_slide(
        path: str,
        title: str,
        body: str = "",
        meta: str = "",
        position: int | None = None,
        out_path: str | None = None,
    ) -> dict[str, Any]:
        """Add a new slide (append by default, or insert at `position`)."""
        written = pptx_edit.add_slide(
            path,
            title=title,
            body=body,
            meta=meta,
            position=position,
            out_path=out_path,
        )
        return {"path": str(written), "position": position}


def _collection_to_payload(collection: PaperCollection) -> dict[str, Any]:
    return {
        "query": {
            "keywords": collection.query.keywords,
            "sources": list(collection.query.sources),
            "max_results": collection.query.max_results,
            "year_from": collection.query.year_from,
            "year_to": collection.query.year_to,
        },
        "count": len(collection),
        "papers": [paper.to_dict() for paper in collection.papers],
    }


def _coerce_shape_updates(raw: dict[int, str] | dict[str, str] | None) -> dict[int, str] | None:
    if raw is None:
        return None
    cleaned: dict[int, str] = {}
    for key, value in raw.items():
        try:
            idx = int(key)
        except (TypeError, ValueError) as err:
            raise AutoPaperToPPTError(
                f"shape_updates keys must be integers, got {key!r}"
            ) from err
        cleaned[idx] = value
    return cleaned
