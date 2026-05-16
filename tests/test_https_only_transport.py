"""The HTTPS-only transport must refuse plain HTTP requests."""

from __future__ import annotations

import httpx
import pytest

from autopapertoppt.fetchers.http import HttpsOnlyTransport


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
