"""Regenerate Ling et al. 2026 (Agent Skills) as a Traditional Chinese deck.

LLM-as-agent flow — the summary is hand-translated from the 18-page PDF
into zh-tw, then handed to the exporter with ``language="zh-tw"``. No
Anthropic API key required.

PDF source: https://arxiv.org/abs/2602.08004
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

SUMMARY = PaperSummary(
    language="zh-tw",
    model="claude-opus-4-7 (LLM-as-agent, 讀完 18 頁 PDF)",
    raw_text_chars=85_406,
    pain_points=(
        (
            "技能生態快速膨脹",
            (
                "2026/2/5 從 skills.sh 蒐集到 40,285 筆技能",
                "20 天成長 18.5 倍,集中於少數爆量日",
                "OpenClaw GitHub stars 同步飆升,屬注意力驅動",
            ),
        ),
        (
            "重新指定行為很浪費",
            (
                "代理常重複處理檢索、寫程式、編輯等子任務",
                "缺抽象 → prompt 重複,小幅情境變動就脆裂",
                "共用流程的維護分散在多份副本之間",
            ),
        ),
        (
            "市集 metadata 不透明",
            (
                "標籤稀疏、不一致、多為樣板自動生成",
                "難以分辨「被發布」與「被安裝」的差距",
                "缺品質訊號與正規 (canonical) 技能",
            ),
        ),
        (
            "技能會觸發真實副作用",
            (
                "可執行流程會接觸敏感資料與外部服務",
                "涵蓋隱私讀取、寫入、shell 執行等高風險",
                "風險面比純 prompt 互動大上一個量級",
            ),
        ),
    ),
    research_question=(
        "在市集規模下,代理技能有哪些類型?使用者實際採用哪些?"
        "又帶來哪些安全風險?"
    ),
    contributions_detailed=(
        (
            "一、大規模語料 + 成長分析",
            "從 skills.sh 抓取 40,285 筆技能與安裝數,量化 18.5 倍爆量成長"
            "並與社群注意力訊號耦合。",
        ),
        (
            "二、長度與冗餘剖析",
            "重尾 token 長度分布(中位數 1,414),以名稱比對指出 46.3% "
            "為近重複的條目。",
        ),
        (
            "三、功能分類 + 供需落差",
            "六大類 / 二十子類分類由 Qwen2.5-32B-Instruct 完成,揭露軟體"
            "工程供給過剩、檢索與內容創作需求超載。",
        ),
        (
            "四、安全風險稽核 (L0-L3)",
            "最壞情境四級量表覆蓋每一筆技能,9% 落在 critical risk,"
            "其中軟體工程類別 L3 高達 14%。",
        ),
    ),
    headline_metrics=(
        ("語料規模", "40,285", "單一快照的技能總數"),
        ("成長倍率", "18.5x", "20 天內 (2,179 → 40,285)"),
        ("單日峰值", "+8,857", "2026/1/25 一天新增"),
        ("長度中位數", "1,414", "tokens (平均 1,895)"),
        ("名稱重複率", "46.3%", "近重複的條目占比"),
        ("L3 critical", "9%", "全部技能中的占比"),
    ),
    technique_table=(
        ("skills.sh 市集爬蟲", "40,285 筆技能 metadata 與安裝數來源"),
        ("tiktoken o200k_base", "計算 token 長度分布"),
        ("BAAI/bge-m3 embeddings", "近重複偵測 (附錄 B)"),
        ("t-SNE 降維", "技能嵌入的視覺化群聚"),
        ("Qwen2.5-32B-Instruct", "分類 + L0-L3 風險稽核"),
        ("GitHub GraphQL API", "OpenClaw star 歷史作注意力代理"),
    ),
    method_sections=(
        (
            "資料蒐集",
            (
                "爬 skills.sh:抓 name、repo、first_seen、安裝數",
                "每筆儲存為 SKILL.md + JSON metadata",
                "僅以聚合形式呈現,不揭露個別作者",
            ),
        ),
        (
            "長度與冗餘",
            (
                "用 tiktoken o200k_base 標記 SKILL.md",
                "名稱比對:小寫去特殊字元後精確比對",
                "語義比對:bge-m3 最近鄰 + t-SNE (附錄)",
            ),
        ),
        (
            "功能分類",
            (
                "六大類 × 二十子類分類學 (表 1)",
                "Qwen2.5-32B-Instruct 為每筆指派一個子類",
                "嚴格 JSON 輸出,確保可大規模解析",
            ),
        ),
        (
            "風險稽核 (L0-L3)",
            (
                "最壞情境解讀規範 (附錄 E)",
                "L0 安全 / L1 隱私 / L2 中度 / L3 critical",
                "同樣 JSON 契約,支援整體統計聚合",
            ),
        ),
    ),
    evaluation_sections=(
        (
            "成長訊號",
            (
                "累積技能數 vs. OpenClaw 累積 GitHub stars",
                "找出單日與單週發布尖峰",
                "交叉驗證兩條曲線的注意力耦合",
            ),
        ),
        (
            "長度與冗餘",
            (
                "token-count 分布並列分位數明細",
                "以正規化名稱統計重複頻次 (n 次)",
                "列出名稱重複次數最高的 30 個技能",
            ),
        ),
        (
            "供給 vs. 需求",
            (
                "去重後的供給 vs. 平均安裝數",
                "繪製六大類與二十子類的對應圖",
                "凸顯需求過剩與供給過剩的落差",
            ),
        ),
        (
            "風險分布",
            (
                "全 40,285 筆技能的 L0-L3 比例",
                "分類別細分,軟體工程 L3 佔 14%",
                "以詞雲呈現各風險等級的關鍵字",
            ),
        ),
    ),
    system_flow=(
        "爬 skills.sh 市集 → 40,285 筆記錄",
        "Tokenize + 長度分布分析",
        "名稱比對 + 語義近重複偵測",
        "LLM 分類進 6 × 20 分類學",
        "比對去重後供給與平均安裝數 (需求)",
        "LLM 風險稽核為每筆指派 L0-L3",
        "彙整成長訊號 + GitHub star 注意力代理",
    ),
    research_questions=(
        ("RQ1", "技能生態的成長速度與爆量程度為何?"),
        ("RQ2", "已發布技能的長度與冗餘呈現什麼樣貌?"),
        ("RQ3", "供給與採用在各功能類別上分布如何?"),
        ("RQ4", "已發布技能的安全風險廣度與嚴重度為何?"),
    ),
    rq_results=(
        RqResult(
            rq_id="RQ1",
            question="市集的成長速度與爆量程度",
            table=(
                ("區間", "技能數"),
                ("2026/1/16", "2,179"),
                ("2026/2/5", "40,285"),
                ("20 天淨增", "+38,106"),
                ("單日峰值 (1/25)", "+8,857"),
                ("1/25 那週貢獻", "佔語料 47.8%"),
            ),
            analysis=(
                "20 天 18.5 倍成長,平均每日乘冪 15.7%",
                "23.2% 的新技能集中在單一日落地",
                "OpenClaw GitHub stars 在 1/26 達 25,432 高峰",
            ),
        ),
        RqResult(
            rq_id="RQ2",
            question="技能長度分布與條目重複",
            table=(
                ("統計量", "數值"),
                ("中位數長度", "1,414 tokens"),
                ("平均長度", "1,895 tokens"),
                ("90 百分位", "3,935 tokens"),
                ("最大值", "116,239 tokens"),
                ("獨特 vs. 重複名稱", "53.7% / 46.3%"),
            ),
            analysis=(
                "典型技能可順利放入 prompt budget",
                "前 1% 超過 9,253 tokens — 需要選擇性載入",
                "成對重複 (2×) 最常見,佔語料 18.7%",
            ),
        ),
        RqResult(
            rq_id="RQ3",
            question="各功能類別的供給 vs. 需求落差",
            table=(
                ("類別", "供給占比", "平均安裝數"),
                ("軟體工程", "54.7%", "~135 (供給過剩)"),
                ("資訊檢索", "4.8%", "463 (需求過剩)"),
                ("內容創作", "12.1%", "Audio/Video 266, Image 214"),
                ("生產力工具", "11.2%", "~140"),
                ("資料 & 分析", "10.6%", "~115"),
            ),
            analysis=(
                "Infrastructure 子類佔 24.0% — DevOps / 設定型供給氾濫",
                "Web Search 平均安裝 1,268,但供給僅 1.4%",
                "軟體工程技能彼此高度替代,瓜分有限需求",
            ),
        ),
        RqResult(
            rq_id="RQ4",
            question="安全風險在語料中的分布",
            table=(
                ("風險等級", "占比", "典型樣態"),
                ("L0 安全", "54%", "草稿、媒體輸出"),
                ("L1 隱私", "5%", "讀取私人脈絡"),
                ("L2 中度", "30%", "寫入、寄送、編輯"),
                ("L3 critical", "9%", "Shell、sudo、credentials"),
                ("軟體工程 L3 占比", "14%", "所有類別中最高"),
            ),
            analysis=(
                "接近 40% 的技能能存取敏感脈絡或執行寫入",
                "內容創作 L0 達 75%;生產力工具被 L2 主導",
                "風險集中在連接外部系統的橋接型技能",
            ),
        ),
    ),
    core_observation=(
        "代理技能正在成為 LLM 代理的新基礎建設層 —— 20 天 18.5 倍的爆量"
        "成長卻分布不均:軟體工程吃下供給、近半條目為意圖層重複,且約有"
        "兩成技能能觸發狀態改變或系統級動作。下一步重點應落在品質訊號、"
        "正規技能與最小權限沙盒。"
    ),
    limitations=(
        "資料源於 2026/2/5 的單一市集 (skills.sh) 單一快照",
        "採用度以公開安裝數為代理,並非實際執行驗證",
        "企業內部或自建代理的私有使用未納入觀測",
        "風險標籤倚賴 Qwen2.5 最壞情境推論,而非運行期實測",
    ),
    future_work=(
        "結合語義去重與品質訊號,推出每個意圖的正規技能",
        "對長技能做選擇性 / 模組化載入,控制 prompt 預算",
        "以需求訊號驅動的開發工具與獎勵,弭平供需落差",
        "對 L2 / L3 技能建立標準沙盒與最小權限執行協定",
    ),
)

PAPER = Paper(
    source="arxiv",
    source_id="2602.08004v1",
    title=(
        "Agent Skills: A Data-Driven Analysis of Claude Skills for "
        "Extending Large Language Model Functionality"
    ),
    authors=("George Ling", "Shanshan Zhong", "Richard Huang"),
    year=2026,
    venue="arXiv preprint",
    abstract=(
        "Agent skills extend large language model (LLM) agents with reusable, "
        "program-like modules that define triggering conditions, procedural "
        "logic, and tool interactions. As these skills proliferate in public "
        "marketplaces, it is unclear what types are available, how users "
        "adopt them, and what risks they pose."
    ),
    url="https://arxiv.org/abs/2602.08004",
    arxiv_id="2602.08004",
    pdf_url="https://arxiv.org/pdf/2602.08004",
    summary=SUMMARY,
)


def main() -> None:
    collection = PaperCollection(
        query=Query(
            keywords="agent skills 市集分析",
            sources=("arxiv",),
            max_results=1,
        ),
        papers=(PAPER,),
    )
    out_dir = ROOT / "exports" / "single-paper"
    out_dir.mkdir(parents=True, exist_ok=True)
    options = ExportOptions(
        formats=("pptx",),
        out_dir=str(out_dir),
        # Canonical zh-tw filename — distinct from the en deck (different
        # content) but no -rich suffix; this IS the deliverable for the
        # Traditional Chinese audience.
        filename_stem=f"{PAPER.bibtex_key()}-zh-tw",
        include_abstract=True,
        language="zh-tw",
    )
    written = export_collection(collection, options)
    for fmt, path in written.items():
        print(f"  - {fmt}: {path}")


if __name__ == "__main__":
    main()
