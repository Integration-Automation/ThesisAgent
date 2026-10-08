"""Semantic Scholar plugin. Free Graph API — no key needed for low volume."""

from .citations import SemanticScholarCitations
from .fetcher import SemanticScholarFetcher

fetcher_class = SemanticScholarFetcher
citation_provider_class = SemanticScholarCitations

__all__ = ["citation_provider_class", "fetcher_class"]
