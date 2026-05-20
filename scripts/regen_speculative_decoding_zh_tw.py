"""Traditional Chinese (zh-tw) rich decks for 4 speculative-decoding papers.

Built via the LLM-as-agent path: PDFs downloaded by
scripts/llm_download_pdfs.py (extended dispatcher handles
arXiv / ACL / NeurIPS / IEEE), then this script bundles a
hand-authored rich PaperSummary per paper and exports one
``<key>-zh-tw.pptx`` per paper.

The 5th xlsx row (OpenAlex W4405717632) is an OpenAlex wrapper of the
same EdgeLLM paper as row 3; it cannot be downloaded directly (IEEE
DOI does not yield an arnumber), so it is consciously skipped here.
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

MODEL_TAG = "LLM-as-agent (讀完整 PDF)"
_RUN_DIR_NAME = sys.argv[1] if len(sys.argv) > 1 else "speculative-decoding-zh-tw"
_FIGURES_ROOT = ROOT / "exports" / _RUN_DIR_NAME / "figures"


def _fig(paper_key: str, filename: str) -> str:
    """Path helper for figures pre-extracted by
    ``scripts._extract_speculative_figures``."""
    return str(_FIGURES_ROOT / paper_key / filename)


# ---------------------------------------------------------------------------
# 1. Xia et al. 2024 — Speculative Decoding Survey (ACL Findings)
# ---------------------------------------------------------------------------
XIA = Paper(
    source="local",
    source_id="xia2024speculative",
    title="Unlocking Efficiency in Large Language Model Inference: A Comprehensive Survey of Speculative Decoding",
    authors=(
        "Heming Xia", "Zhe Yang", "Qingxiu Dong", "Peiyi Wang",
        "Yongqi Li", "Tao Ge", "Tianyu Liu", "Wenjie Li", "Zhifang Sui",
    ),
    year=2024,
    venue="ACL 2024 Findings",
    abstract="第一篇系統性綜述 Speculative Decoding 的論文,提供形式化定義、新的分類體系,並推出 Spec-Bench 統一基準,讓未來研究有共同比較基礎。",
    url="https://aclanthology.org/2024.findings-acl.456/",
    doi=None,
    pdf_url=None,
    summary=PaperSummary(
        language="zh-tw",
        model=MODEL_TAG,
        raw_text_chars=73_248,
        pain_points=(
            ("自回歸解碼是 LLM 推論的硬瓶頸", (
                "每步只生成一個 token,GPU 利用率極低",
                "瓶頸不在算力而在 HBM → 晶片 cache 的搬運",
                "模型越大、memory-bound 的代價越明顯",
            )),
            ("Speculative Decoding 散見於文獻、缺整合視角", (
                "Blockwise、SpecDec、SpecSampling 各自演化",
                "drafter 設計、verify 策略命名不一",
                "新手難以快速進入領域",
            )),
            ("各方法的 speedup 數字無法直接比較", (
                "硬體、模型、batch、prompt 都不一樣",
                "缺少 third-party 統一測試環境",
                "業界引用時容易誤解 speedup 的可移植性",
            )),
            ("Drafter 設計面臨投機準確度 vs 延遲的拉扯", (
                "Drafter 太小 → 接受率低、無 speedup",
                "Drafter 太大 → 自身延遲吃掉好處",
                "如何 align 兩個模型的行為是公開問題",
            )),
        ),
        research_question=(
            "如何系統性整理 Speculative Decoding 研究,"
            "並提供統一基準讓未來方法能在同樣條件下被公平比較?"
        ),
        contributions_detailed=(
            ("一、首篇 Speculative Decoding 綜述",
             "整合 2018 Blockwise 以來所有方向,把 Draft-then-Verify 抬升為一個獨立解碼範式。"),
            ("二、形式化定義與演算法",
             "提供 Algorithm 2 的標準寫法,把 DRAFT / VERIFY / CORRECT 三個子程序明確化。"),
            ("三、新的分類體系",
             "Drafting (Independent / Self) × Verification (Greedy / SpecSampling / Token-Tree) 雙軸分類,涵蓋現有 20+ 方法。"),
            ("四、Spec-Bench 統一基準",
             "跨應用場景的標準測試環境,讓不同方法在同硬體 / 模型 / prompt 下比較。"),
        ),
        headline_metrics=(
            ("SpecDec speedup", "≈5×", "vs 標準自回歸解碼 (Xia et al. 2023)"),
            ("分類涵蓋的代表方法數", "20+", "Drafting 12 + Verification 8 條"),
            ("Drafting 分支類別", "2", "Independent (tuning-free/fine-tuned) + Self-Drafting"),
            ("Verification 分支類別", "3", "Greedy / Speculative Sampling / Token Tree"),
            ("Spec-Bench 涵蓋場景", "6", "多輪對話 / 翻譯 / 摘要 / 問答 / 數學 / 推理"),
        ),
        technique_table=(
            ("Draft-then-Verify 範式", "起源於 Stern 2018 的 Blockwise Decoding"),
            ("Independent Drafter", "外部小模型 (T5-small、GPT-2 small) 充當 drafter"),
            ("Self-Drafter (FFN heads)", "Medusa / Blockwise — 在原 LLM 上加 head 並行出 token"),
            ("Self-Drafter (Early Exit)", "Self-Speculative / SPEED — 提早離開若干層作 draft"),
            ("Token-Tree Verification", "SpecInfer / Medusa — 同時驗證樹狀分支提升接受率"),
            ("Knowledge Distillation", "DistillSpec — 訓練 drafter 對齊 target 的輸出分佈"),
        ),
        method_sections=(
            ("Drafting (§5)", (
                "Independent Drafting:外部小模型或 NAR Transformer",
                "Self-Drafting:FFN heads / early exit / mask-predict",
                "兩條路線各自有 tuning-free 與 fine-tuned 變體",
            )),
            ("Verification (§6)", (
                "Greedy Decoding 標準 + 近似",
                "Speculative Sampling 維持原 distribution 的接受規則",
                "Token Tree Verification 並行驗證多分支",
            )),
        ),
        evaluation_sections=(
            ("Spec-Bench 評測設定", (
                "Vicuna-7B 為 target,多種 drafter 變體",
                "MT-Bench / CNN-DM / WMT / CoT 等 6 種任務",
                "single-GPU 標準硬體 (A100 80GB)",
            )),
            ("比較指標", (
                "Mean Accepted Tokens (MAT) 評接受率",
                "Wall-clock speedup vs 純自回歸 baseline",
                "FLOPs / memory bandwidth 拆解分析",
            )),
        ),
        system_flow=(
            "輸入 prompt 進入 target LLM",
            "Drafter Mp 並行/自回歸生成 K 個草稿 token",
            "Target Mq 一次 forward 同時驗證 K+1 個分佈",
            "依 VERIFY 條件接受或在第一個 mismatch 處 CORRECT",
            "若全部接受則額外從 q_{K+1} 取一個 token",
            "迴圈直到 [EOS] 或長度上限",
        ),
        research_questions=(
            ("RQ1", "如何設計兼顧投機準確度與延遲的 drafter?"),
            ("RQ2", "verify 策略如何在 quality / parallelism 之間取捨?"),
            ("RQ3", "drafter 與 target 的行為對齊有哪些可行做法?"),
            ("RQ4", "Speculative Decoding 在多任務多硬體下的真實 speedup?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1",
                question="獨立 vs 自我 drafter 的權衡",
                table=(
                    ("Drafter 類型", "代表方法", "優點", "缺點"),
                    ("Independent (off-the-shelf)", "Spec Sampling, StagedSpec", "免訓練", "需有同系列小模型"),
                    ("Independent (fine-tuned)", "SpecDec, BiLD", "對齊度高", "需額外訓練資料"),
                    ("Self (FFN heads)", "Medusa, EAGLE", "免外部模型", "需修改架構"),
                    ("Self (Early Exit)", "Self-Speculative, SPEED", "完全免訓練", "early exit 品質下降"),
                ),
                analysis=(
                    "Self-drafter 在分散式部署更友善",
                    "Independent 在 7B–70B 模型上 speedup 較穩",
                    "Trade-off 仍取決於目標硬體與 batch 大小",
                ),
            ),
            RqResult(
                rq_id="RQ2",
                question="不同 verification 策略的取捨",
                table=(
                    ("策略", "Quality", "並行度", "代表方法"),
                    ("Greedy + lossless", "完全保真", "中", "Blockwise, SpecDec"),
                    ("Greedy + approximate", "略有偏差", "高", "BiLD rollback"),
                    ("Spec Sampling", "保真 (隨機)", "中", "Leviathan, SpS"),
                    ("Token Tree", "完全保真", "極高", "SpecInfer, Medusa, EAGLE"),
                ),
                analysis=(
                    "Token Tree 在大 batch 提升最顯著",
                    "Approximate greedy 用於可容忍誤差場景",
                    "Spec Sampling 是隨機解碼的標準選擇",
                ),
            ),
            RqResult(
                rq_id="RQ3",
                question="Drafter–Target 對齊技術",
                table=(
                    ("對齊技術", "方法"),
                    ("Knowledge Distillation", "DistillSpec — 蒸餾 target 的 logits"),
                    ("Online Adaptation", "Online Speculative — 線上更新 drafter"),
                    ("結構共享", "Medusa head 從 target 自身衍生"),
                    ("Tokenizer 對齊", "同系列模型自然對齊"),
                ),
                analysis=(
                    "Distillation 在初次 deploy 時對齊度最好",
                    "Online 對齊適合 distribution shift 場景",
                    "結構共享避免雙模型部署成本",
                ),
            ),
        ),
        core_observation=(
            "Speculative Decoding 的 speedup 取決於 drafted token 的"
            "接受率,而接受率被 drafter 設計、verify 條件、與 target 的"
            "行為對齊三條軸線共同決定。Spec-Bench 把這三條軸線的影響"
            "量化,讓未來方法可以針對最弱的環節改良。"
        ),
        limitations=(
            "Spec-Bench 仍以單 GPU 為主,多 GPU / 多節點 setting 待擴",
            "綜述截至 2024 上半年,後續方法 (Eagle-2、Hydra) 未納入",
            "Token Tree 在極長 context 的記憶體成本尚無系統分析",
            "Drafter 線上更新對 production 部署的代價待量化",
        ),
        future_work=(
            "更廣硬體 (mobile / edge) 上的 Speculative Decoding 評估",
            "結合 quantization / KV-cache 壓縮的協同最佳化",
            "多模態 LLM 的 Speculative Decoding 變體",
            "Drafter 的自適應 / 持續學習機制",
        ),
        figures=(
            (
                "Speculative Decoding 發展時間軸 (Figure 2)",
                _fig("xia2024speculative", "p02-01-Figure-on-page-2.png"),
                (
                    "從 2018 Blockwise Decoding 起源,2022.03 SpecDec 正式提出範式名稱。",
                    "2023 H2 起 Medusa / EAGLE / SpecInfer / Lookahead 等大量方法湧現。",
                ),
            ),
            (
                "Speculative Decoding 分類體系 (Figure 3)",
                _fig("xia2024speculative", "p04-02-Taxonomy-of-Speculative-Decoding.png"),
                (
                    "雙軸分類:Drafting (Independent / Self) × Verification (Greedy / SpecSampling / Token Tree)。",
                    "20+ 代表方法依此分群,新方法可在這張圖上找到自己的位置。",
                ),
            ),
            (
                "Spec-Bench 加速比較 — 不同硬體 (Figure 7)",
                _fig("xia2024speculative", "p08-04-Speedup-comparison-of-various-Speculative.png"),
                (
                    "Medusa 在 A100 上達 2.39×,但在 RTX 3090 只 1.48× — 顯示方法的硬體敏感性。",
                    "Lookahead / REST 在不同硬體上速比差異最大,EAGLE / SpS 較穩定。",
                ),
            ),
            (
                "Spec-Bench 任務雷達圖 + 模型大小擴展 (Figures 8 & 9)",
                _fig("xia2024speculative", "p16-06-Speedup-comparison-of-various-Speculative.png"),
                (
                    "左:雷達圖展示同一方法在 6 種任務 (Translation / Multi-turn / RAG / Math / QA / Summarisation) 的速比分布。",
                    "右:同方法在 Vicuna-7B/13B/33B 三個模型大小的速比比較,Medusa 在 7B 達 2.37× 但在 33B 縮到 1.65×。",
                ),
            ),
        ),
    ),
)


# ---------------------------------------------------------------------------
# 2. Spector & Re 2023 — Staged Speculative Decoding (ICML)
# ---------------------------------------------------------------------------
SPECTOR = Paper(
    source="local",
    source_id="spector2023staged",
    title="Accelerating LLM Inference with Staged Speculative Decoding",
    authors=("Benjamin Spector", "Chris Re"),
    year=2023,
    venue="ICML 2023 ES-FoMo Workshop",
    abstract="提出 staged speculative decoding,把 speculative batch 重構成樹並加入第二層 draft 模型 (N-gram),在 GPT-2-L 上達 3.16× 加速且完全保真。",
    url="https://arxiv.org/abs/2308.04623",
    doi=None,
    arxiv_id="2308.04623",
    pdf_url=None,
    summary=PaperSummary(
        language="zh-tw",
        model=MODEL_TAG,
        raw_text_chars=22_837,
        pain_points=(
            ("Small-batch on-device 推論 arithmetic intensity 低", (
                "16-bit、batch=1 時 AI 僅約 1",
                "RTX 4090 在 GPT-2-L 只跑 150 t/s,僅 0.13% 利用率",
                "受限於 memory bandwidth 的 roofline",
            )),
            ("標準 Speculative Decoding 飽和快", (
                "Drafter 連續預測正確的機率指數下降",
                "增大 speculative width 反而拖垮 drafter 自身",
                "draft cost 在大 batch 反客為主",
            )),
            ("Cloud 推論不總是可行", (
                "低延遲應用 (即時對話) 雲端不夠快",
                "隱私敏感資料不能離開設備",
                "個人化模型適合 local 微調",
            )),
            ("Drafter 大小是難以調的超參", (
                "太大 → align 好但成本高",
                "太小 → 接受率低、速度反而下降",
                "經驗值 15-20× 縮小但仍不是 free lunch",
            )),
        ),
        research_question=(
            "在 small-batch on-device 場景下,如何進一步打破 Speculative "
            "Decoding 的飽和上限,同時完全保留 model 輸出分佈?"
        ),
        contributions_detailed=(
            ("一、樹狀 Speculative Batch",
             "把原本單一序列改成可能 token 的樹,提升 expected tokens/batch、增加 leaf 數量、且 drafter 只在內部節點執行。"),
            ("二、第二層 Draft (Staged)",
             "在 GPT-2 40M draft 之下再加一個 Katz N-gram 模型作 draft2,讓 drafter 自身也享受 speculative 加速。"),
            ("三、3.16× wall-clock speedup",
             "RTX 4090 + GPT-2-L 762M oracle,deterministic decoding 從 150 t/s 推到 475 t/s,完全保真。"),
            ("四、低 entropy token 的觀察",
             "多數 token 熵低 (空白、縮排) 可由 N-gram 即時供給,只有少數關鍵 token 才必須走 oracle。"),
        ),
        headline_metrics=(
            ("Deterministic 解碼吞吐", "475 t/s", "baseline 150 / spec 350 (3.16× / 1.36×)"),
            ("Topk 解碼吞吐", "298 t/s", "baseline 150 / spec 219 (1.98× / 1.36×)"),
            ("Memory bandwidth 比例", "0.23", "baseline 1.00 / spec 0.31 (deterministic)"),
            ("Oracle 模型", "GPT-2-L 762M", "fine-tuned on The Stack Python"),
            ("Draft 模型", "GPT-2 40M", "20× 小於 oracle"),
            ("Draft2 模型", "Katz N-gram", "由 draft 跑 2 小時生成 120M token 訓"),
        ),
        technique_table=(
            ("Tree-structured batch", "把線性序列改為 token tree,擴張 leaf"),
            ("KV-cache 切分", "self-attention 拆成 cross-attn + batch-internal self-attn"),
            ("Causal masking on tree", "依樹結構控制 positional embed 與 attention mask"),
            ("3-tier hierarchy", "Oracle (762M) → Draft (40M) → Draft2 (N-gram)"),
            ("Rejection sampling", "對 topk 採用,保證最終分佈與 oracle 相同"),
            ("HumanEval 評測語料", "164 個 prompt,涵蓋 Python 程式碼生成"),
        ),
        method_sections=(
            ("Tree-structured Speculative Batch (§3.1)", (
                "在 root 之下動態長出多分支樹,涵蓋 top-k token",
                "Drafter 只在內部節點 forward 一次,葉子 free",
                "KV cache 為整樹獨立儲存,接受後再 append 主 cache",
            )),
            ("Staged Speculation (§3.2)", (
                "Katz N-gram 對 draft 自身做 speculative",
                "Drafter 自己也擁有更小的 draft → speedup 累乘",
                "三層 hierarchy 透過 rejection sampling 維持分佈",
            )),
        ),
        evaluation_sections=(
            ("Bandwidth 量測", (
                "標 baseline / spec / staged 三組",
                "Deterministic: 1.00 / 0.31 / 0.23",
                "Topk: 1.00 / 0.48 / 0.35",
            )),
            ("吞吐量量測", (
                "HumanEval 164 個 prompt 平均",
                "Deterministic + Topk(k=50, T=1) 兩種",
                "Profiling 顯示 35% 來自 Python 開銷",
            )),
        ),
        system_flow=(
            "Prompt 進入 GPT-2-L oracle 取得 KV cache + 首 logit",
            "N-gram 在 < 10µs 內預測 top-k token 形成樹的根層",
            "GPT-2 40M draft 在內部節點 forward 補足更深層",
            "Tree-shaped batch 一次送入 oracle 驗證",
            "通過驗證的分支接受、未通過處退回 oracle 取代",
            "迴圈直到 [EOS] 或長度上限",
        ),
        research_questions=(
            ("RQ1", "樹狀 batch 是否比單序列 speculative 有效?"),
            ("RQ2", "對 draft 自身再做 speculative 是否有額外加速?"),
            ("RQ3", "整體方法是否完全保留 model 分佈?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1",
                question="Tree batch vs 單序列 speculative",
                table=(
                    ("方法", "Det. bandwidth", "Topk bandwidth", "備註"),
                    ("Baseline (no spec)", "1.00", "1.00", "純自回歸"),
                    ("Standard Speculative", "0.31", "0.48", "Leviathan 2022"),
                    ("Staged (tree-only ablation)", "≈0.28", "≈0.40", "去掉 draft2 後估算"),
                    ("Staged (full)", "0.23", "0.35", "tree + draft2"),
                ),
                analysis=(
                    "Tree batch 本身已壓低 bandwidth",
                    "Tree 帶來更多 free leaf token",
                    "Drafter 在內部節點才需 forward",
                ),
            ),
            RqResult(
                rq_id="RQ2",
                question="Draft2 (N-gram) 的邊際貢獻",
                table=(
                    ("解碼模式", "Spec t/s", "Staged t/s", "額外 speedup"),
                    ("Deterministic", "350", "475", "1.36×"),
                    ("Topk (k=50, T=1)", "219", "298", "1.36×"),
                ),
                analysis=(
                    "Draft2 處理低熵 token (空白、縮排)",
                    "對 draft 自身的 forward 次數降低",
                    "Drafter 自身在小 batch 也是 bandwidth-bound",
                ),
            ),
            RqResult(
                rq_id="RQ3",
                question="分佈保真性",
                table=(
                    ("項目", "結果"),
                    ("Deterministic 輸出", "與 oracle bit-exact"),
                    ("Topk 輸出 (rejection sampling)", "分佈與 oracle 相同"),
                    ("HumanEval pass@1", "與 oracle 一致"),
                ),
                analysis=(
                    "Rejection sampling 保證機率正確",
                    "Wall-clock 加速不換取品質下降",
                    "與 quantization 等技術正交",
                ),
            ),
        ),
        core_observation=(
            "多數 LLM 輸出的 token 熵低,可由極輕量模型 (甚至 N-gram) 即時"
            "供給;只有少數關鍵 token 才必須走完整 oracle。把這個觀察"
            "操作化為樹狀 + 多階段 draft 之後,RTX 4090 上 GPT-2-L 從 150 "
            "推到 475 t/s 且分佈不變。意味著推論成本與生成文字的 entropy "
            "本身綁在一起,而非與模型大小直接成正比。"
        ),
        limitations=(
            "35% 來自 Python infrastructure,C++/CUDA 化會更快",
            "Speedup 隨 prompt 內容變化大 (2× ~ 10×)",
            "只在 762M 上驗證,真實大模型行為待驗",
            "Drafter 為同領域 fine-tuned,跨領域 align 度未知",
        ),
        future_work=(
            "T>0 sampling 可先採 multinomial CDF 再選 batch token",
            "8-bit quant 後可在消費 GPU 跑 20B → 1B → 50M → N-gram 四階段",
            "更好的 lowest-level drafter (<10µs 但勝於 N-gram)",
            "與 quantization、Flash-Attn 等技術的協同最佳化",
        ),
        figures=(
            (
                "GPT-2-L 在 RTX 4090 的 roofline (Figure 1)",
                _fig("spector2023staged", "p02-00-A-roofline-plot-for-single-query-GPT-2-L-inference-on-an.png"),
                (
                    "Batch=1 時受 memory bandwidth 限制,算力遠未飽和。",
                    "證明 small-batch 推論的瓶頸不在 FLOPs。",
                ),
            ),
            (
                "HumanEval 各 prompt 的相對加速分布 (Figure 2)",
                _fig("spector2023staged", "p04-01-Relative-performance-distribution-over-different-prob.png"),
                (
                    "(A) Greedy decoding,(B) Topk(k=50, T=1) sampling。",
                    "Speedup 在 2-10× 之間,取決於 prompt 的文本 entropy。",
                ),
            ),
            (
                "Token 來源視覺化 (Figure 3)",
                _fig("spector2023staged", "p04-02-A-visualization-of-the-origin-of-tokens-in-an-example.png"),
                (
                    "綠色 = N-gram draft2、藍色 = GPT-2 40M draft、紅色 = GPT-2-L 762M oracle。",
                    "顯示低 entropy token (空白、縮排) 多由 N-gram 供給,oracle 只處理少數關鍵 token。",
                ),
            ),
        ),
    ),
)


# ---------------------------------------------------------------------------
# 3. Xu et al. 2024 — EdgeLLM (IEEE TMC)
# ---------------------------------------------------------------------------
XU_EDGELLM = Paper(
    source="local",
    source_id="xu2024edgellm",
    title="EdgeLLM: Fast On-Device LLM Inference With Speculative Decoding",
    authors=(
        "Daliang Xu", "Wangsong Yin", "Hao Zhang", "Xin Jin",
        "Ying Zhang", "Shiyun Wei", "Mengwei Xu", "Xuanzhe Liu",
    ),
    year=2024,
    venue="IEEE Transactions on Mobile Computing 24(4)",
    abstract="在 mobile / IoT 上用 speculative decoding 突破裝置記憶體上限,三項新技巧 (寬度自適應 token tree、自適應 fallback、provisional generation pipeline) 帶來 2.9–9.3× 加速。",
    url="https://ieeexplore.ieee.org/abstract/document/10812936/",
    doi=None,
    pdf_url=None,
    summary=PaperSummary(
        language="zh-tw",
        model=MODEL_TAG,
        raw_text_chars=93_090,
        pain_points=(
            ("Mobile LLM 撞上 memory wall", (
                "10B 是 Xiaomi 10 能即時的上限",
                "超出記憶體 → MNN / llama.cpp 反覆從 disk 換入 weight",
                "推論延遲拉長 59–224×",
            )),
            ("Speculative Decoding 在 edge 有新挑戰", (
                "Token tree 增寬會壓垮資源受限的 drafter",
                "Verification 時機難判定;早 / 晚都浪費",
                "Verify 期間 draft 必須暫停,I/O 與 compute 不對稱",
            )),
            ("既有 mobile DNN engine 對 LLM 不友善", (
                "MNN / llama.cpp 走 swap 策略",
                "Disk I/O 占推論時間 95.9–98.8%",
                "Batching / pipeline 對 autoregressive 失效",
            )),
            ("壓縮 / sparsity 方法犧牲精度", (
                "Quantization 在極小裝置上仍會掉點",
                "Context sparsity 在多輪對話崩潰",
                "需要不犧牲精度的加速路線",
            )),
        ),
        research_question=(
            "如何在記憶體不足以裝載目標 LLM 的 mobile / IoT 裝置上,"
            "用 speculative decoding 兼顧記憶體上限與不損失精度的加速?"
        ),
        contributions_detailed=(
            ("一、寬度自適應 Token Tree 與批次驗證",
             "依 token / branch confidence 動態調整每分支寬度,並一次 batch 驗證整棵樹,把 oracle 呼叫降至最低。"),
            ("二、Self-Adaptive Fallback 策略",
             "結合候選分支 joint confidence 與歷史 verify 準確度,動態調整 fallback 觸發門檻。"),
            ("三、Provisional Generation Pipeline",
             "Verify 期間 drafter 不暫停,持續預生成 token 與 verify I/O 重疊,打破 cross-token 依賴。"),
            ("四、四平台 × 六模型 × 七資料集評測",
             "Jetson TX2 / Orin NX、Xiaomi 10 / 11 上跑 GPT2 / T5 / mT5 / Bart / Vicuna / LLaMA2,IoT 2.9–9.3×、手機 3.5–4.7× 加速。"),
        ),
        headline_metrics=(
            ("IoT 加速倍數", "2.9–9.3×", "Jetson TX2 / Orin NX,vs SOTA engine"),
            ("Smartphone 加速倍數", "3.5–4.7×", "Xiaomi 10 / 11"),
            ("vs 競爭性 baseline", "up to 5.6×", "其他 speculative / pipeline 框架"),
            ("LLaMA2-13B 於 Xiaomi 10", ">1 token/s", "原本完全無法即時"),
            ("Memory wall 延遲增幅 (baseline)", "59–224×", "超出記憶體預算時"),
            ("Disk I/O 在純 baseline 佔比", "95.9–98.8%", "在 swap 階段"),
        ),
        technique_table=(
            ("Target LLM (oracle)", "超出記憶體的大模型,只在 verify 時載入"),
            ("Draft LLM (resident)", "常駐記憶體的小模型,負責多數 token"),
            ("Width-adaptive token tree", "依 confidence 動態分配分支寬度"),
            ("Branch decoder", "高效生成樹狀分支,降低 drafter forward 次數"),
            ("Self-adaptive fallback", "預測 drafter 何時出錯 → 觸發 verify"),
            ("Compute-I/O pipeline", "Verify I/O 與 drafter compute 重疊"),
        ),
        method_sections=(
            ("§III-B 寬度自適應 Token Tree", (
                "每個 node 依 token confidence 決定是否擴張",
                "Branch decoder 一次出多分支降低 forward 次數",
                "整棵樹 batch 送 target LLM 一次驗證",
            )),
            ("§III-C 自適應 Fallback + §III-D Provisional Pipeline", (
                "Joint confidence + 歷史準確率決定 fallback 門檻",
                "Verify 期間 drafter 持續 provisional 生成",
                "Cross-token 依賴被 pipeline 打破,I/O 與 compute 重疊",
            )),
        ),
        evaluation_sections=(
            ("實機平台", (
                "Jetson TX2 (4 GB) / Orin NX (16 GB)",
                "Xiaomi 10 (8 GB) / Xiaomi 11",
                "PyTorch-GPU (Jetson) + llama.cpp-CPU (手機)",
            )),
            ("模型 × 資料集 × baseline", (
                "六模型:GPT2 / T5 / mT5 / Bart / Vicuna / LLaMA2",
                "七資料集:CNN/Daily、Wikitext、IWLT2017、WMT14/22、SQuAD、Parrot、TruthfulQA",
                "六 baseline:pipeline + speculative 兩大類",
            )),
        ),
        system_flow=(
            "Prompt 進入常駐 draft LLM",
            "Draft 依 confidence 長出寬度自適應 token tree",
            "Branch decoder 一次出多分支,batch 送 target",
            "Target LLM 從 disk 載入 verify 整樹",
            "Verify 期間 draft 繼續 provisional 生成",
            "Verify 結果回填,接受 / fallback / 修正下一輪",
        ),
        research_questions=(
            ("RQ1", "EdgeLLM 在 IoT / 手機上 vs SOTA engine 的整體加速?"),
            ("RQ2", "三項技巧各自的邊際貢獻 (ablation) ?"),
            ("RQ3", "在各模型 / 資料集 / 平台的穩定性?"),
            ("RQ4", "對 >10B 過去無法即時的模型能達何種吞吐?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1",
                question="整體 wall-clock 加速",
                table=(
                    ("平台", "vs MNN/llama.cpp", "vs spec baseline"),
                    ("Jetson TX2 (IoT)", "9.3×", "up to 5.6×"),
                    ("Jetson Orin NX (IoT)", "2.9×", "up to 4.1×"),
                    ("Xiaomi 10 (手機)", "4.7×", "3.2×"),
                    ("Xiaomi 11 (手機)", "3.5×", "2.8×"),
                ),
                analysis=(
                    "IoT 受 disk I/O 影響大,EdgeLLM 收益最高",
                    "手機 INT4 量化壓力小,差距收斂",
                    "完全不犧牲精度",
                ),
            ),
            RqResult(
                rq_id="RQ2",
                question="三項技巧的 ablation 貢獻",
                table=(
                    ("組合", "相對加速"),
                    ("僅 width-adaptive tree", "1.8×"),
                    ("+ self-adaptive fallback", "2.7×"),
                    ("+ provisional pipeline", "4.7× (full)"),
                ),
                analysis=(
                    "Tree 是 baseline 動力來源",
                    "Fallback 把 verify cost 壓低",
                    "Pipeline 把 I/O 隱藏進 compute",
                ),
            ),
            RqResult(
                rq_id="RQ3",
                question="跨模型 / 資料集 穩健度",
                table=(
                    ("情境", "加速範圍"),
                    ("GPT2 / Bart (小)", "2.9× ~ 5.1×"),
                    ("T5 / mT5 (encoder-decoder)", "3.4× ~ 6.8×"),
                    ("Vicuna / LLaMA2 (decoder)", "4.1× ~ 9.3×"),
                ),
                analysis=(
                    "Decoder-only 模型加速最顯著",
                    "Encoder-decoder 受 encoder 並行影響",
                    "資料集分布對 fallback 觸發影響可控",
                ),
            ),
            RqResult(
                rq_id="RQ4",
                question="超大模型在手機的可行性",
                table=(
                    ("模型 / 裝置", "原 token/s", "EdgeLLM token/s"),
                    ("LLaMA2-13B / Xiaomi 10", "≈0 (swap)", ">1"),
                    ("LLaMA2-13B / Xiaomi 11", "≈0", ">1"),
                ),
                analysis=(
                    "10B+ 模型在手機從不可即時推到可即時",
                    "突破記憶體上限的同時保留精度",
                    "為 on-device 私密 LLM 應用打開新空間",
                ),
            ),
        ),
        core_observation=(
            "Mobile LLM 推論的真正瓶頸是 disk I/O 而非算力。"
            "把多數 token 交給常駐小模型、只在不確定時動用 swap-in 的大"
            "模型驗證,並讓 verify 的 I/O 與 draft 的 compute 完全重疊,"
            "就能在不犧牲精度的前提下把 mobile 推論推到原本不可能的"
            "模型尺寸 (例如 LLaMA2-13B 在 Xiaomi 10 上即時可用)。"
        ),
        limitations=(
            "Fallback 門檻調整需歷史資料,冷啟動有適應期",
            "Branch decoder 在極長 context 下 KV cache 開銷上升",
            "需要 draft / target 同系列以維持 align 品質",
            "Provisional 生成在 verify 全錯的極端情境下浪費",
        ),
        future_work=(
            "Edge-friendly drafter 自動生成 / 壓縮流程",
            "Heterogeneous compute (CPU + GPU + NPU) 上的 pipeline 編排",
            "Dynamic offloading 與 EdgeLLM 的協同",
            "雲端 + edge 混合推論的 fallback 介面",
        ),
        figures=(
            (
                "LLM 在 mobile 上撞 memory wall (Figure 1)",
                _fig(
                    "xu2024edgellm",
                    "p01-00-The-memory-wall-hinders-LLMs-scaling-law-on-mobile-devices.png",
                ),
                (
                    "(a) 模型超過 10B 才有明顯 emergent ability(Math / NLU / Mode / GM)。",
                    "(b) 同一 LLM 越過記憶體上限後,latency 在 Jetson TX2 / Xiaomi 10 / Jetson Orin 各跳幾十倍。",
                    "結論:scaling law 在 edge 撞牆 — 需要超出記憶體仍能即時的方案。",
                ),
            ),
            (
                "Decoder-only LLM 推論架構 (Figure 2)",
                _fig(
                    "xu2024edgellm",
                    "p03-01-InferencedelaybreakdownofdifferentLLMvariantsinoneautoregres.png",
                ),
                (
                    "左:GPT-3 風格的 N 層 decoder (Masked self-attention + LayerNorm + FFN)。",
                    "右:autoregressive 推論一次生成一個 token,大量 weight 在 iter 之間反覆換入晶片 cache。",
                ),
            ),
            (
                "EdgeLLM 整體工作流 (Figure 5)",
                _fig("xu2024edgellm", "p05-03-The-workﬂow-of-EdgeLLM.png"),
                (
                    "Draft LLM (常駐記憶體) → 寬度自適應 token tree → batch 送 target LLM 驗證。",
                    "Verify 期間 draft 持續 provisional generation,I/O 與 compute 重疊。",
                ),
            ),
            (
                "EdgeLLM 演算流程的具體範例 (Figure 6)",
                _fig("xu2024edgellm", "p06-04-An-illustrative-example-of-EdgeLLM-The-ground-truth-is-the-A.png"),
                (
                    "Draft 一步生成多分支樹,每分支以 confidence 決定是否擴張。",
                    "對 ground truth『the Apollo program』展示分支接受 / fallback 軌跡。",
                ),
            ),
            (
                "Branch verification 機制 (Figure 7)",
                _fig("xu2024edgellm", "p07-05-The-illustration-of-branch-veriﬁcation.png"),
                (
                    "Target LLM 一次 forward 同時驗證整棵 token tree。",
                    "比逐分支序列化驗證減少數倍 latency。",
                ),
            ),
            (
                "Fallback 門檻消融研究 (Figure 8)",
                _fig(
                    "xu2024edgellm",
                    "p08-06-Comparison-of-different-initial-thresholds-and-updating-para.png",
                ),
                (
                    "(a) 初始 threshold 對 speedup 影響在 0.005-0.1 區間穩定 — 對 cold-start 不敏感。",
                    "(b) Update rule 的 η 參數:η=0.5 在大資料集上給出最佳 speedup。",
                ),
            ),
            (
                "Per-token 延遲 vs baselines (Figure 11)",
                _fig(
                    "xu2024edgellm",
                    "p11-08-Average-per-token-generation-latency-of-EdgeLLM-and-baseline.png",
                ),
                (
                    "跨 mT5 / T5 / Bart / GPT2 四種模型,EdgeLLM (Ours) 與 SPL / STI / SP / BLD / SI 五條 baseline 對比。",
                    "EdgeLLM 在 gpt2-wikitext 達最大 speedup (8.00→1.79 秒);在 t5-CNN_Daily 最小 (7.10→1.34)。",
                ),
            ),
            (
                "不同記憶體預算下的生成速度 (Figure 13)",
                _fig(
                    "xu2024edgellm",
                    "p13-13-Generation-speed-under-different-memory-budgets-Y--axis-Gene.png",
                ),
                (
                    "Jetson TX2 (4-5.6 GB) 與 Xiaomi 10 (4-8 GB) 上,EdgeLLM(Ours) 在所有預算下都領先 BLD / SP / STI。",
                    "右側表:能耗對比,EdgeLLM 在 LLaMA2-summarization 上達 3.2× 能耗節省。",
                ),
            ),
        ),
    ),
)


# ---------------------------------------------------------------------------
# 4. Svirschevski et al. 2024 — SpecExec (NeurIPS)
# ---------------------------------------------------------------------------
SVIRSCHEVSKI = Paper(
    source="local",
    source_id="svirschevski2024specexec",
    title="SpecExec: Massively Parallel Speculative Decoding for Interactive LLM Inference on Consumer Devices",
    authors=(
        "Ruslan Svirschevski", "Avner May", "Zhuoming Chen",
        "Beidi Chen", "Zhihao Jia", "Max Ryabinin",
    ),
    year=2024,
    venue="NeurIPS 2024",
    abstract="把 RAM / SSD offload 與 massively parallel speculative decoding 結合,讓 50B+ LLM 在消費級 GPU 上以 4–6 t/s (4-bit) 或 2–3 t/s (16-bit) 互動推論。",
    url="https://proceedings.neurips.cc/paper_files/paper/2024/hash/1d91d5689e251d27993a3c2182dddcf7-Abstract-Conference.html",
    doi=None,
    pdf_url=None,
    summary=PaperSummary(
        language="zh-tw",
        model=MODEL_TAG,
        raw_text_chars=87_521,
        pain_points=(
            ("消費級 GPU 裝不下大模型", (
                "Llama-70B、Falcon-180B 遠超單 GPU VRAM",
                "Offload 至 RAM / SSD 是唯一選項",
                "每次參數搬運成本極高",
            )),
            ("既有 speculative 多為 datacenter 設計", (
                "預設模型可整段裝入 VRAM",
                "Tree 寬度設定針對高端硬體調過",
                "消費 GPU 下 speedup 反而被 I/O 吃掉",
            )),
            ("Offload 與 speculative 沒人整合", (
                "Offload 把 batch 變便宜(I/O 攤平)",
                "Speculative 把 batch 變大(同時驗多 token)",
                "兩者天然契合但缺整合工程",
            )),
            ("Drafter 樹寬上限被 OOM 限制", (
                "Tree 太寬 → draft 自身 OOM",
                "Tree 太窄 → 接受率不夠",
                "需在 consumer 硬體下重新調參",
            )),
        ),
        research_question=(
            "在 RAM / SSD offload 是必要條件的消費級 GPU 上,"
            "speculative decoding 能把互動式大模型推論逼到多快?"
        ),
        contributions_detailed=(
            ("一、SpecExec — 大規模並行 speculative 解碼",
             "每次 target iteration 生成最多 20 token,以樹形 cache 一次驗證。"),
            ("二、Offload 與 speculative 的整合工程",
             "Offload 讓 batch 變便宜,speculative 讓 batch 變大,兩者契合度量化。"),
            ("三、消費級 GPU 上的 50B+ 互動推論",
             "Llama-70B / Falcon-180B 等 50B+ 模型在 RTX 3090 / 4090 上可互動使用。"),
            ("四、4-bit / 16-bit 兩種配置的吞吐量化",
             "4-bit:4–6 t/s;16-bit:2–3 t/s,皆完全保真。"),
        ),
        headline_metrics=(
            ("Llama-70B / RTX 4090 (4-bit)", "4–6 t/s", "原本 offload 下 <1 t/s"),
            ("Llama-70B / RTX 4090 (16-bit)", "2–3 t/s", "完整精度"),
            ("每 target iteration 接受 token", "up to 20", "前作多在 4–8"),
            ("最大實驗模型", "Falcon-180B", "在 RTX 4090 + 96 GB RAM 上互動"),
            ("Cache tree branching", "thousands", "受 RAM/SSD 頻寬上限"),
        ),
        technique_table=(
            ("Massively parallel speculative", "樹形 cache,單次 target 驗多 token"),
            ("RAM / SSD offload", "Target LLM 在 RAM/SSD,需要時 stream"),
            ("Probabilistic cache tree", "從 drafter 取最可能 K 個 continuation"),
            ("Single-pass validation", "Target 一次 forward 驗整棵樹"),
            ("4-bit quantization", "AWQ / GPTQ 4-bit 變體"),
            ("Llama / Falcon family", "代表 7B–180B 開源大模型"),
        ),
        method_sections=(
            ("SpecExec 演算法", (
                "Drafter 自回歸生成,記錄機率分佈",
                "用機率展開成寬度可變的 token tree",
                "Target 一次 forward 同時驗證整棵樹",
                "Tree depth 可達 20+,branching 達數千",
            )),
            ("Offload Stack", (
                "Weight 存 RAM 或 SSD",
                "層次化載入策略,KV cache 留 VRAM",
                "Verify batch 大時 I/O 成本被攤平",
            )),
        ),
        evaluation_sections=(
            ("硬體", (
                "RTX 3090 / 4090 消費級 GPU",
                "RAM 上限 64–128 GB",
                "可選 SSD offload (NVMe Gen4)",
            )),
            ("模型 × 量化", (
                "Llama-7B / 13B / 70B、Falcon-7B / 40B / 180B、Mistral-7B",
                "4-bit (AWQ / GPTQ) 與 16-bit 兩組",
                "比較 baseline:SpecInfer、SpecDec、純 autoregressive",
            )),
        ),
        system_flow=(
            "Drafter (常駐 VRAM) 自回歸生成 K depth 的 token tree",
            "依各路徑機率挑 top-N 形成驗證 cache tree",
            "Target LLM 從 RAM/SSD 載入並一次 forward 驗整樹",
            "依驗證結果接受最深可達 20 個 token",
            "未接受處 fallback,KV cache 更新後繼續",
        ),
        research_questions=(
            ("RQ1", "Offload + speculative 在消費 GPU 上能跑多大模型?"),
            ("RQ2", "每 target iteration 能接受多少 token?"),
            ("RQ3", "4-bit vs 16-bit 配置在吞吐 / 品質的折衷?"),
            ("RQ4", "vs SpecInfer / SpecDec 等既有方法的差距?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1",
                question="消費 GPU 上可互動的最大模型",
                table=(
                    ("模型", "GPU + RAM", "互動吞吐"),
                    ("Llama-70B (4-bit)", "RTX 4090 + 64 GB", "4–6 t/s"),
                    ("Llama-70B (16-bit)", "RTX 4090 + 128 GB", "2–3 t/s"),
                    ("Falcon-180B (4-bit)", "RTX 4090 + 96 GB", "互動可用 (低個位數 t/s)"),
                ),
                analysis=(
                    "RAM/SSD offload 把 VRAM 限制解開",
                    "消費級用戶可在家跑 70B–180B 級別模型",
                    "互動性 (>1 t/s) 是 SpecExec 帶來的關鍵",
                ),
            ),
            RqResult(
                rq_id="RQ2",
                question="每 target iteration 的接受 token 數",
                table=(
                    ("方法", "接受 token / iter"),
                    ("Autoregressive", "1"),
                    ("SpecDec (Leviathan 2022)", "≈4"),
                    ("SpecInfer (Miao 2024)", "≈8"),
                    ("SpecExec (本文)", "up to 20"),
                ),
                analysis=(
                    "大寬度 cache tree 攤平 RAM/SSD I/O",
                    "Drafter 機率排序提升 top branch 接受率",
                    "Offload 讓大 batch 變便宜,前作不適用",
                ),
            ),
            RqResult(
                rq_id="RQ3",
                question="量化配置的取捨",
                table=(
                    ("配置", "吞吐", "品質"),
                    ("16-bit (FP16)", "2–3 t/s", "原模型分佈"),
                    ("4-bit (AWQ/GPTQ)", "4–6 t/s", "AWQ 接近 FP16"),
                    ("Speculative 保真性", "兩種都完全保真", "—"),
                ),
                analysis=(
                    "4-bit 在消費 GPU 是主流配置",
                    "Speculative 維持原分佈,不受量化影響",
                    "可用 AWQ / GPTQ 等任一",
                ),
            ),
        ),
        core_observation=(
            "RAM / SSD offload 讓 batch 變便宜,而 speculative decoding 讓"
            "batch 變大,兩者結合在消費級 GPU 上把 50B+ 模型逼到互動可用"
            "區間 (>1 t/s)。意味著大模型在家跑不再只是『裝得進』的問題,"
            "而是『推得快』的問題,SpecExec 把後者顯著推前。"
        ),
        limitations=(
            "RAM 上限決定可跑模型大小,128 GB 是現實天花板",
            "SSD offload 對 NVMe Gen4 以上才有意義",
            "Drafter 仍須對齊 target,跨家系時需重新挑",
            "Tree 寬度仍依硬體微調",
        ),
        future_work=(
            "與更激進量化 (2-bit / 1.58-bit) 的協同",
            "Heterogeneous offload (NVMe + RAM + VRAM tier) 自動化",
            "Multi-GPU 消費級配置的 partition 策略",
            "Cache tree 在多輪對話中的重用",
        ),
        figures=(
            (
                "SpecExec 演算法總覽 (Figure 1)",
                _fig(
                    "svirschevski2024specexec",
                    "p17-00-A-high-level-overview-of-the-SpecExec-algorithm.png",
                ),
                (
                    "Drafter 自回歸長出寬度可變的 token tree (深度可達 20+、寬度可達數千)。",
                    "Target LLM 從 RAM/SSD 載入一次 forward 驗證整棵樹。",
                ),
            ),
            (
                "Draft size vs 接受 token 數 (Figure 3)",
                _fig(
                    "svirschevski2024specexec",
                    "p19-01-Number-of-accepted-tokens-as-a-function-of-the-draft-size-B-.png",
                ),
                (
                    "B 軸 = 樹寬度。寬度從 64 增到 4096 時接受 token 數從 ≈4 拉到 20+。",
                    "Offload 讓大寬度的 verify 變便宜,前作的 4-8 token 上限被打破。",
                ),
            ),
            (
                "Token penalty 下的接受率曲線 (Figure 4)",
                _fig(
                    "svirschevski2024specexec",
                    "p20-02-Acceptance-rate-in-generation-with-token-penalty-dont-start-.png",
                ),
                (
                    "在 token penalty 解碼下,接受率隨樹寬度上升仍維持線性。",
                    "證明 SpecExec 在抗重複等修正解碼策略下仍有效。",
                ),
            ),
        ),
    ),
)


ALL_PAPERS = (XIA, SPECTOR, XU_EDGELLM, SVIRSCHEVSKI)


def main() -> None:
    out_dir = ROOT / "exports" / _RUN_DIR_NAME
    out_dir.mkdir(parents=True, exist_ok=True)
    for paper in ALL_PAPERS:
        collection = PaperCollection(
            query=Query(
                keywords="speculative decoding LLM inference",
                sources=("local",),
                max_results=1,
            ),
            papers=(paper,),
        )
        options = ExportOptions(
            formats=("pptx",),
            out_dir=str(out_dir),
            # Language-variant filename is the explicit exception to the
            # canonical-stem rule, so the user can keep zh-tw and English
            # decks side-by-side without collision.
            filename_stem=f"{paper.bibtex_key()}-zh-tw",
            include_abstract=True,
            language="zh-tw",
            # Disable the 25-slides-per-paper cap so every curated
            # figure makes it into the deck even when the rich-tier
            # body content already consumes most of the budget.
            max_slides_per_paper=0,
        )
        written = export_collection(collection, options)
        for fmt, path in written.items():
            print(f"  - {paper.bibtex_key()} {fmt}: {path}")


if __name__ == "__main__":
    main()
