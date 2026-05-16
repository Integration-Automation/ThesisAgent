"""Fetcher base class and source registry. Each source plugin subclasses Fetcher."""

from __future__ import annotations

import importlib
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from autopapertoppt.core.exceptions import ConfigError
from autopapertoppt.core.models import Paper, Query
from autopapertoppt.fetchers.rate_limit import RateLimit, TokenBucket
from autopapertoppt.utils.logging import get_logger

_LOG = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class FetcherConfig:
    """Static configuration block declared by every source plugin."""

    name: str
    rate_limit: RateLimit
    requires_api_key: bool = False
    enabled_by_default: bool = True
    opt_in_env_var: str | None = None


class Fetcher(ABC):
    """Strategy interface every source plugin implements."""

    config: FetcherConfig

    def __init__(self) -> None:
        self._bucket = TokenBucket(self.config.rate_limit)

    @property
    def bucket(self) -> TokenBucket:
        return self._bucket

    @abstractmethod
    async def search(self, query: Query) -> list[Paper]:
        """Run the query against this source and return up to `query.max_results`."""

    async def fetch_by_id(self, identifier: str) -> Paper:
        """Fetch a single paper by source-native identifier.

        Subclasses that support direct-by-ID lookup MUST override this. The
        default raises so callers can detect unsupported sources cleanly.
        """
        raise NotImplementedError(
            f"source '{self.config.name}' does not support fetch_by_id"
        )


_SOURCES_DIR = Path(__file__).resolve().parents[2] / "sources"


def _ensure_sources_on_path() -> None:
    sources_dir = str(_SOURCES_DIR)
    if sources_dir not in sys.path:
        sys.path.insert(0, sources_dir)


def load_fetcher(name: str) -> Fetcher:
    """Load and instantiate the fetcher plugin for the given source name."""
    _ensure_sources_on_path()
    try:
        module = importlib.import_module(name)
    except ImportError as err:
        raise ConfigError(f"unknown or unavailable source plugin: {name}") from err
    fetcher_class = getattr(module, "fetcher_class", None)
    if fetcher_class is None:
        raise ConfigError(
            f"source plugin '{name}' does not expose `fetcher_class`"
        )
    instance = fetcher_class()
    if not isinstance(instance, Fetcher):
        raise ConfigError(
            f"source plugin '{name}' fetcher_class did not produce a Fetcher"
        )
    _LOG.debug("Loaded fetcher plugin %s", name)
    return instance
