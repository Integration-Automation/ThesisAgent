"""OpenAlex source plugin. Exposes `fetcher_class` for the source registry."""

from .fetcher import OpenAlexFetcher

fetcher_class = OpenAlexFetcher

__all__ = ["fetcher_class"]
