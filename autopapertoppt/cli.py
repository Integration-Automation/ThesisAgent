"""argparse-based CLI for AutoPaperToPPT.

Usage:
    py -m autopapertoppt --query "diffusion models" --source arxiv \\
        --max 10 --export pptx,md,bib --out ./exports/
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import dataclasses
import sys
from pathlib import Path
from typing import Final

from autopapertoppt import __version__
from autopapertoppt.core.constants import (
    ALL_EXPORTS,
    ALL_SOURCES,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SOURCES,
    EXPORT_BIBTEX,
    EXPORT_PPTX,
    EXPORT_XLSX,
    MAX_RESULTS_PER_SOURCE,
)
from autopapertoppt.core.exceptions import AutoPaperToPPTError, ConfigError
from autopapertoppt.core.identifiers import parse_identifier
from autopapertoppt.core.models import ExportOptions, Paper, PaperCollection, Query
from autopapertoppt.core.pdf_download import download_pdfs
from autopapertoppt.core.pipeline import (
    enrich_collection,
    run_search,
    run_single_paper,
)
from autopapertoppt.core.query import normalize_query
from autopapertoppt.exporters import export_collection
from autopapertoppt.exporters.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from autopapertoppt.fetchers.http import shutdown_clients
from autopapertoppt.utils.logging import get_logger
from autopapertoppt.utils.path_safety import ensure_export_dir, safe_filename

_LOG = get_logger(__name__)
_DEFAULT_OUT_DIR = "./exports"
_DEFAULT_EXPORTS_SEARCH = (EXPORT_PPTX, EXPORT_XLSX, EXPORT_BIBTEX)
_DEFAULT_EXPORTS_SINGLE = (EXPORT_PPTX, EXPORT_BIBTEX)
DEFAULT_PAYWALL_THRESHOLD = 0.30


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autopapertoppt",
        description=(
            "Search papers by keywords across multiple sources and export them "
            "to slides, summaries, and BibTeX."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"autopapertoppt {__version__}"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--query",
        "-q",
        help="Search keywords (use quotes for multi-word queries).",
    )
    mode.add_argument(
        "--paper",
        "-p",
        help=(
            "Fetch a single paper by identifier: arXiv ID (2401.08741), "
            "arXiv URL (https://arxiv.org/abs/...), or DOI (10.x/y)."
        ),
    )
    mode.add_argument(
        "--pdf",
        help=(
            "Path to a local PDF or a directory of PDFs. Each file is "
            "scanned with a heuristic metadata extractor (title / authors / "
            "year / DOI / arXiv ID / real abstract anchored on the "
            "Abstract header) and copied into {out}/pdfs/. The "
            "--title / --authors / --year / --venue / --doi / --arxiv-id "
            "flags only override when exactly one PDF is passed — in batch "
            "mode they are ignored so per-file extraction wins. Use "
            "--enrich to upgrade each to a rich thesis-style deck via "
            "Anthropic; otherwise lightweight decks are produced and you "
            "can fill in a PaperSummary via scripts/regen_*.py."
        ),
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Override the paper title (used with --pdf when the PDF "
        "filename / first-page heuristic isn't right).",
    )
    parser.add_argument(
        "--authors",
        default=None,
        help="Comma-separated author list (used with --pdf).",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Publication year (used with --pdf).",
    )
    parser.add_argument(
        "--venue",
        default=None,
        help="Venue / journal / conference name (used with --pdf).",
    )
    parser.add_argument(
        "--doi",
        default=None,
        help="DOI (used with --pdf).",
    )
    parser.add_argument(
        "--arxiv-id",
        default=None,
        help="arXiv ID (used with --pdf).",
    )
    parser.add_argument(
        "--source",
        "-s",
        default=",".join(DEFAULT_SOURCES),
        help=(
            f"Comma-separated source list (used with --query). "
            f"Available: {', '.join(ALL_SOURCES)}. "
            f"Default: {','.join(DEFAULT_SOURCES)} "
            "(opt-in plugins like ieee/scholar only contribute when their "
            "env var is set; otherwise they are skipped silently)."
        ),
    )
    parser.add_argument(
        "--max",
        "-n",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help=f"Max results per source (1..{MAX_RESULTS_PER_SOURCE}). Default: {DEFAULT_PAGE_SIZE}.",
    )
    parser.add_argument(
        "--year-from",
        type=int,
        default=None,
        help="Earliest publication year (inclusive).",
    )
    parser.add_argument(
        "--year-to",
        type=int,
        default=None,
        help="Latest publication year (inclusive).",
    )
    parser.add_argument(
        "--export",
        "-e",
        default=None,
        help=(
            f"Comma-separated export formats. Available: {', '.join(ALL_EXPORTS)}. "
            f"Default with --query: {','.join(_DEFAULT_EXPORTS_SEARCH)}. "
            f"Default with --paper: {','.join(_DEFAULT_EXPORTS_SINGLE)}."
        ),
    )
    parser.add_argument(
        "--out",
        "-o",
        default=_DEFAULT_OUT_DIR,
        help=f"Output directory. Default: {_DEFAULT_OUT_DIR}.",
    )
    parser.add_argument(
        "--filename-stem",
        default=None,
        help="Override the generated filename stem (excludes extension).",
    )
    parser.add_argument(
        "--no-abstract",
        action="store_true",
        help="Omit abstracts from exports (titles/authors/links only).",
    )
    parser.add_argument(
        "--lang",
        "-l",
        default=DEFAULT_LANGUAGE,
        choices=SUPPORTED_LANGUAGES,
        help=(
            f"Slide deck language for template strings and (when --enrich is on) "
            f"LLM-generated bullets. Default: {DEFAULT_LANGUAGE}."
        ),
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        help=(
            "Explicitly enable PDF + Claude enrichment. Errors out when "
            "ANTHROPIC_API_KEY is unset. By default the CLI now auto-enriches "
            "when the env var is set, so you only need this flag when you "
            "want to fail-loud instead of fall-back-quietly. Requires "
            "`pip install autopapertoppt[intelligence]`."
        ),
    )
    parser.add_argument(
        "--lightweight",
        action="store_true",
        help=(
            "Force the lightweight (abstract-only) deck even when the "
            "environment has ANTHROPIC_API_KEY set. Skips Anthropic API "
            "calls entirely. Use this for fast, free runs."
        ),
    )
    parser.add_argument(
        "--max-slides",
        type=int,
        default=25,
        help=(
            "Cap each paper's deck at N slides (default 25). The "
            "exporter drops lower-priority sections (figures, "
            "paper-tables, contribution-summary, then pagination "
            "tails) until the count fits. Cover / overview / "
            "contributions / metrics / core observation / references "
            "are kept. Pass 0 to disable the cap and render the full "
            "rich-tier deck regardless of size."
        ),
    )
    parser.add_argument(
        "--llm-model",
        default=None,
        help=(
            "Override the Anthropic model used when --enrich is on. "
            "Default: claude-opus-4-7 (or AUTOPAPERTOPPT_LLM_MODEL)."
        ),
    )
    parser.add_argument(
        "--no-pdf",
        dest="download_pdf",
        action="store_false",
        help=(
            "Skip automatic PDF download. By default each paper's PDF "
            "(when a pdf_url is available) is saved under {out}/pdfs/. "
            "Disabling this also disables the per-paper PPT gate "
            "because no PDF means no full content."
        ),
    )
    parser.set_defaults(download_pdf=True)
    parser.add_argument(
        "--all-venues",
        dest="top_tier_only",
        action="store_false",
        help=(
            "Disable the top-tier CS venue filter. By default the search "
            "keeps only papers from arXiv or from a curated whitelist of "
            "top-tier conferences / journals (S&P, CCS, NDSS, USENIX "
            "Security, NeurIPS, ICML, ICSE, SIGMOD, SIGCOMM, CHI, etc.). "
            "Pass --all-venues to keep every result regardless of venue."
        ),
    )
    parser.set_defaults(top_tier_only=True)
    parser.add_argument(
        "--paywall-threshold",
        type=float,
        default=DEFAULT_PAYWALL_THRESHOLD,
        help=(
            "Fraction of papers without a public PDF URL that triggers a "
            "warning + confirmation prompt before slides are generated. "
            f"Default: {DEFAULT_PAYWALL_THRESHOLD:.2f} (warn when more "
            "than 30 percent of the result set is paywalled)."
        ),
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help=(
            "Skip the paywall confirmation prompt and proceed automatically. "
            "Useful for unattended runs."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-paper printout in stdout.",
    )
    return parser


def _parse_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _resolve_formats(args: argparse.Namespace) -> tuple[str, ...]:
    """Pick the export-format default appropriate for the mode.

    Why mode-specific defaults: a one-row Excel sheet for ``--paper`` or
    ``--pdf`` is busy work, so single-paper modes default to slides +
    BibTeX only. An explicit ``--export`` always wins.
    """
    if args.export is not None:
        return _parse_csv(args.export)
    if args.paper or args.pdf:
        return _DEFAULT_EXPORTS_SINGLE
    return _DEFAULT_EXPORTS_SEARCH


def _validate_sources(sources: tuple[str, ...]) -> None:
    invalid = [s for s in sources if s not in ALL_SOURCES]
    if invalid:
        raise SystemExit(
            f"Unknown source(s): {', '.join(invalid)}. "
            f"Available: {', '.join(ALL_SOURCES)}"
        )


def _validate_exports(formats: tuple[str, ...]) -> None:
    invalid = [f for f in formats if f not in ALL_EXPORTS]
    if invalid:
        raise SystemExit(
            f"Unknown export format(s): {', '.join(invalid)}. "
            f"Available: {', '.join(ALL_EXPORTS)}"
        )


def _print_results(collection, quiet: bool) -> None:
    if quiet:
        return
    print(f"\nFound {len(collection)} papers for: {collection.query.keywords}")
    for index, paper in enumerate(collection.papers, start=1):
        year = paper.year or "n.d."
        first_author = paper.authors[0] if paper.authors else "—"
        print(f"  [{index:>3}] ({year}) {first_author}: {paper.title}")


async def _run(args: argparse.Namespace) -> int:
    formats = _resolve_formats(args)
    _validate_exports(formats)
    options = ExportOptions(
        formats=formats,
        out_dir=args.out,
        filename_stem=args.filename_stem,
        include_abstract=not args.no_abstract,
        language=args.lang,
        max_slides_per_paper=args.max_slides,
    )
    needs_pptx = EXPORT_PPTX in formats
    # ``--pdf`` already supplies the PDF — the paywall gate is irrelevant
    # and download_pdfs would try to fetch a file:// URL through the
    # HTTPS-only transport and fail. Skip both for that mode.
    gate_pptx = needs_pptx and args.download_pdf and not args.pdf
    pdf_results = []
    try:
        collection = await _collect(args)
        collection = await _maybe_enrich(collection, args)
        if gate_pptx and collection.papers and not _confirm_paywall(
            collection, threshold=args.paywall_threshold, auto_yes=args.yes
        ):
            return 1
        if args.download_pdf and collection.papers and not args.pdf:
            pdf_results = await download_pdfs(collection, args.out)
    finally:
        await shutdown_clients()
    if not collection.papers:
        print("No results.", file=sys.stderr)
        return 1
    # ``--pdf`` batch mode (more than one PDF) routes through the per-paper
    # emit path so each PDF gets its own deck named after its bibtex_key.
    # We synthesise a saved PdfDownloadResult per paper because the PDF
    # was copied into ``{out}/pdfs/`` by ``_build_from_local_pdf`` already.
    if needs_pptx and args.pdf and len(collection.papers) > 1:
        pdf_results = _synthetic_pdf_results(collection, args.out)
        return _emit_per_paper(collection, options, pdf_results, args)
    if gate_pptx:
        return _emit_per_paper(collection, options, pdf_results, args)
    written = export_collection(collection, options)
    _print_results(collection, args.quiet)
    print("\nWrote:")
    for fmt, path in written.items():
        print(f"  - {fmt}: {Path(path).resolve()}")
    if args.download_pdf:
        _print_pdf_summary(pdf_results, args.quiet)
    return 0


def _confirm_paywall(
    collection: PaperCollection, *, threshold: float, auto_yes: bool
) -> bool:
    """Return True to continue, False to abort.

    Why a hard gate before any export work runs: producing a 30-slide deck
    where 80% of papers are paywalled is busy work — the user wanted to read
    the papers, not look at their abstracts. So we tell them up-front what
    fraction of the result set is actually retrievable.
    """
    total = len(collection.papers)
    if total == 0:
        return True
    inaccessible = sum(1 for p in collection.papers if not p.pdf_url)
    ratio = inaccessible / total
    if ratio <= threshold:
        return True
    accessible = total - inaccessible
    print(
        f"\nWarning: {inaccessible}/{total} papers ({ratio:.0%}) have no "
        f"public PDF URL and will be skipped — slides are only generated "
        f"for papers whose full PDF is downloadable.",
        file=sys.stderr,
    )
    if accessible == 0:
        print(
            "error: no paper in the result set exposes a PDF URL; nothing "
            "to generate. Try a different query or enable more sources.",
            file=sys.stderr,
        )
        return False
    if auto_yes:
        print(f"--yes set; continuing with {accessible} accessible paper(s).")
        return True
    prompt = (
        f"Continue and generate slides for the {accessible} accessible "
        f"paper(s)? [y/N]: "
    )
    try:
        response = input(prompt).strip().lower()
    except EOFError:
        return False
    return response in ("y", "yes")


def _synthetic_pdf_results(
    collection: PaperCollection, out_dir: str
) -> list:
    """Build a PdfDownloadResult per paper for the ``--pdf`` batch path.

    The PDFs are already in ``{out}/pdfs/`` (copied by
    ``_build_from_local_pdf``) so we just need ``PdfDownloadResult``
    placeholders pointing at them so ``_emit_per_paper`` treats every
    paper as accessible.
    """
    from autopapertoppt.core.pdf_download import PdfDownloadResult

    pdf_dir = Path(out_dir) / "pdfs"
    return [
        PdfDownloadResult(
            paper_key=paper.bibtex_key(),
            path=pdf_dir / f"{safe_filename(paper.title) or paper.source_id}.pdf",
            skipped_reason=None,
        )
        for paper in collection.papers
    ]


def _emit_per_paper(
    collection: PaperCollection,
    options: ExportOptions,
    pdf_results: list,
    args: argparse.Namespace,
) -> int:
    """Generate one PPT per paper that has a successfully downloaded PDF.

    Non-PPT formats (xlsx, bib, md, json) aggregate over the accessible
    subset so the bibliography file matches the slides on disk.
    """
    saved_by_key = {
        r.paper_key: r for r in pdf_results if r.path is not None
    }
    accessible_papers: list[Paper] = [
        p for p in collection.papers if p.bibtex_key() in saved_by_key
    ]
    if not accessible_papers:
        print(
            "error: no PDF could be downloaded; no slides were generated.",
            file=sys.stderr,
        )
        _print_pdf_summary(pdf_results, args.quiet)
        return 1

    accessible_collection = PaperCollection(
        query=collection.query, papers=tuple(accessible_papers)
    )

    aggregate_formats = tuple(f for f in options.formats if f != EXPORT_PPTX)
    written_aggregate: dict[str, Path] = {}
    if aggregate_formats:
        agg_options = dataclasses.replace(options, formats=aggregate_formats)
        written_aggregate = export_collection(accessible_collection, agg_options)

    per_paper_written: list[tuple[Paper, Path]] = []
    for paper in accessible_papers:
        single = PaperCollection(query=collection.query, papers=(paper,))
        per_options = dataclasses.replace(
            options,
            formats=(EXPORT_PPTX,),
            filename_stem=paper.bibtex_key(),
        )
        emitted = export_collection(single, per_options)
        per_paper_written.append((paper, emitted[EXPORT_PPTX]))

    _print_results(accessible_collection, args.quiet)
    if args.download_pdf:
        _print_pdf_summary(pdf_results, args.quiet)
    if not args.quiet:
        print(f"\nGenerated {len(per_paper_written)} per-paper PPT(s):")
        for paper, path in per_paper_written:
            print(f"  - {paper.bibtex_key()}: {Path(path).resolve()}")
        if written_aggregate:
            print("\nAggregate exports (accessible papers only):")
            for fmt, path in written_aggregate.items():
                print(f"  - {fmt}: {Path(path).resolve()}")
    return 0


def _print_pdf_summary(pdf_results, quiet: bool) -> None:
    if quiet or not pdf_results:
        return
    saved = [r for r in pdf_results if r.path is not None]
    skipped = [r for r in pdf_results if r.path is None]
    print(f"\nPDFs: {len(saved)} saved, {len(skipped)} skipped")
    for r in saved:
        print(f"  - {r.paper_key}: {r.path}")
    for r in skipped:
        print(f"  - {r.paper_key}: skipped ({r.skipped_reason})")


async def _collect(args: argparse.Namespace):
    if args.pdf:
        return _build_from_local_pdf(args)
    if args.paper:
        identifier = parse_identifier(args.paper)
        _LOG.info(
            "Fetching single paper: %s (%s)", identifier.value, identifier.kind.value
        )
        return await run_single_paper(identifier)
    keywords = normalize_query(args.query)
    sources = _parse_csv(args.source)
    _validate_sources(sources)
    query = Query(
        keywords=keywords,
        sources=sources,
        max_results=args.max,
        year_from=args.year_from,
        year_to=args.year_to,
        top_tier_only=args.top_tier_only,
    )
    _LOG.info("Running search: %s across %s", keywords, ", ".join(sources))
    return await run_search(query)


def _resolve_enrich_mode(args: argparse.Namespace) -> str:
    """Decide whether to enrich, and why. Returns one of:

    * ``"explicit"`` — user passed ``--enrich``; any failure surfaces.
    * ``"auto"`` — ``ANTHROPIC_API_KEY`` is set and ``--lightweight`` is not;
      enrichment runs, failures fall back to lightweight.
    * ``"skip-lightweight"`` — user passed ``--lightweight``; no API call,
      no notice (they asked for it).
    * ``"skip-no-key"`` — no API key, no ``--enrich``; lightweight with a
      one-line hint about how to upgrade.
    """
    import os as _os
    if args.enrich:
        return "explicit"
    if args.lightweight:
        return "skip-lightweight"
    if _os.environ.get("ANTHROPIC_API_KEY"):
        return "auto"
    return "skip-no-key"


async def _maybe_enrich(
    collection: PaperCollection, args: argparse.Namespace
) -> PaperCollection:
    """Resolve enrichment mode, print user-visible notices, dispatch."""
    enrich_mode = _resolve_enrich_mode(args)
    if enrich_mode == "skip-no-key" and not args.quiet:
        print(
            "Lightweight deck — no ANTHROPIC_API_KEY in env.\n"
            "If you (the human) want auto-enrichment, set the key and "
            "rerun.\n"
            "If you (an LLM agent) are running this, the lightweight "
            "deck is intermediate, NOT the deliverable: read each PDF "
            "in exports/<run>/pdfs/, hand-author a rich PaperSummary, "
            "drop a scripts/regen_<query>.py, run it. See AGENTS.md "
            "'LLM-as-agent default path' and "
            "scripts/regen_llm_security_batch.py for the worked example.",
            file=sys.stderr,
        )
    if enrich_mode not in {"explicit", "auto"} or not collection.papers:
        return collection
    print(
        f"Auto-enriching {len(collection)} paper(s) via Anthropic API "
        f"({args.llm_model or 'default model'}). "
        f"Pass --lightweight to skip.",
        file=sys.stderr,
    )
    try:
        return await _enrich_for_mode(collection, args)
    except ConfigError as err:
        if enrich_mode == "explicit":
            raise
        _LOG.warning(
            "auto-enrichment unavailable (%s); falling back to lightweight",
            err,
        )
        return collection


async def _enrich_for_mode(
    collection: PaperCollection, args: argparse.Namespace
) -> PaperCollection:
    """Dispatch enrichment between the network path and the local-PDF path.

    ``--pdf`` papers carry pre-extracted text in ``paper.raw`` and have
    ``pdf_url=None``, so they can't go through ``enrich_collection`` (which
    would try to fetch the URL via httpx). The local-PDF helper feeds the
    stashed text straight into ``summarise_paper`` instead.
    """
    if args.pdf:
        return await _enrich_local_pdf_collection(collection, args)
    return await enrich_collection(
        collection, language=args.lang, model=args.llm_model
    )


async def _enrich_local_pdf_collection(
    collection: PaperCollection, args: argparse.Namespace
) -> PaperCollection:
    try:
        from autopapertoppt.intelligence.pdf import ExtractedPdf
        from autopapertoppt.intelligence.summarise import summarise_paper
    except ImportError as err:
        raise ConfigError(
            "intelligence extras not installed; "
            "run `pip install autopapertoppt[intelligence]`"
        ) from err
    enriched: list[Paper] = []
    for paper in collection.papers:
        text = (paper.raw or {}).get("extracted_text") or ""
        if not text:
            enriched.append(paper)
            continue
        extracted = ExtractedPdf(
            url=paper.url,
            page_count=(paper.raw or {}).get("page_count") or 1,
            chars=len(text),
            text=text,
        )
        try:
            summary = await asyncio.to_thread(
                summarise_paper, paper, extracted,
                language=args.lang, model=args.llm_model,
            )
        except (AutoPaperToPPTError, Exception) as err:  # noqa: BLE001  # API client raises various
            _LOG.warning(
                "local PDF summarisation failed for %s: %s",
                paper.bibtex_key(), err,
            )
            enriched.append(paper)
            continue
        if summary.is_empty():
            enriched.append(paper)
        else:
            enriched.append(dataclasses.replace(paper, summary=summary))
    return PaperCollection(query=collection.query, papers=tuple(enriched))


def _build_from_local_pdf(args: argparse.Namespace) -> PaperCollection:
    """Build a single-paper PaperCollection from a local PDF (or directory).

    ``args.pdf`` may point at one ``.pdf`` file or a directory of them.
    Each file is:

    1. validated (existence + ``%PDF`` magic) — encrypted / empty / huge
       files surface as a friendly :class:`AutoPaperToPPTError` instead of
       a pypdf stack trace;
    2. read once, with text extracted via ``intelligence.pdf._extract_text``
       (pypdf). The text feeds both the auto-extracted metadata heuristic
       and the ``--enrich`` summariser;
    3. parsed with :func:`extract_metadata` so missing CLI overrides
       (``--title`` / ``--authors`` / ``--year`` / ``--doi`` / ``--arxiv-id``)
       fall back to values pulled directly from the PDF's front matter and
       the abstract anchors on an explicit ``Abstract`` / ``ABSTRACT`` /
       ``摘要`` header instead of an arbitrary first-1500-chars prefix;
    4. copied into ``{out}/pdfs/`` (skipped when the source path is already
       inside that directory).

    Returns a ``PaperCollection`` with one ``Paper`` per PDF.
    """
    pdf_paths = _resolve_pdf_inputs(args.pdf)
    if not pdf_paths:
        raise AutoPaperToPPTError(f"--pdf found no PDFs at {args.pdf!r}")
    out_root = ensure_export_dir(args.out)
    pdf_dir = ensure_export_dir(out_root / "pdfs")
    overrides_apply_to_all = len(pdf_paths) == 1
    papers = tuple(
        _build_one_local_paper(path, args, pdf_dir, overrides_apply_to_all)
        for path in pdf_paths
    )
    keywords = papers[0].title if len(papers) == 1 else f"{len(papers)} local PDFs"
    query = Query(
        keywords=keywords,
        sources=("local",),
        max_results=max(len(papers), 1),
    )
    return PaperCollection(query=query, papers=papers)


def _resolve_pdf_inputs(raw: str) -> list[Path]:
    """Expand ``--pdf`` to a sorted list of ``.pdf`` files.

    A directory is walked one level deep; a file is returned as-is.
    """
    root = Path(raw).expanduser().resolve()
    if root.is_dir():
        return sorted(p for p in root.glob("*.pdf") if p.is_file())
    if root.is_file():
        return [root]
    raise AutoPaperToPPTError(f"--pdf path does not exist: {root}")


_MAX_LOCAL_PDF_BYTES: Final[int] = 100 * 1024 * 1024  # 100 MB safety bound


def _build_one_local_paper(
    pdf_path: Path,
    args: argparse.Namespace,
    pdf_dir: Path,
    overrides_apply: bool,
) -> Paper:
    """Read, parse, and stage one local PDF; return the resulting Paper.

    ``overrides_apply`` is True only when exactly one PDF was passed —
    in batch mode the per-PDF flag set would shadow real per-file
    metadata, so we ignore the overrides and rely on the extractor.
    """
    import hashlib
    import shutil

    body = _read_pdf_safely(pdf_path)
    from autopapertoppt.intelligence.pdf import _extract_text
    from autopapertoppt.intelligence.pdf_metadata import extract_metadata

    extracted, page_count = _extract_text(body, source="local")
    metadata = extract_metadata(extracted)
    title = _pick(
        args.title if overrides_apply else None,
        metadata.title,
        pdf_path.stem.replace("_", " ").replace("-", " ").strip(),
    )
    authors = _resolve_authors(
        args.authors if overrides_apply else None,
        metadata.authors,
    )
    year = _pick(args.year if overrides_apply else None, metadata.year, None)
    venue = _pick(args.venue if overrides_apply else None, None, None)
    doi = _pick(args.doi if overrides_apply else None, metadata.doi, None)
    arxiv_id = _pick(
        args.arxiv_id if overrides_apply else None, metadata.arxiv_id, None
    )
    abstract = metadata.abstract or " ".join(extracted.split())[:1500]
    digest = hashlib.sha256(body, usedforsecurity=False).hexdigest()[:16]
    target = pdf_dir / f"{safe_filename(title) or digest}.pdf"
    if pdf_path.resolve() != target.resolve():
        shutil.copyfile(pdf_path, target)
    _LOG.info(
        "Local PDF: %s (%d bytes, %d chars, %d pages) -> %s",
        pdf_path.name, len(body), len(extracted), page_count, target,
    )
    return Paper(
        source="local",
        source_id=digest,
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        abstract=abstract,
        url=f"file:///{pdf_path.as_posix().lstrip('/')}",
        doi=doi,
        arxiv_id=arxiv_id,
        pdf_url=None,
        raw={"extracted_text": extracted, "page_count": page_count},
    )


def _read_pdf_safely(pdf_path: Path) -> bytes:
    """Read a PDF off disk with size cap + magic check, raising friendly errors."""
    try:
        size = pdf_path.stat().st_size
    except OSError as err:
        raise AutoPaperToPPTError(
            f"--pdf could not stat {pdf_path}: {err}"
        ) from err
    if size == 0:
        raise AutoPaperToPPTError(f"--pdf file is empty: {pdf_path}")
    if size > _MAX_LOCAL_PDF_BYTES:
        raise AutoPaperToPPTError(
            f"--pdf file exceeds {_MAX_LOCAL_PDF_BYTES // (1024 * 1024)} MB safety cap: "
            f"{pdf_path} ({size} bytes)"
        )
    body = pdf_path.read_bytes()
    if not body.startswith(b"%PDF"):
        raise AutoPaperToPPTError(
            f"--pdf is not a PDF file (no %PDF magic): {pdf_path}"
        )
    if b"/Encrypt" in body[:4096]:
        raise AutoPaperToPPTError(
            f"--pdf is encrypted; decrypt it first (qpdf / pdftk): {pdf_path}"
        )
    return body


def _pick(*candidates):
    """Return the first non-empty candidate (or None)."""
    for c in candidates:
        if c not in (None, "", ()):
            return c
    return None


def _resolve_authors(
    override: str | None, extracted: tuple[str, ...]
) -> tuple[str, ...]:
    if override:
        return tuple(a.strip() for a in override.split(",") if a.strip())
    return extracted


def _configure_stdio_for_unicode() -> None:
    """Force stdout/stderr to UTF-8 with replacement.

    Why: on Windows the default console codepage (cp950 / cp1252) cannot
    encode many paper titles and author names returned by international
    sources, and a UnicodeEncodeError surfaces as ``error: ...`` and
    masks the real exports. Replacement is acceptable here — these
    streams are diagnostic, not data.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(OSError, ValueError):
                reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _configure_stdio_for_unicode()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return asyncio.run(_run(args))
    except AutoPaperToPPTError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
