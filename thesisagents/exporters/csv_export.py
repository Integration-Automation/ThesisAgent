"""CSV exporter — a flat, one-row-per-paper table.

The ``.xlsx`` exporter produces a styled workbook; this CSV exporter is its
plain-text counterpart for quick triage: it opens in any spreadsheet, greps
cleanly on the command line, and diffs row-by-row in version control. One
header row, then one row per paper, in ranked order.

The author list is joined with ``"; "`` into a single cell so the column count
stays fixed regardless of how many authors a paper has — a ragged row count
would break naive CSV consumers. The module uses :mod:`csv` (not manual string
joins) so embedded commas, quotes and newlines in titles/abstracts are quoted
per RFC 4180 instead of corrupting the column layout.

Anti-pattern this guards against: building rows with ``",".join(...)`` by hand.
A single paper title containing a comma (``"Attention, Revisited"``) would shift
every following column. ``csv.writer`` quotes such fields automatically.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from thesisagents.core.constants import EXPORT_CSV
from thesisagents.core.exceptions import ExportError
from thesisagents.core.models import ExportOptions, Paper, PaperCollection
from thesisagents.exporters.base import Exporter

# Stable column schema. Kept fixed (abstract column always present, blank when
# the caller opts out) so downstream scripts can rely on header positions.
_HEADER = (
    "rank",
    "title",
    "authors",
    "year",
    "venue",
    "source",
    "doi",
    "arxiv_id",
    "citation_count",
    "url",
    "pdf_url",
    "abstract",
)


class CsvExporter(Exporter):
    format = EXPORT_CSV
    extension = "csv"

    def export(self, collection: PaperCollection, options: ExportOptions) -> Path:
        try:
            content = self._render(collection, options)
        except Exception as err:
            raise ExportError(self.format, f"render failed: {err}") from err
        out_path = self.resolve_out_path(collection, options)
        # newline="" is the documented contract for the csv module so it owns
        # line terminators; without it Windows doubles every CR.
        out_path.write_text(content, encoding="utf-8", newline="")
        return out_path

    def _render(self, collection: PaperCollection, options: ExportOptions) -> str:
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        writer.writerow(_HEADER)
        for rank, paper in enumerate(collection.papers, start=1):
            writer.writerow(_row(rank, paper, options.include_abstract))
        return buffer.getvalue()


def _row(rank: int, paper: Paper, include_abstract: bool) -> list[str]:
    abstract = paper.short_abstract() if (include_abstract and paper.abstract) else ""
    return [
        str(rank),
        paper.title,
        "; ".join(paper.authors),
        str(paper.year) if paper.year is not None else "",
        paper.venue or "",
        paper.source,
        paper.doi or "",
        paper.arxiv_id or "",
        str(paper.citation_count) if paper.citation_count is not None else "",
        paper.url,
        paper.pdf_url or "",
        abstract,
    ]
