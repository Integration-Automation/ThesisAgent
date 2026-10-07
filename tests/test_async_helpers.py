"""``run_blocking``: one way to finish a coroutine from synchronous code."""

from __future__ import annotations

import asyncio
import threading

import pytest

from thesisagents.utils.async_helpers import run_blocking


async def _answer() -> int:
    await asyncio.sleep(0)
    return 42


def test_runs_a_coroutine_when_no_loop_is_running():
    assert run_blocking(_answer) == 42


async def test_runs_a_coroutine_from_inside_a_running_loop():
    """``asyncio.run`` would raise here. The CLI reaches this case because its
    ``_run`` coroutine calls the synchronous ``export_collection``."""
    assert run_blocking(_answer) == 42


async def test_inside_a_loop_the_coroutine_runs_on_another_thread_and_loop():
    outer_loop = asyncio.get_running_loop()
    outer_thread = threading.get_ident()

    async def _where() -> tuple[int, bool]:
        return threading.get_ident(), asyncio.get_running_loop() is outer_loop

    inner_thread, same_loop = run_blocking(_where)

    assert inner_thread != outer_thread
    assert same_loop is False


def test_without_a_loop_the_coroutine_runs_on_the_calling_thread():
    async def _where() -> int:
        return threading.get_ident()

    assert run_blocking(_where) == threading.get_ident()


@pytest.mark.parametrize("inside_loop", [False, True])
def test_the_coroutines_exception_reaches_the_caller(inside_loop: bool):
    async def _fail() -> None:
        raise ValueError("from the coroutine")

    def _call() -> None:
        with pytest.raises(ValueError, match="from the coroutine"):
            run_blocking(_fail)

    if not inside_loop:
        _call()
        return

    async def _within_loop() -> None:
        _call()

    asyncio.run(_within_loop())


def test_the_factory_is_called_once_per_run():
    built: list[int] = []

    def _factory():
        built.append(1)
        return _answer()

    assert run_blocking(_factory) == 42
    assert built == [1]
