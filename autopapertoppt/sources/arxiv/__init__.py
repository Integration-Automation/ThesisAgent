"""arXiv source plugin. Exposes `fetcher_class` for the source registry."""

from .fetcher import ArxivFetcher

fetcher_class = ArxivFetcher

__all__ = ["fetcher_class"]
