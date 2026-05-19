"""Patch the 13 non-English READMEs to match the current env-var table.

The translated READMEs duplicate the English README's "Environment variables"
section verbatim except for prose around each row, so the surgical edits are:

1. ENABLE_IEEE_SCRAPING row -> DISABLE_IEEE_SCRAPING (opt-out, default-on).
2. ENABLE_SCHOLAR_SCRAPING row -> DISABLE_SCHOLAR_SCRAPING (same).
3. Append three NEW rows (CHROME_PROFILE_DIR, DISABLE_WEBRUNNER, CORE_API_KEY)
   after the SPRINGER_API_KEY row in each language file.

The purpose text in the new rows is English — translation of every nuance into
13 languages is out of scope; the variable name + a short English description
is enough for users who know the project. Adopt-as-you-can in future PRs.

Usage:
    .venv\\Scripts\\python.exe -m scripts._update_readme_envvars
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
READMES_DIR = REPO / "readmes"

# (variable name, English purpose text). Same as README.md.
_DISABLE_IEEE = (
    "AUTOPAPERTOPPT_DISABLE_IEEE_SCRAPING",
    "**IEEE is default-ON via visible Chrome.** Set `=1` to opt out (e.g. CI without Chrome).",
)
_DISABLE_SCHOLAR = (
    "AUTOPAPERTOPPT_DISABLE_SCHOLAR_SCRAPING",
    "**Scholar is default-ON via visible Chrome.** Set `=1` to opt out (Google ToS forbids automation).",
)
_NEW_ROWS = (
    (
        "AUTOPAPERTOPPT_CHROME_PROFILE_DIR",
        "Scholar + IEEE + paywalled-PDF downloads",
        "Persistent Chrome `--user-data-dir`. Set this and complete VPN / SSO once; subsequent runs inherit the cookies.",
    ),
    (
        "AUTOPAPERTOPPT_DISABLE_WEBRUNNER",
        "Scholar + IEEE + paywalled-PDF downloads",
        "`=1` forces the httpx paths instead of driving real Chrome. For CI / Docker without a Chrome binary.",
    ),
    (
        "AUTOPAPERTOPPT_CORE_API_KEY",
        "OA resolver",
        "Free key from <https://core.ac.uk/services/api>. Enables the CORE.ac.uk lookup step in the OA PDF resolver.",
    ),
)


def _patch(text: str) -> str:
    # Flip ENABLE_IEEE -> DISABLE_IEEE (variable name only). Leave the
    # localized purpose column intact except for the variable name.
    text = re.sub(
        r"`AUTOPAPERTOPPT_ENABLE_IEEE_SCRAPING`",
        f"`{_DISABLE_IEEE[0]}`",
        text,
    )
    text = re.sub(
        r"`AUTOPAPERTOPPT_ENABLE_SCHOLAR_SCRAPING`",
        f"`{_DISABLE_SCHOLAR[0]}`",
        text,
    )
    # Locate the Springer row and inject the new rows directly after it.
    pattern = re.compile(
        r"(\| `AUTOPAPERTOPPT_SPRINGER_API_KEY` \|[^\n]*\n)",
        re.MULTILINE,
    )

    def insert(match: re.Match[str]) -> str:
        rows = [match.group(1)]
        for env, used_by, purpose in _NEW_ROWS:
            # Skip if a row with this variable already exists in the file.
            if f"`{env}`" in text:
                continue
            rows.append(f"| `{env}` | {used_by} | {purpose} |\n")
        return "".join(rows)

    text = pattern.sub(insert, text, count=1)
    return text


def main() -> int:
    changed = 0
    for path in sorted(READMES_DIR.glob("README.*.md")):
        before = path.read_text(encoding="utf-8")
        after = _patch(before)
        if after != before:
            path.write_text(after, encoding="utf-8")
            changed += 1
            print(f"updated {path.name}")
    print(f"{changed} file(s) changed")
    return 0


if __name__ == "__main__":
    main()
