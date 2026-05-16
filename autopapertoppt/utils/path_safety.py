"""Path-traversal-safe resolution. Every user-controlled path goes through here."""

from __future__ import annotations

from pathlib import Path


def resolve_safe(root: str | Path, reference: str | Path) -> Path:
    """Resolve `reference` relative to `root`, refusing anything that escapes `root`.

    Rejects: absolute paths, `..` segments, and symlinks pointing outside `root`.
    Returns a real, absolute path inside `root`.
    """
    root_path = Path(root).expanduser().resolve()
    reference_path = Path(reference)
    if reference_path.is_absolute():
        raise ValueError(f"absolute paths are not allowed: {reference}")
    if any(part == ".." for part in reference_path.parts):
        raise ValueError(f"parent-segment paths are not allowed: {reference}")
    candidate = (root_path / reference_path).resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError as err:
        raise ValueError(
            f"resolved path escapes root: {candidate} not under {root_path}"
        ) from err
    return candidate


def ensure_export_dir(out_dir: str | Path) -> Path:
    """Create the export dir if missing; refuse if it is an existing non-directory."""
    path = Path(out_dir).expanduser().resolve()
    if path.exists() and not path.is_dir():
        raise ValueError(f"export path exists and is not a directory: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_filename(stem: str) -> str:
    """Slugify a string so it is safe as a filename component."""
    allowed = []
    for char in stem:
        if char.isalnum() or char in "-_":
            allowed.append(char)
        elif char in " \t":
            allowed.append("-")
    cleaned = "".join(allowed).strip("-")
    return cleaned[:80] or "autopapertoppt"
