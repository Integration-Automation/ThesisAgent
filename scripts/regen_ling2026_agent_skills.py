"""Regenerate Ling et al. 2026 (Agent Skills) as a rich thesis-style deck.

Uses the LLM-as-agent flow: this Python script ships a hand-authored
``PaperSummary`` derived from reading the full 18-page PDF in-context.
No Anthropic API key required.

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
    language="en",
    model="claude-opus-4-7 (LLM-as-agent, read 18-page PDF)",
    raw_text_chars=85_406,
    pain_points=(
        (
            "Skill ecosystem is exploding",
            (
                "40,285 skills crawled from skills.sh on Feb 5, 2026",
                "18.5x growth in 20 days, bursty publication spikes",
                "OpenClaw GitHub stars surge in lockstep — attention-driven",
            ),
        ),
        (
            "Re-specifying behaviour is wasteful",
            (
                "Agents revisit similar subtasks (retrieval, codegen, edits)",
                "Without abstraction, prompts repeat and become brittle",
                "Maintenance of shared procedures fragments across copies",
            ),
        ),
        (
            "Marketplace metadata is opaque",
            (
                "Tags are sparse, inconsistent, and template-derived",
                "Hard to know what is published vs. what users actually install",
                "Quality signals and canonical skills are missing",
            ),
        ),
        (
            "Skills enable real side effects",
            (
                "Executable procedures touch sensitive data and external services",
                "Privacy reads, state-changing writes, shell execution all in scope",
                "Harm surface is larger than prompt-only interactions",
            ),
        ),
    ),
    research_question=(
        "What types of agent skills are published, how are they adopted, "
        "and what safety risks do they introduce — at marketplace scale?"
    ),
    contributions_detailed=(
        (
            "1. Large-scale corpus + growth analysis",
            "40,285 skills crawled from skills.sh with metadata and install "
            "counts; quantified 18.5x bursty growth coupled to community attention.",
        ),
        (
            "2. Length & redundancy profile",
            "Heavy-tailed token-length distribution (median 1,414) and "
            "name-based redundancy measurement flagging 46.3% of listings.",
        ),
        (
            "3. Functional taxonomy + supply-demand gap",
            "Six-major / twenty-sub taxonomy classified by Qwen2.5-32B; "
            "exposes supply-heavy SWE vs. demand-heavy retrieval/content.",
        ),
        (
            "4. Safety-risk audit (L0-L3)",
            "Worst-case rubric over every skill — 9% land at critical risk, "
            "concentrated in software engineering (14% L3).",
        ),
    ),
    headline_metrics=(
        ("Corpus size", "40,285", "skills, single-snapshot"),
        ("Growth", "18.5x", "in 20 days (2,179 -> 40,285)"),
        ("Single-day peak", "+8,857", "skills on Jan 25, 2026"),
        ("Median length", "1,414", "tokens (mean 1,895)"),
        ("Name-redundant share", "46.3%", "of listings"),
        ("Critical-risk (L3)", "9%", "of all skills"),
    ),
    technique_table=(
        ("skills.sh marketplace crawl", "Source of 40,285 skill records + install counts"),
        ("tiktoken o200k_base", "Token counting for length distribution"),
        ("BAAI/bge-m3 embeddings", "Semantic near-duplicate detection (Appendix B)"),
        ("t-SNE projection", "Visual clustering of skill embeddings"),
        ("Qwen2.5-32B-Instruct", "Taxonomy classification + L0-L3 risk audit"),
        ("GitHub GraphQL API", "OpenClaw star-history as attention proxy"),
    ),
    method_sections=(
        (
            "Data collection",
            (
                "Crawl skills.sh; capture name, repo, first_seen, install counts",
                "Persist each skill as SKILL.md plus a JSON metadata record",
                "Aggregate-only reporting; no creator-level attribution",
            ),
        ),
        (
            "Length & redundancy",
            (
                "Tokenize SKILL.md with tiktoken o200k_base",
                "Name match: lowercase + strip specials, then exact match",
                "Semantic match: bge-m3 nearest neighbour + t-SNE (Appendix)",
            ),
        ),
        (
            "Functional taxonomy",
            (
                "Six major categories x twenty sub-categories (Table 1)",
                "Qwen2.5-32B-Instruct picks one sub-category per skill",
                "Strict JSON output for reliable parsing at scale",
            ),
        ),
        (
            "Risk audit (L0-L3)",
            (
                "Worst-case interpretation rubric (Appendix E)",
                "L0 safe / L1 privacy / L2 moderate / L3 critical",
                "Same JSON contract per skill enables aggregation",
            ),
        ),
    ),
    evaluation_sections=(
        (
            "Growth signal",
            (
                "Cumulative listings vs. cumulative OpenClaw GitHub stars",
                "Identify single-day and weekly publication spikes",
                "Cross-check attention coupling between the two curves",
            ),
        ),
        (
            "Length & redundancy",
            (
                "Token-count distribution with quantile breakouts",
                "Frequency of repeated normalised names (n-times counts)",
                "Top 30 repeated names enumerated for inspection",
            ),
        ),
        (
            "Supply vs. demand",
            (
                "De-duplicated supply per category vs. mean installs",
                "Plotted across 6 major + 20 sub categories",
                "Surfaces demand-heavy and supply-heavy gaps",
            ),
        ),
        (
            "Risk distribution",
            (
                "Overall L0-L3 share across all 40,285 skills",
                "Per-category breakdown highlights SWE 14% L3",
                "Word clouds expose vocabulary per risk level",
            ),
        ),
    ),
    system_flow=(
        "Crawl skills.sh marketplace -> 40,285 records",
        "Tokenize + length-distribution analysis",
        "Name-based + semantic redundancy detection",
        "LLM taxonomy classification into 6x20 grid",
        "Pair supply (de-duped) against demand (mean installs)",
        "LLM risk audit assigns L0-L3 per skill",
        "Aggregate growth + GitHub star attention signal",
    ),
    research_questions=(
        ("RQ1", "How fast and how burstily is the skill ecosystem growing?"),
        ("RQ2", "What length and redundancy patterns characterise published skills?"),
        ("RQ3", "Where do supply and adoption diverge across functional categories?"),
        ("RQ4", "How widespread and severe are safety risks in published skills?"),
    ),
    rq_results=(
        RqResult(
            rq_id="RQ1",
            question="Growth and burstiness of the marketplace",
            table=(
                ("Period", "Skills"),
                ("Jan 16, 2026", "2,179"),
                ("Feb 5, 2026", "40,285"),
                ("Net gain in 20 days", "+38,106"),
                ("Single-day peak (Jan 25)", "+8,857"),
                ("Week of Jan 25 contribution", "47.8% of corpus"),
            ),
            analysis=(
                "18.5x corpus growth; ~15.7% average daily multiplicative rate",
                "23.2% of all new skills arrive on a single day",
                "OpenClaw GitHub stars peak at 25,432 on Jan 26 — attention spike",
            ),
        ),
        RqResult(
            rq_id="RQ2",
            question="Length distribution and listing redundancy",
            table=(
                ("Statistic", "Value"),
                ("Median length", "1,414 tokens"),
                ("Mean length", "1,895 tokens"),
                ("90th percentile", "3,935 tokens"),
                ("Maximum", "116,239 tokens"),
                ("Unique vs. redundant names", "53.7% / 46.3%"),
            ),
            analysis=(
                "Typical skill fits within standard prompt budgets",
                "Top 1% exceed 9,253 tokens — selective loading needed",
                "Pairs are the most common multiplicity at 18.7% of corpus",
            ),
        ),
        RqResult(
            rq_id="RQ3",
            question="Supply vs. demand across functional categories",
            table=(
                ("Category", "Supply %", "Mean installs"),
                ("Software Engineering", "54.7%", "~135 (supply-heavy)"),
                ("Information Retrieval", "4.8%", "463 (demand-heavy)"),
                ("Content Creation", "12.1%", "Audio/Video 266, Image 214"),
                ("Productivity Tools", "11.2%", "~140"),
                ("Data & Analytics", "10.6%", "~115"),
            ),
            analysis=(
                "Infrastructure alone is 24.0% of corpus — DevOps / setup glut",
                "Web Search has highest mean installs (1,268) at just 1.4% supply",
                "Software engineering skills compete as close substitutes",
            ),
        ),
        RqResult(
            rq_id="RQ4",
            question="Safety-risk distribution across the corpus",
            table=(
                ("Risk level", "Share", "Typical pattern"),
                ("L0 Safe", "54%", "Drafts, media outputs"),
                ("L1 Privacy", "5%", "Reads of private context"),
                ("L2 Moderate", "30%", "Writes, sends, edits"),
                ("L3 Critical", "9%", "Shell, sudo, credentials"),
                ("SWE L3 fraction", "14%", "Highest L3 of any category"),
            ),
            analysis=(
                "Nearly 40% of skills can access sensitive context or perform writes",
                "Content Creation safest at 75% L0; Productivity Tools dominated by L2",
                "Risk concentrates where skills bridge to external systems",
            ),
        ),
    ),
    core_observation=(
        "Agent skills are an emerging infrastructure layer for LLM agents — "
        "growing 18.5x in 20 days yet unevenly: software-engineering skills "
        "saturate supply, ~46% of listings are intent-level duplicates, and "
        "roughly two-fifths enable state-changing or system-level actions. "
        "Quality signals, canonical skills, and least-privilege sandboxing "
        "are the priority directions for the ecosystem."
    ),
    limitations=(
        "Single-snapshot crawl (Feb 5, 2026) of one marketplace (skills.sh)",
        "Adoption measured via public install counts, not verified executions",
        "Private enterprise / custom-stack usage is not captured",
        "Risk labels rely on Qwen2.5 worst-case interpretation, not runtime",
    ),
    future_work=(
        "Pair semantic de-duplication with quality signals to surface canonical skills",
        "Selective / modular loading of long skills to control prompt budget",
        "Demand-driven authoring tools and incentives to close supply-demand gaps",
        "Standardised sandboxing + least-privilege enforcement for L2 / L3 skills",
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
        "adopt them, and what risks they pose. To answer these questions, we "
        "conduct a large-scale, data-driven analysis of 40,285 publicly "
        "listed skills from a major marketplace. Our results show that skill "
        "publication tends to occur in short bursts that track shifts in "
        "community attention. We also find that skill content is highly "
        "concentrated in software engineering workflows, while information "
        "retrieval and content creation account for a substantial share of "
        "adoption. Beyond content trends, we uncover a pronounced "
        "supply-demand imbalance across categories, and we show that most "
        "skills remain within typical prompt budgets despite a heavy-tailed "
        "length distribution. Finally, we observe strong ecosystem "
        "homogeneity, with widespread intent-level redundancy, and we "
        "identify non-trivial safety risks, including skills that enable "
        "state-changing or system-level actions."
    ),
    url="https://arxiv.org/abs/2602.08004",
    arxiv_id="2602.08004",
    pdf_url="https://arxiv.org/pdf/2602.08004",
    summary=SUMMARY,
)


def main() -> None:
    collection = PaperCollection(
        query=Query(
            keywords="agent skills marketplace analysis",
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
        # Canonical filename — overwrites the CLI's lightweight emit
        # (one .pptx per paper, the rich one).
        filename_stem=PAPER.bibtex_key(),
        include_abstract=True,
        language="en",
    )
    written = export_collection(collection, options)
    for fmt, path in written.items():
        print(f"  - {fmt}: {path}")


if __name__ == "__main__":
    main()
