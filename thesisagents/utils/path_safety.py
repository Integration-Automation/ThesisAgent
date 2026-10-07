"""Path-traversal-safe resolution. Every user-controlled path goes through here."""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath


def resolve_safe(root: str | Path, reference: str | Path) -> Path:
    """Resolve `reference` relative to `root`, refusing anything that escapes `root`.

    Rejects: absolute paths (POSIX or Windows-style, regardless of host OS),
    `..` segments, and symlinks pointing outside `root`. Returns a real,
    absolute path inside `root`.
    """
    root_path = Path(root).expanduser().resolve()
    reference_path = Path(reference)
    reference_str = str(reference)
    # Check both flavours so a Windows drive letter (e.g. "C:/evil/path") is
    # still rejected on POSIX runners, where Path treats it as a directory name.
    if (
        reference_path.is_absolute()
        or PurePosixPath(reference_str).is_absolute()
        or PureWindowsPath(reference_str).is_absolute()
    ):
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


def resolve_library_path(path: str | Path) -> Path:
    """Absolute path of a literature-library file, refusing a directory.

    The boundary this guards: the ``--library`` flag and the ``library``
    argument of the MCP tools, both of which name a file the process will
    open for writing. The failure it prevents is SQLite's own answer to a
    directory, "unable to open database file", which does not say what is
    wrong with the path.

    Unlike :func:`resolve_safe` there is no root to stay inside: like
    ``--out``, the location is the user's choice.

    Example: ``resolve_library_path("~/thesis.db")`` returns the absolute
    path. ``resolve_library_path("./exports/")`` raises ``ValueError``.
    """
    if not str(path).strip():
        raise ValueError("the library path is empty")
    resolved = Path(path).expanduser().resolve()
    if resolved.is_dir():
        raise ValueError(
            f"the library path is a directory, it must be a file: {resolved}"
        )
    return resolved


def safe_filename(stem: str) -> str:
    """Slugify a string so it is safe as a filename component."""
    allowed = []
    for char in stem:
        if char.isalnum() or char in "-_":
            allowed.append(char)
        elif char in " \t":
            allowed.append("-")
    cleaned = "".join(allowed).strip("-")
    return cleaned[:80] or "thesisagents"
