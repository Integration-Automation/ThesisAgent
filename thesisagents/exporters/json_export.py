"""JSON exporter: dumps the full PaperCollection as structured data."""

from __future__ import annotations

import json
from pathlib import Path

from thesisagents.core.constants import EXPORT_JSON
from thesisagents.core.exceptions import ExportError
from thesisagents.core.models import ExportOptions, PaperCollection
from thesisagents.exporters.base import Exporter


class JsonExporter(Exporter):
    format = EXPORT_JSON
    extension = "json"

    def export(self, collection: PaperCollection, options: ExportOptions) -> Path:
        try:
            payload = {
                "query": {
                    "keywords": collection.query.keywords,
                    "sources": list(collection.query.sources),
                    "max_results": collection.query.max_results,
                    "year_from": collection.query.year_from,
                    "year_to": collection.query.year_to,
                },
                "papers": [paper.to_dict() for paper in collection.papers],
            }
            content = json.dumps(payload, ensure_ascii=False, indent=2)
        except Exception as err:
            raise ExportError(self.format, f"render failed: {err}") from err
        out_path = self.resolve_out_path(collection, options)
        out_path.write_text(content, encoding="utf-8")
        return out_path
