"""Coverage tests for GUI label translations."""

from __future__ import annotations

import pytest

from autopapertoppt.gui import i18n


def test_every_key_has_english():
    """English is the fallback; every key MUST resolve in English."""
    missing = [key for key, table in i18n._LABELS.items() if "en" not in table]
    assert not missing, f"keys without an English entry: {missing}"


def test_every_key_has_traditional_chinese():
    """Traditional Chinese is the first translation we ship; keep it complete."""
    missing = [key for key, table in i18n._LABELS.items() if "zh-tw" not in table]
    assert not missing, f"keys without a zh-tw entry: {missing}"


def test_unknown_language_falls_back_to_english():
    assert i18n.t("nav.search", "klingon") == "Search"


def test_normalise_language_handles_locale_suffix():
    # PySide6 / QLocale can hand back "zh_TW" or "zh-Hant-TW"; the
    # GUI table only knows "zh-tw", so anything fancier should fall
    # back to English rather than crash.
    assert i18n.normalise_language("zh_TW") == "zh-tw"
    assert i18n.normalise_language("zh-Hant-TW") == "en"
    assert i18n.normalise_language(None) == "en"


def test_format_placeholder_renders():
    rendered = i18n.t("search.status_done", "en", count=7)
    assert "7" in rendered


@pytest.mark.parametrize("language", ["en", "zh-tw"])
def test_status_done_template_keeps_count_placeholder(language):
    template = i18n._LABELS["search.status_done"][language]
    assert "{count}" in template
