"""Project-wide constants. Module-level so we never repeat magic numbers."""

from __future__ import annotations

DEFAULT_PAGE_SIZE: int = 25
MAX_RESULTS_PER_SOURCE: int = 200
MAX_KEYWORD_LENGTH: int = 256
CACHE_TTL_SECONDS: int = 86_400

HTTP_TIMEOUT_SECONDS: float = 30.0
HTTP_MAX_RETRIES: int = 3
HTTP_BACKOFF_BASE_SECONDS: float = 1.5

# Pipeline-level retry on RateLimitError. Sources that report 429 get retried
# this many times with exponential backoff before the source is reported as
# failed and skipped. 3 attempts at 5s/10s/20s = up to 35s of waiting per
# rate-limited source. Other sources keep running concurrently.
RATE_LIMIT_RETRY_ATTEMPTS: int = 3
RATE_LIMIT_RETRY_BASE_SECONDS: float = 5.0

ABSTRACT_TRUNCATE_CHARS: int = 1200

SOURCE_ARXIV: str = "arxiv"
SOURCE_SEMANTIC_SCHOLAR: str = "semantic_scholar"
SOURCE_OPENALEX: str = "openalex"
SOURCE_SCHOLAR: str = "scholar"
SOURCE_PUBMED: str = "pubmed"
SOURCE_IEEE: str = "ieee"
SOURCE_ACM: str = "acm"
SOURCE_DBLP: str = "dblp"
SOURCE_CROSSREF: str = "crossref"
SOURCE_OPENAIRE: str = "openaire"
SOURCE_SPRINGER: str = "springer"

CORE_SOURCES: tuple[str, ...] = (
    SOURCE_ARXIV,
    SOURCE_SEMANTIC_SCHOLAR,
    SOURCE_OPENALEX,
)
PLUGIN_SOURCES: tuple[str, ...] = (
    SOURCE_SCHOLAR,
    SOURCE_PUBMED,
    SOURCE_IEEE,
    SOURCE_ACM,
    SOURCE_DBLP,
    SOURCE_CROSSREF,
    SOURCE_OPENAIRE,
    SOURCE_SPRINGER,
)
ALL_SOURCES: tuple[str, ...] = CORE_SOURCES + PLUGIN_SOURCES
# Sources tried by default when --source is not given. The full source mix
# is on by default for maximum coverage. ieee and scholar are now also
# default-on (their scrape paths gated by AUTOPAPERTOPPT_DISABLE_*_SCRAPING
# opt-out env vars instead of the previous opt-in vars). springer still
# raises ConfigError at construction without an API key, so the pipeline
# silently skips it — leaving it in the list is harmless and keeps it
# easy to enable by setting AUTOPAPERTOPPT_SPRINGER_API_KEY.
DEFAULT_SOURCES: tuple[str, ...] = (
    SOURCE_ARXIV,
    SOURCE_SEMANTIC_SCHOLAR,
    SOURCE_OPENALEX,
    SOURCE_PUBMED,
    SOURCE_IEEE,
    SOURCE_ACM,
    SOURCE_DBLP,
    SOURCE_CROSSREF,
    SOURCE_OPENAIRE,
    SOURCE_SPRINGER,
    SOURCE_SCHOLAR,
)

EXPORT_BIBTEX: str = "bib"
EXPORT_MARKDOWN: str = "md"
EXPORT_PPTX: str = "pptx"
EXPORT_XLSX: str = "xlsx"
EXPORT_PDF: str = "pdf"
EXPORT_JSON: str = "json"
ALL_EXPORTS: tuple[str, ...] = (
    EXPORT_BIBTEX,
    EXPORT_MARKDOWN,
    EXPORT_PPTX,
    EXPORT_XLSX,
    EXPORT_PDF,
    EXPORT_JSON,
)
