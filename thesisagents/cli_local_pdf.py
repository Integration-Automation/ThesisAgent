"""``--pdf`` mode: turn local PDF files into the papers of a run.

No search and no download happens in this mode. Each file is validated, read
once, and described by what its own front matter says (title, authors, year,
DOI, arXiv ID, abstract), with the ``--title`` / ``--authors`` / ... flags as
overrides. Kept out of ``cli.py`` so that module stays about the order of the
stages.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Final

from thesisagents.core.exceptions import ThesisAgentsError
from thesisagents.core.models import Paper, PaperCollection, Query
from thesisagents.utils.logging import get_logger
from thesisagents.utils.path_safety import ensure_export_dir, safe_filename

_LOG = get_logger(__name__)


def build_from_local_pdf(args: argparse.Namespace) -> PaperCollection:
    """Build a single-paper PaperCollection from a local PDF (or directory).

    ``args.pdf`` may point at one ``.pdf`` file or a directory of them.
    Each file is:

    1. validated (existence + ``%PDF`` magic) — encrypted / empty / huge
       files surface as a friendly :class:`ThesisAgentsError` instead of
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
        raise ThesisAgentsError(f"--pdf found no PDFs at {args.pdf!r}")
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
        max_results=Query.clamp_max_results(len(papers)),
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
    raise ThesisAgentsError(f"--pdf path does not exist: {root}")


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
    from thesisagents.intelligence.pdf import _extract_text
    from thesisagents.intelligence.pdf_metadata import extract_metadata

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
        raise ThesisAgentsError(
            f"--pdf could not stat {pdf_path}: {err}"
        ) from err
    if size == 0:
        raise ThesisAgentsError(f"--pdf file is empty: {pdf_path}")
    if size > _MAX_LOCAL_PDF_BYTES:
        raise ThesisAgentsError(
            f"--pdf file exceeds {_MAX_LOCAL_PDF_BYTES // (1024 * 1024)} MB safety cap: "
            f"{pdf_path} ({size} bytes)"
        )
    body = pdf_path.read_bytes()
    if not body.startswith(b"%PDF"):
        raise ThesisAgentsError(
            f"--pdf is not a PDF file (no %PDF magic): {pdf_path}"
        )
    if b"/Encrypt" in body[:4096]:
        raise ThesisAgentsError(
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
