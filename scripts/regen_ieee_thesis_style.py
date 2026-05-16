"""Regenerate the IEEE paper as a thesis-style deck — backed by the real PDF.

Bullets are written to fit one wrapped line at 19pt on a 16:9 widescreen
slide (≤ ~45 Chinese characters). Numbers and table values come verbatim
from the paper's text (fetched via the project's PDF extractor).
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sources"))

os.environ.setdefault("AUTOPAPERTOPPT_ENABLE_IEEE_SCRAPING", "1")

from autopapertoppt.core.identifiers import parse_identifier  # noqa: E402
from autopapertoppt.core.models import (  # noqa: E402
    ExportOptions,
    Paper,
    PaperCollection,
    PaperSummary,
    Query,
    RqResult,
)
from autopapertoppt.core.pipeline import run_single_paper  # noqa: E402
from autopapertoppt.exporters import export_collection  # noqa: E402
from autopapertoppt.fetchers.http import shutdown_clients  # noqa: E402

SUMMARY = PaperSummary(
    language="zh-tw",
    model="claude-opus-4-7 (in-conversation, read 19-page PDF)",
    raw_text_chars=80_000,
    pain_points=(
        (
            "IoRT 進入高風險場景",
            (
                "市場 2030 預估 USD 78.83B 起 [1][2]",
                "覆蓋造船、精準農業、管線檢測",
                "失效或被攻破代價極高",
            ),
        ),
        (
            "AI 整合的新攻擊面",
            (
                "Adversarial attack 誤導推論",
                "GPS / sensor spoofing 造成定位錯誤",
                "MITM 攔截 Inference Engine 指令",
            ),
        ),
        (
            "RMF 1.0 對 IoRT 不足",
            (
                "只是治理 guide,缺技術細節",
                "缺 swarm 與多子系統的具體規範",
                "缺量化評估與 TinyML 稽核框架",
            ),
        ),
        (
            "LLM 改寫任務指派",
            (
                "傳統 NLP 難處理動態與模糊指令",
                "LLM 提供上下文理解與彈性適應",
                "需安全攔截層才能用在 mission-critical",
            ),
        ),
    ),
    research_question=(
        "如何用量化模型(τ·M·P/K)、子系統治理、LLM 任務翻譯三軸,"
        "把 NIST AI RMF 補成可在 IoRT 落地的框架?"
    ),
    contributions_detailed=(
        (
            "一、IoRT 跨領域脆弱性分析",
            "涵蓋造船、精準農業 swarm、管線檢測三大場景的攻擊面映射。",
        ),
        (
            "二、Sally 洪災 use case + LLM 指令翻譯",
            "Alpha/Beta/Gamma/Delta 四機 swarm 完成搜救;自然語言指令經 LLM Engine。",
        ),
        (
            "三、AI 弱點全面對應到 NIST AI RMF",
            "Adversarial / Sensor Spoofing / Rogue Central 三大威脅完整 mapping。",
        ),
        (
            "四、量化風險模型 Risk = τ·M·P/K",
            "搭配 NIST 800-53 control,提出 RMF 四項增強。",
        ),
    ),
    headline_metrics=(
        ("MITM 風險(TLS 1.3 後)", "729.0 → 8.1", "原始"),
        ("Sensor Spoofing(加冗餘 + anomaly)", "128.0 → 8.0", "原始"),
        ("Model Inversion(rate limit + DP)", "21.0 → 2.333", "原始"),
        ("RMF 提出增強面向", "4", "RMF 1.0 未涵蓋"),
    ),
    technique_table=(
        ("NIST AI RMF 1.0", "Govern/Map/Measure/Manage 治理骨幹"),
        ("MITRE ATLAS [47]", "對抗性戰術與技術分類"),
        ("NIST SP 800-30r1 [48]", "風險評估數學基礎"),
        ("FAIR Playbook [49]", "術語對照組(LEF / LM)"),
        ("NIST SP 800-53", "Control 基線(AES-256 等)"),
        ("LLM Engine + NLP", "自然語言指令翻譯成 AI 子任務"),
        ("Federated Learning [4][5]", "去中心化訓練,提高隱私"),
    ),
    literature_table=(
        ("研究", "治理", "IoRT", "量化", "LLM"),
        ("Ray [8] / Simoens [9]", "✗", "✓", "✗", "✗"),
        ("HuBotVerse [27]", "部分", "✓", "✗", "✗"),
        ("SMART-LLM [11]", "✗", "部分", "✗", "✓"),
        ("NIST AI RMF [7]", "✓", "✗", "✗", "✗"),
        ("Karim & Rawat [6]", "✓", "部分", "✗", "✗"),
        ("本研究", "✓", "✓", "✓", "✓"),
    ),
    system_flow=(
        "操作員以自然語言下達指令",
        "LLM Engine 翻譯成 AI 子任務序列",
        "DroneBot Alpha 熱影像 / 視覺搜尋",
        "座標經 Fusion Engine + Inference Engine",
        "SwarmBot Gamma 地面靠近並評估",
        "isSafe ≠ OK 則觸發 attemptRescue()",
        "完整指令審計寫入中央管理 plane",
    ),
    method_sections=(
        (
            "量化風險模型(Equation 1)",
            (
                "Risk = τ · M · P / K",
                "τ ∈ [0, 1] = 脆弱性 × 可達攻擊面",
                "M ∈ [0, 10] 影響等級(NIST 800-30r1)",
                "P = α · t,正規化到 [0, 1]",
            ),
        ),
        (
            "IoRT 中央管理訓練模型",
            (
                "輸入:元件、能力、自然語言對應",
                "輸出:target 元件 + 指令 + 預期回應",
                "Fusion Engine + Inference Engine 雙引擎",
                "邊緣端先做插值補值與冗餘",
            ),
        ),
        (
            "三大關鍵威脅(Threat Model)",
            (
                "Adversarial Examples → 熱影像誤判",
                "Sensor Spoofing → GPS / 影像被竄改",
                "Rogue Central → MITM 攔截指令",
            ),
        ),
        (
            "Use Case:Sally 洪災搜救",
            (
                "玉米田淹水,Sally 失蹤",
                "swarm 四機:Alpha/Beta/Gamma/Delta",
                "DroneBots:熱影像 + GPS + IMU",
                "SwarmBots:履帶 + 障礙物清除",
            ),
        ),
    ),
    evaluation_sections=(
        (
            "量化風險評估(Table 5)",
            (
                "每個威脅給 τ/M/P/K 數值",
                "比較 Initial vs Improved Risk",
                "Figure 5 對數座標統一比較",
            ),
        ),
        (
            "邊界情況分析",
            (
                "K → 0+ 時 Risk → ∞(不可接受)",
                "P = 0 時 Risk = 0",
                "極端 τ=1、M=10 仍 Risk = 5.56",
            ),
        ),
        (
            "對照組:NIST vs FAIR(Table 3)",
            (
                "與 NIST 800-30r1 / FAIR 術語對齊",
                "P 改成 α × t,契合 IoRT",
                "保留與既有框架的可比性",
            ),
        ),
        (
            "Use case 端到端驗證",
            (
                "Sally 救援場景跑完整流程",
                "三項威脅實際代入數字檢驗",
                "對齊 NIST 800-53 control baseline",
            ),
        ),
    ),
    research_questions=(
        ("RQ1", "Risk = τ·M·P/K 是否能合理量化 IoRT 威脅?"),
        ("RQ2", "MITRE ATLAS 對 IoRT 脆弱性 mapping 完整嗎?"),
        ("RQ3", "套用 800-53 control 後 risk 下降多少?"),
        ("RQ4", "RMF 1.0 在 IoRT 場景還缺什麼?"),
    ),
    rq_results=(
        RqResult(
            rq_id="RQ1",
            question="Risk = τ·M·P/K 是否能合理量化?",
            table=(
                ("威脅", "τ", "M", "P", "K", "Risk"),
                ("Drone 未授權存取", "0.8", "9", "0.3", "0.9", "2.4"),
                ("Model Inversion(初始)", "0.6", "7", "0.5", "0.1", "21.0"),
                ("Model Inversion(改進)", "0.6", "7", "0.5", "0.9", "2.333"),
            ),
            analysis=(
                "模型能區分強控制 vs 弱控制",
                "邊界 K→0+ 行為合理(發散)",
                "符合 NIST 800-30r1 閾值定義",
            ),
        ),
        RqResult(
            rq_id="RQ2",
            question="MITRE ATLAS → IoRT mapping 是否完整?",
            table=(
                ("威脅", "ATLAS 類別", "RMF 階段"),
                ("Model Evasion [50]", "Adversarial ML", "MAP / MEA / MAN"),
                ("Model Injection [52]", "Tampering", "GOV / MAN"),
                ("Poisoning [53][54]", "Training-time", "MAP / MEA"),
                ("Hallucination [55]", "Inference-time", "MEA / MAN"),
            ),
            analysis=(
                "Table 2 對應 AI 攻擊面與 IoT 環境",
                "Table 4 列出 CIA 影響與緩解",
                "所有 ATLAS 類別都映射到 RMF",
            ),
        ),
        RqResult(
            rq_id="RQ3",
            question="800-53 control 後 risk 下降多少?",
            table=(
                ("威脅", "Initial", "Improved", "Control"),
                ("Man-in-the-Middle", "729.0", "8.1", "TLS 1.3"),
                ("Sensor Spoofing", "128.0", "8.0", "Anomaly + 冗餘"),
                ("Model Inversion", "21.0", "2.333", "Rate limit + DP"),
            ),
            analysis=(
                "MITM 與 Spoofing 改善幅度最大",
                "Hardware Tampering 改善較溫和",
                "Figure 5 對數座標佐證成本效益",
            ),
        ),
        RqResult(
            rq_id="RQ4",
            question="RMF 1.0 在 IoRT 還缺什麼?",
            table=(
                ("缺口", "本研究增強"),
                ("缺量化評估", "Bayesian + Monte Carlo"),
                ("缺多子系統治理", "swarm 通訊與行為框架"),
                ("缺資料治理細節", "training + LLM 資料規範"),
                ("缺稽核框架", "Component-level audit"),
            ),
            analysis=(
                "Section IX 的四項增強對應四個缺口",
                "與既有 NIST 標準相容",
                "未來可用 LLM 自動產合規建議",
            ),
        ),
    ),
    limitations=(
        "框架層級設計加單一 use case,缺大規模實測",
        "τ/M/P/K 由專家估計,可能有偏差",
        "LLM 翻譯層延遲與一致性未獨立 benchmark",
        "未涵蓋 swarm 放大時的計算負載",
    ),
    future_work=(
        "用 Bayesian + Monte Carlo 強化 risk 模型",
        "解決從機器人池選最適任的最佳化問題",
        "用 LLM 提供 IoRT 合規建議",
        "拓展到醫療、物流、能源等領域",
    ),
    core_observation=(
        "用 Risk = τ·M·P/K 把 AI 治理具象化為數字,"
        "再以四機 swarm 救援驗證 LLM 任務翻譯與完整 RMF mapping。"
    ),
    motivation=(
        "IoRT 在高風險場景快速擴張",
        "AI 整合引入 adversarial / spoofing / MITM",
        "NIST RMF 缺 IoRT 子系統 / 量化 / 稽核細節",
    ),
    contributions=(
        "提供 IoRT 跨領域脆弱性分析",
        "精準農業 swarm + LLM 任務翻譯 use case",
        "IoRT 弱點對應 NIST AI RMF + 四項增強",
        "Risk = τ·M·P/K 量化模型",
    ),
    method=(
        "NIST AI RMF 四階段治理骨幹",
        "Risk = τ·M·P/K 量化威脅與改進",
        "MITRE ATLAS 對齊 RMF 階段",
        "swarm 四機 + LLM Engine 端到端",
    ),
    results=(
        "MITM Risk:729.0 → 8.1(TLS 1.3)",
        "Sensor Spoofing:128.0 → 8.0",
        "Model Inversion:21.0 → 2.333",
    ),
    takeaways=(
        "量化 risk 模型是 AI 治理落地關鍵",
        "LLM 翻譯層 + 獨立安全控制可部署",
        "RMF 需 IoRT-specific 增強才完整",
    ),
)


async def main() -> int:
    identifier = parse_identifier(
        "https://ieeexplore.ieee.org/abstract/document/10965643"
    )
    try:
        collection = await run_single_paper(identifier)
    finally:
        await shutdown_clients()
    if not collection.papers:
        print("no paper fetched", file=sys.stderr)
        return 1
    raw = collection.papers[0]
    enriched = Paper(
        source=raw.source,
        source_id=raw.source_id,
        title=raw.title,
        authors=raw.authors,
        year=raw.year,
        venue=raw.venue,
        abstract=raw.abstract,
        url=raw.url,
        doi=raw.doi,
        arxiv_id=raw.arxiv_id,
        citation_count=raw.citation_count,
        pdf_url=raw.pdf_url,
        summary=SUMMARY,
    )
    new_coll = PaperCollection(
        query=Query(keywords=raw.title[:60], sources=("ieee",), max_results=1),
        papers=(enriched,),
    )
    options = ExportOptions(
        formats=("pptx", "bib"),
        out_dir=str(ROOT / "exports" / "ieee-thesis-style-v3"),
        filename_stem="securing-llm-iort",
        language="zh-tw",
    )
    written = export_collection(new_coll, options)
    for fmt, path in written.items():
        print(f"{fmt}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
