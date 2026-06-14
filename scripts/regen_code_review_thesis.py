"""Degree-thesis ORAL-DEFENCE deck for 陳冠穎's master's thesis, authored via the
`thesis-deck-author` Mode A flow (candidate's own thesis file).

Source: D:/Codes/Code-Review-Framework-.../paper/論文_v1.9.docx
All content (metrics, RQs, tables, limitations) is drawn from that thesis — no
number is invented. Cross-reference markers (§5.2, 表 2, [7]) and draft version
tags are intentionally NOT carried onto slides (post-author-audit Audit 3/4).

Seven-section coverage (paper_rule → PaperSummary field):
  Abstract ............... core_observation + headline_metrics
  1. Introduction ........ pain_points (1.2) + research_question (1.3) +
                           contributions_detailed (1.5, cap 4)
  2. Literature Review ... literature_table (2.3) + technique_table
  3. Methodology ......... system_flow (3.1 系統架構) + method_sections
                           (3.2 訓練流程 起,其餘往後移) + evaluation_sections (3.5/4)
  4. Experiment .......... research_questions + rq_results (5.1-5.3)
  5. Conclusion .......... core_observation (5.1) + limitations (6.3) + future_work (6.4)

Output: the paper's own folder (white + blue academic default, dark_mode=False).
Run:  .venv/Scripts/python.exe scripts/regen_code_review_thesis.py
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

OUT_DIR = (
    r"D:\Codes\Code-Review-Framework-Combining-Large-Language-Models-"
    r"and-Chain-of-Thought-Reasoning\paper"
)
FILENAME_STEM = "code-review-thesis-defense-zh-tw"
LANGUAGE = "zh-tw"


def _build_summary() -> PaperSummary:
    return PaperSummary(
        language=LANGUAGE,
        # ---- 1.2 研究動機 / 痛點(四宮格)------------------------------------
        pain_points=(
            (
                "人工程式碼審查已成開發瓶頸",
                (
                    "程式碼審查可在整合前發現 50–70% 缺陷,卻耗費可觀人力與時間",
                    "處理審查意見的時間幾乎隨評論數線性增加",
                    "大型專案中審查標準不一、審查者主觀性偏高",
                ),
            ),
            (
                "LLM 直接審查仍有風險",
                (
                    "易產生幻覺(編造看似合理卻不正確的內容)",
                    "輸出不穩定、缺乏領域規範約束",
                    "單一提示詞同時做摘要/審查/風格/異味,造成 context 過載",
                ),
            ),
            (
                "傳統靜態分析工具不足",
                (
                    "規則僵化,多僅能偵測語法錯誤或已知模式",
                    "缺乏語義層理解與設計合理性判斷",
                    "約 2/3 的 LLM 檢測結果超出傳統工具能力範圍",
                ),
            ),
            (
                "既有 LLM 審查研究的缺口",
                (
                    "多採單一提示詞或單一技術面向改良",
                    "鮮少同時整合多階段 CoT、知識蒸餾、RAG 與細粒度評估",
                    "評估多沿用字串重疊或粗粒度 1–5 分,解析度不足",
                ),
            ),
        ),
        research_question=(
            "在資源受限的前提下,能否以「多階段思維鏈提示詞 + 知識蒸餾微調 + "
            "RAG 規則注入」建立一套兼具效率與一致性,且品質可量化交叉驗證的"
            "自動化程式碼審查框架?"
        ),
        # ---- 1.5 研究貢獻(cap 4)------------------------------------------
        contributions_detailed=(
            (
                "1. 多階段思維鏈審查流程",
                "將審查拆解為摘要、初步審查、靜態分析(linter)、程式碼異味偵測與"
                "總彙整五個循序步驟,以 build_global_rule_template 統一注入全域規則,"
                "降低單一提示詞的 context 負載並形成可追蹤的審查鏈。",
            ),
            (
                "2. 知識蒸餾 + QLoRA 輕量化",
                "以教師模型生成帶 Chain-of-Thought 推理軌跡的審查資料,蒸餾至學生模型 "
                "Qwen3-Coder-30B-A3B-Instruct,並以 QLoRA(NF4 4-bit + LoRA rank "
                "$r$=64)在兩張 L40S 上完成微調,以可拆卸的 LoRA 適配器保留彈性。",
            ),
            (
                "3. FAISS RAG 規則檢索層",
                "以 Qwen3-Embedding-4B 將領域規則向量化寫入 FAISS,推論時以餘弦相似度 "
                "≥ 0.7 動態注入相關規則,抑制幻覺,並避免規則總量隨 context window 擴張"
                "而線性增加。",
            ),
            (
                "4. LLM-as-a-Judge-Our 五維百分制評估",
                "設計可讀性、建設性、正確性、多評論覆蓋與完整性五維百分制評分,並以 "
                "GPT-5 / Gemini-3 雙裁判加人工評分三方交叉驗證,提升評估解析度與可信度。",
            ),
        ),
        # ---- 摘要 / §5 主要量化成果(KPI)----------------------------------
        headline_metrics=(
            ("完整性 (CRSCORE++)", "0.86", "基準 0.67"),
            ("相關性 (CRSCORE++)", "0.83", "基準 0.63"),
            ("簡潔性 (CRSCORE++)", "0.64", "基準 0.57"),
            ("多階段提示詞邊際貢獻", "+34 分", "品質提升的主導因素"),
            ("模型微調邊際貢獻", "+2 分", "與流程設計相差逾一個數量級"),
            ("測試資料", "44 筆", "GPT-5 + Copilot 生成、人工驗證"),
        ),
        # ---- 2.10 文獻比較與研究缺口 ---------------------------------------
        literature_table=(
            ("方法", "多階段提示詞", "模型微調", "RAG", "評估方式"),
            ("CRScore (Naik 2024)", "✗", "✗", "✗", "3 維 1–5 分"),
            ("CRScore++ (Kapadnis 2025)", "✗", "✗", "✗", "3 維 1–5 分 + RL"),
            ("LLaMA-Reviewer (Lu 2023)", "✗", "✓ LoRA", "✗", "BLEU / ROUGE"),
            ("AutoReview (Chen 2025)", "✓ 多代理", "✗", "✗", "質性分析"),
            ("本研究 Ours", "✓ 5 階段", "✓ QLoRA", "✓ 規則注入", "5 維百分制 + 人工"),
        ),
        # ---- 關鍵技術 → 角色 ----------------------------------------------
        technique_table=(
            ("多階段 CoT 提示詞", "降 context 負載,形成可追蹤、可介入的審查鏈"),
            ("知識蒸餾 + QLoRA", "把 30B 教師能力移轉到可在有限資源部署的學生模型"),
            ("RAG(FAISS)", "以相似度檢索注入專案規範,抑制幻覺"),
            ("LLM-as-a-Judge", "GPT-5 / Gemini-3 雙裁判自動量化評分"),
            ("人工評分", "交叉驗證自動評分的可信度"),
        ),
        # ---- 3.1 系統架構(整體五大組件,對應論文圖二)--------------------
        system_flow=(
            "測試資料:ChatGPT 與 Copilot 生成的 Source Code,依 bad_data / code_diff / only_code 三類組織",
            "RAG 規則檢索:規則文件經 Qwen3-Embedding-4B 向量化寫入 FAISS,取回相似度 ≥ 0.7 的規則注入提示詞",
            "核心模型:Qwen3-Coder-30B-A3B + 4-bit 量化 + 微調 LoRA Adapter,三條 Pipeline 共用",
            "審查策略:CoT(五階段)、Single Prompt 基準、Skills(Explainer + Review 雙角色)三者對照",
            "評估方法:LLM-as-a-Judge(五維百分制)、CRScore、人工評估三方交叉驗證",
        ),
        # ---- 3.2 起 方法細節(訓練流程提到最前,其餘依序往後移)----------
        method_sections=(
            (
                "訓練流程:知識蒸餾 + QLoRA 微調",
                (
                    "教師模型以 CoT 提示生成帶推理軌跡的審查樣本(instruction / question / think / answer)作為監督訊號",
                    "資料 tokenize 後做 label masking,只對 answer 計算 loss",
                    "學生 Qwen3-Coder-30B-A3B-Instruct 以 NF4 4-bit 量化載入,LoRA rank $r$=64、$α$=64,注入 q/k/v/o 與 gate/up/down_proj",
                ),
            ),
            (
                "多階段思維鏈審查",
                (
                    "五階段串接:摘要 → 初步審查 → Linter → Code Smell → 總彙整",
                    "每階段專注單一明確任務,降低模型認知負擔",
                    "中間文件形成可追蹤、可人工介入的審查鏈",
                ),
            ),
            (
                "RAG 規則注入",
                (
                    "Qwen3-Embedding-4B 將規則向量化後寫入 FAISS 索引",
                    "推論時取回餘弦相似度 ≥ 0.7 的規則",
                    "與七大審查標準一併注入全域提示詞",
                ),
            ),
            # —— 以下為隨附開源框架 prthinker 之設計貢獻,端到端量化效益列為未來工作 ——
            (
                "prthinker:把審查接上 GitHub PR 與 IDE",
                (
                    "以下皆為開源框架 prthinker 的設計貢獻,量化效益列為未來工作",
                    "JudgeStep 輸出 {verdict, score, reasons} 裁決,保守聚合後映射為 PR 的 APPROVE / REQUEST_CHANGES / COMMENT 事件",
                    "可替換推論後端(本機 HF / FastAPI / OpenAI / Anthropic),並以 MCP 將審查管線暴露為 IDE 可直接調用的工具",
                ),
            ),
            (
                "prthinker:從作者反饋持續學習",
                (
                    "Dismissed 語料:對被作者拒絕的留言以相似度過濾抑制重複噪音(作用於輸出端)",
                    "Accepted 語料:以被採納的建議作 in-context 範例提升採納率(作用於輸入端)",
                    "再衍生可重用規則、跨 PR finding 聚類,並以 repo 知識圖譜接地符號以抑制虛構",
                ),
            ),
            (
                "prthinker:強化審查品質的研究級機制",
                (
                    "prompt-injection 強健性、counterfactual 替代方案、provenance 引用鏈",
                    "reviewer personas 多視角 + 衝突顯化、reproducibility 一致性訊號",
                    "PR 類型自適應審查深度、risk-weighted attention 分配 findings 預算",
                ),
            ),
            (
                "prthinker:CI/CD 部署與工程化",
                (
                    "CI matrix 分片 + 非同步 job endpoint,化解 30B 推論的逾時與 GPU OOM",
                    "force-push 差分 cache、崩潰安全部分結果、PR 留言冪等性",
                    "secret 預過濾、SARIF / HTML 報告匯出、diff bomb 偵測",
                ),
            ),
            (
                "prthinker:零推論的無模型定向信號",
                (
                    "12 項確定性啟發式,無需 GPU 或 API 即可作前置分流",
                    "遺留衝突標記、Trojan-Source 隱形字元、遺留除錯敘述、吞噬例外",
                    "大塊新增、新增 TODO / FIXME、純格式變更、檔案模式變更等",
                ),
            ),
        ),
        # ---- 4 評估指標與實驗設計 -----------------------------------------
        evaluation_sections=(
            (
                "評估指標",
                (
                    "CRSCORE++:完整性 / 簡潔性 / 相關性 三維 1–5 分",
                    "LLM-as-a-Judge-Our:五維百分制(可讀性 / 建設性 / 正確性 / 多評論覆蓋 / 完整性)",
                    "百分制較 1–5 分更能反映細微差異",
                ),
            ),
            (
                "實驗設計與環境",
                (
                    "44 筆測試資料,由 GPT-5 + Copilot 生成並經人工驗證",
                    "GPT-5 與 Gemini-3 雙裁判,降低單一裁判偏差",
                    "硬體:2× Intel Xeon Gold 6526Y、512 GB RAM、2× NVIDIA L40S(96 GB)",
                ),
            ),
        ),
        # ---- 研究問題 -----------------------------------------------------
        research_questions=(
            ("RQ1", "多階段 CoT 提示詞 + LoRA 微調,相較傳統單一提示詞,能否在完整性 / 簡潔性 / 相關性顯著提升審查品質?"),
            ("RQ2", "固定參數規模下,僅引入多階段提示詞而不微調,是否即可帶來品質提升?"),
            ("RQ3", "多階段提示詞與模型微調各自的邊際貢獻為何?何者主導品質改善?"),
            ("RQ4", "自動 LLM-as-a-Judge 評分,能否由獨立人工評分交叉驗證並保持一致?"),
        ),
        # ---- 5.1-5.3 各 RQ 結果(真實表格)-------------------------------
        rq_results=(
            RqResult(
                rq_id="RQ1",
                question="多階段 CoT + 微調相較單一提示詞,能否顯著提升審查品質?",
                table=(
                    ("CRSCORE++ 維度", "本研究 Ours", "基準"),
                    ("完整性 comprehensiveness", "0.86", "0.67"),
                    ("相關性 relevance", "0.83", "0.63"),
                    ("簡潔性 conciseness", "0.64", "0.57"),
                ),
                analysis=(
                    "本研究在 CRSCORE++ 三維度全面優於基準",
                    "GPT-5 裁判下,多階段較單一提示詞於正確性 90 vs 82、簡潔性 96 vs 78 明顯領先",
                    "7B 學生模型仍可達完整性 0.79–0.80,顯示框架在不同模型尺寸的可行性",
                ),
            ),
            RqResult(
                rq_id="RQ2",
                question="不微調、僅加多階段提示詞,是否即可提升品質?",
                table=(
                    ("Gemini-3 裁判", "多階段 Ours", "單一提示詞"),
                    ("正確性 Correctness", "98", "95"),
                    ("可維護性 Maintainability", "95", "88"),
                    ("簡潔性 conciseness", "100", "85"),
                ),
                analysis=(
                    "即使不微調,僅靠多階段提示詞即帶來顯著提升",
                    "顯示主要瓶頸是單一提示詞的 context 過載,而非模型能力不足",
                    "Qwen3-Coder-30B 本身已具備充分的程式碼語義理解能力",
                ),
            ),
            RqResult(
                rq_id="RQ3",
                question="多階段提示詞 vs 模型微調,何者主導品質改善?",
                table=(
                    ("消融變化(自動評分)", "可維護性", "正確性"),
                    ("基礎 → 微調 + 多階段", "85 → 95", "82 → 98"),
                    ("僅多階段(未微調) → 微調 + 多階段", "95 → 95", "98 → 98"),
                ),
                analysis=(
                    "多階段提示詞邊際貢獻 +34 分,為品質提升的主導因素",
                    "模型微調邊際貢獻僅 +2 分,兩者相差逾一個數量級",
                    "資源受限下,流程結構化設計較參數微調更具決定性",
                ),
            ),
            RqResult(
                rq_id="RQ4",
                question="自動評分能否由人工評分交叉驗證並保持一致?",
                table=(
                    ("人工評分", "本研究 Ours", "基礎模型"),
                    ("正確性 Correctness", "87.75", "80.75"),
                    ("可維護性 Maintainability", "86.25", "79.88"),
                    ("多評論覆蓋 Multi-Review Coverage", "86.25", "74.13"),
                ),
                analysis=(
                    "人工評分與自動評分方向一致,完整方法於三維度同時領先",
                    "惟可讀性出現 LLM 評分(92)高於人工(83.50)的系統性偏差",
                    "此偏差與文獻所述 LLM 對語感類指標較人類寬鬆一致,可作為後續校正依據",
                ),
            ),
        ),
        # ---- 5.1 / 6.1 核心觀察(callout)--------------------------------
        core_observation=(
            "在資源受限的程式碼審查情境下,把單一提示詞拆解為多階段思維鏈流程帶來的"
            "品質提升(+34 分),遠大於對模型做 LoRA 微調(+2 分),相差逾一個數量級 —— "
            "流程的結構化設計,比模型參數微調更具決定性。"
        ),
        # ---- 6.3 研究限制 -------------------------------------------------
        limitations=(
            "資料規模:僅 44 筆 Python 測試資料,未驗證 C++ / Java / Go 等語言與其他專案類型的泛化",
            "評審偏差:GPT-5 / Gemini-3 同屬商用 LLM,可能共享預訓練分布傾向",
            "微調範圍:僅微調 Qwen3-Coder-30B,未比較其他基座模型與 LoRA rank / 量化精度",
            "部署實證:已整合 CI/CD,但未於真實團隊長期試行,缺採用率 / 省時 / 誤報等實務指標",
        ),
        # ---- 6.4 未來工作 -------------------------------------------------
        future_work=(
            "跨後端(本機 / FastAPI / OpenAI / Anthropic)的品質、成本與延遲偏序評估",
            "作者反饋語料(dismissed / accepted)累積後的採納率與精確率量化驗證",
            "跨平台(GitLab / Bitbucket / Gitea)支援與多模型仲裁擴展",
            "IDE 觸發 vs CI 觸發的開發者接受率比較,並補強生產級維運",
        ),
        model="hand-authored:regen_code_review_thesis",
    )


def _build_paper() -> Paper:
    return Paper(
        source="local",
        source_id="code-review-thesis-2026",
        title="基於大語言模型和思維鏈推理的程式碼審查框架",
        authors=("陳冠穎",),
        year=2026,
        venue="國立高雄師範大學 · 軟體工程與管理學系 · 碩士學位論文 · 指導教授:李文廷 博士",
        abstract="",
        url="",
        summary=_build_summary(),
    )


def main() -> None:
    collection = PaperCollection(
        query=Query(keywords="code review llm chain-of-thought", sources=("local",)),
        papers=(_build_paper(),),
    )
    options = ExportOptions(
        formats=("pptx",),
        out_dir=OUT_DIR,
        filename_stem=FILENAME_STEM,
        language=LANGUAGE,
        dark_mode=False,  # white + blue academic default
        max_slides_per_paper=30,  # framework feature coverage fits in a 30-slide budget
    )
    out_path = PptxExporter().export(collection, options)
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()
