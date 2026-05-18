"""Tests for ``autopapertoppt.core.oa_resolver``."""

from __future__ import annotations

import pytest

from autopapertoppt.core import oa_resolver
from autopapertoppt.core.models import Paper, PaperCollection, Query


def _paper(**overrides) -> Paper:
    defaults = {
        "source": "openalex",
        "source_id": "W123",
        "title": "Attention Is All You Need",
        "authors": ("Vaswani",),
        "year": 2017,
        "venue": "NeurIPS",
        "abstract": "...",
        "url": "https://example.com/abs",
        "doi": "10.5555/example",
        "arxiv_id": None,
        "pdf_url": None,
    }
    defaults.update(overrides)
    return Paper(**defaults)


@pytest.fixture(autouse=True)
def _reset_warning_flag():
    """The email-missing warning is one-shot per process; reset between tests."""
    oa_resolver._email_warning_emitted = False  # noqa: SLF001
    yield
    oa_resolver._email_warning_emitted = False  # noqa: SLF001


async def test_resolve_returns_unchanged_when_all_papers_have_pdf_url():
    collection = PaperCollection(
        query=Query(keywords="x", sources=("openalex",)),
        papers=(_paper(pdf_url="https://example.com/p.pdf"),),
    )
    result = await oa_resolver.resolve_oa_pdfs(collection)
    assert result.papers[0].pdf_url == "https://example.com/p.pdf"
    # Early-exit returns the same instance — no lookups happened.
    assert result is collection


async def test_resolve_fills_pdf_url_from_unpaywall(monkeypatch):
    async def fake_unpaywall(doi: str) -> str | None:
        assert doi == "10.5555/example"
        return "https://oa-mirror.example/paper.pdf"

    async def fake_arxiv(_paper):
        pytest.fail("arXiv fallback should not run when Unpaywall hits")

    monkeypatch.setattr(oa_resolver, "_query_unpaywall", fake_unpaywall)
    monkeypatch.setattr(oa_resolver, "_query_arxiv_title", fake_arxiv)

    collection = PaperCollection(
        query=Query(keywords="x", sources=("openalex",)),
        papers=(_paper(),),
    )
    result = await oa_resolver.resolve_oa_pdfs(collection)
    assert result.papers[0].pdf_url == "https://oa-mirror.example/paper.pdf"


async def test_resolve_falls_back_to_arxiv_when_unpaywall_misses(monkeypatch):
    async def fake_unpaywall(_doi: str) -> str | None:
        return None

    async def fake_arxiv(_paper):
        return "https://arxiv.org/pdf/1706.03762"

    monkeypatch.setattr(oa_resolver, "_query_unpaywall", fake_unpaywall)
    monkeypatch.setattr(oa_resolver, "_query_arxiv_title", fake_arxiv)

    collection = PaperCollection(
        query=Query(keywords="x", sources=("openalex",)),
        papers=(_paper(),),
    )
    result = await oa_resolver.resolve_oa_pdfs(collection)
    assert result.papers[0].pdf_url == "https://arxiv.org/pdf/1706.03762"


async def test_resolve_passes_through_when_no_doi_and_no_arxiv_hit(monkeypatch):
    async def fake_arxiv(_paper):
        return None

    monkeypatch.setattr(oa_resolver, "_query_arxiv_title", fake_arxiv)

    collection = PaperCollection(
        query=Query(keywords="x", sources=("openalex",)),
        papers=(_paper(doi=None),),
    )
    result = await oa_resolver.resolve_oa_pdfs(collection)
    assert result.papers[0].pdf_url is None


async def test_unpaywall_skipped_silently_when_email_unset(monkeypatch):
    monkeypatch.delenv("AUTOPAPERTOPPT_CONTACT_EMAIL", raising=False)
    result = await oa_resolver._query_unpaywall("10.x/y")  # noqa: SLF001
    assert result is None
    # And the one-shot warning got emitted.
    assert oa_resolver._email_warning_emitted is True  # noqa: SLF001


async def test_unpaywall_skip_does_not_double_warn(monkeypatch):
    """The one-shot flag prevents repeat warnings within a single process."""
    monkeypatch.delenv("AUTOPAPERTOPPT_CONTACT_EMAIL", raising=False)
    call_count = 0

    def counting_warning(*_args, **_kwargs):
        nonlocal call_count
        call_count += 1

    monkeypatch.setattr(oa_resolver._LOG, "warning", counting_warning)  # noqa: SLF001
    await oa_resolver._query_unpaywall("10.x/y")  # noqa: SLF001
    await oa_resolver._query_unpaywall("10.x/z")  # noqa: SLF001
    await oa_resolver._query_unpaywall("10.x/w")  # noqa: SLF001
    assert call_count == 1


async def test_normalise_title_strips_punctuation_and_case():
    norm = oa_resolver._normalise_title  # noqa: SLF001
    assert norm("Attention Is All You Need") == "attentionisallyouneed"
    assert norm("Attention: Is All You Need!") == "attentionisallyouneed"
    assert norm("Attention is all you need.") == "attentionisallyouneed"


async def test_arxiv_fallback_skips_arxiv_sourced_papers():
    paper = _paper(source="arxiv", pdf_url=None)
    result = await oa_resolver._query_arxiv_title(paper)  # noqa: SLF001
    assert result is None


async def test_arxiv_fallback_matches_only_exact_normalised_title(monkeypatch):
    """Title search should NOT accept loosely-similar titles."""
    from unittest.mock import MagicMock

    async def fake_search(query):
        # Return a paper whose title overlaps but isn't a real match.
        return [
            _paper(
                title="Attention is all you need for a totally different topic",
                pdf_url="https://arxiv.org/pdf/9999.99999",
            )
        ]

    fake_fetcher = MagicMock()
    fake_fetcher.search = fake_search

    def fake_load(_name):
        return fake_fetcher

    monkeypatch.setattr(
        "autopapertoppt.fetchers.base.load_fetcher", fake_load
    )
    result = await oa_resolver._query_arxiv_title(_paper())  # noqa: SLF001
    assert result is None


async def test_arxiv_fallback_accepts_exact_match(monkeypatch):
    from unittest.mock import MagicMock

    async def fake_search(query):
        return [
            _paper(
                title="Attention Is All You Need",
                pdf_url="https://arxiv.org/pdf/1706.03762",
            )
        ]

    fake_fetcher = MagicMock()
    fake_fetcher.search = fake_search

    def fake_load(_name):
        return fake_fetcher

    monkeypatch.setattr(
        "autopapertoppt.fetchers.base.load_fetcher", fake_load
    )
    result = await oa_resolver._query_arxiv_title(_paper())  # noqa: SLF001
    assert result == "https://arxiv.org/pdf/1706.03762"


async def test_arxiv_fallback_rejects_non_https():
    """Defence in depth: even if arxiv returned an http:// URL we don't keep it."""
    # The HTTPS-only transport would reject the download later anyway,
    # but the resolver should not stash a known-bad URL into the Paper.
    from unittest.mock import MagicMock

    async def fake_search(query):
        return [
            _paper(
                title="Attention Is All You Need",
                pdf_url="http://arxiv.org/pdf/1706.03762",
            )
        ]

    fake_fetcher = MagicMock()
    fake_fetcher.search = fake_search

    import pytest as _pytest  # local import — monkeypatch is fn-level

    with _pytest.MonkeyPatch().context() as mp:
        mp.setattr("autopapertoppt.fetchers.base.load_fetcher", lambda _: fake_fetcher)
        result = await oa_resolver._query_arxiv_title(_paper())  # noqa: SLF001
    assert result is None
