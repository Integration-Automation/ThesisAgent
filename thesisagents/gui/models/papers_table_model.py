"""``QAbstractTableModel`` exposing a ``PaperCollection`` to a ``QTableView``."""

from __future__ import annotations

from typing import Final

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from thesisagents.core.models import Paper, PaperCollection
from thesisagents.gui.i18n import t

_COLUMN_KEYS: Final[tuple[str, ...]] = (
    "results.col_title",
    "results.col_authors",
    "results.col_year",
    "results.col_source",
    "results.col_doi",
    "results.col_citations",
)


class PapersTableModel(QAbstractTableModel):
    """Read-only view of ``PaperCollection.papers``.

    The model holds a tuple, not a list, mirroring the dataclass'
    immutability — to "update" the model the caller assigns a new
    collection via :meth:`set_collection`, which fires a layout reset
    so the table redraws.
    """

    def __init__(self, language: str = "en", parent=None) -> None:
        super().__init__(parent)
        self._papers: tuple[Paper, ...] = ()
        self._language = language

    def set_collection(self, collection: PaperCollection | None) -> None:
        self.beginResetModel()
        self._papers = tuple(collection.papers) if collection else ()
        self.endResetModel()

    def set_language(self, language: str) -> None:
        self._language = language
        # Force header redraw with the new language.
        self.headerDataChanged.emit(
            Qt.Horizontal, 0, self.columnCount() - 1
        )

    def papers(self) -> tuple[Paper, ...]:
        return self._papers

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802, B008  # Qt override
        if parent.isValid():
            return 0
        return len(self._papers)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802, B008  # Qt override
        if parent.isValid():
            return 0
        return len(_COLUMN_KEYS)

    def headerData(  # noqa: N802  # Qt override
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.DisplayRole,
    ) -> object:
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        if 0 <= section < len(_COLUMN_KEYS):
            return t(_COLUMN_KEYS[section], self._language)
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> object:
        if role != Qt.DisplayRole or not index.isValid():
            return None
        if not (0 <= index.row() < len(self._papers)):
            return None
        paper = self._papers[index.row()]
        column = index.column()
        if column == 0:
            return paper.title
        if column == 1:
            return ", ".join(paper.authors[:3]) + (
                ", …" if len(paper.authors) > 3 else ""
            )
        if column == 2:
            return paper.year if paper.year is not None else "—"
        if column == 3:
            return paper.source
        if column == 4:
            return paper.doi or "—"
        if column == 5:
            return paper.citation_count if paper.citation_count is not None else "—"
        return None
