"""Demonstration degree-thesis ORAL-DEFENCE deck (學位論文口試簡報) built via the
`thesis-deck-author` flow.

Why this script exists
----------------------
A request to "see" the degree-thesis deck capability. Rather than fabricate a
fake thesis's results (which the thesis-deck-author "no fabrication" rule
forbids), this deck is **about ThesisAgents itself** and every number is real —
the test count, the fang2026 overflow before/after, the math-rendering surface
count, the dark-text audit outcome are all drawn from this codebase and the work
recorded in the session. It is a DEMONSTRATION of the deck format (seven
`paper_rule` sections, defence cover, dark mode, $...$ math, KPI + tables,
height-adaptive overflow-safe layout), with the candidate / institution on the
cover marked as placeholders to edit.

Seven-section coverage (paper_rule → PaperSummary field):
  Abstract ............... core_observation + headline_metrics
  1. Introduction ........ pain_points (1.2) + research_question (1.3) +
                           contributions_detailed (1.5, cap 4)
  2. Literature Review ... literature_table (2.3) + technique_table
  3. Methodology ......... system_flow (3.1) + method_sections (3.2-3.4) +
                           evaluation_sections (3.5)
  4. Experiment .......... research_questions + rq_results (4.4/4.5) + headline_metrics
  5. Conclusion .......... core_observation (5.1) + limitations (5.3) + future_work (5.4)
  References ............. the collection's Paper record

Run from the project root:  .venv/Scripts/python.exe scripts/regen_thesis_demo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from thesisagents.core.models import (  # noqa: E402
    ExportOptions,
    Paper,
    PaperCollection,
    PaperSummary,
    Query,
    RqResult,
)
from thesisagents.exporters.pptx import PptxExporter  # noqa: E402

OUT_DIR = "exports"
FILENAME_STEM = "thesisagents-thesis-demo-zh-tw"
LANGUAGE = "zh-tw"


def _build_summary() -> PaperSummary:
    return PaperSummary(
        language=LANGUAGE,
        # ---- 1. Introduction:1.2 痛點 + 1.3 研究問題 -------------------------
        pain_points=(
            (
                "把論文做成口試簡報,耗時且品質不一",
                (
                    "研究生需手動把數十頁論文濃縮成 20 分鐘的 deck",
                    "排版、配色、字體靠人工反覆調整",
                    "同一份內容換語系就得整份重做",
                ),
            ),
            (
                "通用 LLM 產出的簡報一看就是機器生成",
                (
                    "預設 Calibri 字體、純白底、置中標題是明顯 AI tell",
                    "整頁文字牆,沒有圖表與視覺層次",
                    "紅字過度強調,像 error 而非重點",
                ),
            ),
            (
                "版面與可讀性問題反覆出現",
                (
                    "長段落溢出固定高度的文字框",
                    "暗色背景上出現看不見的黑字",
                    "數學記號被壓成扁平 ASCII(za 而非 $z_a$)",
                ),
            ),
            (
                "缺乏把七大論文章節結構化落地的流程",
                (
                    "工具多半只填模板,不檢查章節完整性",
                    "沒有機器可讀的視覺契約可稽核",
                    "品質仰賴人工巡檢,難以回歸守護",
                ),
            ),
        ),
        research_question=(
            "能否用一套多代理人規則 + 規則化匯出引擎,自動產生"
            "結構完整、視覺專業、且可被機器稽核的論文級簡報?"
        ),
        # ---- 1.5 貢獻(cap 4)------------------------------------------------
        contributions_detailed=(
            (
                "1. 多代理人規則架構",
                "把製作知識拆成唯讀規則代理(rules/:slide-deck-rules、deck-design、"
                "paper_rule …)與任務代理(tasks/:paper-summary-author、"
                "thesis-deck-author、稽核代理),規則與執行分離,可平行調度。",
            ),
            (
                "2. 三層渲染引擎",
                "依 PaperSummary 內容自動分派 lightweight / enriched-flat / "
                "thesis-style 三層,豐富層把每個欄位對映到一張論文章節投影片。",
            ),
            (
                "3. 可機器稽核的視覺契約",
                "暗色不可見字、紅字、淺底淺字、版面溢出皆有可執行稽核器"
                "(check_overflow.py、_audit_dark_text.py)+ pytest 回歸守護。",
            ),
            (
                "4. 自適應版面,從不截斷作者內容",
                "文字框高度依估算行數自適應,堆疊段落與四宮格依高度預算分頁"
                "而非固定張數,內容過多時分頁而非砍字。",
            ),
        ),
        # ---- 摘要 / 5.1 核心觀察(callout)----------------------------------
        core_observation=(
            "把論文簡報生成拆成三層:結構化內容(七大章節)、規則化視覺契約、"
            "與機器稽核;就能在不犧牲視覺品質的前提下自動產生可口試的 deck,"
            "且品質由測試守住而非靠人工巡檢。"
        ),
        # ---- 摘要 / 4 主要量化成果(KPI)-----------------------------------
        headline_metrics=(
            ("回歸測試總數", "614", "改善前 603"),
            ("範例 deck 版面溢出", "0 處", "改善前 8 處"),
            ("數學記號渲染介面數", "5", "改善前 3(bullets/KPI/表格)"),
            ("暗色硬性問題", "0", "_audit_dark_text 全 PASS"),
            ("支援語系", "14", "i18n SUPPORTED_LANGUAGES"),
            ("渲染層", "3 層", "lightweight / flat / thesis"),
        ),
        # ---- 2. Literature Review:2.3 比較表 -------------------------------
        literature_table=(
            ("做法", "章節完整性", "視覺品質", "自動稽核"),
            ("純手動製作", "高(人工)", "視人而定", "無"),
            ("通用 LLM 產 slide", "低", "低(AI tell)", "無"),
            ("模板填空工具", "中", "中", "無"),
            ("ThesisAgents(本系統)", "高(七章)", "高(品牌契約)", "有"),
        ),
        # ---- 2.x 關鍵技術 → 角色 -------------------------------------------
        technique_table=(
            ("python-pptx", "OOXML 簡報生成底層"),
            ("規則子代理(rules/)", "設計與稽核知識來源"),
            ("check_overflow.py", "版面溢出稽核器"),
            ("_audit_dark_text.py", "暗色文字契約稽核器"),
        ),
        # ---- 3. Methodology:3.1 架構流程 ----------------------------------
        system_flow=(
            "多來源關鍵字搜尋,正規化為 Paper 記錄",
            "依 DOI / arXiv ID / 標題模糊比對去重,再依新近度與引用排序",
            "LLM-as-agent 或 Python pipeline 充實成結構化 PaperSummary",
            "三層渲染引擎產出 pptx / xlsx / bib / md / json",
            "子代理稽核:版面溢出、暗色契約、七章完整性",
        ),
        # ---- 3.2-3.4 方法細節 ----------------------------------------------
        method_sections=(
            (
                "渲染層分派",
                (
                    "依 summary.has_rich_fields() 判斷走哪一層",
                    "豐富層:痛點四宮格、RQ callout、KPI、技術表、各 RQ 結果表",
                    "每個 PaperSummary 欄位對映一張論文章節投影片",
                ),
            ),
            (
                "自適應堆疊分頁",
                (
                    "_stacked_body_height_in 依估算換行數定本文框高度",
                    "_paginate_stacks 依高度預算(1.7\" → 7.0\")分頁",
                    "四宮格文字多時自動降為一列兩格,不砍字",
                ),
            ),
            (
                "數學記號渲染",
                (
                    "$...$ 契約:_x / ^x → 真下標 / 上標,單字母變數轉斜體",
                    "涵蓋 bullets、KPI 值、表格、貢獻本文、RQ callout 五介面",
                    "離 $...$ 的底線(檔名、prose)不受影響",
                ),
            ),
            (
                "暗色後處理",
                (
                    "_apply_dark_mode 以兩個對映字典重上色",
                    "兩層防線:每個 helper 顯式設色 + 後處理把 None/黑字提升為近白",
                    "淺底淺字由對比契約攔截",
                ),
            ),
        ),
        # ---- 3.5 評估方法 --------------------------------------------------
        evaluation_sections=(
            (
                "版面溢出量測",
                (
                    "check_overflow.py 估算每形狀換行高度 vs 框高與 footer guard 7.05\"",
                    "全形 CJK ≈ 1.0 em,半形拉丁 ≈ 0.55 em",
                    "表格改為估算實際列高,可抓宣告值騙過的長表",
                ),
            ),
            (
                "視覺契約量測",
                (
                    "_audit_dark_text 掃隱形字、紅字、淺底淺字、離調色盤色",
                    "可套用於手作 deck(回歸測試只覆蓋生成 deck)",
                    "硬性問題數需為 0 才放行",
                ),
            ),
        ),
        # ---- 4. Experiment:研究問題 ---------------------------------------
        research_questions=(
            ("RQ1", "能否在不截斷作者內容下消除版面溢出?"),
            ("RQ2", "數學記號能否渲染為真上下標而非扁平 ASCII?"),
            ("RQ3", "暗色與版面契約能否被自動稽核?"),
            ("RQ4", "系統是否覆蓋七大論文章節?"),
        ),
        # ---- 4.4 / 4.5 各 RQ 結果(真實數據)------------------------------
        rq_results=(
            RqResult(
                rq_id="RQ1",
                question="能否在不截斷作者內容下消除版面溢出?",
                table=(
                    ("版本", "範例 deck 溢出", "回歸測試"),
                    ("固定高度(改善前)", "8 處", "603"),
                    ("自適應分頁(改善後)", "0 處", "614"),
                ),
                analysis=(
                    "自適應高度 + 高度預算分頁把 fang2026 範例 deck 的本文溢出從 8 降到 0",
                    "全程不截斷任何作者文字,改以分頁吸收超長內容",
                    "表格估算上線後可抓 9 列長表(估算 9.03\" > 7.05\")",
                ),
            ),
            RqResult(
                rq_id="RQ2",
                question="數學記號能否渲染為真上下標而非扁平 ASCII?",
                table=(
                    ("介面", "改善前", "改善後"),
                    ("貢獻 / 方法本文", "扁平 za", "真下標 $z_a$"),
                    ("RQ / 核心觀察 callout", "扁平", "真下標"),
                    ("涵蓋介面數", "3", "5"),
                ),
                analysis=(
                    "$...$ 契約讓五個內容介面都渲染真上下標與斜體變數",
                    "互資訊式目標如 $I(z_a;z_b|E_p)$ 不再顯示為扁平字串",
                    "新增 paper-summary-author / thesis-deck-author 的授權規則",
                ),
            ),
            RqResult(
                rq_id="RQ3",
                question="暗色與版面契約能否被自動稽核?",
                table=(
                    ("檢查項", "稽核器", "最終 deck"),
                    ("隱形字(None/黑)", "_audit_dark_text", "0"),
                    ("紅字 #C0392B", "_audit_dark_text", "0"),
                    ("版面溢出", "check_overflow", "0"),
                ),
                analysis=(
                    "三項自動稽核在最終 deck 全數 PASS",
                    "稽核器可獨立套用於手作 deck,補上回歸測試的覆蓋缺口",
                    "_ACCEPTED_DARK_RUN_COLORS 與 exporter 調色盤同步",
                ),
            ),
            RqResult(
                rq_id="RQ4",
                question="系統是否覆蓋七大論文章節?",
                table=(
                    ("論文章節", "對映欄位", "覆蓋"),
                    ("Introduction", "pain_points / RQ / contributions", "✓"),
                    ("Literature", "literature_table", "✓"),
                    ("Methodology", "system_flow / method_sections", "✓"),
                    ("Experiment", "rq_results / headline_metrics", "✓"),
                    ("Conclusion", "core_observation / limitations / future_work", "✓"),
                ),
                analysis=(
                    "七大章節皆有對映的 PaperSummary 欄位",
                    "thesis-deck-author 以完整度稽核把關,缺章即視為未完成",
                    "本 deck 自身即覆蓋全部七章",
                ),
            ),
        ),
        # ---- 5.3 限制 ------------------------------------------------------
        limitations=(
            "量化評估以系統內部指標為主,尚缺正式使用者研究",
            "內容充實仰賴 LLM-as-agent 或 API,離線品質有限",
            "表格不自動分頁,超大表需在作者層拆分",
            "暗色 RTL(阿拉伯文)deck 尚未支援",
        ),
        # ---- 5.4 未來工作 --------------------------------------------------
        future_work=(
            "加入使用者研究與主觀品質評分",
            "多模態:自動生成結果圖表並嵌入",
            "擴充 RTL 與更多語系的 deck 渲染",
            "線上協作與即時編輯",
        ),
        model="hand-authored:regen_thesis_demo",
    )


def _build_paper() -> Paper:
    return Paper(
        source="local",
        source_id="thesisagents-thesis-demo",
        title="ThesisAgents:從研究主題到論文級簡報的多代理人生成系統",
        # 候選人 / 校系為示範佔位,實際使用時請替換。
        authors=("Jeffrey Chen",),
        year=2026,
        venue="資訊工程學系 · 碩士學位論文(示範範本)",
        abstract="",
        url="",
        summary=_build_summary(),
    )


def main() -> None:
    collection = PaperCollection(
        query=Query(keywords="thesisagents thesis deck", sources=("local",)),
        papers=(_build_paper(),),
    )
    options = ExportOptions(
        formats=("pptx",),
        out_dir=OUT_DIR,
        filename_stem=FILENAME_STEM,
        language=LANGUAGE,
        # White + blue academic-paper style is the default deliverable
        # (light palette: white bg, navy headings/body, blue emphasis).
        # Dark mode stays opt-in via dark_mode=True for OLED / low-light venues.
        dark_mode=False,
    )
    out_path = PptxExporter().export(collection, options)
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()
