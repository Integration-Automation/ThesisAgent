"""Crossref source plugin. Exposes `fetcher_class` for the source registry."""

from .citations import CrossrefCitations
from .fetcher import CrossrefFetcher

fetcher_class = CrossrefFetcher
citation_provider_class = CrossrefCitations

__all__ = ["citation_provider_class", "fetcher_class"]
