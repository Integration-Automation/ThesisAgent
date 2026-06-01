"""Semantic Scholar plugin. Free Graph API — no key needed for low volume."""

from semantic_scholar.fetcher import SemanticScholarFetcher

fetcher_class = SemanticScholarFetcher

__all__ = ["fetcher_class"]
