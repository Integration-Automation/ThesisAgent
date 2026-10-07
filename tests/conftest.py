"""Shared fixtures for the ThesisAgents test suite."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

#: pytest rewrites its own ``PYTEST_CURRENT_TEST`` marker between the setup,
#: call and teardown phases, so restoring it would fight the runner.
_RUNNER_OWNED_PREFIX = "PYTEST_"


@pytest.fixture(autouse=True)
def _block_live_http(monkeypatch):
    """Refuse every request that would open a real socket.

    The boundary this guards: "no live HTTP in tests". A test that forgets to
    install a mock transport used to reach the real service, because the
    pipeline swallows per-source and per-paper network errors by design. The
    call then passed or failed with the network instead of with the code.

    Failure mode it prevents: four tests looked up DOIs and titles at Semantic
    Scholar and arXiv for real (``tests/test_pipeline.py`` through the OA
    resolver, ``test_cli_rejects_doi_identifier_until_resolver_lands``,
    ``test_resolve_falls_back_to_arxiv_when_unpaywall_misses``). They passed,
    slowly, and would hang on a host where those calls stall.

    How: the real transports are patched to raise ``httpx.ConnectError``, the
    error an offline machine produces, so the code under test takes its normal
    "source unreachable" branch at once. A test that passes its own transport
    to ``httpx.AsyncClient`` (``tests/sources/_mock.py``) never reaches these
    two methods and is unaffected.

    Example: ``await get_client("arxiv")`` followed by ``client.get(...)``
    raises ``ConnectError("live HTTP is blocked in tests: GET https://…")``.
    """

    def _refusal(request: httpx.Request) -> httpx.ConnectError:
        return httpx.ConnectError(
            f"live HTTP is blocked in tests: {request.method} {request.url}",
            request=request,
        )

    async def _refuse_async(_self, request: httpx.Request) -> httpx.Response:
        raise _refusal(request)

    def _refuse_sync(_self, request: httpx.Request) -> httpx.Response:
        raise _refusal(request)

    monkeypatch.setattr(
        httpx.AsyncHTTPTransport, "handle_async_request", _refuse_async
    )
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _refuse_sync)


@pytest.fixture(autouse=True)
def _restore_environment():
    """Put ``os.environ`` back exactly as the test found it.

    The boundary this guards: application code that writes the process
    environment directly. The GUI Settings page mirrors every saved field into
    ``os.environ`` (``thesisagents/gui/pages/settings.py``), and
    ``monkeypatch.delenv(name, raising=False)`` registers no undo when the
    variable was absent beforehand, so the value outlives the test.

    Failure mode it prevents: ``tests/gui`` runs first and left
    ``ANTHROPIC_API_KEY`` set, so every later CLI test took the auto-enrich
    branch and made live HTTPS calls (a PDF download plus an API request with a
    fake key). The suite stopped being hermetic, and on a host where those
    calls stall ``tests/test_cli.py::test_cli_runs_end_to_end`` hung for
    minutes. See ``tests/test_env_isolation.py`` for the regression test.

    Example: a test that calls ``SettingsPage.trigger_save()`` with a key typed
    in no longer changes what the next test reads from ``os.environ``.
    """
    snapshot = dict(os.environ)
    yield
    for name in set(os.environ) - set(snapshot):
        if not name.startswith(_RUNNER_OWNED_PREFIX):
            del os.environ[name]
    for name, value in snapshot.items():
        if name.startswith(_RUNNER_OWNED_PREFIX):
            continue
        if os.environ.get(name) != value:
            os.environ[name] = value


@pytest.fixture()
def sample_papers():
    from thesisagents.core.models import Paper

    return [
        Paper(
            source="arxiv",
            source_id="2401.00001v1",
            title="Sample Paper on Attention",
            authors=("Alice Anderson", "Bob Brown"),
            year=2024,
            venue=None,
            abstract="A short abstract about attention mechanisms.",
            url="https://arxiv.org/abs/2401.00001v1",
            arxiv_id="2401.00001",
            pdf_url="https://arxiv.org/pdf/2401.00001v1",
        ),
        Paper(
            source="arxiv",
            source_id="2305.99999v2",
            title="Second Paper with Special & Chars",
            authors=("Carol Chen",),
            year=2023,
            venue="NeurIPS 2023",
            abstract="Second abstract. Includes math like $x^2$ and curly {braces}.",
            url="https://arxiv.org/abs/2305.99999v2",
            doi="10.1234/example.99999",
            arxiv_id="2305.99999",
        ),
    ]


@pytest.fixture()
def arxiv_fixture_path():
    return Path(__file__).resolve().parent / "fixtures" / "arxiv" / "attention.xml"
