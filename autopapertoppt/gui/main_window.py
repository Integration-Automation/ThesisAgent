"""Main application window — tabbed shell that hosts the four pages."""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget

from autopapertoppt.gui.i18n import t
from autopapertoppt.gui.pages.placeholder import PlaceholderPage
from autopapertoppt.gui.pages.search import SearchPage
from autopapertoppt.gui.pages.settings import SettingsPage


class MainWindow(QMainWindow):
    """Top-level window. Owns the tab widget and all page instances."""

    def __init__(self, ui_language: str = "en", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("app.title", ui_language))
        self.resize(1100, 720)

        tabs = QTabWidget(self)

        self._search_page = SearchPage(ui_language=ui_language)
        tabs.addTab(self._search_page, t("nav.search", ui_language))

        self._enrich_page = PlaceholderPage(
            body_key="placeholder.enrich_body", ui_language=ui_language
        )
        tabs.addTab(self._enrich_page, t("nav.enrich", ui_language))

        self._deck_page = PlaceholderPage(
            body_key="placeholder.deck_body", ui_language=ui_language
        )
        tabs.addTab(self._deck_page, t("nav.deck", ui_language))

        self._settings_page = SettingsPage(ui_language=ui_language)
        tabs.addTab(self._settings_page, t("nav.settings", ui_language))

        self.setCentralWidget(tabs)
        self._tabs = tabs

    # --- accessors used by tests ----------------------------------------

    def search_page(self) -> SearchPage:
        return self._search_page

    def settings_page(self) -> SettingsPage:
        return self._settings_page

    def tab_count(self) -> int:
        return self._tabs.count()
