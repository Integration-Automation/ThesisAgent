"""Tests for the Deck page.

``export_collection`` is monkey-patched so the test verifies the wiring
(format checkboxes → ExportOptions, out_dir / max_slides / etc.) without
actually rendering a .pptx via python-pptx.
"""

from __future__ import annotations

from pathlib import Path

from thesisagents.core.models import Paper, PaperCollection, PaperSummary, Query
from thesisagents.gui.pages.deck import DeckPage


def _paper(idx: int, *, enriched: bool = False) -> Paper:
    summary = (
        PaperSummary(language="en", core_observation="fake")
        if enriched
        else None
    )
    return Paper(
        source="arxiv",
        source_id=f"2401.{idx:05d}",
        title=f"Test paper {idx}",
        authors=("Author A",),
        year=2024,
        venue=None,
        abstract="…",
        url="https://example.com/abs",
        doi=None,
        arxiv_id=f"2401.{idx:05d}",
        pdf_url=None,
        summary=summary,
    )


def _collection(*papers: Paper) -> PaperCollection:
    return PaperCollection(
        query=Query(keywords="deck-test", sources=("arxiv",)),
        papers=papers,
    )


def test_initial_state_disabled(qtbot):
    page = DeckPage(ui_language="en")
    qtbot.addWidget(page)
    assert page._export_button.isEnabled() is False  # noqa: SLF001
    assert "search" in page.status_text().lower()


def test_set_raw_collection_marks_lightweight(qtbot):
    page = DeckPage(ui_language="en")
    qtbot.addWidget(page)
    page.set_collection(_collection(_paper(1), _paper(2)))
    assert page._export_button.isEnabled() is True  # noqa: SLF001
    assert "lightweight" in page.status_text().lower()


def test_set_enriched_collection_marks_thesis(qtbot):
    page = DeckPage(ui_language="en")
    qtbot.addWidget(page)
    page.set_collection(_collection(_paper(1, enriched=True)))
    text = page.status_text().lower()
    # Either of the two phrases used in the en string is acceptable.
    assert "enriched" in text or "thesis" in text


def test_export_calls_backend_with_selected_formats(qtbot, monkeypatch, tmp_path):
    captured: dict[str, object] = {}

    def fake_export(collection, options):
        captured["collection"] = collection
        captured["options"] = options
        return {"pptx": Path(options.out_dir) / "fake.pptx"}

    monkeypatch.setattr(
        "thesisagents.gui.pages.deck.export_collection", fake_export,
    )
    page = DeckPage(ui_language="en")
    qtbot.addWidget(page)
    page._out_dir_input.setText(str(tmp_path))  # noqa: SLF001
    page.set_collection(_collection(_paper(1)))
    # Toggle off bib (selected by default), pptx + xlsx remain on.
    page.format_checkbox("bib").setChecked(False)
    page.format_checkbox("md").setChecked(True)
    page._on_export_clicked()  # noqa: SLF001

    qtbot.waitUntil(lambda: "Wrote" in page.status_text(), timeout=3000)
    opts = captured["options"]
    assert set(opts.formats) == {"pptx", "xlsx", "md"}
    assert opts.out_dir == str(tmp_path)
    assert opts.include_abstract is True


def test_export_blocks_when_no_formats(qtbot):
    page = DeckPage(ui_language="en")
    qtbot.addWidget(page)
    page.set_collection(_collection(_paper(1)))
    # Uncheck everything.
    for fmt in ("pptx", "xlsx", "bib", "md", "json"):
        page.format_checkbox(fmt).setChecked(False)
    page._on_export_clicked()  # noqa: SLF001
    assert "format" in page.status_text().lower()


def test_open_folder_disabled_until_first_export(qtbot):
    page = DeckPage(ui_language="en")
    qtbot.addWidget(page)
    assert page._open_folder_button.isEnabled() is False  # noqa: SLF001
    page.set_collection(_collection(_paper(1)))
    # Setting a collection enables Export but not Open folder.
    assert page._export_button.isEnabled() is True  # noqa: SLF001
    assert page._open_folder_button.isEnabled() is False  # noqa: SLF001


def _capture_export_options(monkeypatch) -> dict[str, object]:
    captured: dict[str, object] = {}

    def fake_export(collection, options):
        captured["options"] = options
        return {"bib": Path(options.out_dir) / "fake.bib"}

    monkeypatch.setattr("thesisagents.gui.pages.deck.export_collection", fake_export)
    return captured


def test_export_verifies_identifiers_by_default(qtbot, monkeypatch, tmp_path):
    captured = _capture_export_options(monkeypatch)
    page = DeckPage(ui_language="en")
    qtbot.addWidget(page)
    page._out_dir_input.setText(str(tmp_path))  # noqa: SLF001
    page.set_collection(_collection(_paper(1)))
    assert page.verify_identifiers_checkbox().isChecked() is True
    page._on_export_clicked()  # noqa: SLF001

    qtbot.waitUntil(lambda: "Wrote" in page.status_text(), timeout=3000)
    assert captured["options"].verify_identifiers is True


def test_unchecking_verify_identifiers_reaches_the_export(qtbot, monkeypatch, tmp_path):
    captured = _capture_export_options(monkeypatch)
    page = DeckPage(ui_language="en")
    qtbot.addWidget(page)
    page._out_dir_input.setText(str(tmp_path))  # noqa: SLF001
    page.set_collection(_collection(_paper(1)))
    page.verify_identifiers_checkbox().setChecked(False)
    page._on_export_clicked()  # noqa: SLF001

    qtbot.waitUntil(lambda: "Wrote" in page.status_text(), timeout=3000)
    assert captured["options"].verify_identifiers is False


def test_a_failed_preflight_is_shown_in_the_status_line(qtbot, tmp_path):
    """No monkeypatch: the real export runs and the preflight rejects the DOI."""
    import dataclasses

    page = DeckPage(ui_language="en")
    qtbot.addWidget(page)
    page._out_dir_input.setText(str(tmp_path))  # noqa: SLF001
    page.set_collection(
        _collection(dataclasses.replace(_paper(1), doi="10.x/not-a-doi"))
    )
    page._on_export_clicked()  # noqa: SLF001

    qtbot.waitUntil(
        lambda: "identifier verification failed" in page.status_text(), timeout=5000
    )
    assert "10.x/not-a-doi" in page.status_text()
    assert page._export_button.isEnabled() is True  # noqa: SLF001
    assert list(tmp_path.iterdir()) == []
