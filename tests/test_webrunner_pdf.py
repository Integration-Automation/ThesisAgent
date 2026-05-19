"""Tests for ``autopapertoppt.fetchers.webrunner_pdf``."""

from __future__ import annotations

import pytest

from autopapertoppt.fetchers import webrunner_pdf


@pytest.mark.parametrize(
    "url",
    [
        "https://dl.acm.org/doi/pdf/10.1145/3411764.3445005",
        "https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=10965643",
        "https://link.springer.com/content/pdf/10.1007/s11042.pdf",
        "https://www.sciencedirect.com/science/article/pii/X.pdf",
        "https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/x.pdf",
        "https://academic.oup.com/journal/article/X/Y/pdf",
        "https://www.nature.com/articles/x.pdf",
        "https://www.science.org/doi/pdf/10.1126/x",
    ],
)
def test_should_use_webrunner_matches_paywalled_publishers(url):
    assert webrunner_pdf.should_use_webrunner(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://arxiv.org/pdf/1706.03762.pdf",
        "https://export.arxiv.org/pdf/2401.08741.pdf",
        "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1234/pdf/x.pdf",
        "https://www.example.com/paper.pdf",
        "https://oa-repo.university.edu/files/x.pdf",
    ],
)
def test_should_use_webrunner_skips_open_access_hosts(url):
    assert webrunner_pdf.should_use_webrunner(url) is False


def test_should_use_webrunner_handles_garbage_url():
    assert webrunner_pdf.should_use_webrunner("") is False
    assert webrunner_pdf.should_use_webrunner("not-a-url") is False


def test_is_available_skipped_when_disable_env_set(monkeypatch):
    monkeypatch.setenv("AUTOPAPERTOPPT_DISABLE_WEBRUNNER", "1")
    assert webrunner_pdf.is_available() is False


def test_is_available_returns_true_when_selenium_present(monkeypatch):
    monkeypatch.delenv("AUTOPAPERTOPPT_DISABLE_WEBRUNNER", raising=False)
    # selenium is in [dev] extras so it's importable in the test venv.
    assert webrunner_pdf.is_available() is True


async def test_pdf_download_routes_paywalled_through_webrunner(monkeypatch, tmp_path):
    """The PDF downloader pipeline routes paywalled URLs via WebRunner."""
    from autopapertoppt.core import pdf_download
    from autopapertoppt.core.models import Paper, PaperCollection, Query

    captured: dict[str, object] = {}

    async def fake_browser_download(url, target):
        captured["url"] = url
        captured["target"] = target
        # Write a fake PDF so the persistence check passes.
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"%PDF-1.4\n...fake body...\n%%EOF")
        return True

    monkeypatch.setattr(webrunner_pdf, "is_available", lambda: True)
    monkeypatch.setattr(webrunner_pdf, "download_via_browser", fake_browser_download)

    paper = Paper(
        source="acm", source_id="X",
        title="ACM paper", authors=("A",), year=2025,
        venue="ACM CCS", abstract="...",
        url="https://dl.acm.org/doi/10.1145/X",
        doi="10.1145/X", arxiv_id=None,
        pdf_url="https://dl.acm.org/doi/pdf/10.1145/X",
    )
    collection = PaperCollection(
        query=Query(keywords="x", sources=("acm",)),
        papers=(paper,),
    )
    results = await pdf_download.download_pdfs(collection, tmp_path)
    assert len(results) == 1
    assert results[0].skipped_reason is None
    assert results[0].path is not None
    assert results[0].path.exists()
    assert captured["url"] == "https://dl.acm.org/doi/pdf/10.1145/X"


async def test_pdf_download_skips_webrunner_for_arxiv(monkeypatch, tmp_path):
    """arXiv PDFs bypass WebRunner — httpx works fine on arXiv."""
    from autopapertoppt.core import pdf_download
    from autopapertoppt.core.models import Paper, PaperCollection, Query

    async def fail_browser(_url, _target):
        pytest.fail("WebRunner should not be called for arXiv URLs")

    monkeypatch.setattr(webrunner_pdf, "is_available", lambda: True)
    monkeypatch.setattr(webrunner_pdf, "download_via_browser", fail_browser)

    # Stub the httpx fetch so we don't hit the real network.
    async def fake_fetch_and_validate(_paper, target, _key):
        target.write_bytes(b"%PDF-1.4\nfrom arxiv\n%%EOF")
        return pdf_download.PdfDownloadResult(
            paper_key=_key, path=target, skipped_reason=None,
        )

    monkeypatch.setattr(pdf_download, "_fetch_and_validate", fake_fetch_and_validate)

    paper = Paper(
        source="arxiv", source_id="1706.03762",
        title="Attention", authors=("V",), year=2017,
        venue=None, abstract="...",
        url="https://arxiv.org/abs/1706.03762",
        doi=None, arxiv_id="1706.03762",
        pdf_url="https://arxiv.org/pdf/1706.03762.pdf",
    )
    collection = PaperCollection(
        query=Query(keywords="x", sources=("arxiv",)),
        papers=(paper,),
    )
    results = await pdf_download.download_pdfs(collection, tmp_path)
    assert results[0].skipped_reason is None
    assert results[0].path is not None
