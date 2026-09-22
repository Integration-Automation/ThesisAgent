"""Google Scholar plugin (default-on scraping).

Set ``THESISAGENTS_DISABLE_SCHOLAR_SCRAPING=1`` to opt out. Google's terms
forbid bulk automated scraping; this plugin paces requests aggressively
(1 every 10s with jitter) and surfaces a clear error when the upstream
returns the CAPTCHA / sorry page.
"""

from .fetcher import ScholarFetcher

fetcher_class = ScholarFetcher

__all__ = ["fetcher_class"]
