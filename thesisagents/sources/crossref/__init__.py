"""Crossref source plugin. Exposes `fetcher_class` for the source registry."""

from .fetcher import CrossrefFetcher

fetcher_class = CrossrefFetcher

__all__ = ["fetcher_class"]
