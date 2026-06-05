"""Shared HTTP / rate-limit / Fetcher base classes used by every source plugin."""

from thesisagents.fetchers.base import Fetcher, FetcherConfig
from thesisagents.fetchers.http import HttpsOnlyTransport, get_client, shutdown_clients
from thesisagents.fetchers.rate_limit import RateLimit, TokenBucket

__all__ = [
    "Fetcher",
    "FetcherConfig",
    "HttpsOnlyTransport",
    "RateLimit",
    "TokenBucket",
    "get_client",
    "shutdown_clients",
]
