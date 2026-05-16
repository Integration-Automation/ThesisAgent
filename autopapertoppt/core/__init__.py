"""Core domain models, exceptions, constants, and pipeline."""

from autopapertoppt.core.constants import (
    DEFAULT_PAGE_SIZE,
    MAX_KEYWORD_LENGTH,
    MAX_RESULTS_PER_SOURCE,
)
from autopapertoppt.core.exceptions import (
    AutoPaperToPPTError,
    CacheError,
    ConfigError,
    ExportError,
    FetchError,
    ParseError,
    RateLimitError,
    SourceUnavailableError,
)
from autopapertoppt.core.models import (
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
    "AutoPaperToPPTError",
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
