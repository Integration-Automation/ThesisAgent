"""Project exception hierarchy. Catch at boundaries, never bare `except`."""

from __future__ import annotations


class ThesisAgentsError(Exception):
    """Base for all ThesisAgents errors."""


class ConfigError(ThesisAgentsError):
    """Invalid configuration or environment."""


class FetchError(ThesisAgentsError):
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


class CacheError(ThesisAgentsError):
    """Local cache could not be read or written."""


class ExportError(ThesisAgentsError):
    """An exporter could not produce its artefact."""

    def __init__(self, exporter: str, message: str) -> None:
        super().__init__(f"[{exporter}] {message}")
        self.exporter = exporter
