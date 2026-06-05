"""Background-thread wrappers for the GUI.

Qt's event loop runs on the main thread; calling a blocking or async
backend function directly from a button handler freezes the UI. Each
worker here wraps one backend call, runs it on a worker thread (via
``QThreadPool``), and emits a signal back to the main thread when done.

Signals are typed as ``object`` because ``Signal`` doesn't accept
``PaperCollection`` / ``Path`` as parameter types directly; the
receiving slot casts as needed.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class _WorkerSignals(QObject):
    """Signals emitted by :class:`AsyncWorker` and :class:`BlockingWorker`.

    Defined here (not on the QRunnable subclasses) because QRunnable is
    not a QObject and can't carry signals directly.
    """

    finished = Signal(object)
    failed = Signal(object)


class AsyncWorker(QRunnable):
    """Run a coroutine off the main thread and report back via signals.

    Use this for anything that calls ``await`` — searches, single-paper
    fetches, anything that touches ``httpx.AsyncClient``.
    """

    def __init__(self, coro_factory: Callable[[], Any]) -> None:
        super().__init__()
        self._coro_factory = coro_factory
        self.signals = _WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = asyncio.run(self._coro_factory())
        except Exception as err:  # noqa: BLE001 — UI must catch everything
            self.signals.failed.emit(err)
            return
        self.signals.finished.emit(result)


class BlockingWorker(QRunnable):
    """Run a plain blocking callable off the main thread.

    Use this for synchronous CPU / IO calls — ``export_collection``
    is the main one (renders a pptx via python-pptx).
    """

    def __init__(self, func: Callable[[], Any]) -> None:
        super().__init__()
        self._func = func
        self.signals = _WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self._func()
        except Exception as err:  # noqa: BLE001
            self.signals.failed.emit(err)
            return
        self.signals.finished.emit(result)
