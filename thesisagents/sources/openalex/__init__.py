"""OpenAlex source plugin. Exposes `fetcher_class` for the source registry."""

from .citations import OpenAlexCitations
from .fetcher import OpenAlexFetcher

fetcher_class = OpenAlexFetcher
citation_provider_class = OpenAlexCitations

__all__ = ["citation_provider_class", "fetcher_class"]
