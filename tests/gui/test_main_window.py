"""Smoke tests for the main window shell."""

from __future__ import annotations

from thesisagents.gui.main_window import MainWindow


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
