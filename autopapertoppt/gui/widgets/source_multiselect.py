"""Checkbox grid for picking which paper sources to query."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QGridLayout, QWidget

from autopapertoppt.core.constants import ALL_SOURCES, DEFAULT_SOURCES

_COLUMNS = 3


class SourceMultiselect(QWidget):
    """Compact grid of source checkboxes.

    Defaults follow ``DEFAULT_SOURCES`` from core/constants.py — the
    opt-in sources (scholar, ieee scraping) are unchecked by default
    to match CLI behaviour.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._boxes: dict[str, QCheckBox] = {}
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        for idx, name in enumerate(ALL_SOURCES):
            box = QCheckBox(name, self)
            box.setChecked(name in DEFAULT_SOURCES)
            grid.addWidget(box, idx // _COLUMNS, idx % _COLUMNS, Qt.AlignLeft)
            self._boxes[name] = box

    def selected(self) -> tuple[str, ...]:
        return tuple(name for name, box in self._boxes.items() if box.isChecked())

    def set_selected(self, names: tuple[str, ...]) -> None:
        wanted = set(names)
        for name, box in self._boxes.items():
            box.setChecked(name in wanted)
