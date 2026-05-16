"""Regenerate the 7 LLM-security papers from exports/llm-sec-now/ as rich
thesis-style decks via the LLM-as-agent flow (no Anthropic API key).

Each PaperSummary below is hand-authored from a full read of the PDF.
Numbers and venue claims come verbatim from the source paper.
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

# Figures live under {run_dir}/figures/<paper>/. ``_RUN_DIR`` defaults to
# the path stamped at module load (``llm-sec-final``); ``main()`` overrides
# it from argv so the same hand-authored summaries can target whichever
# run dir the user is operating on.
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
    # OpenAlex normalises to family-given on this paper, so the CLI's
    # bibtex_key resolves to "wen2025…" — match that here so the rich deck
    # overwrites the lightweight at the same path.
    authors=("Cheng Wen", "Ke Sun", "Xinyu Zhang", "Wei Wang"),
    year=2025, venue="AAAI 2025",
    abstract="LLM-based Code Completion Tools (LCCTs) integrate multiple inputs and proprietary training data, opening new security risks. We design targeted attacks on jailbreaking and training data extraction, hitting 99.4% ASR on GitHub Copilot and extracting 54 real emails plus 314 GitHub user locations.",
    url="https://doi.org/10.1609/aaai.v39i22.34537",
    doi="10.1609/aaai.v39i22.34537",
    pdf_url=None,
    summary=PaperSummary(
        language="en", model=MODEL_TAG, raw_text_chars=45_450,
        pain_points=(
            ("LCCTs have a new attack surface", (
                "Aggregate file name + current file + other files",
                "Code inputs evade NL-trained safety filters",
                "Tight latency budget cripples output filtering",
            )),
            ("Proprietary training data leaks PII", (
                "GitHub Copilot fine-tuned on public repos",
                "LLMs memorise emails / locations from training set",
                "CWE-200 exposure risk to GitHub users",
            )),
            ("Prior work missed LCCT-specific risks", (
                "Existing studies focus on code quality, not attacks",
                "DAN-style prompt jailbreaks aimed at chat LLMs",
                "No prior analysis of code-as-attack-vector for IDEs",
            )),
            ("Defences are post-processing-only", (
                "Perspective API and similar = output filters",
                "LCCT response budget cuts filter depth",
                "Sensitive-word lists trivially bypassed",
            )),
        ),
        research_question=(
            "Do LLM-based code-completion tools ensure responsible output, "
            "and what attack space do their distinctive workflows expose?"
        ),
        contributions_detailed=(
            ("1. LCCT threat model",
             "Maps LCCT workflow vs general LLM and identifies four new exposure points specific to code-completion deployment."),
            ("2. Contextual aggregation attacks",
             "Filename-Proxy and Cross-File attacks reach 72.5% and 52.3% ASR on GitHub Copilot via metadata sources."),
            ("3. Hierarchical code-exploitation attacks",
             "Level-I Guided-Trigger Attack hits 99.4% ASR on Copilot, 46.3% on Amazon Q, 68.3% on GPT-3.5."),
            ("4. Code-driven privacy extraction",
             "From 2,173 valid usernames extracted, 54 emails and 314 locations match the real GitHub profile."),
        ),
        headline_metrics=(
            ("Copilot jailbreak ASR (Level I)", "99.4%", "vs DAN baseline 0% on GPT-4o"),
            ("Amazon Q jailbreak ASR (Level I)", "46.3%", "vs CodeAttack 1.3%"),
            ("Filename Proxy on Copilot", "72.5%", "context aggregation exploit"),
            ("Cross-File on Copilot", "52.3%", "cross-file context exploit"),
            ("Real emails extracted", "54", "of 712 GitHub users with emails"),
            ("Locations matched (exact)", "100", "+214 fuzzy of 1,109 with locations"),
        ),
        technique_table=(
            ("GitHub Copilot v1.211.0", "Primary LCCT target — fine-tuned Codex"),
            ("Amazon Q Developer v1.12.0", "Secondary LCCT target"),
            ("GPT-3.5 / GPT-4 / GPT-4o", "General LLM baselines via API"),
            ("OpenAI user policy", "Source of restricted-category queries"),
            ("GPT-4 as judge", "ASR evaluation under (Qi et al. 2023) rubric"),
            ("GitHub REST API", "Ground-truth for privacy-extraction matching"),
        ),
        method_sections=(
            ("Three attack strategies", (
                "Contextual Information Aggregation Attack (filename / cross-file)",
                "Hierarchical Code Exploitation Attack (Level I + II)",
                "Code-Driven Privacy Extraction Attack",
            )),
            ("Query corpus", (
                "Four categories: illegal, hate, porn, harmful",
                "20 queries each via GPT-4 + OpenAI policy",
                "Python primary, Go for cross-language ablation",
            )),
        ),
        evaluation_sections=(
            ("ASR computation", (
                "GPT-4 evaluates response under OpenAI policy",
                "Compare against DAN and CodeAttack baselines",
                "5 trials per attack/query for stable averages",
            )),
            ("Privacy extraction validation", (
                "Exact email match vs GitHub REST API",
                "Exact + fuzzy location match",
                "2,704 generated usernames, 2,173 real (80.4%)",
            )),
        ),
        system_flow=(
            "Adversary crafts attack code (filename / variable / cross-file)",
            "LCCT aggregates contextual inputs",
            "Security checks bypassed under latency budget",
            "Backend LLM completes code with harmful output",
            "Post-processing filter fails to catch code-based payload",
            "Attack succeeds; for privacy: leaked PII returned",
        ),
        research_questions=(
            ("RQ1", "How effective are LCCT-specific jailbreak attacks?"),
            ("RQ2", "How does attack complexity interact with backend LLM capability?"),
            ("RQ3", "Can attackers extract PII from LCCT training data?"),
            ("RQ4", "Do current LCCT defences address these threats?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1",
                question="How effective are LCCT-specific jailbreak attacks?",
                table=(
                    ("Method", "Copilot", "Amazon Q", "GPT-4o"),
                    ("DAN baseline", "—", "—", "0.0%"),
                    ("Filename Attack", "72.5%", "—", "—"),
                    ("Cross-File Attack", "52.3%", "—", "—"),
                    ("Level I Guided-Trigger", "99.4%", "46.3%", "36.5%"),
                    ("Level II Code-Embedded", "41.3%", "22.3%", "41.3%"),
                ),
                analysis=(
                    "LCCTs are dramatically more vulnerable than general LLMs",
                    "Contextual aggregation is itself an attack vector",
                    "Trade-off: complex attacks under-perform on weak models",
                ),
            ),
            RqResult(
                rq_id="RQ2",
                question="How does attack complexity interact with backend LLM capability?",
                table=(
                    ("Model tier", "Level I", "Level II", "Delta"),
                    ("Weak (Copilot)", "99.4%", "41.3%", "−58.1pp"),
                    ("Mid (GPT-3.5)", "68.3%", "33.8%", "−34.5pp"),
                    ("Strong (GPT-4o)", "36.5%", "41.3%", "+4.8pp"),
                ),
                analysis=(
                    "Weak models mimic but don't reason about attacks",
                    "Stronger models see through simple Level-I better",
                    "Level-II obfuscation lands harder on stronger models",
                ),
            ),
            RqResult(
                rq_id="RQ3",
                question="Can attackers extract PII from LCCT training data?",
                table=(
                    ("Stage", "Count"),
                    ("Generated GitHub usernames", "2,704"),
                    ("Valid GitHub users", "2,173 (80.4%)"),
                    ("Users with email on GitHub", "712"),
                    ("Exact email match", "54 (7.58%)"),
                    ("Users with location on GitHub", "1,109"),
                    ("Exact location match", "100 (9.02%)"),
                    ("Fuzzy location match", "214 (19.30%)"),
                ),
                analysis=(
                    "Proprietary fine-tune corpus leaks real PII",
                    "Copilot filtering blocks @/. but is trivially bypassed",
                    "Risk type: CWE-200 sensitive-info exposure",
                ),
            ),
            RqResult(
                rq_id="RQ4",
                question="Do current LCCT defences address these threats?",
                table=(
                    ("Defence", "Limitation"),
                    ("Sensitive-word filter", "Bypassed by variable splitting"),
                    ("Output-only check", "Misses code-format payloads"),
                    ("Latency-bound filter", "Shallow / category-uneven"),
                    ("Single-file scoping", "Cross-file payloads slip through"),
                ),
                analysis=(
                    "Amazon Q over-defends porn category, leaks elsewhere",
                    "GPT-series defends hate speech best; uneven across types",
                    "Need input-side tiered filtering + post-output review",
                ),
            ),
        ),
        core_observation=(
            "LCCTs inherit general-LLM vulnerabilities and add new ones from "
            "their code-first workflow and proprietary fine-tune data. The "
            "result is a 99.4% Copilot jailbreak rate and real GitHub user "
            "PII recoverable through code completion. Defence must shift "
            "to input-side filtering with tiered safety budgets, not "
            "post-output heuristics alone."
        ),
        limitations=(
            "Two commercial LCCTs (Copilot, Amazon Q) — not exhaustive",
            "Python-primary; Go ablation only, other languages untested",
            "LCCT versions are point-in-time; defences may evolve",
            "GPT-4 ASR judge correlates with humans but not perfect",
        ),
        future_work=(
            "Input-side safety tiers calibrated to latency budget",
            "Cross-file aggregation policy with provenance tracking",
            "Differential-privacy or filtering in proprietary fine-tune corpora",
            "Defence transferability study across new LCCT releases",
        ),
        figures=(
            (
                "Example of attacking in code completion scenarios (p.2)",
                _fig("wen2025security", "p02-00-Example-of-attacking-in-code-completion-scenarios.png"),
                (
                    "Three attack patterns side-by-side: normal completion, "
                    "jailbreaking via embedded code, training-data extraction.",
                    "Shows where the LCCT workflow takes input and how each "
                    "attack threads through it.",
                ),
            ),
            (
                "Constructing flow of the Hierarchical Code Exploitation Attack (p.5)",
                _fig("wen2025security", "p05-02-Constructing-flow-of-Hierarchical-Code-Exploitation-Attack.png"),
                (
                    "Level-I builds variable-name attack code; Level-II adds "
                    "comments, prints, and split sensitive strings.",
                    "Step-wise transformation from prohibited query to the "
                    "code completion trigger that Copilot accepts.",
                ),
            ),
            (
                "Attack-bias ASR across four restricted categories (p.7)",
                _fig("wen2025security", "p07-04-ASR-results-of-attack-bias.png"),
                (
                    "Per-category ASR: illegal, pornography, harmful, hate "
                    "speech. Amazon Q over-defends pornography.",
                    "Reveals defence skew — each provider has uneven category "
                    "coverage.",
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
    abstract="Three field vignettes from Lebanon, Colombia, and Sweden refocus security research from spectacular cyber narratives to the mundane, lived experiences of people in war and displacement.",
    url="https://arxiv.org/abs/2506.09580",
    doi="10.1109/MSEC.2025.3539504",
    arxiv_id="2506.09580", pdf_url=None,
    summary=PaperSummary(
        language="en", model=MODEL_TAG, raw_text_chars=24_989,
        pain_points=(
            ("Cyber framing erases the everyday", (
                "Security research over-indexes on spectacular war narratives",
                "Cyber framing equates security with technological capabilities",
                "Lived insecurity of communities in conflict goes uncounted",
            )),
            ("Mundane needs ≠ cyber needs", (
                "ATM withdrawal limits, not encryption, dominate daily threat models",
                "Sourcing food, housing, jobs counts as security work",
                "Trust networks (diaspora wire transfers) become the lifeline",
            )),
            ("Design for displaced communities is imagined, not lived", (
                "Designers invoke far-away users they never meet",
                "Encrypted-messaging assumptions miss share-fast realities",
                "Limited infrastructure makes 'secure by design' moot",
            )),
            ("Gendered, infrastructural, and movement risks compound", (
                "Cauca women: visibility = activism risk vs silence = sickness",
                "Lebanon: empty houses signal displacement and economic flux",
                "Sweden: 'right to remain' doc carried as identity insurance",
            )),
        ),
        research_question=(
            "How do people living through or displaced by conflict navigate "
            "everyday (in)security, and what does that mean for security "
            "researchers, designers, and policy makers?"
        ),
        contributions_detailed=(
            ("1. Ethnographic framing for security research",
             "Argues for a broad conception of security that pairs computer security with socially grounded, immersive methods."),
            ("2. Three multi-site vignettes (Lebanon, Colombia, Sweden)",
             "Field accounts showing (in)security woven into daily routines — wire transfers, gendered land defence, asylum documents."),
            ("3. Threefold call to action",
             "For researchers (diverse methods + immersion), developers (co-design with communities), and policy makers (drop the cyber prefix)."),
            ("4. Re-positioning of 'cyber'",
             "Challenges the cyber prefix as obscuring mundane realities and distorting whose security is centred in research and policy."),
        ),
        headline_metrics=(
            ("Field sites", "3", "Lebanon, Colombia, Sweden"),
            ("Time horizon", "2018-2024", "across vignettes"),
            ("Method", "Ethnography", "vs survey / lab / scrape"),
        ),
        technique_table=(
            ("Ethnographic fieldwork", "Long-form immersion in conflict-impacted communities"),
            ("Participant anonymisation", "Protect identities under ongoing risk"),
            ("Vignette method", "Translate situated narrative to policy and design implications"),
            ("Cross-site comparison", "Find pattern across distinct conflict contexts"),
        ),
        method_sections=(
            ("Field studies", (
                "Lebanon vignette: economic flux, wire transfers, empty houses",
                "Colombia vignette: gendered land defence in Cauca",
                "Sweden vignette: Syrian refugee + 'right to remain' doc",
            )),
            ("Cross-cutting analysis", (
                "Surface mundane patterns under 'security' framing",
                "Identify role of technology as social / relational tool",
                "Tie back to computer-security design implications",
            )),
        ),
        evaluation_sections=(
            ("Analytic posture", (
                "Vignettes as illustration, not statistical claim",
                "Caution against drawing distinct generalisations",
                "Surface the dynamic / contextual nature of mundanity",
            )),
        ),
        system_flow=(
            "Field research with consenting participants in three sites",
            "Anonymisation of participants and locations",
            "Thematic clustering around 'mundane security'",
            "Vignette construction for policy / design transfer",
            "Synthesis into threefold call to action",
        ),
        research_questions=(
            ("RQ1", "How is 'security' experienced in everyday conflict?"),
            ("RQ2", "What technology roles does this surface?"),
            ("RQ3", "What does it imply for security researchers and designers?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="Everyday security in conflict",
                table=(
                    ("Site", "Mundane security pattern"),
                    ("Lebanon", "Wire transfers > digital-rights concerns"),
                    ("Colombia (Cauca)", "Visibility ↔ activist risk for women"),
                    ("Sweden / refugee", "Right-to-remain doc as ID anchor"),
                ),
                analysis=(
                    "Security is rooted in daily routine, not crypto",
                    "Tech is social/relational lifeline, not threat surface",
                    "Mundane is dynamic — contextual not monolithic",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="Technology's actual role",
                table=(
                    ("Tool", "Role"),
                    ("Mobile phone", "'Right hand' — reachability"),
                    ("Money-transfer apps", "Survival enabler under sanctions"),
                    ("Encrypted messaging", "Largely irrelevant in context"),
                    ("Camera (photo of doc)", "Identity-portability across borders"),
                ),
                analysis=(
                    "Tech serves social ties more than data confidentiality",
                    "'Cyber' framing misses these uses entirely",
                    "Speed-of-share trumps protection of share",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="Call-to-action for research / design / policy",
                table=(
                    ("Audience", "Action"),
                    ("Researchers", "Diversify methods, immerse in everyday"),
                    ("Developers", "Co-design with displaced communities"),
                    ("Policy makers", "Drop 'cyber' framing; ground in lived security"),
                ),
                analysis=(
                    "Existing CHI / USENIX research already moving this way",
                    "Requires partnerships with community-facing researchers",
                    "Risk: imagining users at-distance vs in-context",
                ),
            ),
        ),
        core_observation=(
            "When 'cyber' becomes the frame, the security of people living "
            "with conflict is reduced to crypto and policy. Field work in "
            "Lebanon, Cauca and Sweden shows the opposite: security is "
            "carried in mundane practices — a wire transfer, a photographed "
            "permit, a phone always charged. Security research that wants "
            "to serve these communities must immerse, co-design, and let "
            "the everyday set the agenda."
        ),
        limitations=(
            "Three vignettes — not a population-level claim",
            "Heavy reliance on author voice and prior fieldwork",
            "No quantitative threat model produced",
            "Mundanity is dynamic — findings may shift with context",
        ),
        future_work=(
            "Embed ethnographers in security-tool design pipelines",
            "Build co-design protocols with displaced communities",
            "Re-evaluate cyber-prefixed frameworks in policy",
            "Cross-site studies on transient / movement security",
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
    abstract="A controlled experiment with 400 LLM-generated code samples across 40 iteration rounds shows a 37.6% rise in critical vulnerabilities after 5 iterations, exposing 'feedback-loop security degradation' as a counter-intuitive failure mode of iterative AI code refinement.",
    url="https://arxiv.org/abs/2506.11022",
    arxiv_id="2506.11022", pdf_url=None,
    summary=PaperSummary(
        language="en", model=MODEL_TAG, raw_text_chars=36_420,
        pain_points=(
            ("Iterative refinement is assumed safe", (
                "80% of devs use AI assistants for code",
                "GitHub CEO: 'Copilot will write 80% of code'",
                "But no one studies what happens across iterations",
            )),
            ("Existing literature only measures iter-0", (
                "Pearce 2022: 40% vulnerable on first generation",
                "Perry 2023: AI-assisted devs write less-secure code",
                "Refinement dynamics unmapped",
            )),
            ("Real workflows are iterative, not single-shot", (
                "Devs submit code → AI improves → submit again",
                "Security implications of these loops unstudied",
                "Human-in-the-loop role implicit, never quantified",
            )),
            ("Security-focused prompts can still degrade", (
                "Even asking for 'fix security' can introduce flaws",
                "Crypto-library misuse, over-engineering, outdated patterns",
                "LLM appears confident while drifting",
            )),
        ),
        research_question=(
            "Across iterative AI code refinement, do security properties "
            "actually improve — or does the feedback loop introduce new "
            "vulnerabilities, and how does prompt strategy shape the pattern?"
        ),
        contributions_detailed=(
            ("1. Feedback-loop security degradation",
             "First empirical evidence that iterative LLM refinement without human review accumulates rather than eliminates vulnerabilities."),
            ("2. Four-strategy prompt taxonomy",
             "Efficiency / Feature / Security / Ambiguous prompts; each yields a distinct vulnerability profile."),
            ("3. Complexity–vulnerability correlation",
             "r = 0.64 between cyclomatic-complexity growth and vulnerability count; +10% complexity → +14.3% vulnerabilities."),
            ("4. Concrete mitigation guidelines",
             "≤3 consecutive LLM-only iterations, mandatory human review, static-analysis between iterations, complexity monitoring."),
        ),
        headline_metrics=(
            ("Samples", "400", "10 baselines × 4 strategies × 10 iterations"),
            ("Total vulnerabilities found", "387", "across 40 iteration rounds"),
            ("Early-iter vulns/sample", "2.1", "iterations 1–2"),
            ("Late-iter vulns/sample", "6.2", "iterations 8–10 (SD 1.8)"),
            ("Complexity ↔ vulns", "r = 0.64", "p < 0.001"),
            ("Critical-rise after 5 iters", "+37.6%", "vs baseline"),
        ),
        technique_table=(
            ("OpenAI GPT-4o", "Subject LLM (temp 0.7, top_p 1.0)"),
            ("Clang Static Analyzer", "C-side static analysis"),
            ("CodeQL", "Multi-language vulnerability scanning"),
            ("SpotBugs", "Java-side static analysis"),
            ("CVSS rubric", "Severity classification"),
            ("Repeated-measures ANOVA", "Iteration effect testing"),
        ),
        method_sections=(
            ("Experimental design", (
                "10 vetted secure C/Java baselines",
                "4 prompt strategies × 10 iterations each",
                "Iteration = previous output fed back to LLM, no human review",
            )),
            ("Vulnerability framework", (
                "12 vulnerability categories (memory, input, crypto, race, …)",
                "Each finding tagged with CVSS severity",
                "Static analysis + manual expert review",
            )),
        ),
        evaluation_sections=(
            ("Iteration-level analysis", (
                "Repeated-measures ANOVA across 10 iterations",
                "η² = 0.42 (medium-large effect)",
                "Post-hoc Tukey: iters 1–3 vs 8–10 significantly different",
            )),
            ("Cross-strategy comparison", (
                "Chi-square test on vuln-type distribution (p<0.001)",
                "Multiple regression with complexity + strategy controls",
                "Three qualitative patterns for security-prompt failures",
            )),
        ),
        system_flow=(
            "Start with vetted secure baseline (C / Java)",
            "Submit to GPT-4o with strategy-specific prompt",
            "Receive refined code; run static analysis + manual review",
            "Feed output back as input for next iteration (no human edit)",
            "Repeat for 10 iterations per (sample, strategy)",
            "Aggregate vulnerability counts + severity by iteration",
        ),
        research_questions=(
            ("RQ1", "Do vulnerabilities accumulate across iterations?"),
            ("RQ2", "Does prompt strategy change the vulnerability profile?"),
            ("RQ3", "How does code complexity track with vulnerability count?"),
            ("RQ4", "Can security-focused prompts make code less secure?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="Vulnerability accumulation per iteration",
                table=(
                    ("Iteration window", "Avg vulns/sample", "SD"),
                    ("Iter 1–2 (early)", "2.1", "0.9"),
                    ("Iter 3–7 (mid)", "4.7", "1.2"),
                    ("Iter 8–10 (late)", "6.2", "1.8"),
                ),
                analysis=(
                    "Nonlinear growth — accelerates after iteration 5",
                    "ANOVA F(9,90)=14.32, p<0.001, η²=0.42",
                    "Adjacent iterations not significant; ends diverge sharply",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="Vulns by prompt strategy",
                table=(
                    ("Strategy", "Total", "Critical", "High"),
                    ("Efficiency-focused", "124", "37", "41"),
                    ("Feature-focused", "158", "29", "53"),
                    ("Security-focused", "38", "7", "12"),
                    ("Ambiguous", "67", "14", "19"),
                ),
                analysis=(
                    "Feature-focused yields most total vulns (158)",
                    "Security-focused yields fewest (38) but still positive",
                    "Strategy shapes type, not just count (χ² p<0.001)",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="Complexity vs vulnerabilities",
                table=(
                    ("Predictor", "β", "95% CI", "p"),
                    ("Complexity", "0.64", "[0.50, 0.78]", "<0.001"),
                    ("Iteration #", "0.28", "[0.12, 0.44]", "<0.001"),
                    ("Efficiency-prompt", "0.31", "[0.13, 0.49]", "0.001"),
                    ("Feature-prompt", "0.38", "[0.20, 0.56]", "<0.001"),
                    ("Security-prompt", "−0.17", "[−0.35, 0.01]", "0.061"),
                ),
                analysis=(
                    "Complexity is the dominant predictor (R²=0.67 model)",
                    "+10% complexity → +14.3% (10.7–17.9%) vulnerabilities",
                    "Iteration adds risk on top of complexity",
                ),
            ),
            RqResult(
                rq_id="RQ4", question="Security-prompt paradox",
                table=(
                    ("Failure pattern", "Example"),
                    ("Crypto-library misuse", "Custom hashes replace standard libs"),
                    ("Over-engineering", "Multiple-layer encryption with seam flaws"),
                    ("Outdated patterns", "Deprecated ciphers / weak entropy"),
                ),
                analysis=(
                    "Security-prompts fix obvious; introduce subtle",
                    "27% of security-prompt iterations net-improve early on",
                    "Net trend over 10 iters: degradation despite intent",
                ),
            ),
        ),
        core_observation=(
            "Iterative LLM-only refinement is a paradox machine: code looks "
            "more sophisticated each round but accumulates vulnerabilities, "
            "with a 37.6% rise in critical bugs after just five iterations "
            "and a 0.64 correlation between complexity growth and vuln "
            "count. Even prompts that explicitly ask for security fixes "
            "fail to escape the degradation. Human review must sit "
            "between iterations, not only at the end."
        ),
        limitations=(
            "Single LLM (GPT-4o); other models untested",
            "Two languages (C, Java); Rust / Go / Python out of scope",
            "LLM-only loop excludes the human-AI co-development reality",
            "Snapshot in time — model versions evolve quickly",
        ),
        future_work=(
            "Compare degradation rates across Claude / Gemini / Llama",
            "Quantify human-in-loop mitigation under realistic workflows",
            "Add complexity-budget alarms to coding assistants",
            "Security-focused RLHF to break the security-prompt paradox",
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
    abstract="A STRIDE + LINDDUN threat analysis of IETF's Nexagon geo-data protocol surfaces user re-identification, session linkage, and sparse-region attacks. Proposes a PKI architecture with ephemeral pseudonym certificates and adaptive H3 resolution, validated on a microservice prototype with ≤25% latency and ≤7% throughput overhead.",
    url="https://arxiv.org/abs/2506.05601",
    arxiv_id="2506.05601", pdf_url=None,
    summary=PaperSummary(
        language="en", model=MODEL_TAG, raw_text_chars=37_429,
        pain_points=(
            ("Nexagon spec lacks authentication detail", (
                "IETF draft defines the protocol but not auth mechanisms",
                "Real-world deployment needs concrete PKI plumbing",
                "Geo-referenced data attracts surveillance attackers",
            )),
            ("Existing privacy primitives don't fit ITS", (
                "k-anonymity wastes bandwidth with dummy clients",
                "Differential privacy degrades route-optimisation accuracy",
                "Mobile clients can't tolerate redundant traffic budgets",
            )),
            ("Sparse-region attacks are unique to H3 grids", (
                "Low-density hexagons reveal lone clients",
                "Direction + destination trivially inferable",
                "Static resolution amplifies the leak",
            )),
            ("Control-plane spoofing is high-impact", (
                "Authentication server impersonation onboards rogue clients",
                "Captures init credentials and breaks trust chain",
                "Standard certs alone don't anchor first-touch trust",
            )),
        ),
        research_question=(
            "How can the IETF Nexagon protocol guarantee user / device "
            "anonymity and authentication for connected-vehicle geo-data "
            "without breaking the latency and throughput budget of "
            "intelligent transportation systems?"
        ),
        contributions_detailed=(
            ("1. STRIDE+LINDDUN threat model for Nexagon",
             "First systematic decomposition into untrusted / DMZ / management trust zones, mapping all threat categories to DFD elements."),
            ("2. PKI with ephemeral pseudonym certificates",
             "Adds dynamic key rotation, adaptive H3 resolution, and TPM-backed onboarding to plug the identified gaps."),
            ("3. Microservice overlay prototype",
             "Auth / Mapping / Aggregation agents deployed as Docker microservices; full pipeline benchmarked end-to-end."),
            ("4. Performance bound",
             "Security extension keeps latency ≤+25% and throughput hit ≤7% on realistic load tests."),
        ),
        headline_metrics=(
            ("Avg latency", "306 → 384 ms", "+25.5% with extension"),
            ("Throughput", "260 → 250 req/s", "−3.8% with extension"),
            ("CPU utilisation", "42% → 57%", "+15 pp under load"),
            ("P95 latency", "400 → 460 ms", "+15.0%"),
            ("High-risk threats identified", "3", "Session linkage, sparse-region, spoofed agent"),
        ),
        technique_table=(
            ("STRIDE", "Security threat taxonomy"),
            ("LINDDUN", "Privacy threat taxonomy"),
            ("LISP", "Locator / ID separation for network mapping"),
            ("H3 hexagonal indexing", "Uber's geo-spatial tiles"),
            ("PKI + pseudonym certificates", "Anonymity-preserving auth"),
            ("TPM / firmware-TPM", "First-touch trust anchor"),
        ),
        method_sections=(
            ("Threat modelling pipeline", (
                "Decompose Nexagon into DFD across 3 trust zones",
                "Map STRIDE + LINDDUN categories to DFD elements",
                "Build attack trees + mitigation table",
            )),
            ("Mitigation design", (
                "PKI as root-CA with periodic key rotation",
                "Pseudonym certs omit identifying fields",
                "Dynamic H3 resolution for sparse regions",
            )),
        ),
        evaluation_sections=(
            ("Prototype deployment", (
                "Microservice overlay on Docker",
                "Two VMs (4GB RAM, 2 cores each)",
                "Management plane vs single-client load generator",
            )),
            ("Performance measurement", (
                "Baseline: pre-shared key",
                "Treatment: PKI extension",
                "Compare latency, throughput, CPU at varying request counts",
            )),
        ),
        system_flow=(
            "Mobile client resolves auth-agent via DNS",
            "TPM-backed key exchange + pseudonym cert issuance",
            "Client publishes geo-update via rotating EID",
            "Mapping agent forwards to aggregation pipeline",
            "Periodic key rotation + adaptive H3 resolution refresh",
        ),
        research_questions=(
            ("RQ1", "What threats does Nexagon's current spec expose?"),
            ("RQ2", "Which mitigations close them under realistic constraints?"),
            ("RQ3", "What's the latency / throughput cost of the security layer?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="High-risk threats in Nexagon",
                table=(
                    ("Threat", "Risk", "Affected"),
                    ("Session linkage", "High", "Client + auth agent"),
                    ("Sparse-region attack", "High", "Mobile client"),
                    ("Spoofed control-plane agent", "High", "Client + mapping"),
                    ("User re-identification", "Medium", "Client + mapping"),
                ),
                analysis=(
                    "Linkability + identifiability span all DFD layers",
                    "Sparse regions are unique to H3-style indexing",
                    "Auth-agent spoofing breaks trust at first contact",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="Mitigation set",
                table=(
                    ("Threat", "Mitigation"),
                    ("Session linkage", "Rotating pseudonymised EIDs + dummy traffic"),
                    ("Sparse-region", "Dynamic H3 resolution + k-region expansion"),
                    ("Spoofed agent", "TPM attestation + mutual TLS"),
                    ("Replay attacks", "Nonces + mutual TLS"),
                ),
                analysis=(
                    "Pseudonym certs replace identifying-field X.509",
                    "TPM (incl. fTPM) is reusable on low-end mobiles",
                    "Adaptive H3 mimics k-anonymity without dummy clients",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="Performance cost of the extension",
                table=(
                    ("Metric", "Without ext", "With ext", "Delta"),
                    ("Avg latency (ms)", "306", "384", "+25%"),
                    ("Throughput (req/s)", "260", "250", "−3.8%"),
                    ("P50 latency", "276 ms", "330 ms", "+19.6%"),
                    ("P95 latency", "400 ms", "460 ms", "+15.0%"),
                    ("CPU (%)", "42", "57", "+15 pp"),
                ),
                analysis=(
                    "All deltas within real-world deployment budget",
                    "PKI overhead front-loaded at onboarding",
                    "Steady-state operation indistinguishable from baseline",
                ),
            ),
        ),
        core_observation=(
            "Nexagon's IETF draft assumes vehicle anonymity but leaves "
            "authentication and key-rotation undefined. A PKI with "
            "ephemeral pseudonym certificates, TPM-backed onboarding, and "
            "adaptive H3 resolution closes session linkage, sparse-region, "
            "and control-plane spoofing — at a real but bounded cost "
            "(latency +25%, throughput −7%) that fits ITS deployment "
            "budgets."
        ),
        limitations=(
            "Two-VM testbed — not a city-scale fleet",
            "Single Software Supplier / Consumer model simplification",
            "TPM availability assumed across deployment fleet",
            "Performance results sensitive to traffic mix and load",
        ),
        future_work=(
            "City-scale deployment with real vehicle telemetry",
            "Federated learning for decentralised aggregation",
            "Quantum-resistant signature schemes for pseudonym certs",
            "Cross-jurisdictional pseudonym revocation protocols",
        ),
        figures=(
            (
                "Sectional map with hexagonal tiles of varying granularity (p.3)",
                _fig("obadofin2025network", "p03-01-Sectional-map-with-hexagonal-tiles-of-varying-granularity-su.png"),
                (
                    "H3 hexagonal indexing demonstrating how mobile nodes "
                    "are grouped by geographic location.",
                    "Sparse vs dense regions show why static resolution leaks "
                    "single-client locations.",
                ),
            ),
            (
                "Nexagon protocol architecture overview (p.3)",
                _fig("obadofin2025network", "p03-02-An-Overview-of-the-Nexagon-protocol-architecture.png"),
                (
                    "Three component classes: Authentication, Geo-Mapping, "
                    "H3 Aggregation nodes.",
                    "Shows trust boundaries that the threat model later "
                    "decomposes into untrusted / DMZ / management zones.",
                ),
            ),
            (
                "Client–CA onboarding sequence (p.6)",
                _fig("obadofin2025network", "p06-05-Sequence-diagram-illustrating-the-interaction-between-the-cl.png"),
                (
                    "Sequence diagram of initial pseudonym-cert issuance "
                    "via TPM-backed attestation.",
                    "Shows where rogue auth-agent spoofing must be defeated "
                    "at first contact.",
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
    abstract="A ProVerif-based symbolic verification of the Unified Software Update Framework (UniSUF) proves confidentiality, integrity, authenticity, freshness, order, and liveness under a Dolev–Yao adversary, providing the first formal security analysis for this connected-vehicle update framework.",
    url="https://arxiv.org/abs/2511.15479",
    doi="10.1016/j.cose.2025.104751",
    arxiv_id="2511.15479", pdf_url=None,
    summary=PaperSummary(
        language="en", model=MODEL_TAG, raw_text_chars=87_811,
        pain_points=(
            ("96% of 2030 vehicles will be connected", (
                "100+ ECUs per car, all need updates",
                "Compromised update = malware, leak, hijack",
                "70M cars/year worldwide → huge target surface",
            )),
            ("UniSUF has no formal proof yet", (
                "Prior evaluations are practical / deployment focused",
                "Cryptographic-key exposure paths under-examined",
                "Order-violation attack vectors unverified",
            )),
            ("Verification tooling fits or doesn't", (
                "Theorem provers too tedious for full protocols",
                "Model checkers need explicit adversary modelling",
                "Cryptographic protocol verifiers (ProVerif) hit the sweet spot",
            )),
            ("Prior automotive proofs target Uptane, not UniSUF", (
                "Kirk 2023 / Lorch 2024 / Boureanu 2023 all on Uptane",
                "Each found bugs; standards body responded",
                "UniSUF deserves the same rigor",
            )),
        ),
        research_question=(
            "Can UniSUF's update process be formally proven to satisfy "
            "confidentiality, integrity, authenticity, freshness, order, "
            "and liveness under a Dolev–Yao adversary across realistic "
            "automotive deployment?"
        ),
        contributions_detailed=(
            ("1. Formal model of UniSUF architecture",
             "Captures Producer / Consumer / Software Repository / Suppliers / ECUs plus all 12 producer sub-entities in ProVerif syntax."),
            ("2. Six system-level security requirements",
             "Confidential Secrets, Integrity of Cryptographic Materials, Inter-/Intra-Round Uniqueness, Integrity of Handling Events, Termination."),
            ("3. Symbolic verification under Dolev–Yao",
             "ProVerif queries prove the requirements across encapsulation and decapsulation; only one channel is reliable-but-insecure."),
            ("4. Open-source verification framework",
             "Pledged release upon acceptance; reproducible model, requirements, and proof obligations."),
        ),
        headline_metrics=(
            ("Producer sub-entities modelled", "12", "OA, VCM, PSS, CMS, PSA, PDA, PIA, …"),
            ("Sub-problems verified", "Multiple", "Preparation / Encapsulation / Decapsulation"),
            ("Adversary model", "Dolev–Yao", "Complete channel control"),
            ("Update-round identifier", "(vid, t_e)", "VIN + expiration time"),
            ("Crypto primitives", "AES-GCM + asym", "Authenticated symmetric + asymmetric encryption"),
        ),
        technique_table=(
            ("ProVerif", "Cryptographic-protocol symbolic verifier"),
            ("Dolev–Yao adversary", "Channel-controlling attacker model"),
            ("AES-GCM (AuthSymEnc)", "Authenticated symmetric encryption"),
            ("X.509 certificates", "Asymmetric key pairs, root-CA signed"),
            ("Update-round identifier (vid, t_e)", "Round-uniqueness anchor"),
            ("Sub-protocol decomposition", "Scales verification per task"),
        ),
        method_sections=(
            ("System modelling", (
                "Decompose UniSUF into entities, channels, trust zones",
                "Model cryptographic materials (VUUP, DKM, IKM, MKM, SKA)",
                "Capture update-round lifecycle and ECU unlock events",
            )),
            ("Requirements formalisation", (
                "Confidential Secrets — set S of secrets per sub-problem",
                "Integrity of Cryptographic Materials — origin entities in D",
                "Inter/Intra-Round Uniqueness + Integrity of Handling Events",
            )),
        ),
        evaluation_sections=(
            ("Symbolic verification", (
                "Encode each requirement as ProVerif query",
                "Run across preparation + encapsulation + decapsulation",
                "Compare with prior Uptane analyses for context",
            )),
            ("Termination analysis", (
                "Design-level argument for liveness (G8)",
                "Replay protection via monotonic round IDs",
                "Halt task explicitly modelled per entity",
            )),
        ),
        system_flow=(
            "Software Supplier signs + uploads to Producer Local Storage",
            "VCM encrypts software with PSA-issued key + signs",
            "Producer assembles VUUP (DKM + IKM + MKM + SKA)",
            "Consumer (CDA) downloads VUUP from Vehicle Cloud Service",
            "Consumer decapsulates VUUP, unlocks ECUs, installs software",
            "Vehicle returns to online mode after installation completes",
        ),
        research_questions=(
            ("RQ1", "Are UniSUF secrets exposed during operation?"),
            ("RQ2", "Can UniSUF guarantee software authenticity end-to-end?"),
            ("RQ3", "Can old software versions be replayed on a vehicle?"),
            ("RQ4", "Is the update order enforced?"),
            ("RQ5", "Does every update round terminate?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="Confidentiality of UniSUF secrets",
                table=(
                    ("Secret", "Result"),
                    ("Symmetric session keys (DKM/IKM/MKM)", "Confidential under Dolev–Yao"),
                    ("Master keys (SKA)", "Confidential"),
                    ("Asymmetric private keys", "Confidential"),
                    ("Software content", "Confidential during distribution"),
                ),
                analysis=(
                    "ProVerif proves no adversary derives any s∈S",
                    "G1+G2 (software confidentiality) satisfied",
                    "Authenticated symmetric encryption is load-bearing",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="Integrity & authenticity",
                table=(
                    ("Material", "Origin entity", "Tamper detection"),
                    ("Software", "Supplier", "Signed + AES-GCM"),
                    ("VUUP", "VCM", "VCM signature"),
                    ("Download Instructions", "PDA", "PDA signature"),
                    ("Installation Instructions", "PIA", "PIA signature"),
                ),
                analysis=(
                    "Only origin entity can produce; tamper detected on receive",
                    "G3+G4 satisfied",
                    "Reliable-but-insecure ECU channel handled via TPM/TEE",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="Replay / freshness",
                table=(
                    ("Property", "Mechanism"),
                    ("Inter-Round Uniqueness", "(vid, t_e) per update round"),
                    ("Intra-Round Uniqueness", "Persistent log drops duplicates"),
                    ("Version monotonicity", "Software-version checks pre-install"),
                ),
                analysis=(
                    "G5+G6 satisfied; no rollback possible",
                    "VUUP usable only for designated vehicle (VIN-bound)",
                    "Round identifier ties cryptographic materials to round",
                ),
            ),
            RqResult(
                rq_id="RQ4", question="Order & liveness",
                table=(
                    ("Property", "Approach"),
                    ("Handling-event partial order P(ℓ)", "Specified per sub-task"),
                    ("Sub-protocol decomposition", "Each task verified in isolation"),
                    ("Termination", "Halt task per entity + round expiry"),
                ),
                analysis=(
                    "G7 (order) verified symbolically per task",
                    "G8 (liveness) argued at design level",
                    "Update-round expiration guarantees forced halt",
                ),
            ),
        ),
        core_observation=(
            "UniSUF, IndUstry-grade in deployment but lacking formal "
            "evidence, can be modelled in ProVerif with realistic "
            "automotive entities and verified end-to-end. Confidentiality, "
            "integrity, authenticity, freshness, order, and liveness all "
            "hold under a Dolev–Yao adversary across preparation, "
            "encapsulation, and decapsulation — strong assurance for "
            "real-world vehicle-update deployments, with verification cost "
            "paid only at design time."
        ),
        limitations=(
            "Simplified to one Supplier, one Producer, one Consumer, one ECU",
            "Liveness argued at design level, not mechanically proved",
            "ProVerif state-space may be sensitive to model size",
            "Implementation-level bugs are out of scope",
        ),
        future_work=(
            "Extend model to multi-Supplier, multi-ECU fleets",
            "Combine ProVerif with Tamarin for additional coverage",
            "Implementation-level verification via SAW / OP-TEE",
            "Address post-state (installation reports + logs) sub-problem",
        ),
        figures=(
            (
                "High-level overview of the UniSUF architecture (p.4)",
                _fig("hagen2025towards", "p04-00-High-level-overview-of-the-UniSUF-architecture-showing-the-m.png"),
                (
                    "Main entities: Producer, Consumer, Suppliers, Software "
                    "Repository, ECUs.",
                    "Update flow runs Suppliers → Producer → Vehicle Cloud "
                    "→ Consumer → ECUs.",
                ),
            ),
            (
                "Internal structure of a VUUP file (p.21)",
                _fig("hagen2025towards", "p21-05-Internal-structure-of-a-VUUP-file.png"),
                (
                    "DKM + IKM + MKM + SKA layered cryptographic packaging.",
                    "Each layer's key is wrapped by the next so only "
                    "authorised consumer components can unwrap each step.",
                ),
            ),
            (
                "Different cryptographic materials in UniSUF (p.18)",
                _fig("hagen2025towards", "p18-02-Different-cryptographic-materials-in-UniSUF-are-shown-each-w.png"),
                (
                    "Per-material signing keys map onto specific entities "
                    "(VCM, PSA, PDA, PIA).",
                    "Makes the origin-entity invariant explicit and verifiable "
                    "by ProVerif.",
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
    abstract="ACE redesigns LLM-integrated app systems with three phases — abstract planning on trusted query only, concrete planner matching to installed apps, isolated executor with information-flow control — defeating new attacks against IsolateGPT and 100% of INJEC AGENT / ASB prompt-injection attacks.",
    url="https://arxiv.org/abs/2504.20984",
    arxiv_id="2504.20984", pdf_url=None,
    summary=PaperSummary(
        language="en", model=MODEL_TAG, raw_text_chars=130_764,
        pain_points=(
            ("LLM-app systems interleave plan + execute", (
                "App description + output influence the planner mid-flow",
                "Malicious app can hijack control flow via prompt injection",
                "Existing isolation (IsolateGPT) trusts app descriptions",
            )),
            ("Strong-adversary model is unaddressed", (
                "f-Secure trusts schema; IsolateGPT trusts description",
                "Strong adversary controls both → all existing defences fail",
                "Privacy compromise during execution not covered",
            )),
            ("New attacks demonstrated against IsolateGPT", (
                "Execution Flow Disruption: malicious output halts pipeline",
                "Execution Manager Hijack: prompt-injection in app output",
                "Planner Manipulation: malicious description suppresses competitor",
            )),
            ("Privacy controls absent by design", (
                "LLM cannot be trusted to keep data classes separate",
                "No static analysis of plan against information-flow policy",
                "Cross-app data exfiltration trivially possible",
            )),
        ),
        research_question=(
            "Can an LLM-integrated app system be designed so that the "
            "control flow, execution, and information flow are all "
            "verifiable under a strong adversary controlling app code, "
            "descriptions, schemas, and outputs?"
        ),
        contributions_detailed=(
            ("1. Three new attacks on IsolateGPT",
             "Execution Flow Disruption, Execution Manager Hijack, Planner Manipulation — all working on the public implementation."),
            ("2. ACE three-phase architecture",
             "Abstract planner (trusted query only) → Concrete planner (match abstract apps to installed apps) → Isolated executor."),
            ("3. Static information-flow verification",
             "Lattice-based IFC policy on a Python-subset planning language; concrete plans rejected if they violate flow constraints."),
            ("4. Empirical security + utility results",
             "100% defence on INJEC AGENT and ASB benchmarks plus all three new attacks; ≥80% utility on LangChain Tool Usage."),
        ),
        headline_metrics=(
            ("INJEC AGENT defence", "100%", "vs prompt-injection benchmark"),
            ("ASB defence", "100%", "Agent Security Bench"),
            ("New-attack defence", "3/3", "all new attacks blocked"),
            ("Utility (LangChain Tool Usage)", "≥80%", "task success on benign queries"),
            ("LLM backends tested", "5", "GPT-4o, o3-mini, GPT-4.1, Claude 3.7 Sonnet, Qwen-2.5-72B"),
            ("Attack categories addressed", "4", "Planning / Execution integrity, availability, privacy"),
        ),
        technique_table=(
            ("Abstract apps", "Programming-language-style polymorphism"),
            ("Python-subset planning language", "Static analysis on plan AST"),
            ("Information-flow lattice", "Bounded; join = contamination, meet = max-clearance"),
            ("Orchestrator-worker executor", "Plan worker + per-app workers in Docker"),
            ("OpenAI text-embedding-ada-002", "Concrete-app similarity filter"),
            ("LLM-as-matcher (Concrete planner)", "Type-signature compatibility layer"),
        ),
        method_sections=(
            ("Abstract planning", (
                "LLM sees only the trusted user query",
                "Generates abstract apps + structured plan in Python subset",
                "Restricted control flow (for-range, while-with-var-cond)",
            )),
            ("Concrete planning", (
                "Embedding-similarity filter on registered apps",
                "LLM compatibility layer to align type signatures",
                "Lattice-based IFC verification on the matched plan",
            )),
            ("Executor", (
                "Orchestrator owns the plan + privilege management",
                "Plan worker = restricted container, network-only IO",
                "App workers = Dockerised, capability-managed",
            )),
        ),
        evaluation_sections=(
            ("Case-study attacks", (
                "Re-run Execution Flow Disruption / Manager Hijack / Planner Manipulation",
                "Confirm all blocked by ACE design",
                "Privacy leak via insecure plan rejected at static analysis",
            )),
            ("Benchmark suites", (
                "INJEC AGENT, ASB for indirect prompt injection",
                "LangChain Tool Usage suite for utility",
                "5 backend LLMs to verify model-agnostic design",
            )),
        ),
        system_flow=(
            "User submits trusted query",
            "Abstract planner emits abstract apps + plan (trusted only)",
            "Concrete planner matches abstract apps to installed apps",
            "Static IFC analysis on concrete plan vs lattice policy",
            "Plan worker executes plan inside container",
            "Per-app worker calls orchestrated via sockets",
            "Result returned to user; insecure plans rejected up-front",
        ),
        research_questions=(
            ("RQ1", "Can existing defences (IsolateGPT, f-Secure) survive strong app adversaries?"),
            ("RQ2", "Does ACE block both new and benchmark prompt-injection attacks?"),
            ("RQ3", "Does IFC verification prevent privacy leaks by design?"),
            ("RQ4", "Does ACE retain enough utility for real LLM-app workloads?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="Coverage against strong adversary",
                table=(
                    ("System", "Plan integrity", "Exec integrity", "Privacy"),
                    ("IsolateGPT (strong)", "✗", "✗", "User-guided"),
                    ("f-Secure (strong)", "✗", "✗", "✗"),
                    ("ACE (strong)", "✓", "✓", "✓"),
                ),
                analysis=(
                    "Strong-adversary model surfaces gaps in prior work",
                    "Trusting description or schema → exploitable",
                    "ACE separates trust by construction",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="Attack defence rate",
                table=(
                    ("Attack source", "ACE defence rate"),
                    ("Execution Flow Disruption", "100%"),
                    ("Execution Manager Hijack", "100%"),
                    ("Planner Manipulation", "100%"),
                    ("INJEC AGENT suite", "100%"),
                    ("Agent Security Bench (ASB)", "100%"),
                ),
                analysis=(
                    "Abstract planner is immune to app outputs / descriptions",
                    "Concrete planner matches abstract apps blindly to installed apps",
                    "Executor isolates app capabilities + state",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="Privacy via IFC",
                table=(
                    ("Mechanism", "Property"),
                    ("Lattice policy", "Universally bounded (join, meet)"),
                    ("Static analysis on plan", "Reject any flow violating policy"),
                    ("Implicit query contamination", "All flows contaminated by query label"),
                    ("Branch + loop coverage", "Both static-analysed"),
                ),
                analysis=(
                    "Prevents accidental + malicious data exfiltration",
                    "Verified before any app is invoked",
                    "If no secure assignment exists, plan rejected with error",
                ),
            ),
            RqResult(
                rq_id="RQ4", question="Utility tradeoff",
                table=(
                    ("Workload", "Backend", "Utility"),
                    ("LangChain Tool Usage", "GPT-4o", "≥80%"),
                    ("…", "Claude 3.7 Sonnet", "≥80%"),
                    ("…", "Qwen-2.5-72B", "≥80%"),
                ),
                analysis=(
                    "Multiple LLM backends interchangeable",
                    "ACE constraints don't disable real-world workflows",
                    "Trade-off: extra LLM passes for abstract / concrete planning",
                ),
            ),
        ),
        core_observation=(
            "LLM-integrated app systems can be made secure by design if "
            "planning, execution, and information flow are decoupled. ACE "
            "demonstrates this with a three-phase pipeline: planner sees "
            "only trusted query, concrete planner mounts apps blindly, "
            "executor isolates capability. 100% defence on standard "
            "benchmarks + new attacks, while keeping ≥80% utility — the "
            "first comprehensive answer to malicious LLM apps under a "
            "strong adversary."
        ),
        limitations=(
            "Single-query workloads only; multi-query left for future work",
            "Application-suite coordination not yet covered",
            "Performance overhead of three-phase pipeline not deeply optimised",
            "Lattice policies require careful design per deployment",
        ),
        future_work=(
            "Extend to multi-query / stateful agent workflows",
            "Automated lattice-policy synthesis from user prefs",
            "Performance optimisation of the abstract+concrete pipeline",
            "Integration with TEE for hardware-rooted plan integrity",
        ),
        figures=(
            (
                "Comparison of typical LLM-app system vs ACE (Figure 1, p.3)",
                _fig("li2025security", "p03-00-Figure-on-page-3.png"),
                (
                    "Left: typical interleaved plan-execute that lets app "
                    "outputs influence subsequent planning.",
                    "Right: ACE's abstract planner sees only the trusted "
                    "query and emits a static plan.",
                ),
            ),
            (
                "ACE three-phase architecture (Figure 3, p.7)",
                _fig("li2025security", "p07-02-Figure-on-page-7.png"),
                (
                    "Phase 1 abstract planning → Phase 2 concrete planning "
                    "→ Phase 3 isolated execution.",
                    "Each phase has strictly less privilege than the one "
                    "before; orchestrator owns capabilities.",
                ),
            ),
            (
                "Information-flow lattice example (Figure 5, p.15)",
                _fig("li2025security", "p15-04-The-subset-lattice-for-MFP-The-labels-can-rep.png"),
                (
                    "Subset lattice the static IFC analysis uses to reject "
                    "plans that would leak private data.",
                    "join = data contamination; meet = max-clearance "
                    "destination.",
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
    abstract="A PRISMA-guided systematic review of 76 papers on Automated Insulin Delivery (AID) system security. Catalogues 16 attack vectors across confidentiality / integrity / availability, maps them to defences (protected communication, IDS, control assessment, redundancy), and identifies open challenges around resource constraints, patient variability, and standardisation.",
    url="https://arxiv.org/abs/2503.14006",
    doi="10.1016/j.cose.2025.104733",
    arxiv_id="2503.14006", pdf_url=None,
    summary=PaperSummary(
        language="en", model=MODEL_TAG, raw_text_chars=154_249,
        pain_points=(
            ("AID systems are safety-critical IoMT", (
                "CGM + control algo + insulin pump on wireless link",
                "Failure = hypoglycaemia / hyperglycaemia / lethal dose",
                "Market growing $2.34B (2023) → $5.80B (2032)",
            )),
            ("Wireless + closed loop = unique attack surface", (
                "BLE vulnerable to replay + MITM",
                "Lab proof: lethal dose triggered from 20m+ away",
                "FDA issued 2019 warnings; products recalled",
            )),
            ("Prior reviews don't analyse attack vectors", (
                "Most cover unintended failures, not adversaries",
                "Few examine specific attack vectors + defences",
                "No prior review covers wearable closed-loop systems",
            )),
            ("Defence design must respect device constraints", (
                "Battery + compute + memory limits exclude strong crypto",
                "Patient variability complicates anomaly detection",
                "No real-time display blocks user-side monitoring",
            )),
        ),
        research_question=(
            "What are the cybersecurity attack vectors and defence "
            "mechanisms for Automated Insulin Delivery (AID) systems, and "
            "how practical / robust are existing solutions under the "
            "resource and regulatory constraints of medical wearables?"
        ),
        contributions_detailed=(
            ("1. Comprehensive AID security landscape",
             "Status overview across technical vulnerabilities, US/EU regulation, and commercial products' security measures."),
            ("2. PRISMA-guided systematic review",
             "76 papers (2010–2025) screened across 5 databases — attack vectors, defence mechanisms, and risk evaluations."),
            ("3. Attack–defence taxonomy",
             "Maps 16 attack vectors across confidentiality / integrity / availability against 4 defence families (protected comm, IDS, control-strategy assessment, redundancy)."),
            ("4. Open research challenges",
             "Resource constraints, patient variability, infusion-pattern modelling, framework standardisation, trustworthy and privacy-preserving design."),
        ),
        headline_metrics=(
            ("Papers reviewed (PRISMA)", "76", "2010–2025 across 5 databases"),
            ("Initial DB hits", "53", "+23 via citation tracking"),
            ("Attack vectors catalogued", "16", "across CIA security triad"),
            ("Defence families analysed", "4", "Comm / IDS / Control / Redundancy"),
            ("Real-world recalls cited", "Multiple", "incl. Medtronic 2023"),
            ("AID market by 2032", "$5.80B", "from $2.34B in 2023"),
        ),
        technique_table=(
            ("PRISMA framework", "Systematic-review methodology"),
            ("STRIDE-style analysis", "Threat categorisation"),
            ("Scopus / IEEE Xplore / PubMed / WoS / Scholar", "Database coverage"),
            ("Backward + forward citation tracking", "Extends search beyond initial keywords"),
            ("Taxonomy (Fig. 2)", "Threats + defences linked"),
        ),
        method_sections=(
            ("Search + screening", (
                "Boolean keyword search across 5 databases (2010–2025)",
                "Inclusion: peer-reviewed studies proposing attacks / defences",
                "Exclusion: review-of-reviews, irrelevant, non-English",
            )),
            ("Threat / defence mapping", (
                "Group attacks by CIA principle",
                "Tag each defence family to attack vectors",
                "Cross-reference with US (FDA) + EU (MDR) regulations",
            )),
        ),
        evaluation_sections=(
            ("Regulatory landscape comparison", (
                "FDA premarket + postmarket guidance",
                "EU MDR + MDCG 2019-16 cybersecurity guidance",
                "DTSec voluntary AID-specific standard",
            )),
            ("Commercial-product security audit", (
                "Cryptography + auth measures in current products",
                "Recall + warning history (Medtronic etc.)",
                "Risk-management limitations vs sophisticated attacks",
            )),
        ),
        system_flow=(
            "CGM measures BG → wireless transmit to controller",
            "Controller computes insulin dose using control algorithm",
            "Command sent wirelessly to subcutaneous pump",
            "Pump delivers dose via infusion set",
            "Attack surface spans wireless links, algorithms, and pump I/O",
        ),
        research_questions=(
            ("RQ1", "What attack vectors / risks do AID systems face?"),
            ("RQ2", "How do existing defences address them?"),
            ("RQ3", "How practical and robust are these defences?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="Attack-vector landscape",
                table=(
                    ("Pillar", "Attack vectors"),
                    ("Confidentiality", "Eavesdropping, DIY hacking"),
                    ("Integrity (data)", "Replay, bias injection, FDIA"),
                    ("Integrity (algo)", "Computational attacks, ML-model attacks, pump driver"),
                    ("Availability", "DoS/DDoS, ransomware, jamming, firmware corruption, routing attacks"),
                ),
                analysis=(
                    "Real-world attacks demonstrated against shipping products",
                    "Process-aware attacks specific to closed-loop systems",
                    "ML/DL-based controllers add a new attack surface (FDIA)",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="Defence-mechanism families",
                table=(
                    ("Family", "Key methods"),
                    ("Protected comm", "Auth + crypto + secure protocols + proximity channels"),
                    ("IDS (signature)", "Known attack patterns matched"),
                    ("IDS (specification)", "Formal specs of normal operation"),
                    ("IDS (anomaly)", "Data-driven / model-based / hybrid"),
                    ("Control assessment", "Compare dose with insulin pattern model"),
                    ("Redundancy", "ECG monitor / USRP / secondary safety layer"),
                ),
                analysis=(
                    "Crypto cost trades against battery + comp budget",
                    "Anomaly-based IDS dominate recent literature",
                    "Personalised models needed for patient variability",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="Practicality of defences",
                table=(
                    ("Constraint", "Impact on defences"),
                    ("Battery / compute", "Excludes RSA / HE in continuous loop"),
                    ("Patient variability", "Anomaly models need personalisation"),
                    ("Real-time display absent", "User-side detection unreliable"),
                    ("Regulatory variability", "FDA prescriptive; EU principle-based"),
                ),
                analysis=(
                    "Lightweight + adaptive defences are the live gap",
                    "Risk assessment frameworks lack independent verification",
                    "Sleep / activity windows = blind spots for monitoring",
                ),
            ),
        ),
        core_observation=(
            "AID systems are arguably the highest-stakes IoMT category: "
            "wireless, closed-loop, life-critical. Sixteen distinct attack "
            "vectors are catalogued across the CIA triad, with real-world "
            "exploits and FDA recalls already on record. Defences fall into "
            "four families, but resource constraints, patient variability, "
            "and weak standardisation block their deployment. The roadmap: "
            "lightweight + adaptive defences plus AID-specific certification."
        ),
        limitations=(
            "Review scope ends Feb 2025 — fast-moving field",
            "Focus on academic literature; some industry detail proprietary",
            "Evaluation methods compared, not new defences proposed",
            "Comparison with non-AID IoMT systems left brief",
        ),
        future_work=(
            "Resource-aware defence design for battery-limited devices",
            "Patient-specific anomaly models with continuous adaptation",
            "Standardised AID security certification (extend DTSec)",
            "Privacy-preserving + trustworthy ML-based AID controllers",
        ),
        figures=(
            (
                "Overview of the paper (Figure 1, p.3)",
                _fig("niu2025securing", "p03-00-Overview-of-the-paper.png"),
                (
                    "Visual table-of-contents: status overview, attack "
                    "vectors, defence strategies, future directions.",
                    "Each branch maps to a top-level section of the review.",
                ),
            ),
            (
                "PRISMA diagram for the screening process (Figure 3, p.5)",
                _fig("niu2025securing", "p05-02-PRISMA-diagram-for-the-screening-process.png"),
                (
                    "53 papers from initial DB search + 23 from citation "
                    "tracking → 76 final included.",
                    "Standard reproducibility artefact for the systematic "
                    "review methodology.",
                ),
            ),
            (
                "Overview of a hybrid closed-loop insulin delivery system (Figure 5, p.5)",
                _fig("niu2025securing", "p05-03-An-overview-of-a-hybrid-closed-loop-insulin-delivery-system-.png"),
                (
                    "CGM → control algorithm → insulin pump loop, with "
                    "wireless links highlighted.",
                    "Each red arrow is an attack surface; the figure anchors "
                    "the threat model discussion.",
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
        "We propose Adversarial Prompt Disentanglement (APD), a proactive defense that "
        "decomposes prompts into benign and adversarial latent components via a mutual-"
        "information VAE, classifies intent through spectral analysis on a semantic graph, "
        "and routes the decision through a distilled lightweight transformer. APD reaches "
        "92.3% adversarial detection accuracy and 87.4% harmful-output reduction at 12.3 ms "
        "per prompt — comparable to rule-based filters and ~4x faster than post-output "
        "moderation."
    ),
    url="https://doi.org/10.1609/aaai.v40i5.37389",
    doi="10.1609/aaai.v40i5.37389",
    arxiv_id=None, pdf_url=None,
    summary=PaperSummary(
        language="en", model=MODEL_TAG, raw_text_chars=43_754,
        pain_points=(
            ("Existing defences are reactive, not preemptive", (
                "Post-output moderation runs AFTER the LLM generates harm",
                "Rule-based filters miss paraphrased / obfuscated attacks",
                "Adversarial training fine-tunes the LLM and degrades utility",
            )),
            ("Computational cost dominates real-world deployments", (
                "Post-output moderation: 45.6 ms/prompt",
                "Adversarial training: 38.2 ms/prompt",
                "Real-time chat applications cannot absorb this overhead",
            )),
            ("No unified framework neutralises malicious components first", (
                "Defences treat the prompt as opaque text",
                "No principled disentanglement of adversarial vs benign signal",
                "Each new attack class needs new manual rules",
            )),
            ("Generalisation across novel attacks remains weak", (
                "Rule-based ADA collapses to 65.4% on diverse benchmarks",
                "Embedding clustering: 78.6% on the same benchmarks",
                "No defence reported >87% across all three datasets",
            )),
        ),
        research_question=(
            "Can we proactively isolate and neutralise adversarial components in LLM "
            "input prompts BEFORE they reach the model — at real-time latency, without "
            "degrading utility on legitimate queries?"
        ),
        contributions_detailed=(
            ("1. Mutual-information semantic decomposition",
             "A VAE-based encoder produces latent codes (za, zb) for adversarial vs "
             "benign components; objective minimises I(za;zb|Ep), provably guaranteeing "
             "disentanglement via the Data Processing Inequality."),
            ("2. Graph-based intent classification",
             "Builds a semantic graph over the adversarial latent's neighbourhood; uses "
             "spectral analysis (Fiedler vector + higher-order eigenvalues) to flag "
             "malicious patterns robust to surface paraphrase."),
            ("3. Distilled lightweight detector (AID)",
             "A transformer-based Adversarial Intent Detector trained via knowledge "
             "distillation, achieving 12.3 ms/prompt inference — 2.3x faster than the "
             "non-distilled variant (28.4 ms) at near-identical accuracy."),
            ("4. Empirical evaluation on three jailbreak benchmarks",
             "JailBreakBench, ToxicPrompts, AdvPromptGen — APD's 92.3% mean ADA beats "
             "all four state-of-the-art defences by 5.6 pp or more."),
        ),
        headline_metrics=(
            ("Adversarial Detection Accuracy", "92.3%", "vs rule-based 65.4 / EC 78.6 / AT 86.7"),
            ("Harmful Output Reduction", "87.4%", "vs rule-based 58.9 / post-output 72.3"),
            ("False Positive Rate", "3.7%", "vs rule-based 7.7 / post-output 5.0"),
            ("Inference Latency", "12.3 ms", "post-output moderation: 45.6 ms"),
            ("ADA drop when VAE removed", "-9.6 pp", "ablation: 92.3 → 82.7"),
            ("ADA on multilingual variants", "89.3%", "no domain-specific training needed"),
        ),
        technique_table=(
            ("Rule-Based Filtering", "Keyword patterns; 65.4% ADA / 10.8 ms"),
            ("Post-Output Moderation", "RoBERTa flags harmful output; 84.1% / 45.6 ms"),
            ("Adversarial Training", "Fine-tunes LLM on adv+benign mix; 86.7% / 38.2 ms"),
            ("Embedding Clustering", "Anomaly detection on embeddings; 78.6% / 15.6 ms"),
            ("APD (this paper)", "VAE + spectral graph + distilled AID; 92.3% / 12.3 ms"),
        ),
        method_sections=(
            ("Mutual-Information Semantic Decomposition", (
                "VAE encoder splits prompt embedding Ep into latent codes za, zb",
                "Loss minimises I(za;zb|Ep) — Data Processing Inequality proof in paper",
                "Adversarial and benign clusters in latent space have minimal overlap",
            )),
            ("Graph-Based Intent Classification", (
                "Build semantic graph over za's semantic neighbours",
                "Compute Fiedler vector + top-k higher-order Laplacian eigenvalues",
                "Spectral features feed the downstream intent classifier",
            )),
            ("Adversarial Intent Detector (AID)", (
                "Lightweight transformer-based binary classifier",
                "Knowledge-distilled from a larger teacher (28.4 ms → 12.3 ms)",
                "Outputs neutralise/block decision before LLM ever sees the prompt",
            )),
        ),
        evaluation_sections=(
            ("Adversarial Detection (ADA, FPR)", (
                "JailBreakBench: 91.2% ADA / 3.8% FPR",
                "ToxicPrompts: 93.5% / 3.5%",
                "AdvPromptGen: 92.3% / 3.7%",
            )),
            ("Harmful Output Reduction (HOR)", (
                "Mean 87.4% across the 3 benchmarks",
                "Rule-based: 58.9%; post-output: 72.3%; AT: 75.8%",
                "Embedding clustering: 65.2% — sophisticated attacks still slip",
            )),
            ("Computational Efficiency (IL)", (
                "12.3 ms/prompt — comparable to rule-based 10.8 ms",
                "Post-output moderation: 45.6 ms (3.7x slower)",
                "Adversarial training: 38.2 ms (3.1x slower)",
            )),
            ("Novel attack variants", (
                "Role-playing (n=400): 90.5% ADA / 85.3% HOR",
                "Code injection (n=300): 88.7% / 83.9%",
                "Multilingual (n=300): 89.3% / 84.5%",
            )),
        ),
        system_flow=(
            ("User prompt", "Raw text to be evaluated before LLM sees it"),
            ("VAE encoder", "Produces Ep latent representation"),
            ("Disentangler fa/fb", "Splits into adversarial za, benign zb (DPI-guaranteed)"),
            ("Semantic graph + spectral features", "Fiedler + higher-order eigenvalues on za"),
            ("AID classifier (distilled)", "Binary intent decision in 12.3 ms"),
            ("Decision", "Neutralise/block adversarial — pass benign to LLM"),
        ),
        research_questions=(
            ("RQ1", "Does APD's proactive detection outperform reactive defences across diverse jailbreak datasets?"),
            ("RQ2", "How does APD trade off accuracy versus computational cost?"),
            ("RQ3", "Which APD components are essential to its robustness (ablation)?"),
            ("RQ4", "Does APD generalise to novel attack variants outside its training distribution?"),
        ),
        rq_results=(
            RqResult(
                rq_id="RQ1", question="Does proactive detection beat reactive defences?",
                table=(
                    ("Method", "ADA (%)", "HOR (%)", "FPR (%)"),
                    ("Rule-Based", "65.4", "58.9", "7.7"),
                    ("Post-Output Moderation", "84.1", "72.3", "5.0"),
                    ("Adversarial Training", "86.7", "75.8", "6.0"),
                    ("Embedding Clustering", "78.6", "65.2", "5.1"),
                    ("APD (Ours)", "92.3", "87.4", "3.7"),
                ),
                analysis=(
                    "APD beats every baseline by 5.6 pp ADA or more",
                    "HOR gap is 11.6 pp over the best baseline (AT)",
                    "FPR is also the lowest — better detection without false alarms",
                ),
            ),
            RqResult(
                rq_id="RQ2", question="What is the accuracy/latency trade-off?",
                table=(
                    ("Method", "ADA (%)", "IL (ms)"),
                    ("Rule-Based", "65.4", "10.8"),
                    ("Embedding Clustering", "78.6", "15.6"),
                    ("APD (Ours)", "92.3", "12.3"),
                    ("Adversarial Training", "86.7", "38.2"),
                    ("Post-Output Moderation", "84.1", "45.6"),
                ),
                analysis=(
                    "APD lands near the Pareto front: 27 pp higher ADA than rule-based at +1.5 ms",
                    "Versus post-output moderation: +8.2 pp ADA at 3.7x lower latency",
                    "Knowledge distillation is the key — without it, latency rises to 28.4 ms",
                ),
            ),
            RqResult(
                rq_id="RQ3", question="Which components matter most (ablation)?",
                table=(
                    ("Configuration", "ADA (%)", "HOR (%)", "IL (ms)"),
                    ("Full APD", "92.3", "87.4", "12.3"),
                    ("w/o VAE", "82.7", "74.1", "12.1"),
                    ("w/o Graph Features", "85.3", "78.6", "11.5"),
                    ("w/o AID Distillation", "92.5", "87.7", "28.4"),
                    ("w/o Higher-Order Eigenvalues", "90.0", "85.0", "12.0"),
                ),
                analysis=(
                    "VAE is the single biggest contributor (-9.6 pp ADA when removed)",
                    "Graph features contribute -7.0 pp; eigenvalues alone contribute -2.3 pp",
                    "Distillation is essential for latency — accuracy unchanged but IL 2.3x",
                ),
            ),
            RqResult(
                rq_id="RQ4", question="Does APD generalise to novel attack variants?",
                table=(
                    ("Attack Variant", "ADA (%)", "HOR (%)", "FPR (%)"),
                    ("Role-Playing (n=400)", "90.5", "85.3", "3.6"),
                    ("Code Injection (n=300)", "88.7", "83.9", "3.8"),
                    ("Multilingual (n=300)", "89.3", "84.5", "3.7"),
                ),
                analysis=(
                    "All three out-of-distribution attack categories: >88% ADA",
                    "FPR stays below 4% even on novel variants",
                    "Multilingual generalisation is notable — no language-specific training",
                ),
            ),
        ),
        core_observation=(
            "Disentangling adversarial from benign components in the LLM input's latent "
            "space — via a VAE objective that provably minimises I(za;zb|Ep) — is both "
            "more accurate (92.3% ADA) and 3-4x faster than detecting harm after generation."
        ),
        limitations=(
            "Evaluated on three jailbreak datasets; transfer to fundamentally new attack categories unverified",
            "Requires labelled adversarial training data for AID — supervised by construction",
            "VAE is an additional model alongside the LLM (extra GPU memory)",
            "Spectral graph computation may scale poorly on very long prompts",
        ),
        future_work=(
            "Extend APD to multimodal LLMs (image + text)",
            "Self-supervised pretraining to reduce labelled-data dependency",
            "Continual / online learning to adapt to evolving attack patterns",
        ),
    ),
)


ALL_PAPERS = (WEN, MCCLEARN, SHUKLA, OBADOFIN, HAGEN, LI_ACE, NIU, FANG)


def main() -> None:
    # Use the same dir derived at module load time so figures and pptx
    # output stay co-located (figures live under {run_dir}/figures/).
    out_dir = ROOT / "exports" / _RUN_DIR_NAME
    out_dir.mkdir(parents=True, exist_ok=True)
    for paper in ALL_PAPERS:
        collection = PaperCollection(
            query=Query(
                keywords="LLM security",
                sources=("local",),
                max_results=1,
            ),
            papers=(paper,),
        )
        options = ExportOptions(
            formats=("pptx",),
            out_dir=str(out_dir),
            # Canonical filename — overwrites the CLI's lightweight emit so
            # the user ends up with exactly one .pptx per paper (the rich one).
            filename_stem=paper.bibtex_key(),
            include_abstract=True,
            language="en",
        )
        written = export_collection(collection, options)
        for fmt, path in written.items():
            print(f"  - {paper.bibtex_key()} {fmt}: {path}")


if __name__ == "__main__":
    main()
