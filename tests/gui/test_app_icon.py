"""Smoke tests for the bundled app icon."""

from __future__ import annotations

from pathlib import Path

import pytest

from autopapertoppt.gui import app as gui_app


def test_icon_file_exists_in_repo():
    """The .ico must be committed — Nuitka reads it at build time."""
    assert gui_app._ICON_PATH.is_file(), (  # noqa: SLF001
        f"missing app icon at {gui_app._ICON_PATH}"  # noqa: SLF001
    )


def test_icon_loads_as_qicon(qtbot):  # noqa: ARG001 — qtbot primes QApplication
    icon = gui_app._load_app_icon()  # noqa: SLF001
    assert icon is not None
    # Available sizes should include the ones generate_icon.py embeds.
    available = {(size.width(), size.height()) for size in icon.availableSizes()}
    # At minimum the 16x16 + 256x256 should be present after Pillow's
    # ICO writer round-trip.
    assert (16, 16) in available or (32, 32) in available
    assert (256, 256) in available


def test_load_app_icon_handles_missing_file(monkeypatch, tmp_path):
    """If a future repackaging breaks the path lookup, the GUI should
    still boot — _load_app_icon returns None and the default Qt icon
    is used."""
    monkeypatch.setattr(gui_app, "_ICON_PATH", tmp_path / "does-not-exist.ico")
    assert gui_app._load_app_icon() is None  # noqa: SLF001


@pytest.mark.parametrize("attr", ["_ICON_PATH"])
def test_icon_path_resolves_under_repo(attr):
    """The computed path must live somewhere under the project root."""
    repo_root = Path(__file__).resolve().parents[2]
    icon_path = getattr(gui_app, attr)
    assert repo_root in icon_path.parents
