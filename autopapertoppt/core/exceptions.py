"""Project exception hierarchy. Catch at boundaries, never bare `except`."""

from __future__ import annotations


class AutoPaperToPPTError(Exception):
    """Base for all AutoPaperToPPT errors."""


class ConfigError(AutoPaperToPPTError):
    """Invalid configuration or environment."""


class FetchError(AutoPaperToPPTError):
    """Network or source-side failure during fetch."""

    def __init__(self, source: str, message: str) -> None:
        super().__init__(f"[{source}] {message}")
        self.source = source


class RateLimitError(FetchError):
    """Source rejected the request because we hit a rate limit."""


class ParseError(FetchError):
    """Source returned a payload we could not parse."""


class SourceUnavailableError(FetchError):
    """Source temporarily unreachable (5xx, DNS failure, timeout)."""


class CacheError(AutoPaperToPPTError):
    """Local cache could not be read or written."""


class ExportError(AutoPaperToPPTError):
    """An exporter could not produce its artefact."""

    def __init__(self, exporter: str, message: str) -> None:
        super().__init__(f"[{exporter}] {message}")
        self.exporter = exporter
