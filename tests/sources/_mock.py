"""Shared mock-transport helpers for source-plugin tests."""

from __future__ import annotations

import httpx

from thesisagents.fetchers import http as http_module


class MockTransport(httpx.AsyncBaseTransport):
    """Return a canned response for every request and record the last URL."""

    def __init__(self, status: int, body: str | bytes) -> None:
        self._status = status
        self._body = body.encode("utf-8") if isinstance(body, str) else body
        self.received_url: httpx.URL | None = None
        self.received_method: str | None = None
        self.received_body: bytes | None = None

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.received_url = request.url
        self.received_method = request.method
        self.received_body = bytes(request.content) if request.content else None
        return httpx.Response(self._status, content=self._body, request=request)

    async def aclose(self) -> None:
        return None


def install_mock(monkeypatch, target_module_path: str, transport: MockTransport) -> None:
    """Monkeypatch ``get_client`` inside the named module to return a client
    wired to ``transport``. The shared client registry is cleared so the
    mock is observed."""
    http_module._CLIENTS.clear()  # noqa: SLF001  # tests reach into the registry on purpose

    async def fake_get_client(_source: str) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=transport)

    monkeypatch.setattr(f"{target_module_path}.get_client", fake_get_client)
