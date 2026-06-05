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
SOURCE_EUROPEPMC: str = "europepmc"
SOURCE_DOAJ: str = "doaj"
SOURCE_HAL: str = "hal"
SOURCE_CORE: str = "core"

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
    SOURCE_EUROPEPMC,
    SOURCE_DOAJ,
    SOURCE_HAL,
    SOURCE_CORE,
)
ALL_SOURCES: tuple[str, ...] = CORE_SOURCES + PLUGIN_SOURCES
# Sources tried by default when --source is not given. The full source mix
# is on by default for maximum coverage. ieee and scholar are now also
# default-on (their scrape paths gated by THESISAGENTS_DISABLE_*_SCRAPING
# opt-out env vars instead of the previous opt-in vars). springer still
# raises ConfigError at construction without an API key, so the pipeline
# silently skips it — leaving it in the list is harmless and keeps it
# easy to enable by setting THESISAGENTS_SPRINGER_API_KEY.
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
    # Europe PMC: open REST API, no key, HTTPS-only, life-sciences + preprints
    # + agriculture coverage beyond PubMed. ToS-friendly for automated use, so
    # per docs/source_plugins.md it joins the default mix.
    SOURCE_EUROPEPMC,
    # DOAJ: curated open-access journal index, open keyword API, no key. Every
    # hit is open access (often with a direct PDF link), so it joins the
    # default mix too.
    SOURCE_DOAJ,
    # HAL: France's open archive (CS / maths / physics heavy), open Solr API,
    # no key, full-text PDFs on most deposits — joins the default mix.
    SOURCE_HAL,
    # CORE: largest open-access aggregator (250M+ works). Needs a free API key
    # (THESISAGENTS_CORE_API_KEY); like Springer it sits in the default mix but
    # is silently skipped at construction when the key is absent.
    SOURCE_CORE,
)

EXPORT_BIBTEX: str = "bib"
EXPORT_MARKDOWN: str = "md"
EXPORT_PPTX: str = "pptx"
EXPORT_XLSX: str = "xlsx"
EXPORT_PDF: str = "pdf"
EXPORT_JSON: str = "json"
# RIS is the line-oriented interchange format imported by Zotero, Mendeley,
# EndNote and RefWorks — the BibTeX sibling for the non-LaTeX reference-manager
# crowd. CSV is a flat one-row-per-paper table for quick spreadsheet / grep
# triage, lighter and more diffable than the styled .xlsx.
EXPORT_RIS: str = "ris"
EXPORT_CSV: str = "csv"
# CSL-JSON (Citation Style Language) is the citation format Pandoc and citeproc
# consume to render a bibliography in any of thousands of CSL styles. It rides
# the ``.csl.json`` extension so it never collides with the plain ``json`` dump.
EXPORT_CSL: str = "csl"
ALL_EXPORTS: tuple[str, ...] = (
    EXPORT_BIBTEX,
    EXPORT_MARKDOWN,
    EXPORT_PPTX,
    EXPORT_XLSX,
    EXPORT_PDF,
    EXPORT_JSON,
    EXPORT_RIS,
    EXPORT_CSV,
    EXPORT_CSL,
)
# Formats whose exporter writes ONE artefact for the whole run. The rest
# (``pptx``, ``pdf``) are emitted per paper. Used by the CLI ``--list-exports``
# flag and the MCP ``list_exports`` tool so both describe a format the same way.
AGGREGATE_EXPORTS: frozenset[str] = frozenset({
    EXPORT_BIBTEX,
    EXPORT_MARKDOWN,
    EXPORT_XLSX,
    EXPORT_JSON,
    EXPORT_RIS,
    EXPORT_CSV,
    EXPORT_CSL,
})
# Canonical one-line description per export format. Single source of truth so
# the CLI help, the CLI ``--list-exports`` flag and the MCP ``list_exports``
# tool never drift. Lives here (dependency-free) rather than in the MCP server
# so the CLI can use it without importing the optional ``mcp`` extra.
EXPORT_DESCRIPTIONS: dict[str, str] = {
    EXPORT_PPTX: (
        "Thesis-style PowerPoint deck (rich / enriched / lightweight tiers; "
        "dark mode default). One deck per paper in search mode."
    ),
    EXPORT_XLSX: "Styled Excel workbook — one ranked row per paper.",
    EXPORT_MARKDOWN: (
        "Markdown summary — title, authors, identifiers and abstract per paper."
    ),
    EXPORT_BIBTEX: "BibTeX file for LaTeX-based reference managers.",
    EXPORT_JSON: "Structured JSON round-trip of the PaperCollection.",
    EXPORT_RIS: "RIS interchange imported by Zotero / Mendeley / EndNote / RefWorks.",
    EXPORT_CSV: "Flat one-row-per-paper CSV for spreadsheets / quick grep triage.",
    EXPORT_CSL: "CSL-JSON for Pandoc / citeproc — render a bibliography in any CSL style.",
    EXPORT_PDF: (
        "Per-paper PDF download where a PDF URL is resolvable, not an aggregate file."
    ),
}
