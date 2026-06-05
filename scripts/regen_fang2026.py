"""Regenerate exports/fang2026disentangling-zh-tw.pptx from a hand-authored
``PaperSummary``, replacing the earlier patch-stack build.

Why this script exists
----------------------
The deck shipped 2026-05-19 as a *light-mode* export, then was mutated in
place by three follow-up scripts:

  * ``convert_fang2026_to_dark_mode.py`` — light → dark post-pass,
  * ``apply_clarity_rule_fang2026.py``   — clarity pass 1 (gloss ADA / VAE / DPI / …),
  * ``apply_clarity_pass2_fang2026.py``  — clarity pass 2 (APD / SOTA / 越獄 / table cells).

That patch stack is fragile: the clarity passes did in-run / merged-run
text surgery (losing per-run formatting on merged paragraphs), the
dark-mode conversion ran on a deck the exporter never built dark, and the
two contribution slides (主要貢獻 / 貢獻總結) drifted apart because only the
first was glossed. "重新製作" means rebuild the deck *natively* through the
real exporter so every visual-identity pass (typography, accent geometry,
dark mode) runs at construction time and the glosses live in the source
``PaperSummary`` instead of being bolted on afterwards.

What this reconstructs
----------------------
The full rich-tier ``PaperSummary`` for the AAAI-2026 paper
"Disentangling Adversarial Prompts: A Semantic-Graph Defense for Robust
LLM Security" (Xiang Fang, Wanlong Fang). Every field carries the
clarity-glossed wording from the audited deck — acronyms defined at first
use per ``slide-deck-rules`` §8 (ADA / VAE / DPI / Fiedler / APD / SOTA /
越獄 / RoBERTa / pp / ablation / 譜分析 / Transformer / 知識蒸餾). Content is
preserved verbatim from the existing deck — no metrics, claims, authors,
DOI, or venue are invented here.

Field → slide mapping (single-paper rich tier, dark mode, zh-tw):

  cover + overview ........ Paper (title / authors / year / venue / doi / url)
  pain_points + research_question ... slide 3  研究背景與痛點
  contributions_detailed .. slide 4  主要貢獻  (and slide 16 貢獻總結 — same field)
  headline_metrics ........ slide 5  主要量化成果
  technique_table ......... slide 6  關鍵技術概覽
  method_sections ......... slides 7-8  方法細節 (2 per slide)
  evaluation_sections ..... slides 9-10 評估方法 (2 per slide)
  research_questions ...... slide 11 研究問題
  rq_results .............. slides 12-15 主要結果 RQ1-4
  core_observation ........ slide 17 核心觀察
  limitations + future_work slide 18 研究限制 & 未來工作

Run from the project root:  ``.venv/Scripts/python.exe scripts/regen_fang2026.py``
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
FILENAME_STEM = "fang2026disentangling-zh-tw"
LANGUAGE = "zh-tw"


def _build_summary() -> PaperSummary:
    return PaperSummary(
        language=LANGUAGE,
        # ---- slide 3: 研究背景與痛點 (pain-point quadrant + RQ callout) --------
        pain_points=(
            (
                "既有防禦是事後反應,不是事前阻斷",
                (
                    "Post-output moderation 是在 LLM 已產出後才掃描",
                    "規則式過濾遇到改述(paraphrasing,攻擊者改寫提示文字) / "
                    "混淆(obfuscation,以異常編碼或拼字繞過)攻擊就破功",
                    "對抗訓練要 fine-tune LLM,正常任務的效能會掉",
                ),
            ),
            (
                "實際部署的計算成本壓不下來",
                (
                    "Post-output moderation:45.6 ms/prompt",
                    "對抗訓練(AT):38.2 ms/prompt",
                    "即時對話應用根本吸收不了這個延遲",
                ),
            ),
            (
                "沒有統一框架可以「先把對抗成分卸掉」",
                (
                    "防禦把 prompt 當成不透明文字處理",
                    "缺乏對「對抗 vs 良性」訊號的原理性分離",
                    "每出現一類新攻擊就得加一批新規則",
                ),
            ),
            (
                "跨新攻擊的泛化能力薄弱",
                (
                    "規則式 ADA(對抗偵測準確率,Adversarial Detection Accuracy)"
                    "在多樣 benchmark 上掉到 65.4%",
                    "Embedding clustering(以 embedding 距離找異常的偵測法):"
                    "同一批 benchmark 只有 78.6%",
                    "三組資料集中沒有任何既有防禦能維持 >87%",
                ),
            ),
        ),
        research_question=(
            "在保持實時延遲、不傷害正常查詢效能的前提下,我們能否 "
            "在 LLM 處理 prompt 之前主動偵測並中和其中的對抗性成分?"
        ),
        # ---- slide 4 / 16: 主要貢獻 / 貢獻總結 --------------------------------
        contributions_detailed=(
            (
                "1. 互資訊式語意分解",
                "VAE(變分自編碼器,Variational Autoencoder)編碼器把 prompt "
                "切成對抗潛在向量 za 與良性潛在向量 zb,訓練目標最小化"
                "互資訊 I(za;zb|Ep),透過 Data Processing Inequality"
                "(DPI,限制條件互資訊在資料處理鏈中不會上升)保證分離。",
            ),
            (
                "2. 基於語意圖的意圖分類",
                "在 za 的語意鄰域建圖,以譜分析(spectral analysis,從圖的"
                "特徵值結構抓出社群分離模式)之 Fiedler 向量(圖 Laplacian 的"
                "第二小特徵向量)與更高階特徵值抓出對抗模式, 對改述具備強穩定性。",
            ),
            (
                "3. 知識蒸餾的輕量偵測器(AID)",
                "Transformer-based(以注意力機制為核心的深度學習網路)對抗意圖"
                "偵測器,經知識蒸餾(把大型 teacher 模型的推理能力轉到小型 "
                "student 模型)後每筆 12.3 ms — 比未蒸餾版本(28.4 ms)快 2.3 倍,"
                "精度幾乎無損。",
            ),
            (
                "4. 在三組越獄(jailbreak,誘騙 LLM 繞過安全限制之提示)"
                "benchmark 上的全面評估",
                "JailBreakBench、ToxicPrompts、AdvPromptGen — APD"
                "(Adversarial Prompt Disentanglement,對抗提示語意分解)平均 "
                "ADA 92.3%,比四個 SOTA(State-of-the-Art,當前最佳)防禦至少"
                "高 5.6 個百分點。",
            ),
        ),
        # ---- slide 5: 主要量化成果 (KPI block; baseline prefix 對照組 added by builder)
        headline_metrics=(
            (
                "對抗偵測準確率 (ADA)",
                "92.3%",
                "規則式 65.4 / EC(Embedding Clustering) 78.6 / AT(對抗訓練) 86.7",
            ),
            ("有害輸出減量 (HOR)", "87.4%", "規則式 58.9 / post-output 72.3"),
            ("偽陽性率 (FPR)", "3.7%", "規則式 7.7 / post-output 5.0"),
            ("推論延遲 (IL)", "12.3 ms", "post-output moderation:45.6 ms"),
            (
                "移除 VAE 後 ADA 下降",
                "-9.6 pp(percentage points,百分點)",
                "ablation 消融實驗:92.3 → 82.7",
            ),
            ("多語對抗變體的 ADA", "89.3%", "不需要語言特定再訓練"),
        ),
        # ---- slide 6: 關鍵技術概覽 (technique → role table) ------------------
        technique_table=(
            ("規則式過濾", "關鍵字 pattern,65.4% ADA / 10.8 ms"),
            (
                "Post-Output Moderation",
                "RoBERTa(BERT 改良版預訓練語言模型)掃輸出,84.1% / 45.6 ms",
            ),
            ("對抗訓練(AT)", "LLM fine-tune adv+benign,86.7% / 38.2 ms"),
            ("Embedding Clustering", "embedding 異常偵測,78.6% / 15.6 ms"),
            ("APD(本論文)", "VAE + 譜圖 + 蒸餾 AID,92.3% / 12.3 ms"),
        ),
        # ---- slides 7-8: 方法細節 (2 sections per slide) ---------------------
        method_sections=(
            (
                "互資訊式語意分解",
                (
                    "VAE 編碼器把 prompt embedding Ep 切成 za / zb 兩個 latent",
                    "Loss 最小化 I(za;zb|Ep) — 論文以 DPI 給出形式化證明",
                    "對抗與良性 latent 在 latent 空間幾乎不重疊",
                ),
            ),
            (
                "基於語意圖的意圖分類",
                (
                    "在 za 的語意鄰域建立 graph",
                    "計算 Fiedler 向量 + 前 k 個高階 Laplacian 特徵值",
                    "譜特徵串接後送入下游意圖分類器",
                ),
            ),
            (
                "對抗意圖偵測器(AID)",
                (
                    "輕量 transformer 二元分類器",
                    "從大型 teacher 知識蒸餾而來(28.4 ms → 12.3 ms)",
                    "輸出「中和 / 阻擋」決策後,prompt 才進到 LLM",
                ),
            ),
        ),
        # ---- slides 9-10: 評估方法 (2 sections per slide) --------------------
        evaluation_sections=(
            (
                "對抗偵測(ADA / FPR)",
                (
                    "JailBreakBench:91.2% ADA / 3.8% FPR",
                    "ToxicPrompts:93.5% / 3.5%",
                    "AdvPromptGen:92.3% / 3.7%",
                ),
            ),
            (
                "有害輸出減量(HOR)",
                (
                    "三組 benchmark 平均 87.4%",
                    "規則式 58.9%、post-output 72.3%、AT 75.8%",
                    "Embedding clustering 65.2% — 複雜攻擊仍會漏",
                ),
            ),
            (
                "計算效率(IL)",
                (
                    "12.3 ms/prompt — 與規則式 10.8 ms 同級",
                    "Post-output moderation:45.6 ms(慢 3.7 倍)",
                    "對抗訓練:38.2 ms(慢 3.1 倍)",
                ),
            ),
            (
                "新型攻擊變體",
                (
                    "角色扮演 (n=400):90.5% ADA / 85.3% HOR",
                    "程式碼注入 (n=300):88.7% / 83.9%",
                    "多語 prompt (n=300):89.3% / 84.5%",
                ),
            ),
        ),
        # ---- slide 11: 研究問題 ---------------------------------------------
        research_questions=(
            ("RQ1", "APD 的主動式偵測在多樣越獄資料集上能否勝過反應式防禦?"),
            ("RQ2", "APD 在精度與計算成本之間的取捨如何?"),
            ("RQ3", "APD 各組件的貢獻(ablation)?"),
            ("RQ4", "APD 是否能泛化到訓練分佈外的新型攻擊變體?"),
        ),
        # ---- slides 12-15: 主要結果 RQ1-4 (table + analysis) ----------------
        rq_results=(
            RqResult(
                rq_id="RQ1",
                question="APD 的主動式偵測在多樣越獄資料集上能否勝過反應式防禦?",
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
                rq_id="RQ2",
                question="APD 在精度與計算成本之間的取捨如何?",
                table=(
                    ("方法", "ADA (%)", "IL (ms)"),
                    ("規則式", "65.4", "10.8"),
                    ("Embedding Clustering", "78.6", "15.6"),
                    ("APD(本論文)", "92.3", "12.3"),
                    ("對抗訓練", "86.7", "38.2"),
                    ("Post-Output Moderation", "84.1", "45.6"),
                ),
                analysis=(
                    "APD :比規則式 ADA 高 27 %,只多 1.5 ms",
                    "對 post-output moderation:ADA +8.2 % 而延遲 1/3.7",
                    "蒸餾是關鍵 — 不做蒸餾延遲會升到 28.4 ms",
                ),
            ),
            RqResult(
                rq_id="RQ3",
                question="APD 各組件的貢獻(ablation)?",
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
                    "圖特徵貢獻 7.0 pp,單高階特徵值 2.3 pp",
                    "蒸餾不影響精度但決定延遲:省下 2.3 倍時間",
                ),
            ),
            RqResult(
                rq_id="RQ4",
                question="APD 是否能泛化到訓練分佈外的新型攻擊變體?",
                table=(
                    ("攻擊變體", "ADA (%)", "HOR (%)", "FPR (%)"),
                    ("角色扮演 (n=400)", "90.5", "85.3", "3.6"),
                    ("程式碼注入 (n=300)", "88.7", "83.9", "3.8"),
                    ("多語 prompt (n=300)", "89.3", "84.5", "3.7"),
                ),
                analysis=(
                    "三類分佈外攻擊全部維持 ADA >88%",
                    "FPR 即使在新變體上也低於 4%",
                    "多語泛化尤為顯著 — 不需要語言特定再訓練",
                ),
            ),
        ),
        # ---- slide 17: 核心觀察 ---------------------------------------------
        core_observation=(
            "在 LLM 輸入的 latent 空間裡,把對抗成分和良性成分分離"
            "(VAE 目標形式化最小化 I(za;zb|Ep)),既比事後偵測準(92.3% ADA),"
            "又快 3-4 倍。"
        ),
        # ---- slide 18: 研究限制 & 未來工作 -----------------------------------
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
        model="hand-authored:regen_fang2026",
    )


def _build_paper() -> Paper:
    return Paper(
        source="local",
        source_id="fang2026disentangling",
        title=(
            "Disentangling Adversarial Prompts: A Semantic-Graph Defense "
            "for Robust LLM Security"
        ),
        authors=("Xiang Fang", "Wanlong Fang"),
        year=2026,
        venue="AAAI 2026",
        abstract="",
        url="https://doi.org/10.1609/aaai.v40i5.37389",
        doi="10.1609/aaai.v40i5.37389",
        summary=_build_summary(),
    )


def main() -> None:
    paper = _build_paper()
    collection = PaperCollection(
        query=Query(keywords="disentangling adversarial prompts", sources=("local",)),
        papers=(paper,),
    )
    options = ExportOptions(
        formats=("pptx",),
        out_dir=OUT_DIR,
        filename_stem=FILENAME_STEM,
        language=LANGUAGE,
        dark_mode=True,
    )
    out_path = PptxExporter().export(collection, options)
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()
