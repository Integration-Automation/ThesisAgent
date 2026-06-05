"""CORE source plugin. Exposes `fetcher_class` for the source registry."""

from .fetcher import CoreFetcher

fetcher_class = CoreFetcher

__all__ = ["fetcher_class"]
