"""What the CLI prints about a run, beyond the list of papers.

Split out of ``cli.py`` so that module stays about arguments and the order of
the stages. Each function here turns one part of a finished stage into text
(and, for the diagnostics, a JSON file): what each source returned, why the
papers rank as they do, and what a snowball expansion found.

They take the parsed ``argparse`` namespace where the output depends on
several flags, like the other CLI helpers.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Final

from thesisagents.core.diagnostics import (
    PruningAction,
    SourceStatus,
    collection_report,
)
from thesisagents.core.exceptions import ExportError
from thesisagents.core.models import PaperCollection
from thesisagents.core.snowball import SnowballResult
from thesisagents.utils.path_safety import ensure_export_dir

#: Written into --out by --diagnostics. A fixed name, so a script that
#: prunes a run directory knows where to read the recommendations.
DIAGNOSTICS_FILENAME = "diagnostics.json"
_SOURCE_DETAIL_MAX_CHARS: Final[int] = 100


def print_source_stats(collection: PaperCollection, quiet: bool) -> None:
    """Print what each source contributed to the search that just ran.

    The boundary this guards: a failing source returns nothing and never stops
    the others, so a search that lost half its sources used to look exactly
    like one that found nothing there. Printed after every ``--query`` search,
    with no flag needed, because the user cannot know to ask.

    Nothing is printed under ``--quiet``, or for ``--paper`` / ``--pdf`` runs,
    which have no per-source counts.

    Example::

        Sources (up to 25 requested from each):
          arxiv              23 returned, 19 after dedup
          semantic_scholar    0 returned  rate_limited: gave up after 3 rate-limit retries
          springer            0 returned  disabled: THESISAGENTS_SPRINGER_API_KEY is not set
    """
    diagnostics = collection.diagnostics
    if quiet or diagnostics is None or not diagnostics.source_stats:
        return
    stats = diagnostics.source_stats
    width = max(len(stat.source) for stat in stats)
    print(f"\nSources (up to {stats[0].requested} requested from each):")
    for stat in stats:
        line = f"  {stat.source:<{width}}  {stat.returned:>3} returned"
        if stat.status is SourceStatus.OK:
            line += f", {stat.after_dedup} after dedup"
        else:
            detail = " ".join(stat.detail.split())
            if len(detail) > _SOURCE_DETAIL_MAX_CHARS:
                detail = detail[: _SOURCE_DETAIL_MAX_CHARS - 1] + "…"
            line += f"  {stat.status.value}: {detail}" if detail else f"  {stat.status.value}"
        print(line)


def report_diagnostics(
    collection: PaperCollection, args: argparse.Namespace
) -> None:
    """Print and save the ranking explanation when ``--diagnostics`` is set.

    The boundary this guards: the search returns papers in an order the user
    cannot otherwise question. This is where the score behind each position
    and the pruning advice become visible, right after the search and before
    any PDF is downloaded, so off-topic results can be spotted early.

    stdout gets one line per paper, with the reasons spelled out only for
    papers recommended for review or pruning (a 25-paper run would otherwise
    print some 200 lines). ``diagnostics.json`` in ``--out`` holds everything.
    ``--quiet`` silences stdout and still writes the file.

    Nothing is removed from ``collection``: the recommendations are advice.

    Example line: ``[  4] prune   total 2.18 = relevance 0.00 + recency 0.11
    + citations 2.07``.
    """
    if not args.diagnostics or not collection.papers:
        return
    if collection.diagnostics is None:
        print(
            "No ranking diagnostics for this run: they are produced by "
            "--query searches, not by --paper or --pdf.",
            file=sys.stderr,
        )
        return
    report = collection_report(collection)
    path = ensure_export_dir(args.out) / DIAGNOSTICS_FILENAME
    try:
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as err:
        raise ExportError("diagnostics", f"could not write {path}: {err}") from err
    if args.quiet:
        return
    print(f"\nRanking diagnostics for: {collection.query.keywords}")
    for entry in report["papers"]:
        _print_diagnostic_entry(entry)
    summary = report["summary"]
    print(
        f"Recommendations: {summary[PruningAction.KEEP.value]} keep, "
        f"{summary[PruningAction.REVIEW.value]} review, "
        f"{summary[PruningAction.PRUNE.value]} prune. "
        "Advice only, nothing was removed."
    )
    print(f"Diagnostics written to: {path.resolve()}")


def _print_diagnostic_entry(entry: dict) -> None:
    """One paper of the ``--diagnostics`` printout (see ``_report_diagnostics``)."""
    score = entry["score"]
    advice = entry["recommendation"]
    if score is None or advice is None:
        print(f"  [{entry['rank']:>3}] (no score recorded) {entry['title']}")
        return
    print(
        f"  [{entry['rank']:>3}] {advice['action']:<7} "
        f"total {score['total']:.2f} = relevance {score['relevance']:.2f} "
        f"+ recency {score['recency']:.2f} + citations {score['citation']:.2f}"
    )
    print(f"        {entry['title']}")
    if advice["action"] == PruningAction.KEEP.value:
        return
    for reason in score["reasons"]:
        print(f"        - {reason}")
    for reason in advice["reasons"]:
        print(f"        > {reason}")
    print(f"        rule: {advice['threshold']}")


def print_snowball(
    collection: PaperCollection, result: SnowballResult, args: argparse.Namespace
) -> None:
    """Say what the snowball found and how each paper was reached.

    Provider errors go to stderr even under ``--quiet``: a provider that
    failed means links are missing, and the user should know the expansion
    was incomplete.
    """
    for error in result.errors:
        print(f"snowball: {error}", file=sys.stderr)
    if args.quiet:
        return
    names = {paper.dedup_key(): paper.bibtex_key() for paper in collection.papers}
    names.update({paper.dedup_key(): paper.bibtex_key() for paper in result.papers})
    print(
        f"\nSnowball ({args.snowball}, depth {args.snowball_depth}) from "
        f"{len(result.seeds)} seed(s): {len(result.discovered)} new paper(s), "
        f"{len(result.relations)} citation link(s)."
    )
    for entry in result.discovered:
        via = entry.found_by
        origin = names.get(via.source_key, via.source_key)
        print(f"  + {entry.paper.title}")
        print(
            f"      {via.relation.value} of {origin} "
            f"({via.provider}, depth {via.depth})"
        )
    if result.truncated:
        print(
            f"  Stopped at --snowball-max-total {args.snowball_max_total}: "
            "more papers were found than kept."
        )
