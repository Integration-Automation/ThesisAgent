"""The suite refuses real network traffic.

Guards the autouse ``_block_live_http`` fixture in ``tests/conftest.py``: a
client built the way production code builds one must fail at once instead of
reaching the service, and a client given a mock transport must keep working.
"""

from __future__ import annotations

import httpx
import pytest

from tests.sources._mock import MockTransport
from thesisagents.fetchers import http as http_module


async def test_a_registry_client_cannot_reach_the_network():
    http_module._CLIENTS.clear()  # noqa: SLF001  # start from an empty registry
    client = await http_module.get_client("arxiv")
    try:
        with pytest.raises(httpx.ConnectError, match="live HTTP is blocked in tests"):
            await client.get("https://export.arxiv.org/api/query")
    finally:
        await http_module.shutdown_clients()


def test_a_plain_sync_client_cannot_reach_the_network():
    with (
        httpx.Client() as client,
        pytest.raises(httpx.ConnectError, match="live HTTP is blocked in tests"),
    ):
        client.get("https://example.org/")


async def test_a_mock_transport_still_answers():
    transport = MockTransport(200, '{"ok": true}')
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("https://example.org/data")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert str(transport.received_url) == "https://example.org/data"
