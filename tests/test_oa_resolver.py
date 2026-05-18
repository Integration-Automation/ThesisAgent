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
    """One-shot warning flags reset between tests."""
    oa_resolver._email_warning_emitted = False  # noqa: SLF001
    oa_resolver._core_warning_emitted = False  # noqa: SLF001
    yield
    oa_resolver._email_warning_emitted = False  # noqa: SLF001
    oa_resolver._core_warning_emitted = False  # noqa: SLF001


def test_arxiv_id_to_pdf_strips_version_suffix():
    assert oa_resolver._arxiv_id_to_pdf("1706.03762") == "https://arxiv.org/pdf/1706.03762.pdf"  # noqa: SLF001
    assert oa_resolver._arxiv_id_to_pdf("1706.03762v2") == "https://arxiv.org/pdf/1706.03762.pdf"  # noqa: SLF001
    assert oa_resolver._arxiv_id_to_pdf("cs.LG/0001001v1") == "https://arxiv.org/pdf/cs.LG/0001001.pdf"  # noqa: SLF001
    assert oa_resolver._arxiv_id_to_pdf("") is None  # noqa: SLF001
    assert oa_resolver._arxiv_id_to_pdf("   ") is None  # noqa: SLF001


async def test_resolve_uses_arxiv_id_direct_before_unpaywall(monkeypatch):
    """If arxiv_id is set, derive the PDF URL directly with no HTTP call."""
    unpaywall_calls: list[str] = []

    async def fake_unpaywall(doi):
        unpaywall_calls.append(doi)
        return

    monkeypatch.setattr(oa_resolver, "_query_unpaywall", fake_unpaywall)

    paper = _paper(arxiv_id="1706.03762")
    collection = PaperCollection(
        query=Query(keywords="x", sources=("openalex",)),
        papers=(paper,),
    )
    result = await oa_resolver.resolve_oa_pdfs(collection)
    assert result.papers[0].pdf_url == "https://arxiv.org/pdf/1706.03762.pdf"
    # Unpaywall should NOT have been called — arxiv_id short-circuited.
    assert unpaywall_calls == []


async def test_resolve_falls_back_to_s2_when_unpaywall_misses(monkeypatch):
    async def fake_unpaywall(_doi):
        return None

    async def fake_s2(doi):
        assert doi == "10.5555/example"
        return "https://semantic-scholar-oa.example/p.pdf"

    monkeypatch.setattr(oa_resolver, "_query_unpaywall", fake_unpaywall)
    monkeypatch.setattr(oa_resolver, "_query_semantic_scholar", fake_s2)

    collection = PaperCollection(
        query=Query(keywords="x", sources=("openalex",)),
        papers=(_paper(),),
    )
    result = await oa_resolver.resolve_oa_pdfs(collection)
    assert result.papers[0].pdf_url == "https://semantic-scholar-oa.example/p.pdf"


async def test_resolve_falls_back_to_core_when_s2_misses(monkeypatch):
    async def miss(_doi):
        return None

    async def fake_core(doi):
        assert doi == "10.5555/example"
        return "https://institutional-repo.example/p.pdf"

    monkeypatch.setattr(oa_resolver, "_query_unpaywall", miss)
    monkeypatch.setattr(oa_resolver, "_query_semantic_scholar", miss)
    monkeypatch.setattr(oa_resolver, "_query_core", fake_core)

    collection = PaperCollection(
        query=Query(keywords="x", sources=("openalex",)),
        papers=(_paper(),),
    )
    result = await oa_resolver.resolve_oa_pdfs(collection)
    assert result.papers[0].pdf_url == "https://institutional-repo.example/p.pdf"


async def test_core_skipped_silently_when_key_unset(monkeypatch):
    monkeypatch.delenv("AUTOPAPERTOPPT_CORE_API_KEY", raising=False)
    result = await oa_resolver._query_core("10.x/y")  # noqa: SLF001
    assert result is None
    assert oa_resolver._core_warning_emitted is True  # noqa: SLF001


async def test_s2_cache_skips_repeat_lookups(monkeypatch):
    """A DOI looked up once is served from in-process cache the second time."""
    monkeypatch.setattr(oa_resolver, "_S2_CACHE", {"10.x/cached": "https://oa.example/p.pdf"})
    result = await oa_resolver._query_semantic_scholar("10.x/cached")  # noqa: SLF001
    assert result == "https://oa.example/p.pdf"


async def test_s2_api_key_sent_when_set(monkeypatch):
    """When AUTOPAPERTOPPT_S2_API_KEY is set, the resolver attaches x-api-key."""
    monkeypatch.setattr(oa_resolver, "_S2_CACHE", {})
    monkeypatch.setenv("AUTOPAPERTOPPT_S2_API_KEY", "test-key")

    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"openAccessPdf": {"url": "https://s2.example/p.pdf"}}

    class FakeClient:
        async def get(self, url, params=None, headers=None):
            captured["headers"] = headers
            return FakeResponse()

    async def fake_get_client(_name):
        return FakeClient()

    monkeypatch.setattr(oa_resolver, "get_client", fake_get_client)

    result = await oa_resolver._query_semantic_scholar("10.x/with-key")  # noqa: SLF001
    assert result == "https://s2.example/p.pdf"
    assert captured["headers"] == {"x-api-key": "test-key"}


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
