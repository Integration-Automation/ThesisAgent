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


def export_collection(
    collection: PaperCollection, options: ExportOptions
) -> dict[str, Path]:
    """Run every requested exporter; return {format: output path}.

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
    written: dict[str, Path] = {}
    for fmt in options.formats:
        exporter_cls = _REGISTRY.get(fmt)
        if exporter_cls is None:
            raise ExportError(fmt, "no exporter registered for this format")
        exporter = exporter_cls()
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
