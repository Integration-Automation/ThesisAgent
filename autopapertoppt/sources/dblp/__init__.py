"""DBLP source plugin. Exposes `fetcher_class` for the source registry."""

from dblp.fetcher import DblpFetcher

fetcher_class = DblpFetcher

__all__ = ["fetcher_class"]
