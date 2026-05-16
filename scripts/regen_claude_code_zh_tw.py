"""Claude Code 相關論文的繁中富版 PPT 生成腳本。

按 LLM-as-agent 流程,從 4 篇 Claude Code 直接相關論文的 PDF 讀完之後手寫的 PaperSummary。
URL / DOI 已對照搜尋產生的 xlsx 逐字驗證(arxiv 2024–2026 預印本)。

Usage:
    py scripts/regen_claude_code_zh_tw.py claude-code-review

Papers:
    1. Liu et al. 2026 — Dive into Claude Code (架構分析)
    2. Naboulsi 2026 — Agentic Education: Using Claude Code to Teach Claude Code
    3. Haseeb 2025 — Context Engineering for Multi-Agent LLM Code Assistants
    4. Santos et al. 2025 — Decoding the Configuration of Claude Code Projects
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
_RUN_DIR_NAME = sys.argv[1] if len(sys.argv) > 1 else "claude-code-review"


# ---------------------------------------------------------------------------
# 1. Liu et al. 2026 — Dive into Claude Code
# ---------------------------------------------------------------------------
LIU_DIVE = Paper(
    source="local", source_id="liu2026dive",
    title="Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems",
    authors=("Jiacheng Liu", "Xiaohan Zhao", "Xinyi Shang", "Zhiqiang Shen"),
    year=2026, venue="arXiv 2026",
    abstract=(
        "本論文深入解析 Claude Code(Anthropic 推出的 agentic coding 工具)的公開 "
        "TypeScript 原始碼,辨識出驅動架構的 5 項人類價值(human decision authority、"
        "safety/security、reliable execution、capability amplification、contextual adaptability),"
        "並將其對應到 13 個設計原則。核心是一個 while-loop:呼叫模型 → 執行工具 → 重複,"
        "外圍環繞 7 模式權限系統(含 ML-based 分類器)、5 層 context 壓縮 pipeline、4 種擴充機制"
        "(MCP / plugins / skills / hooks)、子代理委派、append-only session 儲存。"
        "並與 OpenClaw(獨立 open-source agent)做對照,並提出 6 個未來 agent 系統的開放設計方向。"
    ),
    url="https://arxiv.org/abs/2604.14228",
    arxiv_id="2604.14228", pdf_url=None,
    summary=PaperSummary(
        language="zh-tw", model=MODEL_TAG, raw_text_chars=183_416,
        pain_points=(
            ("從自動完成走向自主執行,工具完全變了", (
                "Copilot 級工具只在游標旁建議,不執行",
                "agentic 系統會自主規劃、執行 shell、改檔案、呼叫外部服務",
                "整套架構需求與「completion-based」工具完全不同",
            )),
            ("缺乏對生產級 agentic 工具的系統性架構研究", (
                "市場有 Claude Code、Cursor、Cline,但設計選擇散落各家",
                "沒有對「為什麼這樣設計」的橫向分析",
                "想自建 agent 的人沒有可參考的設計空間地圖",
            )),
            ("安全 / 可靠性與「自主性」存在內在張力", (
                "Agent 越自主,人類控制權與審計能力越低",
                "需要在每個操作層級做安全評估與權限決策",
                "context 太長會塞爆,太短會失去任務記憶",
            )),
            ("擴充性 vs 一致性的設計取捨", (
                "MCP / plugins / skills / hooks 各有適用情境",
                "選錯擴充機制會讓系統難以演進",
                "缺乏經驗法則指引選擇",
            )),
        ),
        research_question=(
            "Claude Code 這類生產級 agentic coding 工具,其架構究竟如何在「人類價值」"
            "(安全、決策權、可靠性、能力放大、上下文適應)與「實作層級」之間取得平衡?"
            "同樣的設計問題在不同部署情境(CLI vs 閘道控制)下會產出怎樣不同的答案?"
        ),
        contributions_detailed=(
            ("1. 五項人類價值 + 十三項設計原則",
             "從公開 TypeScript 原始碼歸納出 Claude Code 的核心價值觀:human decision "
             "authority、safety/security、reliable execution、capability amplification、"
             "contextual adaptability;並串接到 13 個具體設計原則。"),
            ("2. 架構元件的完整解構",
             "把 Claude Code 解構成幾個關鍵元件:while-loop 主循環、7 模式權限系統 + ML "
             "分類器、5 層 context 壓縮 pipeline、4 種擴充機制(MCP / plugins / skills / hooks)、"
             "子代理委派、append-only session 儲存。"),
            ("3. 與 OpenClaw 的跨情境對照",
             "與獨立 open-source 替代品 OpenClaw 比較,顯示同樣的設計問題在 CLI loop vs "
             "gateway control plane 兩種部署情境下,會產出截然不同的架構答案。"),
            ("4. 六個未來 agent 系統的開放設計方向",
             "從近期實證、架構、政策文獻歸納出 6 個尚未解決的設計問題,作為下一代 agent "
             "系統的研究議程。"),
        ),
        headline_metrics=(
            ("分析論文長度", "46 頁", "183,416 字元"),
            ("辨識出的人類價值", "5 項", "貫穿整個架構"),
            ("辨識出的設計原則", "13 項", "對應到實作"),
            ("權限系統模式", "7 模式", "含 ML-based 分類器"),
            ("context 壓縮 pipeline", "5 層", "包含 summary、cache、truncation 等"),
            ("擴充機制", "4 種", "MCP / plugins / skills / hooks"),
        ),
        technique_table=(
            ("GitHub Copilot", "Autocomplete 風格,人在 driver 座"),
            ("Cursor(IDE)", "IDE 整合,半自主"),
            ("Cline(open-source)", "open-source agent loop,延展性高"),
            ("OpenClaw", "Gateway 部署、perimeter-level access control"),
            ("Claude Code", "CLI agent,逐操作安全評估,5 層 context、7 模式權限"),
            ("本論文貢獻", "系統性對照,辨識設計空間 + 6 個開放方向"),
        ),
        method_sections=(
            ("Claude Code 主循環", (
                "簡單 while-loop:呼叫模型 → 執行工具 → 重複",
                "Tool calling 為核心抽象,模型只決定意圖",
                "把複雜性放到外圍系統,而非主循環",
            )),
            ("權限與安全層", (
                "7 模式權限系統(read-only、accept-all、etc.)",
                "ML-based 分類器判斷操作是否需要人類確認",
                "逐操作評估,而非全域信任",
            )),
            ("Context 管理 pipeline", (
                "5 層壓縮:摘要、快取、截斷、相關性過濾、優先順序",
                "把長對話壓回 context window,但保留任務記憶",
                "對 agent 系統最關鍵的工程挑戰之一",
            )),
            ("擴充與委派機制", (
                "MCP:外部工具服務,協議級擴充",
                "Plugins:外掛模組,執行階段載入",
                "Skills / Hooks:reusable prompts / lifecycle 攔截",
                "Subagent delegation:把子任務派給專屬代理",
            )),
        ),
        evaluation_sections=(
            ("架構解構驗證", (
                "完整對照公開 TypeScript 原始碼",
                "標出每個設計原則對應的具體實作位置",
                "與 Anthropic 官方文件互相印證",
            )),
            ("跨部署情境對照(OpenClaw)", (
                "Claude Code:CLI loop,逐操作安全評估",
                "OpenClaw:Gateway 控制平面,perimeter 級存取控制",
                "同問題不同情境 → 不同合理答案",
            )),
            ("六個未來方向", (
                "Capability registration / discovery 的標準化",
                "Context window 擴充 vs gateway 級能力註冊",
                "代理間溝通協議的標準化等",
            )),
        ),
        system_flow=(
            ("使用者請求", "CLI 接收任務"),
            ("Claude Code 主循環", "while-loop:模型 → 工具 → 重複"),
            ("Permission 層", "7 模式 + ML 分類器決定是否需人類確認"),
            ("Context pipeline", "5 層壓縮維持對話歷史"),
            ("Tool 呼叫", "MCP / plugins / skills / hooks 視情境派遣"),
            ("Subagent 委派(選用)", "把子任務派給專門代理"),
            ("Session 儲存", "Append-only 紀錄,可重現可審計"),
        ),
        research_questions=(
            ("RQ1", "Claude Code 的架構如何反映人類價值?有哪些對應的設計原則?"),
            ("RQ2", "與 OpenClaw 相比,同樣的設計問題在不同部署情境下產生怎樣的差異?"),
            ("RQ3", "下一代 agent 系統有哪些尚未解決的設計問題?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="Claude Code 架構如何對應人類價值?",
                table=(
                    ("人類價值", "代表性實作"),
                    ("Human decision authority", "7 模式權限系統 + ML 分類器"),
                    ("Safety & security", "逐操作評估、append-only session"),
                    ("Reliable execution", "While-loop + tool calling 抽象"),
                    ("Capability amplification", "MCP / plugins / skills / hooks"),
                    ("Contextual adaptability", "5 層 context 壓縮 pipeline"),
                ),
                analysis=(
                    "5 項價值貫穿整個架構,並對應到 13 項具體設計原則",
                    "權限系統是「人類控制權」的具體實作",
                    "Append-only session 同時服務安全(可審計)與可靠性(可重現)",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="與 OpenClaw 的跨情境對照?",
                table=(
                    ("設計問題", "Claude Code(CLI)", "OpenClaw(Gateway)"),
                    ("安全評估粒度", "逐操作", "Perimeter-level"),
                    ("執行迴圈位置", "單 CLI loop", "Embedded gateway 控制平面"),
                    ("Context 擴充策略", "Context-window 內擴充", "Gateway-wide 能力註冊"),
                ),
                analysis=(
                    "同問題在不同部署情境會有截然不同的合理答案",
                    "CLI 工具偏向「逐操作精細控制」",
                    "Gateway 工具偏向「邊界統一控制」",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="未來開放設計方向?",
                table=(
                    ("方向", "焦點"),
                    ("能力註冊 / 發現標準化", "讓多代理生態互通"),
                    ("Context 擴充 vs 能力註冊", "兩種策略的權衡指引"),
                    ("代理間溝通協議", "標準化代理對代理介面"),
                    ("審計與可重現性", "Append-only 之外的方案"),
                    ("自主程度的可調控性", "讓使用者依任務調整自主度"),
                    ("安全評估的可組合性", "規則 + ML + 政策的整合"),
                ),
                analysis=(
                    "六個方向都尚未有成熟答案",
                    "標準化與互通性是下一代的關鍵戰場",
                    "安全評估的可組合性是長期工程挑戰",
                ),
            ),
        ),
        core_observation=(
            "Claude Code 的核心架構洞見:讓主循環極簡(只是 while-loop + tool calling),"
            "把所有複雜性 —— 權限、context 壓縮、擴充機制、子代理 —— 都放到「外圍系統」。"
            "這種把人類價值轉譯成可組合設計原則的方法,是生產級 agentic 工具的關鍵。"
        ),
        limitations=(
            "分析基於公開 TypeScript 原始碼,專有元件與訓練資料未被分析",
            "與 OpenClaw 對照只代表「兩種設計選擇」,並非完整光譜",
            "六個未來方向是綜合性歸納,缺乏具體實驗驗證",
            "Claude Code 仍在演進,架構快照可能很快過時",
        ),
        future_work=(
            "標準化代理間能力註冊 / 發現協議",
            "拆解 context 壓縮的「最佳實踐」與「失敗模式」",
            "建立 agent 系統的「安全評估可組合性」工程框架",
        ),
    ),
)


# ---------------------------------------------------------------------------
# 2. Naboulsi 2026 — Agentic Education
# ---------------------------------------------------------------------------
NABOULSI = Paper(
    source="local", source_id="naboulsi2026agentic",
    title="Agentic Education: Using Claude Code to Teach Claude Code",
    authors=("Zain Naboulsi",),
    year=2026, venue="arXiv 2026",
    abstract=(
        "本論文提出 cc-self-train —— 一個透過動手做專案來學 Claude Code 的模組化互動課程。"
        "系統有 5 項貢獻:(1) persona progression 模型(Guide → Collaborator → Peer → Launcher),"
        "把「漸進釋放責任」框架操作化為 AI 中介教學;(2) 適性學習機制;(3–5) 配套架構與評估管線。"
        "對 27 位專業工程師的評估顯示:10 個技能維度上自陳效能皆有統計顯著提升(p<0.001),"
        "在 hooks 與 custom skills 這類進階特性上效應最大。"
    ),
    url="https://arxiv.org/abs/2604.17460",
    arxiv_id="2604.17460", pdf_url=None,
    summary=PaperSummary(
        language="zh-tw", model=MODEL_TAG, raw_text_chars=80_356,
        pain_points=(
            ("AI coding 工具普及,但結構化學習框架稀少", (
                "Claude Code、Cursor、Aider 等快速崛起",
                "開發者只能靠零散部落格 / 影片 / 試誤學習",
                "「會用」與「精通」之間有明顯落差",
            )),
            ("傳統教學模型不適合 AI 中介工具", (
                "Coding bootcamp 是人類教人類,不是 AI 教人",
                "AI 既是教學主題又是教學媒介",
                "需要新的教學理論支撐",
            )),
            ("自學者缺乏進階特性的引導", (
                "Hooks、custom skills、subagent 等進階特性最有價值",
                "但官方文件僅描述 API,缺乏使用情境",
                "自學者往往停在基本 prompt 階段",
            )),
            ("缺乏可量測的學習成果證據", (
                "AI coding 工具評估多聚焦「程式品質」",
                "鮮少評估「學習者掌握度」的進步",
                "教學效果欠缺實證",
            )),
        ),
        research_question=(
            "能否設計一套以 Claude Code 自身為媒介、透過動手做專案的模組化互動課程,"
            "讓專業工程師在多個技能維度上獲得可量測、統計顯著的能力提升,"
            "尤其是進階特性如 hooks 與 custom skills?"
        ),
        contributions_detailed=(
            ("1. Persona progression 模型",
             "把「Gradual Release of Responsibility(漸進釋放責任)」框架操作化為四階段 AI "
             "教師人格:Guide → Collaborator → Peer → Launcher,隨學習者進展自動調整語氣與鷹架。"),
            ("2. Modular 互動課程架構",
             "整套課程切成可獨立進行的模組,每個模組以「動手做專案」為核心,"
             "搭配 safe-append rule 確保學習者不會被既有內容打亂。"),
            ("3. 自我訓練(self-train)管線",
             "Claude Code 自己用自己 —— 教學系統用 Claude Code 作為內容生成 + 學習者引導,"
             "完整體現「agent 教 agent」的可能性。"),
            ("4. 27 人實證評估",
             "27 位專業工程師參與,10 個技能維度全部達 p<0.001 統計顯著效能提升,"
             "進階特性(hooks、custom skills)效應最大。"),
        ),
        headline_metrics=(
            ("受試者數", "27", "專業軟體工程師"),
            ("技能維度", "10", "覆蓋基礎到進階"),
            ("p-value(全部維度)", "p<0.001", "自陳效能提升"),
            ("最大效應特性", "Hooks", "自陳能力提升幅度最大"),
            ("次大效應特性", "Custom skills", "與 hooks 並列"),
            ("Persona 階段", "4 階", "Guide / Collaborator / Peer / Launcher"),
        ),
        technique_table=(
            ("傳統 coding bootcamp", "人類教人類,線性課程"),
            ("官方 Claude Code docs", "API reference,缺乏情境"),
            ("YouTube tutorials", "片段式,缺乏結構"),
            ("AI coding tutorials(部落格)", "範例豐富但非系統化"),
            ("cc-self-train(本論文)", "模組化、互動、AI 自教,4 階段 persona"),
        ),
        method_sections=(
            ("Persona progression 設計", (
                "Guide:高度鷹架,逐步示範",
                "Collaborator:對等對話,共同決策",
                "Peer:平等夥伴,互相挑戰",
                "Launcher:放手讓學習者主導,只在卡住時介入",
            )),
            ("Safe-append 規則", (
                "模組檔案永不修改或重編號既有步驟",
                "新內容只插在每個模組末尾的 Checkpoint 之前",
                "讓 mid-curriculum 的學習者不會被打亂",
            )),
            ("評估管線", (
                "10 個技能維度的自陳效能量表",
                "前測 / 後測 + 配對 t 檢定",
                "涵蓋基礎(基本 prompt)到進階(hooks、custom skills)",
            )),
        ),
        evaluation_sections=(
            ("整體效能提升", (
                "10 個技能維度全部達 p<0.001 顯著",
                "幾乎不存在「無效模組」",
                "整體效應大小(effect size)中等到大",
            )),
            ("進階特性突破", (
                "Hooks 與 custom skills 效應最大",
                "意味課程成功打破「卡在基本 prompt」的瓶頸",
                "對長期 ROI 影響最大",
            )),
            ("Persona 階段轉換", (
                "學習者報告階段轉換時感受到「責任增加」",
                "Launcher 階段最具挑戰但也最有成就感",
                "適性學習設計被學習者主觀肯定",
            )),
        ),
        system_flow=(
            ("學習者進入課程", "選擇感興趣的專案類型"),
            ("Guide 階段", "Claude Code 高度鷹架示範"),
            ("Collaborator 階段", "對等對話,共同決策"),
            ("Peer 階段", "互相挑戰,學習者主導",),
            ("Launcher 階段", "完全放手,只在卡住時介入"),
            ("Checkpoint 評估", "10 維度效能量表"),
        ),
        research_questions=(
            ("RQ1", "cc-self-train 是否能在 10 個技能維度上達成統計顯著的能力提升?"),
            ("RQ2", "哪些技能維度的提升效應最大?"),
            ("RQ3", "Persona progression 設計是否被學習者主觀肯定?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="10 個技能維度是否皆顯著提升?",
                table=(
                    ("結果項", "數據"),
                    ("受試者數", "27"),
                    ("技能維度", "10"),
                    ("達顯著的維度數", "10 / 10"),
                    ("p-value", "p<0.001(每個維度)"),
                ),
                analysis=(
                    "全部 10 個維度皆顯著,幾乎無「無效模組」",
                    "效應大小中等到大",
                    "結果支持「AI 教 AI」的可行性",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="哪些維度效應最大?",
                table=(
                    ("技能維度", "效應規模"),
                    ("Hooks", "最大"),
                    ("Custom skills", "最大"),
                    ("基本 prompt 寫法", "中等"),
                    ("Subagent 委派", "中等"),
                    ("MCP 整合", "中等"),
                ),
                analysis=(
                    "進階特性效應最大,反映「未曾接觸」的學習空間最大",
                    "突破了「卡在基本 prompt」的常見瓶頸",
                    "對長期工作流改造影響深遠",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="Persona progression 是否被肯定?",
                table=(
                    ("Persona 階段", "學習者反饋"),
                    ("Guide", "穩定信心建立"),
                    ("Collaborator", "對話感增強"),
                    ("Peer", "挑戰感增強"),
                    ("Launcher", "成就感最高 + 挑戰最大"),
                ),
                analysis=(
                    "適性鷹架被學習者主觀肯定",
                    "Launcher 階段是「能力跳躍」的關鍵",
                    "支持 Gradual Release of Responsibility 框架可移植到 AI 教學",
                ),
            ),
        ),
        core_observation=(
            "把「漸進釋放責任」教學框架操作化為 4 階段 AI persona(Guide → Collaborator → "
            "Peer → Launcher),可以讓專業工程師在 10 個 Claude Code 技能維度上同時取得 "
            "p<0.001 的顯著進步,而且效應最大的恰好是進階特性 —— 證實「AI 教 AI」是可行的"
            "結構化學習路徑。"
        ),
        limitations=(
            "27 人樣本來自單一客戶組織,泛化性受限",
            "參與者知道課程設計者為本文作者,可能有 demand bias",
            "效能評估為自陳量表,非客觀技能測驗",
            "缺乏長期(>3 個月)追蹤,無法評估技能保留",
        ),
        future_work=(
            "跨組織、跨地理的更大樣本驗證",
            "加入客觀技能測驗(完成真實任務的能力)",
            "把 cc-self-train 移植到 Cursor / Aider 等其他 agent 工具",
        ),
    ),
)


# ---------------------------------------------------------------------------
# 3. Haseeb 2025 — Context Engineering for Multi-Agent LLM Code Assistants
# ---------------------------------------------------------------------------
HASEEB = Paper(
    source="local", source_id="haseeb2025context",
    title="Context Engineering for Multi-Agent LLM Code Assistants Using Elicit, NotebookLM, ChatGPT, and Claude Code",
    authors=("Muhammad Haseeb",),
    year=2025, venue="arXiv 2025",
    abstract=(
        "本論文提出整合四個 AI 元件的 context engineering 工作流,以提升多檔案專案下 LLM "
        "程式碼助手的精度:(1) Intent Translator(GPT-5)把使用者請求改寫為結構化任務規格;"
        "(2) Elicit 語意文獻檢索注入領域知識;(3) NotebookLM 把文件 / 程式碼合成上下文;"
        "(4) Claude Code 多代理子系統做生成與驗證。在大型 Next.js 程式庫上,本系統能在「單一"
        "生成週期」內完成跨前後端的新功能(基線單代理多需多次嘗試)。並與 CodePlan、MASAI、"
        "HyperAgent 等近期框架做比較。"
    ),
    url="https://arxiv.org/abs/2508.08322",
    arxiv_id="2508.08322", pdf_url=None,
    summary=PaperSummary(
        language="zh-tw", model=MODEL_TAG, raw_text_chars=39_617,
        pain_points=(
            ("LLM 在多檔案專案表現嚴重落差", (
                "Context window 容不下整個 repo",
                "缺乏領域知識讓 LLM 對外部模式 / API 不熟",
                "跨檔案修改容易產生不一致"
            )),
            ("既有工作流多為單代理 + 單回合", (
                "ChatGPT 直接生成不修正",
                "Cursor / Copilot 對話式但缺乏結構化規劃",
                "失敗率高,需要反覆人類介入",
            )),
            ("Intent 模糊讓 LLM 自由發揮", (
                "使用者請求多為自然語言短句",
                "缺乏明確 acceptance criteria",
                "LLM 容易偏離真正需求",
            )),
            ("沒有自動把領域文獻 / 程式碼合成成上下文", (
                "新框架 / API 在 cutoff 之後 LLM 不熟悉",
                "手動貼 docs 既耗時又零散",
                "缺少「合成式」上下文輸入工具",
            )),
        ),
        research_question=(
            "在大型多檔案專案下,是否可以透過整合 intent 澄清、語意文獻檢索、文件合成、"
            "與多代理生成+驗證這四個 AI 元件的 context engineering 工作流,顯著提升 LLM "
            "程式碼助手的單回合成功率,同時保持對專案上下文的高度遵循?"
        ),
        contributions_detailed=(
            ("1. Intent Translator(GPT-5)",
             "把使用者自由文字請求改寫 / 詳述為結構化任務規格 —— 包含 acceptance criteria、"
             "邊界條件、改動範圍 —— 顯著降低 LLM 偏離需求的機率。"),
            ("2. Elicit 語意文獻檢索",
             "以使用者請求做語意檢索,把相關技術文獻 / 論文段落注入上下文,"
             "讓 LLM 學到 cutoff 之後的外部模式。"),
            ("3. NotebookLM 文件 / 程式碼合成",
             "把專案 README、API 文件、相關檔案結構合成成上下文摘要,"
             "解決 context window 容納全 repo 的問題。"),
            ("4. Claude Code 多代理生成 + 驗證子系統",
             "Claude Code 多代理子系統做程式碼生成與驗證,自動跑測試與 lint,"
             "比起單代理單回合大幅提升成功率。"),
        ),
        headline_metrics=(
            ("AI 元件數", "4", "Intent / 文獻 / 文件 / 多代理"),
            ("測試基準", "大型 Next.js codebase", "真實 production 規模"),
            ("單回合成功示例", "前端 + 後端整體跨層", "新功能單一生成週期內完成"),
            ("基線比較對象", "CodePlan / MASAI / HyperAgent", "近期 multi-agent 框架"),
            ("結果優勢", "更高 single-shot 成功率", "更佳專案上下文遵循度"),
        ),
        technique_table=(
            ("CodePlan", "Multi-agent + planning,缺乏 intent 結構化"),
            ("MASAI", "Multi-agent 拆解任務,但無外部文獻整合"),
            ("HyperAgent", "強化代理協調,但無 NotebookLM 式合成"),
            ("ChatGPT 單代理", "對話式,缺乏結構化規劃與驗證"),
            ("本論文工作流", "GPT-5 + Elicit + NotebookLM + Claude Code 多代理 4 件套"),
        ),
        method_sections=(
            ("Intent Translation 階段", (
                "用 GPT-5 改寫請求為結構化規格",
                "明確列出 acceptance criteria 與邊界條件",
                "降低 LLM 偏離真正需求的機率",
            )),
            ("Context 合成階段", (
                "Elicit 做語意文獻檢索注入領域知識",
                "NotebookLM 合成 README / API docs / 相關檔案",
                "兩者合在一起當作擴充 context 餵給生成代理",
            )),
            ("多代理生成 + 驗證階段", (
                "Claude Code 子代理規劃編輯 / 測試 / 驗證",
                "驗證階段跑 lint、test、build",
                "失敗時回饋給生成代理重做",
            )),
        ),
        evaluation_sections=(
            ("Next.js codebase 案例研究", (
                "成功在單一生成週期內加入跨前後端的新互動視覺化模組",
                "基線單代理需多次嘗試才能完成",
                "對既有專案風格遵循度高",
            )),
            ("與近期框架比較", (
                "比 CodePlan / MASAI / HyperAgent 在 single-shot 成功率上更佳",
                "比單代理 + 提示工程方法穩定",
                "驗證階段對 silent failure 的攔截率較高",
            )),
            ("質性結果", (
                "Intent Translation 階段最關鍵 —— 結構化規格幾乎是「prompt magic」",
                "Elicit 對新版套件 API 整合特別有用",
                "NotebookLM 文件合成解決 context overflow",
            )),
        ),
        system_flow=(
            ("使用者請求", "自由文字短句"),
            ("Intent Translator(GPT-5)", "改寫成結構化規格"),
            ("Elicit 文獻檢索", "注入領域知識"),
            ("NotebookLM 合成", "README / docs / repo 結構摘要"),
            ("Claude Code 多代理", "規劃 + 編輯 + 驗證"),
            ("單回合成功 / 失敗", "失敗則回饋給生成代理重做"),
        ),
        research_questions=(
            ("RQ1", "整合式 context engineering 工作流是否提升 single-shot 成功率?"),
            ("RQ2", "哪個 AI 元件對最終品質貢獻最大?"),
            ("RQ3", "與近期 multi-agent 框架比較表現如何?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="整合工作流是否提升單回合成功率?",
                table=(
                    ("方法", "single-shot 成功"),
                    ("ChatGPT 單代理", "需多次重試"),
                    ("Cursor / Copilot", "對話式但失敗常見"),
                    ("本論文工作流", "Next.js 跨前後端新模組一次成功"),
                ),
                analysis=(
                    "是 —— 案例研究展示明顯提升",
                    "對複雜跨檔案修改尤其顯著",
                    "驗證階段攔截 silent failure",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="哪個元件貢獻最大?",
                table=(
                    ("元件", "主要貢獻"),
                    ("Intent Translator", "降低偏離需求的機率,最關鍵"),
                    ("Elicit 文獻檢索", "注入新版 API 知識"),
                    ("NotebookLM 文件合成", "解決 context overflow"),
                    ("Claude Code 多代理", "規劃 + 驗證的執行層"),
                ),
                analysis=(
                    "Intent Translator 是「prompt magic」的核心",
                    "Elicit 在新版套件 API 整合場景特別有用",
                    "NotebookLM 是 context overflow 的工程解法",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="與近期 multi-agent 框架比較?",
                table=(
                    ("方法", "差異點"),
                    ("CodePlan", "缺乏 intent 結構化"),
                    ("MASAI", "缺乏外部文獻整合"),
                    ("HyperAgent", "缺乏 NotebookLM 式合成"),
                    ("本論文", "整合 4 件套,涵蓋意圖 / 知識 / 上下文 / 執行"),
                ),
                analysis=(
                    "其他框架聚焦「代理協調」,本論文補上「上下文工程」缺口",
                    "上下文品質決定生成品質,代理協調只是執行層",
                    "兩者互補而非互斥",
                ),
            ),
        ),
        core_observation=(
            "Multi-agent LLM 程式碼助手的精度瓶頸不在「代理協調」,而在「上下文品質」:"
            "整合 intent 澄清、語意文獻檢索、文件合成、與多代理生成+驗證的 4 件套 context "
            "engineering 工作流,可以讓大型多檔案專案的 single-shot 成功率顯著提升。"
        ),
        limitations=(
            "案例研究為單一 Next.js 專案,跨領域泛化未證實",
            "4 個 AI 元件成本疊加,實務部署 ROI 未量化",
            "Intent Translator 依賴 GPT-5,模型可得性會限制使用",
            "比較對象 CodePlan / MASAI / HyperAgent 為描述性比較,缺乏共同 benchmark",
        ),
        future_work=(
            "把 4 件套整合度更高,做成可重用 framework",
            "在統一 benchmark(如 SWE-bench)上量化 single-shot 改善幅度",
            "替換 Intent Translator 為 open-weight 模型以降低成本",
        ),
    ),
)


# ---------------------------------------------------------------------------
# 4. Santos et al. 2025 — Decoding the Configuration of Claude Code Projects
# ---------------------------------------------------------------------------
SANTOS = Paper(
    source="local", source_id="santos2025decoding",
    title="Decoding the Configuration of AI Coding Agents: Insights from Claude Code Projects",
    authors=("Hélio Victor F. Santos", "Vitor Costa", "João Eduardo Montandon", "Marco Tulio Valente"),
    year=2025, venue="arXiv 2025 (UFMG, Brazil)",
    abstract=(
        "本論文對 328 個真實 GitHub repo 的 CLAUDE.md 配置檔做實證分析,探究開發者如何"
        "為 AI coding agent 寫指令。3 個 RQ:(1) 配置檔涵蓋哪些關注點與實踐?(2) 程式碼"
        "範例與連結的使用情形?(3) 配置檔的常見組合模式?關鍵發現:架構(Architecture)"
        "出現在 72.6% 的檔案中,是最主導的關注點;開發指南、專案概述、測試、命令依序居後。"
        "最熱門組合是 Architecture + Dependencies + Project Overview(21.6%)。"
    ),
    url="https://arxiv.org/abs/2511.09268",
    arxiv_id="2511.09268", pdf_url=None,
    summary=PaperSummary(
        language="zh-tw", model=MODEL_TAG, raw_text_chars=27_694,
        pain_points=(
            ("Agentic 編碼工具效能高度依賴配置檔", (
                "Claude.md 等檔案定義架構限制與工具使用政策",
                "配置不當會讓 agent 行為脫軌",
                "但配置檔的內容結構鮮少被系統研究",
            )),
            ("缺乏「該寫什麼」的指引", (
                "Anthropic 官方文件描述基本格式",
                "缺乏跨專案的最佳實踐統計",
                "新使用者只能靠模仿"
            )),
            ("CLAUDE.md 跨專案差異極大", (
                "中位數 7 個 Level-2 區段",
                "最少 0,最多 213 個",
                "缺乏結構化指引導致變異巨大",
            )),
            ("程式碼範例 / 連結的使用未被量化", (
                "配置檔中該不該放程式碼範例?",
                "外部連結的使用率多高?",
                "缺乏實證來指引",
            )),
        ),
        research_question=(
            "真實 GitHub 專案的開發者如何寫 CLAUDE.md 配置檔來指導 Claude Code agent?"
            "他們最常寫哪些關注點 / 實踐?程式碼範例與連結的使用情形如何?"
            "有哪些常見的配置組合模式?"
        ),
        contributions_detailed=(
            ("1. 328 個真實 CLAUDE.md 配置檔的實證分析",
             "從 2025/8 的 4,724 個含 CLAUDE.md 的 repo 篩選出 100+ stars、活躍、real-world "
             "的 top-100 + 補充樣本,共 328 個 CLAUDE.md 檔案做系統分析。"),
            ("2. 關注點 / 實踐分類法",
             "從 2,492 個 Level-2 標題人工歸納出語意類別:Architecture(72.6%)、"
             "Development Guidelines(44.8%)、Project Overview(39%)、Testing(35.4%)、"
             "Commands(33.2%)等。"),
            ("3. 程式碼範例與連結量化",
             "對每個類別量化程式碼範例與外部連結出現率:Development Guidelines 含程式碼"
             "範例最多(17.68%),Architecture 含連結最多(1.83%)。"),
            ("4. FP-Max 配置組合模式",
             "用 FP-Max 演算法找出 maximal frequent itemsets;最熱門 pattern 是 "
             "Architecture + Dependencies + Project Overview(21.6%);Architecture 出現在 top-5 "
             "所有 pattern 中。"),
        ),
        headline_metrics=(
            ("分析的 CLAUDE.md 數量", "328", "篩選自 4,724 個 repo"),
            ("Architecture 出現率", "72.6%", "最主導的關注點"),
            ("Development Guidelines", "44.8%", "次之"),
            ("Project Overview", "39%", "第三"),
            ("Level-2 區段中位數", "7", "Q1=4, Q3=10, max=213"),
            ("最熱門 pattern 出現率", "21.6%", "Architecture+Dependencies+Project Overview"),
        ),
        technique_table=(
            ("Anthropic 官方文件", "描述基本格式與 best practice"),
            ("Watanabe et al. 2025", "分析 567 個 Claude Code PR"),
            ("Tufano et al. / Watanabe", "ChatGPT 等 chatbot 的使用研究"),
            ("Silva et al.", "ChatGPT 偵測 Java code smell"),
            ("Agentless 工作流", "三步驟以 LLM 解決 bug"),
            ("本論文", "328 個 CLAUDE.md 的關注點 / 模式實證"),
        ),
        method_sections=(
            ("Repo 蒐集與篩選", (
                "GitHub Search API 找含 CLAUDE.md 的 4,724 個 repo",
                "篩選 100+ stars、英文、real-world 應用",
                "保留 top-100 + 補充,最終 328 個",
            )),
            ("人工分類", (
                "解析 Level-2 區段標題,共 2,492 個",
                "一位作者初分,兩位審稿確認",
                "語意相似的標題歸為同類(如 Testing 各種變體)",
            )),
            ("FP-Max 模式探勘", (
                "把每個 CLAUDE.md 表示為一組類別 tuple",
                "用 MLxtend FP-Max,minimum support 0.15",
                "找 maximal frequent itemsets 作為配置 pattern",
            )),
        ),
        evaluation_sections=(
            ("最主導的關注點(RQ1)", (
                "Architecture:72.6%(主導)",
                "Development Guidelines:44.8%",
                "Project Overview:39%",
                "Testing:35.4%,Commands:33.2%",
            )),
            ("程式碼範例與連結(RQ2)", (
                "Code Examples:Development Guidelines 17.68% 最多",
                "Links:Architecture 1.83% 最多,但整體罕見",
                "UML/Mermaid 圖:僅 2 個檔案",
            )),
            ("常見配置 pattern(RQ3)", (
                "Top1:Architecture + Dependencies + Project Overview(21.6%)",
                "Top2:Architecture + General Guidelines(20.1%)",
                "Top3:Architecture + Development Guidelines + Project Overview(19.8%)",
                "Architecture 出現在所有 top-5 pattern 中",
            )),
            ("資料集多樣性", (
                "23 種程式語言,JS/TS 35 個、Python 16 個、Go 9 個最多",
                "Repo 中位數 950 stars、488 commits、58 個月歷史",
                "涵蓋 SDK / runtime / testing library 等",
            )),
        ),
        system_flow=(
            ("GitHub Search 找 CLAUDE.md", "4,724 個初始 repo"),
            ("popularity / language / real-world 篩選", "→ 328 個有效 repo"),
            ("Level-2 標題抽取", "2,492 個區段標題"),
            ("人工語意歸類", "建立關注點 / 實踐分類"),
            ("FP-Max 模式探勘", "minimum support 0.15"),
            ("RQ1–3 量化分析", "出現率 + 範例 + 模式"),
        ),
        research_questions=(
            ("RQ1", "配置檔中描述哪些關注點與實踐?"),
            ("RQ2", "程式碼範例與連結的使用情形?"),
            ("RQ3", "配置檔有哪些常見組合模式?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="配置檔最常描述哪些關注點?",
                table=(
                    ("類別", "出現率(%)"),
                    ("Architecture", "72.6"),
                    ("Development Guidelines", "44.8"),
                    ("Project Overview", "39.0"),
                    ("Testing", "35.4"),
                    ("Commands", "33.2"),
                    ("Dependencies", "30.8"),
                ),
                analysis=(
                    "Architecture 是壓倒性主導(72.6%)",
                    "「指定架構」是開發者寫 CLAUDE.md 的第一動機",
                    "Testing 與 Commands 約佔三分之一,顯示「可重複工作流」也是重點",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="程式碼範例與連結的使用?",
                table=(
                    ("類別", "Code Examples(%)", "Links(%)"),
                    ("Development Guidelines", "17.68", "0.61"),
                    ("Commands", "15.55", "0.30"),
                    ("Testing", "15.24", "0.00"),
                    ("Architecture", "10.98", "1.83"),
                ),
                analysis=(
                    "Development Guidelines 最常含程式碼範例(17.68%)",
                    "Architecture 最常含外部連結(1.83%),但整體罕見",
                    "UML/Mermaid 圖罕見(僅 2 個檔案)",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="最常見的配置 pattern?",
                table=(
                    ("Pattern", "出現率(%)"),
                    ("Architecture + Dependencies + Project Overview", "21.6"),
                    ("Architecture + General Guidelines", "20.1"),
                    ("Architecture + Development Guidelines + Project Overview", "19.8"),
                    ("Architecture + Development Guidelines + Testing", "18.9"),
                    ("Architecture + Integration", "17.7"),
                ),
                analysis=(
                    "Architecture 是所有 top-5 pattern 的核心",
                    "Top-1 是 Architecture + Dependencies + Project Overview(21.6%)",
                    "代表「告訴 agent 整體架構與依賴」是最廣為接受的配置模板",
                ),
            ),
        ),
        core_observation=(
            "真實 GitHub 專案的開發者在寫 CLAUDE.md 時,壓倒性地以「告訴 agent 整體架構」"
            "為核心(72.6%),其次是 development guidelines 與 project overview。最熱門的"
            "配置 pattern 是 Architecture + Dependencies + Project Overview(21.6%),"
            "Architecture 出現在所有 top-5 pattern 中。"
        ),
        limitations=(
            "標題分類由一位作者主導,雖兩位審稿確認仍有主觀性",
            "AI agent 領域快速演化,結果可能很快過時",
            "FP-Max minimum support 0.15 為經驗值,未做敏感度分析",
            "未跨足 AGENTS.md / .cursorrules 等其他 agent 配置檔",
        ),
        future_work=(
            "把分析延伸到 PR 對 CLAUDE.md 的演進歷史",
            "比較 CLAUDE.md 與 AGENTS.md / .cursorrules 等其他 agent 配置檔的設計差異",
            "建立「最佳實踐 CLAUDE.md 範本」與 schema 標準",
        ),
    ),
)


ALL_PAPERS = (LIU_DIVE, NABOULSI, HASEEB, SANTOS)


def main() -> None:
    out_dir = ROOT / "exports" / _RUN_DIR_NAME
    out_dir.mkdir(parents=True, exist_ok=True)
    for paper in ALL_PAPERS:
        collection = PaperCollection(
            query=Query(
                keywords="Claude Code 程式碼審查",
                sources=("local",),
                max_results=1,
            ),
            papers=(paper,),
        )
        options = ExportOptions(
            formats=("pptx",),
            out_dir=str(out_dir),
            filename_stem=f"{paper.bibtex_key()}-zh-tw",
            include_abstract=True,
            language="zh-tw",
        )
        written = export_collection(collection, options)
        for fmt, path in written.items():
            print(f"  - {paper.bibtex_key()} {fmt}: {path}")


if __name__ == "__main__":
    main()
