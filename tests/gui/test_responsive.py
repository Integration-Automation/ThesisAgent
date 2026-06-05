"""Tests for the responsive layout + HiDPI behaviour."""

from __future__ import annotations

import pytest

from thesisagents.gui.i18n import SUPPORTED_LANGUAGES
from thesisagents.gui.main_window import MainWindow


def test_main_window_has_a_minimum_size(qtbot):
    """The window must be resizeable down to a sensible floor so a 720p
    laptop can still see every tab."""
    window = MainWindow(ui_language="en")
    qtbot.addWidget(window)
    min_size = window.minimumSize()
    assert min_size.width() >= 800
    assert min_size.height() >= 500


def test_main_window_default_size_is_reasonable(qtbot):
    window = MainWindow(ui_language="en")
    qtbot.addWidget(window)
    # The default should not exceed a typical small-laptop screen.
    assert window.width() <= 1600
    assert window.height() <= 1000


def test_window_can_be_resized_smaller_than_default(qtbot):
    """Calling resize() with a value below the default but above the
    minimum must succeed — proves the layout isn't hardcoded."""
    window = MainWindow(ui_language="en")
    qtbot.addWidget(window)
    window.resize(900, 600)
    qtbot.wait(50)
    assert window.width() == 900
    assert window.height() == 600


def test_tabs_wrap_search_and_settings_in_scroll_areas(qtbot):
    """Search + Settings live inside QScrollArea wrappers so a small
    window scrolls instead of clipping content."""
    from PySide6.QtWidgets import QScrollArea

    window = MainWindow(ui_language="en")
    qtbot.addWidget(window)
    # Tab index 0 = Search, 3 = Settings; both must be QScrollAreas.
    search_container = window._tabs.widget(0)  # noqa: SLF001
    settings_container = window._tabs.widget(3)  # noqa: SLF001
    assert isinstance(search_container, QScrollArea)
    assert isinstance(settings_container, QScrollArea)
    assert search_container.widgetResizable() is True
    assert settings_container.widgetResizable() is True


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_main_window_constructs_in_every_supported_language(qtbot, language):
    """A typo in any one language's translation table would crash one
    of the tab labels at construction. This parametrised smoke test
    locks that down for all 14."""
    window = MainWindow(ui_language=language)
    qtbot.addWidget(window)
    assert window.tab_count() == 4
