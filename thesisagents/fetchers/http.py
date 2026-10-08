"""HTTPS-only shared HTTP client registry.

All outbound HTTP goes through `get_client(source)`. The transport rejects any
non-HTTPS request (including redirect targets) so a misconfigured endpoint or a
malicious redirect cannot exfiltrate over plain HTTP.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

from thesisagents.core.constants import HTTP_TIMEOUT_SECONDS
from thesisagents.utils.logging import get_logger

_LOG = get_logger(__name__)


class HttpsOnlyTransport(httpx.AsyncBaseTransport):
    """Wrap an underlying transport and reject non-HTTPS requests."""

    def __init__(self, inner: httpx.AsyncBaseTransport) -> None:
        self._inner = inner

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        scheme = request.url.scheme
        if scheme != "https":
            raise httpx.RequestError(
                f"refusing non-HTTPS request to {request.url}",
                request=request,
            )
        return await self._inner.handle_async_request(request)

    async def aclose(self) -> None:
        await self._inner.aclose()


@dataclass(frozen=True, slots=True)
class _ClientKey:
    source: str


_CLIENTS: dict[_ClientKey, httpx.AsyncClient] = {}
_LOCK = asyncio.Lock()


_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

# Sources that are scraped from human-facing pages must look like a browser
# or the upstream returns 403 / 418. The HTTPS-only + rate-limit guardrails
# still apply.
_BROWSER_UA_SOURCES = frozenset({"ieee", "scholar"})


def _user_agent_for(source: str) -> str:
    if source in _BROWSER_UA_SOURCES:
        return _BROWSER_UA
    return (
        f"ThesisAgents/0.1 (+source={source}; "
        "contact=set THESISAGENTS_CONTACT)"
    )


def _build_client(source: str) -> httpx.AsyncClient:
    inner = httpx.AsyncHTTPTransport(retries=0)
    transport = HttpsOnlyTransport(inner)
    return httpx.AsyncClient(
        transport=transport,
        timeout=HTTP_TIMEOUT_SECONDS,
        follow_redirects=True,
        headers={
            "User-Agent": _user_agent_for(source),
            "Accept-Encoding": "gzip, deflate",
        },
    )


async def get_client(source: str) -> httpx.AsyncClient:
    """Return the per-source shared async client, lazily constructed."""
    key = _ClientKey(source=source)
    client = _CLIENTS.get(key)
    if client is not None:
        return client
    async with _LOCK:
        client = _CLIENTS.get(key)
        if client is None:
            client = _build_client(source)
            _CLIENTS[key] = client
            _LOG.debug("Constructed HTTP client for source=%s", source)
    return client


@contextlib.asynccontextmanager
async def scoped_client(source: str) -> AsyncIterator[httpx.AsyncClient]:
    """An HTTPS-only client that lives for one ``async with`` block.

    Same transport, timeout and User-Agent rules as :func:`get_client`, but the
    client is not put in the shared registry and is closed when the block ends.

    Why it exists: a registry client belongs to the event loop that created
    it. Code that may run on a private, short-lived loop (the export preflight
    under ``run_blocking``, which starts a fresh loop per call) would leave a
    client in the registry bound to a loop that has already closed, and the
    next caller would fail with ``Event loop is closed``.

    Example::

        async with scoped_client("identifier_preflight") as client:
            response = await client.get("https://doi.org/api/handles/10.1/x")

    Anti-pattern: ``httpx.AsyncClient()`` built by hand for the same purpose.
    That skips the HTTPS-only transport, which is the guarantee every outbound
    request in this package relies on.
    """
    client = _build_client(source)
    try:
        yield client
    finally:
        await client.aclose()


async def shutdown_clients() -> None:
    """Close all shared clients. Call from app shutdown / CLI exit.

    Tolerates clients whose original event loop has already closed —
    that happens in the test suite where each ``asyncio.run`` spins
    its own loop, and a client cached during an earlier test cannot
    be re-closed in a later loop's context. We drop those clients
    from the registry; the OS will reclaim the dangling sockets.
    """
    async with _LOCK:
        clients = list(_CLIENTS.values())
        _CLIENTS.clear()
    for client in clients:
        try:
            await client.aclose()
        except RuntimeError as err:
            # "Event loop is closed" / "got Future <...> attached to a
            # different loop" — the client outlived its loop. Nothing
            # we can do at this point that's safer than letting GC
            # reap the connection pool.
            _LOG.debug("client.aclose() raised %r; dropping silently", err)
