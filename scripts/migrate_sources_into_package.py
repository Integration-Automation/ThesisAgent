"""Move sources/<name>/ → autopapertoppt/sources/<name>/ and rewrite imports.

Motivation: with the dual-directory layout, ``pip install autopapertoppt``
ships only the ``autopapertoppt/`` tree — the dynamic loader in
``autopapertoppt/fetchers/base.py::load_fetcher`` then can't find the
plugins on the install target. Physically relocating the plugins under
``autopapertoppt/sources/`` makes them part of the installed wheel.

What this script does, in order:

  1. ``git mv sources/<name> autopapertoppt/sources/<name>`` (preserves
     rename detection in git log / blame).
  2. Creates ``autopapertoppt/sources/__init__.py`` (package marker +
     short module docstring).
  3. Rewrites intra-source imports in every moved file:
     - ``from <name>.fetcher import X`` → ``from .fetcher import X``
     - ``from <name>.parser  import X`` → ``from .parser  import X``
     - ``from <name>         import webrunner_backend`` →
       ``from .             import webrunner_backend``
  4. Rewrites test-file imports:
     - ``from <name>.<mod> import X`` →
       ``from autopapertoppt.sources.<name>.<mod> import X``
     - ``from <name> import webrunner_backend`` →
       ``from autopapertoppt.sources.<name> import webrunner_backend``
  5. Patches ``autopapertoppt/fetchers/base.py`` — drops the sys.path
     hack, changes ``import_module(name)`` →
     ``import_module(f"autopapertoppt.sources.{name}")``.
  6. Patches ``tests/conftest.py`` — drops the matching sys.path hack.
  7. Deletes the now-empty ``sources/`` directory and any leftover
     ``__pycache__``.

Idempotent: re-running aborts on the missing ``sources/`` directory rather
than double-applying.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_SOURCES = ROOT / "sources"
NEW_SOURCES = ROOT / "autopapertoppt" / "sources"

SOURCE_NAMES = [
    "acm", "arxiv", "crossref", "dblp", "ieee",
    "openaire", "openalex", "pubmed", "scholar",
    "semantic_scholar", "springer",
]


def _run(cmd: list[str]) -> None:
    """Run a subprocess command, fail loud."""
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit(
            f"command failed: {' '.join(cmd)}\nstderr:\n{res.stderr}"
        )


# ---------------------------------------------------------------------------
# Step 1 — git mv each source directory
# ---------------------------------------------------------------------------
def step1_move_directories() -> None:
    if not OLD_SOURCES.is_dir():
        raise SystemExit(
            f"{OLD_SOURCES} does not exist — already migrated, or run from "
            "wrong cwd."
        )
    if NEW_SOURCES.exists():
        raise SystemExit(
            f"{NEW_SOURCES} already exists — aborting to avoid clobbering."
        )

    NEW_SOURCES.mkdir(parents=True)
    # Drop a package marker FIRST so git tracks the new package root.
    init_py = NEW_SOURCES / "__init__.py"
    init_py.write_text(
        '"""Built-in source plugins.\n\n'
        "Each subpackage exposes a ``fetcher_class`` attribute pointing at a\n"
        "``Fetcher`` subclass. Plugins are discovered dynamically by\n"
        "``autopapertoppt.fetchers.base.load_fetcher(name)`` via\n"
        '``importlib.import_module(f"autopapertoppt.sources.{name}")``.\n\n'
        "Adding a new source: create ``autopapertoppt/sources/<name>/__init__.py``\n"
        "with ``from .fetcher import <Name>Fetcher; fetcher_class = <Name>Fetcher``.\n"
        '"""\n',
        encoding="utf-8",
    )
    print(f"  created {init_py.relative_to(ROOT)}")

    for name in SOURCE_NAMES:
        src = OLD_SOURCES / name
        dest = NEW_SOURCES / name
        if not src.is_dir():
            raise SystemExit(f"missing source directory: {src}")
        if dest.exists():
            raise SystemExit(f"destination exists: {dest}")
        _run(["git", "mv", str(src), str(dest)])
        print(f"  git mv {src.relative_to(ROOT)} → {dest.relative_to(ROOT)}")

    # Clear any leftover __pycache__ at the old location.
    for cache in OLD_SOURCES.glob("**/__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)
    # Try to remove the now-empty directory; ignore if git keeps it staged.
    try:
        OLD_SOURCES.rmdir()
        print(f"  removed empty {OLD_SOURCES.relative_to(ROOT)}/")
    except OSError as err:
        print(f"  warning: could not rmdir {OLD_SOURCES} ({err}) — non-fatal")


# ---------------------------------------------------------------------------
# Step 2 — rewrite intra-source imports (now under new path)
# ---------------------------------------------------------------------------
def _rewrite_file(path: Path, rules: list[tuple[re.Pattern, str]]) -> int:
    text = path.read_text(encoding="utf-8")
    new = text
    hits = 0
    for pat, repl in rules:
        new, n = pat.subn(repl, new)
        hits += n
    if hits:
        path.write_text(new, encoding="utf-8")
    return hits


def step2_rewrite_intra_source_imports() -> None:
    for name in SOURCE_NAMES:
        # `from <name>.X import Y` → `from .X import Y`
        # `from <name>   import Y` → `from .  import Y`
        from_module = re.compile(rf"^from {re.escape(name)}\.(\w+) import",
                                 re.MULTILINE)
        from_pkg = re.compile(rf"^from {re.escape(name)} import",
                              re.MULTILINE)
        rules = [
            (from_module, r"from .\1 import"),
            (from_pkg, "from . import"),
        ]
        pkg_dir = NEW_SOURCES / name
        for py in pkg_dir.rglob("*.py"):
            hits = _rewrite_file(py, rules)
            if hits:
                print(f"  rewrote {hits} import(s) in {py.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Step 3 — rewrite test-file imports
# ---------------------------------------------------------------------------
def step3_rewrite_test_imports() -> None:
    tests_dir = ROOT / "tests"
    name_alt = "|".join(re.escape(n) for n in SOURCE_NAMES)
    # `from <name>.<mod> import …` → `from autopapertoppt.sources.<name>.<mod> import …`
    pat_with_mod = re.compile(
        rf"^from ({name_alt})\.(\w+) import", re.MULTILINE
    )
    # `from <name> import webrunner_backend` → `from autopapertoppt.sources.<name> import webrunner_backend`
    pat_bare = re.compile(rf"^from ({name_alt}) import", re.MULTILINE)
    for py in tests_dir.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        new = text
        new, n1 = pat_with_mod.subn(r"from autopapertoppt.sources.\1.\2 import", new)
        new, n2 = pat_bare.subn(r"from autopapertoppt.sources.\1 import", new)
        if n1 + n2:
            py.write_text(new, encoding="utf-8")
            print(f"  rewrote {n1+n2} import(s) in {py.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Step 4 — patch base.py
# ---------------------------------------------------------------------------
def step4_patch_base_py() -> None:
    base_py = ROOT / "autopapertoppt" / "fetchers" / "base.py"
    text = base_py.read_text(encoding="utf-8")

    # Remove the sys + Path imports if they were added only for the hack.
    text = re.sub(r"^import sys\n", "", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"^from pathlib import Path\n", "", text, count=1,
                  flags=re.MULTILINE)

    # Drop the _SOURCES_DIR constant + _ensure_sources_on_path helper.
    text = re.sub(
        r"\n\n_SOURCES_DIR = Path\(__file__\).resolve\(\).parents\[2\] / \"sources\"\n+"
        r"\n+def _ensure_sources_on_path\(\) -> None:\n"
        r"    sources_dir = str\(_SOURCES_DIR\)\n"
        r"    if sources_dir not in sys\.path:\n"
        r"        sys\.path\.insert\(0, sources_dir\)\n",
        "\n",
        text,
    )

    # Drop the _ensure_sources_on_path() call inside load_fetcher.
    text = text.replace("    _ensure_sources_on_path()\n", "")

    # Rewrite the import target.
    text = text.replace(
        'module = importlib.import_module(name)',
        'module = importlib.import_module(f"autopapertoppt.sources.{name}")',
    )

    base_py.write_text(text, encoding="utf-8")
    print(f"  patched {base_py.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Step 5 — patch tests/conftest.py
# ---------------------------------------------------------------------------
def step5_patch_conftest() -> None:
    conftest = ROOT / "tests" / "conftest.py"
    text = conftest.read_text(encoding="utf-8")
    new = re.sub(
        r"import sys\n"
        r"from pathlib import Path\n\n"
        r"import pytest\n\n"
        r"_ROOT = Path\(__file__\)\.resolve\(\)\.parents\[1\]\n"
        r"_SOURCES = _ROOT / \"sources\"\n\n\n"
        r"def _ensure_sources_on_path\(\) -> None:\n"
        r"    sources_dir = str\(_SOURCES\)\n"
        r"    if sources_dir not in sys\.path:\n"
        r"        sys\.path\.insert\(0, sources_dir\)\n\n\n"
        r"_ensure_sources_on_path\(\)\n\n\n",
        "import pytest\n\n\n",
        text,
    )
    if new == text:
        print(f"  warning: conftest.py — sys.path hack not found verbatim, "
              "may need manual cleanup")
    else:
        conftest.write_text(new, encoding="utf-8")
        print(f"  patched {conftest.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("== Step 1: git mv directories ==")
    step1_move_directories()
    print("\n== Step 2: rewrite intra-source imports ==")
    step2_rewrite_intra_source_imports()
    print("\n== Step 3: rewrite test imports ==")
    step3_rewrite_test_imports()
    print("\n== Step 4: patch base.py ==")
    step4_patch_base_py()
    print("\n== Step 5: patch tests/conftest.py ==")
    step5_patch_conftest()
    print("\nMigration complete. Next: run pytest + ruff to verify.")


if __name__ == "__main__":
    main()
