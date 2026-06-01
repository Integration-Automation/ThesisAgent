"""Google Scholar plugin (opt-in scraping).

Set ``AUTOPAPERTOPPT_ENABLE_SCHOLAR_SCRAPING=1`` to enable. Google's terms
forbid bulk automated scraping; this plugin paces requests aggressively
(1 every 10s with jitter) and surfaces a clear error when the upstream
returns the CAPTCHA / sorry page.
"""

from scholar.fetcher import ScholarFetcher

fetcher_class = ScholarFetcher

__all__ = ["fetcher_class"]
