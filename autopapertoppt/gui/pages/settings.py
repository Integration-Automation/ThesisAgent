"""Settings page.

Stores API keys / contact email / cookies-file path locally via
``QSettings`` (native registry on Windows / plist on macOS / ini on
Linux). On startup the values are also pushed into ``os.environ`` so
the existing source plugins pick them up — saving here is equivalent
to setting the corresponding env var before launching the CLI.

The page deliberately does NOT validate the keys against the live
APIs — that would require a network round-trip per field, and would
leak the key into HTTP logs. Empty strings clear the env var.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from autopapertoppt.gui.i18n import SUPPORTED_LANGUAGES, t

# QSettings key (under organization/app) → env var name. The page reads
# both directions: load() pulls from QSettings into the form fields,
# save() writes back AND mirrors into os.environ for the current
# process.
_SETTINGS_FIELDS: Final[tuple[tuple[str, str, str], ...]] = (
    # (qsettings_key, env_var, label_i18n_key)
    ("api/anthropic", "ANTHROPIC_API_KEY", "settings.anthropic_key"),
    (
        "api/semantic_scholar",
        "AUTOPAPERTOPPT_S2_API_KEY",
        "settings.s2_key",
    ),
    ("api/ncbi", "AUTOPAPERTOPPT_NCBI_API_KEY", "settings.ncbi_key"),
    ("api/ieee", "AUTOPAPERTOPPT_IEEE_API_KEY", "settings.ieee_key"),
    (
        "api/springer",
        "AUTOPAPERTOPPT_SPRINGER_API_KEY",
        "settings.springer_key",
    ),
    (
        "api/crossref_plus",
        "AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN",
        "settings.crossref_token",
    ),
    (
        "contact/email",
        "AUTOPAPERTOPPT_CONTACT_EMAIL",
        "settings.contact_email",
    ),
)

_COOKIES_KEY: Final[str] = "pdf/cookies_file"
_COOKIES_ENV: Final[str] = "AUTOPAPERTOPPT_PDF_COOKIES_FILE"
_UI_LANG_KEY: Final[str] = "ui/language"

_ORG: Final[str] = "AutoPaperToPPT"
_APP: Final[str] = "AutoPaperToPPT"


def settings_store() -> QSettings:
    """Return the QSettings handle for the GUI.

    Centralised so tests can monkey-patch the storage location via
    ``QSettings.setDefaultFormat(...)`` + ``setPath(...)``.
    """
    return QSettings(_ORG, _APP)


def apply_saved_env() -> None:
    """Push every saved value into ``os.environ`` for this process.

    Called on app startup so the CLI / fetchers see the same values
    the user typed in Settings without needing a shell restart.
    """
    store = settings_store()
    for key, env_var, _label in _SETTINGS_FIELDS:
        value = store.value(key, "", type=str)
        if value:
            os.environ[env_var] = value
        else:
            os.environ.pop(env_var, None)
    cookies = store.value(_COOKIES_KEY, "", type=str)
    if cookies:
        os.environ[_COOKIES_ENV] = cookies
    else:
        os.environ.pop(_COOKIES_ENV, None)


def saved_ui_language(default: str = "en") -> str:
    """Read the persisted UI language, defaulting if unset."""
    store = settings_store()
    value = store.value(_UI_LANG_KEY, default, type=str)
    return value if value in SUPPORTED_LANGUAGES else default


class SettingsPage(QWidget):
    """Form for API keys + cookies-file + UI language."""

    def __init__(self, ui_language: str = "en", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ui_language = ui_language
        self._field_inputs: dict[str, QLineEdit] = {}
        self._build_ui()
        self._load_from_store()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)

        ui_group = QGroupBox(t("settings.title", self._ui_language), self)
        ui_form = QFormLayout(ui_group)
        self._ui_lang_combo = QComboBox(self)
        for code in SUPPORTED_LANGUAGES:
            self._ui_lang_combo.addItem(code, code)
        ui_form.addRow(
            t("settings.ui_language", self._ui_language), self._ui_lang_combo
        )
        outer.addWidget(ui_group)

        api_group = QGroupBox(
            t("settings.api_keys_group", self._ui_language), self
        )
        api_form = QFormLayout(api_group)
        for key, _env_var, label_key in _SETTINGS_FIELDS:
            edit = QLineEdit(self)
            # Mask secret-shaped fields; contact email stays plain.
            if key.startswith("api/"):
                edit.setEchoMode(QLineEdit.PasswordEchoOnEdit)
            api_form.addRow(t(label_key, self._ui_language), edit)
            self._field_inputs[key] = edit
        outer.addWidget(api_group)

        cookies_row = QWidget(self)
        cookies_layout = QHBoxLayout(cookies_row)
        cookies_layout.setContentsMargins(0, 0, 0, 0)
        self._cookies_input = QLineEdit(self)
        self._cookies_input.setReadOnly(True)
        browse = QPushButton(t("settings.browse_button", self._ui_language), self)
        browse.clicked.connect(self._on_browse_cookies)
        cookies_layout.addWidget(QLabel(t("settings.cookies_file", self._ui_language)))
        cookies_layout.addWidget(self._cookies_input, stretch=1)
        cookies_layout.addWidget(browse)
        outer.addWidget(cookies_row)

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        save_button = QPushButton(t("settings.save_button", self._ui_language), self)
        save_button.clicked.connect(self._on_save)
        save_row.addWidget(save_button)
        outer.addLayout(save_row)

        self._status_label = QLabel("", self)
        outer.addWidget(self._status_label)
        outer.addStretch(1)

    def _on_browse_cookies(self) -> None:
        start = self._cookies_input.text() or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("settings.cookies_dialog_title", self._ui_language),
            start,
            "Cookies (*.txt);;All files (*.*)",
        )
        if path:
            self._cookies_input.setText(path)

    def _on_save(self) -> None:
        store = settings_store()
        for key, env_var, _label in _SETTINGS_FIELDS:
            value = self._field_inputs[key].text().strip()
            store.setValue(key, value)
            if value:
                os.environ[env_var] = value
            else:
                os.environ.pop(env_var, None)
        cookies = self._cookies_input.text().strip()
        store.setValue(_COOKIES_KEY, cookies)
        if cookies:
            os.environ[_COOKIES_ENV] = cookies
        else:
            os.environ.pop(_COOKIES_ENV, None)
        lang = self._ui_lang_combo.currentData() or "en"
        store.setValue(_UI_LANG_KEY, lang)
        store.sync()
        self._status_label.setText(
            t("settings.saved_message", self._ui_language)
        )

    def _load_from_store(self) -> None:
        store = settings_store()
        for key, _env_var, _label in _SETTINGS_FIELDS:
            self._field_inputs[key].setText(store.value(key, "", type=str))
        self._cookies_input.setText(store.value(_COOKIES_KEY, "", type=str))
        saved_lang = store.value(_UI_LANG_KEY, self._ui_language, type=str)
        for idx in range(self._ui_lang_combo.count()):
            if self._ui_lang_combo.itemData(idx) == saved_lang:
                self._ui_lang_combo.setCurrentIndex(idx)
                break

    # --- accessors used by tests ----------------------------------------

    def field_input(self, qsettings_key: str) -> QLineEdit:
        return self._field_inputs[qsettings_key]

    def cookies_input(self) -> QLineEdit:
        return self._cookies_input

    def status_text(self) -> str:
        return self._status_label.text()

    def trigger_save(self) -> None:
        self._on_save()
