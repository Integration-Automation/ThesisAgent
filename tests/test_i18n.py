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
