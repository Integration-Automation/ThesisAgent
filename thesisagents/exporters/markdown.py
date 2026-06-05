"""Markdown summary exporter. Contains every paper's source, title, and abstract."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from thesisagents.core.constants import EXPORT_MARKDOWN
from thesisagents.core.exceptions import ExportError
from thesisagents.core.models import ExportOptions, Paper, PaperCollection
from thesisagents.exporters.base import Exporter


class MarkdownExporter(Exporter):
    format = EXPORT_MARKDOWN
    extension = "md"

    def export(self, collection: PaperCollection, options: ExportOptions) -> Path:
        try:
            content = self._render(collection, options)
        except Exception as err:
            raise ExportError(self.format, f"render failed: {err}") from err
        out_path = self.resolve_out_path(collection, options)
        out_path.write_text(content, encoding="utf-8")
        return out_path

    def _render(
        self, collection: PaperCollection, options: ExportOptions
    ) -> str:
        lines: list[str] = []
        lines.append(f"# Paper search: `{collection.query.keywords}`")
        lines.append("")
        lines.append(_render_metadata(collection))
        lines.append("")
        lines.append(f"**{len(collection)} papers** after de-duplication and ranking.")
        lines.append("")
        lines.append("## Results")
        lines.append("")
        for index, paper in enumerate(collection.papers, start=1):
            lines.extend(_render_paper(index, paper, options.include_abstract))
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


def _render_metadata(collection: PaperCollection) -> str:
    query = collection.query
    return (
        f"- **Sources**: {', '.join(query.sources)}\n"
        f"- **Max per source**: {query.max_results}\n"
        f"- **Year range**: "
        f"{query.year_from or '—'} – {query.year_to or '—'}\n"
        f"- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )


def _render_paper(index: int, paper: Paper, include_abstract: bool) -> list[str]:
    authors_line = ", ".join(paper.authors) if paper.authors else "—"
    year_part = str(paper.year) if paper.year else "n.d."
    venue_part = f" · *{paper.venue}*" if paper.venue else ""
    identifier_bits: list[str] = []
    if paper.doi:
        identifier_bits.append(f"DOI [{paper.doi}](https://doi.org/{paper.doi})")
    if paper.arxiv_id:
        identifier_bits.append(f"arXiv `{paper.arxiv_id}`")
    identifier_line = " · ".join(identifier_bits)
    block: list[str] = [
        f"### {index}. {paper.title}",
        "",
        f"- **Authors**: {authors_line}",
        f"- **Year**: {year_part}{venue_part}",
        f"- **Indexed via**: `{paper.source}` — [{paper.url}]({paper.url})",
    ]
    if identifier_line:
        block.append(f"- **IDs**: {identifier_line}")
    if include_abstract and paper.abstract:
        block.append("")
        block.append("**Abstract**")
        block.append("")
        block.append(paper.short_abstract())
    return block
