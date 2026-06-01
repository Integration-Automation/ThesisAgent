"""PubMed plugin via NCBI E-utilities (esearch + efetch)."""

from .fetcher import PubMedFetcher

fetcher_class = PubMedFetcher

__all__ = ["fetcher_class"]
