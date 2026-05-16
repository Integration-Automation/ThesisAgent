"""OpenAIRE Graph source plugin. Exposes `fetcher_class` for the source registry."""

from openaire.fetcher import OpenAireFetcher

fetcher_class = OpenAireFetcher

__all__ = ["fetcher_class"]
