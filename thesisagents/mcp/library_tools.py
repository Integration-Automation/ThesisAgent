"""MCP tools for the literature library: ``library_add``, ``library_search``, ``library_stats``.

Kept apart from ``server.py`` so the tool surface stays readable as it grows.
``server.build_server`` calls :func:`register_library_tools` with its own
tool decorator, which is how these tools get the same error reporting as the
rest (a ``ThesisAgentsError`` reaches the client with its message).

The server is stateless between calls, so every tool names the library file
and opens it for the length of the call.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from thesisagents.core.diagnostics import PaperRelation, RelationKind
from thesisagents.core.exceptions import ThesisAgentsError
from thesisagents.core.models import Paper
from thesisagents.core.query import normalize_query
from thesisagents.library import Library

#: Runs listed by ``library_stats``. The newest ones say what the library was
#: last used for, and the full history can run to hundreds of rows.
_STATS_RECENT_RUNS = 10
#: Upper bound of ``library_search``'s ``limit``. Each paper carries its
#: abstract, so a larger answer would mostly be noise in a model's context.
_SEARCH_MAX_LIMIT = 200
_RELATION_FIELDS = ("source_key", "target_key", "relation", "provider", "depth")


def register_library_tools(tool: Callable[[Callable[..., Any]], Any]) -> None:
    """Register the three library tools through ``tool`` (``server._tool(server)``)."""

    @tool
    def library_add(
        library: str,
        papers: list[dict[str, Any]],
        keywords: str = "",
        relations: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Keep papers in a literature library, so later sessions can reuse them.

        ``library`` is the path of an SQLite file, created when it does not
        exist. ``papers`` are paper dicts from ``search``, ``snowball`` or
        ``fetch_paper``, with their ``summary`` when you have authored one.

        Adding is a merge. A paper the library already holds (same DOI, arXiv
        ID, or title + first author + year) is updated, not duplicated: fields
        it lacked are filled in and the new sighting is recorded. So it is
        safe to add the same search again.

        ``keywords`` records what the papers were found for. ``relations`` are
        the citation links from ``snowball`` (its ``relations`` list, passed
        as it is). A link is stored when both of its papers are in the
        library after this call.

        Returns ``added`` (new papers), ``merged`` (already held),
        ``relations_added``, ``relations_skipped`` and ``total`` (papers in
        the library now).
        """
        if not papers:
            raise ThesisAgentsError("library_add requires at least one paper")
        links = tuple(_relation(entry) for entry in relations or ())
        with Library(library) as store:
            report = store.add_papers(
                tuple(Paper.from_dict(entry) for entry in papers),
                keywords=normalize_query(keywords) if keywords.strip() else "",
                kind="mcp",
                relations=links,
            )
            return {"library": str(store.path), **report.to_dict()}

    @tool
    def library_search(
        library: str,
        query: str = "",
        limit: int = 20,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> dict[str, Any]:
        """Find papers already kept in a literature library. No network access.

        Use it before a new ``search``: papers found and verified in an
        earlier session are here, with any summary authored for them.

        ``query`` is scored like a search (stemming, phrases, acronyms), and
        only papers matching at least one query term are returned, best
        first. An empty ``query`` lists the most recently seen papers.
        ``limit`` is 1..200.

        Returns ``papers`` (plain paper dicts, ready for ``export`` or
        ``download_pdfs``) and ``entries``, one per paper in the same order,
        with its history: ``first_seen``, ``last_seen``, ``times_seen``, the
        ``sources`` that returned it, and its ``score`` for the query.
        ``total`` is the number of papers in the library.
        """
        if not 1 <= limit <= _SEARCH_MAX_LIMIT:
            raise ThesisAgentsError(f"limit must be in [1, {_SEARCH_MAX_LIMIT}]")
        with Library(library, create=False) as store:
            found = store.search(query, limit=limit, year_from=year_from, year_to=year_to)
            total = len(store)
            path = str(store.path)
        return {
            "library": path,
            "query": query,
            "total": total,
            "count": len(found),
            "papers": [entry.paper.to_dict() for entry in found],
            "entries": [
                {
                    "paper_key": entry.paper.dedup_key(),
                    "bibtex_key": entry.paper.bibtex_key(),
                    "first_seen": entry.first_seen,
                    "last_seen": entry.last_seen,
                    "times_seen": entry.times_seen,
                    "sources": list(entry.sources),
                    "score": None if entry.score is None else entry.score.to_dict(),
                }
                for entry in found
            ],
        }

    @tool
    def library_stats(library: str) -> dict[str, Any]:
        """Summarise a literature library: how much it holds and where it came from.

        Returns the number of ``papers``, ``runs`` and citation ``relations``,
        the year range, the papers each source has returned (``sources``), the
        stored DOI / URL verdicts by status (``verifications``), the
        ``schema_version``, and ``recent_runs`` (the latest imports with their
        keywords and paper counts).
        """
        with Library(library, create=False) as store:
            payload = store.stats().to_dict()
            payload["recent_runs"] = [
                {
                    "run_id": run.run_id,
                    "started_at": run.started_at,
                    "kind": run.kind,
                    "keywords": run.keywords,
                    "papers": run.papers,
                }
                for run in store.runs()[:_STATS_RECENT_RUNS]
            ]
        return payload


def _relation(entry: dict[str, Any]) -> PaperRelation:
    """Rebuild one citation link from the dict shape ``snowball`` returns.

    The boundary this guards: links arrive as JSON written or forwarded by an
    agent. A missing field or an unknown direction is reported by name here,
    instead of surfacing as a ``KeyError`` from inside the import.

    Example: ``{"source_key": "doi:10.1/a", "target_key": "doi:10.1/b",
    "relation": "references", "provider": "openalex", "depth": 1}``.
    """
    missing = [name for name in _RELATION_FIELDS if entry.get(name) in (None, "")]
    if missing:
        raise ThesisAgentsError(
            f"relation is missing field(s): {', '.join(missing)} "
            f"(expected {', '.join(_RELATION_FIELDS)})"
        )
    try:
        kind = RelationKind(entry["relation"])
        depth = int(entry["depth"])
    except ValueError as err:
        raise ThesisAgentsError(
            f"relation is not valid ({err}): 'relation' must be "
            f"'{RelationKind.REFERENCES.value}' or '{RelationKind.CITED_BY.value}' "
            "and 'depth' a whole number"
        ) from err
    return PaperRelation(
        source_key=str(entry["source_key"]),
        target_key=str(entry["target_key"]),
        relation=kind,
        provider=str(entry["provider"]),
        depth=depth,
    )
