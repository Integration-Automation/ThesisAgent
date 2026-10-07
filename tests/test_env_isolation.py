"""The suite restores ``os.environ`` after every test.

These tests run in definition order, so each ``*_then_*`` pair checks that a
change made by the first test is gone when the second one starts. They guard
the autouse ``_restore_environment`` fixture in ``tests/conftest.py``.

Why it matters: the GUI Settings page writes saved keys straight into
``os.environ``. Its tests left ``ANTHROPIC_API_KEY`` set, so the CLI tests that
ran afterwards took the auto-enrich branch and made live HTTPS calls.

The "added" pair is the regression test: it writes a new variable the same
direct way, so ``monkeypatch`` has nothing recorded to undo and only the
fixture can remove it (the pair fails without the fixture). The "changed" and
"removed" pairs check that the fixture and ``monkeypatch`` undo the same
variable without fighting each other.
"""

from __future__ import annotations

import os

_ADDED = "THESISAGENTS_TEST_ENV_ADDED"
_CHANGED = "THESISAGENTS_TEST_ENV_CHANGED"
_REMOVED = "THESISAGENTS_TEST_ENV_REMOVED"


def test_a_variable_added_directly_is_set_inside_the_test():
    os.environ[_ADDED] = "1"
    assert os.environ[_ADDED] == "1"


def test_then_the_added_variable_is_gone():
    assert _ADDED not in os.environ


def test_a_variable_changed_directly_is_changed_inside_the_test(monkeypatch):
    monkeypatch.setenv(_CHANGED, "original")
    os.environ[_CHANGED] = "overwritten"
    assert os.environ[_CHANGED] == "overwritten"


def test_then_the_changed_variable_does_not_carry_over():
    assert _CHANGED not in os.environ


def test_a_variable_removed_directly_is_absent_inside_the_test(monkeypatch):
    monkeypatch.setenv(_REMOVED, "kept")
    del os.environ[_REMOVED]
    assert _REMOVED not in os.environ


def test_then_the_removed_variable_does_not_carry_over_either():
    assert _REMOVED not in os.environ
