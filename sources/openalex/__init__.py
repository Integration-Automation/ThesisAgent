"""OpenAlex source plugin. Exposes `fetcher_class` for the source registry."""

from openalex.fetcher import OpenAlexFetcher

fetcher_class = OpenAlexFetcher

__all__ = ["fetcher_class"]
