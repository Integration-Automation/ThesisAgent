"""HAL source plugin. Exposes `fetcher_class` for the source registry."""

from .fetcher import HalFetcher

fetcher_class = HalFetcher

__all__ = ["fetcher_class"]
