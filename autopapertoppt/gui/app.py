"""GUI entry point. ``autopapertoppt-gui`` and ``autopapertoppt gui``
both resolve here.
"""

from __future__ import annotations

import sys

from autopapertoppt.gui.pages.settings import apply_saved_env, saved_ui_language


def main(argv: list[str] | None = None) -> int:
    """Boot the PySide6 desktop UI.

    Returns the Qt event-loop exit code so a non-zero shell exit
    propagates a crash up to the caller.
    """
    # Import inside main so importing the package itself never pays
    # the PySide6 cost (~80 MB) when only the CLI is used.
    from PySide6.QtWidgets import QApplication

    from autopapertoppt.gui.main_window import MainWindow

    # Mirror any saved API keys into os.environ BEFORE the first source
    # plugin is loaded by a search; otherwise the env var lookup that
    # the IEEE / Springer / Anthropic clients perform at fetcher
    # __init__ time will miss them.
    apply_saved_env()

    app_argv = list(sys.argv if argv is None else [sys.argv[0], *argv])
    app = QApplication.instance() or QApplication(app_argv)

    window = MainWindow(ui_language=saved_ui_language())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
