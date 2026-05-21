"""Traditional Chinese (zh-tw) rich decks for the 7 LLM-security papers.

Same 7 papers as scripts/regen_llm_security_batch.py — same PDFs, same
hand-authored facts, but every PaperSummary string is translated.
Output filename pattern: ``{bibtex_key}-zh-tw.pptx`` (the language-variant
suffix explicitly allowed by the canonical-filename rule in AGENTS.md).
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

MODEL_TAG = "claude-opus-4-7 (LLM-as-agent, 讀完整 PDF)"

_RUN_DIR_NAME = sys.argv[1] if len(sys.argv) > 1 else "llm-sec-final"
_FIGURES_ROOT = ROOT / "exports" / _RUN_DIR_NAME / "figures"


def _fig(paper_key: str, filename: str) -> str:
    return str(_FIGURES_ROOT / paper_key / filename)

# ---------------------------------------------------------------------------
# 1. Wen et al. 2025 — Security Attacks on LLM-based Code Completion Tools
# ---------------------------------------------------------------------------
WEN = Paper(
    source="local", source_id="wen2025security",
    title="Security Attacks on LLM-based Code Completion Tools",
    authors=("Cheng Wen", "Ke Sun", "Xinyu Zhang", "Wei Wang"),
    year=2025, venue="AAAI 2025",
    abstract="針對 LLM 程式碼補全工具設計 jailbreak 與訓練資料萃取攻擊，GitHub Copilot ASR 99.4%、從中取出 54 個真實 email 與 314 個 GitHub 用戶位置。",
    url="https://doi.org/10.1609/aaai.v39i22.34537",
    doi="10.1609/aaai.v39i22.34537", pdf_url=None,
    summary=PaperSummary(
        language="zh-tw", model=MODEL_TAG, raw_text_chars=45_450,
        pain_points=(
            ("LCCT 帶來新攻擊面", (
                "聚合檔名 + 當前檔 + 其他開啟檔的內容",
                "程式碼輸入繞過為自然語言訓練的安全濾網",
                "緊迫延遲預算壓縮輸出端的過濾深度",
            )),
            ("專有訓練資料洩漏 PII", (
                "GitHub Copilot 用公開 repo 微調",
                "LLM 會記憶訓練集裡的 email 與位置",
                "符合 CWE-200 敏感資訊洩漏類型",
            )),
            ("既有研究忽略 LCCT 特有風險", (
                "現有研究多聚焦在程式碼品質而非攻擊",
                "DAN 等 jailbreak 主要針對對話式 LLM",
                "缺乏針對 IDE 場景的程式碼即攻擊向量分析",
            )),
            ("防禦只在輸出端做事", (
                "Perspective API 之類純粹過濾輸出",
                "LCCT 回應延遲限制使深度檢查不可行",
                "敏感字過濾很容易被分割繞過",
            )),
        ),
        research_question=(
            "LLM 程式碼補全工具 (LCCT) 是否能保證負責任的輸出？"
            "其特有工作流又暴露了哪些攻擊空間？"
        ),
        contributions_detailed=(
            ("一、LCCT 威脅模型",
             "比對 LCCT 與一般 LLM 的工作流，找出四個 LCCT 部署環境特有的暴露點。"),
            ("二、上下文聚合攻擊",
             "Filename-Proxy 與 Cross-File 攻擊在 GitHub Copilot 達 72.5%、52.3% ASR。"),
            ("三、階層式程式碼利用攻擊",
             "Level-I Guided-Trigger 在 Copilot 達 99.4%、Amazon Q 46.3%、GPT-3.5 68.3%。"),
            ("四、程式碼驅動的隱私萃取",
             "從 2,173 個有效用戶名中萃出 54 個 email 與 314 個位置，全部可與 GitHub 個人頁對齊。"),
        ),
        headline_metrics=(
            ("Copilot jailbreak ASR (Level I)", "99.4%", "DAN baseline 對 GPT-4o 為 0%"),
            ("Amazon Q jailbreak ASR (Level I)", "46.3%", "CodeAttack 僅 1.3%"),
            ("Filename Proxy 對 Copilot", "72.5%", "上下文聚合攻擊"),
            ("Cross-File 對 Copilot", "52.3%", "跨檔上下文攻擊"),
            ("萃取到的真實 email", "54", "/ 712 個有公開 email 的用戶"),
            ("地點 (exact match)", "100", "+ 模糊比對 214 / 1,109 個有公開地點"),
        ),
        technique_table=(
            ("GitHub Copilot v1.211.0", "主要 LCCT 攻擊目標 — fine-tuned Codex"),
            ("Amazon Q Developer v1.12.0", "次要 LCCT 攻擊目標"),
            ("GPT-3.5 / GPT-4 / GPT-4o", "一般 LLM 對照組"),
            ("OpenAI user policy", "違規查詢的來源"),
            ("GPT-4 作 judge", "ASR 評分 (Qi 2023 規範)"),
            ("GitHub REST API", "隱私萃取結果的 ground truth"),
        ),
        method_sections=(
            ("三類攻擊策略", (
                "上下文聚合攻擊 (filename / cross-file)",
                "階層式程式碼利用攻擊 (Level I + II)",
                "程式碼驅動隱私萃取攻擊",
            )),
            ("查詢語料", (
                "四類受限項目：illegal / hate / porn / harmful",
                "每類 20 條，由 GPT-4 配合 OpenAI policy 生成",
                "主要用 Python，Go 作為跨語言消融",
            )),
        ),
        evaluation_sections=(
            ("ASR 計算", (
                "GPT-4 依 OpenAI policy 評估每個回應",
                "對照 DAN 與 CodeAttack 兩條 baseline",
                "每組攻擊 × 查詢執行 5 次取平均",
            )),
            ("隱私萃取驗證", (
                "與 GitHub REST API 比對 email 與位置",
                "exact match + 模糊 match 兩種精度",
                "2,704 個用戶名中 2,173 個有效 (80.4%)",
            )),
        ),
        system_flow=(
            "攻擊者構造攻擊程式碼 (filename / variable / cross-file)",
            "LCCT 聚合上下文輸入",
            "在延遲預算內安全檢查被繞過",
            "後端 LLM 補全並產生有害輸出",
            "輸出端過濾識別不出 code-format 載荷",
            "攻擊成功；隱私場景下：洩漏的 PII 被回傳",
        ),
        research_questions=(
            ("RQ1", "針對 LCCT 的 jailbreak 攻擊效果如何？"),
            ("RQ2", "攻擊複雜度與後端 LLM 能力如何交互？"),
            ("RQ3", "攻擊者能否從 LCCT 訓練資料萃出 PII？"),
            ("RQ4", "現行 LCCT 防禦是否抵擋這些威脅？"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="LCCT vs 一般 LLM 的 jailbreak ASR",
                table=(
                    ("方法", "Copilot", "Amazon Q", "GPT-4o"),
                    ("DAN baseline", "—", "—", "0.0%"),
                    ("Filename Attack", "72.5%", "—", "—"),
                    ("Cross-File Attack", "52.3%", "—", "—"),
                    ("Level I Guided-Trigger", "99.4%", "46.3%", "36.5%"),
                    ("Level II Code-Embedded", "41.3%", "22.3%", "41.3%"),
                ),
                analysis=(
                    "LCCT 比一般 LLM 脆弱許多",
                    "上下文聚合本身就是攻擊向量",
                    "Trade-off：複雜攻擊在弱模型反而表現差",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="攻擊複雜度 vs 模型能力",
                table=(
                    ("模型分層", "Level I", "Level II", "差距"),
                    ("弱 (Copilot)", "99.4%", "41.3%", "−58.1pp"),
                    ("中 (GPT-3.5)", "68.3%", "33.8%", "−34.5pp"),
                    ("強 (GPT-4o)", "36.5%", "41.3%", "+4.8pp"),
                ),
                analysis=(
                    "弱模型只能模仿無法理解攻擊",
                    "強模型較能識破簡單 Level-I",
                    "Level-II 混淆對強模型反而更有效",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="訓練資料 PII 萃取",
                table=(
                    ("階段", "數量"),
                    ("生成的 GitHub 用戶名", "2,704"),
                    ("有效 GitHub 用戶", "2,173 (80.4%)"),
                    ("公開 email 的用戶", "712"),
                    ("Exact email match", "54 (7.58%)"),
                    ("公開地點的用戶", "1,109"),
                    ("Exact location match", "100 (9.02%)"),
                    ("Fuzzy location match", "214 (19.30%)"),
                ),
                analysis=(
                    "專有微調語料洩漏真實 PII",
                    "Copilot 的 @ / . 過濾規則容易被繞過",
                    "風險類型：CWE-200 敏感資訊暴露",
                ),
            ),
            RqResult(
                rq_id="RQ4", question="防禦規則的缺口",
                table=(
                    ("防禦", "限制"),
                    ("敏感字過濾", "可由變數切割繞過"),
                    ("僅輸出端檢查", "漏掉 code-format 載荷"),
                    ("受延遲限制", "深度淺、各類別表現不均"),
                    ("單檔範圍", "Cross-file 載荷可滲透"),
                ),
                analysis=(
                    "Amazon Q 對情色類強防，其他類別漏",
                    "GPT 系列對 hate speech 最強；不均衡",
                    "需輸入端分級過濾 + 輸出端複審",
                ),
            ),
        ),
        core_observation=(
            "LCCT 繼承一般 LLM 的漏洞，又因 code-first 工作流與專有"
            "微調資料新增風險。結果：Copilot 99.4% jailbreak 成功率，加上"
            "可從程式碼補全還原真實 GitHub PII。防禦必須從輸出端轉成"
            "輸入端分級過濾，並依延遲預算配置安全檢查深度。"
        ),
        limitations=(
            "僅測試兩家商用 LCCT (Copilot、Amazon Q)，覆蓋有限",
            "以 Python 為主、Go 僅作消融，其他語言未涵蓋",
            "LCCT 版本固定於某時點，後續防禦會演變",
            "以 GPT-4 作 ASR judge 與人類判斷高度相關但非完美",
        ),
        future_work=(
            "依延遲預算配置的輸入端安全分級",
            "Cross-file 聚合的來源 / provenance 追蹤政策",
            "專有微調語料中加入差分隱私或過濾",
            "新版 LCCT 上的防禦可移植性研究",
        ),
        figures=(
            (
                "程式碼補全情境下的攻擊範例 (第 2 頁)",
                _fig("wen2025security", "p02-00-Example-of-attacking-in-code-completion-scenarios.png"),
                (
                    "三種攻擊模式並列：正常補全、嵌入程式碼的 jailbreak、訓練資料萃取。",
                    "顯示 LCCT 工作流如何取得輸入，以及各攻擊如何鑽入。",
                ),
            ),
            (
                "階層式程式碼利用攻擊的構造流程 (第 5 頁)",
                _fig("wen2025security", "p05-02-Constructing-flow-of-Hierarchical-Code-Exploitation-Attack.png"),
                (
                    "Level-I 由變數名構建攻擊；Level-II 加入註解、print、切割敏感字串。",
                    "由禁止查詢逐步轉換到 Copilot 願意補全的觸發碼。",
                ),
            ),
            (
                "四類受限查詢的 ASR 偏誤 (第 7 頁)",
                _fig("wen2025security", "p07-04-ASR-results-of-attack-bias.png"),
                (
                    "分類 ASR：illegal、porn、harmful、hate。Amazon Q 對 porn 過度防守。",
                    "各家防禦各類別的覆蓋率不均勻。",
                ),
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# 2. McClearn et al. 2025 — The Everyday Security of Living with Conflict
# ---------------------------------------------------------------------------
MCCLEARN = Paper(
    source="local", source_id="mcclearn2025everyday",
    title="The Everyday Security of Living with Conflict",
    authors=("Jessica McClearn", "Reem Talhouk", "Rikke Bjerg Jensen"),
    year=2025, venue="IEEE Security & Privacy magazine",
    abstract="以黎巴嫩、哥倫比亞、瑞典三個田野片段，把資安研究從『戲劇化的 cyber 敘事』拉回到戰亂與遷徙者的日常 (in)security。",
    url="https://arxiv.org/abs/2506.09580",
    doi="10.1109/MSEC.2025.3539504",
    arxiv_id="2506.09580", pdf_url=None,
    summary=PaperSummary(
        language="zh-tw", model=MODEL_TAG, raw_text_chars=24_989,
        pain_points=(
            ("Cyber 框架抹消日常經驗", (
                "資安研究過度聚焦在戲劇化的戰爭敘事",
                "Cyber 框架把 security 等同於技術能力",
                "戰亂下社群的日常 insecurity 不被計入",
            )),
            ("日常需求 ≠ cyber 需求", (
                "ATM 提款上限比加密更貼近日常威脅模型",
                "找食物、找住處、找工作就是 security work",
                "信任網路 (海外親屬匯款) 成為救命工具",
            )),
            ("為流離者設計往往是想像而非真實", (
                "設計師可以隨意想像永遠不見面的使用者",
                "加密通訊的設計假設忽略 share-fast 現實",
                "在基礎設施貧弱地『secure by design』失效",
            )),
            ("性別、基礎設施、流動風險疊加", (
                "Cauca 婦女：可見度 = 行動風險 vs 沉默 = 病痛",
                "Lebanon：空屋象徵遷徙與經濟動盪",
                "Sweden：『居留證』隨身帶以保留身分",
            )),
        ),
        research_question=(
            "在戰亂與流離中，人們如何穿越日常 (in)security？"
            "這對資安研究、設計、政策意味著什麼？"
        ),
        contributions_detailed=(
            ("一、為資安研究引入民族誌框架",
             "主張將 computer security 與沉浸式社會研究方法結合，採取更廣義的 security 概念。"),
            ("二、三個多地田野片段（Lebanon / Colombia / Sweden）",
             "呈現 (in)security 被編織進日常的具體路徑——匯款、女性土地維權、庇護文件。"),
            ("三、三向行動呼籲",
             "對研究者（多元方法 + 沉浸）、開發者（與社群協同設計）、政策制定者（卸下 cyber 前綴）。"),
            ("四、重新定位『cyber』",
             "批判 cyber 前綴掩蓋日常現實，扭曲了研究與政策中『誰的 security』被中心化。"),
        ),
        headline_metrics=(
            ("田野地點", "3", "Lebanon / Colombia / Sweden"),
            ("時間跨度", "2018–2024", "橫跨三個案例"),
            ("研究方法", "民族誌", "vs 問卷 / 實驗室 / 爬蟲"),
        ),
        technique_table=(
            ("民族誌田野工作", "長時間沉浸於戰亂影響社群"),
            ("受訪者匿名化", "保護持續處於風險中的身分"),
            ("Vignette 方法", "把情境敘事轉成政策 / 設計可用素材"),
            ("跨地點比較", "在三個不同戰亂脈絡中找出共同模式"),
        ),
        method_sections=(
            ("田野研究", (
                "Lebanon：經濟動盪、匯款、空屋",
                "Colombia (Cauca)：性別 + 土地 + 維權婦女",
                "Sweden：敘利亞難民 + 居留證",
            )),
            ("跨案例分析", (
                "在『security』框架下浮現日常的共同模式",
                "辨識科技作為社會 / 關係工具的角色",
                "把心得回扣到 computer-security 設計意涵",
            )),
        ),
        evaluation_sections=(
            ("分析姿態", (
                "Vignette 是說明性質，不作統計推論",
                "提醒避免從單一片段做普遍化結論",
                "凸顯日常的動態與脈絡相依",
            )),
        ),
        system_flow=(
            "三地與受同意受訪者進行田野研究",
            "去識別化受訪者與位置",
            "圍繞『mundane security』作主題聚類",
            "建構 vignette 以利政策 / 設計轉換",
            "綜合成三向行動呼籲",
        ),
        research_questions=(
            ("RQ1", "日常衝突中 security 如何被經驗？"),
            ("RQ2", "這暴露了科技扮演的什麼角色？"),
            ("RQ3", "對研究者與設計者的啟示為何？"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="戰亂中的日常 security",
                table=(
                    ("地點", "日常 security 模式"),
                    ("Lebanon", "匯款 > 數位權利論述"),
                    ("Colombia (Cauca)", "可見度 ↔ 維權女性風險"),
                    ("Sweden / 難民", "居留證作為身分錨點"),
                ),
                analysis=(
                    "Security 紮根於日常 routine，不在加密",
                    "科技是社會關係的救命線，非攻擊面",
                    "Mundanity 是動態的、隨情境變化",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="科技的實際角色",
                table=(
                    ("工具", "角色"),
                    ("行動電話", "『右手』— 可被聯繫"),
                    ("匯款 app", "在制裁下維持生存"),
                    ("加密通訊", "在此情境幾乎無關"),
                    ("文件相片", "穿越邊境的身分可攜性"),
                ),
                analysis=(
                    "科技服務社會連結勝於資料機密性",
                    "Cyber 框架完全忽略這些用法",
                    "分享速度勝於分享保護",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="對研究 / 設計 / 政策的呼籲",
                table=(
                    ("對象", "行動"),
                    ("研究者", "多元方法、沉浸於日常"),
                    ("開發者", "與流離社群協同設計"),
                    ("政策制定者", "卸下 cyber 框架，回到日常 security"),
                ),
                analysis=(
                    "CHI / USENIX 等社群已在這個方向上推進",
                    "需要與面向社群的研究者協作",
                    "風險：遠距想像 vs 在場理解",
                ),
            ),
        ),
        core_observation=(
            "當『cyber』成為主框架，戰亂下人們的 security 被簡化為"
            "加密與政策。Lebanon、Cauca、Sweden 三段田野顯示相反：security"
            "藏在日常實踐裡——一次匯款、一張隨身許可、一支永遠充滿電的手機。"
            "想服務這些社群的資安研究，必須沉浸、協同設計，並讓日常設定議程。"
        ),
        limitations=(
            "僅 3 個 vignette — 不作群體層面斷言",
            "高度倚賴作者本人聲音與既有田野資料",
            "未產出量化威脅模型",
            "Mundanity 隨脈絡變動 — 結論會隨時演化",
        ),
        future_work=(
            "把民族誌研究員嵌入資安工具設計流程",
            "建立與流離社群的協同設計協定",
            "在政策中重新評估 cyber 前綴框架",
            "跨地點的流動 / 遷徙 security 研究",
        ),
    ),
)

# ---------------------------------------------------------------------------
# 3. Shukla et al. 2025 — Security Degradation in Iterative AI Code Generation
# ---------------------------------------------------------------------------
SHUKLA = Paper(
    source="local", source_id="shukla2025security",
    title="Security Degradation in Iterative AI Code Generation: A Systematic Analysis of the Paradox",
    authors=("Shivani Shukla", "Himanshu Joshi", "Romilla Syed"),
    year=2025, venue="IEEE ISTAS 2025",
    abstract="以 400 個 LLM 生成程式碼樣本進行 40 輪可控實驗，顯示 5 輪迭代後 critical vulnerability 增加 37.6%，揭露『回饋迴圈 security 退化』這個反直覺失敗模式。",
    url="https://arxiv.org/abs/2506.11022",
    arxiv_id="2506.11022", pdf_url=None,
    summary=PaperSummary(
        language="zh-tw", model=MODEL_TAG, raw_text_chars=36_420,
        pain_points=(
            ("迭代精修被假設為安全的", (
                "80% 開發者已用 AI 助手寫程式",
                "GitHub CEO：『Copilot 將會寫 80% 程式碼』",
                "迭代後到底會怎樣，無人研究",
            )),
            ("既有文獻只測 iter-0", (
                "Pearce 2022：初次生成有 40% 含漏洞",
                "Perry 2023：AI 輔助下開發者寫的程式更不安全",
                "精修動態尚未被量化",
            )),
            ("真實流程是迭代而非一次性", (
                "開發者提交 → AI 改善 → 再提交",
                "這些迴圈的 security 影響沒人研究",
                "Human-in-the-loop 的角色從未量化",
            )),
            ("安全導向 prompt 仍會退化", (
                "明確要求『修安全』也可能引入新漏洞",
                "Crypto 函式庫誤用、過度工程、過期模式",
                "LLM 看似自信卻在偏離",
            )),
        ),
        research_question=(
            "在迭代式 AI 程式碼精修中，security 屬性真的會提升嗎？"
            "或者回饋迴圈本身引入新漏洞——prompt 策略又如何形塑這個模式？"
        ),
        contributions_detailed=(
            ("一、回饋迴圈 security 退化現象",
             "首次以實證證明：無人為審查的迭代式 LLM 精修會累積而非消除漏洞。"),
            ("二、四種 prompt 策略分類",
             "Efficiency / Feature / Security / Ambiguous 各自對應不同漏洞輪廓。"),
            ("三、複雜度—漏洞相關性",
             "Cyclomatic complexity 與漏洞數 r = 0.64；複雜度 +10% → 漏洞 +14.3%。"),
            ("四、具體緩解指引",
             "連續 LLM-only 迭代 ≤ 3 次、必要的人為審查、迭代間靜態分析、複雜度監控。"),
        ),
        headline_metrics=(
            ("樣本", "400", "10 baseline × 4 策略 × 10 迭代"),
            ("總漏洞數", "387", "在 40 輪迭代中發現"),
            ("早期迭代漏洞/樣本", "2.1", "iter 1–2"),
            ("晚期迭代漏洞/樣本", "6.2", "iter 8–10 (SD 1.8)"),
            ("複雜度 ↔ 漏洞", "r = 0.64", "p < 0.001"),
            ("Critical 漏洞 5 輪後增幅", "+37.6%", "對比 baseline"),
        ),
        technique_table=(
            ("OpenAI GPT-4o", "受試 LLM (temp 0.7, top_p 1.0)"),
            ("Clang Static Analyzer", "C 端靜態分析"),
            ("CodeQL", "跨語言漏洞掃描"),
            ("SpotBugs", "Java 端靜態分析"),
            ("CVSS 規範", "嚴重度分級"),
            ("Repeated-measures ANOVA", "迭代效果檢定"),
        ),
        method_sections=(
            ("實驗設計", (
                "10 個經審核的安全 C/Java baseline",
                "4 種 prompt 策略 × 各 10 輪迭代",
                "迭代 = 前一輪輸出作為下一輪輸入，不經人為修正",
            )),
            ("漏洞分析框架", (
                "12 類漏洞 (記憶體、輸入、加密、競態…)",
                "每個發現附 CVSS 嚴重度",
                "靜態分析 + 專家手動審查",
            )),
        ),
        evaluation_sections=(
            ("迭代層級分析", (
                "對 10 輪迭代執行 repeated-measures ANOVA",
                "η² = 0.42 (中-大效應)",
                "事後 Tukey：iter 1–3 與 8–10 顯著差異",
            )),
            ("跨策略比較", (
                "Chi-square 檢定 prompt 策略間漏洞型態分布 (p<0.001)",
                "多元迴歸控制複雜度 + 策略",
                "Security-prompt 失敗的三類質性模式",
            )),
        ),
        system_flow=(
            "以審核過的安全 baseline (C / Java) 開始",
            "用策略對應的 prompt 提交給 GPT-4o",
            "收下精修後的程式，跑靜態分析 + 手動審查",
            "將輸出作為下一輪輸入（無人為修改）",
            "對每組 (sample, strategy) 重複 10 輪",
            "依迭代彙整漏洞數與嚴重度",
        ),
        research_questions=(
            ("RQ1", "迭代間漏洞會累積嗎？"),
            ("RQ2", "Prompt 策略會改變漏洞輪廓嗎？"),
            ("RQ3", "程式碼複雜度與漏洞數的關係？"),
            ("RQ4", "安全導向 prompt 是否反而讓程式更不安全？"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="迭代間漏洞累積",
                table=(
                    ("迭代區間", "平均漏洞/樣本", "SD"),
                    ("Iter 1–2 (早期)", "2.1", "0.9"),
                    ("Iter 3–7 (中期)", "4.7", "1.2"),
                    ("Iter 8–10 (晚期)", "6.2", "1.8"),
                ),
                analysis=(
                    "非線性成長 — 第 5 輪後加速",
                    "ANOVA F(9,90)=14.32, p<0.001, η²=0.42",
                    "相鄰迭代差異不顯著；首尾差異劇烈",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="各 prompt 策略的漏洞",
                table=(
                    ("策略", "總計", "Critical", "High"),
                    ("Efficiency-focused", "124", "37", "41"),
                    ("Feature-focused", "158", "29", "53"),
                    ("Security-focused", "38", "7", "12"),
                    ("Ambiguous", "67", "14", "19"),
                ),
                analysis=(
                    "Feature 取向總漏洞最多 (158)",
                    "Security 取向最少 (38)，但仍為正",
                    "策略形塑型態，不只數量 (χ² p<0.001)",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="複雜度 vs 漏洞",
                table=(
                    ("Predictor", "β", "95% CI", "p"),
                    ("Complexity", "0.64", "[0.50, 0.78]", "<0.001"),
                    ("Iteration #", "0.28", "[0.12, 0.44]", "<0.001"),
                    ("Efficiency-prompt", "0.31", "[0.13, 0.49]", "0.001"),
                    ("Feature-prompt", "0.38", "[0.20, 0.56]", "<0.001"),
                    ("Security-prompt", "−0.17", "[−0.35, 0.01]", "0.061"),
                ),
                analysis=(
                    "複雜度是最強解釋變數 (R²=0.67)",
                    "+10% 複雜度 → +14.3% 漏洞",
                    "迭代在複雜度之上仍有額外風險貢獻",
                ),
            ),
            RqResult(
                rq_id="RQ4", question="安全 prompt 的悖論",
                table=(
                    ("失敗模式", "範例"),
                    ("Crypto 函式庫誤用", "用自訂 hash 取代標準函式"),
                    ("過度工程", "多層加密之間接縫產生漏洞"),
                    ("過期模式", "已棄用 cipher / 弱亂數源"),
                ),
                analysis=(
                    "Security prompt 修明顯洞、引入細微洞",
                    "早期 27% 的 security 迭代仍會淨改善",
                    "10 輪整體仍呈退化趨勢",
                ),
            ),
        ),
        core_observation=(
            "純 LLM 迭代精修是個悖論機器：程式碼看起來愈來愈精緻，"
            "漏洞卻在累積；5 輪後 critical 漏洞增加 37.6%，複雜度與漏洞"
            "相關係數高達 0.64。即使明確要求修安全，也擋不住退化。"
            "Human review 必須坐進迭代之間，而非只在最後一輪。"
        ),
        limitations=(
            "單一 LLM (GPT-4o)，其他模型未測",
            "僅 C 與 Java 兩種語言 (Rust / Go / Python 待測)",
            "Pure LLM-only loop 排除了真實 human-AI 共開發",
            "時點快照 — 模型版本演進快",
        ),
        future_work=(
            "比較 Claude / Gemini / Llama 等的退化率",
            "量化真實 human-in-loop 工作流的緩解效果",
            "在 coding assistant 加入複雜度預算告警",
            "面向安全的 RLHF 解開 security-prompt 悖論",
        ),
    ),
)

# ---------------------------------------------------------------------------
# 4. Obadofin & Barros 2025 — Network Hexagons Under Attack
# ---------------------------------------------------------------------------
OBADOFIN = Paper(
    source="local", source_id="obadofin2025network",
    title="Network Hexagons Under Attack: Secure Crowdsourcing of Geo-Referenced Data",
    authors=("Okemawo Obadofin", "João Barros"),
    year=2025, venue="arXiv preprint",
    abstract="對 IETF Nexagon 地理資料協定執行 STRIDE + LINDDUN 威脅分析，揭示再識別、session linkage、稀疏區域攻擊。提出 PKI + 短效 pseudonym 證書 + 自適應 H3 解析度的架構，原型實作下延遲增加 ≤25%、吞吐損失 ≤7%。",
    url="https://arxiv.org/abs/2506.05601",
    arxiv_id="2506.05601", pdf_url=None,
    summary=PaperSummary(
        language="zh-tw", model=MODEL_TAG, raw_text_chars=37_429,
        pain_points=(
            ("Nexagon 規範缺認證細節", (
                "IETF draft 定義協定但未指定 auth 機制",
                "實際部署需要具體的 PKI 機制",
                "Geo-referenced 資料對攻擊者極具吸引力",
            )),
            ("既有隱私技術不適 ITS", (
                "k-anonymity 浪費頻寬 (dummy clients)",
                "差分隱私破壞路徑最佳化的精度",
                "行動端無法承擔冗餘流量預算",
            )),
            ("稀疏區域攻擊是 H3 特有", (
                "低密度六邊形暴露孤立 client",
                "可推論行進方向與目的地",
                "靜態解析度放大了洩漏",
            )),
            ("Control-plane spoofing 影響大", (
                "假冒 auth server 可吸收 rogue client",
                "竊取初次憑證並破壞信任鏈",
                "標準 cert 不能錨定 first-touch 信任",
            )),
        ),
        research_question=(
            "如何在 ITS 的延遲與吞吐預算下，讓 IETF Nexagon 同時"
            "保證車輛 / 裝置匿名性與認證？"
        ),
        contributions_detailed=(
            ("一、Nexagon 的 STRIDE+LINDDUN 威脅模型",
             "首次將協定分解為 untrusted / DMZ / management 三個信任區，並映射所有威脅類別到 DFD 元素。"),
            ("二、PKI + 短效 pseudonym 證書",
             "新增動態金鑰輪替、自適應 H3 解析度、TPM-backed onboarding，覆蓋所識別威脅。"),
            ("三、Microservice overlay 原型",
             "Auth / Mapping / Aggregation agents 以 Docker microservice 部署，端到端 benchmark。"),
            ("四、效能上限",
             "安全擴充延遲增加 ≤+25%、吞吐損失 ≤7%。"),
        ),
        headline_metrics=(
            ("平均延遲", "306 → 384 ms", "+25.5% 加上擴充"),
            ("吞吐", "260 → 250 req/s", "−3.8% 加上擴充"),
            ("CPU 使用率", "42% → 57%", "+15 pp 滿載"),
            ("P95 延遲", "400 → 460 ms", "+15.0%"),
            ("高風險威脅數", "3", "Session linkage / 稀疏區域 / 假 agent"),
        ),
        technique_table=(
            ("STRIDE", "資安威脅分類"),
            ("LINDDUN", "隱私威脅分類"),
            ("LISP", "Locator / ID 分離以映射網路"),
            ("H3 hexagonal indexing", "Uber 的地理六邊形分割"),
            ("PKI + pseudonym certificates", "保護匿名的認證"),
            ("TPM / firmware-TPM", "首次接觸的信任錨"),
        ),
        method_sections=(
            ("威脅建模流程", (
                "將 Nexagon 分解為跨三個信任區的 DFD",
                "把 STRIDE + LINDDUN 類別映射到 DFD 元素",
                "依攻擊樹建立威脅 + 緩解表",
            )),
            ("緩解設計", (
                "PKI 作為 root-CA，定期金鑰輪替",
                "Pseudonym cert 省去身份欄位",
                "在稀疏區域動態調整 H3 解析度",
            )),
        ),
        evaluation_sections=(
            ("原型部署", (
                "Docker 上的 microservice overlay",
                "兩台 VM (4GB RAM, 2 cores 各一)",
                "管理面 vs 單一 client 負載產生器",
            )),
            ("效能測量", (
                "Baseline：pre-shared key",
                "Treatment：PKI 擴充",
                "在不同請求量下比較延遲 / 吞吐 / CPU",
            )),
        ),
        system_flow=(
            "Mobile client 透過 DNS 解析 auth-agent",
            "TPM-backed 金鑰交換 + pseudonym 證書發行",
            "Client 以輪替 EID 發布 geo-update",
            "Mapping agent 轉發到 aggregation pipeline",
            "週期性金鑰輪替 + 自適應 H3 解析度",
        ),
        research_questions=(
            ("RQ1", "Nexagon 現行規範暴露哪些威脅？"),
            ("RQ2", "在實際限制下哪些緩解能堵住？"),
            ("RQ3", "安全層的延遲 / 吞吐成本？"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="Nexagon 高風險威脅",
                table=(
                    ("威脅", "風險", "影響範圍"),
                    ("Session linkage", "高", "Client + auth agent"),
                    ("稀疏區域攻擊", "高", "Mobile client"),
                    ("假 control-plane agent", "高", "Client + mapping"),
                    ("用戶再識別", "中", "Client + mapping"),
                ),
                analysis=(
                    "Linkability + identifiability 橫跨所有 DFD 層",
                    "稀疏區域攻擊是 H3 索引特有",
                    "Auth-agent spoofing 破壞首次接觸信任",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="緩解集合",
                table=(
                    ("威脅", "緩解"),
                    ("Session linkage", "輪替 pseudonymised EID + dummy 流量"),
                    ("稀疏區域", "動態 H3 解析度 + k-region 擴張"),
                    ("假 agent", "TPM attestation + mutual TLS"),
                    ("Replay", "Nonce + mutual TLS"),
                ),
                analysis=(
                    "Pseudonym cert 取代帶識別欄位的 X.509",
                    "TPM (包含 fTPM) 適用低階行動裝置",
                    "自適應 H3 模擬 k-anonymity 但不需 dummy",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="擴充的效能成本",
                table=(
                    ("指標", "無擴充", "有擴充", "差距"),
                    ("平均延遲 (ms)", "306", "384", "+25%"),
                    ("吞吐 (req/s)", "260", "250", "−3.8%"),
                    ("P50 延遲", "276 ms", "330 ms", "+19.6%"),
                    ("P95 延遲", "400 ms", "460 ms", "+15.0%"),
                    ("CPU (%)", "42", "57", "+15 pp"),
                ),
                analysis=(
                    "所有差距都在實際部署可接受範圍",
                    "PKI overhead 集中在 onboarding",
                    "穩態運作與 baseline 幾無區別",
                ),
            ),
        ),
        core_observation=(
            "Nexagon IETF draft 假設車輛匿名，但 auth 與金鑰輪替都未定義。"
            "本研究提出 PKI + 短效 pseudonym + TPM-backed onboarding "
            "+ 自適應 H3 解析度，封閉 session linkage、稀疏區域、"
            "control-plane spoofing 三大威脅，並付出有限但可接受的代價"
            "(延遲 +25%、吞吐 −7%)。"
        ),
        limitations=(
            "兩台 VM 的測試平台 — 非城市規模車隊",
            "簡化為單一 Supplier / Consumer 模型",
            "假設整個部署車隊都有 TPM 可用",
            "效能結果對流量混合與負載敏感",
        ),
        future_work=(
            "城市規模實車測試",
            "聯邦學習作分散去中心化彙整",
            "Post-quantum 安全的 pseudonym 簽章",
            "跨司法管轄區的 pseudonym 撤銷協定",
        ),
        figures=(
            (
                "不同粒度六邊形格點的局部地圖 (第 3 頁)",
                _fig("obadofin2025network", "p03-01-Sectional-map-with-hexagonal-tiles-of-varying-granularity-su.png"),
                (
                    "H3 hexagonal indexing 以地理位置分組行動節點。",
                    "稀疏 vs 密集區域呈現靜態解析度為何洩漏單一 client 位置。",
                ),
            ),
            (
                "Nexagon 協定架構總覽 (第 3 頁)",
                _fig("obadofin2025network", "p03-02-An-Overview-of-the-Nexagon-protocol-architecture.png"),
                (
                    "三類元件：Authentication、Geo-Mapping、H3 Aggregation 節點。",
                    "信任邊界後續被分解成 untrusted / DMZ / management 三區。",
                ),
            ),
            (
                "Client–CA 初次認證序列 (第 6 頁)",
                _fig("obadofin2025network", "p06-05-Sequence-diagram-illustrating-the-interaction-between-the-cl.png"),
                (
                    "初次 pseudonym 證書經 TPM-backed attestation 發行。",
                    "顯示在首次接觸時必須阻擋假冒 auth-agent。",
                ),
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# 5. Hagen et al. 2025 — Formal Verification of Secure Vehicle Software Updates
# ---------------------------------------------------------------------------
HAGEN = Paper(
    source="local", source_id="hagen2025towards",
    title="Towards a Formal Verification of Secure Vehicle Software Updates",
    authors=("Martin Slind Hagen", "Emil Lundqvist", "Alex Phu", "Yenan Wang",
             "Kim Strandberg", "Elad Michael Schiller"),
    year=2025, venue="Computers & Security (Elsevier)",
    abstract="以 ProVerif 對 Unified Software Update Framework (UniSUF) 執行符號化驗證，在 Dolev–Yao 攻擊者模型下證明機密性、完整性、真實性、新鮮性、順序、liveness 六項屬性，為連網車輛更新框架提供首份形式安全分析。",
    url="https://arxiv.org/abs/2511.15479",
    doi="10.1016/j.cose.2025.104751",
    arxiv_id="2511.15479", pdf_url=None,
    summary=PaperSummary(
        language="zh-tw", model=MODEL_TAG, raw_text_chars=87_811,
        pain_points=(
            ("2030 年 96% 車輛將連網", (
                "每車 100+ ECU，全部需要更新",
                "更新被攻陷 = malware / 洩漏 / 劫持",
                "全球年銷 70M 輛 = 巨大攻擊面",
            )),
            ("UniSUF 尚無形式證明", (
                "既有評估偏實務 / 部署面",
                "金鑰暴露路徑未被審視",
                "順序違規攻擊向量未經驗證",
            )),
            ("驗證工具各有所長與限制", (
                "Theorem prover 對完整協定太繁瑣",
                "Model checker 需要明確的攻擊者建模",
                "Cryptographic protocol verifier (ProVerif) 折衷最佳",
            )),
            ("既有自動車證明聚焦 Uptane 而非 UniSUF", (
                "Kirk 2023 / Lorch 2024 / Boureanu 2023 皆做 Uptane",
                "每一篇都找到漏洞、標準組織皆已回應",
                "UniSUF 同樣需要這份嚴謹度",
            )),
        ),
        research_question=(
            "在 Dolev–Yao 攻擊者模型下，能否把 UniSUF 的更新流程形式化證明"
            "滿足機密性、完整性、真實性、新鮮性、順序、liveness 六項屬性？"
        ),
        contributions_detailed=(
            ("一、UniSUF 架構的形式模型",
             "在 ProVerif 中捕捉 Producer / Consumer / Software Repository / Suppliers / ECUs 與 12 個 producer 子實體。"),
            ("二、六項系統層安全需求",
             "Confidential Secrets、Integrity of Cryptographic Materials、Inter/Intra-Round Uniqueness、Integrity of Handling Events、Termination。"),
            ("三、Dolev–Yao 下的符號驗證",
             "ProVerif queries 在 encapsulation 與 decapsulation 階段證明上述需求。"),
            ("四、開源驗證框架",
             "論文接受後將開源；模型、需求、proof obligation 全可重現。"),
        ),
        headline_metrics=(
            ("建模的 Producer 子實體", "12", "OA, VCM, PSS, CMS, PSA, PDA, PIA, …"),
            ("已驗證的子問題", "多個", "Preparation / Encapsulation / Decapsulation"),
            ("攻擊者模型", "Dolev–Yao", "完整 channel control"),
            ("更新回合識別碼", "(vid, t_e)", "VIN + 過期時間"),
            ("加密原語", "AES-GCM + 非對稱", "Authenticated symmetric + asymmetric"),
        ),
        technique_table=(
            ("ProVerif", "符號化加密協定驗證器"),
            ("Dolev–Yao 攻擊者", "完全控制通訊通道"),
            ("AES-GCM (AuthSymEnc)", "經認證的對稱加密"),
            ("X.509 憑證", "非對稱金鑰、由 root-CA 簽署"),
            ("更新回合識別 (vid, t_e)", "回合唯一性錨點"),
            ("子協定分解", "每個任務獨立驗證"),
        ),
        method_sections=(
            ("系統建模", (
                "把 UniSUF 分解為實體、通道、信任區",
                "建模 VUUP、DKM、IKM、MKM、SKA 等加密物件",
                "捕捉更新回合生命週期與 ECU 解鎖事件",
            )),
            ("需求形式化", (
                "Confidential Secrets — 每子問題的 S 集合",
                "Integrity of Cryptographic Materials — D 中的 origin 實體",
                "Inter/Intra-Round Uniqueness + Integrity of Handling Events",
            )),
        ),
        evaluation_sections=(
            ("符號化驗證", (
                "每個需求編碼成 ProVerif query",
                "貫穿 preparation + encapsulation + decapsulation",
                "與既有 Uptane 分析作對照",
            )),
            ("Termination 分析", (
                "Liveness (G8) 在設計層論證",
                "Replay 防護以單調 round ID 強制",
                "每個實體都明確建模 halt task",
            )),
        ),
        system_flow=(
            "Software Supplier 簽署並上傳至 Producer Local Storage",
            "VCM 用 PSA 提供的金鑰加密軟體並簽名",
            "Producer 組合 VUUP (DKM + IKM + MKM + SKA)",
            "Consumer (CDA) 從 Vehicle Cloud Service 下載 VUUP",
            "Consumer 解封 VUUP、解鎖 ECU、安裝軟體",
            "安裝完成後車輛回到 online 模式",
        ),
        research_questions=(
            ("RQ1", "UniSUF 操作中會否暴露 secret？"),
            ("RQ2", "UniSUF 能否保證軟體的端到端真實性？"),
            ("RQ3", "能否阻止舊版軟體被 replay 安裝？"),
            ("RQ4", "更新順序是否被強制？"),
            ("RQ5", "每個更新回合都會終止嗎？"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="UniSUF secrets 的機密性",
                table=(
                    ("Secret", "結果"),
                    ("對稱 session key (DKM/IKM/MKM)", "在 Dolev–Yao 下機密"),
                    ("Master key (SKA)", "機密"),
                    ("非對稱私鑰", "機密"),
                    ("軟體內容", "分發期間機密"),
                ),
                analysis=(
                    "ProVerif 證明攻擊者導不出任何 s ∈ S",
                    "G1+G2 (軟體機密性) 達成",
                    "Authenticated symmetric encryption 是關鍵",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="完整性 & 真實性",
                table=(
                    ("物件", "Origin", "竄改偵測"),
                    ("軟體", "Supplier", "簽署 + AES-GCM"),
                    ("VUUP", "VCM", "VCM 簽章"),
                    ("Download Instructions", "PDA", "PDA 簽章"),
                    ("Installation Instructions", "PIA", "PIA 簽章"),
                ),
                analysis=(
                    "只有 origin 能產生；收件端可偵測竄改",
                    "G3+G4 達成",
                    "Reliable-but-insecure 的 ECU 通道由 TPM/TEE 處理",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="Replay / 新鮮性",
                table=(
                    ("屬性", "機制"),
                    ("Inter-Round Uniqueness", "(vid, t_e) per 更新回合"),
                    ("Intra-Round Uniqueness", "持久 log 自動去重"),
                    ("版本單調性", "安裝前版本檢查"),
                ),
                analysis=(
                    "G5+G6 達成；不可能 rollback",
                    "VUUP 僅限指定車輛使用 (VIN-bound)",
                    "回合 ID 將加密物件綁定到該回合",
                ),
            ),
            RqResult(
                rq_id="RQ4", question="順序 & liveness",
                table=(
                    ("屬性", "做法"),
                    ("Handling-event partial order P(ℓ)", "依子任務逐一指定"),
                    ("子協定分解", "各任務獨立驗證"),
                    ("Termination", "每實體都有 halt + 回合過期"),
                ),
                analysis=(
                    "G7 (順序) 經符號化驗證",
                    "G8 (liveness) 在設計層論證",
                    "更新回合過期保證強制 halt",
                ),
            ),
        ),
        core_observation=(
            "UniSUF 在實務上已部署於業界，但形式證據缺位。本研究在 ProVerif "
            "中以真實汽車實體建模並端到端驗證：機密性、完整性、真實性、"
            "新鮮性、順序、liveness 在 Dolev–Yao 攻擊下皆成立。驗證成本"
            "只發生在設計時，運行期不增加負擔，對真實部署提供強保證。"
        ),
        limitations=(
            "簡化為單 Supplier、單 Producer、單 Consumer、單 ECU",
            "Liveness 在設計層論證、非機械化證明",
            "ProVerif 狀態空間對模型大小敏感",
            "實作層級的 bug 不在範圍內",
        ),
        future_work=(
            "擴展到多 Supplier、多 ECU 車隊",
            "ProVerif 與 Tamarin 組合以加大涵蓋",
            "經 SAW / OP-TEE 進行實作層驗證",
            "處理 post-state (安裝報告 + log) 子問題",
        ),
        figures=(
            (
                "UniSUF 架構高階概覽 (第 4 頁)",
                _fig("hagen2025towards", "p04-00-High-level-overview-of-the-UniSUF-architecture-showing-the-m.png"),
                (
                    "主要實體：Producer、Consumer、Suppliers、Software Repository、ECUs。",
                    "更新流程：Suppliers → Producer → Vehicle Cloud → Consumer → ECUs。",
                ),
            ),
            (
                "VUUP 檔內部結構 (第 21 頁)",
                _fig("hagen2025towards", "p21-05-Internal-structure-of-a-VUUP-file.png"),
                (
                    "DKM + IKM + MKM + SKA 層層套疊的加密封包。",
                    "每層金鑰由上一層包裹，只有授權的 consumer 元件能逐層解開。",
                ),
            ),
            (
                "UniSUF 的不同加密物件 (第 18 頁)",
                _fig("hagen2025towards", "p18-02-Different-cryptographic-materials-in-UniSUF-are-shown-each-w.png"),
                (
                    "每個物件的簽署金鑰對應到特定實體 (VCM、PSA、PDA、PIA)。",
                    "讓 origin-entity 不變量明確化，便於 ProVerif 驗證。",
                ),
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# 6. Li et al. 2025 (ACE) — A Security Architecture for LLM-Integrated Apps
# ---------------------------------------------------------------------------
LI_ACE = Paper(
    source="local", source_id="li2025security",
    title="ACE: A Security Architecture for LLM-Integrated App Systems",
    authors=("Evan Li", "Tushin Mallick", "Evan Rose", "William Robertson",
             "Alina Oprea", "Cristina Nita-Rotaru"),
    year=2025, venue="NDSS 2026",
    abstract="ACE 將 LLM-integrated app 系統重新設計為三階段：僅靠可信查詢的 abstract planning、對已安裝 app 的 concrete planning、隔離式 executor 加上 information-flow control。擊敗 IsolateGPT 的新攻擊、INJEC AGENT 與 ASB benchmark 100% 防禦。",
    url="https://arxiv.org/abs/2504.20984",
    arxiv_id="2504.20984", pdf_url=None,
    summary=PaperSummary(
        language="zh-tw", model=MODEL_TAG, raw_text_chars=130_764,
        pain_points=(
            ("LLM-app 系統將 plan/execute 交錯", (
                "App description / 輸出影響規劃流程",
                "惡意 app 可以透過 prompt injection 劫持 control flow",
                "既有隔離 (IsolateGPT) 仍信任 app description",
            )),
            ("Strong-adversary 模型尚未被涵蓋", (
                "f-Secure 信任 schema；IsolateGPT 信任 description",
                "強對手控制兩者 → 既有防禦失效",
                "Execution 期間的隱私洩漏未被處理",
            )),
            ("對 IsolateGPT 的新攻擊", (
                "Execution Flow Disruption：惡意輸出中斷管線",
                "Execution Manager Hijack：app 輸出 prompt injection",
                "Planner Manipulation：惡意 description 壓制競爭 app",
            )),
            ("Privacy 控制不在設計裡", (
                "LLM 無法被信任以隔離資料類別",
                "對 plan 沒有靜態的 information-flow 政策檢查",
                "跨 app 的資料外流容易發生",
            )),
        ),
        research_question=(
            "在強對手能控制 app 程式、描述、schema、輸出的情況下，能否"
            "設計一個 LLM-integrated app 系統，使其 control flow、execution、"
            "information flow 全可驗證？"
        ),
        contributions_detailed=(
            ("一、針對 IsolateGPT 的三個新攻擊",
             "Execution Flow Disruption、Execution Manager Hijack、Planner Manipulation 全部在公開實作上奏效。"),
            ("二、ACE 三階段架構",
             "Abstract planner (僅信任查詢) → Concrete planner (將 abstract app 對應到已安裝 app) → 隔離 executor。"),
            ("三、靜態 information-flow 驗證",
             "在 Python 子集合的規劃語言上以 lattice-based IFC 政策做靜態分析；違規 plan 被拒絕。"),
            ("四、實證安全 + 效用結果",
             "INJEC AGENT、ASB benchmark 與三個新攻擊全部 100% 防禦；LangChain Tool Usage benchmark 達 ≥80% 效用。"),
        ),
        headline_metrics=(
            ("INJEC AGENT 防禦率", "100%", "prompt-injection benchmark"),
            ("ASB 防禦率", "100%", "Agent Security Bench"),
            ("新攻擊防禦", "3/3", "全部新攻擊封閉"),
            ("Tool Usage 效用", "≥80%", "良性查詢成功率"),
            ("LLM 後端", "5", "GPT-4o, o3-mini, GPT-4.1, Claude 3.7, Qwen-2.5-72B"),
            ("處理攻擊類別", "4", "Planning/Execution integrity, availability, privacy"),
        ),
        technique_table=(
            ("Abstract apps", "類似程式語言多型的抽象抽象 app"),
            ("Python 子集合規劃語言", "對 plan AST 做靜態分析"),
            ("Information-flow lattice", "join = 污染、meet = 最大 clearance"),
            ("Orchestrator-worker executor", "Plan worker + per-app worker (Docker)"),
            ("text-embedding-ada-002", "Concrete-app 相似度篩選"),
            ("LLM-as-matcher (Concrete planner)", "Type signature 相容層"),
        ),
        method_sections=(
            ("Abstract planning", (
                "LLM 只看可信使用者查詢",
                "產生 abstract app + Python 子集合 plan",
                "Control flow 限制 (for-range、while-with-var)",
            )),
            ("Concrete planning", (
                "用 embedding 相似度篩選已註冊 app",
                "LLM 相容層校正型別差異",
                "以 lattice-based IFC 對 matched plan 做驗證",
            )),
            ("Executor", (
                "Orchestrator 擁有 plan + 權限管理",
                "Plan worker = 受限容器，僅網路 IO",
                "App worker = Docker、各自最小特權",
            )),
        ),
        evaluation_sections=(
            ("Case-study 攻擊", (
                "重現 Flow Disruption / Hijack / Planner Manipulation",
                "確認 ACE 全部阻擋",
                "違規 plan 在靜態分析就被拒絕",
            )),
            ("Benchmark", (
                "INJEC AGENT、ASB 兩個 prompt-injection 套件",
                "LangChain Tool Usage 套件作效用評估",
                "5 個後端 LLM 驗證設計與模型無關",
            )),
        ),
        system_flow=(
            "使用者提交可信查詢",
            "Abstract planner 產出 abstract app + plan (僅可信輸入)",
            "Concrete planner 將 abstract app 對應到已安裝 app",
            "在 concrete plan 上做靜態 IFC 分析",
            "Plan worker 在容器內執行 plan",
            "Per-app worker 經 socket 與 orchestrator 溝通",
            "結果回傳；違規 plan 在前期被拒絕",
        ),
        research_questions=(
            ("RQ1", "既有防禦 (IsolateGPT, f-Secure) 在強對手下能否撐住？"),
            ("RQ2", "ACE 能否阻擋新攻擊與 benchmark prompt-injection？"),
            ("RQ3", "IFC 驗證能否從設計層防止隱私洩漏？"),
            ("RQ4", "ACE 在實際工作負載下保留多少效用？"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="強對手下的覆蓋率",
                table=(
                    ("系統", "Plan 完整性", "Exec 完整性", "隱私"),
                    ("IsolateGPT (強對手)", "✗", "✗", "User-guided"),
                    ("f-Secure (強對手)", "✗", "✗", "✗"),
                    ("ACE (強對手)", "✓", "✓", "✓"),
                ),
                analysis=(
                    "強對手模型暴露既有工作的缺口",
                    "信任 description 或 schema → 可被利用",
                    "ACE 以設計切開信任邊界",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="攻擊防禦率",
                table=(
                    ("攻擊來源", "ACE 防禦率"),
                    ("Execution Flow Disruption", "100%"),
                    ("Execution Manager Hijack", "100%"),
                    ("Planner Manipulation", "100%"),
                    ("INJEC AGENT", "100%"),
                    ("Agent Security Bench (ASB)", "100%"),
                ),
                analysis=(
                    "Abstract planner 對 app 輸出 / 描述完全免疫",
                    "Concrete planner 對已安裝 app 盲對應",
                    "Executor 隔離 app 能力與狀態",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="IFC 帶來的隱私",
                table=(
                    ("機制", "屬性"),
                    ("Lattice 政策", "通用上下界 (join, meet)"),
                    ("Plan 靜態分析", "違規流向直接拒絕"),
                    ("查詢隱含污染", "所有流向都帶查詢 label"),
                    ("分支 + 迴圈覆蓋", "兩者皆靜態分析",),
                ),
                analysis=(
                    "預防意外與惡意的資料外流",
                    "在任何 app 被呼叫前完成驗證",
                    "若無安全指派則拒絕 plan",
                ),
            ),
            RqResult(
                rq_id="RQ4", question="效用代價",
                table=(
                    ("Workload", "後端", "效用"),
                    ("LangChain Tool Usage", "GPT-4o", "≥80%"),
                    ("…", "Claude 3.7 Sonnet", "≥80%"),
                    ("…", "Qwen-2.5-72B", "≥80%"),
                ),
                analysis=(
                    "多種後端 LLM 可互換",
                    "ACE 限制不會阻斷真實流程",
                    "代價：abstract / concrete 各一次 LLM pass",
                ),
            ),
        ),
        core_observation=(
            "LLM-integrated app 系統若把規劃、執行、資訊流分離，就能"
            "從設計層做到 secure-by-design。ACE 以三階段管線示範：planner"
            "只看可信查詢、concrete planner 盲掛 app、executor 隔離權限。"
            "在 benchmark 與新攻擊上全部 100% 防禦，仍保留 ≥80% 效用——"
            "強對手下對抗惡意 LLM app 的第一個完整答案。"
        ),
        limitations=(
            "目前僅支援 single-query workloads",
            "Application suite 尚未涵蓋",
            "三階段管線的效能未經深度最佳化",
            "Lattice 政策需要部署時細心設計",
        ),
        future_work=(
            "擴展到 multi-query / stateful agent 工作流",
            "從使用者偏好自動合成 lattice 政策",
            "深度最佳化 abstract+concrete pipeline",
            "與 TEE 整合以硬體錨定 plan 完整性",
        ),
        figures=(
            (
                "典型 LLM-app 系統 vs ACE 比較 (Figure 1, 第 3 頁)",
                _fig("li2025security", "p03-00-Figure-on-page-3.png"),
                (
                    "左：典型交錯 plan-execute；app 輸出影響後續規劃。",
                    "右：ACE 的 abstract planner 只看可信查詢，輸出靜態 plan。",
                ),
            ),
            (
                "ACE 三階段架構 (Figure 3, 第 7 頁)",
                _fig("li2025security", "p07-02-Figure-on-page-7.png"),
                (
                    "Phase 1 abstract planning → Phase 2 concrete planning → Phase 3 isolated execution。",
                    "每階段權限比前一個少；orchestrator 持有能力。",
                ),
            ),
            (
                "Information-flow lattice 範例 (Figure 5, 第 15 頁)",
                _fig("li2025security", "p15-04-The-subset-lattice-for-MFP-The-labels-can-rep.png"),
                (
                    "靜態 IFC 分析所用的子集合 lattice，會拒絕外洩私密資料的 plan。",
                    "join = 資料污染；meet = 目的地最大 clearance。",
                ),
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# 7. Niu & Lam 2025 — Securing Automated Insulin Delivery Systems
# ---------------------------------------------------------------------------
NIU = Paper(
    source="local", source_id="niu2025securing",
    title="Securing Automated Insulin Delivery Systems: A Review of Security Threats and Protective Strategies",
    authors=("Yuchen Niu", "Siew-Kei Lam"),
    year=2025, venue="Computers & Security (Elsevier)",
    abstract="以 PRISMA 系統性回顧 76 篇關於自動胰島素輸注 (AID) 系統資安的文獻，整理 16 個攻擊向量 (機密 / 完整 / 可用性) 並對應防禦家族，揭露資源限制、病患差異、標準化等開放挑戰。",
    url="https://arxiv.org/abs/2503.14006",
    doi="10.1016/j.cose.2025.104733",
    arxiv_id="2503.14006", pdf_url=None,
    summary=PaperSummary(
        language="zh-tw", model=MODEL_TAG, raw_text_chars=154_249,
        pain_points=(
            ("AID 是 safety-critical IoMT", (
                "CGM + 控制演算法 + 胰島素幫浦透過無線連線",
                "失誤即代表低/高血糖甚至致命劑量",
                "市場 2023 $2.34B → 2032 $5.80B"
            )),
            ("無線 + 閉迴路 = 獨特攻擊面", (
                "BLE 易遭 replay 與 MITM 攻擊",
                "實驗證實 20m+ 外可注入致命胰島素劑量",
                "FDA 2019 警告、產品已下架",
            )),
            ("既有回顧未深入攻擊向量", (
                "多數聚焦『非預期失效』而非對手",
                "少數雖談對手但未細究攻擊向量 + 防禦",
                "尚無針對 wearable closed-loop 的系統性回顧",
            )),
            ("防禦設計受裝置限制", (
                "電池 / 計算 / 記憶體限制排除強加密",
                "病患差異使例外偵測難以普適",
                "缺即時顯示，靠病患監看不切實際",
            )),
        ),
        research_question=(
            "AID 系統的 cybersecurity 攻擊向量與防禦機制有哪些？"
            "現有方案在醫療穿戴的資源 / 法規限制下是否實際與穩健？"
        ),
        contributions_detailed=(
            ("一、AID 安全的全景概述",
             "整合技術漏洞、美 / 歐法規、商用產品的安全措施狀態。"),
            ("二、PRISMA 系統性回顧",
             "在 5 個資料庫 (2010–2025) 中經過篩選保留 76 篇研究攻擊向量、防禦、風險評估的文獻。"),
            ("三、攻擊—防禦對映表",
             "依 CIA 三原則整理 16 個攻擊向量，與 4 大防禦家族 (受保護通訊、IDS、控制策略評估、冗餘) 對應。"),
            ("四、開放研究挑戰",
             "資源限制、病患差異、胰島素輸注模式建模、框架標準化、可信賴與隱私保護。"),
        ),
        headline_metrics=(
            ("回顧文獻數 (PRISMA)", "76", "2010–2025 共 5 個資料庫"),
            ("初次資料庫命中", "53", "另 23 篇來自引用追蹤"),
            ("攻擊向量整理", "16", "橫跨 CIA 三原則"),
            ("分析的防禦家族", "4", "通訊 / IDS / 控制 / 冗餘"),
            ("引用之真實召回", "多筆", "含 Medtronic 2023"),
            ("AID 市場 2032 預估", "$5.80B", "從 2023 $2.34B"),
        ),
        technique_table=(
            ("PRISMA 框架", "系統性回顧方法"),
            ("STRIDE 風格", "威脅分類"),
            ("Scopus / IEEE Xplore / PubMed / WoS / Scholar", "資料庫涵蓋"),
            ("Backward + forward citation tracking", "擴大關鍵字之外的搜尋"),
            ("Taxonomy 圖", "威脅與防禦對應"),
        ),
        method_sections=(
            ("搜尋 + 篩選", (
                "5 個資料庫的 Boolean 查詢 (2010–2025)",
                "納入：提出攻擊 / 防禦 / 風險評估的同儕審查文獻",
                "排除：reviews of reviews、無關、非英文",
            )),
            ("威脅 / 防禦對映", (
                "依 CIA 原則分組攻擊",
                "為每個防禦家族標出對應攻擊向量",
                "與美 (FDA) 與歐 (MDR) 法規交叉參考",
            )),
        ),
        evaluation_sections=(
            ("法規景觀比較", (
                "FDA premarket + postmarket guidance",
                "EU MDR + MDCG 2019-16 cybersecurity guidance",
                "DTSec 之 AID 專用標準",
            )),
            ("商用產品安全審視", (
                "現行產品的加密與認證做法",
                "召回與警告紀錄 (Medtronic 等)",
                "風險管理對先進攻擊的限制",
            )),
        ),
        system_flow=(
            "CGM 量測 BG → 無線傳給控制器",
            "控制器以演算法計算胰島素劑量",
            "指令無線送往皮下胰島素幫浦",
            "幫浦透過 infusion set 輸注劑量",
            "攻擊面橫跨無線連線、演算法、幫浦 I/O",
        ),
        research_questions=(
            ("RQ1", "AID 系統面臨哪些攻擊向量 / 風險？"),
            ("RQ2", "既有防禦如何應對？"),
            ("RQ3", "這些防禦在實務上有多穩健？"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="攻擊向量地景",
                table=(
                    ("原則", "攻擊向量"),
                    ("機密性", "Eavesdropping, DIY hacking"),
                    ("完整性 (資料)", "Replay, bias injection, FDIA"),
                    ("完整性 (演算法)", "Computational, ML model, pump driver"),
                    ("可用性", "DoS/DDoS, ransomware, jamming, firmware corruption, routing"),
                ),
                analysis=(
                    "已有商用產品被實證攻擊",
                    "閉迴路系統有特有的 process-aware 攻擊",
                    "ML/DL 控制器引入新攻擊面 (FDIA)",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="防禦家族",
                table=(
                    ("家族", "關鍵方法"),
                    ("受保護通訊", "Auth + 加密 + 安全協定 + 近場通訊"),
                    ("IDS (signature)", "比對已知攻擊樣式"),
                    ("IDS (specification)", "規約化正常運作的形式化規範"),
                    ("IDS (anomaly)", "資料驅動 / 模型驅動 / 混合"),
                    ("控制策略評估", "比對劑量與胰島素輸注模式"),
                    ("冗餘", "ECG monitor / USRP / 次要安全層"),
                ),
                analysis=(
                    "加密成本與電池 / 計算預算衝突",
                    "Anomaly-based IDS 是近年主流",
                    "病患差異要求個人化模型",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="實務可行性",
                table=(
                    ("限制", "對防禦的影響"),
                    ("電池 / 計算", "排除連續迴圈內的 RSA / HE"),
                    ("病患差異", "Anomaly 模型需個人化"),
                    ("無即時顯示", "病患端偵測不可靠"),
                    ("法規不一致", "FDA 處方式、EU 原則式"),
                ),
                analysis=(
                    "輕量 + 自適應防禦是核心缺口",
                    "風險評估缺乏獨立驗證機制",
                    "睡眠 / 日常活動 = 監看盲區",
                ),
            ),
        ),
        core_observation=(
            "AID 系統可說是風險最高的 IoMT 類別：無線、閉迴路、攸關性命。"
            "本研究整理 16 個橫跨 CIA 的攻擊向量，並指出實際攻擊與 FDA 召回。"
            "防禦分為四大家族，但資源限制、病患差異、標準化薄弱阻擋落地。"
            "未來路徑：輕量 + 自適應防禦 + AID 專用認證。"
        ),
        limitations=(
            "回顧範圍止於 2025/2，後續快速變動",
            "聚焦學術文獻，部分業界細節為機密",
            "未提出新防禦，僅比較既有評估方法",
            "與其他 IoMT 系統的比較較為簡略",
        ),
        future_work=(
            "為電池受限裝置設計的資源感知防禦",
            "可持續適應的個人化例外模型",
            "標準化 AID 安全認證 (延伸 DTSec)",
            "可信賴 + 隱私保護的 ML-based AID 控制器",
        ),
        figures=(
            (
                "本論文導覽圖 (Figure 1, 第 3 頁)",
                _fig("niu2025securing", "p03-00-Overview-of-the-paper.png"),
                (
                    "視覺化目錄：狀態概覽、攻擊向量、防禦策略、未來方向。",
                    "每個分支對應論文一個主章節。",
                ),
            ),
            (
                "PRISMA 篩選流程 (Figure 3, 第 5 頁)",
                _fig("niu2025securing", "p05-02-PRISMA-diagram-for-the-screening-process.png"),
                (
                    "資料庫初篩 53 篇 + 引用追蹤 23 篇 → 最終納入 76 篇。",
                    "系統性回顧方法論的標準可重現紀錄。",
                ),
            ),
            (
                "Hybrid 閉迴路胰島素輸送系統概覽 (Figure 5, 第 5 頁)",
                _fig("niu2025securing", "p05-03-An-overview-of-a-hybrid-closed-loop-insulin-delivery-system-.png"),
                (
                    "CGM → 控制演算法 → 胰島素幫浦的閉迴路，並標出無線連線。",
                    "每條紅色箭頭是一個攻擊面；此圖錨定後續威脅模型。",
                ),
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# 8. Fang & Fang 2026 — Disentangling Adversarial Prompts (AAAI 2026)
# ---------------------------------------------------------------------------
FANG = Paper(
    source="local", source_id="fang2026disentangling",
    title="Disentangling Adversarial Prompts: A Semantic-Graph Defense for Robust LLM Security",
    authors=("Xiang Fang", "Wanlong Fang"),
    year=2026, venue="AAAI 2026",
    abstract=(
        "本文提出 Adversarial Prompt Disentanglement(APD)主動式防禦,先以互資訊 "
        "VAE 將輸入 prompt 分解為良性與對抗性兩個 latent 成分,接著在語意圖上以譜分析 "
        "(spectral analysis)判定意圖,最後交給知識蒸餾過的輕量 transformer 做決策。 "
        "APD 在三組越獄資料集上取得 92.3% 的對抗偵測準確率(ADA)、87.4% 的有害輸出 "
        "減量(HOR),每筆 prompt 推論延遲 12.3 ms — 與規則式 filter 相當,比 post-output "
        "moderation 快約 4 倍。"
    ),
    url="https://doi.org/10.1609/aaai.v40i5.37389",
    doi="10.1609/aaai.v40i5.37389",
    arxiv_id=None, pdf_url=None,
    summary=PaperSummary(
        language="zh-tw", model=MODEL_TAG, raw_text_chars=43_754,
        pain_points=(
            ("既有防禦是事後反應,不是事前阻斷", (
                "Post-output moderation 是在 LLM 已產出後才掃描",
                "規則式過濾遇到改述 / 混淆攻擊就破功",
                "對抗訓練要 fine-tune LLM,正常任務的效能會掉",
            )),
            ("實際部署的計算成本壓不下來", (
                "Post-output moderation:45.6 ms/prompt",
                "對抗訓練(AT):38.2 ms/prompt",
                "即時對話應用根本吸收不了這個延遲",
            )),
            ("沒有統一框架可以「先把對抗成分卸掉」", (
                "防禦把 prompt 當成不透明文字處理",
                "缺乏對「對抗 vs 良性」訊號的原理性分離",
                "每出現一類新攻擊就得加一批新規則",
            )),
            ("跨新攻擊的泛化能力薄弱", (
                "規則式 ADA 在多樣 benchmark 上掉到 65.4%",
                "Embedding clustering:同一批 benchmark 只有 78.6%",
                "三組資料集中沒有任何既有防禦能維持 >87%",
            )),
        ),
        research_question=(
            "在保持實時延遲、不傷害正常查詢效能的前提下,我們能否 **在 LLM 處理 prompt "
            "之前** 主動偵測並中和其中的對抗性成分?"
        ),
        contributions_detailed=(
            ("1. 互資訊式語意分解",
             "VAE 編碼器把 prompt 切成對抗 latent za 與良性 latent zb;訓練目標最小化 "
             "I(za;zb|Ep),透過 Data Processing Inequality(DPI)保證分離。"),
            ("2. 基於語意圖的意圖分類",
             "在 za 的語意鄰域建圖,以譜分析(Fiedler 向量 + 高階特徵值)抓出對抗模式, "
             "對 surface-level 改述具備強穩健性。"),
            ("3. 知識蒸餾的輕量偵測器(AID)",
             "Transformer-based 對抗意圖偵測器,經知識蒸餾後每筆 12.3 ms — "
             "比未蒸餾版本(28.4 ms)快 2.3 倍,精度幾乎無損。"),
            ("4. 在三組越獄 benchmark 上的全面評估",
             "JailBreakBench、ToxicPrompts、AdvPromptGen — APD 平均 ADA 92.3%,比 "
             "四個 SOTA 防禦至少高 5.6 個百分點。"),
        ),
        headline_metrics=(
            ("對抗偵測準確率", "92.3%", "規則式 65.4 / EC 78.6 / AT 86.7"),
            ("有害輸出減量", "87.4%", "規則式 58.9 / post-output 72.3"),
            ("偽陽性率", "3.7%", "規則式 7.7 / post-output 5.0"),
            ("推論延遲", "12.3 ms", "post-output moderation:45.6 ms"),
            ("移除 VAE 後 ADA 下降", "-9.6 pp", "ablation:92.3 → 82.7"),
            ("多語對抗變體的 ADA", "89.3%", "不需要語言特定再訓練"),
        ),
        technique_table=(
            ("規則式過濾", "關鍵字 pattern;65.4% ADA / 10.8 ms"),
            ("Post-Output Moderation", "RoBERTa 掃輸出;84.1% / 45.6 ms"),
            ("對抗訓練(AT)", "LLM fine-tune adv+benign;86.7% / 38.2 ms"),
            ("Embedding Clustering", "embedding 例外偵測;78.6% / 15.6 ms"),
            ("APD(本論文)", "VAE + 譜圖 + 蒸餾 AID;92.3% / 12.3 ms"),
        ),
        method_sections=(
            ("互資訊式語意分解", (
                "VAE 編碼器把 prompt embedding Ep 切成 za / zb 兩個 latent",
                "Loss 最小化 I(za;zb|Ep) — 論文以 DPI 給出形式化證明",
                "對抗與良性 latent 在 latent 空間幾乎不重疊",
            )),
            ("基於語意圖的意圖分類", (
                "在 za 的語意鄰域建立 graph",
                "計算 Fiedler 向量 + 前 k 個高階 Laplacian 特徵值",
                "譜特徵串接後送入下游意圖分類器",
            )),
            ("對抗意圖偵測器(AID)", (
                "輕量 transformer 二元分類器",
                "從大型 teacher 知識蒸餾而來(28.4 ms → 12.3 ms)",
                "輸出「中和 / 阻擋」決策後,prompt 才進到 LLM",
            )),
        ),
        evaluation_sections=(
            ("對抗偵測(ADA / FPR)", (
                "JailBreakBench:91.2% ADA / 3.8% FPR",
                "ToxicPrompts:93.5% / 3.5%",
                "AdvPromptGen:92.3% / 3.7%",
            )),
            ("有害輸出減量(HOR)", (
                "三組 benchmark 平均 87.4%",
                "規則式 58.9%、post-output 72.3%、AT 75.8%",
                "Embedding clustering 65.2% — 複雜攻擊仍會漏",
            )),
            ("計算效率(IL)", (
                "12.3 ms/prompt — 與規則式 10.8 ms 同級",
                "Post-output moderation:45.6 ms(慢 3.7 倍)",
                "對抗訓練:38.2 ms(慢 3.1 倍)",
            )),
            ("新型攻擊變體", (
                "角色扮演 (n=400):90.5% ADA / 85.3% HOR",
                "代碼注入 (n=300):88.7% / 83.9%",
                "多語 prompt (n=300):89.3% / 84.5%",
            )),
        ),
        system_flow=(
            ("使用者 prompt", "進入 LLM 前先送 APD 評估"),
            ("VAE 編碼器", "產生 latent 表示 Ep"),
            ("分離器 fa / fb", "切成對抗 za、良性 zb(DPI 保證)"),
            ("語意圖 + 譜特徵", "在 za 上計算 Fiedler + 高階特徵值"),
            ("AID 分類器(蒸餾版)", "12.3 ms 內輸出二元意圖判斷"),
            ("決策", "對抗:中和 / 阻擋;良性:放行給 LLM"),
        ),
        research_questions=(
            ("RQ1", "APD 的主動式偵測在多樣越獄資料集上能否勝過反應式防禦?"),
            ("RQ2", "APD 在精度與計算成本之間的取捨如何?"),
            ("RQ3", "APD 各組件對穩健性的貢獻(ablation)?"),
            ("RQ4", "APD 是否能泛化到訓練分佈外的新型攻擊變體?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="主動偵測能否勝過反應式防禦?",
                table=(
                    ("方法", "ADA (%)", "HOR (%)", "FPR (%)"),
                    ("規則式", "65.4", "58.9", "7.7"),
                    ("Post-Output Moderation", "84.1", "72.3", "5.0"),
                    ("對抗訓練", "86.7", "75.8", "6.0"),
                    ("Embedding Clustering", "78.6", "65.2", "5.1"),
                    ("APD(本論文)", "92.3", "87.4", "3.7"),
                ),
                analysis=(
                    "APD 在 ADA 上至少領先所有 baseline 5.6 個百分點",
                    "HOR 領先最佳 baseline(AT)11.6 個百分點",
                    "同時 FPR 最低 — 不靠誤判換偵測率",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="精度 / 延遲的取捨?",
                table=(
                    ("方法", "ADA (%)", "IL (ms)"),
                    ("規則式", "65.4", "10.8"),
                    ("Embedding Clustering", "78.6", "15.6"),
                    ("APD(本論文)", "92.3", "12.3"),
                    ("對抗訓練", "86.7", "38.2"),
                    ("Post-Output Moderation", "84.1", "45.6"),
                ),
                analysis=(
                    "APD 落在帕雷托前緣:比規則式 ADA 高 27 pp,只多 1.5 ms",
                    "對 post-output moderation:ADA +8.2 pp 而延遲 1/3.7",
                    "蒸餾是關鍵 — 不做蒸餾延遲會升到 28.4 ms",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="哪些組件最關鍵(ablation)?",
                table=(
                    ("配置", "ADA (%)", "HOR (%)", "IL (ms)"),
                    ("完整 APD", "92.3", "87.4", "12.3"),
                    ("移除 VAE", "82.7", "74.1", "12.1"),
                    ("移除圖特徵", "85.3", "78.6", "11.5"),
                    ("移除 AID 蒸餾", "92.5", "87.7", "28.4"),
                    ("移除高階特徵值", "90.0", "85.0", "12.0"),
                ),
                analysis=(
                    "VAE 是貢獻最大的單一組件(移除 ADA 掉 9.6 pp)",
                    "圖特徵貢獻 7.0 pp;單高階特徵值 2.3 pp",
                    "蒸餾不影響精度但決定延遲:省下 2.3 倍時間",
                ),
            ),
            RqResult(
                rq_id="RQ4", question="能否泛化到新型攻擊變體?",
                table=(
                    ("攻擊變體", "ADA (%)", "HOR (%)", "FPR (%)"),
                    ("角色扮演 (n=400)", "90.5", "85.3", "3.6"),
                    ("代碼注入 (n=300)", "88.7", "83.9", "3.8"),
                    ("多語 prompt (n=300)", "89.3", "84.5", "3.7"),
                ),
                analysis=(
                    "三類分佈外攻擊全部維持 ADA >88%",
                    "FPR 即使在新變體上也低於 4%",
                    "多語泛化尤為顯著 — 不需要語言特定再訓練",
                ),
            ),
        ),
        core_observation=(
            "在 LLM 輸入的 latent 空間裡,把對抗成分和良性成分分離(VAE 目標形式化最小化 "
            "I(za;zb|Ep)),既比事後偵測準(92.3% ADA),又快 3-4 倍。"
        ),
        limitations=(
            "只在三組越獄 benchmark 上驗證 — 對全新攻擊類別的轉移未經實證",
            "AID 需要標註過的對抗訓練資料 — 本質上仍是監督式",
            "VAE 是獨立模型,部署時需要額外 GPU 記憶體",
            "譜圖計算對於極長 prompt 可能 scale 不佳",
        ),
        future_work=(
            "把 APD 延伸到多模態 LLM(圖像 + 文字)",
            "用自監督預訓練降低對標註資料的依賴",
            "持續 / 線上學習以追上演化中的攻擊模式",
        ),
    ),
)


ALL_PAPERS = (WEN, MCCLEARN, SHUKLA, OBADOFIN, HAGEN, LI_ACE, NIU, FANG)


def main() -> None:
    out_dir = ROOT / "exports" / _RUN_DIR_NAME
    out_dir.mkdir(parents=True, exist_ok=True)
    for paper in ALL_PAPERS:
        collection = PaperCollection(
            query=Query(
                keywords="LLM 資安",
                sources=("local",),
                max_results=1,
            ),
            papers=(paper,),
        )
        options = ExportOptions(
            formats=("pptx",),
            out_dir=str(out_dir),
            # Language variant: -zh-tw is the explicitly allowed exception
            # to the canonical-filename rule, so the user can keep both
            # English and Traditional Chinese decks side-by-side.
            filename_stem=f"{paper.bibtex_key()}-zh-tw",
            include_abstract=True,
            language="zh-tw",
        )
        written = export_collection(collection, options)
        for fmt, path in written.items():
            print(f"  - {paper.bibtex_key()} {fmt}: {path}")


if __name__ == "__main__":
    main()
