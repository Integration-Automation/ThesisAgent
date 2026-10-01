"""The source distribution carries no tests.

setuptools adds ``tests/test*.py`` to an sdist by default, so the ``thesisagents`` 0.1.22 sdist
shipped 28 files of this suite although the wheel installs only ``thesisagents``
(``include = ["thesisagents*"]`` in ``pyproject.toml``). ``MANIFEST.in`` prunes the directory.
Nothing is built here: the template is read and its commands are checked in the order
setuptools applies them.
"""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TEST_DIRECTORY = Path(__file__).resolve().parent.name
_PRUNE = ["prune", _TEST_DIRECTORY]
# The template commands that add files. One of them after the prune could bring tests back.
_ADDING = {"include", "recursive-include", "global-include", "graft"}


def _commands() -> list[list[str]]:
    """Return the commands of ``MANIFEST.in`` in order, each split into words.

    Blank lines and comments are dropped, so ``prune tests`` comes back as
    ``["prune", "tests"]``. A missing ``MANIFEST.in`` raises, which fails the tests that
    call this: without the file the sdist carries the suite again.
    """
    lines = (_ROOT / "MANIFEST.in").read_text(encoding="utf-8").splitlines()
    return [line.split() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def test_manifest_prunes_the_test_directory():
    assert _PRUNE in _commands()


def test_nothing_after_the_prune_adds_files_back():
    commands = _commands()
    following = commands[commands.index(_PRUNE) + 1:]
    assert [command for command in following if command[0] in _ADDING] == []
