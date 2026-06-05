"""Token bucket pacing."""

from __future__ import annotations

import time

from thesisagents.fetchers.rate_limit import RateLimit, TokenBucket


async def test_token_bucket_paces_requests():
    bucket = TokenBucket(RateLimit(requests_per_second=10.0, burst=1))
    start = time.monotonic()
    for _ in range(3):
        await bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.18  # 2 waits of ~0.1s after the initial token


async def test_token_bucket_burst():
    bucket = TokenBucket(RateLimit(requests_per_second=1.0, burst=3))
    start = time.monotonic()
    for _ in range(3):
        await bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.5  # burst should drain immediately
