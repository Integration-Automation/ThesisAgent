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
    """Run every requested exporter; return {format: output path}."""
    written: dict[str, Path] = {}
    for fmt in options.formats:
        exporter_cls = _REGISTRY.get(fmt)
        if exporter_cls is None:
            raise ExportError(fmt, "no exporter registered for this format")
        exporter = exporter_cls()
        path = exporter.export(collection, options)
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
