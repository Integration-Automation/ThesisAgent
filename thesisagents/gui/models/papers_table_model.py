"""``QAbstractTableModel`` exposing a ``PaperCollection`` to a ``QTableView``."""

from __future__ import annotations

from typing import Final

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from thesisagents.core.diagnostics import PruningAction, SearchDiagnostics
from thesisagents.core.models import Paper, PaperCollection
from thesisagents.gui.i18n import t

_COLUMN_KEYS: Final[tuple[str, ...]] = (
    "results.col_title",
    "results.col_authors",
    "results.col_year",
    "results.col_source",
    "results.col_doi",
    "results.col_citations",
    "results.col_suggestion",
)
_SUGGESTION_COLUMN: Final[int] = _COLUMN_KEYS.index("results.col_suggestion")
_SUGGESTION_KEYS: Final[dict[PruningAction, str]] = {
    PruningAction.KEEP: "results.suggestion_keep",
    PruningAction.REVIEW: "results.suggestion_review",
    PruningAction.PRUNE: "results.suggestion_prune",
}
_NO_VALUE: Final[str] = "—"


class PapersTableModel(QAbstractTableModel):
    """Read-only view of ``PaperCollection.papers``.

    The model holds a tuple, not a list, mirroring the dataclass'
    immutability — to "update" the model the caller assigns a new
    collection via :meth:`set_collection`, which fires a layout reset
    so the table redraws.

    The last column shows the advisory pruning recommendation the search
    recorded for each paper (keep / review / prune), and hovering any cell of a
    row shows why: the score breakdown and the rule that triggered the advice.
    A collection without diagnostics (one loaded from elsewhere than a search)
    shows a dash there and no tooltip.
    """

    def __init__(self, language: str = "en", parent=None) -> None:
        super().__init__(parent)
        self._papers: tuple[Paper, ...] = ()
        self._diagnostics: SearchDiagnostics | None = None
        self._language = language

    def set_collection(self, collection: PaperCollection | None) -> None:
        self.beginResetModel()
        self._papers = tuple(collection.papers) if collection else ()
        self._diagnostics = collection.diagnostics if collection else None
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
        if not index.isValid() or not (0 <= index.row() < len(self._papers)):
            return None
        paper = self._papers[index.row()]
        if role == Qt.ToolTipRole:
            return self._explanation(paper)
        if role != Qt.DisplayRole:
            return None
        return self._display(paper, index.column())

    def _display(self, paper: Paper, column: int) -> object:
        if column == _SUGGESTION_COLUMN:
            return self._suggestion(paper)
        values: tuple[object, ...] = (
            paper.title,
            ", ".join(paper.authors[:3]) + (", …" if len(paper.authors) > 3 else ""),
            paper.year if paper.year is not None else _NO_VALUE,
            paper.source,
            paper.doi or _NO_VALUE,
            paper.citation_count if paper.citation_count is not None else _NO_VALUE,
        )
        return values[column] if 0 <= column < len(values) else None

    def _suggestion(self, paper: Paper) -> str:
        """Localised keep / review / prune label, or a dash when none was recorded."""
        if self._diagnostics is None:
            return _NO_VALUE
        advice = self._diagnostics.recommendation_for(paper.dedup_key())
        if advice is None:
            return _NO_VALUE
        return t(_SUGGESTION_KEYS[advice.action], self._language)

    def _explanation(self, paper: Paper) -> str | None:
        """Tooltip text: the score split, its reasons, then the advice's reasons.

        The sentences come from ``ranking.py`` / ``pruning.py`` and are English
        only, like the CLI's ``--diagnostics`` output: they quote query terms
        and thresholds, which would not survive a table of translations.
        """
        if self._diagnostics is None:
            return None
        key = paper.dedup_key()
        score = self._diagnostics.score_for(key)
        advice = self._diagnostics.recommendation_for(key)
        if score is None:
            return None
        lines = [
            f"total {score.total:.2f} = relevance {score.relevance:.2f} "
            f"+ recency {score.recency:.2f} + citations {score.citation:.2f}",
            *(f"• {reason}" for reason in score.reasons),
        ]
        if advice is not None:
            lines.append(f"→ {advice.action.value}")
            lines.extend(f"• {reason}" for reason in advice.reasons)
        return "\n".join(lines)
