"""Main application window — tabbed shell that hosts the four pages.

Layout is intentionally responsive: every tab page sits inside a
``QScrollArea`` with ``widgetResizable=True`` so the form widgets
stretch horizontally with the window and reveal a vertical
scrollbar when the window shrinks below the form's natural height.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow,
    QScrollArea,
    QTabWidget,
    QWidget,
)

from autopapertoppt.gui.i18n import t
from autopapertoppt.gui.pages.placeholder import PlaceholderPage
from autopapertoppt.gui.pages.search import SearchPage
from autopapertoppt.gui.pages.settings import SettingsPage

# Sensible window-size bounds: a 720p laptop can still see everything
# at 900x600, while a 4K monitor gets a comfortable default that does
# not feel cramped.
_MIN_WIDTH = 900
_MIN_HEIGHT = 600
_DEFAULT_WIDTH = 1280
_DEFAULT_HEIGHT = 800


class MainWindow(QMainWindow):
    """Top-level window. Owns the tab widget and all page instances."""

    def __init__(self, ui_language: str = "en", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("app.title", ui_language))
        self.setMinimumSize(_MIN_WIDTH, _MIN_HEIGHT)
        self.resize(_DEFAULT_WIDTH, _DEFAULT_HEIGHT)

        tabs = QTabWidget(self)
        tabs.setDocumentMode(True)

        self._search_page = SearchPage(ui_language=ui_language)
        tabs.addTab(
            self._wrap_scrollable(self._search_page),
            t("nav.search", ui_language),
        )

        self._enrich_page = PlaceholderPage(
            body_key="placeholder.enrich_body", ui_language=ui_language
        )
        tabs.addTab(self._enrich_page, t("nav.enrich", ui_language))

        self._deck_page = PlaceholderPage(
            body_key="placeholder.deck_body", ui_language=ui_language
        )
        tabs.addTab(self._deck_page, t("nav.deck", ui_language))

        self._settings_page = SettingsPage(ui_language=ui_language)
        tabs.addTab(
            self._wrap_scrollable(self._settings_page),
            t("nav.settings", ui_language),
        )

        self.setCentralWidget(tabs)
        self._tabs = tabs

    def _wrap_scrollable(self, page: QWidget) -> QScrollArea:
        """Wrap a page so it scrolls vertically when the window shrinks.

        widgetResizable=True is what makes the inner widget stretch with
        the scroll area's width — without it the page would sit at its
        sizeHint() and ignore the available horizontal space.
        """
        scroll = QScrollArea(self)
        scroll.setWidget(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        return scroll

    # --- accessors used by tests ----------------------------------------

    def search_page(self) -> SearchPage:
        return self._search_page

    def settings_page(self) -> SettingsPage:
        return self._settings_page

    def tab_count(self) -> int:
        return self._tabs.count()
