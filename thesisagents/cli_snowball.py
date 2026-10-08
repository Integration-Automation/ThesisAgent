"""The CLI's citation-snowballing flags and the stage they switch on.

``--snowball`` expands a run's top results along their citation links before
the export. The flags, their range checks and the stage itself live here, so
``cli.py`` stays about the order of the stages.
"""

from __future__ import annotations

import argparse

from thesisagents.cli_output import print_snowball
from thesisagents.core.constants import (
    MAX_RESULTS_PER_SOURCE,
    SNOWBALL_DEFAULT_DEPTH,
    SNOWBALL_DEFAULT_MAX_PER_SEED,
    SNOWBALL_MAX_DEPTH,
    SNOWBALL_MAX_PER_SEED,
    SNOWBALL_MAX_TOTAL,
)
from thesisagents.core.models import PaperCollection
from thesisagents.core.snowball import Direction, expand_collection, snowball

#: --snowball defaults that are the CLI's own. Five seeds and twenty new
#: papers keep a first expansion to a size a person can read through, and
#: every new paper also costs a PDF download and a deck.
DEFAULT_SNOWBALL_SEEDS = 5
DEFAULT_SNOWBALL_MAX_TOTAL = 20


def add_snowball_arguments(parser: argparse.ArgumentParser) -> None:
    """Register ``--snowball`` and the flags that bound it."""
    parser.add_argument(
        "--snowball",
        choices=tuple(direction.value for direction in Direction),
        default=None,
        help=(
            "Expand the result along citation links before exporting. "
            "'references' adds papers the top results cite, 'cited_by' adds "
            "papers that cite them, 'both' does both. The new papers are "
            "appended to the results and go through the same PDF download "
            "and export. Off by default. Links come from OpenAlex, Semantic "
            "Scholar and Crossref."
        ),
    )
    parser.add_argument(
        "--snowball-seeds",
        type=int,
        default=DEFAULT_SNOWBALL_SEEDS,
        help=(
            "How many of the top-ranked results to expand (used with "
            f"--snowball). Default: {DEFAULT_SNOWBALL_SEEDS}."
        ),
    )
    parser.add_argument(
        "--snowball-depth",
        type=int,
        default=SNOWBALL_DEFAULT_DEPTH,
        help=(
            "Steps to follow from a seed (used with --snowball). 2 also "
            "expands the papers found at step 1. "
            f"1..{SNOWBALL_MAX_DEPTH}. Default: {SNOWBALL_DEFAULT_DEPTH}."
        ),
    )
    parser.add_argument(
        "--snowball-max-per-seed",
        type=int,
        default=SNOWBALL_DEFAULT_MAX_PER_SEED,
        help=(
            "Papers taken per seed and direction (used with --snowball). "
            f"1..{SNOWBALL_MAX_PER_SEED}. Default: {SNOWBALL_DEFAULT_MAX_PER_SEED}."
        ),
    )
    parser.add_argument(
        "--snowball-max-total",
        type=int,
        default=DEFAULT_SNOWBALL_MAX_TOTAL,
        help=(
            "Stop after this many new papers in all (used with --snowball). "
            f"1..{SNOWBALL_MAX_TOTAL}. Default: {DEFAULT_SNOWBALL_MAX_TOTAL}, "
            "kept low because every new paper is also downloaded and exported."
        ),
    )
    parser.add_argument(
        "--snowball-min-relevance",
        type=float,
        default=None,
        help=(
            "Drop papers found by --snowball whose relevance to the --query "
            "keywords is below this fraction (0..1) of the best possible. "
            "Needs --query. Omit to keep every paper found."
        ),
    )


def validate_snowball_args(args: argparse.Namespace) -> None:
    """Reject a ``--snowball-*`` value outside its range before any search runs.

    The boundary this guards: ``snowball()`` checks the same ranges, but only
    when it is called, which is after the search. A typo in a flag should not
    cost the user a multi-source search first.

    Example: ``--snowball both --snowball-depth 9`` exits at once with
    ``--snowball-depth must be in 1..3``.
    """
    if args.snowball is None:
        return
    bounds = (
        ("--snowball-seeds", args.snowball_seeds, MAX_RESULTS_PER_SOURCE),
        ("--snowball-depth", args.snowball_depth, SNOWBALL_MAX_DEPTH),
        ("--snowball-max-per-seed", args.snowball_max_per_seed, SNOWBALL_MAX_PER_SEED),
        ("--snowball-max-total", args.snowball_max_total, SNOWBALL_MAX_TOTAL),
    )
    for flag, value, upper in bounds:
        if not 1 <= value <= upper:
            raise SystemExit(f"{flag} must be in 1..{upper}")
    floor = args.snowball_min_relevance
    if floor is None:
        return
    if not 0.0 <= floor <= 1.0:
        raise SystemExit("--snowball-min-relevance must be in 0..1")
    if not args.query:
        raise SystemExit(
            "--snowball-min-relevance scores papers against the --query "
            "keywords, so it cannot be used with --paper, --pdf or "
            "--library-export"
        )


async def maybe_snowball(
    collection: PaperCollection, args: argparse.Namespace
) -> PaperCollection:
    """Expand ``collection`` along citation links when ``--snowball`` is set.

    The top ``--snowball-seeds`` papers are the seeds. The rest of the
    collection is passed as ``known`` so a paper the search already returned
    is not reported as new. Discovered papers are appended, which sends them
    through the identifier preflight, the PDF download and the export like
    any search result.

    Only a ``--query`` run scores what it finds: its keywords are what the
    papers are scored against. ``--paper`` and ``--pdf`` have no keywords, so
    their discoveries are kept in the order they were found.
    """
    if args.snowball is None or not collection.papers:
        return collection
    result = await snowball(
        collection.papers[: args.snowball_seeds],
        known=collection.papers,
        direction=args.snowball,
        depth=args.snowball_depth,
        max_per_seed=args.snowball_max_per_seed,
        max_total=args.snowball_max_total,
        keywords=collection.query.keywords if args.query else None,
        min_relevance=args.snowball_min_relevance,
    )
    print_snowball(collection, result, args)
    return expand_collection(collection, result)
