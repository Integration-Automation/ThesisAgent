"""GUI label translations across all 14 supported languages.

Separate from ``autopapertoppt/exporters/i18n.py`` so the slide-deck
i18n table (which the test suite enforces 14-language coverage for)
and the UI labels can evolve independently — but the language set
is intentionally identical so users see one consistent menu.

Adding a new key: extend ``_LABELS`` with one entry. The test in
``tests/gui/test_i18n.py`` enforces every key has every language;
that catches a missing translation at PR time, not at runtime.
"""

from __future__ import annotations

from typing import Final

DEFAULT_LANGUAGE: Final[str] = "en"
SUPPORTED_LANGUAGES: Final[tuple[str, ...]] = (
    "en",
    "zh-tw",
    "zh-cn",
    "ja",
    "es",
    "fr",
    "de",
    "ko",
    "pt",
    "ru",
    "it",
    "vi",
    "hi",
    "id",
)

# Human-readable language name to display in the UI language dropdown.
LANGUAGE_DISPLAY_NAMES: Final[dict[str, str]] = {
    "en": "English",
    "zh-tw": "繁體中文",
    "zh-cn": "简体中文",
    "ja": "日本語",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "ko": "한국어",
    "pt": "Português",
    "ru": "Русский",
    "it": "Italiano",
    "vi": "Tiếng Việt",
    "hi": "हिन्दी",
    "id": "Bahasa Indonesia",
}

_LABELS: Final[dict[str, dict[str, str]]] = {
    # Window + nav ----------------------------------------------------
    "app.title": {
        "en": "AutoPaperToPPT",
        "zh-tw": "AutoPaperToPPT",
        "zh-cn": "AutoPaperToPPT",
        "ja": "AutoPaperToPPT",
        "es": "AutoPaperToPPT",
        "fr": "AutoPaperToPPT",
        "de": "AutoPaperToPPT",
        "ko": "AutoPaperToPPT",
        "pt": "AutoPaperToPPT",
        "ru": "AutoPaperToPPT",
        "it": "AutoPaperToPPT",
        "vi": "AutoPaperToPPT",
        "hi": "AutoPaperToPPT",
        "id": "AutoPaperToPPT",
    },
    "nav.search": {
        "en": "Search",
        "zh-tw": "搜尋",
        "zh-cn": "搜索",
        "ja": "検索",
        "es": "Buscar",
        "fr": "Rechercher",
        "de": "Suchen",
        "ko": "검색",
        "pt": "Pesquisar",
        "ru": "Поиск",
        "it": "Cerca",
        "vi": "Tìm kiếm",
        "hi": "खोज",
        "id": "Cari",
    },
    "nav.enrich": {
        "en": "Enrich",
        "zh-tw": "豐富化",
        "zh-cn": "丰富化",
        "ja": "強化",
        "es": "Enriquecer",
        "fr": "Enrichir",
        "de": "Anreichern",
        "ko": "보강",
        "pt": "Enriquecer",
        "ru": "Обогащение",
        "it": "Arricchisci",
        "vi": "Làm giàu",
        "hi": "समृद्ध करें",
        "id": "Perkaya",
    },
    "nav.deck": {
        "en": "Deck",
        "zh-tw": "投影片",
        "zh-cn": "幻灯片",
        "ja": "スライド",
        "es": "Diapositivas",
        "fr": "Diapos",
        "de": "Folien",
        "ko": "슬라이드",
        "pt": "Slides",
        "ru": "Слайды",
        "it": "Diapositive",
        "vi": "Slide",
        "hi": "स्लाइड",
        "id": "Slide",
    },
    "nav.settings": {
        "en": "Settings",
        "zh-tw": "設定",
        "zh-cn": "设置",
        "ja": "設定",
        "es": "Ajustes",
        "fr": "Paramètres",
        "de": "Einstellungen",
        "ko": "설정",
        "pt": "Configurações",
        "ru": "Настройки",
        "it": "Impostazioni",
        "vi": "Cài đặt",
        "hi": "सेटिंग्स",
        "id": "Pengaturan",
    },
    # Search page — inputs --------------------------------------------
    "search.query_label": {
        "en": "Query",
        "zh-tw": "查詢關鍵字",
        "zh-cn": "查询关键词",
        "ja": "検索キーワード",
        "es": "Consulta",
        "fr": "Requête",
        "de": "Suchbegriff",
        "ko": "검색어",
        "pt": "Consulta",
        "ru": "Запрос",
        "it": "Query",
        "vi": "Truy vấn",
        "hi": "क्वेरी",
        "id": "Kueri",
    },
    "search.query_placeholder": {
        "en": "e.g. transformer attention",
        "zh-tw": "例如:transformer attention",
        "zh-cn": "例如:transformer attention",
        "ja": "例:transformer attention",
        "es": "p. ej. transformer attention",
        "fr": "p. ex. transformer attention",
        "de": "z. B. transformer attention",
        "ko": "예: transformer attention",
        "pt": "p. ex. transformer attention",
        "ru": "напр. transformer attention",
        "it": "es. transformer attention",
        "vi": "vd. transformer attention",
        "hi": "उदा. transformer attention",
        "id": "mis. transformer attention",
    },
    "search.sources_label": {
        "en": "Sources",
        "zh-tw": "資料來源",
        "zh-cn": "数据来源",
        "ja": "ソース",
        "es": "Fuentes",
        "fr": "Sources",
        "de": "Quellen",
        "ko": "출처",
        "pt": "Fontes",
        "ru": "Источники",
        "it": "Fonti",
        "vi": "Nguồn",
        "hi": "स्रोत",
        "id": "Sumber",
    },
    "search.language_label": {
        "en": "Slide language",
        "zh-tw": "投影片語言",
        "zh-cn": "幻灯片语言",
        "ja": "スライドの言語",
        "es": "Idioma de las diapositivas",
        "fr": "Langue des diapositives",
        "de": "Foliensprache",
        "ko": "슬라이드 언어",
        "pt": "Idioma dos slides",
        "ru": "Язык слайдов",
        "it": "Lingua delle diapositive",
        "vi": "Ngôn ngữ slide",
        "hi": "स्लाइड भाषा",
        "id": "Bahasa slide",
    },
    "search.max_results_label": {
        "en": "Max results per source",
        "zh-tw": "每個來源的最多結果數",
        "zh-cn": "每个来源的最多结果数",
        "ja": "ソースごとの最大結果数",
        "es": "Resultados máximos por fuente",
        "fr": "Résultats maximum par source",
        "de": "Maximale Ergebnisse pro Quelle",
        "ko": "출처당 최대 결과 수",
        "pt": "Resultados máximos por fonte",
        "ru": "Макс. результатов на источник",
        "it": "Risultati massimi per fonte",
        "vi": "Số kết quả tối đa mỗi nguồn",
        "hi": "प्रति स्रोत अधिकतम परिणाम",
        "id": "Hasil maks per sumber",
    },
    "search.top_tier_only": {
        "en": "Top-tier venues only",
        "zh-tw": "僅頂級會議 / 期刊",
        "zh-cn": "仅顶级会议 / 期刊",
        "ja": "トップ会議 / 学術誌のみ",
        "es": "Solo eventos de primer nivel",
        "fr": "Conférences / revues de premier plan uniquement",
        "de": "Nur Top-Tier-Veranstaltungsorte",
        "ko": "최상위 학회 / 저널만",
        "pt": "Apenas eventos de primeiro nível",
        "ru": "Только топовые конференции / журналы",
        "it": "Solo sedi di alto livello",
        "vi": "Chỉ hội thảo / tạp chí hàng đầu",
        "hi": "केवल शीर्ष श्रेणी के स्थान",
        "id": "Hanya tempat papan atas",
    },
    "search.year_from": {
        "en": "Year from",
        "zh-tw": "起始年份",
        "zh-cn": "起始年份",
        "ja": "開始年",
        "es": "Año desde",
        "fr": "Année de début",
        "de": "Jahr ab",
        "ko": "시작 연도",
        "pt": "Ano de",
        "ru": "Год с",
        "it": "Anno da",
        "vi": "Năm từ",
        "hi": "वर्ष से",
        "id": "Tahun dari",
    },
    "search.year_to": {
        "en": "Year to",
        "zh-tw": "結束年份",
        "zh-cn": "结束年份",
        "ja": "終了年",
        "es": "Año hasta",
        "fr": "Année de fin",
        "de": "Jahr bis",
        "ko": "종료 연도",
        "pt": "Ano até",
        "ru": "Год по",
        "it": "Anno a",
        "vi": "Năm đến",
        "hi": "वर्ष तक",
        "id": "Tahun sampai",
    },
    "search.search_button": {
        "en": "Search",
        "zh-tw": "搜尋",
        "zh-cn": "搜索",
        "ja": "検索",
        "es": "Buscar",
        "fr": "Rechercher",
        "de": "Suchen",
        "ko": "검색",
        "pt": "Pesquisar",
        "ru": "Искать",
        "it": "Cerca",
        "vi": "Tìm kiếm",
        "hi": "खोजें",
        "id": "Cari",
    },
    "search.export_button": {
        "en": "Export…",
        "zh-tw": "匯出…",
        "zh-cn": "导出…",
        "ja": "エクスポート…",
        "es": "Exportar…",
        "fr": "Exporter…",
        "de": "Exportieren…",
        "ko": "내보내기…",
        "pt": "Exportar…",
        "ru": "Экспорт…",
        "it": "Esporta…",
        "vi": "Xuất…",
        "hi": "निर्यात…",
        "id": "Ekspor…",
    },
    "search.export_dialog_title": {
        "en": "Choose export directory",
        "zh-tw": "選擇匯出資料夾",
        "zh-cn": "选择导出文件夹",
        "ja": "エクスポート先のフォルダを選択",
        "es": "Elija el directorio de exportación",
        "fr": "Choisir le dossier d'exportation",
        "de": "Exportverzeichnis auswählen",
        "ko": "내보내기 폴더 선택",
        "pt": "Escolha a pasta de exportação",
        "ru": "Выберите папку для экспорта",
        "it": "Scegli la cartella di esportazione",
        "vi": "Chọn thư mục xuất",
        "hi": "निर्यात फ़ोल्डर चुनें",
        "id": "Pilih folder ekspor",
    },
    # Search page — status / errors -----------------------------------
    "search.status_idle": {
        "en": "Idle.",
        "zh-tw": "閒置中。",
        "zh-cn": "空闲。",
        "ja": "待機中。",
        "es": "Inactivo.",
        "fr": "Inactif.",
        "de": "Bereit.",
        "ko": "대기 중.",
        "pt": "Ocioso.",
        "ru": "Ожидание.",
        "it": "Inattivo.",
        "vi": "Chờ.",
        "hi": "निष्क्रिय।",
        "id": "Diam.",
    },
    "search.status_running": {
        "en": "Searching…",
        "zh-tw": "搜尋中…",
        "zh-cn": "搜索中…",
        "ja": "検索中…",
        "es": "Buscando…",
        "fr": "Recherche…",
        "de": "Suche läuft…",
        "ko": "검색 중…",
        "pt": "Pesquisando…",
        "ru": "Идёт поиск…",
        "it": "Ricerca in corso…",
        "vi": "Đang tìm…",
        "hi": "खोज रहे हैं…",
        "id": "Mencari…",
    },
    "search.status_done": {
        "en": "Found {count} paper(s).",
        "zh-tw": "找到 {count} 篇論文。",
        "zh-cn": "找到 {count} 篇论文。",
        "ja": "{count} 件の論文が見つかりました。",
        "es": "Se encontraron {count} artículo(s).",
        "fr": "{count} article(s) trouvé(s).",
        "de": "{count} Paper gefunden.",
        "ko": "{count}개의 논문을 찾았습니다.",
        "pt": "{count} artigo(s) encontrado(s).",
        "ru": "Найдено статей: {count}.",
        "it": "Trovati {count} articolo/i.",
        "vi": "Tìm thấy {count} bài báo.",
        "hi": "{count} शोधपत्र मिले।",
        "id": "Ditemukan {count} makalah.",
    },
    "search.status_export_running": {
        "en": "Exporting…",
        "zh-tw": "正在匯出…",
        "zh-cn": "正在导出…",
        "ja": "エクスポート中…",
        "es": "Exportando…",
        "fr": "Exportation…",
        "de": "Exportiere…",
        "ko": "내보내는 중…",
        "pt": "Exportando…",
        "ru": "Экспорт…",
        "it": "Esportazione…",
        "vi": "Đang xuất…",
        "hi": "निर्यात हो रहा है…",
        "id": "Mengekspor…",
    },
    "search.status_export_done": {
        "en": "Exported to {path}",
        "zh-tw": "已匯出至 {path}",
        "zh-cn": "已导出至 {path}",
        "ja": "{path} へエクスポートしました",
        "es": "Exportado a {path}",
        "fr": "Exporté vers {path}",
        "de": "Exportiert nach {path}",
        "ko": "{path}로 내보냈습니다",
        "pt": "Exportado para {path}",
        "ru": "Экспортировано в {path}",
        "it": "Esportato in {path}",
        "vi": "Đã xuất tới {path}",
        "hi": "{path} में निर्यात किया गया",
        "id": "Diekspor ke {path}",
    },
    "search.error_empty_query": {
        "en": "Enter a query first.",
        "zh-tw": "請先輸入查詢關鍵字。",
        "zh-cn": "请先输入查询关键词。",
        "ja": "まず検索キーワードを入力してください。",
        "es": "Introduzca primero una consulta.",
        "fr": "Saisissez d'abord une requête.",
        "de": "Bitte zuerst einen Suchbegriff eingeben.",
        "ko": "먼저 검색어를 입력하세요.",
        "pt": "Digite uma consulta primeiro.",
        "ru": "Сначала введите запрос.",
        "it": "Inserisci prima una query.",
        "vi": "Vui lòng nhập truy vấn trước.",
        "hi": "पहले एक क्वेरी दर्ज करें।",
        "id": "Masukkan kueri terlebih dahulu.",
    },
    "search.error_no_results": {
        "en": "No results to export. Run a search first.",
        "zh-tw": "沒有可匯出的結果,請先執行搜尋。",
        "zh-cn": "没有可导出的结果,请先执行搜索。",
        "ja": "エクスポートする結果がありません。先に検索してください。",
        "es": "No hay resultados para exportar. Ejecute una búsqueda primero.",
        "fr": "Aucun résultat à exporter. Lancez d'abord une recherche.",
        "de": "Keine Ergebnisse zum Exportieren. Bitte zuerst suchen.",
        "ko": "내보낼 결과가 없습니다. 먼저 검색하세요.",
        "pt": "Nenhum resultado para exportar. Faça uma pesquisa primeiro.",
        "ru": "Нет результатов для экспорта. Сначала выполните поиск.",
        "it": "Nessun risultato da esportare. Esegui prima una ricerca.",
        "vi": "Không có kết quả để xuất. Hãy tìm kiếm trước.",
        "hi": "निर्यात के लिए कोई परिणाम नहीं। पहले खोजें।",
        "id": "Tidak ada hasil untuk diekspor. Lakukan pencarian terlebih dahulu.",
    },
    "search.error_generic": {
        "en": "Error: {error}",
        "zh-tw": "錯誤:{error}",
        "zh-cn": "错误:{error}",
        "ja": "エラー: {error}",
        "es": "Error: {error}",
        "fr": "Erreur : {error}",
        "de": "Fehler: {error}",
        "ko": "오류: {error}",
        "pt": "Erro: {error}",
        "ru": "Ошибка: {error}",
        "it": "Errore: {error}",
        "vi": "Lỗi: {error}",
        "hi": "त्रुटि: {error}",
        "id": "Galat: {error}",
    },
    # Results table columns -------------------------------------------
    "results.col_title": {
        "en": "Title",
        "zh-tw": "標題",
        "zh-cn": "标题",
        "ja": "タイトル",
        "es": "Título",
        "fr": "Titre",
        "de": "Titel",
        "ko": "제목",
        "pt": "Título",
        "ru": "Заголовок",
        "it": "Titolo",
        "vi": "Tiêu đề",
        "hi": "शीर्षक",
        "id": "Judul",
    },
    "results.col_authors": {
        "en": "Authors",
        "zh-tw": "作者",
        "zh-cn": "作者",
        "ja": "著者",
        "es": "Autores",
        "fr": "Auteurs",
        "de": "Autoren",
        "ko": "저자",
        "pt": "Autores",
        "ru": "Авторы",
        "it": "Autori",
        "vi": "Tác giả",
        "hi": "लेखक",
        "id": "Penulis",
    },
    "results.col_year": {
        "en": "Year",
        "zh-tw": "年份",
        "zh-cn": "年份",
        "ja": "年",
        "es": "Año",
        "fr": "Année",
        "de": "Jahr",
        "ko": "연도",
        "pt": "Ano",
        "ru": "Год",
        "it": "Anno",
        "vi": "Năm",
        "hi": "वर्ष",
        "id": "Tahun",
    },
    "results.col_source": {
        "en": "Source",
        "zh-tw": "來源",
        "zh-cn": "来源",
        "ja": "ソース",
        "es": "Fuente",
        "fr": "Source",
        "de": "Quelle",
        "ko": "출처",
        "pt": "Fonte",
        "ru": "Источник",
        "it": "Fonte",
        "vi": "Nguồn",
        "hi": "स्रोत",
        "id": "Sumber",
    },
    "results.col_doi": {
        "en": "DOI",
        "zh-tw": "DOI",
        "zh-cn": "DOI",
        "ja": "DOI",
        "es": "DOI",
        "fr": "DOI",
        "de": "DOI",
        "ko": "DOI",
        "pt": "DOI",
        "ru": "DOI",
        "it": "DOI",
        "vi": "DOI",
        "hi": "DOI",
        "id": "DOI",
    },
    "results.col_citations": {
        "en": "Citations",
        "zh-tw": "引用數",
        "zh-cn": "引用数",
        "ja": "引用数",
        "es": "Citas",
        "fr": "Citations",
        "de": "Zitate",
        "ko": "인용 수",
        "pt": "Citações",
        "ru": "Цитирования",
        "it": "Citazioni",
        "vi": "Số trích dẫn",
        "hi": "उद्धरण",
        "id": "Sitasi",
    },
    # Enrich / Deck placeholder ---------------------------------------
    "placeholder.coming_soon_title": {
        "en": "Coming soon",
        "zh-tw": "即將推出",
        "zh-cn": "即将推出",
        "ja": "近日公開",
        "es": "Próximamente",
        "fr": "Bientôt disponible",
        "de": "Demnächst",
        "ko": "곧 출시",
        "pt": "Em breve",
        "ru": "Скоро",
        "it": "Prossimamente",
        "vi": "Sắp ra mắt",
        "hi": "जल्द आ रहा है",
        "id": "Segera hadir",
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
        "zh-cn": (
            "单篇论文的 PDF + LLM 丰富化会放在这个分页。目前请先到「设置」"
            "输入 ANTHROPIC_API_KEY,执行搜索后再导出 — CLI 会自动丰富每篇"
            "有可下载 PDF 的论文。"
        ),
        "ja": (
            "論文ごとの PDF + LLM 強化はここに搭載予定です。当面は「設定」で "
            "ANTHROPIC_API_KEY を入力し、検索を実行してからエクスポートして"
            "ください — CLI が PDF を取得できる論文ごとに自動で強化します。"
        ),
        "es": (
            "El enriquecimiento por artículo con PDF + LLM llegará aquí. "
            "Por ahora, configure ANTHROPIC_API_KEY en Ajustes, ejecute "
            "una búsqueda y luego exporte — la CLI enriquecerá "
            "automáticamente cada artículo con un PDF descargable."
        ),
        "fr": (
            "L'enrichissement article par article (PDF + LLM) sera "
            "disponible ici. Pour l'instant, définissez ANTHROPIC_API_KEY "
            "dans Paramètres, lancez une recherche puis exportez — la CLI "
            "enrichira automatiquement chaque article avec un PDF "
            "téléchargeable."
        ),
        "de": (
            "Pro-Paper-Anreicherung mit PDF + LLM kommt hierher. Bis dahin "
            "ANTHROPIC_API_KEY in Einstellungen setzen, suchen und "
            "exportieren — die CLI reichert jedes Paper mit "
            "herunterladbarem PDF automatisch an."
        ),
        "ko": (
            "논문별 PDF + LLM 보강이 곧 여기에 추가됩니다. 지금은 설정에서 "
            "ANTHROPIC_API_KEY를 입력하고 검색을 실행한 뒤 내보내기를 "
            "하세요 — CLI가 PDF를 다운로드할 수 있는 각 논문을 자동으로 "
            "보강합니다."
        ),
        "pt": (
            "O enriquecimento por artigo com PDF + LLM chegará aqui. Por "
            "enquanto, defina ANTHROPIC_API_KEY em Configurações, execute "
            "uma pesquisa e exporte — a CLI enriquecerá automaticamente "
            "cada artigo com PDF baixável."
        ),
        "ru": (
            "Постатейное обогащение PDF + LLM появится здесь. Пока "
            "укажите ANTHROPIC_API_KEY в Настройках, выполните поиск и "
            "экспортируйте — CLI автоматически обогатит каждую статью с "
            "загружаемым PDF."
        ),
        "it": (
            "L'arricchimento per articolo con PDF + LLM arriverà qui. Per "
            "ora, imposta ANTHROPIC_API_KEY in Impostazioni, esegui una "
            "ricerca e poi esporta — la CLI arricchirà automaticamente "
            "ogni articolo con un PDF scaricabile."
        ),
        "vi": (
            "Tính năng làm giàu từng bài (PDF + LLM) sẽ có ở đây. Hiện "
            "tại, hãy đặt ANTHROPIC_API_KEY trong Cài đặt, chạy tìm kiếm "
            "rồi xuất — CLI sẽ tự động làm giàu mỗi bài có PDF tải được."
        ),
        "hi": (
            "प्रति-शोधपत्र PDF + LLM समृद्धि यहाँ आएगी। अभी के लिए, "
            "सेटिंग्स में ANTHROPIC_API_KEY सेट करें, खोजें और निर्यात "
            "करें — CLI डाउनलोड योग्य PDF वाले प्रत्येक शोधपत्र को "
            "स्वचालित रूप से समृद्ध करेगा।"
        ),
        "id": (
            "Pengayaan per-makalah dengan PDF + LLM akan hadir di sini. "
            "Untuk saat ini, setel ANTHROPIC_API_KEY di Pengaturan, "
            "jalankan pencarian, lalu ekspor — CLI akan otomatis memperkaya "
            "setiap makalah yang PDF-nya bisa diunduh."
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
        "zh-cn": (
            "幻灯片查看 / 编辑界面会放在这个分页。MCP 服务器已经提供 "
            "pptx_inspect / pptx_update_slide / pptx_reorder_slides / "
            "pptx_delete_slide / pptx_add_slide,这页会把它们接到 Qt list view。"
        ),
        "ja": (
            "スライドの検査 / 編集 UI はここに搭載予定です。MCP サーバーは "
            "すでに pptx_inspect / pptx_update_slide / pptx_reorder_slides / "
            "pptx_delete_slide / pptx_add_slide を公開しており、このページでは "
            "それらを Qt の list view に接続します。"
        ),
        "es": (
            "El inspector / editor de diapositivas llegará aquí. El "
            "servidor MCP ya expone pptx_inspect / pptx_update_slide / "
            "pptx_reorder_slides / pptx_delete_slide / pptx_add_slide; "
            "esta página los conectará a una vista de lista Qt."
        ),
        "fr": (
            "L'inspecteur / éditeur de diapositives sera disponible ici. "
            "Le serveur MCP expose déjà pptx_inspect / pptx_update_slide / "
            "pptx_reorder_slides / pptx_delete_slide / pptx_add_slide ; "
            "cette page les reliera à une vue liste Qt."
        ),
        "de": (
            "Folien-Inspektor / -Editor kommt hierher. Der MCP-Server "
            "stellt bereits pptx_inspect / pptx_update_slide / "
            "pptx_reorder_slides / pptx_delete_slide / pptx_add_slide "
            "bereit; diese Seite verdrahtet sie mit einer Qt-Listenansicht."
        ),
        "ko": (
            "슬라이드 검사 / 편집기가 곧 여기에 추가됩니다. MCP 서버는 이미 "
            "pptx_inspect / pptx_update_slide / pptx_reorder_slides / "
            "pptx_delete_slide / pptx_add_slide를 제공하고, 이 페이지는 "
            "이를 Qt 리스트 뷰에 연결합니다."
        ),
        "pt": (
            "O inspector / editor de slides chegará aqui. O servidor MCP "
            "já expõe pptx_inspect / pptx_update_slide / "
            "pptx_reorder_slides / pptx_delete_slide / pptx_add_slide; "
            "esta página os ligará a uma view de lista Qt."
        ),
        "ru": (
            "Инспектор / редактор слайдов появится здесь. MCP-сервер уже "
            "предоставляет pptx_inspect / pptx_update_slide / "
            "pptx_reorder_slides / pptx_delete_slide / pptx_add_slide; "
            "эта страница подключит их к Qt-списку."
        ),
        "it": (
            "L'ispettore / editor di diapositive arriverà qui. Il server "
            "MCP espone già pptx_inspect / pptx_update_slide / "
            "pptx_reorder_slides / pptx_delete_slide / pptx_add_slide; "
            "questa pagina li collegherà a una vista lista Qt."
        ),
        "vi": (
            "Trình kiểm tra / chỉnh sửa slide sẽ có ở đây. Máy chủ MCP đã "
            "cung cấp pptx_inspect / pptx_update_slide / "
            "pptx_reorder_slides / pptx_delete_slide / pptx_add_slide; "
            "trang này sẽ kết nối chúng với Qt list view."
        ),
        "hi": (
            "स्लाइड डेक निरीक्षक / संपादक यहाँ आएगा। MCP सर्वर पहले से "
            "pptx_inspect / pptx_update_slide / pptx_reorder_slides / "
            "pptx_delete_slide / pptx_add_slide उपलब्ध कराता है; यह पेज "
            "उन्हें Qt list view से जोड़ेगा।"
        ),
        "id": (
            "Inspektur / editor slide akan hadir di sini. Server MCP "
            "sudah menyediakan pptx_inspect / pptx_update_slide / "
            "pptx_reorder_slides / pptx_delete_slide / pptx_add_slide; "
            "halaman ini akan menghubungkannya ke list view Qt."
        ),
    },
    # Settings page ---------------------------------------------------
    "settings.title": {
        "en": "Settings",
        "zh-tw": "設定",
        "zh-cn": "设置",
        "ja": "設定",
        "es": "Ajustes",
        "fr": "Paramètres",
        "de": "Einstellungen",
        "ko": "설정",
        "pt": "Configurações",
        "ru": "Настройки",
        "it": "Impostazioni",
        "vi": "Cài đặt",
        "hi": "सेटिंग्स",
        "id": "Pengaturan",
    },
    "settings.ui_language": {
        "en": "Interface language",
        "zh-tw": "介面語言",
        "zh-cn": "界面语言",
        "ja": "インターフェース言語",
        "es": "Idioma de la interfaz",
        "fr": "Langue de l'interface",
        "de": "Oberflächensprache",
        "ko": "인터페이스 언어",
        "pt": "Idioma da interface",
        "ru": "Язык интерфейса",
        "it": "Lingua dell'interfaccia",
        "vi": "Ngôn ngữ giao diện",
        "hi": "इंटरफ़ेस भाषा",
        "id": "Bahasa antarmuka",
    },
    "settings.api_keys_group": {
        "en": "API keys (stored locally via QSettings)",
        "zh-tw": "API 金鑰(透過 QSettings 儲存在本機)",
        "zh-cn": "API 密钥(通过 QSettings 存储在本机)",
        "ja": "API キー(QSettings でローカル保存)",
        "es": "Claves de API (guardadas localmente vía QSettings)",
        "fr": "Clés API (stockées localement via QSettings)",
        "de": "API-Schlüssel (lokal via QSettings gespeichert)",
        "ko": "API 키 (QSettings로 로컬 저장)",
        "pt": "Chaves de API (armazenadas localmente via QSettings)",
        "ru": "Ключи API (хранятся локально через QSettings)",
        "it": "Chiavi API (memorizzate localmente tramite QSettings)",
        "vi": "Khóa API (lưu cục bộ qua QSettings)",
        "hi": "API कुंजियाँ (QSettings के माध्यम से स्थानीय रूप से संग्रहीत)",
        "id": "Kunci API (disimpan lokal lewat QSettings)",
    },
    "settings.anthropic_key": {
        "en": "Anthropic API key",
        "zh-tw": "Anthropic API 金鑰",
        "zh-cn": "Anthropic API 密钥",
        "ja": "Anthropic API キー",
        "es": "Clave de API de Anthropic",
        "fr": "Clé API Anthropic",
        "de": "Anthropic-API-Schlüssel",
        "ko": "Anthropic API 키",
        "pt": "Chave de API da Anthropic",
        "ru": "API-ключ Anthropic",
        "it": "Chiave API Anthropic",
        "vi": "Khóa API Anthropic",
        "hi": "Anthropic API कुंजी",
        "id": "Kunci API Anthropic",
    },
    "settings.s2_key": {
        "en": "Semantic Scholar API key (optional)",
        "zh-tw": "Semantic Scholar API 金鑰(選填)",
        "zh-cn": "Semantic Scholar API 密钥(可选)",
        "ja": "Semantic Scholar API キー(任意)",
        "es": "Clave de API de Semantic Scholar (opcional)",
        "fr": "Clé API Semantic Scholar (facultative)",
        "de": "Semantic-Scholar-API-Schlüssel (optional)",
        "ko": "Semantic Scholar API 키 (선택)",
        "pt": "Chave de API do Semantic Scholar (opcional)",
        "ru": "API-ключ Semantic Scholar (необяз.)",
        "it": "Chiave API Semantic Scholar (opzionale)",
        "vi": "Khóa API Semantic Scholar (tùy chọn)",
        "hi": "Semantic Scholar API कुंजी (वैकल्पिक)",
        "id": "Kunci API Semantic Scholar (opsional)",
    },
    "settings.ncbi_key": {
        "en": "NCBI / PubMed API key (optional)",
        "zh-tw": "NCBI / PubMed API 金鑰(選填)",
        "zh-cn": "NCBI / PubMed API 密钥(可选)",
        "ja": "NCBI / PubMed API キー(任意)",
        "es": "Clave de API de NCBI / PubMed (opcional)",
        "fr": "Clé API NCBI / PubMed (facultative)",
        "de": "NCBI- / PubMed-API-Schlüssel (optional)",
        "ko": "NCBI / PubMed API 키 (선택)",
        "pt": "Chave de API do NCBI / PubMed (opcional)",
        "ru": "API-ключ NCBI / PubMed (необяз.)",
        "it": "Chiave API NCBI / PubMed (opzionale)",
        "vi": "Khóa API NCBI / PubMed (tùy chọn)",
        "hi": "NCBI / PubMed API कुंजी (वैकल्पिक)",
        "id": "Kunci API NCBI / PubMed (opsional)",
    },
    "settings.ieee_key": {
        "en": "IEEE Xplore API key (optional)",
        "zh-tw": "IEEE Xplore API 金鑰(選填)",
        "zh-cn": "IEEE Xplore API 密钥(可选)",
        "ja": "IEEE Xplore API キー(任意)",
        "es": "Clave de API de IEEE Xplore (opcional)",
        "fr": "Clé API IEEE Xplore (facultative)",
        "de": "IEEE-Xplore-API-Schlüssel (optional)",
        "ko": "IEEE Xplore API 키 (선택)",
        "pt": "Chave de API do IEEE Xplore (opcional)",
        "ru": "API-ключ IEEE Xplore (необяз.)",
        "it": "Chiave API IEEE Xplore (opzionale)",
        "vi": "Khóa API IEEE Xplore (tùy chọn)",
        "hi": "IEEE Xplore API कुंजी (वैकल्पिक)",
        "id": "Kunci API IEEE Xplore (opsional)",
    },
    "settings.springer_key": {
        "en": "Springer Nature API key (optional)",
        "zh-tw": "Springer Nature API 金鑰(選填)",
        "zh-cn": "Springer Nature API 密钥(可选)",
        "ja": "Springer Nature API キー(任意)",
        "es": "Clave de API de Springer Nature (opcional)",
        "fr": "Clé API Springer Nature (facultative)",
        "de": "Springer-Nature-API-Schlüssel (optional)",
        "ko": "Springer Nature API 키 (선택)",
        "pt": "Chave de API do Springer Nature (opcional)",
        "ru": "API-ключ Springer Nature (необяз.)",
        "it": "Chiave API Springer Nature (opzionale)",
        "vi": "Khóa API Springer Nature (tùy chọn)",
        "hi": "Springer Nature API कुंजी (वैकल्पिक)",
        "id": "Kunci API Springer Nature (opsional)",
    },
    "settings.crossref_token": {
        "en": "Crossref Plus token (optional)",
        "zh-tw": "Crossref Plus token(選填)",
        "zh-cn": "Crossref Plus token(可选)",
        "ja": "Crossref Plus トークン(任意)",
        "es": "Token de Crossref Plus (opcional)",
        "fr": "Jeton Crossref Plus (facultatif)",
        "de": "Crossref-Plus-Token (optional)",
        "ko": "Crossref Plus 토큰 (선택)",
        "pt": "Token do Crossref Plus (opcional)",
        "ru": "Токен Crossref Plus (необяз.)",
        "it": "Token Crossref Plus (opzionale)",
        "vi": "Token Crossref Plus (tùy chọn)",
        "hi": "Crossref Plus टोकन (वैकल्पिक)",
        "id": "Token Crossref Plus (opsional)",
    },
    "settings.contact_email": {
        "en": "Contact email (Crossref polite pool)",
        "zh-tw": "聯絡 email(Crossref polite pool)",
        "zh-cn": "联系 email(Crossref polite pool)",
        "ja": "連絡先メール(Crossref polite pool)",
        "es": "Correo de contacto (Crossref polite pool)",
        "fr": "E-mail de contact (Crossref polite pool)",
        "de": "Kontakt-E-Mail (Crossref Polite Pool)",
        "ko": "연락 이메일 (Crossref polite pool)",
        "pt": "E-mail de contato (Crossref polite pool)",
        "ru": "Контактный e-mail (Crossref polite pool)",
        "it": "Email di contatto (Crossref polite pool)",
        "vi": "Email liên hệ (Crossref polite pool)",
        "hi": "संपर्क ईमेल (Crossref polite pool)",
        "id": "Email kontak (Crossref polite pool)",
    },
    "settings.cookies_file": {
        "en": "PDF cookies file (Netscape format)",
        "zh-tw": "PDF cookies 檔案(Netscape 格式)",
        "zh-cn": "PDF cookies 文件(Netscape 格式)",
        "ja": "PDF cookies ファイル(Netscape 形式)",
        "es": "Archivo de cookies PDF (formato Netscape)",
        "fr": "Fichier de cookies PDF (format Netscape)",
        "de": "PDF-Cookies-Datei (Netscape-Format)",
        "ko": "PDF cookies 파일 (Netscape 형식)",
        "pt": "Arquivo de cookies PDF (formato Netscape)",
        "ru": "Файл cookies для PDF (формат Netscape)",
        "it": "File cookies PDF (formato Netscape)",
        "vi": "Tệp cookies PDF (định dạng Netscape)",
        "hi": "PDF कुकीज़ फ़ाइल (Netscape फॉर्मेट)",
        "id": "Berkas cookies PDF (format Netscape)",
    },
    "settings.browse_button": {
        "en": "Browse…",
        "zh-tw": "瀏覽…",
        "zh-cn": "浏览…",
        "ja": "参照…",
        "es": "Examinar…",
        "fr": "Parcourir…",
        "de": "Durchsuchen…",
        "ko": "찾아보기…",
        "pt": "Procurar…",
        "ru": "Обзор…",
        "it": "Sfoglia…",
        "vi": "Duyệt…",
        "hi": "ब्राउज़ करें…",
        "id": "Telusuri…",
    },
    "settings.save_button": {
        "en": "Save",
        "zh-tw": "儲存",
        "zh-cn": "保存",
        "ja": "保存",
        "es": "Guardar",
        "fr": "Enregistrer",
        "de": "Speichern",
        "ko": "저장",
        "pt": "Salvar",
        "ru": "Сохранить",
        "it": "Salva",
        "vi": "Lưu",
        "hi": "सहेजें",
        "id": "Simpan",
    },
    "settings.saved_message": {
        "en": "Settings saved. Restart the app to apply.",
        "zh-tw": "設定已儲存,重新啟動 App 後生效。",
        "zh-cn": "设置已保存,重启 App 后生效。",
        "ja": "設定を保存しました。アプリを再起動すると反映されます。",
        "es": "Ajustes guardados. Reinicie la app para aplicar.",
        "fr": "Paramètres enregistrés. Redémarrez l'app pour appliquer.",
        "de": "Einstellungen gespeichert. App neu starten zum Anwenden.",
        "ko": "설정이 저장되었습니다. 적용하려면 앱을 재시작하세요.",
        "pt": "Configurações salvas. Reinicie o app para aplicar.",
        "ru": "Настройки сохранены. Перезапустите приложение.",
        "it": "Impostazioni salvate. Riavvia l'app per applicare.",
        "vi": "Đã lưu cài đặt. Khởi động lại app để áp dụng.",
        "hi": "सेटिंग्स सहेजी गईं। लागू करने के लिए ऐप पुनः शुरू करें।",
        "id": "Pengaturan disimpan. Mulai ulang app untuk menerapkan.",
    },
    "settings.cookies_dialog_title": {
        "en": "Choose cookies file",
        "zh-tw": "選擇 cookies 檔案",
        "zh-cn": "选择 cookies 文件",
        "ja": "cookies ファイルを選択",
        "es": "Elija el archivo de cookies",
        "fr": "Choisir le fichier de cookies",
        "de": "Cookies-Datei auswählen",
        "ko": "cookies 파일 선택",
        "pt": "Escolha o arquivo de cookies",
        "ru": "Выберите файл cookies",
        "it": "Scegli il file cookies",
        "vi": "Chọn tệp cookies",
        "hi": "कुकीज़ फ़ाइल चुनें",
        "id": "Pilih berkas cookies",
    },
}


def normalise_language(code: str | None) -> str:
    """Map any string to a supported GUI language, defaulting to English."""
    if not code:
        return DEFAULT_LANGUAGE
    lowered = code.strip().lower().replace("_", "-")
    if lowered in SUPPORTED_LANGUAGES:
        return lowered
    # Strip locale subtags (zh-Hant-TW → zh-tw) by keeping the first
    # two segments only — covers PySide6 / QLocale strings.
    segments = lowered.split("-")
    if len(segments) >= 2:
        prefix = f"{segments[0]}-{segments[-1]}"
        if prefix in SUPPORTED_LANGUAGES:
            return prefix
    if segments and segments[0] in SUPPORTED_LANGUAGES:
        return segments[0]
    return DEFAULT_LANGUAGE


def t(key: str, language: str = DEFAULT_LANGUAGE, /, **fmt: object) -> str:
    """Translate a UI key, with optional format placeholders.

    Returns the English string when ``key`` is missing for ``language``
    (so adding a key without translating it yet is a soft failure). If
    the key is missing from English too the key itself is returned —
    a visible bug marker the test suite catches via the coverage tests.
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
