"""Deck tab.

Granular export controls for a PaperCollection — supplements the Search
tab's one-button Export by exposing every ExportOptions knob:

* Output directory + filename stem
* Per-format checkboxes (pptx / xlsx / bib / md / json)
* Deck language (independent of UI language)
* Max-slides cap (per-paper)
* Include-abstract toggle

The page accepts either the raw collection from SearchPage or the
enriched one from EnrichPage. ``set_collection`` is the only entry
point — the page does not call the search pipeline itself.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool, QUrl
from PySide6.QtGui import QDesktopServices, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from autopapertoppt.core.models import ExportOptions, PaperCollection
from autopapertoppt.exporters import export_collection
from autopapertoppt.exporters.i18n import SUPPORTED_LANGUAGES as DECK_LANGUAGES
from autopapertoppt.gui.i18n import LANGUAGE_DISPLAY_NAMES, t
from autopapertoppt.gui.workers import BlockingWorker

# Match autopapertoppt.exporters.__init__.SUPPORTED_FORMATS ordering.
_FORMAT_CHOICES: tuple[tuple[str, str], ...] = (
    ("pptx", "deck.format_pptx"),
    ("xlsx", "deck.format_xlsx"),
    ("bib", "deck.format_bib"),
    ("md", "deck.format_md"),
    ("json", "deck.format_json"),
)
_DEFAULT_FORMATS: frozenset[str] = frozenset({"pptx", "xlsx", "bib"})
_DEFAULT_MAX_SLIDES = 25


class DeckPage(QWidget):
    """Granular export controls for the active collection."""

    def __init__(self, ui_language: str = "en", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ui_language = ui_language
        self._collection: PaperCollection | None = None
        self._collection_is_enriched: bool = False
        self._last_written_dir: Path | None = None
        self._files_model = QStandardItemModel(0, 2, self)
        self._files_model.setHorizontalHeaderLabels([
            t("deck.column_format", ui_language),
            t("deck.column_path", ui_language),
        ])
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)

        # Output dir + filename row
        output_box = QGroupBox(t("deck.output_group", self._ui_language), self)
        output_form = QFormLayout(output_box)

        dir_row = QWidget(self)
        dir_layout = QHBoxLayout(dir_row)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        self._out_dir_input = QLineEdit(self)
        self._out_dir_input.setText(str(Path.cwd() / "exports"))
        browse = QPushButton(t("deck.browse_button", self._ui_language), self)
        browse.clicked.connect(self._on_browse_out_dir)
        dir_layout.addWidget(self._out_dir_input, stretch=1)
        dir_layout.addWidget(browse)
        output_form.addRow(t("deck.out_dir_label", self._ui_language), dir_row)

        self._filename_stem_input = QLineEdit(self)
        self._filename_stem_input.setPlaceholderText(
            t("deck.filename_stem_placeholder", self._ui_language),
        )
        output_form.addRow(
            t("deck.filename_stem_label", self._ui_language),
            self._filename_stem_input,
        )

        self._language_combo = QComboBox(self)
        for code in DECK_LANGUAGES:
            display = LANGUAGE_DISPLAY_NAMES.get(code, code)
            self._language_combo.addItem(display, code)
        output_form.addRow(
            t("deck.language_label", self._ui_language), self._language_combo,
        )

        outer.addWidget(output_box)

        # Format checkboxes
        format_box = QGroupBox(t("deck.format_group", self._ui_language), self)
        format_row = QHBoxLayout(format_box)
        self._format_checks: dict[str, QCheckBox] = {}
        for fmt, label_key in _FORMAT_CHOICES:
            chk = QCheckBox(t(label_key, self._ui_language), self)
            chk.setChecked(fmt in _DEFAULT_FORMATS)
            format_row.addWidget(chk)
            self._format_checks[fmt] = chk
        format_row.addStretch(1)
        outer.addWidget(format_box)

        # Options
        options_box = QGroupBox(t("deck.options_group", self._ui_language), self)
        options_form = QFormLayout(options_box)
        self._max_slides_spin = QSpinBox(self)
        self._max_slides_spin.setRange(0, 200)
        self._max_slides_spin.setValue(_DEFAULT_MAX_SLIDES)
        self._max_slides_spin.setSpecialValueText(
            t("deck.unlimited", self._ui_language),
        )
        options_form.addRow(
            t("deck.max_slides_label", self._ui_language), self._max_slides_spin,
        )
        self._include_abstract_check = QCheckBox(
            t("deck.include_abstract_label", self._ui_language), self,
        )
        self._include_abstract_check.setChecked(True)
        options_form.addRow(self._include_abstract_check)
        # Default is DARK; this checkbox is the opt-OUT toggle for light.
        self._light_mode_check = QCheckBox(
            t("deck.light_mode_label", self._ui_language), self,
        )
        self._light_mode_check.setChecked(False)
        options_form.addRow(self._light_mode_check)
        outer.addWidget(options_box)

        # Action row
        button_row = QHBoxLayout()
        self._export_button = QPushButton(
            t("deck.export_button", self._ui_language), self,
        )
        self._export_button.setEnabled(False)
        self._export_button.clicked.connect(self._on_export_clicked)
        self._open_folder_button = QPushButton(
            t("deck.open_folder_button", self._ui_language), self,
        )
        self._open_folder_button.setEnabled(False)
        self._open_folder_button.clicked.connect(self._on_open_folder_clicked)
        button_row.addWidget(self._export_button)
        button_row.addWidget(self._open_folder_button)
        button_row.addStretch(1)
        outer.addLayout(button_row)

        # Output table
        self._table = QTableView(self)
        self._table.setModel(self._files_model)
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setEditTriggers(QTableView.NoEditTriggers)
        header = self._table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        outer.addWidget(self._table, stretch=1)

        self._status_label = QLabel(
            t("deck.status_no_collection", self._ui_language), self,
        )
        self._status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        outer.addWidget(self._status_label)

    # --- public API -----------------------------------------------------

    def set_collection(self, collection: object) -> None:
        if collection is None or not isinstance(collection, PaperCollection):
            self._collection = None
            self._collection_is_enriched = False
            self._export_button.setEnabled(False)
            self._status_label.setText(
                t("deck.status_no_collection", self._ui_language),
            )
            return
        self._collection = collection
        # Heuristic: when any paper has a populated summary, the
        # collection has been through EnrichPage. Surface the distinction
        # because the user wants to know whether the exported deck will
        # be lightweight or thesis-style before clicking Export.
        self._collection_is_enriched = any(
            p.summary is not None for p in collection.papers
        )
        self._export_button.setEnabled(bool(collection.papers))
        status_key = (
            "deck.status_ready_enriched"
            if self._collection_is_enriched
            else "deck.status_ready_raw"
        )
        self._status_label.setText(
            t(status_key, self._ui_language, count=len(collection.papers)),
        )

    def collection(self) -> PaperCollection | None:
        return self._collection

    def status_text(self) -> str:
        return self._status_label.text()

    def files_model(self) -> QStandardItemModel:
        return self._files_model

    def format_checkbox(self, fmt: str) -> QCheckBox:
        return self._format_checks[fmt]

    # --- internals ------------------------------------------------------

    def _on_browse_out_dir(self) -> None:
        start = self._out_dir_input.text() or str(Path.cwd())
        path = QFileDialog.getExistingDirectory(
            self, t("deck.out_dir_dialog_title", self._ui_language), start,
        )
        if path:
            self._out_dir_input.setText(path)

    def _selected_formats(self) -> tuple[str, ...]:
        return tuple(
            fmt for fmt, _label in _FORMAT_CHOICES
            if self._format_checks[fmt].isChecked()
        )

    def _on_export_clicked(self) -> None:
        if self._collection is None or not self._collection.papers:
            self._status_label.setText(
                t("deck.error_no_collection", self._ui_language),
            )
            return
        formats = self._selected_formats()
        if not formats:
            self._status_label.setText(
                t("deck.error_no_formats", self._ui_language),
            )
            return
        out_dir = self._out_dir_input.text().strip()
        if not out_dir:
            self._status_label.setText(
                t("deck.error_no_out_dir", self._ui_language),
            )
            return
        stem = self._filename_stem_input.text().strip() or None
        language = self._language_combo.currentData() or "en"
        options = ExportOptions(
            formats=formats,
            out_dir=out_dir,
            filename_stem=stem,
            include_abstract=self._include_abstract_check.isChecked(),
            language=language,
            max_slides_per_paper=self._max_slides_spin.value(),
            dark_mode=not self._light_mode_check.isChecked(),
        )
        collection = self._collection
        self._export_button.setEnabled(False)
        self._open_folder_button.setEnabled(False)
        self._files_model.removeRows(0, self._files_model.rowCount())
        self._status_label.setText(t("deck.status_running", self._ui_language))

        def call() -> dict[str, Path]:
            return export_collection(collection, options)

        worker = BlockingWorker(call)
        worker.signals.finished.connect(self._on_export_finished)
        worker.signals.failed.connect(self._on_export_failed)
        QThreadPool.globalInstance().start(worker)

    def _on_export_finished(self, written: object) -> None:
        self._export_button.setEnabled(True)
        if not isinstance(written, dict) or not written:
            self._status_label.setText(
                t("deck.error_no_output", self._ui_language),
            )
            return
        any_path: Path | None = None
        for fmt, path in written.items():
            self._files_model.appendRow([
                QStandardItem(fmt),
                QStandardItem(str(path)),
            ])
            any_path = path
        if any_path is not None:
            self._last_written_dir = any_path.parent
            self._open_folder_button.setEnabled(True)
        self._status_label.setText(
            t("deck.status_done", self._ui_language, count=len(written)),
        )

    def _on_export_failed(self, err: object) -> None:
        self._export_button.setEnabled(True)
        self._status_label.setText(
            t("deck.error_generic", self._ui_language, error=str(err)),
        )

    def _on_open_folder_clicked(self) -> None:
        if self._last_written_dir is None:
            return
        # QDesktopServices is the cross-platform "open in file manager"
        # — Windows Explorer, macOS Finder, xdg-open on Linux. Subprocess
        # would be more controllable but also leaks the host OS into the
        # GUI layer; this is the right abstraction.
        url = QUrl.fromLocalFile(str(self._last_written_dir))
        QDesktopServices.openUrl(url)


