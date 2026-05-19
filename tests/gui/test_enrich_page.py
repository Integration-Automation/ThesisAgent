"""Tests for the Enrich page.

The Anthropic call is mocked end-to-end so the test never hits the
network and never needs ``ANTHROPIC_API_KEY``-shaped credentials in
the environment except where we explicitly set one to drive a code
path.
"""

from __future__ import annotations

import os

import pytest

from autopapertoppt.core.models import (
    Paper,
    PaperCollection,
    PaperSummary,
    Query,
)
from autopapertoppt.gui.pages.enrich import EnrichPage


def _paper(idx: int, *, with_pdf: bool = True) -> Paper:
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
        pdf_url=f"https://example.com/pdf/{idx}" if with_pdf else None,
    )


def _collection(*papers: Paper) -> PaperCollection:
    return PaperCollection(
        query=Query(keywords="enrich-test", sources=("arxiv",)),
        papers=papers,
    )


def test_initial_state_no_collection(qtbot):
    page = EnrichPage(ui_language="en")
    qtbot.addWidget(page)
    # Enrich button disabled, status mentions running a search first.
    assert page._enrich_button.isEnabled() is False  # noqa: SLF001
    assert "search" in page.status_text().lower()


def test_set_collection_enables_button_and_populates_table(qtbot):
    page = EnrichPage(ui_language="en")
    qtbot.addWidget(page)
    page.set_collection(_collection(_paper(1), _paper(2)))
    assert page._enrich_button.isEnabled() is True  # noqa: SLF001
    assert page.table_model().rowCount() == 2
    assert "2" in page.status_text()


def test_enrich_without_api_key_surfaces_settings_hint(qtbot, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    page = EnrichPage(ui_language="en")
    qtbot.addWidget(page)
    page.set_collection(_collection(_paper(1)))
    page._on_enrich_clicked()  # noqa: SLF001
    assert "ANTHROPIC_API_KEY" in page.status_text()


def test_enrich_happy_path_attaches_summaries(qtbot, monkeypatch):
    """Mock fetch_and_extract + summarise_paper so the worker thread
    drives the UI without any real network or LLM call."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    class FakeExtracted:
        text = "abstract … methods … results …"
        chars = 50_000

    async def fake_fetch(_url, source="intelligence"):
        return FakeExtracted()

    def fake_summarise(paper, _pdf, *, language, model, api_key=None):
        return PaperSummary(
            language=language,
            model=model,
            raw_text_chars=50_000,
            core_observation=f"fake summary for {paper.source_id}",
        )

    monkeypatch.setattr(
        "autopapertoppt.intelligence.pdf.fetch_and_extract", fake_fetch,
    )
    monkeypatch.setattr(
        "autopapertoppt.intelligence.summarise.summarise_paper",
        fake_summarise,
    )

    page = EnrichPage(ui_language="en")
    qtbot.addWidget(page)
    page.set_collection(_collection(_paper(1), _paper(2)))
    page._on_enrich_clicked()  # noqa: SLF001

    qtbot.waitUntil(
        lambda: "Done" in page.status_text() or "Done:" in page.status_text(),
        timeout=5000,
    )

    enriched = page.collection()
    assert enriched is not None
    assert len(enriched.papers) == 2
    assert all(p.summary is not None for p in enriched.papers)
    assert "1" in page.status_text() or "2" in page.status_text()


def test_paper_without_pdf_url_is_skipped(qtbot, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    page = EnrichPage(ui_language="en")
    qtbot.addWidget(page)
    page.set_collection(_collection(_paper(1, with_pdf=False)))
    page._on_enrich_clicked()  # noqa: SLF001

    qtbot.waitUntil(
        lambda: "Done" in page.status_text(), timeout=3000,
    )
    enriched = page.collection()
    assert enriched is not None
    # Original paper preserved, summary stays None.
    assert enriched.papers[0].summary is None


def test_collection_ready_emitted_after_enrich(qtbot, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    page = EnrichPage(ui_language="en")
    qtbot.addWidget(page)
    received: list[object] = []
    page.collection_ready.connect(lambda c: received.append(c))
    page.set_collection(_collection(_paper(1, with_pdf=False)))
    page._on_enrich_clicked()  # noqa: SLF001
    qtbot.waitUntil(lambda: len(received) >= 1, timeout=3000)
    assert isinstance(received[0], PaperCollection)


@pytest.fixture(autouse=True)
def _clear_anthropic_key_after_test():
    """Defensive: never leak a fake key into other tests."""
    yield
    os.environ.pop("ANTHROPIC_API_KEY", None)
