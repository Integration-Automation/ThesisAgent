"""i18n table coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

from autopapertoppt.exporters.i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    normalise_language,
    strings_for,
    t,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]

_REQUIRED_KEYS: set[str] = set(strings_for(DEFAULT_LANGUAGE).keys())


@pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
def test_every_language_has_every_key(lang: str):
    table = strings_for(lang)
    missing = _REQUIRED_KEYS - set(table.keys())
    assert not missing, f"{lang} is missing keys: {missing}"


def test_normalise_language_fallback():
    assert normalise_language(None) == DEFAULT_LANGUAGE
    assert normalise_language("klingon") == DEFAULT_LANGUAGE
    assert normalise_language("ZH_TW") == "zh-tw"
    assert normalise_language("zh-cn") == "zh-cn"


def test_t_formats_kwargs():
    assert "5" in t("en", "paper_n_of_m", n=5, m=10)
    assert "5" in t("zh-tw", "paper_n_of_m", n=5, m=10)


def test_unknown_key_falls_back_to_self():
    assert t("en", "missing_key_does_not_exist") == "missing_key_does_not_exist"


@pytest.mark.parametrize(
    "lang,expected_agenda",
    [
        ("en", "Agenda"),
        ("zh-tw", "議程"),
        ("zh-cn", "议程"),
        ("ja", "目次"),
        ("es", "Índice"),
        ("fr", "Sommaire"),
        ("de", "Inhalt"),
        ("ko", "목차"),
        ("pt", "Sumário"),
        ("ru", "Содержание"),
        ("it", "Indice"),
        ("vi", "Mục lục"),
        ("hi", "विषय-सूची"),
        ("id", "Daftar Isi"),
    ],
)
def test_agenda_string_per_language(lang: str, expected_agenda: str):
    assert t(lang, "agenda") == expected_agenda


def test_section_limitations_is_standalone():
    """``section_limitations`` must be just "Limitations" so the
    Limitations & Future Work slide title doesn't render as
    "Limitations & Future Work & Future Work" after the exporter
    concatenates ``section_future_work`` onto it."""
    assert t("en", "section_limitations") == "Limitations"
    assert "Future Work" not in t("en", "section_limitations")


def test_paper_n_of_m_format_works_for_all_languages():
    """The {n}/{m} placeholders must render correctly for every language."""
    for lang in SUPPORTED_LANGUAGES:
        rendered = t(lang, "paper_n_of_m", n=3, m=7)
        assert "3" in rendered, f"{lang}: n=3 not in output {rendered!r}"
        assert "7" in rendered, f"{lang}: m=7 not in output {rendered!r}"


def test_every_supported_language_has_readme_and_sphinx_tree():
    """Every value in SUPPORTED_LANGUAGES must have a README and a Sphinx
    index.rst file. This prevents the i18n table and the user-facing docs
    from drifting apart — if a new language is added to one, the test
    fails loudly until the other is filled in too.

    File-name convention: English is the canonical ``README.md`` at the
    repo root; every other language lives under ``readmes/README.<lang>.md``
    plus its own ``docs/<lang>/index.rst``. The zh-TW README file uses the
    historical mixed-case ``zh-TW`` to match the Languages: navigation
    links across the repo; everywhere else the folder/code is lowercase.
    """
    readme_overrides = {
        "en": "README.md",
        "zh-tw": "readmes/README.zh-TW.md",
        "zh-cn": "readmes/README.zh-CN.md",
    }
    missing_readme: list[str] = []
    missing_sphinx: list[str] = []
    for lang in SUPPORTED_LANGUAGES:
        readme_name = readme_overrides.get(lang, f"readmes/README.{lang}.md")
        if not (_REPO_ROOT / readme_name).is_file():
            missing_readme.append(f"{lang} (expected {readme_name})")
        sphinx_index = _REPO_ROOT / "docs" / lang / "index.rst"
        if not sphinx_index.is_file():
            missing_sphinx.append(f"{lang} (expected docs/{lang}/index.rst)")
    assert not missing_readme, (
        f"SUPPORTED_LANGUAGES lists these without a README: {missing_readme}"
    )
    assert not missing_sphinx, (
        f"SUPPORTED_LANGUAGES lists these without a Sphinx index: {missing_sphinx}"
    )


def test_sphinx_master_toctree_lists_every_language():
    """The master docs/index.rst toctree must reference every language's
    index.rst — otherwise a translated tree exists on disk but is invisible
    to Sphinx's navigation."""
    master = (_REPO_ROOT / "docs" / "index.rst").read_text(encoding="utf-8")
    for lang in SUPPORTED_LANGUAGES:
        expected = f"{lang}/index"
        assert expected in master, (
            f"docs/index.rst is missing {expected!r} in its Languages toctree"
        )


def test_prune_irrelevant_downloads_rule_in_all_14_languages():
    """The prune-irrelevant-downloads anti-pattern must appear in every
    language's README and Sphinx index.rst. Catches future drift where
    a new language gets added to ``SUPPORTED_LANGUAGES`` but its README
    + Sphinx miss this load-bearing rule.

    Each language has a distinctive marker phrase — present in the
    Don't bullet — so a one-line regex check per language is enough.
    """
    import re

    markers = {
        "en": r"irrelevant downloads in the run",
        "zh-tw": r"不相關下載留在",
        "zh-cn": r"不相关下载留在",
        "ja": r"無関係なダウンロード",
        "es": r"descargas irrelevantes",
        "fr": r"téléchargements non pertinents",
        "de": r"irrelevanten? Downloads",
        "ko": r"무관한 다운로드",
        "pt": r"downloads irrelevantes",
        "ru": r"нерелевантные загрузки",
        "it": r"download non pertinenti",
        "vi": r"tải xuống không liên quan",
        "hi": r"अप्रासंगिक डाउनलोड",
        "id": r"unduhan tidak relevan",
    }
    readme_overrides = {
        "en": "README.md",
        "zh-tw": "readmes/README.zh-TW.md",
        "zh-cn": "readmes/README.zh-CN.md",
    }
    missing: list[str] = []
    for lang, marker in markers.items():
        readme_path = _REPO_ROOT / readme_overrides.get(lang, f"readmes/README.{lang}.md")
        sphinx_path = _REPO_ROOT / "docs" / lang / "index.rst"
        if not re.search(marker, readme_path.read_text(encoding="utf-8")):
            missing.append(f"README {lang}: missing prune-irrelevant marker")
        if not re.search(marker, sphinx_path.read_text(encoding="utf-8")):
            missing.append(f"Sphinx {lang}: missing prune-irrelevant marker")
    assert not missing, (
        "Prune-irrelevant-downloads rule missing from some language docs:\n  "
        + "\n  ".join(missing)
    )


def test_zh_tw_files_use_traditional_chinese_vocabulary():
    """Common Simplified-Chinese-only terms that must not leak into zh-tw
    surfaces. Each pattern uses a negative-lookbehind / negative-lookahead
    to exclude legitimate occurrences (e.g. ``算法`` inside ``演算法``,
    ``信息`` inside ``互信息`` — wait, ``互信息`` itself is S; the T form
    is ``互資訊``, so the pattern catches bare ``信息`` AND the compound).

    Caught real bugs that this test was written for: ``互信息`` (mutual
    information) leaking into a zh-tw regen script — the T-Chinese form
    is ``互資訊``.
    """
    import re

    s_only_patterns = [
        # Character-level (Simplified hanzi). Most of these are caught by
        # any orthography pass — bare 信息 / 网络 / 算法 / 实现 etc.
        (re.compile(r"互?信息"), "信息 → 資訊 (or 互信息 → 互資訊)"),
        (re.compile(r"(?<!演)算法"), "算法 → 演算法"),
        (re.compile(r"软件|软体"), "軟體"),
        (re.compile(r"数据(?!庫)"), "数据 → 資料"),
        (re.compile(r"网络"), "网络 → 網路"),
        (re.compile(r"默认"), "默认 → 預設"),
        (re.compile(r"函数"), "函数 → 函式"),
        (re.compile(r"(?<![連子])接口"), "接口 → 介面"),
        (re.compile(r"缓存"), "缓存 → 快取"),
        (re.compile(r"调试"), "调试 → 偵錯"),
        (re.compile(r"训练"), "训练 → 訓練"),
        (re.compile(r"学习"), "学习 → 學習"),
        (re.compile(r"输入"), "输入 → 輸入"),
        (re.compile(r"输出"), "输出 → 輸出"),
        (re.compile(r"复杂"), "复杂 → 複雜"),
        (re.compile(r"实现"), "实现 → 實作"),
        (re.compile(r"实验"), "实验 → 實驗"),
        (re.compile(r"攻击"), "攻击 → 攻擊"),
        (re.compile(r"防御"), "防御 → 防禦"),
        # Lexicon-level — these use Traditional characters but are
        # Simplified-Chinese vocabulary calques. The plain
        # T-vs-S-hanzi check does NOT catch them; this layer is the
        # whole reason language-vocabulary-check exists.
        (re.compile(r"內存"), "內存 → 記憶體"),
        (re.compile(r"魯棒"), "魯棒(性) → 穩健(性)"),
        (re.compile(r"視頻"), "視頻 → 影片"),
        (re.compile(r"屏幕"), "屏幕 → 螢幕"),
        (re.compile(r"鼠標"), "鼠標 → 滑鼠"),
        (re.compile(r"(?<![駭])黑客"), "黑客 → 駭客"),
        (re.compile(r"服務器"), "服務器 → 伺服器"),
        (re.compile(r"數據庫"), "數據庫 → 資料庫"),
        (re.compile(r"操作系統"), "操作系統 → 作業系統"),
        (re.compile(r"應用程序"), "應用程序 → 應用程式"),
        (re.compile(r"(?<![電一程])計算機(?![ 視程])"), "計算機 → 電腦"),
        (re.compile(r"字符串"), "字符串 → 字串"),
        (re.compile(r"(?<![字])字符(?![元串集])"), "字符 → 字元"),
        (re.compile(r"線程"), "線程 → 執行緒"),
        (re.compile(r"(?<![行])進程(?![師])"), "進程 → 行程 / 處理程序"),
        (re.compile(r"隊列"), "隊列 → 佇列"),
        (re.compile(r"帶寬"), "帶寬 → 頻寬"),
        (re.compile(r"(?<![核])內核"), "內核 → 核心"),
        (re.compile(r"內置"), "內置 → 內建"),
        (re.compile(r"鏈接"), "鏈接 → 連結"),
        (re.compile(r"加載"), "加載 → 載入"),
        (re.compile(r"(?<![預])設置"), "設置 → 設定"),
        (re.compile(r"集群"), "集群 → 叢集"),
        (re.compile(r"模塊"), "模塊 → 模組"),
        (re.compile(r"集成"), "集成 → 整合"),
        (re.compile(r"重定向"), "重定向 → 重新導向"),
        (re.compile(r"主頁"), "主頁 → 首頁"),
        (re.compile(r"(?<![組])編程"), "編程 → 程式設計"),
        (re.compile(r"賬戶"), "賬戶 → 帳戶"),
        (re.compile(r"賬號"), "賬號 → 帳號"),
        (re.compile(r"菜單"), "菜單 → 選單"),
        (re.compile(r"對話框"), "對話框 → 對話方塊"),
        (re.compile(r"句柄"), "句柄 → 控制代碼"),
        (re.compile(r"(?<![異])異常(?![案的快只新終難艱])"), "異常 → 例外"),
        # Hardware vocabulary — Traditional chars, Simplified words.
        (re.compile(r"硬件"), "硬件 → 硬體"),
        (re.compile(r"主板"), "主板 → 主機板"),
        (re.compile(r"顯卡"), "顯卡 → 顯示卡"),
        (re.compile(r"硬盤"), "硬盤 → 硬碟"),
        (re.compile(r"軟盤"), "軟盤 → 軟碟"),
        (re.compile(r"光盤"), "光盤 → 光碟"),
        # Printing / output devices.
        (re.compile(r"打印"), "打印(機) → 列印(機 → 印表機)"),
        # Crypto / data structures / variables.
        (re.compile(r"密鑰"), "密鑰 → 金鑰"),
        (re.compile(r"數組"), "數組 → 陣列"),
        # `不變量` (invariant, math / formal-verification context) is
        # accepted in TW, so exclude it. Bare `變量` (= variable) is S-only.
        (re.compile(r"(?<![不])變量"), "變量 → 變數"),
        (re.compile(r"字節"), "字節 → 位元組 (or just 'byte')"),
        # `比特` IS legit inside `比特幣` (bitcoin, accepted in TW), so
        # exclude that one compound with a negative-lookahead.
        (re.compile(r"比特(?!幣)"), "比特 → 位元 (or just 'bit')"),
        # Comments / templates / tracking / async.
        (re.compile(r"注釋"), "注釋 → 註解 (or 註釋 with 註)"),
        (re.compile(r"模板"), "模板 → 範本"),
        (re.compile(r"跟蹤"), "跟蹤 → 追蹤"),
        (re.compile(r"異步"), "異步 → 非同步"),
        # Ports + UI elements.
        (re.compile(r"串口"), "串口 → 序列埠"),
        (re.compile(r"圖標"), "圖標 → 圖示"),
        # Display / media.
        (re.compile(r"高清"), "高清 → 高畫質"),
        (re.compile(r"寬屏"), "寬屏 → 寬螢幕"),
        # Filesystem / messaging.
        (re.compile(r"信道"), "信道 → 通道 / 頻道"),
        (re.compile(r"鏡像文件"), "鏡像文件 → 映像檔"),
        (re.compile(r"文件夾"), "文件夾 → 資料夾"),
        (re.compile(r"短信"), "短信 → 簡訊"),
        # Network — Traditional chars, Simplified words.
        (re.compile(r"網絡"), "網絡 → 網路"),
        (re.compile(r"互聯網"), "互聯網 → 網際網路"),
        (re.compile(r"數據包"), "數據包 → 封包"),
        (re.compile(r"報文"), "報文 → 訊息"),
        (re.compile(r"抓包"), "抓包 → 封包擷取"),
        (re.compile(r"套接字"), "套接字 → 通訊端 (or 'socket')"),
        (re.compile(r"交換機"), "交換機 → 交換器"),
        # ML / math / stats.
        (re.compile(r"歸一化"), "歸一化 → 標準化 / 正規化"),
        (re.compile(r"概率"), "概率 → 機率"),
        (re.compile(r"方差"), "方差 → 變異數"),
        (re.compile(r"標量"), "標量 → 純量"),
        # Programming.
        (re.compile(r"哈希"), "哈希 → 雜湊"),
        (re.compile(r"遞歸"), "遞歸 → 遞迴"),
        (re.compile(r"死循環"), "死循環 → 死迴圈"),
        (re.compile(r"析構"), "析構 → 解構"),
        (re.compile(r"常量"), "常量 → 常數"),
        (re.compile(r"對象導向"), "對象導向 → 物件導向"),
        # Files / DB / config.
        (re.compile(r"配置文件"), "配置文件 → 設定檔 / 組態檔"),
        (re.compile(r"文件名"), "文件名 → 檔名"),
        (re.compile(r"擴展名"), "擴展名 → 副檔名"),
        (re.compile(r"字段"), "字段 → 欄位"),
        (re.compile(r"死鎖"), "死鎖 → 死結"),
        # Cloud / infra.
        (re.compile(r"雲計算"), "雲計算 → 雲端運算"),
        (re.compile(r"雲存儲"), "雲存儲 → 雲端儲存"),
        (re.compile(r"沙盒"), "沙盒 → 沙箱"),
        # Hardware / system / media.
        (re.compile(r"寄存器"), "寄存器 → 暫存器"),
        (re.compile(r"主存(?!款)"), "主存 → 主記憶體"),
        (re.compile(r"外設"), "外設 → 周邊設備"),
        (re.compile(r"批處理"), "批處理 → 批次處理"),
        (re.compile(r"攝像頭"), "攝像頭 → 攝影機 / 鏡頭"),
        (re.compile(r"(?<![拍])攝像(?!記)"), "攝像 → 攝影"),
        (re.compile(r"充電寶"), "充電寶 → 行動電源"),
        # UI widgets.
        (re.compile(r"滑塊"), "滑塊 → 滑桿"),
        (re.compile(r"滾動條"), "滾動條 → 捲軸"),
        (re.compile(r"復選框"), "復選框 → 核取方塊"),
        (re.compile(r"單選框"), "單選框 → 選項按鈕"),
        (re.compile(r"下拉框"), "下拉框 → 下拉選單"),
        (re.compile(r"標籤頁"), "標籤頁 → 索引標籤"),
        (re.compile(r"工具欄"), "工具欄 → 工具列"),
        (re.compile(r"狀態欄"), "狀態欄 → 狀態列"),
        (re.compile(r"任務欄"), "任務欄 → 工作列"),
        (re.compile(r"通知欄"), "通知欄 → 通知列"),
        (re.compile(r"彈窗"), "彈窗 → 彈出視窗"),
        # Verbs.
        (re.compile(r"搜索"), "搜索 → 搜尋"),
        (re.compile(r"查找"), "查找 → 尋找"),
        # Round 4 — more OOP / type-system / language-construct terms.
        (re.compile(r"多態"), "多態 → 多型"),
        (re.compile(r"重定義"), "重定義 → 重新定義 / 覆寫"),
        (re.compile(r"解引用"), "解引用 → 解參考"),
        (re.compile(r"標識符"), "標識符 → 識別字"),
        (re.compile(r"動態庫"), "動態庫 → 動態函式庫"),
        (re.compile(r"靜態庫"), "靜態庫 → 靜態函式庫"),
        (re.compile(r"共享庫"), "共享庫 → 共用函式庫"),
        # Mobile / touch / screen specifics.
        (re.compile(r"觸屏"), "觸屏 → 觸控螢幕"),
        (re.compile(r"觸摸"), "觸摸 → 觸控"),
        (re.compile(r"全屏"), "全屏 → 全螢幕"),
        (re.compile(r"截屏"), "截屏 → 螢幕擷取 / 截圖"),
        (re.compile(r"顯示屏"), "顯示屏 → 螢幕 / 顯示器"),
        # Audio / video.
        (re.compile(r"音頻"), "音頻 → 音訊"),
        (re.compile(r"音視頻"), "音視頻 → 影音"),
        (re.compile(r"視頻會議"), "視頻會議 → 視訊會議"),
        # Storage compounds.
        (re.compile(r"U盤"), "U盤 → 隨身碟"),
        (re.compile(r"雲盤"), "雲盤 → 雲端硬碟"),
        (re.compile(r"網盤"), "網盤 → 網路硬碟"),
        (re.compile(r"系統盤"), "系統盤 → 系統碟"),
        (re.compile(r"啟動盤"), "啟動盤 → 開機磁碟"),
        # Networking.
        (re.compile(r"組播"), "組播 → 多播"),
        (re.compile(r"廣域網"), "廣域網 → 廣域網路 (WAN)"),
        (re.compile(r"局域網"), "局域網 → 區域網路 (LAN)"),
        # Data structures.
        (re.compile(r"鏈表"), "鏈表 → 鏈結串列 / 連結串列"),
        (re.compile(r"二叉樹"), "二叉樹 → 二元樹"),
        (re.compile(r"散列表"), "散列表 → 雜湊表"),
        # Math.
        (re.compile(r"素數"), "素數 → 質數"),
        (re.compile(r"整型"), "整型 → 整數 / 整數型別"),
        (re.compile(r"均值"), "均值 → 平均值"),
        # ML / DB / DevOps.
        (re.compile(r"激活"), "激活 → 啟用"),
        (re.compile(r"存儲過程"), "存儲過程 → 預存程序"),
        (re.compile(r"灰度發布"), "灰度發布 → 灰階發布"),
        # UI / desktop / interaction.
        (re.compile(r"進度條"), "進度條 → 進度列"),
        (re.compile(r"復選"), "復選 → 核取"),
        (re.compile(r"單擊"), "單擊 → 點擊 / 按一下"),
        (re.compile(r"拖拽"), "拖拽 → 拖曳"),
        (re.compile(r"任務管理器"), "任務管理器 → 工作管理員"),
        (re.compile(r"文件管理器"), "文件管理器 → 檔案管理員 / 檔案總管"),
        (re.compile(r"注冊表"), "注冊表 → 登錄檔"),
        # Round 5 — overflow / escape / punctuation / pixels / images.
        (re.compile(r"溢出"), "溢出 → 溢位 (overflow / under-)"),
        (re.compile(r"內聯"), "內聯 → 內嵌 / 行內"),
        (re.compile(r"轉義"), "轉義 → 跳脫 (escape char)"),
        (re.compile(r"反斜杠"), "反斜杠 → 反斜線"),
        (re.compile(r"(?<!反)斜杠"), "斜杠 → 斜線"),
        (re.compile(r"方括號"), "方括號 → 中括號"),
        (re.compile(r"數字化"), "數字化 → 數位化"),
        (re.compile(r"數字簽名"), "數字簽名 → 數位簽名"),
        (re.compile(r"分辨率"), "分辨率 → 解析度"),
        (re.compile(r"矢量"), "矢量 → 向量"),
        (re.compile(r"響應"), "響應 → 回應"),
        # T-char Simplified-vocab — the standalone form 軟件 that the
        # existing char-level 软件 pattern misses. CRITICAL.
        (re.compile(r"軟件"), "軟件 → 軟體"),
        # Documents.
        (re.compile(r"文檔"), "文檔 → 文件 / 說明文件 (S `文檔` = document)"),
        (re.compile(r"文本框"), "文本框 → 文字方塊"),
        (re.compile(r"縮略圖"), "縮略圖 → 縮圖"),
        (re.compile(r"二維碼"), "二維碼 → 二維條碼 / QR code"),
        # Addresses / IPs.
        (re.compile(r"IP\s*地址"), "IP地址 → IP 位址"),
        (re.compile(r"物理地址"), "物理地址 → 實體位址"),
        (re.compile(r"MAC\s*地址"), "MAC 地址 → MAC 位址"),
        # Alerts / errors.
        (re.compile(r"報警"), "報警 → 警報"),
        # Source / footnotes.
        (re.compile(r"源代碼"), "源代碼 → 原始碼"),
        (re.compile(r"腳注"), "腳注 → 腳註"),
        # UI shortcuts / tray.
        (re.compile(r"快捷方式"), "快捷方式 → 捷徑"),
        (re.compile(r"系統托盤"), "系統托盤 → 系統匣"),
        # Security.
        (re.compile(r"殺毒"), "殺毒 → 防毒"),
        # Round 6 — T-char-S-vocab cache, GPU memory, segfault, mobile,
        # social, web headers, connections, stats, security, ownership,
        # quality, CLI / CI.
        # The bare T-char `緩存` was missed by the existing 缓存 (S-char)
        # pattern, parallel to round 5's 軟件 → 軟體 catch.
        (re.compile(r"緩存"), "緩存 → 快取"),
        (re.compile(r"顯存"), "顯存 → 顯示記憶體 / VRAM"),
        (re.compile(r"段錯誤"), "段錯誤 → 區段錯誤"),
        # Mobile / social.
        (re.compile(r"應用商店"), "應用商店 → 應用程式商店"),
        (re.compile(r"彩信"), "彩信 → 多媒體簡訊 (MMS)"),
        (re.compile(r"手機卡"), "手機卡 → SIM 卡"),
        (re.compile(r"鎖屏"), "鎖屏 → 鎖定螢幕"),
        (re.compile(r"屏保"), "屏保 → 螢幕保護"),
        (re.compile(r"點贊"), "點贊 → 按讚"),
        # HTTP / network connections.
        (re.compile(r"請求頭"), "請求頭 → 請求標頭"),
        (re.compile(r"響應頭"), "響應頭 → 回應標頭"),
        (re.compile(r"長連接"), "長連接 → 長連線"),
        (re.compile(r"短連接"), "短連接 → 短連線"),
        (re.compile(r"連接池"), "連接池 → 連線池"),
        # Statistics + ML.
        (re.compile(r"步長"), "步長 → 步幅"),
        (re.compile(r"置信區間"), "置信區間 → 信賴區間"),
        (re.compile(r"置信度"), "置信度 → 信賴度"),
        (re.compile(r"顯著水平"), "顯著水平 → 顯著水準"),
        # Security continued.
        (re.compile(r"入侵檢測"), "入侵檢測 → 入侵偵測"),
        (re.compile(r"防病毒"), "防病毒 → 防毒"),
        (re.compile(r"數字證書"), "數字證書 → 數位憑證"),
        # Filesystem ownership.
        (re.compile(r"屬主"), "屬主 → 擁有者 / 所有者"),
        (re.compile(r"屬組"), "屬組 → 群組 / 所屬群組"),
        # Quality / pipelines / CLI.
        (re.compile(r"服務質量"), "服務質量 → 服務品質 (QoS)"),
        (re.compile(r"命令行"), "命令行 → 命令列 (CLI)"),
        (re.compile(r"流水線"), "流水線 → 管線 (CI/CD pipeline)"),
        # Round 7 — common verbs / number bases / kernel terms / UI controls
        # that were in the agent doc but never in the test.
        # `復` (= again) vs `複` (= duplicate). S 復制 / 復用 conflate them.
        (re.compile(r"復制"), "復制 → 複製 (S `復` ≠ T `複`)"),
        (re.compile(r"復用"), "復用 → 重用"),
        (re.compile(r"編寫"), "編寫 → 撰寫"),
        # Number bases.
        (re.compile(r"二進制"), "二進制 → 二進位"),
        (re.compile(r"八進制"), "八進制 → 八進位"),
        (re.compile(r"十進制"), "十進制 → 十進位"),
        (re.compile(r"十六進制"), "十六進制 → 十六進位"),
        (re.compile(r"(?<![進])進制"), "進制 → 進位"),
        # Serial / parallel transmission.
        (re.compile(r"串行"), "串行 → 串列"),
        # Files / containers.
        (re.compile(r"壓縮文件"), "壓縮文件 → 壓縮檔"),
        (re.compile(r"二叉堆"), "二叉堆 → 二元堆積"),
        (re.compile(r"堆棧"), "堆棧 → 堆疊"),
        # Messaging.
        (re.compile(r"私聊"), "私聊 → 私訊"),
        # Kernel / syscalls.
        (re.compile(r"用戶態"), "用戶態 → 使用者模式"),
        (re.compile(r"系統調用"), "系統調用 → 系統呼叫"),
        (re.compile(r"(?<![失強])調用"), "調用 → 呼叫"),
        # Engineering / reverse engineering.
        (re.compile(r"反向工程"), "反向工程 → 逆向工程"),
        # UI controls / components.
        (re.compile(r"控件"), "控件 → 控制項"),
        (re.compile(r"部件"), "部件 → 元件"),
        # Identifiers / labels.
        (re.compile(r"標識(?![別字符碼])"), "標識 → 標示 (`標識符` already covered)"),
        # Image / pixel.
        (re.compile(r"圖元"), "圖元 → 像素"),
    ]
    zh_tw_paths = [
        _REPO_ROOT / "scripts" / "regen_llm_security_batch_zh_tw.py",
        _REPO_ROOT / "readmes" / "README.zh-TW.md",
        _REPO_ROOT / "docs" / "zh-tw" / "index.rst",
    ]
    offenders: list[str] = []
    for path in zh_tw_paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for regex, fix_hint in s_only_patterns:
            for match in regex.finditer(text):
                # Surrounding context for the failure message.
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 20)
                ctx = text[start:end].replace("\n", " ")
                offenders.append(
                    f"{path.name}: {fix_hint} — found at offset "
                    f"{match.start()}: ...{ctx}..."
                )
    assert not offenders, (
        "zh-tw files contain Simplified-Chinese-only vocabulary:\n  "
        + "\n  ".join(offenders)
    )


def test_section_limitations_avoids_future_work_collision_in_all_languages():
    """No language's section_limitations may include its own future-work
    word, otherwise the "Limitations & Future Work" slide title
    concatenation duplicates the phrase."""
    future_substrings = {
        "en": "Future Work",
        "zh-tw": "未來",
        "zh-cn": "未来",
        "ja": "今後",
        "es": "Trabajo futuro",
        "fr": "Travaux futurs",
        "de": "Künftige",
        "ko": "향후",
        "pt": "Trabalhos futuros",
        "ru": "Дальнейшие",
        "it": "Lavori futuri",
        "vi": "Hướng nghiên cứu",
        "hi": "भविष्य",
        "id": "Mendatang",
    }
    for lang, marker in future_substrings.items():
        assert marker not in t(lang, "section_limitations"), (
            f"{lang}: section_limitations contains future-work word {marker!r}"
        )
