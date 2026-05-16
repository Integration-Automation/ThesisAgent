"""Search + export tab.

End-to-end flow:

1. User fills query / sources / language / year range / max-results.
2. ``Search`` button kicks off :func:`autopapertoppt.core.pipeline.run_search`
   on a worker thread.
3. Results populate the table; status bar reports the count.
4. ``Export…`` opens a directory picker and runs ``export_collection``
   on another worker thread.

All worker callbacks land on the main thread because Qt signal/slot
across threads is queue-routed automatically.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from autopapertoppt.core.constants import DEFAULT_PAGE_SIZE, MAX_RESULTS_PER_SOURCE
from autopapertoppt.core.models import ExportOptions, PaperCollection, Query
from autopapertoppt.core.pipeline import run_search
from autopapertoppt.core.query import normalize_query
from autopapertoppt.exporters import export_collection
from autopapertoppt.exporters.i18n import SUPPORTED_LANGUAGES as DECK_LANGUAGES
from autopapertoppt.fetchers.http import shutdown_clients
from autopapertoppt.gui.i18n import t
from autopapertoppt.gui.models.papers_table_model import PapersTableModel
from autopapertoppt.gui.widgets.source_multiselect import SourceMultiselect
from autopapertoppt.gui.workers import AsyncWorker, BlockingWorker

_MIN_YEAR = 1900
_MAX_YEAR = 2100


class SearchPage(QWidget):
    """Search + export page."""

    def __init__(self, ui_language: str = "en", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ui_language = ui_language
        self._collection: PaperCollection | None = None
        self._papers_model = PapersTableModel(language=ui_language)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)

        form_box = QGroupBox(t("nav.search", self._ui_language), self)
        form = QFormLayout(form_box)

        self._query_input = QLineEdit(self)
        self._query_input.setPlaceholderText(
            t("search.query_placeholder", self._ui_language)
        )
        form.addRow(t("search.query_label", self._ui_language), self._query_input)

        self._sources_widget = SourceMultiselect(self)
        form.addRow(t("search.sources_label", self._ui_language), self._sources_widget)

        self._language_combo = QComboBox(self)
        for code in DECK_LANGUAGES:
            self._language_combo.addItem(code, code)
        form.addRow(
            t("search.language_label", self._ui_language), self._language_combo
        )

        self._max_spin = QSpinBox(self)
        self._max_spin.setRange(1, MAX_RESULTS_PER_SOURCE)
        self._max_spin.setValue(DEFAULT_PAGE_SIZE)
        form.addRow(
            t("search.max_results_label", self._ui_language), self._max_spin
        )

        year_row = QWidget(self)
        year_layout = QHBoxLayout(year_row)
        year_layout.setContentsMargins(0, 0, 0, 0)
        self._year_from_spin = self._year_spin()
        self._year_to_spin = self._year_spin()
        year_layout.addWidget(
            QLabel(t("search.year_from", self._ui_language))
        )
        year_layout.addWidget(self._year_from_spin)
        year_layout.addWidget(QLabel(t("search.year_to", self._ui_language)))
        year_layout.addWidget(self._year_to_spin)
        year_layout.addStretch(1)
        form.addRow(year_row)

        self._top_tier_check = QCheckBox(
            t("search.top_tier_only", self._ui_language), self
        )
        self._top_tier_check.setChecked(True)
        form.addRow(self._top_tier_check)

        button_row = QHBoxLayout()
        self._search_button = QPushButton(
            t("search.search_button", self._ui_language), self
        )
        self._search_button.clicked.connect(self._on_search_clicked)
        self._export_button = QPushButton(
            t("search.export_button", self._ui_language), self
        )
        self._export_button.setEnabled(False)
        self._export_button.clicked.connect(self._on_export_clicked)
        button_row.addWidget(self._search_button)
        button_row.addWidget(self._export_button)
        button_row.addStretch(1)
        form.addRow(button_row)

        outer.addWidget(form_box)

        self._table = QTableView(self)
        self._table.setModel(self._papers_model)
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setSectionResizeMode(
            self._table.horizontalHeader().ResizeMode.Stretch
        )
        outer.addWidget(self._table, stretch=1)

        self._status_label = QLabel(t("search.status_idle", self._ui_language), self)
        self._status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        outer.addWidget(self._status_label)

    def _year_spin(self) -> QSpinBox:
        spin = QSpinBox(self)
        spin.setRange(_MIN_YEAR - 1, _MAX_YEAR)
        spin.setSpecialValueText("—")
        spin.setValue(_MIN_YEAR - 1)
        return spin

    def _year(self, spin: QSpinBox) -> int | None:
        value = spin.value()
        return value if value >= _MIN_YEAR else None

    def _on_search_clicked(self) -> None:
        keywords = self._query_input.text().strip()
        if not keywords:
            self._set_status(t("search.error_empty_query", self._ui_language))
            return
        sources = self._sources_widget.selected()
        if not sources:
            self._set_status(t("search.error_empty_query", self._ui_language))
            return
        normalised = normalize_query(keywords)
        query = Query(
            keywords=normalised,
            sources=sources,
            max_results=self._max_spin.value(),
            year_from=self._year(self._year_from_spin),
            year_to=self._year(self._year_to_spin),
            top_tier_only=self._top_tier_check.isChecked(),
        )
        self._search_button.setEnabled(False)
        self._export_button.setEnabled(False)
        self._set_status(t("search.status_running", self._ui_language))

        async def coro() -> PaperCollection:
            try:
                return await run_search(query)
            finally:
                await shutdown_clients()

        worker = AsyncWorker(coro)
        worker.signals.finished.connect(self._on_search_finished)
        worker.signals.failed.connect(self._on_worker_failed)
        QThreadPool.globalInstance().start(worker)

    def _on_search_finished(self, collection: object) -> None:
        if not isinstance(collection, PaperCollection):  # pragma: no cover — defensive
            self._on_worker_failed(
                RuntimeError(f"unexpected worker result type: {type(collection)!r}")
            )
            return
        self._collection = collection
        self._papers_model.set_collection(collection)
        self._search_button.setEnabled(True)
        self._export_button.setEnabled(bool(collection.papers))
        self._set_status(
            t(
                "search.status_done",
                self._ui_language,
                count=len(collection.papers),
            )
        )

    def _on_worker_failed(self, err: object) -> None:
        self._search_button.setEnabled(True)
        self._export_button.setEnabled(bool(self._collection and self._collection.papers))
        self._set_status(
            t("search.error_generic", self._ui_language, error=str(err))
        )

    def _on_export_clicked(self) -> None:
        if self._collection is None or not self._collection.papers:
            self._set_status(t("search.error_no_results", self._ui_language))
            return
        directory = QFileDialog.getExistingDirectory(
            self,
            t("search.export_dialog_title", self._ui_language),
            str(Path.cwd() / "exports"),
        )
        if not directory:
            return
        language = self._language_combo.currentData() or "en"
        options = ExportOptions(
            formats=("pptx", "xlsx", "bibtex"),
            out_dir=directory,
            language=language,
        )
        collection = self._collection
        self._export_button.setEnabled(False)
        self._set_status(t("search.status_export_running", self._ui_language))

        def export_call() -> dict[str, Path]:
            return export_collection(collection, options)

        worker = BlockingWorker(export_call)
        worker.signals.finished.connect(self._on_export_finished)
        worker.signals.failed.connect(self._on_worker_failed)
        QThreadPool.globalInstance().start(worker)

    def _on_export_finished(self, written: object) -> None:
        self._export_button.setEnabled(True)
        if not isinstance(written, dict) or not written:
            self._set_status(t("search.error_no_results", self._ui_language))
            return
        any_path = next(iter(written.values()))
        self._set_status(
            t("search.status_export_done", self._ui_language, path=str(any_path))
        )

    def _set_status(self, text: str) -> None:
        self._status_label.setText(text)

    # --- accessors used by tests ----------------------------------------

    def papers_model(self) -> PapersTableModel:
        return self._papers_model

    def status_text(self) -> str:
        return self._status_label.text()

    def set_query_text(self, text: str) -> None:
        self._query_input.setText(text)
