"""Exporter Strategy implementations and the dispatch registry."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from autopapertoppt.core.constants import (
    EXPORT_BIBTEX,
    EXPORT_JSON,
    EXPORT_MARKDOWN,
    EXPORT_PPTX,
    EXPORT_XLSX,
)
from autopapertoppt.core.exceptions import ExportError
from autopapertoppt.core.models import ExportOptions, PaperCollection
from autopapertoppt.exporters.base import Exporter
from autopapertoppt.exporters.bibtex import BibtexExporter
from autopapertoppt.exporters.json_export import JsonExporter
from autopapertoppt.exporters.markdown import MarkdownExporter
from autopapertoppt.exporters.pptx import PptxExporter
from autopapertoppt.exporters.xlsx import XlsxExporter

_REGISTRY: Mapping[str, type[Exporter]] = {
    EXPORT_BIBTEX: BibtexExporter,
    EXPORT_MARKDOWN: MarkdownExporter,
    EXPORT_PPTX: PptxExporter,
    EXPORT_XLSX: XlsxExporter,
    EXPORT_JSON: JsonExporter,
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
    "Exporter",
    "JsonExporter",
    "MarkdownExporter",
    "PptxExporter",
    "XlsxExporter",
    "export_collection",
]
