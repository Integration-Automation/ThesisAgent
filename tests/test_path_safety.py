"""Tests for path-traversal safety."""

from __future__ import annotations

import pytest

from autopapertoppt.utils.path_safety import (
    ensure_export_dir,
    resolve_safe,
    safe_filename,
)


def test_resolve_safe_accepts_relative(tmp_path):
    target = resolve_safe(tmp_path, "out/file.pptx")
    assert target.is_relative_to(tmp_path.resolve())


def test_resolve_safe_rejects_absolute(tmp_path):
    with pytest.raises(ValueError):
        resolve_safe(tmp_path, "C:/evil/path.txt")


def test_resolve_safe_rejects_dotdot(tmp_path):
    with pytest.raises(ValueError):
        resolve_safe(tmp_path, "../escape.txt")


def test_ensure_export_dir_creates(tmp_path):
    target = ensure_export_dir(tmp_path / "new_export")
    assert target.is_dir()


def test_safe_filename_strips_specials():
    assert safe_filename("hello/world*") == "helloworld"
    assert safe_filename("  spaced  text  ") == "spaced--text"
    assert safe_filename("") == "autopapertoppt"
