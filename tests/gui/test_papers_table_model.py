"""Tests for ``PapersTableModel``."""

from __future__ import annotations

from autopapertoppt.core.models import Paper, PaperCollection, Query
from autopapertoppt.gui.models.papers_table_model import PapersTableModel


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
    assert model.columnCount() == 6


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
