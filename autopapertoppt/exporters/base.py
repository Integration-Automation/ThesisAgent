"""Exporter Strategy interface plus shared filename helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from autopapertoppt.core.models import ExportOptions, PaperCollection
from autopapertoppt.utils.path_safety import ensure_export_dir, safe_filename


class Exporter(ABC):
    """One concrete subclass per output format."""

    format: str
    extension: str

    @abstractmethod
    def export(self, collection: PaperCollection, options: ExportOptions) -> Path:
        """Render `collection` to disk; return the path to the written artefact."""

    def resolve_out_path(
        self, collection: PaperCollection, options: ExportOptions
    ) -> Path:
        out_dir = ensure_export_dir(options.out_dir)
        stem = options.filename_stem or _default_stem(collection)
        return out_dir / f"{safe_filename(stem)}.{self.extension}"


def _default_stem(collection: PaperCollection) -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    keyword_part = collection.query.keywords[:32]
    return f"{keyword_part}-{timestamp}"
