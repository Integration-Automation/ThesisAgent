"""The CLI's deck-template flags and the check they trigger before a run.

``--pptx-template`` builds decks on a PowerPoint template instead of the
built-in navy-band deck, and ``--pptx-template-config`` overrides how the
template is used. The contract itself is in
``thesisagents/exporters/template.py``. Kept out of ``cli.py`` so that module
stays about the order of the stages.
"""

from __future__ import annotations

import argparse
import sys

from thesisagents.exporters.template import TemplateError, validate_template


def add_template_arguments(parser: argparse.ArgumentParser) -> None:
    """Register ``--pptx-template`` and ``--pptx-template-config``."""
    parser.add_argument(
        "--pptx-template",
        metavar="FILE",
        default=None,
        help=(
            "Build decks on a PowerPoint template (.pptx / .potx) instead of "
            "the built-in navy-band deck: its layouts, background and logo "
            "show through. Checked before the search starts: it needs 16:9 "
            "slides and a layout for slide content (named 'content' or "
            "'Blank'). Run `thesisagents validate-template FILE` to see what "
            "an export would use."
        ),
    )
    parser.add_argument(
        "--pptx-template-config",
        metavar="FILE",
        default=None,
        help=(
            "A TOML or JSON file of overrides for --pptx-template: which "
            "layout each slide role uses ([layouts]), roles whose title goes "
            "into the layout's title placeholder ([placeholders]), font "
            "families ([fonts]), palette colours ([colors]) and whether the "
            "header band and cover panel are drawn ([chrome])."
        ),
    )


def validate_template_early(args: argparse.Namespace) -> None:
    """Check ``--pptx-template`` against the template contract before the search.

    The boundary this guards: the exporter runs the same check, but only
    when the first deck is built, which is after the search, the PDF
    downloads and the enrichment. A layout name mistyped in the config should
    cost a second, not the run.

    Raises ``TemplateError`` (exit code 2 through ``main``) listing every
    problem. Warnings, such as a 4:3 template being resized, go to stderr
    even under ``--quiet``, because they change how the deck looks.

    Example: ``--pptx-template thesis.pptx --pptx-template-config thesis.toml``
    with ``[layouts] table = "Nope"`` stops at once and lists the layouts
    the template does have.
    """
    if args.pptx_template_config and not args.pptx_template:
        raise SystemExit("--pptx-template-config needs --pptx-template FILE")
    if not args.pptx_template:
        return
    report = validate_template(
        args.pptx_template, args.pptx_template_config, dark_mode=args.dark_mode
    )
    if not report.ok:
        raise TemplateError(report.message())
    for issue in report.warnings:
        print(f"Template warning: {issue.message}", file=sys.stderr)
