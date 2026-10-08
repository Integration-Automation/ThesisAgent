"""Exporter Strategy implementations and the dispatch registry."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from thesisagents.core.constants import (
    EXPORT_BIBTEX,
    EXPORT_CSL,
    EXPORT_CSV,
    EXPORT_JSON,
    EXPORT_MARKDOWN,
    EXPORT_PPTX,
    EXPORT_RIS,
    EXPORT_XLSX,
)
from thesisagents.core.exceptions import ExportError
from thesisagents.core.export_validation import (
    IdentifierVerificationError,
    VerificationCache,
    verify_collection_blocking,
)
from thesisagents.core.models import ExportOptions, PaperCollection
from thesisagents.exporters.base import Exporter
from thesisagents.exporters.bibtex import BibtexExporter
from thesisagents.exporters.csljson import CslJsonExporter
from thesisagents.exporters.csv_export import CsvExporter
from thesisagents.exporters.json_export import JsonExporter
from thesisagents.exporters.markdown import MarkdownExporter
from thesisagents.exporters.pptx import PptxExporter
from thesisagents.exporters.ris import RisExporter
from thesisagents.exporters.xlsx import XlsxExporter
from thesisagents.utils.logging import get_logger

_REGISTRY: Mapping[str, type[Exporter]] = {
    EXPORT_BIBTEX: BibtexExporter,
    EXPORT_MARKDOWN: MarkdownExporter,
    EXPORT_PPTX: PptxExporter,
    EXPORT_XLSX: XlsxExporter,
    EXPORT_JSON: JsonExporter,
    EXPORT_RIS: RisExporter,
    EXPORT_CSV: CsvExporter,
    EXPORT_CSL: CslJsonExporter,
}


_LOG = get_logger(__name__)


def export_collection(
    collection: PaperCollection,
    options: ExportOptions,
    *,
    verification_cache: VerificationCache | None = None,
) -> dict[str, Path]:
    """Run every requested exporter; return {format: output path}.

    The identifier preflight runs first (see :func:`_preflight_identifiers`):
    unless ``options.verify_identifiers`` is False, a paper whose DOI or URL is
    wrong or unreachable raises ``IdentifierVerificationError`` before any
    file is written, so a failed run leaves no half-finished export behind.
    ``verification_cache`` lets a caller that exports the same papers more than
    once in one run (the CLI: aggregate formats, then one deck per paper) check
    each identifier only once.

    Every exporter already wraps its *render* step in an ``ExportError``, but
    each one then writes to disk outside that guard. The write is where the
    most common real-world failure lives: on Windows, re-running a search while
    the previous ``.xlsx`` / ``.pptx`` is still open in Excel or PowerPoint
    raises ``PermissionError: [WinError 32]``, which reached the CLI as a raw
    traceback because ``main()`` only translates ``ThesisAgentsError``. Wrapping
    ``OSError`` here — one place, every format, including any added later —
    turns that into ``error: [xlsx] could not write ...`` with the fix in the
    message.
    """
    for fmt in options.formats:
        if fmt not in _REGISTRY:
            raise ExportError(fmt, "no exporter registered for this format")
    _preflight_identifiers(collection, options, verification_cache)
    written: dict[str, Path] = {}
    for fmt in options.formats:
        exporter = _REGISTRY[fmt]()
        try:
            path = exporter.export(collection, options)
        except OSError as err:
            raise ExportError(
                fmt,
                f"could not write the output file ({err}). If the previous "
                f"export is still open in another application, close it and "
                f"re-run, or pass a different --out directory.",
            ) from err
        written[fmt] = path
    return written


def _preflight_identifiers(
    collection: PaperCollection,
    options: ExportOptions,
    cache: VerificationCache | None,
) -> None:
    """Stop the export when a paper's DOI or URL does not check out.

    The boundary this guards: the last point before a bibliography leaves the
    program. Failure mode it prevents: a hand-authored ``Paper`` whose DOI was
    typed from memory reaching a ``.bib`` file or a references slide.

    The opt-out is logged at WARNING so an unverified export is never silent.

    Example: a collection holding ``Paper(doi="10.1234/typo")`` raises
    ``IdentifierVerificationError`` whose ``report.failures`` names that paper
    and DOI. With ``ExportOptions(verify_identifiers=False)`` the same call
    exports and logs "identifier verification is OFF".
    """
    if not options.verify_identifiers:
        _LOG.warning(
            "identifier verification is OFF for this export "
            "(verify_identifiers=False): DOIs and URLs were not checked"
        )
        return
    report = verify_collection_blocking(collection, cache=cache)
    if not report.ok:
        raise IdentifierVerificationError(report)


__all__ = [
    "BibtexExporter",
    "CslJsonExporter",
    "CsvExporter",
    "Exporter",
    "JsonExporter",
    "MarkdownExporter",
    "PptxExporter",
    "RisExporter",
    "XlsxExporter",
    "export_collection",
]
