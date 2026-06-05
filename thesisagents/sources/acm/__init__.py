"""ACM Digital Library plugin via Crossref (member 320).

Crossref indexes every ACM DOI and offers a free, rate-friendly REST API,
which lets us cover ACM without scraping ACM's site directly.
"""

from .fetcher import AcmFetcher

fetcher_class = AcmFetcher

__all__ = ["fetcher_class"]
