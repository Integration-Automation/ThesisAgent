"""DOAJ source plugin. Exposes `fetcher_class` for the source registry."""

from .fetcher import DoajFetcher

fetcher_class = DoajFetcher

__all__ = ["fetcher_class"]
