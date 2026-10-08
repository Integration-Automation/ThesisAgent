"""Export preflight: DOI / URL verification before any exporter runs.

Every test here drives the real resolver (``real_identifier_preflight``
marker) against :class:`RoutingTransport`, which answers from a table of
canned responses and fails the test on any request it was not told about. No
live HTTP.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections import Counter

import httpx
import pytest

from thesisagents.core import export_validation as ev
from thesisagents.core.export_validation import (
    KIND_DOI,
    KIND_URL,
    IdentifierVerificationError,
    MemoryVerificationCache,
    Verdict,
    VerificationStatus,
    verify_collection,
    verify_collection_blocking,
)
from thesisagents.core.models import ExportOptions, Paper, PaperCollection, Query
from thesisagents.exporters import export_collection

pytestmark = pytest.mark.real_identifier_preflight

_HANDLE = "https://doi.org/api/handles/"


def _handle_found(landing: str = "https://publisher.example/paper") -> tuple[int, dict, bytes]:
    body = {
        "responseCode": 1,
        "handle": "x",
        "values": [
            {"index": 100, "type": "HS_ADMIN", "data": {"format": "admin", "value": {}}},
            {"index": 1, "type": "URL", "data": {"format": "string", "value": landing}},
        ],
    }
    return (200, {}, json.dumps(body).encode())


def _handle_missing() -> tuple[int, dict, bytes]:
    return (404, {}, json.dumps({"responseCode": 100, "handle": "x"}).encode())


def _status(code: int, **headers: str) -> tuple[int, dict, bytes]:
    return (code, headers, b"")


class RoutingTransport(httpx.AsyncBaseTransport):
    """Answer each URL from ``routes`` and record what was asked.

    A route value is ``(status, headers, body)``, an exception instance to
    raise, or a list of those consumed one per request (for retry tests).
    ``delay`` makes each request take that long so concurrency can be measured.
    """

    def __init__(self, routes: dict[str, object], *, delay: float = 0.0) -> None:
        self._routes = routes
        self._delay = delay
        self.calls: list[str] = []
        self.in_flight = 0
        self.peak = 0
        self._host_in_flight: Counter[str] = Counter()
        self.host_peak: Counter[str] = Counter()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        host = request.url.host
        self.calls.append(url)
        self.in_flight += 1
        self._host_in_flight[host] += 1
        self.peak = max(self.peak, self.in_flight)
        self.host_peak[host] = max(self.host_peak[host], self._host_in_flight[host])
        try:
            if self._delay:
                await asyncio.sleep(self._delay)
            return self._answer(url, request)
        finally:
            self.in_flight -= 1
            self._host_in_flight[host] -= 1

    def _answer(self, url: str, request: httpx.Request) -> httpx.Response:
        if url not in self._routes:
            raise AssertionError(f"unexpected request: {url}")
        spec = self._routes[url]
        if isinstance(spec, list):
            spec = spec.pop(0) if len(spec) > 1 else spec[0]
        if isinstance(spec, Exception):
            raise spec
        status, headers, body = spec
        return httpx.Response(status, headers=headers, content=body, request=request)

    async def aclose(self) -> None:
        return None


@pytest.fixture()
def route(monkeypatch):
    """Install a :class:`RoutingTransport` as the preflight's client."""

    def _install(routes: dict[str, object], *, delay: float = 0.0) -> RoutingTransport:
        transport = RoutingTransport(routes, delay=delay)

        @contextlib.asynccontextmanager
        async def fake_scoped_client(_source: str):
            async with httpx.AsyncClient(transport=transport) as client:
                yield client

        monkeypatch.setattr(ev, "scoped_client", fake_scoped_client)
        return transport

    return _install


def _paper(key: str = "p1", **overrides) -> Paper:
    fields = {
        "source": "arxiv",
        "source_id": key,
        "title": f"Paper {key} about verification",
        "authors": (f"Author {key.capitalize()}",),
        "year": 2024,
        "venue": None,
        "abstract": "",
        "url": "",
    }
    fields.update(overrides)
    return Paper(**fields)


def _collection(*papers: Paper) -> PaperCollection:
    query = Query(keywords="verification", sources=("arxiv",), max_results=10)
    return PaperCollection(query=query, papers=tuple(papers))


def _by_kind(report, kind: str):
    return next(check for check in report.checks if check.kind == kind)


# ---------------------------------------------------------------------------
# Roadmap cases
# ---------------------------------------------------------------------------


async def test_valid_url_and_valid_doi_pass(route):
    transport = route(
        {
            _HANDLE + "10.1234/good": _handle_found(),
            "https://example.org/paper": _status(200),
        }
    )
    paper = _paper(doi="10.1234/good", url="https://example.org/paper")

    report = await verify_collection(_collection(paper))

    assert report.ok
    assert [check.status for check in report.checks] == [VerificationStatus.OK] * 2
    assert sorted(transport.calls) == sorted(
        [_HANDLE + "10.1234/good", "https://example.org/paper"]
    )


async def test_malformed_doi_fails_without_a_network_request(route):
    transport = route({})

    report = await verify_collection(_collection(_paper(doi="10.x/not-a-doi")))

    assert transport.calls == []
    check = _by_kind(report, KIND_DOI)
    assert check.status is VerificationStatus.INVALID
    assert "10.<registrant>/<suffix>" in check.detail
    assert not report.ok


async def test_redirect_is_accepted_and_the_supplied_url_is_preserved(route):
    route(
        {
            "https://old.example/p": _status(301, location="https://new.example/p"),
            "https://new.example/p": _status(200),
        }
    )
    paper = _paper(url="https://old.example/p")

    report = await verify_collection(_collection(paper))

    check = _by_kind(report, KIND_URL)
    assert check.status is VerificationStatus.OK
    assert check.value == "https://old.example/p"          # what the paper cites
    assert check.resolved_url == "https://new.example/p"   # where it leads today
    assert paper.url == "https://old.example/p"            # the record is untouched


async def test_doi_landing_page_is_reported_separately_from_the_doi(route):
    route({_HANDLE + "10.1234/good": _handle_found("https://dl.example/abs/42")})
    paper = _paper(doi="10.1234/GOOD")

    report = await verify_collection(_collection(paper))

    check = _by_kind(report, KIND_DOI)
    assert check.value == "10.1234/GOOD"
    assert check.resolved_url == "https://dl.example/abs/42"
    assert paper.doi == "10.1234/GOOD"


async def test_timeout_is_reported_distinctly(route):
    transport = route({"https://slow.example/p": httpx.ReadTimeout("too slow")})

    report = await verify_collection(_collection(_paper(url="https://slow.example/p")))

    check = _by_kind(report, KIND_URL)
    assert check.status is VerificationStatus.TIMEOUT
    assert check.status is not VerificationStatus.UNREACHABLE
    assert "no answer within" in check.detail
    assert len(transport.calls) == ev._ATTEMPTS  # noqa: SLF001  # one retry, then give up


def test_one_invalid_paper_blocks_a_strict_export(route, tmp_path):
    route(
        {
            _HANDLE + "10.1234/good": _handle_found(),
            _HANDLE + "10.1234/typo": _handle_missing(),
        }
    )
    collection = _collection(
        _paper("good", doi="10.1234/good"), _paper("bad", doi="10.1234/typo")
    )
    options = ExportOptions(formats=("bib", "json"), out_dir=str(tmp_path))

    with pytest.raises(IdentifierVerificationError) as raised:
        export_collection(collection, options)

    report = raised.value.report
    assert [check.value for check in report.failures] == ["10.1234/typo"]
    assert report.failures[0].paper_key == _paper("bad").bibtex_key()
    message = str(raised.value)
    assert "10.1234/typo is invalid" in message
    assert "--no-verify-identifiers" in message
    assert "verify_identifiers=False" in message
    assert list(tmp_path.iterdir()) == []  # nothing was written


def test_opt_out_allows_the_export_and_says_so(route, tmp_path, caplog):
    transport = route({})
    collection = _collection(_paper(doi="10.x/not-a-doi", url="https://gone.example/"))
    options = ExportOptions(
        formats=("bib",), out_dir=str(tmp_path), verify_identifiers=False
    )

    with caplog.at_level(logging.WARNING, logger="thesisagents.exporters"):
        written = export_collection(collection, options)

    assert written["bib"].exists()
    assert transport.calls == []
    assert "identifier verification is OFF" in caplog.text


async def test_probes_are_bounded_and_the_report_is_deterministic(route):
    papers = [
        _paper(f"p{i}", doi=f"10.1234/d{i}", url=f"https://host{i % 3}.example/{i}")
        for i in range(12)
    ]
    routes: dict[str, object] = {}
    for i in range(12):
        routes[_HANDLE + f"10.1234/d{i}"] = _handle_found()
        routes[f"https://host{i % 3}.example/{i}"] = _status(200)
    transport = route(routes, delay=0.01)

    first = await verify_collection(_collection(*papers))
    second = await verify_collection(_collection(*papers))

    assert first == second
    assert [check.value for check in first.checks][:2] == [
        "10.1234/d0", "https://host0.example/0"
    ]
    assert 1 < transport.peak <= ev._CONCURRENCY  # noqa: SLF001
    assert max(transport.host_peak.values()) <= ev._PER_HOST_CONCURRENCY  # noqa: SLF001


# ---------------------------------------------------------------------------
# DOI resolution
# ---------------------------------------------------------------------------


async def test_unregistered_doi_is_invalid(route):
    route({_HANDLE + "10.1234/nope": _handle_missing()})

    report = await verify_collection(_collection(_paper(doi="10.1234/nope")))

    check = _by_kind(report, KIND_DOI)
    assert check.status is VerificationStatus.INVALID
    assert "no such DOI" in check.detail


async def test_registered_doi_without_a_landing_url_is_ok(route):
    body = json.dumps({"responseCode": 200, "handle": "x"}).encode()
    route({_HANDLE + "10.1234/bare": (404, {}, body)})

    report = await verify_collection(_collection(_paper(doi="10.1234/bare")))

    assert _by_kind(report, KIND_DOI).status is VerificationStatus.OK


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, VerificationStatus.INVALID),
        (429, VerificationStatus.SKIPPED),
        (503, VerificationStatus.UNREACHABLE),
    ],
)
async def test_doi_resolver_status_codes(route, status, expected):
    route({_HANDLE + "10.1234/x": _status(status)})

    report = await verify_collection(_collection(_paper(doi="10.1234/x")))

    assert _by_kind(report, KIND_DOI).status is expected


async def test_doi_org_url_is_checked_as_the_doi_it_names(route):
    transport = route({_HANDLE + "10.1234/good": _handle_found()})
    paper = _paper(doi="10.1234/good", url="https://doi.org/10.1234/GOOD")

    report = await verify_collection(_collection(paper))

    assert report.ok
    assert transport.calls == [_HANDLE + "10.1234/good"]  # one lookup serves both
    assert _by_kind(report, KIND_URL).value == "https://doi.org/10.1234/GOOD"


async def test_doi_with_reserved_characters_is_percent_encoded(route):
    transport = route({_HANDLE + "10.1234/a%23b%3Fc": _handle_found()})

    report = await verify_collection(_collection(_paper(doi="10.1234/a#b?c")))

    assert report.ok
    assert transport.calls == [_HANDLE + "10.1234/a%23b%3Fc"]


# ---------------------------------------------------------------------------
# URL probing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (200, VerificationStatus.OK),
        (404, VerificationStatus.INVALID),
        (410, VerificationStatus.INVALID),
        (401, VerificationStatus.SKIPPED),
        (403, VerificationStatus.SKIPPED),
        (429, VerificationStatus.SKIPPED),
        (500, VerificationStatus.UNREACHABLE),
    ],
)
async def test_url_status_codes(route, status, expected):
    route({"https://example.org/p": _status(status)})

    report = await verify_collection(_collection(_paper(url="https://example.org/p")))

    assert _by_kind(report, KIND_URL).status is expected


async def test_a_refusing_server_does_not_block_the_export(route):
    route({"https://walled.example/p": _status(403)})

    report = await verify_collection(_collection(_paper(url="https://walled.example/p")))

    assert report.ok
    assert "refuses automated access" in _by_kind(report, KIND_URL).detail


async def test_connection_failure_is_unreachable(route):
    transport = route({"https://nxdomain.example/p": httpx.ConnectError("no such host")})

    report = await verify_collection(
        _collection(_paper(url="https://nxdomain.example/p"))
    )

    check = _by_kind(report, KIND_URL)
    assert check.status is VerificationStatus.UNREACHABLE
    assert "ConnectError" in check.detail
    assert len(transport.calls) == ev._ATTEMPTS  # noqa: SLF001


async def test_a_transient_failure_is_retried_once(route):
    transport = route(
        {"https://flaky.example/p": [httpx.ConnectError("reset"), _status(200)]}
    )

    report = await verify_collection(_collection(_paper(url="https://flaky.example/p")))

    assert report.ok
    assert len(transport.calls) == 2


async def test_a_definite_answer_is_not_retried(route):
    transport = route({"https://example.org/gone": _status(404)})

    await verify_collection(_collection(_paper(url="https://example.org/gone")))

    assert len(transport.calls) == 1


async def test_browser_only_publisher_url_is_never_requested(route):
    transport = route({_HANDLE + "10.1145/abc": _handle_found()})
    paper = _paper(doi="10.1145/abc", url="https://dl.acm.org/doi/10.1145/abc")

    report = await verify_collection(_collection(paper))

    assert transport.calls == [_HANDLE + "10.1145/abc"]
    check = _by_kind(report, KIND_URL)
    assert check.status is VerificationStatus.SKIPPED
    assert "DOI check covers" in check.detail
    assert report.ok


async def test_browser_only_publisher_url_without_a_doi_is_skipped(route):
    transport = route({})

    report = await verify_collection(
        _collection(_paper(url="https://ieeexplore.ieee.org/document/123"))
    )

    assert transport.calls == []
    check = _by_kind(report, KIND_URL)
    assert check.status is VerificationStatus.SKIPPED
    assert "no DOI to check" in check.detail


async def test_redirect_to_a_publisher_page_is_not_followed(route):
    transport = route(
        {
            "https://hdl.example/1": _status(
                302, location="https://ieeexplore.ieee.org/document/9"
            )
        }
    )

    report = await verify_collection(_collection(_paper(url="https://hdl.example/1")))

    check = _by_kind(report, KIND_URL)
    assert check.status is VerificationStatus.OK
    assert check.resolved_url == "https://ieeexplore.ieee.org/document/9"
    assert "browser-only" in check.detail
    assert transport.calls == ["https://hdl.example/1"]


async def test_redirect_to_plain_http_is_not_followed(route):
    transport = route(
        {"https://example.org/p": _status(301, location="http://example.org/p2")}
    )

    report = await verify_collection(_collection(_paper(url="https://example.org/p")))

    check = _by_kind(report, KIND_URL)
    assert check.status is VerificationStatus.OK
    assert check.resolved_url == "http://example.org/p2"
    assert "non-https" in check.detail
    assert transport.calls == ["https://example.org/p"]


async def test_relative_redirect_is_resolved_against_the_current_url(route):
    route(
        {
            "https://example.org/a/b": _status(302, location="../c"),
            "https://example.org/c": _status(200),
        }
    )

    report = await verify_collection(_collection(_paper(url="https://example.org/a/b")))

    assert _by_kind(report, KIND_URL).resolved_url == "https://example.org/c"


async def test_a_redirect_loop_ends_as_unreachable(route):
    route({"https://loop.example/p": _status(302, location="https://loop.example/p")})

    report = await verify_collection(_collection(_paper(url="https://loop.example/p")))

    check = _by_kind(report, KIND_URL)
    assert check.status is VerificationStatus.UNREACHABLE
    assert "redirects" in check.detail


async def test_plain_http_url_is_verified_through_its_https_form(route):
    transport = route({"https://example.org/p?x=1": _status(200)})
    paper = _paper(url="http://example.org/p?x=1")

    report = await verify_collection(_collection(paper))

    check = _by_kind(report, KIND_URL)
    assert check.status is VerificationStatus.OK
    assert check.value == "http://example.org/p?x=1"
    assert "https form" in check.detail
    assert transport.calls == ["https://example.org/p?x=1"]


async def test_plain_http_url_with_a_dead_https_form_is_skipped_not_failed(route):
    route({"https://httponly.example/p": httpx.ConnectError("refused")})

    report = await verify_collection(
        _collection(_paper(url="http://httponly.example/p"))
    )

    check = _by_kind(report, KIND_URL)
    assert check.status is VerificationStatus.SKIPPED
    assert report.ok


async def test_plain_http_url_whose_https_form_is_404_is_invalid(route):
    route({"https://example.org/missing": _status(404)})

    report = await verify_collection(
        _collection(_paper(url="http://example.org/missing"))
    )

    assert _by_kind(report, KIND_URL).status is VerificationStatus.INVALID


@pytest.mark.parametrize(
    ("url", "status"),
    [
        ("file:///C:/papers/x.pdf", VerificationStatus.SKIPPED),
        ("ftp://example.org/x", VerificationStatus.SKIPPED),
        ("https:///no-host", VerificationStatus.INVALID),
    ],
)
async def test_urls_decided_without_a_request(route, url, status):
    transport = route({})

    report = await verify_collection(_collection(_paper(url=url)))

    assert transport.calls == []
    assert _by_kind(report, KIND_URL).status is status


async def test_a_paper_without_identifiers_adds_no_checks(route):
    transport = route({})

    report = await verify_collection(_collection(_paper(url="", doi=None)))

    assert report.checks == ()
    assert report.ok
    assert transport.calls == []


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


async def test_duplicate_identifiers_are_probed_once(route):
    transport = route({_HANDLE + "10.1234/same": _handle_found()})
    collection = _collection(
        _paper("a", doi="10.1234/same"), _paper("b", doi="10.1234/SAME")
    )

    report = await verify_collection(collection)

    assert len(report.checks) == 2
    assert transport.calls == [_HANDLE + "10.1234/same"]


async def test_a_shared_cache_avoids_repeat_requests(route):
    transport = route(
        {
            _HANDLE + "10.1234/good": _handle_found(),
            "https://example.org/p": _status(200),
        }
    )
    collection = _collection(_paper(doi="10.1234/good", url="https://example.org/p"))
    cache = MemoryVerificationCache()

    first = await verify_collection(collection, cache=cache)
    second = await verify_collection(collection, cache=cache)

    assert first == second
    assert len(transport.calls) == 2
    assert len(cache) == 2
    assert cache.get(KIND_DOI, "10.1234/good").status is VerificationStatus.OK


def test_export_collection_reuses_the_callers_cache(route, tmp_path):
    transport = route({_HANDLE + "10.1234/good": _handle_found()})
    collection = _collection(_paper(doi="10.1234/good"))
    cache = MemoryVerificationCache()
    options = ExportOptions(formats=("bib",), out_dir=str(tmp_path), filename_stem="a")

    export_collection(collection, options, verification_cache=cache)
    export_collection(collection, options, verification_cache=cache)

    assert len(transport.calls) == 1


def test_a_cached_verdict_is_served_without_a_client(monkeypatch):
    def _no_client(_source: str):
        raise AssertionError("the cache should have answered")

    monkeypatch.setattr(ev, "scoped_client", _no_client)
    cache = MemoryVerificationCache()
    cache.put(KIND_DOI, "10.1234/known", Verdict(VerificationStatus.OK))

    report = verify_collection_blocking(
        _collection(_paper(doi="10.1234/known")), cache=cache
    )

    assert report.ok


# ---------------------------------------------------------------------------
# Synchronous entry point
# ---------------------------------------------------------------------------


def test_blocking_verify_works_without_an_event_loop(route):
    route({_HANDLE + "10.1234/good": _handle_found()})

    report = verify_collection_blocking(_collection(_paper(doi="10.1234/good")))

    assert report.ok


async def test_blocking_verify_works_inside_a_running_event_loop(route):
    """The CLI and the MCP ``export`` tool both call it from a coroutine."""
    route({_HANDLE + "10.1234/good": _handle_found()})

    report = verify_collection_blocking(_collection(_paper(doi="10.1234/good")))

    assert report.ok


# ---------------------------------------------------------------------------
# Report + export wiring
# ---------------------------------------------------------------------------


async def test_report_serialises_every_check(route):
    route(
        {
            _HANDLE + "10.1234/typo": _handle_missing(),
            "https://example.org/p": _status(200),
        }
    )
    paper = _paper(doi="10.1234/typo", url="https://example.org/p")

    payload = (await verify_collection(_collection(paper))).to_dict()

    assert payload["ok"] is False
    assert payload["counts"] == {
        "ok": 1, "invalid": 1, "unreachable": 0, "timeout": 0, "skipped": 0,
    }
    assert payload["checks"][0] == {
        "paper_key": paper.bibtex_key(),
        "title": paper.title,
        "kind": "doi",
        "value": "10.1234/typo",
        "status": "invalid",
        "resolved_url": None,
        "detail": "doi.org has no such DOI registered",
    }
    json.dumps(payload)  # must be JSON-serialisable for the MCP response


def test_unknown_format_is_rejected_before_the_preflight(route, tmp_path):
    from thesisagents.core.exceptions import ExportError

    transport = route({})
    options = ExportOptions(formats=("bib", "nope"), out_dir=str(tmp_path))

    with pytest.raises(ExportError, match="no exporter registered"):
        export_collection(_collection(_paper(doi="10.1234/good")), options)

    assert transport.calls == []
    assert list(tmp_path.iterdir()) == []


def test_verification_error_is_an_export_error(route, tmp_path):
    from thesisagents.core.exceptions import ExportError, ThesisAgentsError

    route({})
    options = ExportOptions(formats=("bib",), out_dir=str(tmp_path))

    with pytest.raises(ExportError) as raised:
        export_collection(_collection(_paper(doi="not-a-doi")), options)

    assert isinstance(raised.value, IdentifierVerificationError)
    assert isinstance(raised.value, ThesisAgentsError)  # the CLI turns it into exit 2


def test_long_transport_errors_are_clipped():
    clipped = ev._clip("x" * 500)  # noqa: SLF001

    assert len(clipped) == ev._DETAIL_MAX_CHARS  # noqa: SLF001
    assert clipped.endswith("…")
    assert ev._clip("two\n  lines") == "two lines"  # noqa: SLF001


async def test_a_cache_only_run_does_not_log_at_info(route, caplog):
    """The CLI exports once per paper after the first check. Each of those
    calls reads the cache, and an INFO line per call would bury the one that
    reports real work."""
    route({_HANDLE + "10.1234/good": _handle_found()})
    collection = _collection(_paper(doi="10.1234/good"))
    cache = MemoryVerificationCache()

    with caplog.at_level(logging.DEBUG, logger="thesisagents.core.export_validation"):
        await verify_collection(collection, cache=cache)
        await verify_collection(collection, cache=cache)

    preflight = [r for r in caplog.records if "identifier preflight" in r.getMessage()]
    assert [r.levelno for r in preflight] == [logging.INFO, logging.DEBUG]
    assert "1 probed" in preflight[0].getMessage()
    assert "0 probed" in preflight[1].getMessage()


async def test_a_cached_failure_is_still_logged_at_info(route, caplog):
    route({_HANDLE + "10.1234/typo": _handle_missing()})
    collection = _collection(_paper(doi="10.1234/typo"))
    cache = MemoryVerificationCache()

    with caplog.at_level(logging.DEBUG, logger="thesisagents.core.export_validation"):
        await verify_collection(collection, cache=cache)
        await verify_collection(collection, cache=cache)

    preflight = [r for r in caplog.records if "identifier preflight" in r.getMessage()]
    assert [r.levelno for r in preflight] == [logging.INFO, logging.INFO]
