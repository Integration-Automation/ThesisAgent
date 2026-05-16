"""GUI label translations.

Separate from ``autopapertoppt/exporters/i18n.py`` so the slide-deck
i18n table (which has a strict 14-language coverage test) and the UI
labels can evolve independently. The GUI ships with **English** and
**Traditional Chinese** label sets; any other language code falls
back to English. Add a language by extending the per-key dicts —
the test in ``tests/gui/test_i18n.py`` will tell you which keys
need filling in.
"""

from __future__ import annotations

from typing import Final

DEFAULT_LANGUAGE: Final[str] = "en"
SUPPORTED_LANGUAGES: Final[tuple[str, ...]] = ("en", "zh-tw")

_LABELS: Final[dict[str, dict[str, str]]] = {
    # Window + nav
    "app.title": {
        "en": "AutoPaperToPPT",
        "zh-tw": "AutoPaperToPPT",
    },
    "nav.search": {"en": "Search", "zh-tw": "搜尋"},
    "nav.enrich": {"en": "Enrich", "zh-tw": "豐富化"},
    "nav.deck": {"en": "Deck", "zh-tw": "投影片"},
    "nav.settings": {"en": "Settings", "zh-tw": "設定"},
    # Search page — inputs
    "search.query_label": {"en": "Query", "zh-tw": "查詢關鍵字"},
    "search.query_placeholder": {
        "en": "e.g. transformer attention",
        "zh-tw": "例如:transformer attention",
    },
    "search.sources_label": {"en": "Sources", "zh-tw": "資料來源"},
    "search.language_label": {"en": "Slide language", "zh-tw": "投影片語言"},
    "search.max_results_label": {
        "en": "Max results per source",
        "zh-tw": "每個來源的最多結果數",
    },
    "search.top_tier_only": {
        "en": "Top-tier venues only",
        "zh-tw": "僅頂級會議 / 期刊",
    },
    "search.year_from": {"en": "Year from", "zh-tw": "起始年份"},
    "search.year_to": {"en": "Year to", "zh-tw": "結束年份"},
    "search.search_button": {"en": "Search", "zh-tw": "搜尋"},
    "search.export_button": {"en": "Export…", "zh-tw": "匯出…"},
    "search.export_dialog_title": {
        "en": "Choose export directory",
        "zh-tw": "選擇匯出資料夾",
    },
    # Search page — status / errors
    "search.status_idle": {"en": "Idle.", "zh-tw": "閒置中。"},
    "search.status_running": {
        "en": "Searching…",
        "zh-tw": "搜尋中…",
    },
    "search.status_done": {
        "en": "Found {count} paper(s).",
        "zh-tw": "找到 {count} 篇論文。",
    },
    "search.status_export_running": {
        "en": "Exporting…",
        "zh-tw": "正在匯出…",
    },
    "search.status_export_done": {
        "en": "Exported to {path}",
        "zh-tw": "已匯出至 {path}",
    },
    "search.error_empty_query": {
        "en": "Enter a query first.",
        "zh-tw": "請先輸入查詢關鍵字。",
    },
    "search.error_no_results": {
        "en": "No results to export. Run a search first.",
        "zh-tw": "沒有可匯出的結果,請先執行搜尋。",
    },
    "search.error_generic": {
        "en": "Error: {error}",
        "zh-tw": "錯誤:{error}",
    },
    # Results table columns
    "results.col_title": {"en": "Title", "zh-tw": "標題"},
    "results.col_authors": {"en": "Authors", "zh-tw": "作者"},
    "results.col_year": {"en": "Year", "zh-tw": "年份"},
    "results.col_source": {"en": "Source", "zh-tw": "來源"},
    "results.col_doi": {"en": "DOI", "zh-tw": "DOI"},
    "results.col_citations": {"en": "Citations", "zh-tw": "引用數"},
    # Enrich / Deck placeholder
    "placeholder.coming_soon_title": {
        "en": "Coming soon",
        "zh-tw": "即將推出",
    },
    "placeholder.enrich_body": {
        "en": (
            "Per-paper PDF + LLM enrichment will land here. For now, "
            "set ANTHROPIC_API_KEY in Settings, run a search, then "
            "export — the CLI will auto-enrich each paper that has a "
            "downloadable PDF."
        ),
        "zh-tw": (
            "單篇論文的 PDF + LLM 豐富化會放在這個分頁。目前請先到「設定」"
            "輸入 ANTHROPIC_API_KEY,執行搜尋後再匯出 — CLI 會自動豐富每篇"
            "有可下載 PDF 的論文。"
        ),
    },
    "placeholder.deck_body": {
        "en": (
            "Slide-deck inspector / editor will land here. The MCP "
            "server already exposes pptx_inspect / pptx_update_slide / "
            "pptx_reorder_slides / pptx_delete_slide / pptx_add_slide; "
            "this page will wire them to a Qt list view."
        ),
        "zh-tw": (
            "投影片檢視 / 編輯介面會放在這個分頁。MCP 伺服器已經提供 "
            "pptx_inspect / pptx_update_slide / pptx_reorder_slides / "
            "pptx_delete_slide / pptx_add_slide,這頁會把它們接到 Qt list view。"
        ),
    },
    # Settings page
    "settings.title": {"en": "Settings", "zh-tw": "設定"},
    "settings.ui_language": {
        "en": "Interface language",
        "zh-tw": "介面語言",
    },
    "settings.api_keys_group": {
        "en": "API keys (stored locally via QSettings)",
        "zh-tw": "API 金鑰(透過 QSettings 儲存在本機)",
    },
    "settings.anthropic_key": {
        "en": "Anthropic API key",
        "zh-tw": "Anthropic API 金鑰",
    },
    "settings.s2_key": {
        "en": "Semantic Scholar API key (optional)",
        "zh-tw": "Semantic Scholar API 金鑰(選填)",
    },
    "settings.ncbi_key": {
        "en": "NCBI / PubMed API key (optional)",
        "zh-tw": "NCBI / PubMed API 金鑰(選填)",
    },
    "settings.ieee_key": {
        "en": "IEEE Xplore API key (optional)",
        "zh-tw": "IEEE Xplore API 金鑰(選填)",
    },
    "settings.springer_key": {
        "en": "Springer Nature API key (optional)",
        "zh-tw": "Springer Nature API 金鑰(選填)",
    },
    "settings.crossref_token": {
        "en": "Crossref Plus token (optional)",
        "zh-tw": "Crossref Plus token(選填)",
    },
    "settings.contact_email": {
        "en": "Contact email (Crossref polite pool)",
        "zh-tw": "聯絡 email(Crossref polite pool)",
    },
    "settings.cookies_file": {
        "en": "PDF cookies file (Netscape format)",
        "zh-tw": "PDF cookies 檔案(Netscape 格式)",
    },
    "settings.browse_button": {"en": "Browse…", "zh-tw": "瀏覽…"},
    "settings.save_button": {"en": "Save", "zh-tw": "儲存"},
    "settings.saved_message": {
        "en": "Settings saved. Restart the app to apply.",
        "zh-tw": "設定已儲存,重新啟動 App 後生效。",
    },
    "settings.cookies_dialog_title": {
        "en": "Choose cookies file",
        "zh-tw": "選擇 cookies 檔案",
    },
}


def normalise_language(code: str | None) -> str:
    """Map any string to a supported GUI language, defaulting to English."""
    if not code:
        return DEFAULT_LANGUAGE
    lowered = code.strip().lower().replace("_", "-")
    if lowered in SUPPORTED_LANGUAGES:
        return lowered
    # zh-cn / zh-hk / zh-sg etc. all fall back to en (the slide-deck i18n
    # table covers their PPT output; the UI labels intentionally do not
    # yet, to keep the table small).
    return DEFAULT_LANGUAGE


def t(key: str, language: str = DEFAULT_LANGUAGE, /, **fmt: object) -> str:
    """Translate a UI key, with optional format placeholders.

    Returns the English string when ``key`` is missing for ``language``
    (so adding a key without translating it yet is a soft failure). If
    the key is missing from English too the key itself is returned —
    a visible bug marker that lets the test suite catch unwired strings.
    """
    lang = normalise_language(language)
    entry = _LABELS.get(key)
    if entry is None:
        return key
    template = entry.get(lang) or entry.get(DEFAULT_LANGUAGE) or key
    if fmt:
        try:
            return template.format(**fmt)
        except (KeyError, IndexError):
            return template
    return template
