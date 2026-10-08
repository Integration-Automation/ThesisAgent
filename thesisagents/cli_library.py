"""The CLI's literature-library flags.

``--library PATH`` names the library file. Three flags say what to do with it:

* ``--library-add`` merges the papers of a ``--query`` / ``--paper`` / ``--pdf``
  run into the library.
* ``--library-search QUERY`` lists stored papers that match, without any
  network access.
* ``--library-export [QUERY]`` sends stored papers through ``--export``.

``--library`` on its own, with a normal run, makes the library the run's
identifier cache: a DOI or URL that verified in an earlier run is not asked
about again.

Kept out of ``cli.py`` so that module stays about the order of the stages.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from thesisagents.core.models import PaperCollection
from thesisagents.library import Library, LibraryEntry


def add_library_arguments(
    parser: argparse.ArgumentParser, mode: argparse._MutuallyExclusiveGroup
) -> None:
    """Register the library flags. The two that replace a search join ``mode``."""
    parser.add_argument(
        "--library",
        metavar="PATH",
        default=None,
        help=(
            "A literature library: an SQLite file that keeps papers, their "
            "citation links and the identifier checks between runs. Created "
            "when it does not exist. With a normal run it is the identifier "
            "cache, so a DOI or URL verified in an earlier run is not checked "
            "again. Combine with --library-add, --library-search or "
            "--library-export."
        ),
    )
    parser.add_argument(
        "--library-add",
        action="store_true",
        help=(
            "Merge this run's papers into --library, with the query, what "
            "each source returned, each paper's score and any citation links "
            "from --snowball. A paper the library already holds is merged, "
            "not duplicated."
        ),
    )
    mode.add_argument(
        "--library-search",
        metavar="QUERY",
        default=None,
        help=(
            "List the papers in --library that match QUERY, best first, and "
            "exit. Nothing is fetched. Scored like a search, so only papers "
            "matching at least one query term are listed. --max caps the "
            "list, --year-from / --year-to narrow it. Pass \"\" to list the "
            "most recently seen papers."
        ),
    )
    mode.add_argument(
        "--library-export",
        metavar="QUERY",
        nargs="?",
        const="",
        default=None,
        help=(
            "Export the papers in --library through --export, all of them or "
            "only those matching QUERY. Default formats: xlsx,bib. No PDF is "
            "downloaded unless --export includes pdf."
        ),
    )


def validate_library_args(args: argparse.Namespace) -> None:
    """Reject a contradictory combination of library flags before anything runs.

    The boundary this guards: the flags are only looked at late in a run
    (``--library-add`` after the search and the enrichment). A forgotten
    ``--library`` should not cost the user that work first.

    Example: ``--query x --library-add`` without ``--library`` exits at once
    with ``--library-add needs --library PATH``.
    """
    wants_read = args.library_search is not None or args.library_export is not None
    if args.library is None:
        for flag, used in (
            ("--library-add", args.library_add),
            ("--library-search", args.library_search is not None),
            ("--library-export", args.library_export is not None),
        ):
            if used:
                raise SystemExit(f"{flag} needs --library PATH")
        return
    if args.library_add and wants_read:
        raise SystemExit(
            "--library-add stores the papers of a --query / --paper / --pdf "
            "run, so it cannot be combined with --library-search or "
            "--library-export, which read the library"
        )


@contextmanager
def opened_library(args: argparse.Namespace) -> Iterator[Library | None]:
    """The run's library, opened before the search and closed after the export.

    Yields ``None`` when ``--library`` was not given. A read
    (``--library-export``) refuses a path that does not exist, so a mistyped
    path is an error and not an empty export.
    """
    if args.library is None:
        yield None
        return
    library = Library(args.library, create=args.library_export is None)
    try:
        yield library
    finally:
        library.close()


def library_collection(library: Library, args: argparse.Namespace) -> PaperCollection:
    """The papers ``--library-export`` asked for, as a collection to export."""
    return library.collection(
        args.library_export, year_from=args.year_from, year_to=args.year_to
    )


def add_to_library(
    library: Library | None, collection: PaperCollection, args: argparse.Namespace
) -> None:
    """Merge the run's papers into the library when ``--library-add`` is set.

    Example output: ``Library thesis.db: 12 added, 8 already there, 20
    citation link(s) stored. 132 paper(s) in all.``
    """
    if library is None or not args.library_add or not collection.papers:
        return
    kind = "search" if args.query else "paper" if args.paper else "pdf"
    report = library.add_collection(collection, kind=kind)
    if args.quiet:
        return
    print(
        f"\nLibrary {library.path}: {report.added} added, "
        f"{report.merged} already there, {report.relations_added} citation "
        f"link(s) stored. {report.total} paper(s) in all."
    )
    if report.relations_skipped:
        print(
            f"  {report.relations_skipped} citation link(s) not stored: the "
            "paper at the other end is not in the library."
        )


def run_library_search(args: argparse.Namespace) -> int:
    """``--library-search``: print the matching stored papers. Returns the exit code.

    Returns 1 when nothing matches, like a search that found nothing, so a
    script can branch on it.

    Example output::

        Library thesis.db: 2 of 132 paper(s) match "graph neural network".
          [  1]  5.72  (2024) Ada Lovelace: Graph Neural Networks for Molecules
                 doi:10.1/gnn | seen 2 time(s), last 2026-10-08 | arxiv, openalex
    """
    with Library(args.library, create=False) as library:
        total = len(library)
        entries = library.search(
            args.library_search,
            limit=args.max,
            year_from=args.year_from,
            year_to=args.year_to,
        )
    query = args.library_search.strip()
    if not entries:
        print(
            f"Library {library.path}: none of {total} paper(s) match \"{query}\"."
            if query
            else f"Library {library.path} is empty.",
            file=sys.stderr,
        )
        return 1
    if args.quiet:
        return 0
    if query:
        print(
            f"Library {library.path}: {len(entries)} of {total} paper(s) "
            f"match \"{query}\"."
        )
    else:
        print(
            f"Library {library.path}: {len(entries)} of {total} paper(s), "
            "most recently seen first."
        )
    for position, entry in enumerate(entries, start=1):
        _print_entry(position, entry)
    return 0


def _print_entry(position: int, entry: LibraryEntry) -> None:
    paper = entry.paper
    year = paper.year or "n.d."
    first_author = paper.authors[0] if paper.authors else "—"
    score = f"{entry.score.total:>5.2f}  " if entry.score is not None else ""
    print(f"  [{position:>3}]  {score}({year}) {first_author}: {paper.title}")
    sources = ", ".join(entry.sources) or paper.source
    # Stored in UTC, shown as the local date: a paper added at 07:00 in Taipei
    # was added "today" for its user, and UTC still says yesterday.
    last_seen = datetime.fromisoformat(entry.last_seen).astimezone().date()
    print(
        f"         {paper.dedup_key()} | seen {entry.times_seen} time(s), "
        f"last {last_seen} | {sources}"
    )
