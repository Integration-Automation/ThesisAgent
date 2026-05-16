"""LLM 與程式碼審查相關論文的繁中富版 PPT 生成腳本。

按 LLM-as-agent 流程,從 4 篇直接相關論文的 PDF 讀完之後手寫的 PaperSummary。
URL / DOI 已對照搜尋產生的 xlsx 逐字驗證。

Usage:
    py scripts/regen_llm_code_review_zh_tw.py llm-code-review

Papers:
    1. Charoenwet et al. 2026 — AgenticSCR (FSE 2026)
    2. Vulićević 2026 — Locally Deployed LLMs for Bug Detection
    3. Janzen et al. 2026 — Gendered Prompting and LLM Code Review
    4. Khan et al. 2026 — Survey of Code Review Benchmarks (Pre-LLM vs LLM)
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sources"))

from autopapertoppt.core.models import (  # noqa: E402
    ExportOptions,
    Paper,
    PaperCollection,
    PaperSummary,
    Query,
    RqResult,
)
from autopapertoppt.exporters import export_collection  # noqa: E402

MODEL_TAG = "claude-opus-4-7 (LLM-as-agent, read full PDF)"

_RUN_DIR_NAME = sys.argv[1] if len(sys.argv) > 1 else "llm-code-review"

# ---------------------------------------------------------------------------
# 1. Charoenwet et al. 2026 — AgenticSCR (FSE 2026)
# ---------------------------------------------------------------------------
CHAROENWET = Paper(
    source="local", source_id="charoenwet2026agenticscr",
    title="AgenticSCR: An Autonomous Agentic Secure Code Review for Immature Vulnerabilities Detection",
    authors=("Wachiraphan Charoenwet", "Kla Tantithamthavorn", "Patanamon Thongtanunam",
             "Hong Yi Lin", "Minwoo Jeong", "Ming Wu"),
    year=2026, venue="FSE 2026",
    abstract=(
        "AgenticSCR 是一個面向 pre-commit 階段的自主 agentic 安全程式碼審查框架,"
        "由偵測器(detector)與驗證器(validator)子代理串接組成,可自主存取倉庫"
        "層級上下文與 SAST 規則記憶體、CWE 樹語意記憶體。在自建的 SCRBench 資料集上,"
        "AgenticSCR 產生的 17.8% 評論正確定位、相關且能解釋未成形漏洞 —— 比 static LLM 高 "
        "10.6 個百分點,比三套 SAST 工具高 13.8 個百分點;在五大漏洞類別中於四類超越所有基線。"
    ),
    url="https://arxiv.org/abs/2601.19138",
    arxiv_id="2601.19138", pdf_url=None,
    summary=PaperSummary(
        language="zh-tw", model=MODEL_TAG, raw_text_chars=76_179,
        pain_points=(
            ("Pre-commit 安全程式碼審查時間窗極短", (
                "開發者在 commit 前必須以低延遲完成審查",
                "上下文只有正在改動的 diff,缺少倉庫全貌",
                "未成形(immature)漏洞依賴跨檔案上下文才看得出來",
            )),
            ("既有 SAST 工具雜訊太多", (
                "靜態規則產生大量誤報與低嚴重性警告",
                "開發者習慣性忽略或停用 SAST 檢查",
                "預防價值因此大打折扣",
            )),
            ("Static LLM prompt 拿不到必要的上下文", (
                "Liu / Cihan / Haider 等既有工作只給 diff 或 CWE 文字描述",
                "缺乏倉庫導覽、SAST 規則整合與 CWE 分類整合",
                "無法判斷 context-dependent 的未成形漏洞",
            )),
            ("缺乏 line-level、repo-aware 的安全審查基準", (
                "現有 benchmark 多為 PR 級或 chunk 級",
                "驗證資料缺少人類審查標註",
                "難以衡量真實 pre-commit 場景的審查品質",
            )),
        ),
        research_question=(
            "在 pre-commit 階段,如何用 agentic LLM 框架整合 SAST 規則與 CWE 知識,"
            "對倉庫層級上下文做自主推理,以更精準偵測未成形漏洞、產生可解釋的審查評論,"
            "且雜訊比既有 SAST 與 static LLM 更低?"
        ),
        contributions_detailed=(
            ("1. AgenticSCR 框架",
             "首個面向 pre-commit 階段、針對未成形漏洞的 agentic AI 安全程式碼審查方法,"
             "整合 SAST 規則與 CWE 樹語意記憶體,以偵測器 / 驗證器子代理組合提升精度。"),
            ("2. 三項安全審查任務評估",
             "在 line-level localization、安全審查評論生成、漏洞類型解釋三個任務上"
             "全面評估,顯示三項皆能勝過 static LLM 與 SAST 基線。"),
            ("3. SCRBench 資料集",
             "建構 repo-aware、人工驗證的 line-level 漏洞基準資料集,聚焦 pre-commit 階段;"
             "論文錄取後公開釋出。"),
            ("4. 跨漏洞類別評估",
             "在 CWE-1000 五大高階類別(Injection、Authorization、Resource Mgmt、Behavior、Other)"
             "下,於四類中皆顯著超越所有基線。"),
        ),
        headline_metrics=(
            ("Localized + Relevant + Type 正確率", "17.8%", "static LLM 7.2%、SAST 4.0%"),
            ("相對 static LLM 提升", "+153%", "在 L&R&T 綜合正確率上"),
            ("輸出評論數比基線少", "2–5x", "static LLM / SAST 雜訊更高"),
            ("與 static LLM 的絕對提升", "+10.6 pp", "於同一任務"),
            ("與 SAST 工具的絕對提升", "+13.8 pp", "於同一任務"),
            ("勝過所有基線的漏洞類別", "4 / 5", "CWE-1000 高階分類"),
        ),
        technique_table=(
            ("Liu et al. (LLM)", "PR diff 級,有安全聚焦,但無倉庫上下文"),
            ("Cihan et al. (LLM)", "HumanEval block 級,無安全聚焦"),
            ("Haider et al. (LLM)", "CodeReviewer diff 級,無安全聚焦"),
            ("Peng et al. (LLM)", "PrivateLine + CWE,有安全聚焦"),
            ("Tang et al. (MultiAgents)", "TransReview / AutoTransform / T5,無安全聚焦"),
            ("AgenticSCR(本論文)", "Agentic AI + 倉庫導覽 + SAST 規則 + CWE 樹,line 級"),
        ),
        method_sections=(
            ("Detector 子代理", (
                "輸入:diff + 倉庫上下文 + SAST 規則記憶體",
                "輸出:line-level 定位 + 評論草稿 + CWE 類型",
                "工具呼叫:repository navigation、SAST 規則檢索",
            )),
            ("Validator 子代理", (
                "驗證 Detector 評論的正確性以降低雜訊",
                "查 CWE 樹語意記憶體確認漏洞分類合理",
                "丟掉誤報或低品質的評論",
            )),
            ("語意記憶體", (
                "SAST 規則記憶體:整合既有 static 分析規則",
                "CWE 樹記憶體:CWE-1000 的階層式分類",
                "提供 detector / validator 雙方的決策依據",
            )),
        ),
        evaluation_sections=(
            ("L&R&T 綜合正確率(RQ1)", (
                "AgenticSCR:17.8%(line-level 對 + 相關 + CWE 類型正確)",
                "Static LLM:7.2%",
                "SAST 工具:4.0%",
            )),
            ("各漏洞類別表現(RQ2)", (
                "Injection、Authorization、Resource Mgmt、Behavior:全勝",
                "唯一未領先類別:Other(雜項)",
                "CWE-1000 五大高階分類為標準",
            )),
            ("評論數量(雜訊指標)", (
                "AgenticSCR 比 static LLM 少 2–5 倍評論",
                "意味更高的 precision、更低的開發者干擾",
                "符合 pre-commit 低延遲限制",
            )),
        ),
        system_flow=(
            ("Pre-commit diff 進入", "開發者送出 commit 前觸發"),
            ("Detector 子代理", "存取倉庫上下文 + SAST 規則"),
            ("Detector 產出評論草稿", "line 定位 + 描述 + CWE 類型"),
            ("Validator 子代理", "查 CWE 樹驗證評論合理性"),
            ("過濾雜訊 / 誤報", "丟棄不合理草稿"),
            ("最終評論輸出", "高 precision、可解釋的安全評論"),
        ),
        research_questions=(
            ("RQ1", "AgenticSCR 在安全程式碼審查任務上的整體表現如何?"),
            ("RQ2", "AgenticSCR 在哪些漏洞類別表現最好?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="AgenticSCR 在安全程式碼審查任務上的整體表現?",
                table=(
                    ("方法", "L&R&T 正確率(%)"),
                    ("AgenticSCR(本論文)", "17.8"),
                    ("Static LLM", "7.2"),
                    ("SAST(三套)", "4.0"),
                ),
                analysis=(
                    "AgenticSCR 比 static LLM 高 10.6 個百分點(相對提升 153%)",
                    "比 SAST 工具高 13.8 個百分點",
                    "且評論總數比基線少 2–5 倍,代表雜訊更低",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="AgenticSCR 在哪些漏洞類別表現最好?",
                table=(
                    ("CWE 高階類別", "AgenticSCR 是否勝過所有基線"),
                    ("Injection (CWE-707)", "是"),
                    ("Authorization (CWE-287)", "是"),
                    ("Resource Management", "是"),
                    ("Behavior", "是"),
                    ("Other", "否"),
                ),
                analysis=(
                    "五大類別中於四類勝出",
                    "Injection 類受益最多 —— 倉庫上下文能找到 sanitization 缺失",
                    "Other 類因類型多樣,agentic 的優勢不明顯",
                ),
            ),
        ),
        core_observation=(
            "Pre-commit 安全程式碼審查的精度瓶頸不在 LLM 模型本身,而在「上下文」與「雜訊」:"
            "用 agentic 子代理整合 SAST 規則 + CWE 樹 + 倉庫導覽,可同時提升正確定位率"
            "(+10.6 pp)並降低評論雜訊(2–5 倍少)。"
        ),
        limitations=(
            "SCRBench 仍只涵蓋 pre-commit 場景,未跨足完整 PR-level review",
            "agentic 框架的 LLM 呼叫成本與延遲未仔細量化",
            "資料集規模未在論文中報告;泛化到企業內部倉庫的有效性未證實",
            "依賴 SAST 規則與 CWE 樹的更新,知識落差會影響精度",
        ),
        future_work=(
            "把 agentic 架構延伸到 PR-level 與 cross-PR 推理",
            "整合 dynamic analysis(test runner / fuzzer)強化驗證",
            "以多模型 ensemble 進一步降低 false positive",
        ),
    ),
)


# ---------------------------------------------------------------------------
# 2. Vulićević 2026 — Locally Deployed LLMs for Bug Detection
# ---------------------------------------------------------------------------
VULICEVIC = Paper(
    source="local", source_id="vulićević2026empirical",
    title="An Empirical Evaluation of Locally Deployed LLMs for Bug Detection in Python Code",
    authors=("Jelena Ilić Vulićević",),
    year=2026, venue="arXiv 2026",
    abstract=(
        "本文以 BugsInPy 真實 Python 漏洞資料集(17 個專案、349 個有效 bug)系統評估"
        "本機部署的兩個開放權重 LLM —— LLaMA 3.2 與 Mistral,在 zero-shot prompt 與"
        "function-level 設定下的偵測能力。兩模型整體準確率在 43–45% 之間,於 PySnooper"
        "達 100%,但對 type conversion bug 兩者皆 0%;McNemar 檢定顯示兩模型差異不顯著"
        "(p = 0.68)。研究指出本機部署在隱私敏感、資源受限場景具實務價值。"
    ),
    url="https://arxiv.org/abs/2604.23361",
    arxiv_id="2604.23361", pdf_url=None,
    summary=PaperSummary(
        language="zh-tw", model=MODEL_TAG, raw_text_chars=33_922,
        pain_points=(
            ("既有 LLM bug 偵測研究多依賴雲端模型", (
                "Codex / CodeBERT / GPT 系列皆需要 API 與付費",
                "私有程式碼上傳到雲端有合規與隱私疑慮",
                "資源受限團隊難以負擔長期使用成本",
            )),
            ("Open-weight 模型在本機的真實表現未獲驗證", (
                "LLaMA / Mistral 在消費級硬體無 GPU 加速也能跑",
                "但對真實 production bug 的偵測力幾無系統評估",
                "難以據此判斷是否值得導入",
            )),
            ("既有基準多為合成範例", (
                "HumanEval 等強調生成,而非偵測",
                "缺乏跨多專案、多 bug 類型的真實資料",
                "BugsInPy 提供真實 production bug,但模型評估仍稀少",
            )),
            ("Function-level 偵測缺乏跨函式上下文", (
                "single-function prompt 無法處理跨函式 bug",
                "型別轉換、複雜共享狀態尤其困難",
                "現有評估方法多忽略此限制",
            )),
        ),
        research_question=(
            "在消費級硬體 + 無 GPU 加速 + 無雲端依賴的本機部署設定下,"
            "open-weight LLM(LLaMA 3.2 與 Mistral)能否在真實 Python production bug "
            "上達到可用於實務的偵測準確率?跨專案與 bug 類型的表現變異有多大?"
        ),
        contributions_detailed=(
            ("1. 真實 bug 的系統實證評估",
             "在 BugsInPy 的 17 個 Python 專案、349 個有效 bug 上對兩個本機部署 LLM"
             "進行 zero-shot 評估,首次系統量化 open-weight 模型在 production bug 的表現。"),
            ("2. 自動化關鍵字評估方法",
             "對 LLM 自由文字回應設計關鍵字基準評估器,把 free-form 輸出對應到"
             "「正確 / 部分 / 錯誤」三類,可重現且不需人工標註。"),
            ("3. 跨專案與跨 bug 類別分析",
             "識別出影響偵測準確率的關鍵因素 —— 專案規模、bug 類型(Null check / Return value /"
             "Indexing / Type conversion 等),並做統計顯著性檢定(McNemar)。"),
            ("4. 完整可重現的程式碼與資料",
             "釋出全部程式碼、prompt、評估腳本,讓社群可在自家硬體重現結果。"),
        ),
        headline_metrics=(
            ("LLaMA 3.2 整體準確率", "~45%", "349 個 BugsInPy 真實 bug"),
            ("Mistral 整體準確率", "~43%", "同上"),
            ("PySnooper 最佳專案", "100%", "兩模型皆完美"),
            ("Type Conversion bug 兩模型", "0%", "需要 runtime 資訊"),
            ("McNemar p-value", "0.68", "兩模型差異不顯著"),
            ("Null/None Check bug", "~60%", "兩模型表現最佳的類別"),
        ),
        technique_table=(
            ("Codex (Chen et al.)", "GPT-based,HumanEval 生成評估"),
            ("CodeBERT (Feng et al.)", "雙語預訓練,程式碼搜尋 / 文件"),
            ("AutoFL (Kang et al.)", "LLM 故障定位 + 自然語言解釋"),
            ("Mhatre et al.", "雲端模型 + Python/C++ 基準"),
            ("Lee et al.", "長 context 退化研究"),
            ("本論文", "LLaMA 3.2 + Mistral,本機 zero-shot,17 個專案"),
        ),
        method_sections=(
            ("資料集與篩選", (
                "BugsInPy 501 個 bug,經處理後保留 349 個 function-level 可評估樣本",
                "涵蓋 17 個專案:pandas、scrapy、keras、matplotlib 等",
                "每個 bug 含 diff、buggy/fixed commit、失敗 test、重現腳本",
            )),
            ("Zero-shot prompt 設定", (
                "對每個函式詢問 LLM 是否含 bug 與根因為何",
                "無任務專屬範例,反映真實使用情境",
                "在消費級 CPU 推理,無 GPU 加速",
            )),
            ("自動化關鍵字評估器", (
                "對 LLM 自由文字回應,以 bug 修補關鍵字比對",
                "輸出對應到 Correct / Partial / Wrong 三類",
                "避免人工標註成本,結果可重現",
            )),
        ),
        evaluation_sections=(
            ("整體準確率", (
                "LLaMA 3.2:約 45%;Mistral:約 43%",
                "兩模型 McNemar 檢定 p=0.68,差異不顯著",
                "於 349 個樣本上 126 個皆對、169 個皆錯",
            )),
            ("跨專案變異", (
                "PySnooper:100% 兩模型皆對",
                "tqdm:LLaMA 3.2 0%、Mistral 14.3%",
                "matplotlib / pandas / sanic 錯誤率較高",
            )),
            ("跨 bug 類別變異", (
                "Null/None Check:~60% 兩模型最佳",
                "Type Conversion:0%(需 runtime 型別資訊)",
                "Other/Complex:LLaMA 21.7%、Mistral 16.7%(跨函式 bug)",
            )),
        ),
        system_flow=(
            ("BugsInPy 資料集", "349 個真實 Python production bug"),
            ("Function-level 切分", "每個 bug 對應一個函式"),
            ("Zero-shot prompt", "詢問 LLM 是否含 bug + 根因"),
            ("LLaMA 3.2 / Mistral 本機推理", "消費級硬體,無 GPU"),
            ("關鍵字評估器", "自由文字 → Correct/Partial/Wrong"),
            ("跨專案 / bug 類別統計", "識別瓶頸與互補性"),
        ),
        research_questions=(
            ("RQ1", "本機 open-weight LLM 在真實 Python production bug 上的整體偵測表現?"),
            ("RQ2", "LLaMA 3.2 與 Mistral 之間有顯著差異嗎?"),
            ("RQ3", "跨專案 / 跨 bug 類別的表現變異有多大,哪些因素主導?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="本機 LLM 在真實 bug 上的偵測表現?",
                table=(
                    ("模型", "整體準確率 (%)"),
                    ("LLaMA 3.2", "~45"),
                    ("Mistral", "~43"),
                    ("隨機關鍵字 baseline", "<5"),
                ),
                analysis=(
                    "兩模型皆顯著高於隨機 baseline",
                    "雖未達全自動 debug 水準,但約 40% 正確率已可作為輔助",
                    "近半輸出是「部分正確」—— 縮小搜尋範圍但無法給出精確修補",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="LLaMA 3.2 與 Mistral 之間是否有顯著差異?",
                table=(
                    ("配對結果", "計數"),
                    ("兩模型皆對", "126"),
                    ("兩模型皆錯", "169"),
                    ("LLaMA 對而 Mistral 錯", "25"),
                    ("Mistral 對而 LLaMA 錯", "29"),
                    ("McNemar p-value", "0.68"),
                ),
                analysis=(
                    "差異不顯著(p=0.68)—— 兩模型整體實力相當",
                    "但跨類別有互補性 —— Mistral 在 Indexing(+11.3 pp)強",
                    "LLaMA 在 Conditional Logic(+3.6 pp)略勝",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="跨專案 / bug 類別的表現變異?",
                table=(
                    ("Bug 類別", "LLaMA (%)", "Mistral (%)"),
                    ("Null/None Check (n=79)", "59.5", "60.8"),
                    ("Return Value (n=78)", "51.3", "51.3"),
                    ("Conditional Logic (n=55)", "40.0", "36.4"),
                    ("Indexing (n=44)", "36.4", "47.7"),
                    ("Type Conversion (n=4)", "0.0", "0.0"),
                    ("Other/Complex (n=60)", "21.7", "16.7"),
                ),
                analysis=(
                    "語法規律性高的類別(Null check / Return value)表現最佳",
                    "需要 runtime 資訊的(Type conversion)兩模型皆失效",
                    "跨函式的 Other/Complex 因 single-function prompt 限制而低落",
                ),
            ),
        ),
        core_observation=(
            "Open-weight LLM 在本機消費級硬體上 zero-shot 偵測真實 Python bug 的整體準確率"
            "約為 43–45%,雖未達全自動 debug 的可用水準,但已能在隱私敏感與資源受限場景中"
            "提供有意義的輔助 —— 尤其在 Null/None Check 與 Return Value 等語法規律性高的 bug。"
        ),
        limitations=(
            "Function-level 切分使跨函式 bug 偵測力顯著低落(Other/Complex 僅 ~20%)",
            "Type Conversion bug 兩模型皆 0%,需要 runtime 型別資訊才能診斷",
            "BugsInPy 雖為真實 bug 但仍偏向特定 Python 生態,未涵蓋其他語言",
            "Zero-shot 設定可能低估模型潛力 —— few-shot 或 fine-tuning 未測",
        ),
        future_work=(
            "Few-shot 與任務專屬 fine-tuning 對本機模型的提升幅度",
            "Ensemble 或模型選擇策略 —— 兩模型有互補強項",
            "整合 runtime trace 解決 Type Conversion 等動態 bug",
        ),
    ),
)


# ---------------------------------------------------------------------------
# 3. Janzen et al. 2026 — Gendered Prompting and LLM Code Review
# ---------------------------------------------------------------------------
JANZEN = Paper(
    source="local", source_id="janzen2026gendered",
    title="Gendered Prompting and LLM Code Review: How Gender Cues in the Prompt Shape Code Quality and Evaluation",
    authors=("Lynn Janzen", "Üveys Eroglu", "Dorothea Kolossa", "Pia Knöferle",
             "Sebastian Möller", "Vera Schmitt", "Veronika Solopova"),
    year=2026, venue="arXiv 2026",
    abstract=(
        "本文以三項互補研究探究性別與 LLM 程式碼審查的交互作用:"
        "(1) 自真實程式設計 prompt 中描繪性別語言模式;"
        "(2) 控制條件下觀察男性 / 女性使用者使用 LLM 的差異;"
        "(3) 對主流商用 LLM 系統性輸入帶性別線索的 prompt,並讓 LLM 充當審查員。"
        "結果指出:LLM 程式碼生成本身的準確度差異不大,但 **作為自動審查員時**"
        "對相同程式碼會因 prompt 性別線索給出不同評價 —— 這才是公平性風險真正所在。"
    ),
    url="https://arxiv.org/abs/2603.24359",
    arxiv_id="2603.24359", pdf_url=None,
    summary=PaperSummary(
        language="zh-tw", model=MODEL_TAG, raw_text_chars=63_204,
        pain_points=(
            ("LLM 程式碼工作流中的性別偏見幾未被檢視", (
                "Code 生成研究多聚焦準確率,忽略社會公平面向",
                "LLM-as-judge 取代人類審查時,偏見可能被自動化放大",
                "缺乏對「prompt 性別線索」如何影響 LLM 行為的實證",
            )),
            ("既有 LLM 訓練資料偏向男性程式設計師", (
                "公開程式碼 commit 歷史以男性開發者為主",
                "全球女性開發者僅約 23%(2023),核心開發者比例更低(~5%)",
                "模型對男性程式風格 / 用詞可能存在系統性偏好",
            )),
            ("LLM 程式碼生成基準可能高估能力", (
                "HumanEval / MBPP 等存在 data leakage 風險",
                "narrow task 形式忽略社會技術面向",
                "新基準如 CWE-VAL 才開始納入安全性",
            )),
            ("使用者層面的接受度差異", (
                "女性學生 / 專業人員使用 ChatGPT 較少",
                "回報較低的 prompt 自信",
                "可能造成 LLM 輔助工作流的入門落差"
            )),
        ),
        research_question=(
            "(RQ1)使用者性別是否反映在 prompt 的語言風格上,以致僅憑 prompt 文字"
            "即可預測?(RQ2)gendered prompting 是否會在 LLM 程式碼生成出現差異?"
            "(RQ3)同樣的 prompt 性別線索,是否會在 LLM 充當審查員時造成差異化評價?"
        ),
        contributions_detailed=(
            ("1. 真實 prompt 的性別語言模式刻畫",
             "從真實程式設計 prompt 中提取性別語言模式(politeness、hedges、"
             "involved / informational scores),建立可從 prompt 文字預測性別的分類器。"),
            ("2. 受控條件下的男女使用差異研究",
             "三項控制 coding 任務,觀察男 / 女參與者如何使用 LLM,並收集程式碼品質"
             "與 prompt 屬性(長度、複雜度、直接 / 間接請求)。"),
            ("3. LLM 作為審查員的性別效應實驗",
             "對主流商用 LLM 系統性輸入 gender-coded prompts 並讓其評價程式碼;"
             "發現程式碼生成準確度差異有限,但「LLM-as-judge」時對相同程式碼會給出不同評價。"),
            ("4. 公平性風險的重新定位",
             "把 LLM 輔助程式設計的公平性問題從「生成」重新定位到「評估」階段,指出"
             "LLM-as-judge 趨勢中的隱藏偏見才是核心風險。"),
        ),
        headline_metrics=(
            ("全球女性開發者比例(2023)", "23%", "SlashData 報告"),
            ("Open-source 核心開發者女性比例", "~5%", "Trinkenreich et al. 2022"),
            ("研究設計", "3 項互補研究", "prompt 分析 + 使用者研究 + LLM 審查模擬"),
            ("性別預測 baseline", "可從 prompt 文字預測", "顯著高於隨機"),
            ("生成準確度差異", "不顯著", "程式碼是否正確不因 prompt 性別變"),
            ("審查評價差異", "存在跨模型變異", "LLM-as-judge 是公平性風險主源"),
        ),
        technique_table=(
            ("Carvajal et al. 2024", "女性學生較少使用 ChatGPT,prompt 自信較低"),
            ("Brooke 2024", "男 / 女 / 其他性別開發者程式碼風格有顯著差異"),
            ("Mashburn et al. 2025", "politeness / formality / length 未達顯著差異"),
            ("Long et al. 2025", "prompt 任務 framing / decomposition 影響大"),
            ("Leidinger et al. 2023", "微小語言改動會大幅影響跨任務穩定性"),
            ("本論文", "三項研究:prompt 模式 + 用戶研究 + LLM-as-judge 偏見實驗"),
        ),
        method_sections=(
            ("Study 1:真實 prompt 性別模式", (
                "從真實程式設計 prompt 抽取語言特徵",
                "Politeness markers、hedges、involved / informational scores",
                "建立性別分類器,衡量是否可從文字預測",
            )),
            ("Study 2:受控使用者研究", (
                "招募男 / 女參與者執行 3 項 coding 任務",
                "使用 ChatGPT 解題,記錄完整 prompt 歷史 + 程式碼",
                "比較使用模式、解題策略與最終程式碼品質",
            )),
            ("Study 3:LLM-as-judge 偏見模擬", (
                "對同一段程式碼套入帶性別線索的審查請求 prompt",
                "送入多個商用 LLM 家族(GPT、Claude 等)做評價",
                "比較相同程式碼下不同性別線索的審查結果差異",
            )),
        ),
        evaluation_sections=(
            ("Prompt 語言模式(Study 1)", (
                "性別可從 prompt 文字預測 —— 顯著高於隨機",
                "女性 prompt 含較多 politeness、hedges、indirect 請求",
                "男性 prompt 較直接、task-oriented、efficiency-focused",
            )),
            ("實際 LLM 使用差異(Study 2)", (
                "女性參與者較常用 indirect 形式問問題",
                "對等任務下程式碼品質差異不顯著",
                "Prompt 長度與複雜度與最終品質有相關性",
            )),
            ("LLM 審查員偏見(Study 3)", (
                "同一段程式碼下,LLM 對性別線索敏感",
                "審查行為跨 LLM 家族有差異(不是單一模型問題)",
                "生成階段公平,但評估階段不公平"
            )),
            ("跨研究綜合", (
                "公平性風險集中在 evaluation 而非 generation",
                "LLM-as-judge 趨勢需要納入偏見審計",
                "Code length 與 maintainability 受性別 prompt 風格影響",
            )),
        ),
        system_flow=(
            ("真實 prompt 蒐集", "Study 1:大規模 prompt 語料庫"),
            ("性別特徵抽取", "politeness、hedges、involvedness"),
            ("受控使用者實驗", "Study 2:男 / 女各執行 3 個 coding 任務"),
            ("Gender-coded prompt 模擬", "Study 3:輸入性別線索 + 同一段程式碼"),
            ("LLM-as-judge 評價", "對程式碼品質給分 / 評論"),
            ("跨研究綜合", "識別公平性風險點"),
        ),
        research_questions=(
            ("RQ1", "使用者性別是否可從 prompt 文字預測?"),
            ("RQ2", "gendered prompting 是否影響 LLM 程式碼生成?"),
            ("RQ3", "gendered prompting 是否影響 LLM 程式碼審查評價?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="性別可從 prompt 文字預測嗎?",
                table=(
                    ("性別特徵", "差異"),
                    ("Politeness markers", "女性顯著較多"),
                    ("Hedges / indirect 請求", "女性顯著較多"),
                    ("Task-oriented 直接陳述", "男性較多"),
                    ("分類器表現", "顯著高於隨機"),
                ),
                analysis=(
                    "是 —— 純文字即可顯著預測 prompt 作者性別",
                    "與 1970–2000 年代性別語言學文獻一致",
                    "意味 LLM 可以「無意識地」感知 prompt 作者的性別線索",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="性別 prompting 影響程式碼生成嗎?",
                table=(
                    ("觀察項", "結果"),
                    ("程式碼最終正確率", "差異不顯著"),
                    ("程式碼長度", "受 prompt 風格影響"),
                    ("可維護性", "受 prompt 風格影響"),
                    ("Prompt 長度 / 複雜度與品質", "有相關性"),
                ),
                analysis=(
                    "生成階段的公平性風險有限 —— 程式碼準確度不因性別 prompt 變",
                    "但 surface-level 品質指標(長度 / 可維護性)會被影響",
                    "支持「LLM 生成尚屬中性,但邊際品質有差別」的結論",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="性別 prompting 影響 LLM 程式碼審查嗎?",
                table=(
                    ("觀察項", "結果"),
                    ("LLM-as-judge 對同一段碼", "依 prompt 性別線索給不同評價"),
                    ("審查行為跨 LLM 家族", "存在差異"),
                    ("公平性風險主源", "Evaluation 階段 > Generation 階段"),
                ),
                analysis=(
                    "是 —— 這是論文最關鍵的發現",
                    "LLM-as-judge 取代人類審查時會把社會偏見自動化",
                    "需要在審查 prompt 中去除或標準化性別線索,或對 LLM 做偏見審計",
                ),
            ),
        ),
        core_observation=(
            "LLM 輔助程式設計的公平性風險「不在生成、而在評估」:LLM 生成程式碼的正確率"
            "對 prompt 性別線索不敏感,但 LLM 充當審查員時,對相同程式碼會因 prompt 性別"
            "給出不同評價 —— LLM-as-judge 趨勢正在把社會偏見自動化。"
        ),
        limitations=(
            "樣本量相對較小,且性別主要採二元(binary)操作化",
            "Non-binary 與 trans 開發者僅各一份回應,難以做統計推論",
            "Study 2 受實驗時間限制,只測 3 項 coding 任務",
            "Study 3 用商用 LLM 黑盒測試,未能拆解內部偏見機制",
        ),
        future_work=(
            "擴大樣本並納入非二元性別的系統研究",
            "對 LLM-as-judge 訓練資料中的性別 distribution 做透明化審計",
            "建立 LLM 程式碼審查的「性別中性化」prompt 規範",
        ),
    ),
)


# ---------------------------------------------------------------------------
# 4. Khan et al. 2026 — Survey of Code Review Benchmarks
# ---------------------------------------------------------------------------
KHAN = Paper(
    source="local", source_id="khan2026survey",
    title="A Survey of Code Review Benchmarks and Evaluation Practices in Pre-LLM and LLM Era",
    authors=("Taufiqul Islam Khan", "Shaowei Wang", "Haoxiang Zhang", "Tse-Hsun Chen"),
    year=2026, venue="arXiv 2026 (37-page survey)",
    abstract=(
        "本綜述系統整理 2015–2025 年間 61 篇 Pre-LLM 與 45 篇 LLM 程式碼審查研究,"
        "提出五大高階任務 + 18 個子任務的多層次分類法,並比較兩個時代的資料集、評估指標、"
        "與 granularity。關鍵發現:Change Understanding 從 14 個資料集萎縮到 1 個,"
        "Peer Review 在 LLM 時代占近 60%,單語資料集從 59% 降至 34%(多語化),"
        "研究焦點從「協助人類」轉向「end-to-end 自動生成」。"
    ),
    url="https://arxiv.org/abs/2602.13377",
    arxiv_id="2602.13377", pdf_url=None,
    summary=PaperSummary(
        language="zh-tw", model=MODEL_TAG, raw_text_chars=137_254,
        pain_points=(
            ("缺少完整的 LLM 程式碼審查基準對照", (
                "既有綜述多聚焦 code generation,而非 review",
                "code review 涵蓋的子任務分散,難以選對資料集",
                "難以做跨研究的公平比較",
            )),
            ("Pre-LLM 與 LLM 時代資料集設計差異大", (
                "Pre-LLM:任務細分、語言單一、人類協助為主",
                "LLM 時代:end-to-end 自動生成、多語、評估指標改變",
                "兩個世代未經系統對照,趨勢理解模糊",
            )),
            ("評估指標與 granularity 缺乏標準化", (
                "Chunk / file / commit / PR 各種粒度並存",
                "BLEU / ROUGE / human eval / pass-revision 等指標各家不同",
                "新研究選擇基準時缺乏指引",
            )),
            ("Static evaluation 無法反映真實審查價值", (
                "現行多為靜態指標,缺少 runtime / dynamic 驗證",
                "未量化「審查後 build 是否成功 / 測試是否通過」",
                "與真實開發流程脫鉤",
            )),
        ),
        research_question=(
            "(RQ1)Pre-LLM 時代程式碼審查研究有哪些任務 / 資料集 / 評估策略?"
            "(RQ2)LLM 時代的任務與評估策略有何演化?"
            "(RQ3)兩個時代之間的趨勢與落差為何,該如何指引未來基準設計?"
        ),
        contributions_detailed=(
            ("1. 多層次任務分類法",
             "把既有研究歸入 5 個高階領域(Review Prioritization、Change Understanding、"
             "Peer Review、Review Assessment、Code Refinement),細分為 18 個子任務;"
             "讓研究者能精準匹配 benchmark。"),
            ("2. 評估指標 / 資料來源 / 粒度的系統分類",
             "對 106 篇研究做指標 / 資料來源 / granularity 的系統映射,"
             "提供跨研究比較的標準框架。"),
            ("3. Pre-LLM 與 LLM 時代轉變的量化分析",
             "Change Understanding 資料集從 14 個跌到 1 個;Peer Review 占近 60%;"
             "單語資料集比例從 59% 降到 34%(34% 涵蓋九種以上語言);"
             "焦點從人類協助轉向 end-to-end 生成。"),
            ("4. 未來基準設計指引",
             "提出三大方向:擴充任務覆蓋(macro-level 評估、commit decomposition)、"
             "從 static 到 dynamic 評估(build / test 結果)、依分類法做細粒度評估。"),
        ),
        headline_metrics=(
            ("Pre-LLM 程式碼審查論文", "61", "2015–2025 涵蓋"),
            ("LLM 程式碼審查論文", "45", "同期"),
            ("高階任務領域", "5", "Prioritization / Understanding / Peer Review / Assessment / Refinement"),
            ("子任務細分", "18", "完整分類法"),
            ("Change Understanding 資料集", "14 → 1", "Pre-LLM → LLM 時代"),
            ("Peer Review 占比(LLM 時代)", "~60%", "資料集分布"),
        ),
        technique_table=(
            ("Pre-LLM 主流方法", "規則 / 統計 / 傳統 ML"),
            ("Pre-LLM 任務分布", "平均散落於 5 個高階領域"),
            ("LLM 時代主流方法", "End-to-end 生成 / fine-tuning / 提示工程"),
            ("LLM 任務分布", "Peer Review 主導(~60%)"),
            ("資料集語言廣度", "Pre-LLM:59% 單語;LLM:34% ≥9 種語言"),
            ("評估指標趨勢", "從 BLEU/ROUGE 走向 pass-revision、human eval、build success"),
        ),
        method_sections=(
            ("系統性論文蒐集與篩選", (
                "2015–2025 跨 10 年,從多個資料庫收集",
                "Pre-LLM:61 篇;LLM:45 篇",
                "經四作者交叉確認任務分類",
            )),
            ("分類法建構", (
                "由下而上歸納出 5 個高階任務領域",
                "進一步細分為 18 個子任務",
                "兼顧傳統與 LLM 時代的研究",
            )),
            ("跨時代對照分析", (
                "在每個任務領域比較 Pre-LLM / LLM 的資料集數量",
                "分析評估指標 / 粒度 / 語言的演化",
                "識別未被覆蓋的 macro-level 任務缺口",
            )),
        ),
        evaluation_sections=(
            ("任務分布的世代差異", (
                "Pre-LLM:5 個領域分布相對平均",
                "LLM:Peer Review 主導(~60%)",
                "Change Understanding 從支柱變邊緣(14 → 1)",
            )),
            ("資料集語言廣度", (
                "Pre-LLM:59% 為單語",
                "LLM:34% 涵蓋 9 種以上語言",
                "多語化是 LLM 時代最明顯的趨勢",
            )),
            ("評估指標轉變", (
                "Pre-LLM:靜態 surface 指標(BLEU、ROUGE)",
                "LLM:逐漸納入 pass-revision、build success、human eval",
                "但仍以 static 為主,動態驗證缺口仍大",
            )),
            ("Granularity 趨勢", (
                "從 chunk / file 級走向 PR / repository 級",
                "End-to-end 自動生成要求更高層次的評估",
                "細粒度子任務評估仍不足",
            )),
        ),
        system_flow=(
            ("收集 106 篇論文", "2015–2025 系統檢索"),
            ("任務歸納", "5 高階 + 18 子任務分類"),
            ("資料集 / 指標分類", "粒度 / 語言 / 評估指標"),
            ("Pre-LLM vs LLM 對照", "量化跨世代演化"),
            ("缺口識別", "macro-level、dynamic、細粒度"),
            ("未來方向建議", "提供基準設計指引"),
        ),
        research_questions=(
            ("RQ1", "Pre-LLM 時代程式碼審查研究的任務與評估策略為何?"),
            ("RQ2", "LLM 時代的任務與評估策略有何演化?"),
            ("RQ3", "兩個時代間的趨勢與落差為何?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="Pre-LLM 時代研究輪廓?",
                table=(
                    ("任務領域", "Pre-LLM 資料集數量"),
                    ("Review Prioritization", "中等"),
                    ("Change Understanding", "14"),
                    ("Peer Review", "中等"),
                    ("Review Assessment", "少"),
                    ("Code Refinement", "中等"),
                ),
                analysis=(
                    "Pre-LLM 任務分布相對平均",
                    "Change Understanding 是研究支柱(14 個資料集)",
                    "以協助人類審查員為主要動機",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="LLM 時代的演化?",
                table=(
                    ("觀察項", "LLM 時代狀況"),
                    ("Peer Review 占資料集比例", "~60%"),
                    ("Change Understanding 資料集", "1(從 14 萎縮)"),
                    ("多語資料集 ≥9 種語言", "34%"),
                    ("評估指標", "走向 pass-revision、human eval"),
                ),
                analysis=(
                    "焦點從「協助人類」轉向「end-to-end 自動生成」",
                    "Change Understanding 被併入生成式工作流",
                    "Peer Review 成為主導 —— 因 LLM 可自然產生 review comments",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="兩個時代的落差?",
                table=(
                    ("缺口面向", "建議方向"),
                    ("Macro-level 評估", "Impact analysis、commit decomposition"),
                    ("Static → Dynamic", "Build success、test pass rate"),
                    ("細粒度評估", "依任務分類法做子任務級評估"),
                    ("多模型 ensemble", "尚未系統評估"),
                ),
                analysis=(
                    "現行基準仍以 static 為主,缺乏 runtime 驗證",
                    "Macro-level(commit-level decomposition、impact)未被覆蓋",
                    "Taxonomy-guided 細粒度評估是未來方向",
                ),
            ),
        ),
        core_observation=(
            "從 Pre-LLM 到 LLM 時代,程式碼審查研究經歷一場「重新定位」:"
            "焦點從協助人類審查員轉向 end-to-end 自動生成,Peer Review 從多任務之一變成"
            "主導(~60%),語言廣度倍增,但評估指標仍以 static 為主、缺乏 dynamic 驗證"
            "與 macro-level 任務覆蓋。"
        ),
        limitations=(
            "綜述涵蓋 2015–2025,LLM 時代僅 3 年(2023–2025)樣本數較少",
            "任務分類雖經多作者交叉確認,仍有主觀邊界",
            "未對每篇論文做品質分級,僅做任務 / 指標分類",
            "未深入分析具體 LLM 模型差異 —— 聚焦在 benchmark 設計層面",
        ),
        future_work=(
            "建立 macro-level 評估基準(commit decomposition、impact analysis)",
            "從 static 走向 dynamic 評估 —— 整合 build / test 結果",
            "依 18 個子任務做細粒度評估,把 LLM 能力地圖畫得更精細",
        ),
    ),
)


ALL_PAPERS = (CHAROENWET, VULICEVIC, JANZEN, KHAN)


def main() -> None:
    out_dir = ROOT / "exports" / _RUN_DIR_NAME
    out_dir.mkdir(parents=True, exist_ok=True)
    for paper in ALL_PAPERS:
        collection = PaperCollection(
            query=Query(
                keywords="LLM 程式碼審查",
                sources=("local",),
                max_results=1,
            ),
            papers=(paper,),
        )
        options = ExportOptions(
            formats=("pptx",),
            out_dir=str(out_dir),
            # zh-tw 變體 — 唯一允許 -zh-tw 後綴的例外。
            filename_stem=f"{paper.bibtex_key()}-zh-tw",
            include_abstract=True,
            language="zh-tw",
        )
        written = export_collection(collection, options)
        for fmt, path in written.items():
            print(f"  - {paper.bibtex_key()} {fmt}: {path}")


if __name__ == "__main__":
    main()
