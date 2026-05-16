"""Placeholder page for tabs that ship in a follow-up PR."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from autopapertoppt.gui.i18n import t


class PlaceholderPage(QWidget):
    """Static page with a heading + body explaining what is coming."""

    def __init__(
        self,
        body_key: str,
        ui_language: str = "en",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        title = QLabel(t("placeholder.coming_soon_title", ui_language), self)
        title_font = title.font()
        title_font.setPointSize(title_font.pointSize() + 4)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)

        body = QLabel(t(body_key, ui_language), self)
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignCenter)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout.addStretch(1)
        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(body)
        layout.addStretch(2)
