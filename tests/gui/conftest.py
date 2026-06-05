"""GUI test fixtures.

Skips the entire ``tests/gui/`` tree when PySide6 isn't installed —
the suite stays runnable on a dev machine without the ``[gui]`` extra.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="install thesisagents[gui]")
pytest.importorskip("pytestqt", reason="install thesisagents[dev]")
