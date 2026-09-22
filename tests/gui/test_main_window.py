"""Smoke tests for the main window shell."""

from __future__ import annotations

from PySide6.QtCore import QByteArray

from thesisagents.gui.main_window import MainWindow
from thesisagents.gui.pages.settings import settings_store


def test_main_window_has_four_tabs(qtbot):
    window = MainWindow(ui_language="en")
    qtbot.addWidget(window)
    assert window.tab_count() == 4


def test_main_window_title_is_localised(qtbot):
    window = MainWindow(ui_language="zh-tw")
    qtbot.addWidget(window)
    assert window.windowTitle() == "ThesisAgents"


def test_search_tab_exposes_search_page(qtbot):
    window = MainWindow(ui_language="en")
    qtbot.addWidget(window)
    page = window.search_page()
    assert page is not None
    # Initially zero rows + status "Idle."
    assert page.papers_model().rowCount() == 0
    assert "Idle" in page.status_text()


def _recorder(calls):
    """A stand-in for ``restoreGeometry`` that records the bytes it is given."""
    return lambda _window, data: calls.append(bytes(data))


def test_closing_saves_the_window_geometry(qtbot):
    window = MainWindow(ui_language="en")
    qtbot.addWidget(window)
    window.close()
    assert settings_store().value("window/geometry") == window.saveGeometry()


def test_new_window_restores_the_saved_geometry(qtbot, monkeypatch):
    restored = []
    monkeypatch.setattr(MainWindow, "restoreGeometry", _recorder(restored))
    settings_store().setValue("window/geometry", QByteArray(b"saved blob"))
    qtbot.addWidget(MainWindow(ui_language="en"))
    assert restored == [b"saved blob"]


def test_nothing_is_restored_without_saved_geometry(qtbot, monkeypatch):
    restored = []
    monkeypatch.setattr(MainWindow, "restoreGeometry", _recorder(restored))
    qtbot.addWidget(MainWindow(ui_language="en"))
    assert restored == []


def test_maximised_state_survives_a_restart(qtbot):
    first = MainWindow(ui_language="en")
    qtbot.addWidget(first)
    first.showMaximized()
    first.close()
    second = MainWindow(ui_language="en")
    qtbot.addWidget(second)
    assert second.isMaximized()
