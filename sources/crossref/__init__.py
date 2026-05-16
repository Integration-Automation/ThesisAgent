"""Crossref source plugin. Exposes `fetcher_class` for the source registry."""

from crossref.fetcher import CrossrefFetcher

fetcher_class = CrossrefFetcher

__all__ = ["fetcher_class"]
