"""Citation providers against responses recorded from the real APIs.

Fixtures (recorded 2026-10-08 for DOI ``10.1145/3292500.3330701``, with no
API key or contact address in the request):

* ``semantic_scholar/references.json`` / ``citations.json``: ``limit=3``
* ``openalex/resolve_doi.json``, ``references.json``, ``cited_by.json``:
  ``per-page=3``
* ``crossref/work_with_references.json`` (29 references, 7 with a DOI) and
  ``references_hydrated.json`` (the first three of those DOIs)
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs

import pytest

from tests.sources._mock import MockTransport, RoutingTransport, install_mock
from thesisagents.core.exceptions import (
    CitationNotAvailableError,
    ConfigError,
    ParseError,
    RateLimitError,
    SourceUnavailableError,
)
from thesisagents.core.models import Paper
from thesisagents.fetchers.citations import CitationProvider, load_citation_provider
from thesisagents.sources.crossref.citations import CrossrefCitations, _reference_dois
from thesisagents.sources.openalex.citations import OpenAlexCitations
from thesisagents.sources.semantic_scholar.citations import SemanticScholarCitations

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
_TARGET = "thesisagents.fetchers.citations"
_DOI = "10.1145/3292500.3330701"
_WORK_ID = "W2949676527"


def _fixture(source: str, name: str) -> str:
    return (_FIXTURES / source / name).read_text(encoding="utf-8")


def _paper(**overrides) -> Paper:
    fields = {
        "source": "crossref", "source_id": _DOI, "title": "Optuna",
        "authors": ("Takuya Akiba",), "year": 2019, "venue": "KDD", "abstract": "",
        "url": f"https://doi.org/{_DOI}", "doi": _DOI,
    }
    fields.update(overrides)
    return Paper(**fields)


def _params(url) -> dict[str, str]:
    return {key: values[0] for key, values in parse_qs(url.query.decode()).items()}


@pytest.fixture(autouse=True)
def _no_credentials(monkeypatch):
    for name in (
        "THESISAGENTS_S2_API_KEY", "THESISAGENTS_CONTACT_EMAIL",
        "THESISAGENTS_CROSSREF_PLUS_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["semantic_scholar", "openalex", "crossref"])
def test_load_citation_provider_returns_the_plugins_provider(name):
    provider = load_citation_provider(name)

    assert isinstance(provider, CitationProvider)
    assert provider.name == name


def test_a_source_without_citation_links_is_a_config_error():
    with pytest.raises(ConfigError, match="offers no citation provider"):
        load_citation_provider("arxiv")


def test_an_unknown_source_is_a_config_error():
    with pytest.raises(ConfigError, match="unknown or unavailable source plugin"):
        load_citation_provider("no_such_source")


def test_default_providers_all_load():
    from thesisagents.core.constants import DEFAULT_CITATION_PROVIDERS

    assert DEFAULT_CITATION_PROVIDERS == ("openalex", "semantic_scholar", "crossref")
    for name in DEFAULT_CITATION_PROVIDERS:
        assert load_citation_provider(name).name == name


# ---------------------------------------------------------------------------
# Semantic Scholar
# ---------------------------------------------------------------------------


async def test_s2_references_parses_the_cited_papers(monkeypatch):
    transport = MockTransport(200, _fixture("semantic_scholar", "references.json"))
    install_mock(monkeypatch, _TARGET, transport)

    papers = await SemanticScholarCitations().references(_paper(), limit=20)

    assert [p.title for p in papers] == [
        "The Open Images Dataset V4",
        "PFDet: 2nd Place Solution to Open Images Challenge 2018 Object Detection Track",
        "Tune: A Research Platform for Distributed Model Selection and Training",
    ]
    first = papers[0]
    assert first.source == "semantic_scholar"
    assert first.doi == "10.1007/s11263-020-01316-z"
    assert first.arxiv_id == "1811.00982"
    assert first.year == 2018
    assert first.authors  # names come back under plain "authors"
    assert transport.received_url.path == f"/graph/v1/paper/DOI:{_DOI}/references"


async def test_s2_cited_by_parses_the_citing_papers(monkeypatch):
    transport = MockTransport(200, _fixture("semantic_scholar", "citations.json"))
    install_mock(monkeypatch, _TARGET, transport)

    papers = await SemanticScholarCitations().cited_by(_paper(), limit=20)

    assert len(papers) == 3
    assert papers[0].title.startswith("Toward data-driven Digital Twins")
    assert papers[0].doi == "10.1016/j.future.2026.108689"
    assert transport.received_url.path == f"/graph/v1/paper/DOI:{_DOI}/citations"


async def test_s2_does_not_send_the_field_the_endpoint_rejects(monkeypatch):
    """These two endpoints answer HTTP 400 "Unrecognized or unsupported fields:
    [authors.name]", the dotted form the search endpoint accepts."""
    transport = MockTransport(200, '{"data": []}')
    install_mock(monkeypatch, _TARGET, transport)

    await SemanticScholarCitations().references(_paper(), limit=20)

    fields = _params(transport.received_url)["fields"].split(",")
    assert "authors" in fields
    assert "authors.name" not in fields
    assert _params(transport.received_url)["limit"] == "20"


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"source": "semantic_scholar", "source_id": "abc123"}, "abc123"),
        ({"doi": "https://doi.org/10.1145/ABC.42"}, "DOI:10.1145/abc.42"),
        ({"doi": None, "arxiv_id": "1706.03762v5"}, "ARXIV:1706.03762"),
    ],
)
async def test_s2_picks_the_identifier_it_understands(monkeypatch, overrides, expected):
    transport = MockTransport(200, '{"data": []}')
    install_mock(monkeypatch, _TARGET, transport)

    await SemanticScholarCitations().references(_paper(**overrides), limit=5)

    assert transport.received_url.path == f"/graph/v1/paper/{expected}/references"


async def test_s2_without_any_identifier_asks_nothing(monkeypatch):
    transport = MockTransport(200, '{"data": []}')
    install_mock(monkeypatch, _TARGET, transport)

    with pytest.raises(CitationNotAvailableError, match="no DOI, arXiv ID"):
        await SemanticScholarCitations().references(_paper(doi=None), limit=5)

    assert transport.received_url is None


async def test_s2_skips_unresolved_reference_stubs(monkeypatch):
    body = json.dumps(
        {"data": [
            {"citedPaper": {"paperId": None, "title": None}},
            {"citedPaper": None},
            {"citedPaper": {"paperId": "p1", "title": "A Real Paper", "year": 2020}},
        ]}
    )
    install_mock(monkeypatch, _TARGET, MockTransport(200, body))

    papers = await SemanticScholarCitations().references(_paper(), limit=5)

    assert [p.title for p in papers] == ["A Real Paper"]


async def test_s2_caps_the_limit_it_sends_and_what_it_returns(monkeypatch):
    transport = MockTransport(200, _fixture("semantic_scholar", "references.json"))
    install_mock(monkeypatch, _TARGET, transport)

    papers = await SemanticScholarCitations().references(_paper(), limit=2)
    assert len(papers) == 2
    assert _params(transport.received_url)["limit"] == "2"

    await SemanticScholarCitations().references(_paper(), limit=5000)
    assert _params(transport.received_url)["limit"] == "100"


async def test_s2_sends_the_api_key_when_set(monkeypatch):
    monkeypatch.setenv("THESISAGENTS_S2_API_KEY", "key-for-test")
    transport = MockTransport(200, '{"data": []}')
    install_mock(monkeypatch, _TARGET, transport)

    await SemanticScholarCitations().references(_paper(), limit=5)

    assert transport.received_headers["x-api-key"] == "key-for-test"


@pytest.mark.parametrize(
    ("status", "body", "error"),
    [
        (404, '{"error": "Paper with id DOI:x not found"}', CitationNotAvailableError),
        (429, "{}", RateLimitError),
        (503, "{}", SourceUnavailableError),
        (400, '{"error": "Unrecognized or unsupported fields"}', ParseError),
        (200, "<html>not json</html>", ParseError),
        (200, "[1, 2]", ParseError),
    ],
)
async def test_http_outcomes_map_to_the_right_error(monkeypatch, status, body, error):
    install_mock(monkeypatch, _TARGET, MockTransport(status, body))

    with pytest.raises(error):
        await SemanticScholarCitations().references(_paper(), limit=5)


# ---------------------------------------------------------------------------
# OpenAlex
# ---------------------------------------------------------------------------


def _openalex_routes(listing: str) -> list[tuple[str, int, str]]:
    return [
        (f"/works/doi:{_DOI}", 200, _fixture("openalex", "resolve_doi.json")),
        ("/works?", 200, _fixture("openalex", listing)),
    ]


async def test_openalex_references_resolves_the_doi_then_lists(monkeypatch):
    transport = RoutingTransport(_openalex_routes("references.json"))
    install_mock(monkeypatch, _TARGET, transport)

    papers = await OpenAlexCitations().references(_paper(), limit=20)

    assert [p.title for p in papers] == [
        "ImageNet classification with deep convolutional neural networks",
        "Automatic differentiation in PyTorch",
        "Taking the Human Out of the Loop: A Review of Bayesian Optimization",
    ]
    assert papers[0].source == "openalex"
    assert papers[0].doi == "10.1145/3065386"
    resolve, listing = transport.requests
    assert resolve.path == f"/works/doi:{_DOI}"
    assert _params(resolve) == {"select": "id"}
    params = _params(listing)
    assert params["filter"] == f"cited_by:{_WORK_ID}"  # works cited BY this one
    assert params["per-page"] == "20"
    assert "sort" not in params
    assert "abstract_inverted_index" in params["select"]


async def test_openalex_cited_by_lists_the_most_cited_citing_works(monkeypatch):
    transport = RoutingTransport(_openalex_routes("cited_by.json"))
    install_mock(monkeypatch, _TARGET, transport)

    papers = await OpenAlexCitations().cited_by(_paper(), limit=20)

    assert papers[0].title == "Deep Neural Networks and Tabular Data: A Survey"
    assert [p.citation_count for p in papers] == sorted(
        (p.citation_count for p in papers), reverse=True
    )
    params = _params(transport.requests[1])
    assert params["filter"] == f"cites:{_WORK_ID}"     # works that CITE this one
    assert params["sort"] == "cited_by_count:desc"


async def test_openalex_record_skips_the_doi_lookup(monkeypatch):
    transport = RoutingTransport([("/works?", 200, _fixture("openalex", "references.json"))])
    install_mock(monkeypatch, _TARGET, transport)

    await OpenAlexCitations().references(
        _paper(source="openalex", source_id="W123", doi=None), limit=5
    )

    assert len(transport.requests) == 1
    assert _params(transport.requests[0])["filter"] == "cited_by:W123"


async def test_openalex_cannot_resolve_a_paper_without_a_doi(monkeypatch):
    """An arXiv-only record: OpenAlex answers 404 for arXiv's own DOIs."""
    transport = RoutingTransport([])
    install_mock(monkeypatch, _TARGET, transport)

    with pytest.raises(CitationNotAvailableError, match="no DOI"):
        await OpenAlexCitations().references(
            _paper(source="arxiv", doi=None, arxiv_id="1706.03762"), limit=5
        )

    assert transport.requests == []


async def test_openalex_unknown_doi_is_not_available(monkeypatch):
    html = "<!doctype html><title>404 Not Found</title>"
    install_mock(monkeypatch, _TARGET, RoutingTransport([("/works/doi:", 404, html)]))

    with pytest.raises(CitationNotAvailableError):
        await OpenAlexCitations().cited_by(_paper(), limit=5)


async def test_openalex_answer_without_an_id_is_not_available(monkeypatch):
    install_mock(monkeypatch, _TARGET, RoutingTransport([("/works/doi:", 200, "{}")]))

    with pytest.raises(CitationNotAvailableError, match="no work ID"):
        await OpenAlexCitations().references(_paper(), limit=5)


async def test_openalex_caps_per_page_and_truncates(monkeypatch):
    transport = RoutingTransport(_openalex_routes("references.json"))
    install_mock(monkeypatch, _TARGET, transport)

    papers = await OpenAlexCitations().references(_paper(), limit=2)
    assert len(papers) == 2

    await OpenAlexCitations().references(_paper(), limit=500)
    assert _params(transport.requests[-1])["per-page"] == "50"


async def test_openalex_joins_the_polite_pool_when_a_contact_is_set(monkeypatch):
    monkeypatch.setenv("THESISAGENTS_CONTACT_EMAIL", "dev@example.org")
    transport = RoutingTransport(_openalex_routes("references.json"))
    install_mock(monkeypatch, _TARGET, transport)

    await OpenAlexCitations().references(_paper(), limit=5)

    assert all(_params(url)["mailto"] == "dev@example.org" for url in transport.requests)


# ---------------------------------------------------------------------------
# Crossref
# ---------------------------------------------------------------------------


def _crossref_routes() -> list[tuple[str, int, str]]:
    return [
        (f"/works/{_DOI}", 200, _fixture("crossref", "work_with_references.json")),
        ("/works?", 200, _fixture("crossref", "references_hydrated.json")),
    ]


async def test_crossref_references_come_back_in_reference_list_order(monkeypatch):
    """Crossref answers the DOI filter in its own order (Vizier first in the
    recording). The provider returns the order of the paper's reference list."""
    transport = RoutingTransport(_crossref_routes())
    install_mock(monkeypatch, _TARGET, transport)

    papers = await CrossrefCitations().references(_paper(), limit=20)

    assert [p.doi for p in papers] == [
        "10.1088/1749-4699/8/1/014008",
        "10.1145/3097983.3098043",
        "10.1162/106365601750190398",
    ]
    assert papers[0].title.startswith("Hyperopt: a Python library")
    assert papers[1].title == "Google Vizier"
    assert papers[0].source == "crossref"
    work, hydrate = transport.requests
    assert work.path == f"/works/{_DOI}"
    params = _params(hydrate)
    assert params["rows"] == "7"   # the 7 references of 29 that carry a DOI
    assert params["filter"].split(",")[0] == "doi:10.1088/1749-4699/8/1/014008"
    assert "doi:10.1109/jproc.2015.2494218" in params["filter"]  # canonical lower case


async def test_crossref_asks_only_for_as_many_dois_as_the_limit(monkeypatch):
    transport = RoutingTransport(_crossref_routes())
    install_mock(monkeypatch, _TARGET, transport)

    papers = await CrossrefCitations().references(_paper(), limit=2)

    params = _params(transport.requests[1])
    assert params["rows"] == "2"
    assert params["filter"] == "doi:10.1088/1749-4699/8/1/014008,doi:10.1145/3097983.3098043"
    assert [p.doi for p in papers] == [
        "10.1088/1749-4699/8/1/014008", "10.1145/3097983.3098043",
    ]


async def test_crossref_work_without_doi_references_makes_one_request(monkeypatch):
    body = json.dumps({"message": {"reference": [{"unstructured": "A. Author. 2020."}]}})
    transport = RoutingTransport([(f"/works/{_DOI}", 200, body)])
    install_mock(monkeypatch, _TARGET, transport)

    assert await CrossrefCitations().references(_paper(), limit=20) == []
    assert len(transport.requests) == 1


async def test_crossref_needs_a_doi(monkeypatch):
    transport = RoutingTransport([])
    install_mock(monkeypatch, _TARGET, transport)

    with pytest.raises(CitationNotAvailableError, match="by DOI"):
        await CrossrefCitations().references(_paper(doi=None), limit=5)

    assert transport.requests == []


async def test_crossref_has_no_citing_works(monkeypatch):
    transport = RoutingTransport([])
    install_mock(monkeypatch, _TARGET, transport)

    with pytest.raises(CitationNotAvailableError, match="not the works citing it"):
        await CrossrefCitations().cited_by(_paper(), limit=5)

    assert transport.requests == []


async def test_crossref_unknown_doi_is_not_available(monkeypatch):
    install_mock(
        monkeypatch, _TARGET,
        RoutingTransport([("/works/", 404, "Resource not found.")]),
    )

    with pytest.raises(CitationNotAvailableError):
        await CrossrefCitations().references(_paper(), limit=5)


async def test_crossref_sends_contact_and_plus_token_when_set(monkeypatch):
    monkeypatch.setenv("THESISAGENTS_CONTACT_EMAIL", "dev@example.org")
    monkeypatch.setenv("THESISAGENTS_CROSSREF_PLUS_TOKEN", "plus-token")
    transport = RoutingTransport(_crossref_routes())
    install_mock(monkeypatch, _TARGET, transport)

    await CrossrefCitations().references(_paper(), limit=5)

    assert all(_params(url)["mailto"] == "dev@example.org" for url in transport.requests)
    assert all(
        headers["Crossref-Plus-API-Token"] == "Bearer plus-token"
        for headers in transport.headers
    )


def test_reference_dois_are_canonical_ordered_and_unique():
    references = [
        {"DOI": "10.1000/B"},
        {"unstructured": "no doi here"},
        {"DOI": "10.1000/a"},
        {"DOI": "https://doi.org/10.1000/b"},   # the first one again
        {"DOI": "not a doi"},
        "a stray string",
    ]

    assert _reference_dois(references) == ["10.1000/b", "10.1000/a"]


def test_the_recorded_reference_list_is_mostly_without_dois():
    """The fact the Crossref provider's docstring states, kept true by a test."""
    work = json.loads(_fixture("crossref", "work_with_references.json"))
    references = work["message"]["reference"]

    assert len(references) == 29
    assert sum(1 for ref in references if ref.get("DOI")) == 7
    assert sum(1 for ref in references if ref.get("article-title")) == 1
