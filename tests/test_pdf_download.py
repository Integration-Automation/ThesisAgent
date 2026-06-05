"""Tests for the PDF downloader in thesisagents.core.pdf_download."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from thesisagents.core import pdf_download as pdf_download_module
from thesisagents.core.models import Paper, PaperCollection, Query
from thesisagents.core.pdf_download import download_pdfs
from thesisagents.fetchers import http as http_module


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


def _collection(*papers: Paper) -> PaperCollection:
    return PaperCollection(
        query=Query(keywords="x", sources=("arxiv",), max_results=len(papers) or 1),
        papers=tuple(papers),
    )


class _CannedTransport(httpx.AsyncBaseTransport):
    def __init__(self, status: int, body: bytes, content_type: str = "application/pdf"):
        self.status = status
        self.body = body
        self.content_type = content_type
        self.calls: list[str] = []
        self.request_headers: list[dict[str, str]] = []

    async def handle_async_request(self, request):
        self.calls.append(str(request.url))
        self.request_headers.append({k.lower(): v for k, v in request.headers.items()})
        return httpx.Response(
            self.status,
            content=self.body,
            headers={"content-type": self.content_type},
            request=request,
        )

    async def aclose(self):
        return None


def _install_transport(monkeypatch, transport):
    http_module._CLIENTS.clear()  # noqa: SLF001

    async def fake_get_client(_source):
        return httpx.AsyncClient(transport=transport)

    monkeypatch.setattr(
        "thesisagents.core.pdf_download.get_client", fake_get_client
    )


async def test_download_pdfs_writes_file(tmp_path: Path, monkeypatch):
    transport = _CannedTransport(200, b"%PDF-1.4\nfake bytes")
    _install_transport(monkeypatch, transport)
    results = await download_pdfs(_collection(_paper()), tmp_path)
    assert len(results) == 1
    saved = results[0]
    assert saved.skipped_reason is None
    assert saved.path is not None
    assert saved.path.exists()
    assert saved.path.read_bytes().startswith(b"%PDF")
    assert saved.path.parent.name == "pdfs"


async def test_download_pdfs_skips_paper_without_pdf_url(tmp_path: Path, monkeypatch):
    transport = _CannedTransport(200, b"%PDF-1.4\nx")
    _install_transport(monkeypatch, transport)
    results = await download_pdfs(_collection(_paper(pdf_url=None)), tmp_path)
    assert results[0].path is None
    assert results[0].skipped_reason == "no_pdf_url"
    # The transport should never have been touched.
    assert transport.calls == []


async def test_download_pdfs_rejects_non_pdf_payload(tmp_path: Path, monkeypatch):
    transport = _CannedTransport(200, b"<html>nope</html>", content_type="text/html")
    _install_transport(monkeypatch, transport)
    results = await download_pdfs(_collection(_paper()), tmp_path)
    assert results[0].path is None
    assert results[0].skipped_reason == "not_pdf"


class _ScriptedTransport(httpx.AsyncBaseTransport):
    """Returns a different response per request — for the citation_pdf_url
    retry path where the first GET returns HTML and the second returns the
    actual PDF."""

    def __init__(self, responses: list[tuple[int, bytes, str]]):
        self.responses = list(responses)
        self.calls: list[str] = []

    async def handle_async_request(self, request):
        self.calls.append(str(request.url))
        status, body, content_type = self.responses.pop(0)
        return httpx.Response(
            status,
            content=body,
            headers={"content-type": content_type},
            request=request,
        )

    async def aclose(self):
        return None


async def test_download_pdfs_follows_citation_pdf_url_meta(
    tmp_path: Path, monkeypatch
):
    """Publisher landing page returns HTML with citation_pdf_url meta tag —
    downloader extracts the URL and retries once, getting the real PDF."""
    landing_html = (
        b"<html><head>"
        b'<meta name="citation_title" content="A Paper" />'
        b'<meta name="citation_pdf_url" content="/articles/abc.pdf" />'
        b"</head><body>landing</body></html>"
    )
    transport = _ScriptedTransport(
        [
            (200, landing_html, "text/html"),
            (200, b"%PDF-1.4\nreal pdf bytes", "application/pdf"),
        ]
    )
    _install_transport(monkeypatch, transport)
    paper = _paper(
        url="https://publisher.example/article/abc",
        pdf_url="https://publisher.example/article/abc",
    )
    results = await download_pdfs(_collection(paper), tmp_path)
    assert results[0].skipped_reason is None
    assert results[0].path is not None
    assert results[0].path.read_bytes().startswith(b"%PDF")
    # Second GET should resolve the relative meta URL against the first.
    assert transport.calls[1] == "https://publisher.example/articles/abc.pdf"


async def test_download_pdfs_citation_pdf_url_fail_when_retry_also_html(
    tmp_path: Path, monkeypatch
):
    """If the citation_pdf_url target also returns HTML, surface a distinct reason."""
    landing_html = (
        b"<html><head>"
        b'<meta name="citation_pdf_url" content="https://x/y.pdf" />'
        b"</head></html>"
    )
    transport = _ScriptedTransport(
        [
            (200, landing_html, "text/html"),
            (200, b"<html>still not a pdf</html>", "text/html"),
        ]
    )
    _install_transport(monkeypatch, transport)
    results = await download_pdfs(_collection(_paper()), tmp_path)
    assert results[0].path is None
    assert results[0].skipped_reason == "not_pdf"
    # Both URLs were attempted.
    assert len(transport.calls) == 2


async def test_download_pdfs_handles_http_error(tmp_path: Path, monkeypatch):
    transport = _CannedTransport(404, b"missing", content_type="text/plain")
    _install_transport(monkeypatch, transport)
    results = await download_pdfs(_collection(_paper()), tmp_path)
    assert results[0].path is None
    assert results[0].skipped_reason == "http_404"


async def test_download_pdfs_skips_existing_non_empty_file(
    tmp_path: Path, monkeypatch
):
    transport = _CannedTransport(200, b"%PDF-1.4\nfresh content")
    _install_transport(monkeypatch, transport)
    paper = _paper()
    # Pre-create the target file as if a previous run had written it.
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    target = pdf_dir / f"{paper.bibtex_key()}.pdf"
    target.write_bytes(b"%PDF-1.4 already here")
    results = await download_pdfs(_collection(paper), tmp_path)
    assert results[0].path == target
    assert target.read_bytes() == b"%PDF-1.4 already here"
    # No network call should have been issued because the file existed.
    assert transport.calls == []


async def test_download_pdfs_too_large_is_skipped(tmp_path: Path, monkeypatch):
    big_body = b"%PDF-1.4" + b"x" * (pdf_download_module._MAX_PDF_BYTES + 10)  # noqa: SLF001
    transport = _CannedTransport(200, big_body)
    _install_transport(monkeypatch, transport)
    results = await download_pdfs(_collection(_paper()), tmp_path)
    assert results[0].path is None
    assert results[0].skipped_reason == "too_large"


async def test_download_pdfs_filename_is_sanitised(tmp_path: Path, monkeypatch):
    transport = _CannedTransport(200, b"%PDF-1.4\nx")
    _install_transport(monkeypatch, transport)
    paper = _paper(
        authors=("Über Müller",),
        title="Weird/Title: With * Bad ? chars",
    )
    results = await download_pdfs(_collection(paper), tmp_path)
    assert results[0].path is not None
    name = results[0].path.name
    assert name.endswith(".pdf")
    # No path separators or shell metacharacters survived.
    for forbidden in ("/", "\\", ":", "*", "?", "<", ">"):
        assert forbidden not in name


# ---------------------------------------------------------------------------
# Browser-header + cookie behaviour (added when publishers started returning
# 403 to non-browser UAs even on OpenAlex-supplied PDF URLs).
# ---------------------------------------------------------------------------


async def test_download_pdfs_sends_browser_user_agent(tmp_path: Path, monkeypatch):
    transport = _CannedTransport(200, b"%PDF-1.4\nx")
    _install_transport(monkeypatch, transport)
    await download_pdfs(_collection(_paper()), tmp_path)
    headers = transport.request_headers[0]
    assert "Mozilla/5.0" in headers.get("user-agent", "")
    assert "application/pdf" in headers.get("accept", "")
    assert headers.get("accept-language", "").startswith("en")


async def test_download_pdfs_sends_referer_when_landing_host_matches(
    tmp_path: Path, monkeypatch,
):
    """Same-host Referer fixes the most common publisher 403."""
    transport = _CannedTransport(200, b"%PDF-1.4\nx")
    _install_transport(monkeypatch, transport)
    paper = _paper(
        url="https://example.com/article/123",
        pdf_url="https://example.com/pdf/123.pdf",
    )
    await download_pdfs(_collection(paper), tmp_path)
    assert transport.request_headers[0].get("referer") == paper.url


async def test_download_pdfs_omits_referer_on_cross_host(
    tmp_path: Path, monkeypatch,
):
    transport = _CannedTransport(200, b"%PDF-1.4\nx")
    _install_transport(monkeypatch, transport)
    paper = _paper(
        url="https://openalex.org/W123",
        pdf_url="https://arxiv.org/pdf/1706.03762",
    )
    await download_pdfs(_collection(paper), tmp_path)
    assert "referer" not in transport.request_headers[0]


async def test_download_pdfs_attaches_cookies_when_jar_set(
    tmp_path: Path, monkeypatch,
):
    """Cookies from THESISAGENTS_PDF_COOKIES_FILE must reach the request."""
    from thesisagents.core import pdf_cookies

    cookies_file = tmp_path / "cookies.txt"
    cookies_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".example.com\tTRUE\t/\tFALSE\t0\tJSESSIONID\tabc123\n"
        ".example.com\tTRUE\t/\tFALSE\t0\tauth_token\txyz789\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("THESISAGENTS_PDF_COOKIES_FILE", str(cookies_file))
    pdf_cookies._reset_for_tests()  # noqa: SLF001

    transport = _CannedTransport(200, b"%PDF-1.4\nx")
    _install_transport(monkeypatch, transport)
    paper = _paper(
        url="https://example.com/article/123",
        pdf_url="https://example.com/pdf/123.pdf",
    )
    await download_pdfs(_collection(paper), tmp_path / "out")
    cookie_header = transport.request_headers[0].get("cookie", "")
    assert "JSESSIONID=abc123" in cookie_header
    assert "auth_token=xyz789" in cookie_header


async def test_download_pdfs_no_cookies_when_env_unset(
    tmp_path: Path, monkeypatch,
):
    from thesisagents.core import pdf_cookies

    monkeypatch.delenv("THESISAGENTS_PDF_COOKIES_FILE", raising=False)
    pdf_cookies._reset_for_tests()  # noqa: SLF001

    transport = _CannedTransport(200, b"%PDF-1.4\nx")
    _install_transport(monkeypatch, transport)
    await download_pdfs(_collection(_paper()), tmp_path)
    assert "cookie" not in transport.request_headers[0]


async def test_cookies_only_attach_to_matching_host(
    tmp_path: Path, monkeypatch,
):
    """A cookie scoped to ``.publisher.com`` must NOT leak to ``arxiv.org``."""
    from thesisagents.core import pdf_cookies

    cookies_file = tmp_path / "cookies.txt"
    cookies_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".publisher.com\tTRUE\t/\tFALSE\t0\tSECRET\tdo-not-leak\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("THESISAGENTS_PDF_COOKIES_FILE", str(cookies_file))
    pdf_cookies._reset_for_tests()  # noqa: SLF001

    transport = _CannedTransport(200, b"%PDF-1.4\nx")
    _install_transport(monkeypatch, transport)
    paper = _paper(pdf_url="https://arxiv.org/pdf/1706.03762")
    await download_pdfs(_collection(paper), tmp_path / "out")
    cookie_header = transport.request_headers[0].get("cookie", "")
    assert "SECRET" not in cookie_header
    assert "do-not-leak" not in cookie_header
