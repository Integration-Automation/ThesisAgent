"""Verify ``autopapertoppt gui`` dispatches to the GUI entry point."""

from __future__ import annotations

from autopapertoppt import cli as cli_module


def test_gui_subcommand_calls_gui_main(monkeypatch):
    calls = []

    def fake_gui_main(argv):
        calls.append(argv)
        return 0

    monkeypatch.setattr(
        "autopapertoppt.gui.app.main", fake_gui_main
    )
    rc = cli_module.main(["gui", "--debug"])
    assert rc == 0
    assert calls == [["--debug"]]


def test_gui_subcommand_handles_missing_extra(monkeypatch):
    # Force the dynamic import inside _dispatch_gui to fail.
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "autopapertoppt.gui.app":
            raise ImportError("PySide6 not installed (faked)")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    rc = cli_module.main(["gui"])
    assert rc == 2
