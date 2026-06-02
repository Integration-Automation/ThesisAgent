"""AGENTS.md presence + canonical-rule pin.

Why this test exists: ``AGENTS.md`` is the cross-agent mirror of the
critical rules in ``CLAUDE.md``. If someone deletes or empties the file,
non-Claude agents (Codex CLI, Aider, etc.) lose the LLM-as-agent default
path, the HTTPS-only rule, and the per-paper PPT gate — silently. This
test fails loudly instead.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_AGENTS_MD = _ROOT / "AGENTS.md"
_CLAUDE_MD = _ROOT / "CLAUDE.md"
_SUBAGENTS_DIR = _ROOT / ".claude" / "agents"


def _claude_rules_text() -> str:
    """Concatenate CLAUDE.md + every project-scoped subagent doc.

    The Claude-side rule set is split across ``CLAUDE.md`` (always-loaded
    overview + must-knows) and the per-topic subagent docs under
    ``.claude/agents/`` (loaded on demand when the relevant agent runs).
    From the perspective of "do future Claude sessions see this rule," the
    combined text is what counts — so the mirror-with-AGENTS.md tests
    treat both as one Claude-rules document.
    """
    parts = [_CLAUDE_MD.read_text(encoding="utf-8")]
    if _SUBAGENTS_DIR.is_dir():
        # Recursive: subagent docs are organised into subfolders
        # (``rules/`` references + ``tasks/`` runners). Claude Code itself
        # scans ``.claude/agents/`` recursively, so this glob mirrors that.
        for path in sorted(_SUBAGENTS_DIR.rglob("*.md")):
            parts.append(path.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def test_agents_md_exists():
    assert _AGENTS_MD.is_file(), "AGENTS.md must live at the repo root"


def test_agents_md_pins_llm_as_agent_default_path():
    text = _AGENTS_MD.read_text(encoding="utf-8")
    # The heading wording is part of the contract: agents grep for it.
    assert "LLM-as-agent default path" in text
    # The rule has to surface the key talking points so an agent that
    # only skims the file still sees them.
    for must_appear in (
        "ANTHROPIC_API_KEY",
        "PaperSummary",
        "contributions_detailed",
        "7.05",
        "scripts/regen_",
    ):
        assert must_appear in text, f"AGENTS.md lost mention of {must_appear!r}"


def test_agents_md_points_back_to_claude_md():
    text = _AGENTS_MD.read_text(encoding="utf-8")
    assert "CLAUDE.md" in text, (
        "AGENTS.md must point readers at CLAUDE.md for the full guide"
    )


def _normalise_whitespace(text: str) -> str:
    """Collapse runs of whitespace so line-wrap in the source markdown
    doesn't break substring matching for multi-word pinned phrases."""
    return " ".join(text.split())


def test_agents_md_pins_rich_first_anti_patterns():
    """The 'do NOT' anti-patterns are load-bearing: they exist because a
    real agent (Claude 4.7 in dev) repeatedly fell back to telling the
    user 'set the API key' instead of writing the rich summary itself.
    Pin the exact wording so any future cleanup keeps the lesson."""
    text = _normalise_whitespace(_AGENTS_MD.read_text(encoding="utf-8"))
    # Rich-by-default framing
    assert "Rich thesis-style PPT is the default deliverable" in text
    assert "Lightweight is a fallback" in text
    # Decision tree + anti-patterns sections
    assert "Decision tree" in text
    assert "Anti-patterns" in text
    for phrase in (
        "you ARE the LLM",
        "offloading your own",
        "intermediate artefact",
        "not the deliverable",
        "Do NOT",
    ):
        assert phrase in text, f"AGENTS.md lost the anti-pattern phrase: {phrase!r}"
    assert "regen_llm_security_batch.py" in text


def test_claude_md_mirrors_anti_patterns():
    claude_md = _normalise_whitespace(_claude_rules_text())
    assert "Rich thesis-style PPT is the default deliverable" in claude_md
    assert "Decision tree" in claude_md
    assert "Anti-patterns" in claude_md
    assert "you yourself are the LLM" in claude_md or "you ARE the LLM" in claude_md
    assert "regen_llm_security_batch.py" in claude_md


def test_canonical_filename_rule_documented():
    """Regen scripts must write rich decks to the same path as the CLI's
    lightweight emit (no -rich suffix), so the user ends up with exactly
    one deck per paper. Both docs must say so."""
    agents = _normalise_whitespace(_AGENTS_MD.read_text(encoding="utf-8"))
    claude = _normalise_whitespace(_claude_rules_text())
    for text, label in ((agents, "AGENTS.md"), (claude, "CLAUDE.md+subagents")):
        assert "Canonical filename" in text, (
            f"{label} lost the canonical-filename rule"
        )
        assert "no `-rich` suffix" in text, (
            f"{label} lost the no-`-rich`-suffix rule"
        )
        assert "filename_stem=paper.bibtex_key()" in text, (
            f"{label} lost the concrete code-snippet example"
        )


def test_regen_scripts_use_canonical_filenames():
    """The shipped regen-script templates must follow the rule themselves."""
    import re

    scripts_dir = _ROOT / "scripts"
    suffix_pattern = re.compile(r'filename_stem\s*=\s*f?"[^"]*-rich"')
    offenders: list[str] = []
    for path in scripts_dir.glob("regen_*.py"):
        text = path.read_text(encoding="utf-8")
        if suffix_pattern.search(text):
            offenders.append(path.name)
    assert offenders == [], (
        f"regen scripts must drop the -rich suffix; offenders: {offenders}"
    )


def test_agents_md_and_claude_md_rules_aligned():
    """AGENTS.md is the cross-agent mirror of CLAUDE.md's load-bearing rules.
    Both files must carry every rule heading and every anti-pattern bullet,
    so an agent reading either one gets the same instructions. Wording can
    differ (CLAUDE.md is verbose; AGENTS.md is terse) but the *concept* of
    each rule must appear in both.

    This test pins the alignment by checking that each canonical rule
    keyword appears in BOTH files. Add a rule? Add a new check here.
    """
    agents = _normalise_whitespace(_AGENTS_MD.read_text(encoding="utf-8"))
    claude = _normalise_whitespace(_claude_rules_text())

    # (description, list of keywords that must appear in BOTH files)
    rules = [
        ("Decision tree heading", ["Decision tree"]),
        ("Anti-pattern: set ANTHROPIC_API_KEY", ["ANTHROPIC_API_KEY"]),
        ("Anti-pattern: lightweight as deliverable",
         ["lightweight", "deliverable"]),
        ("Anti-pattern: stop after download_pdfs",
         ["download_pdfs"]),
        ("Anti-pattern: invent numbers / RQ / contributions",
         ["invent"]),
        ("Anti-pattern: fabricate URL/DOI/arXiv",
         ["fabricate", "arxiv_id"]),
        ("Anti-pattern: leave irrelevant downloads",
         ["irrelevant downloads"]),
        ("URL/DOI verification rule + verbatim wording",
         ["URL / DOI verification", "verbatim"]),
        ("Pruning irrelevant downloads subsection",
         ["Pruning irrelevant downloads"]),
        ("Concrete file paths to delete",
         ["pdfs/", ".pptx"]),
        ("Keep aggregate xlsx/bib rationale",
         ["honest record"]),
        ("URL-audit Python snippet markers",
         ["ALL_PAPERS", "load_workbook"]),
        ("Production fabrications named",
         ["Wen", "Fang"]),
        ("AAAI / IEEE / ACM URL-path examples",
         ["AAAI", "arnumber"]),
    ]
    missing: list[str] = []
    for description, keywords in rules:
        for kw in keywords:
            for text, label in (
                (agents, "AGENTS.md"),
                (claude, "CLAUDE.md+subagents"),
            ):
                if kw.lower() not in text.lower():
                    missing.append(f"{label}: {description} — missing {kw!r}")
    assert not missing, (
        "AGENTS.md and CLAUDE.md+subagents drifted out of alignment:\n  "
        + "\n  ".join(missing)
    )


def test_pruning_irrelevant_downloads_rule_documented():
    """Both docs must explain the prune-irrelevant-downloads rule.

    Why: search keyword matching is keyword-based, so off-topic papers
    will slip in. Documented examples that this rule was written for:
    a Viterbi-decoder paper matching "Claude code", and an object-detection
    literature review matching "LLM code review". The rule says delete
    the per-paper PDF + lightweight pptx, keep the aggregate xlsx/bib.
    """
    agents = _normalise_whitespace(_AGENTS_MD.read_text(encoding="utf-8"))
    claude = _normalise_whitespace(_claude_rules_text())
    for text, label in ((agents, "AGENTS.md"), (claude, "CLAUDE.md+subagents")):
        # The anti-pattern bullet that introduces the rule.
        assert "irrelevant downloads" in text.lower(), (
            f"{label} lost the 'irrelevant downloads' anti-pattern"
        )
        # The concrete paths to delete.
        assert "pdfs/" in text and ".pptx" in text, (
            f"{label} lost the concrete pdfs/<key>.pdf + <key>.pptx paths"
        )
    # The Claude-side canonical reference must also carry the
    # "Pruning irrelevant downloads" sub-heading + the keep-xlsx note.
    assert "Pruning irrelevant downloads" in claude, (
        "CLAUDE.md+subagents lost the 'Pruning irrelevant downloads' sub-heading"
    )
    assert "honest record" in claude, (
        "CLAUDE.md+subagents lost the 'keep the aggregate xlsx/bib' rationale"
    )


def test_url_doi_verification_rule_documented():
    """Both docs must carry the URL/DOI verification rule.

    Why: a real agent (Claude 4.7) shipped a regen script with
    fabricated AAAI URLs (`view/fang2026`) and a wrong AAAI volume
    (`v39i23.34521` vs the real `v39i22.34537`). Future agents must
    see the rule and the concrete audit snippet so the lesson sticks.
    """
    agents = _normalise_whitespace(_AGENTS_MD.read_text(encoding="utf-8"))
    claude = _normalise_whitespace(_claude_rules_text())
    for text, label in ((agents, "AGENTS.md"), (claude, "CLAUDE.md+subagents")):
        # Rule heading
        assert "URL / DOI verification" in text, (
            f"{label} lost the URL/DOI verification rule heading"
        )
        # The verbatim-from-xlsx anchor that names the canonical source
        # of truth — a regen script must never invent identifiers.
        assert "verbatim" in text, (
            f"{label} lost the 'verbatim' wording on URL/DOI sourcing"
        )
        # Concrete failure mode the rule was written to prevent — the
        # examples make the rule memorable instead of abstract.
        assert "AAAI" in text and "arnumber" in text, (
            f"{label} lost the concrete examples of why URLs can't be guessed"
        )
        # Audit-script signature so an agent can grep for it and run it.
        assert "ALL_PAPERS" in text and "load_workbook" in text, (
            f"{label} lost the post-regen URL-audit snippet"
        )
