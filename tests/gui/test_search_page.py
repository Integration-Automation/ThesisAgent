"""Tests for the Search page.

Network is mocked: ``autopapertoppt.gui.pages.search.run_search`` is
monkey-patched to return a canned ``PaperCollection`` so we never hit
arxiv.org from the test suite.
"""

from __future__ import annotations

from autopapertoppt.core.models import Paper, PaperCollection, Query
from autopapertoppt.gui.pages.search import SearchPage


def _canned_collection() -> PaperCollection:
    paper = Paper(
        source="arxiv",
        source_id="2401.00001",
        title="A canned paper",
        authors=("Author A",),
        year=2024,
        venue=None,
        abstract="…",
        url="https://example.com/abs",
        doi=None,
        arxiv_id="2401.00001",
        pdf_url=None,
    )
    return PaperCollection(
        query=Query(keywords="attention", sources=("arxiv",)),
        papers=(paper,),
    )


def test_search_button_runs_and_populates_table(qtbot, monkeypatch):
    page = SearchPage(ui_language="en")
    qtbot.addWidget(page)

    async def fake_run_search(_query, **_kwargs):
        return _canned_collection()

    async def fake_shutdown():
        return None

    monkeypatch.setattr(
        "autopapertoppt.gui.pages.search.run_search", fake_run_search
    )
    monkeypatch.setattr(
        "autopapertoppt.gui.pages.search.shutdown_clients", fake_shutdown
    )

    page.set_query_text("attention")
    page._on_search_clicked()  # noqa: SLF001 — exercising the same path the button uses

    qtbot.waitUntil(
        lambda: page.papers_model().rowCount() == 1, timeout=5000
    )
    assert "1" in page.status_text() or "Found" in page.status_text()


def test_empty_query_surfaces_validation_error(qtbot):
    page = SearchPage(ui_language="en")
    qtbot.addWidget(page)
    page.set_query_text("   ")
    page._on_search_clicked()  # noqa: SLF001
    assert "query" in page.status_text().lower()


def test_export_button_disabled_until_results(qtbot):
    page = SearchPage(ui_language="en")
    qtbot.addWidget(page)
    # _export_button is wired to enable on result; without running a
    # search it should stay disabled.
    assert page._export_button.isEnabled() is False  # noqa: SLF001
