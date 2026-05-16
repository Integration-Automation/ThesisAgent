"""Tests for the intelligence pipeline (PDF extract + LLM summary)."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from autopapertoppt.core.exceptions import ConfigError, ParseError
from autopapertoppt.core.models import Paper, PaperCollection, Query
from autopapertoppt.core.pipeline import enrich_collection
from autopapertoppt.fetchers import http as http_module
from autopapertoppt.intelligence import pdf as pdf_module
from autopapertoppt.intelligence import summarise as summarise_module


@pytest.fixture(autouse=True)
def _reset_clients():
    yield
    http_module._CLIENTS.clear()  # noqa: SLF001


def _paper(**overrides) -> Paper:
    base = {
        "source": "arxiv",
        "source_id": "1706.03762",
        "title": "Attention Is All You Need",
        "authors": ("Ashish Vaswani",),
        "year": 2017,
        "venue": "NeurIPS",
        "abstract": "We propose the Transformer.",
        "url": "https://arxiv.org/abs/1706.03762",
        "pdf_url": "https://arxiv.org/pdf/1706.03762",
    }
    base.update(overrides)
    return Paper(**base)


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------


_FAKE_PDF_BODY = b"%PDF-1.4 ...content elided..."


def _install_pdf_transport(monkeypatch, transport):
    http_module._CLIENTS.clear()  # noqa: SLF001

    async def fake_get_client(_source):
        return httpx.AsyncClient(transport=transport)

    monkeypatch.setattr("autopapertoppt.intelligence.pdf.get_client", fake_get_client)


class _CannedPdfTransport(httpx.AsyncBaseTransport):
    def __init__(self, status: int, body: bytes, content_type: str = "application/pdf"):
        self.status = status
        self.body = body
        self.content_type = content_type

    async def handle_async_request(self, request):
        return httpx.Response(
            self.status, content=self.body,
            headers={"content-type": self.content_type},
            request=request,
        )

    async def aclose(self):
        return None


def _patch_pypdf_to_return(monkeypatch, text: str, pages: int = 3):
    class _FakePage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class _FakeReader:
        def __init__(self, *_args, **_kwargs):
            self.pages = [_FakePage(text)] * pages

    monkeypatch.setattr("pypdf.PdfReader", _FakeReader)


async def test_fetch_and_extract_happy_path(monkeypatch):
    transport = _CannedPdfTransport(200, _FAKE_PDF_BODY)
    _install_pdf_transport(monkeypatch, transport)
    _patch_pypdf_to_return(monkeypatch, "Some text from a page.\nNext line.\n\nNew paragraph.")
    result = await pdf_module.fetch_and_extract(
        "https://arxiv.org/pdf/1706.03762", source="arxiv"
    )
    assert result.page_count == 3
    assert "Some text from a page" in result.text


async def test_fetch_and_extract_rejects_non_pdf(monkeypatch):
    transport = _CannedPdfTransport(200, b"<html>nope</html>", content_type="text/html")
    _install_pdf_transport(monkeypatch, transport)
    with pytest.raises(ParseError):
        await pdf_module.fetch_and_extract(
            "https://example.com/paper", source="arxiv"
        )


async def test_fetch_and_extract_size_cap(monkeypatch):
    big = b"%PDF-1.4" + b"x" * (pdf_module.MAX_PDF_BYTES + 100)
    transport = _CannedPdfTransport(200, big)
    _install_pdf_transport(monkeypatch, transport)
    with pytest.raises(ParseError):
        await pdf_module.fetch_and_extract(
            "https://arxiv.org/pdf/big", source="arxiv"
        )


async def test_fetch_and_extract_4xx_raises(monkeypatch):
    transport = _CannedPdfTransport(403, b"forbidden", content_type="text/plain")
    _install_pdf_transport(monkeypatch, transport)
    with pytest.raises(ParseError):
        await pdf_module.fetch_and_extract(
            "https://arxiv.org/pdf/forbidden", source="arxiv"
        )


# ---------------------------------------------------------------------------
# Summarisation (mocked Anthropic client)
# ---------------------------------------------------------------------------


def _fake_anthropic_module(response_text: str):
    """Build a `module-like` mock so summarise_module's lazy import picks it up."""
    captured: dict = {}

    def _fake_client_factory(*, api_key: str):
        class _Client:
            def __init__(self):
                self.messages = _Messages()

        class _Messages:
            def create(self, **kwargs):  # noqa: ARG002  # mock signature mirrors the SDK
                captured["kwargs"] = kwargs
                block = MagicMock()
                block.text = response_text
                response = MagicMock()
                response.content = [block]
                return response

        captured["api_key"] = api_key
        return _Client()

    module = MagicMock()
    module.Anthropic = _fake_client_factory
    return module, captured


def test_summariser_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fake_anthropic, _ = _fake_anthropic_module("{}")
    monkeypatch.setitem(
        __import__("sys").modules, "anthropic", fake_anthropic
    )
    paper = _paper()
    pdf = pdf_module.ExtractedPdf(
        url=paper.pdf_url, page_count=1, chars=10, text="text"
    )
    with pytest.raises(ConfigError):
        summarise_module.summarise_paper(paper, pdf, language="en")


def test_summariser_parses_response(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    response_text = (
        '{\n'
        '  "motivation": ["Transformers were not yet established."],\n'
        '  "contributions": ["Pure attention; no recurrence; no convolution."],\n'
        '  "method": ["Self-attention with multi-head + sinusoidal positions."],\n'
        '  "results": ["28.4 BLEU on WMT En→De (+2 BLEU)."],\n'
        '  "limitations": ["Quadratic memory in sequence length."],\n'
        '  "takeaways": ["Attention alone suffices for translation."]\n'
        '}'
    )
    fake_anthropic, captured = _fake_anthropic_module(response_text)
    monkeypatch.setitem(
        __import__("sys").modules, "anthropic", fake_anthropic
    )
    paper = _paper()
    pdf = pdf_module.ExtractedPdf(
        url=paper.pdf_url, page_count=12, chars=50_000, text="full paper text..."
    )
    summary = summarise_module.summarise_paper(paper, pdf, language="zh-tw")
    assert summary.language == "zh-tw"
    assert summary.motivation == ("Transformers were not yet established.",)
    assert len(summary.contributions) == 1
    assert len(summary.results) == 1
    assert summary.model.startswith("claude")
    assert summary.raw_text_chars == 50_000
    # System prompt should be cache-controlled.
    system = captured["kwargs"]["system"]
    assert system[0]["cache_control"] == {"type": "ephemeral"}


def test_summariser_tolerates_markdown_fenced_json(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    response_text = (
        "Here is the summary:\n\n```json\n"
        '{"motivation": ["m1"], "contributions": ["c1"], "method": [],\n'
        ' "results": [], "limitations": [], "takeaways": ["t1"]}\n'
        "```"
    )
    fake_anthropic, _ = _fake_anthropic_module(response_text)
    monkeypatch.setitem(
        __import__("sys").modules, "anthropic", fake_anthropic
    )
    pdf = pdf_module.ExtractedPdf(url="x", page_count=1, chars=10, text="t")
    summary = summarise_module.summarise_paper(_paper(), pdf, language="en")
    assert summary.motivation == ("m1",)
    assert summary.takeaways == ("t1",)


def test_summariser_rejects_non_json(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    fake_anthropic, _ = _fake_anthropic_module("I refuse to comply.")
    monkeypatch.setitem(
        __import__("sys").modules, "anthropic", fake_anthropic
    )
    pdf = pdf_module.ExtractedPdf(url="x", page_count=1, chars=10, text="t")
    with pytest.raises(ParseError):
        summarise_module.summarise_paper(_paper(), pdf, language="en")


# ---------------------------------------------------------------------------
# Enrichment pipeline (skips bad papers, attaches summary on success)
# ---------------------------------------------------------------------------


async def test_enrich_collection_skips_papers_without_pdf(monkeypatch):
    paper_no_pdf = _paper(pdf_url=None)
    coll = PaperCollection(
        query=Query(keywords="x", sources=("arxiv",), max_results=1),
        papers=(paper_no_pdf,),
    )
    out = await enrich_collection(coll, language="en")
    assert out.papers[0].summary is None


async def test_enrich_collection_attaches_summary(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    async def fake_fetch(url, source="arxiv"):
        return pdf_module.ExtractedPdf(
            url=url, page_count=1, chars=100, text="fake paper content"
        )

    response_text = (
        '{"motivation": ["m"], "contributions": ["c"], "method": ["meth"],\n'
        ' "results": ["r"], "limitations": [], "takeaways": ["t"]}'
    )
    fake_anthropic, _ = _fake_anthropic_module(response_text)
    monkeypatch.setitem(
        __import__("sys").modules, "anthropic", fake_anthropic
    )
    monkeypatch.setattr(
        "autopapertoppt.intelligence.pdf.fetch_and_extract", fake_fetch
    )

    paper = _paper()
    coll = PaperCollection(
        query=Query(keywords="x", sources=("arxiv",), max_results=1),
        papers=(paper,),
    )
    out = await enrich_collection(coll, language="en")
    summary = out.papers[0].summary
    assert summary is not None
    assert summary.motivation == ("m",)
    assert summary.takeaways == ("t",)
    assert summary.language == "en"
