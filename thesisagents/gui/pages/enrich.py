"""Enrich tab.

Takes the PaperCollection produced by the Search tab and walks every
paper through ``intelligence.fetch_and_extract`` (download + PDF text
extraction) + ``intelligence.summarise_paper`` (Anthropic call). The
result is a NEW PaperCollection whose ``papers[*].summary`` carries
the rich-tier fields so the Deck tab can render thesis-style decks.

Behaviour rules:

* The Enrich button is disabled until SearchPage emits
  ``collection_ready`` (or a collection is set programmatically by a
  test).
* The Anthropic API key requirement is checked at button-click time,
  not at page-construction time, so opening the tab without a key
  doesn't crash. The error directs the user to the Settings tab.
* Enrichment runs one paper at a time on a worker thread; the UI
  stays responsive and shows per-paper status (pending → ok / failed).
  Sequential (not parallel) because each Anthropic call already takes
  ~10 s and parallelism would just stress the user's rate limit.
* Failed papers don't kill the whole run — they keep the original
  un-enriched ``Paper`` in the output collection so downstream Deck
  rendering still works (falls back to lightweight tier per-paper).
"""

from __future__ import annotations

import os
from dataclasses import replace

from PySide6.QtCore import Qt, QThreadPool, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from thesisagents.core.models import Paper, PaperCollection
from thesisagents.exporters.i18n import SUPPORTED_LANGUAGES as DECK_LANGUAGES
from thesisagents.gui.i18n import LANGUAGE_DISPLAY_NAMES, t
from thesisagents.gui.workers import AsyncWorker

# Anthropic env var name — mirrors intelligence.summarise._API_KEY_ENV
# but duplicated here so importing this page doesn't pull the optional
# anthropic SDK at module-load time.
_API_KEY_ENV = "ANTHROPIC_API_KEY"
_DEFAULT_MODEL = "claude-opus-4-7"


class EnrichPage(QWidget):
    """Enrich the search collection with PDF-derived rich summaries."""

    # Re-emitted to downstream tabs (Deck) whenever an enrichment run
    # finishes — even partially — so they can render whatever survived.
    collection_ready = Signal(object)

    def __init__(self, ui_language: str = "en", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ui_language = ui_language
        self._collection: PaperCollection | None = None
        self._enriched_papers: list[Paper] = []
        self._pending_index: int = 0
        self._table_model = QStandardItemModel(0, 3, self)
        self._table_model.setHorizontalHeaderLabels([
            t("enrich.column_title", ui_language),
            t("enrich.column_pdf", ui_language),
            t("enrich.column_status", ui_language),
        ])
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)

        settings_box = QGroupBox(t("enrich.settings_group", self._ui_language), self)
        form = QFormLayout(settings_box)

        self._language_combo = QComboBox(self)
        for code in DECK_LANGUAGES:
            display = LANGUAGE_DISPLAY_NAMES.get(code, code)
            self._language_combo.addItem(display, code)
        form.addRow(
            t("enrich.language_label", self._ui_language), self._language_combo,
        )

        self._model_input = QLineEdit(self)
        self._model_input.setPlaceholderText(_DEFAULT_MODEL)
        form.addRow(t("enrich.model_label", self._ui_language), self._model_input)

        outer.addWidget(settings_box)

        button_row = QHBoxLayout()
        self._enrich_button = QPushButton(
            t("enrich.enrich_button", self._ui_language), self,
        )
        self._enrich_button.setEnabled(False)
        self._enrich_button.clicked.connect(self._on_enrich_clicked)
        button_row.addWidget(self._enrich_button)
        button_row.addStretch(1)
        outer.addLayout(button_row)

        self._table = QTableView(self)
        self._table.setModel(self._table_model)
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setEditTriggers(QTableView.NoEditTriggers)
        header = self._table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        outer.addWidget(self._table, stretch=1)

        self._status_label = QLabel(
            t("enrich.status_no_collection", self._ui_language), self,
        )
        self._status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        outer.addWidget(self._status_label)

    # --- public API -----------------------------------------------------

    def set_collection(self, collection: object) -> None:
        """Receive the latest collection from SearchPage.

        Called from a Qt signal, so the parameter is typed ``object``.
        ``None`` clears the page (used by tests to simulate the empty
        initial state).
        """
        if collection is None or not isinstance(collection, PaperCollection):
            self._collection = None
            self._enriched_papers = []
            self._table_model.removeRows(0, self._table_model.rowCount())
            self._enrich_button.setEnabled(False)
            self._status_label.setText(
                t("enrich.status_no_collection", self._ui_language),
            )
            return
        self._collection = collection
        self._enriched_papers = []
        self._populate_table(collection.papers)
        self._enrich_button.setEnabled(bool(collection.papers))
        self._status_label.setText(
            t(
                "enrich.status_ready",
                self._ui_language,
                count=len(collection.papers),
            ),
        )

    def collection(self) -> PaperCollection | None:
        """Most recent enriched collection — or the input collection
        when no enrichment has run yet. Used by tests + the Deck tab."""
        if self._enriched_papers:
            assert self._collection is not None  # noqa: S101 # nosec B101  # state-machine invariant, not runtime validation  # invariant
            return replace(self._collection, papers=tuple(self._enriched_papers))
        return self._collection

    def status_text(self) -> str:
        return self._status_label.text()

    def table_model(self) -> QStandardItemModel:
        return self._table_model

    # --- internals ------------------------------------------------------

    def _populate_table(self, papers: tuple[Paper, ...]) -> None:
        self._table_model.removeRows(0, self._table_model.rowCount())
        for paper in papers:
            title_item = QStandardItem(_truncate(paper.title, 80))
            pdf_item = QStandardItem("✓" if paper.pdf_url else "—")
            status_item = QStandardItem(
                t("enrich.row_pending", self._ui_language),
            )
            self._table_model.appendRow([title_item, pdf_item, status_item])

    def _set_row_status(self, row: int, message_key: str, **fmt: object) -> None:
        item = self._table_model.item(row, 2)
        if item is None:
            return
        item.setText(t(message_key, self._ui_language, **fmt))

    def _on_enrich_clicked(self) -> None:
        if self._collection is None or not self._collection.papers:
            self._status_label.setText(
                t("enrich.error_no_collection", self._ui_language),
            )
            return
        if not os.environ.get(_API_KEY_ENV):
            self._status_label.setText(
                t("enrich.error_no_key", self._ui_language),
            )
            return
        self._enriched_papers = []
        self._pending_index = 0
        self._enrich_button.setEnabled(False)
        self._status_label.setText(
            t(
                "enrich.status_running",
                self._ui_language,
                done=0,
                total=len(self._collection.papers),
            ),
        )
        self._enrich_next()

    def _enrich_next(self) -> None:
        assert self._collection is not None  # noqa: S101 # nosec B101  # state-machine invariant, not runtime validation
        idx = self._pending_index
        if idx >= len(self._collection.papers):
            self._on_run_finished()
            return
        paper = self._collection.papers[idx]
        if not paper.pdf_url:
            # No PDF URL means we can't reach the body text — keep the
            # original paper, mark the row, move on.
            self._enriched_papers.append(paper)
            self._set_row_status(idx, "enrich.row_skipped")
            self._pending_index += 1
            self._update_running_status()
            self._enrich_next()
            return
        language = self._language_combo.currentData() or "en"
        model = self._model_input.text().strip() or _DEFAULT_MODEL

        async def coro() -> object:
            # Lazy import — the intelligence extra is optional.
            from thesisagents.intelligence.pdf import fetch_and_extract
            from thesisagents.intelligence.summarise import summarise_paper

            extracted = await fetch_and_extract(paper.pdf_url)
            return summarise_paper(
                paper, extracted, language=language, model=model,
            )

        worker = AsyncWorker(coro)
        worker.signals.finished.connect(self._on_paper_finished)
        worker.signals.failed.connect(self._on_paper_failed)
        QThreadPool.globalInstance().start(worker)

    def _on_paper_finished(self, summary: object) -> None:
        assert self._collection is not None  # noqa: S101 # nosec B101  # state-machine invariant, not runtime validation
        idx = self._pending_index
        paper = self._collection.papers[idx]
        # Attach the new summary, keeping every other field.
        enriched = replace(paper, summary=summary)  # type: ignore[arg-type]
        self._enriched_papers.append(enriched)
        self._set_row_status(idx, "enrich.row_done")
        self._pending_index += 1
        self._update_running_status()
        self._enrich_next()

    def _on_paper_failed(self, err: object) -> None:
        assert self._collection is not None  # noqa: S101 # nosec B101  # state-machine invariant, not runtime validation
        idx = self._pending_index
        paper = self._collection.papers[idx]
        # Failure → keep the original (un-enriched) paper so the
        # downstream collection still has every entry.
        self._enriched_papers.append(paper)
        self._set_row_status(
            idx, "enrich.row_failed", error=str(err)[:60],
        )
        self._pending_index += 1
        self._update_running_status()
        self._enrich_next()

    def _update_running_status(self) -> None:
        assert self._collection is not None  # noqa: S101 # nosec B101  # state-machine invariant, not runtime validation
        total = len(self._collection.papers)
        done = self._pending_index
        self._status_label.setText(
            t("enrich.status_running", self._ui_language, done=done, total=total),
        )

    def _on_run_finished(self) -> None:
        assert self._collection is not None  # noqa: S101 # nosec B101  # state-machine invariant, not runtime validation
        total = len(self._collection.papers)
        successes = sum(
            1 for p in self._enriched_papers if p.summary is not None
        )
        self._enrich_button.setEnabled(True)
        self._status_label.setText(
            t(
                "enrich.status_done",
                self._ui_language,
                successes=successes,
                total=total,
            ),
        )
        result = self.collection()
        if result is not None:
            self.collection_ready.emit(result)


def _truncate(text: str, limit: int) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else text[: limit - 1] + "…"
