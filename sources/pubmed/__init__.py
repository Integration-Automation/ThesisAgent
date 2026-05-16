"""PubMed plugin via NCBI E-utilities (esearch + efetch)."""

from pubmed.fetcher import PubMedFetcher

fetcher_class = PubMedFetcher

__all__ = ["fetcher_class"]
