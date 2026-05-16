"""Tests for the Settings page.

Uses a tmp QSettings path so saving in the test suite never touches the
user's real registry / config file.
"""

from __future__ import annotations

import os

import pytest
from PySide6.QtCore import QSettings

from autopapertoppt.gui.pages.settings import SettingsPage


@pytest.fixture(autouse=True)
def _isolated_qsettings(tmp_path, monkeypatch):
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(
        QSettings.IniFormat, QSettings.UserScope, str(tmp_path)
    )
    # Make sure leftover env vars from the host shell don't pollute the
    # assertions — settings.py mirrors values into os.environ and we
    # check the absence too.
    for var in (
        "ANTHROPIC_API_KEY",
        "AUTOPAPERTOPPT_S2_API_KEY",
        "AUTOPAPERTOPPT_NCBI_API_KEY",
        "AUTOPAPERTOPPT_IEEE_API_KEY",
        "AUTOPAPERTOPPT_SPRINGER_API_KEY",
        "AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN",
        "AUTOPAPERTOPPT_CONTACT_EMAIL",
        "AUTOPAPERTOPPT_PDF_COOKIES_FILE",
    ):
        monkeypatch.delenv(var, raising=False)


def test_save_persists_to_qsettings_and_env(qtbot):
    page = SettingsPage(ui_language="en")
    qtbot.addWidget(page)
    page.field_input("api/anthropic").setText("sk-test-123")
    page.field_input("contact/email").setText("dev@example.com")
    page.trigger_save()

    assert os.environ["ANTHROPIC_API_KEY"] == "sk-test-123"
    assert os.environ["AUTOPAPERTOPPT_CONTACT_EMAIL"] == "dev@example.com"

    # Spin up a fresh page; values should re-hydrate from QSettings.
    page2 = SettingsPage(ui_language="en")
    qtbot.addWidget(page2)
    assert page2.field_input("api/anthropic").text() == "sk-test-123"
    assert page2.field_input("contact/email").text() == "dev@example.com"


def test_clearing_value_removes_env_var(qtbot):
    page = SettingsPage(ui_language="en")
    qtbot.addWidget(page)
    page.field_input("api/anthropic").setText("sk-1")
    page.trigger_save()
    assert os.environ.get("ANTHROPIC_API_KEY") == "sk-1"

    page.field_input("api/anthropic").setText("")
    page.trigger_save()
    assert "ANTHROPIC_API_KEY" not in os.environ


def test_save_message_is_localised(qtbot):
    page = SettingsPage(ui_language="zh-tw")
    qtbot.addWidget(page)
    page.trigger_save()
    assert "重新啟動" in page.status_text()
