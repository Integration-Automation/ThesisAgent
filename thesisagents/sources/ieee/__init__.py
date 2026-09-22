"""IEEE Xplore plugin.

Two paths, selected at runtime by env var:

* Official API (preferred) — set ``THESISAGENTS_IEEE_API_KEY`` to your
  IEEE Xplore API key (https://developer.ieee.org/). Surfaces ``pdf_url``
  for documents inside your subscription scope.
* Scraping path (default when no API key is set) — calls the public
  website's ``/rest/search`` endpoint and the document page through
  visible Chrome via WebRunner. ToS-grey, paced. Set
  ``THESISAGENTS_DISABLE_IEEE_SCRAPING=1`` to opt out entirely
  (the search pipeline catches the ConfigError and skips the source).
"""

from .fetcher import IeeeFetcher

fetcher_class = IeeeFetcher

__all__ = ["fetcher_class"]
