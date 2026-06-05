"""Core domain models, exceptions, constants, and pipeline."""

from thesisagents.core.constants import (
    DEFAULT_PAGE_SIZE,
    MAX_KEYWORD_LENGTH,
    MAX_RESULTS_PER_SOURCE,
)
from thesisagents.core.exceptions import (
    CacheError,
    ConfigError,
    ExportError,
    FetchError,
    ParseError,
    RateLimitError,
    SourceUnavailableError,
    ThesisAgentsError,
)
from thesisagents.core.models import (
    ExportOptions,
    Paper,
    PaperCollection,
    PaperSummary,
    Query,
    RqResult,
)

__all__ = [
    "DEFAULT_PAGE_SIZE",
    "MAX_KEYWORD_LENGTH",
    "MAX_RESULTS_PER_SOURCE",
    "ThesisAgentsError",
    "CacheError",
    "ConfigError",
    "ExportError",
    "FetchError",
    "ParseError",
    "RateLimitError",
    "SourceUnavailableError",
    "ExportOptions",
    "Paper",
    "PaperCollection",
    "PaperSummary",
    "Query",
    "RqResult",
]
