"""GUI entry point. ``autopapertoppt-gui`` and ``autopapertoppt gui``
both resolve here.
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from autopapertoppt.gui.pages.settings import apply_saved_env, saved_ui_language

if TYPE_CHECKING:
    from PySide6.QtGui import QFont


def _configure_hidpi_env() -> None:
    """Pin the HiDPI policy BEFORE QApplication is constructed.

    On Qt 6 HiDPI is on by default but fractional scale factors (e.g.
    Windows at 125% / 150%) sometimes render blurry text without
    explicit guidance. Setting the policy to PassThrough lets the OS
    DPI flow into Qt unchanged; the env var version is the
    construction-time-safe knob because the QApplication-attribute
    version of this flag has to be set before QApplication.__init__
    runs and we cannot rely on import order callers will use.
    """
    # Only set if the user has not picked a policy of their own; respect
    # an explicit override.
    os.environ.setdefault(
        "QT_ENABLE_HIGHDPI_SCALING", "1",
    )
    os.environ.setdefault(
        "QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough",
    )


def main(argv: list[str] | None = None) -> int:
    """Boot the PySide6 desktop UI.

    Returns the Qt event-loop exit code so a non-zero shell exit
    propagates a crash up to the caller.
    """
    _configure_hidpi_env()

    # Import inside main so importing the package itself never pays
    # the PySide6 cost (~80 MB) when only the CLI is used.
    from PySide6.QtCore import QLocale
    from PySide6.QtWidgets import QApplication

    from autopapertoppt.gui.i18n import normalise_language
    from autopapertoppt.gui.main_window import MainWindow

    # Mirror any saved API keys into os.environ BEFORE the first source
    # plugin is loaded by a search; otherwise the env var lookup that
    # the IEEE / Springer / Anthropic clients perform at fetcher
    # __init__ time will miss them.
    apply_saved_env()

    app_argv = list(sys.argv if argv is None else [sys.argv[0], *argv])
    app = QApplication.instance() or QApplication(app_argv)

    # Default to a slightly larger point-size than Qt's platform default
    # so text stays readable across HiDPI screens without per-widget
    # font overrides. Point-sized fonts let Qt's HiDPI scaling do the
    # right thing automatically.
    base_font = app.font()
    if base_font.pointSize() < 10:
        base_font.setPointSize(10)
        app.setFont(base_font)
    # Tell Qt about every CJK / RTL fallback so we don't get tofu boxes
    # for hi / ko / zh-* when the host font lacks a glyph.
    app.setFont(_with_unicode_fallback(base_font))

    # First-run language: settings override → OS locale → English.
    language = saved_ui_language(default=normalise_language(QLocale().name()))
    window = MainWindow(ui_language=language)
    window.show()
    return app.exec()


def _with_unicode_fallback(font: QFont) -> QFont:
    """Add families that ship on Windows + commonly elsewhere to cover
    every script the UI may render. Qt walks the family list in order,
    so the original family stays the primary choice.
    """
    # Qt expects a comma-separated CSS-like family list when set via
    # setFamilies (Qt6+); the order is preference order.
    fallbacks = [
        font.family(),
        "Segoe UI",
        "Microsoft JhengHei UI",  # zh-tw on Windows
        "Microsoft YaHei UI",      # zh-cn on Windows
        "Yu Gothic UI",            # ja on Windows
        "Malgun Gothic",           # ko on Windows
        "Nirmala UI",              # hi / devanagari on Windows
        "Arial",
    ]
    # De-dupe while preserving order.
    seen: set[str] = set()
    ordered = [f for f in fallbacks if not (f in seen or seen.add(f))]
    font.setFamilies(ordered)
    return font


if __name__ == "__main__":
    raise SystemExit(main())
