"""Per-source token-bucket rate limit. Retries go through it too."""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RateLimit:
    """Declarative rate-limit policy for a single source."""

    requests_per_second: float
    burst: int = 1
    jitter_seconds: float = 0.0


class TokenBucket:
    """Async token bucket. One instance per source, shared across all requests."""

    def __init__(self, policy: RateLimit) -> None:
        if policy.requests_per_second <= 0:
            raise ValueError("requests_per_second must be > 0")
        self._policy = policy
        self._capacity = max(1, policy.burst)
        self._tokens = float(self._capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            await self._wait_for_token_locked()
            self._tokens -= 1.0
        if self._policy.jitter_seconds > 0:
            await asyncio.sleep(random.uniform(0, self._policy.jitter_seconds))  # noqa: S311  # nosec B311  # jitter only, not security-relevant

    async def _wait_for_token_locked(self) -> None:
        while True:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._last_refill = now
            self._tokens = min(
                float(self._capacity),
                self._tokens + elapsed * self._policy.requests_per_second,
            )
            if self._tokens >= 1.0:
                return
            deficit = 1.0 - self._tokens
            sleep_for = deficit / self._policy.requests_per_second
            await asyncio.sleep(sleep_for)
