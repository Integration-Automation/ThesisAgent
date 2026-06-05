"""Europe PMC source plugin. Exposes `fetcher_class` for the source registry."""

from .fetcher import EuropePmcFetcher

fetcher_class = EuropePmcFetcher

__all__ = ["fetcher_class"]
