"""Springer Nature source plugin. Exposes `fetcher_class` for the source registry."""

from .fetcher import SpringerFetcher

fetcher_class = SpringerFetcher

__all__ = ["fetcher_class"]
