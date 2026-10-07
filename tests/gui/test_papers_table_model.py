"""Tests for ``PapersTableModel``."""

from __future__ import annotations

from thesisagents.core.models import Paper, PaperCollection, Query
from thesisagents.gui.models.papers_table_model import PapersTableModel


def _paper(**overrides) -> Paper:
    defaults = {
        "source": "arxiv",
        "source_id": "1706.03762",
        "title": "Attention Is All You Need",
        "authors": ("Vaswani", "Shazeer", "Parmar", "Uszkoreit"),
        "year": 2017,
        "venue": "NeurIPS",
        "abstract": "We propose a new architecture …",
        "url": "https://arxiv.org/abs/1706.03762",
        "doi": "10.48550/arXiv.1706.03762",
        "arxiv_id": "1706.03762",
        "pdf_url": "https://arxiv.org/pdf/1706.03762",
        "citation_count": 12345,
    }
    defaults.update(overrides)
    return Paper(**defaults)


def test_empty_model_reports_zero_rows():
    model = PapersTableModel()
    assert model.rowCount() == 0
    # title, authors, year, source, DOI, citations, suggestion
    assert model.columnCount() == 7


def test_set_collection_populates_rows(qtbot):  # noqa: ARG001 — qtbot just primes QApp
    model = PapersTableModel()
    papers = (_paper(), _paper(source_id="2", title="A second one"))
    collection = PaperCollection(
        query=Query(keywords="attention", sources=("arxiv",)),
        papers=papers,
    )
    model.set_collection(collection)
    assert model.rowCount() == 2


def test_data_returns_title_for_column_zero(qtbot):  # noqa: ARG001
    from PySide6.QtCore import QModelIndex, Qt

    model = PapersTableModel()
    model.set_collection(
        PaperCollection(
            query=Query(keywords="x", sources=("arxiv",)),
            papers=(_paper(),),
        )
    )
    index = model.index(0, 0, QModelIndex())
    assert model.data(index, Qt.DisplayRole) == "Attention Is All You Need"


def test_author_column_truncates_after_three(qtbot):  # noqa: ARG001
    from PySide6.QtCore import QModelIndex, Qt

    model = PapersTableModel()
    model.set_collection(
        PaperCollection(
            query=Query(keywords="x", sources=("arxiv",)),
            papers=(_paper(),),  # four authors -> "Vaswani, Shazeer, Parmar, …"
        )
    )
    rendered = model.data(model.index(0, 1, QModelIndex()), Qt.DisplayRole)
    assert rendered.startswith("Vaswani, Shazeer, Parmar")
    assert rendered.endswith("…")


def test_header_uses_current_language(qtbot):  # noqa: ARG001
    from PySide6.QtCore import Qt

    model = PapersTableModel(language="zh-tw")
    assert model.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "標題"
    model.set_language("en")
    assert model.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "Title"


def test_data_handles_missing_optional_fields(qtbot):  # noqa: ARG001
    from PySide6.QtCore import QModelIndex, Qt

    model = PapersTableModel()
    model.set_collection(
        PaperCollection(
            query=Query(keywords="x", sources=("arxiv",)),
            papers=(_paper(year=None, doi=None, citation_count=None),),
        )
    )
    assert model.data(model.index(0, 2, QModelIndex()), Qt.DisplayRole) == "—"
    assert model.data(model.index(0, 4, QModelIndex()), Qt.DisplayRole) == "—"
    assert model.data(model.index(0, 5, QModelIndex()), Qt.DisplayRole) == "—"


def _diagnosed_collection(*papers: Paper, keywords: str = "attention") -> PaperCollection:
    """A collection the way ``run_search`` returns it: ranked, with diagnostics."""
    from thesisagents.core import pipeline
    from thesisagents.core.ranking import rank_with_scores

    ranked = rank_with_scores(papers, keywords, current_year=2026)
    return PaperCollection(
        query=Query(keywords=keywords, sources=("arxiv",)),
        papers=tuple(entry.paper for entry in ranked),
        diagnostics=pipeline._diagnose(ranked),  # noqa: SLF001
    )


def test_suggestion_column_shows_the_pruning_advice(qtbot):  # noqa: ARG001
    from PySide6.QtCore import QModelIndex, Qt

    model = PapersTableModel()
    model.set_collection(
        _diagnosed_collection(
            _paper(),
            _paper(source_id="2", title="Cooking With Gas", abstract="", doi=None,
                   arxiv_id=None),
        )
    )
    column = model.columnCount() - 1

    assert model.headerData(column, Qt.Horizontal, Qt.DisplayRole) == "Suggestion"
    assert model.data(model.index(0, column, QModelIndex()), Qt.DisplayRole) == "keep"
    assert model.data(model.index(1, column, QModelIndex()), Qt.DisplayRole) == "prune"


def test_suggestion_column_is_localised(qtbot):  # noqa: ARG001
    from PySide6.QtCore import QModelIndex, Qt

    model = PapersTableModel(language="zh-tw")
    model.set_collection(_diagnosed_collection(_paper()))
    column = model.columnCount() - 1

    assert model.headerData(column, Qt.Horizontal, Qt.DisplayRole) == "建議"
    assert model.data(model.index(0, column, QModelIndex()), Qt.DisplayRole) == "保留"


def test_tooltip_explains_the_score_and_the_advice(qtbot):  # noqa: ARG001
    from PySide6.QtCore import QModelIndex, Qt

    model = PapersTableModel()
    model.set_collection(
        _diagnosed_collection(
            _paper(),
            _paper(source_id="2", title="Cooking With Gas", abstract="", doi=None,
                   arxiv_id=None),
        )
    )

    kept = model.data(model.index(0, 0, QModelIndex()), Qt.ToolTipRole)
    pruned = model.data(model.index(1, 3, QModelIndex()), Qt.ToolTipRole)

    assert kept.startswith("total ")
    assert "= relevance " in kept
    assert "• title matches 1 of 1 query terms (attention): +3.00" in kept
    assert "→ keep" in kept
    assert "→ prune" in pruned
    assert "below the prune threshold 10%" in pruned


def test_a_collection_without_diagnostics_shows_a_dash_and_no_tooltip(qtbot):  # noqa: ARG001
    from PySide6.QtCore import QModelIndex, Qt

    model = PapersTableModel()
    model.set_collection(
        PaperCollection(
            query=Query(keywords="x", sources=("arxiv",)), papers=(_paper(),),
        )
    )
    column = model.columnCount() - 1

    assert model.data(model.index(0, column, QModelIndex()), Qt.DisplayRole) == "—"
    assert model.data(model.index(0, 0, QModelIndex()), Qt.ToolTipRole) is None


def test_clearing_the_collection_clears_the_diagnostics(qtbot):  # noqa: ARG001
    model = PapersTableModel()
    model.set_collection(_diagnosed_collection(_paper()))
    model.set_collection(None)

    assert model.rowCount() == 0
    assert model._diagnostics is None  # noqa: SLF001
