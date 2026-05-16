"""Shared HTTP / rate-limit / Fetcher base classes used by every source plugin."""

from autopapertoppt.fetchers.base import Fetcher, FetcherConfig
from autopapertoppt.fetchers.http import HttpsOnlyTransport, get_client, shutdown_clients
from autopapertoppt.fetchers.rate_limit import RateLimit, TokenBucket

__all__ = [
    "Fetcher",
    "FetcherConfig",
    "HttpsOnlyTransport",
    "RateLimit",
    "TokenBucket",
    "get_client",
    "shutdown_clients",
]
