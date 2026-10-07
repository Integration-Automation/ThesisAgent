"""The HTTPS-only transport must refuse plain HTTP requests."""

from __future__ import annotations

import httpx
import pytest

from thesisagents.fetchers.http import HttpsOnlyTransport


class _PassthroughTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request):
        return httpx.Response(200, content=b"ok")

    async def aclose(self):
        return None


async def test_rejects_http():
    transport = HttpsOnlyTransport(_PassthroughTransport())
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(httpx.RequestError):
            await client.get("http://example.com/path")


async def test_accepts_https():
    transport = HttpsOnlyTransport(_PassthroughTransport())
    async with httpx.AsyncClient(transport=transport) as client:
        resp = await client.get("https://example.com/path")
    assert resp.status_code == 200


async def test_scoped_client_refuses_plain_http_and_stays_out_of_the_registry():
    """``scoped_client`` must keep the HTTPS-only guarantee of ``get_client``
    while never registering the client it hands out."""
    from thesisagents.fetchers import http as http_module

    http_module._CLIENTS.clear()  # noqa: SLF001  # start from an empty registry
    async with http_module.scoped_client("identifier_preflight") as client:
        assert isinstance(client._transport, HttpsOnlyTransport)  # noqa: SLF001
        assert client.headers["User-Agent"].startswith("ThesisAgents/")
        with pytest.raises(httpx.RequestError, match="refusing non-HTTPS"):
            await client.get("http://example.com/path")
        assert http_module._CLIENTS == {}  # noqa: SLF001
    assert client.is_closed


async def test_scoped_client_is_closed_when_the_block_raises():
    from thesisagents.fetchers import http as http_module

    with pytest.raises(RuntimeError, match="boom"):
        async with http_module.scoped_client("identifier_preflight") as client:
            raise RuntimeError("boom")
    assert client.is_closed
