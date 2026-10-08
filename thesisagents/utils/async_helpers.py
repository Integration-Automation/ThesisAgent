"""Run a coroutine to completion from synchronous code.

The boundary this guards: a synchronous public function that needs async I/O
internally. ``export_collection`` is synchronous and is called both from plain
scripts (no event loop) and from inside a running loop (the CLI's ``_run``
coroutine, the MCP ``export`` tool). ``asyncio.run`` works in the first case
and raises ``RuntimeError: asyncio.run() cannot be called from a running event
loop`` in the second, so the caller cannot just pick one.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import Any


def run_blocking[T](coro_factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
    """Run the coroutine ``coro_factory()`` builds and return its result.

    With no event loop running in this thread the coroutine runs under
    ``asyncio.run``. With one already running it runs on a private loop in a
    worker thread while this thread waits, because a running loop cannot be
    re-entered.

    The argument is a factory, not a coroutine object, so the coroutine is
    created inside the loop that will run it. Anything the coroutine opens (an
    HTTP client, a lock) is then bound to that loop and closed with it. A
    coroutine built by the caller and handed over would carry objects bound to
    the caller's loop.

    Example::

        report = run_blocking(lambda: verify_identifiers(papers))

    Anti-pattern this replaces: calling ``asyncio.run(...)`` directly inside a
    function that an ``async def`` may call, which works in the unit test and
    fails the first time the CLI reaches it.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro_factory())
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(coro_factory())).result()
