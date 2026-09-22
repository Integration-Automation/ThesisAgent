"""TCSE 研討會口頭報告簡報(十分鐘,第二版剪裁)for 陳冠穎、李文廷之 TCSE 論文
《基於大語言模型和思維鏈推理的程式碼審查框架》, built via the `thesis-deck-author`
flow.  SECOND cut of scripts/regen_chen2026_tcse.py — same paper, same numbers,
re-weighted emphasis:

  (1) 框架新增之工程功能(MCP / pre-commit / 無模型 triage / 十七項機制 / 報告與監控)
  (2) GitHub 與 GitLab 雙平台整合(GitLab 為 2026-07 新增)
  (3) 多模型推論後端(九種 BackendKind + Router / Ensemble / 仲裁)
  (4) 與其他論文之比較(文獻定位表,含 AutoReview 列)

實驗結果依 TCSE §5.1 之表-RQ 對應完整呈現三頁:表一 ↔ RQ1+RQ2、表二 ↔ RQ3
(LLM 評分五維全表)、表三 ↔ RQ4(人工評分五維全表)— 候選人 2026-07-03 指示
「五維全表要放」,故不再壓縮為單頁。

Source of truth
---------------
Hand-authored from the candidate's OWN conference manuscript + thesis + code
(all read in full):
  D:\\Codes\\Code-Review-Framework-Combining-Large-Language-Models-and-Chain-of-Thought-Reasoning
  - paper/TCSE_v2.8.docx  ... the conference manuscript this talk presents (PRIMARY)
  - paper/論文_v3.5.docx   ... the full thesis (文獻比較 表一 + §6.4 未來工作)
  - prthinker/             ... platforms / backends / MCP / triage 皆對照原始碼驗證

Every number is copied VERBATIM from the manuscripts — none invented, none
recomputed.  Known traps honoured:
  * CRSCORE++ headline uses the CURRENT Table 1 / §5.2 numbers
    (1.00 / 0.79 / 0.86 vs baseline 0.67 / 0.57 / 0.63, gemma-4-31B-it) — never
    the stale 0.86 / 0.64 / 0.83.
  * 程式碼預設模型是 Qwen/Qwen3-Coder-30B-A3B-Instruct;gemma-4-31B-it 是論文
    評估基座 — 本簡報不寫「框架預設 gemma」。
  * 誠實邊界(TCSE §3.2 末段):工程整合與十七項機制「已實作 + 單元測試,
    端到端品質效益未於本文評估」— 保留於工程頁尾句與限制頁,跨後端品質 /
    成本 / 延遲無實測數字,一律列為未來工作(論文 §6.4)。
  * Bitbucket 尚未實作,僅得列於未來工作(§6.4.3);GitHub / GitLab / Gitea
    已實作(PlatformAdapter)。

Ten-minute slot → 16 slides (after removing the exporter's duplicate tail
「貢獻總結」slide and restamping page numbers), ~40 s per content slide —
the two extra five-dimension result tables are read as「趨勢一致」evidence,
not cell-by-cell.
White + blue academic style;標楷體 + Times New Roman typography, English paper
title on the cover — same candidate requests as the defence deck, applied by the
``_restyle_deck`` post-pass (copied verbatim from regen_chen2026_tcse.py).

Run from the project root:
  .venv/Scripts/python.exe scripts/regen_chen2026_tcse_features.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from pptx import Presentation  # noqa: E402
from pptx.enum.text import MSO_AUTO_SIZE, PP_ALIGN  # noqa: E402
from pptx.oxml.ns import qn  # noqa: E402
from pptx.util import Inches, Pt  # noqa: E402

from thesisagents.core.models import (  # noqa: E402
    ExportOptions,
    Paper,
    PaperCollection,
    PaperSummary,
    Query,
    RqResult,
)
from thesisagents.exporters import overflow as _overflow  # noqa: E402
from thesisagents.exporters.pptx import (  # noqa: E402
    _BODY_WIDTH,
    _BRAND_GREY,
    _DARK_BODY_TEXT,
    _MARGIN_X,
    PptxExporter,
    _add_textbox,
    _set_east_asian_typeface,
)

_EMU_PER_INCH = 914400

OUT_DIR = "exports"
FILENAME_STEM = "chen2026-tcse-features-zh-tw"
LANGUAGE = "zh-tw"

# TCSE 論文標題(TCSE_v2.8.docx 逐字)— 中文為封面主標,英文由 _restyle_deck
# 補到封面副標槽。注意:這是研討會論文標題,非學位論文口試標題。
CHINESE_TITLE = "基於大語言模型和思維鏈推理的程式碼審查框架"
ENGLISH_TITLE = (
    "A Code Review Framework based on Large Language Models "
    "and Chain-of-Thought Reasoning"
)

# 與口試簡報一致的候選人指定字型(見 regen_chen2026_codereview.py 的說明)。
_CJK_FONT = "標楷體"          # DFKai-SB
_LATIN_FONT = "Times New Roman"

# TCSE 論文自己的 圖一 系統架構圖(自 TCSE 手稿 word/media 抽出,
# 2224×2500 透明底;TCSE 版為六層,非學位論文之八層)。
_FIG = _PROJECT_ROOT / "assets" / "figures" / "chen2026_tcse"


def _build_summary() -> PaperSummary:
    return PaperSummary(
        language=LANGUAGE,
        # ===== §1.2 研究動機 — 人工審查瓶頸 + LLM 三大問題(2×2 痛點格)=====
        # (與第一版簡報相同:同一篇論文、同一組動機)
        pain_points=(
            (
                "人工審查是品質把關的瓶頸",
                (
                    "審查可在整合測試前發現約 50–70% 缺陷",
                    "處理意見之時間隨意見數線性增加",
                    "靜態分析規則僵化,難及高層次判斷",
                ),
            ),
            (
                "問題一:幻覺,審查意見不可信",
                (
                    "編造看似合理卻不正確之內容",
                    "需在推理前注入可查證之專案規範",
                ),
            ),
            (
                "問題二:輸出不穩定,難以複現",
                (
                    "同一份程式碼前後給出不一致意見",
                    "需拆解任務、固定流程逐步推理",
                ),
            ),
            (
                "問題三:缺乏領域規範",
                (
                    "不認得個別專案之命名與安全規範",
                    "需動態注入規則,而非重新訓練",
                ),
            ),
        ),
        # ===== §1.2 末段核心動機(callout,渲染於痛點頁)====================
        research_question=(
            "如何在發揮 LLM(大型語言模型)語義理解能力之同時約束其輸出,"
            "使審查結果同時兼具可解釋性、一致性與可維護性?"
        ),
        # ===== §1.3 四項貢獻(依論文「其一~其四」原序;cap 4)===============
        contributions_detailed=(
            (
                "一、多階段 CoT 審查流程",
                "思維鏈(Chain-of-Thought, CoT)把審查結構化為五個可逐步推理且可追溯之"
                "循序步驟:摘要 → 初步審查 → 靜態分析 → 異味偵測 → 總結,每步留檔。",
            ),
            (
                "二、KD + QLoRA 輕量化部署",
                "知識蒸餾(KD)結合 QLoRA(4-bit 量化低秩微調),把教師模型之審查能力"
                "轉移至學生模型 gemma-4-31B-it,於有限運算資源下部署。",
            ),
            (
                "三、RAG 動態注入專案規則",
                "檢索增強生成(RAG)在推理前把個別專案之領域規範注入脈絡,"
                "不重新訓練模型即抑制幻覺、貼合專案規範。",
            ),
            (
                "四、LLM-as-a-Judge-Our 五維評估",
                "以獨立 LLM 當評審,細化為可讀性 / 可維護性 / 正確性 / 跨評論覆蓋 / "
                "簡潔性五項 1–100 分指標,並輔以人工評分交叉驗證。",
            ),
        ),
        # ===== 摘要級 KPI(表一 現行數字 + §5.2 消融;絕不用摘要之過時數字)===
        headline_metrics=(
            ("CRSCORE++ 完整性", "1.00", "自動評估指標 · 基準 0.67 · 該提的問題幾乎不漏"),
            ("CRSCORE++ 相關性", "0.86", "基準 0.63 · 評論貼合變更"),
            ("CRSCORE++ 簡潔性", "0.79", "基準 0.57 · 冗言更少"),
            ("消融:多階段提示詞", "+34 分", "百分制 · 微調 +2 分互補,缺一不可"),
        ),
        # ===== §2 相關研究 2.3/2.4 — 比較表取自學位論文表一(v3.5 勘誤版)=====
        # 本版剪裁強調「與其他論文之比較」:AutoReview 列一併保留(多代理對照)。
        # 候選人 2026-07 勘誤:CRScore / CRScore++ 微調欄為 ✓(已同步至 v3.5 表一)。
        literature_table=(
            ("方法 / 研究", "多階段", "微調", "RAG", "評估方式", "主要限制"),
            ("CRScore [7]", "✗", "✓", "✗", "3 維 1–5 分", "評分維度粗"),
            ("CRScore++ [10]", "✗", "✓", "✗", "3 維 + 強化學習", "缺深度語義"),
            ("LLaMA-Reviewer [16]", "✗", "✓ (LoRA)", "✗", "BLEU / ROUGE", "無語義層次"),
            ("LAURA [20]", "✗", "✓", "✓", "字串重疊", "未拆解推理"),
            ("AutoReview [19]", "✓ (多代理)", "✗", "✗", "案例研究", "缺量化評估"),
            ("本研究 Ours", "✓ (5 階段)", "✓ (QLoRA)", "✓", "5 維百分制 + 人工", "見研究限制頁"),
        ),
        # ===== §3.2 系統架構(TCSE 圖一;六層職責分離)=======================
        figures=(
            (
                "系統架構(TCSE 圖一):輸入 / 流程編排 / 檢索增強 / 提示模板 / 離線訓練 / 推論 六層",
                str(_FIG / "system_architecture.png"),
                (
                    "GitHub PR(Pull Request,程式碼合併申請)觸發 CI(持續整合)→ 單一入口載入模型與 LoRA 權重",
                    "流程編排把審查拆為五步,每步注入全域規則與 RAG 檢索之最相關 K 條規則後推理、即時寫入 .md",
                    "平台與推論後端皆以介面抽換:六層職責分離,是後續 GitHub / GitLab 與多後端擴充之邊界",
                ),
            ),
        ),
        # ===== §3 方法細節(先白話直覺、再技術;2 節/頁 → 3 頁)==============
        # 前 2 節 = 論文核心方法(與第一版相同);後 4 節 = 本版強調之工程功能,
        # 皆對照 prthinker 原始碼驗證,誠實邊界句保留於第 6 節與限制頁。
        method_sections=(
            (
                "多階段 CoT + 全域規則:每步只證一件事",
                (
                    "直覺:與其要模型一口氣審完,不如分五步、每步只做一件事 → 換取一致性",
                    "每步產物即時寫入獨立 .md 檔,長鏈中途失敗不失先前產出,可獨立追溯",
                    "7 條全域準則統一前綴,僅當 RAG 檢索命中才動態追加條件式第 8 條",
                ),
            ),
            (
                "RAG 注入 + KD/QLoRA:規範貼合與可部署",
                (
                    "FAISS(Facebook AI 向量索引庫)依語義檢索專案規則,足夠相關才注入,寧缺勿誤導",
                    "教師以少樣本 CoT 蒸餾出帶推理軌跡之資料,清洗後轉為指令跟隨格式微調學生",
                    "QLoRA:權重 4-bit 量化、僅更新低秩適配器,31B 級模型亦可於有限硬體訓練",
                ),
            ),
            (
                "GitHub 整合:PR 一開,審查自動走到合併閘門",
                (
                    "白話:開 PR 後全自動:enumerate → 逐檔 review → aggregate 三段式 GitHub Actions 管線",
                    "JudgeStep 把裁決映射為 APPROVE / REQUEST_CHANGES / COMMENT,以 check run(合併前檢查)作閘門",
                    "冪等(重跑不重複):同一提交只留一份總結留言,未變動檔以內容雜湊(blob-SHA)快取跳過推論",
                ),
            ),
            (
                "GitLab 整合(2026-07 新增):一鍵切換,MR 上產物對等",
                (
                    "白話:同一套審查核心換平台照用:GitHub / GitLab / Gitea 同走 PlatformAdapter 介面(五方法)",
                    "PRTHINKER_PLATFORM=gitlab 一鍵切換:總結於 MR(Merge Request,合併請求)note 更新,行內意見走 discussions API",
                    "裁決映射 approve / unapprove,閘門改用 commit status(GitLab 無 check run),失敗 pipeline log 擷取為審查訊號",
                ),
            ),
            (
                "多模型後端:九種即插即換,仲裁表決把關",
                (
                    "白話:審查核心不綁定單一模型供應商,create_backend 工廠(策略模式)即插即換",
                    "九種後端:本機 Hugging Face(LoRA+量化)/ 自架 / OpenAI-相容(vLLM、Ollama…)/ Anthropic 等四家雲端 / 二種 agent CLI",
                    "組合層:Router 失敗回退、Ensemble 多後端表決、仲裁(arbitration)覆核行內意見,fail-open 錯誤時放行",
                ),
            ),
            (
                "開發端整合與工程機制:已實作、已測試,效益評估留待未來",
                (
                    "MCP(Model Context Protocol,LLM 工具協定)server 三工具 + pre-commit hook,push 前即時觸發審查",
                    "無模型 triage(免推論分流):十二項確定性訊號(Trojan-Source 不可見字元、殘留衝突標記…),零推論成本",
                    "報告七格式(SARIF 靜態分析交換格式、HTML、CodeQuality…)+ Prometheus 監控,十七項研究級機制,1,506 個單元測試",
                ),
            ),
        ),
        # ===== §4.1 / §4.2 評估方法(2 節/頁 → 1 頁,與第一版相同)===========
        evaluation_sections=(
            (
                "雙軌評估:三維 + 自研五維",
                (
                    "CRSCORE++:先推導理想審查應涵蓋之議題集合,再評 完整性 / 簡潔性 / 相關性(0–1)",
                    "LLM-as-a-Judge-Our:可讀性 / 可維護性 / 正確性 / 跨評論覆蓋 / 簡潔性,1–100 分附理由",
                    "基準資料 44 筆:GPT-5 與 Copilot 生成、人工驗證,涵蓋語法 / 命名 / 設計模式 / 錯誤型態",
                ),
            ),
            (
                "公正性:評審獨立於受測模型",
                (
                    "評審由獨立於審查模型(gemma-4-31B-it)之外部 LLM(如 Claude)擔任,避免自評偏差",
                    "另輔以人工就相同維度評分,交叉驗證自動化評分之可靠度(→ RQ4)",
                ),
            ),
        ),
        # ===== §5 實驗結果 — 依 TCSE §5.1 之表-RQ 對應,三頁結果 =============
        # 表一 ↔ RQ1+RQ2、表二 ↔ RQ3(LLM 評分)、表三 ↔ RQ4(人工評分);
        # 五維全表逐格照搬 TCSE_v2.8(含其表二/表三第五維之 Conciseness 標籤,
        # 候選人指示照搬不改數據);消融 +34 / +2 取自 §5.2。
        rq_results=(
            RqResult(
                rq_id="RQ1 · RQ2",
                question=(
                    "RQ1:多階段提示詞+微調後,整體審查品質是否優於既有基準?"
                    "RQ2:相同參數規模、僅多階段提示詞是否已能提升?"
                ),
                table=(
                    ("維度", "Ours (gemma-4-31B-it)", "CRSCORE++", "Ours (Qwen3-Coder-30B-A3B)", "Ours (Qwen2.5 Coder-7B)"),
                    ("comprehensiveness 完整性", "1.00", "0.67", "1.00", "0.97"),
                    ("conciseness 簡潔性", "0.79", "0.57", "0.78", "0.69"),
                    ("relevance 相關性", "0.86", "0.63", "0.86", "0.79"),
                ),
                analysis=(
                    "RQ1:三維全勝基準,完整性增幅最大(1.00 對 0.67),更少漏看真正該提的問題",
                    "RQ2:未微調模型僅套多階段提示詞,三維仍優於基準,流程結構化本身即有實質效益",
                    "gemma-4-31B、Qwen3-30B、Qwen2.5-7B 三個基座皆優於基準,7B 亦達 0.97 / 0.69 / 0.79",
                ),
            ),
            RqResult(
                rq_id="RQ3",
                question="多階段提示詞與模型微調二者,何者為影響審查品質之主要因素?(LLM 評分,五維百分制)",
                table=(
                    ("維度", "微調模型+提示詞設計", "單提示詞微調後模型", "基礎模型+提示詞設計"),
                    ("Readability", "92", "88", "92"),
                    ("Maintainability", "95", "85", "95"),
                    ("Correctness", "98", "82", "98"),
                    ("Multi-Review Coverage", "96", "90", "94"),
                    ("Conciseness", "100", "78", "100"),
                ),
                analysis=(
                    "單一提示詞 → 多階段提示詞之貢獻達 +34 分(百分制),為框架內單項貢獻最大之一環",
                    "LoRA 微調邊際約 +2 分,但解決不同問題:有限資源下保留並穩定教師之審查能力",
                    "二者互補而非競爭:流程結構 vs 可部署,缺一則無法同時達成一致性與可維護性",
                ),
            ),
            RqResult(
                rq_id="RQ4",
                question="人工評分是否亦支持上述自動化評估之結論?(人工評分,同五維)",
                table=(
                    ("維度", "微調模型+提示詞設計", "單提示詞微調後模型", "基礎模型+提示詞設計"),
                    ("Readability", "83.50", "85.25", "84.63"),
                    ("Maintainability", "86.25", "79.88", "84.88"),
                    ("Correctness", "87.75", "80.75", "86.38"),
                    ("Multi-Review Coverage", "86.25", "74.13", "86.38"),
                    ("Conciseness", "84.25", "76.25", "84.75"),
                ),
                analysis=(
                    "人工與 LLM 評分趨勢一致:Maintainability / Correctness / Coverage / Conciseness 四維皆支持完整方法",
                    "僅 Readability 略低(83.50 對 85.25),其餘維度之高度一致驗證 LLM-as-a-Judge 之可信度",
                    "不論交給機器或交給人來評,結論都指向「整合」而非單一元件",
                ),
            ),
        ),
        # ===== §6.1 核心發現(callout;避開 §6.1 之過時數字,只留定性主軸)===
        core_observation=(
            "核心發現不在某一元件勝出,而在唯有三者整合:多階段 CoT 換取一致性、"
            "RAG 注入專案規範換取可解釋性、KD + QLoRA 換取可部署之可維護性,"
            "方能同時具備三性質、正面回應幻覺 / 輸出不穩定 / 缺乏領域規範三大問題。"
            "消融分解:多階段流程 +34 分、LoRA 微調 +2 分,互補而缺一不可。"
        ),
        # ===== §6.2 研究限制與未來工作(1 頁;未來工作更新為論文 §6.4)=======
        limitations=(
            "資料集:44 筆、以 Python 為主,規模相對有限",
            "模型:僅對單一學生模型微調",
            "多後端推論之品質 / 成本 / 延遲比較未於本文實測,反饋語料效益未量化",
            "隨附開源框架之工程整合與十七項機制:已實作 + 單元測試,端到端品質效益未於本文評估",
        ),
        future_work=(
            "跨後端品質 / 成本 / 延遲之偏序評估:同一基準與提示詞於各後端實測,建立選型對照表(論文 §6.4.1)",
            "作者反饋語料累積後,量化 dismissed / accepted 機制對精確率與採納率之效益(§6.4.2)",
            "平台再擴充:Bitbucket 尚未實作、僅列規劃,另擴展多語言真實專案資料集與多模型協作實證(§6.4.3)",
        ),
        model="hand-authored:thesis-deck-author",
    )


def _build_paper() -> Paper:
    return Paper(
        source="local",
        source_id="chen2026-tcse-features",
        title=CHINESE_TITLE,
        authors=("陳冠穎", "李文廷"),
        year=2026,
        venue="TCSE 台灣軟體工程研討會 · 國立高雄師範大學 軟體工程與管理學系",
        abstract="",
        url="",
        doi=None,  # 研討會投稿尚無出版 DOI → 觸發 own-thesis 路徑(不產生來源頁)
        summary=_build_summary(),
    )


def _bake_font_scale(text_frame, scale: float) -> None:
    """Persist an explicit ``fontScale`` on a shrink-to-fit text frame.

    The exporter sets ``auto_size = TEXT_TO_FIT_SHAPE``, which python-pptx
    writes as a bare ``<a:normAutofit/>`` with no ``fontScale``.  LibreOffice
    shrinks live, but PowerPoint renders such a box at FULL font size — so a
    long question / caption overruns its box.  Baking the scale (percent ×
    1000) makes every renderer draw the text already-shrunk.  Same fix as the
    defence deck (see regen_chen2026_codereview.py).
    """
    pct = max(1, min(100000, int(round(scale * 100000))))
    body_pr = text_frame._txBody.find(qn("a:bodyPr"))  # noqa: SLF001
    norm = body_pr.find(qn("a:normAutofit")) if body_pr is not None else None
    if norm is None:  # not a shrink-to-fit frame — nothing to bake
        return
    norm.set("fontScale", str(pct))


def _slide_title_text(slide) -> str:
    for shape in slide.shapes:
        if shape.has_text_frame and shape.name == "title":
            return shape.text_frame.text.strip()
    return ""


def _restyle_deck(out_path: str) -> None:
    """Post-export pass for this deck's ten-minute cut + candidate styling.

    1. Remove the tail「貢獻總結」slide — the exporter renders
       ``contributions_detailed`` twice (early「主要貢獻」+ tail summary); in a
       ten-minute slot the duplicate costs ~50 s for zero new information.
    2. Restamp page numbers after the removal so ``N / total`` stays true.
    3. Retitle the figure slide from the generic「圖」label to an assertion
       (slide-deck-rules §9: title = the claim, not a topic label).
    4. Surface the English paper title on the cover's reserved subtitle slot.
    5. Trim the per-slide running subtitle to the paper title alone (the
       exporter packs ``title · venue`` into a 0.28" line, which wraps).
    6. Override typography to 標楷體 (CJK) + Times New Roman (Latin) — the
       candidate's standing request, same as the defence deck.
    7. Bake ``fontScale`` into any shrink-to-fit box that still overruns at
       full size, so PowerPoint draws it pre-shrunk.

    Why a post-pass, not exporter changes: every item is this deck's alone.
    Re-running this script reproduces the deck exactly.
    """
    prs = Presentation(out_path)

    # (1) Drop the duplicate「貢獻總結」slide.
    sld_id_lst = prs.slides._sldIdLst  # noqa: SLF001
    for sld_id, slide in zip(list(sld_id_lst), list(prs.slides), strict=True):
        if _slide_title_text(slide) == "貢獻總結":
            sld_id_lst.remove(sld_id)
            break

    # (2) Restamp page numbers (exporter format: "N  /  total-1", no cover #).
    total = len(prs.slides)
    for index, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            if shape.has_text_frame and shape.name == "page_number":
                for paragraph in shape.text_frame.paragraphs:
                    for i, run in enumerate(paragraph.runs):
                        run.text = f"{index}  /  {total - 1}" if i == 0 else ""

    # (3) Assertion title on the figure slide (was the generic「圖」).
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame and shape.name == "title" and \
                    shape.text_frame.text.strip() == "圖":
                runs = [r for p in shape.text_frame.paragraphs for r in p.runs]
                if runs:
                    runs[0].text = "系統架構:六層職責分離、可替換邊界"
                    for extra in runs[1:]:
                        extra.text = ""

    # (4) English paper title beneath the Chinese cover headline.
    cover = prs.slides[0]
    _add_textbox(
        cover, name="subtitle", text=ENGLISH_TITLE,
        left=_MARGIN_X, top=Inches(3.3),
        width=_BODY_WIDTH, height=Inches(1.0),
        font_pt=18, colour=_DARK_BODY_TEXT,
        align=PP_ALIGN.CENTER, shrink_to_fit=True,
    )

    # (5) Running subtitle → title only (cover already carries venue/authors).
    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame or shape.name != "paper_subtitle":
                continue
            tf = shape.text_frame
            runs = [r for p in tf.paragraphs for r in p.runs]
            size = runs[0].font.size if runs else Pt(14)
            tf.text = CHINESE_TITLE
            run = tf.paragraphs[0].runs[0]
            run.font.size = size or Pt(14)
            run.font.color.rgb = _BRAND_GREY

    # (6) Typography override on every run.
    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.font.name = _LATIN_FONT
                    _set_east_asian_typeface(run, _CJK_FONT)

    # (7) Bake fontScale where a shrink-to-fit box still overruns at full size.
    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            tf = shape.text_frame
            if tf.auto_size != MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE:
                continue
            box_h = (shape.height or 0) / _EMU_PER_INCH
            est = _overflow._text_height_in(tf, shape.width or 0)  # noqa: SLF001
            if box_h > 0 and est > box_h * 0.97:
                _bake_font_scale(tf, max(0.55, (box_h * 0.95) / est))

    prs.save(out_path)


def main() -> None:
    collection = PaperCollection(
        query=Query(
            keywords="LLM CoT code review framework engineering TCSE",
            sources=("local",),
        ),
        papers=(_build_paper(),),
    )
    options = ExportOptions(
        formats=("pptx",),
        out_dir=OUT_DIR,
        filename_stem=FILENAME_STEM,
        language=LANGUAGE,
        # 研討會白色 + 藍學術風(白底、深藍標題 / 內文、藍色強調)。
        dark_mode=False,
        # 十分鐘報告:先完整渲染,再由 _restyle_deck 刪重複頁至 ~14 張。
        max_slides_per_paper=25,
    )
    out_path = PptxExporter().export(collection, options)
    _restyle_deck(out_path)
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()
