"""Tests for the Search page.

Network is mocked: ``thesisagents.gui.pages.search.run_search`` is
monkey-patched to return a canned ``PaperCollection`` so we never hit
arxiv.org from the test suite.
"""

from __future__ import annotations

from thesisagents.core.models import Paper, PaperCollection, Query
from thesisagents.gui.pages.search import SearchPage


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
        "thesisagents.gui.pages.search.run_search", fake_run_search
    )
    monkeypatch.setattr(
        "thesisagents.gui.pages.search.shutdown_clients", fake_shutdown
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


def test_quick_export_formats_are_all_registered():
    """The one-button Export once asked for "bibtex", which is not a format
    name (it is "bib"), so every click ended in "no exporter registered"."""
    from thesisagents.exporters import _REGISTRY
    from thesisagents.gui.pages.search import QUICK_EXPORT_FORMATS

    assert QUICK_EXPORT_FORMATS == ("pptx", "xlsx", "bib")
    assert set(QUICK_EXPORT_FORMATS) <= set(_REGISTRY)


def _collection_with_source_stats():
    from thesisagents.core.diagnostics import (
        SearchDiagnostics,
        SourceStat,
        SourceStatus,
    )
    from thesisagents.core.models import Paper, PaperCollection, Query

    paper = Paper(
        source="arxiv", source_id="1", title="A Paper", authors=("Ada Author",),
        year=2025, venue=None, abstract="", url="https://example.org/1",
    )
    stats = (
        SourceStat("arxiv", requested=25, returned=23, after_dedup=19),
        SourceStat("openalex", requested=25, returned=0, after_dedup=0),
        SourceStat(
            "ieee", requested=25, returned=0, after_dedup=0,
            status=SourceStatus.FAILED, detail="[ieee] blocked",
        ),
        SourceStat(
            "semantic_scholar", requested=25, returned=0, after_dedup=0,
            status=SourceStatus.RATE_LIMITED, detail="429",
        ),
        SourceStat(
            "springer", requested=25, returned=0, after_dedup=0,
            status=SourceStatus.DISABLED, detail="no key",
        ),
    )
    return PaperCollection(
        query=Query(keywords="x", sources=("arxiv",)), papers=(paper,),
        diagnostics=SearchDiagnostics(source_stats=stats),
    )


def test_status_line_says_what_each_source_returned(qtbot):
    from thesisagents.gui.pages.search import SearchPage

    page = SearchPage(ui_language="en")
    qtbot.addWidget(page)
    page._on_search_finished(_collection_with_source_stats())  # noqa: SLF001

    assert page.status_text() == (
        "Found 1 paper(s). Sources: arxiv 23, openalex 0, ieee (failed), "
        "semantic_scholar (rate limited), springer (disabled)"
    )


def test_status_line_source_labels_are_localised(qtbot):
    from thesisagents.gui.pages.search import SearchPage

    page = SearchPage(ui_language="zh-tw")
    qtbot.addWidget(page)
    page._on_search_finished(_collection_with_source_stats())  # noqa: SLF001

    text = page.status_text()
    assert "來源: arxiv 23, openalex 0, ieee (失敗)" in text
    assert "semantic_scholar (被限流)" in text
    assert "springer (未啟用)" in text


def test_status_line_has_no_source_part_without_counts(qtbot):
    from thesisagents.core.models import Paper, PaperCollection, Query
    from thesisagents.gui.pages.search import SearchPage

    paper = Paper(
        source="arxiv", source_id="1", title="A Paper", authors=("Ada Author",),
        year=2025, venue=None, abstract="", url="https://example.org/1",
    )
    page = SearchPage(ui_language="en")
    qtbot.addWidget(page)
    page._on_search_finished(  # noqa: SLF001
        PaperCollection(query=Query(keywords="x", sources=("arxiv",)), papers=(paper,))
    )

    assert page.status_text() == "Found 1 paper(s)."
