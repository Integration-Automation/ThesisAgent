"""GUI test fixtures.

Skips the entire ``tests/gui/`` tree when PySide6 isn't installed —
the suite stays runnable on a dev machine without the ``[gui]`` extra.
Every GUI test gets its own QSettings location, so pages and windows
that save state never touch the user's real registry / config file.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="install thesisagents[gui]")
pytest.importorskip("pytestqt", reason="install thesisagents[dev]")

from PySide6.QtCore import QSettings  # noqa: E402 - after the skip guard


@pytest.fixture(autouse=True)
def _isolated_qsettings(tmp_path):
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
