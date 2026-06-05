"""RIS exporter — the reference-manager interchange format.

RIS (Research Information Systems) is the line-oriented citation format that
Zotero, Mendeley, EndNote and RefWorks import natively. It is the BibTeX
sibling for users who don't live in LaTeX. Each record is a block of
``TAG  - value`` lines (two spaces, a hyphen, a space — the column layout is
part of the spec) opened by a ``TY`` type tag and closed by a bare ``ER`` tag.

Example (one record)::

    TY  - JOUR
    TI  - Attention Is All You Need
    AU  - Ashish Vaswani
    AU  - Noam Shazeer
    PY  - 2017
    JO  - NeurIPS
    DO  - 10.5555/3295222.3295349
    UR  - https://arxiv.org/abs/1706.03762
    AB  - The dominant sequence transduction models ...
    ER  -

Anti-pattern this guards against: emitting a value that contains a raw newline.
RIS parsers split on line boundaries, so a newline inside ``AB`` silently
truncates the abstract (or worse, swallows the following record). Every value
therefore has its internal whitespace collapsed to single spaces before it is
written.
"""

from __future__ import annotations

from pathlib import Path

from thesisagents.core.constants import EXPORT_RIS
from thesisagents.core.exceptions import ExportError
from thesisagents.core.models import ExportOptions, Paper, PaperCollection
from thesisagents.exporters.base import Exporter

# RIS reference types (TY). We only need two: a journal/conference article when
# the paper carries a venue, and the generic catch-all otherwise (preprints,
# tech reports, datasets). Keeping the mapping tiny avoids guessing wrongly —
# "GEN" round-trips through every manager without a type-specific schema.
_TYPE_ARTICLE = "JOUR"
_TYPE_GENERIC = "GEN"


class RisExporter(Exporter):
    format = EXPORT_RIS
    extension = "ris"

    def export(self, collection: PaperCollection, options: ExportOptions) -> Path:
        try:
            content = self._render(collection, options)
        except Exception as err:
            raise ExportError(self.format, f"render failed: {err}") from err
        out_path = self.resolve_out_path(collection, options)
        out_path.write_text(content, encoding="utf-8")
        return out_path

    def _render(self, collection: PaperCollection, options: ExportOptions) -> str:
        records = [
            _render_record(paper, options.include_abstract)
            for paper in collection.papers
        ]
        # A trailing blank line after the final ER keeps strict parsers happy.
        return "\n".join(records) + "\n"


def _render_record(paper: Paper, include_abstract: bool) -> str:
    ty = _TYPE_ARTICLE if paper.venue else _TYPE_GENERIC
    lines: list[str] = [_tag("TY", ty)]
    lines.append(_tag("TI", _clean(paper.title)))
    for author in paper.authors:
        lines.append(_tag("AU", _clean(author)))
    if paper.year is not None:
        lines.append(_tag("PY", str(paper.year)))
    if paper.venue:
        # JO = full journal/source name; T2 = secondary title. JO is the most
        # widely understood across managers, so we use it for the venue.
        lines.append(_tag("JO", _clean(paper.venue)))
    if paper.doi:
        lines.append(_tag("DO", _clean(paper.doi)))
    if paper.url:
        lines.append(_tag("UR", _clean(paper.url)))
    if include_abstract and paper.abstract:
        lines.append(_tag("AB", _clean(paper.abstract)))
    lines.append("ER  - ")
    return "\n".join(lines) + "\n"


def _tag(tag: str, value: str) -> str:
    """One RIS line. The ``TAG  - `` prefix layout is mandated by the spec."""
    return f"{tag}  - {value}"


def _clean(value: str) -> str:
    """Collapse internal whitespace so no value spans more than one line."""
    return " ".join(value.split())
