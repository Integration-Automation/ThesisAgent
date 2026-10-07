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


class CitationNotAvailableError(FetchError):
    """A citation provider has no answer for this paper, and that is expected.

    Raised when the paper carries no identifier the provider understands, the
    provider does not know the paper, or the provider cannot serve the
    direction asked for (Crossref has references but not citing works).

    Kept apart from the other ``FetchError`` types because it is not a
    failure: snowballing moves on to the next provider without reporting an
    error. A broken provider raises ``SourceUnavailableError`` or
    ``RateLimitError`` instead, and those are reported.

    Example: asking Crossref for the references of a paper that has no DOI.
    """


class CacheError(ThesisAgentsError):
    """Local cache could not be read or written."""


class ExportError(ThesisAgentsError):
    """An exporter could not produce its artefact."""

    def __init__(self, exporter: str, message: str) -> None:
        super().__init__(f"[{exporter}] {message}")
        self.exporter = exporter
