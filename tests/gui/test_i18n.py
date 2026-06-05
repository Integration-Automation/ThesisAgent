"""Coverage tests for GUI label translations."""

from __future__ import annotations

import pytest

from thesisagents.gui import i18n


def test_every_key_has_every_language():
    """Mirror of the slide-deck i18n coverage gate, scoped to the GUI table.

    The GUI ships 14 languages identical to the slide-deck table; a
    missing translation must fail the PR, not show up at runtime as
    an English string in an otherwise-localised UI.
    """
    failures: list[tuple[str, str]] = []
    for key, table in i18n._LABELS.items():
        for language in i18n.SUPPORTED_LANGUAGES:
            if language not in table or not table[language]:
                failures.append((key, language))
    assert not failures, f"missing GUI translations: {failures}"


def test_supported_languages_match_deck_table():
    """Keep the GUI and deck language sets in lockstep."""
    from thesisagents.exporters.i18n import (
        SUPPORTED_LANGUAGES as DECK_LANGUAGES,
    )

    assert set(i18n.SUPPORTED_LANGUAGES) == set(DECK_LANGUAGES)


def test_unknown_language_falls_back_to_english():
    assert i18n.t("nav.search", "klingon") == "Search"


def test_normalise_language_handles_locale_suffix():
    # PySide6 / QLocale can hand back "zh_TW", "zh-Hant-TW", "es_ES",
    # "fr_CA" — strip the script subtag / region to land on a code we
    # have in SUPPORTED_LANGUAGES, falling back to the language root
    # (es, fr) when present.
    assert i18n.normalise_language("zh_TW") == "zh-tw"
    assert i18n.normalise_language("zh-Hant-TW") == "zh-tw"
    assert i18n.normalise_language("es_ES") == "es"
    assert i18n.normalise_language("fr_CA") == "fr"
    assert i18n.normalise_language(None) == "en"


def test_format_placeholder_renders():
    rendered = i18n.t("search.status_done", "en", count=7)
    assert "7" in rendered


@pytest.mark.parametrize("language", i18n.SUPPORTED_LANGUAGES)
def test_status_done_template_keeps_count_placeholder(language):
    template = i18n._LABELS["search.status_done"][language]
    assert "{count}" in template


def test_language_display_names_cover_every_supported_language():
    missing = [
        code for code in i18n.SUPPORTED_LANGUAGES
        if code not in i18n.LANGUAGE_DISPLAY_NAMES
    ]
    assert not missing, f"language codes without display names: {missing}"
