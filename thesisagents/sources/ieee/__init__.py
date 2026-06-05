"""IEEE Xplore plugin.

Two paths, selected at runtime by env var:

* Official API (preferred) — set ``THESISAGENTS_IEEE_API_KEY`` to your
  IEEE Xplore API key (https://developer.ieee.org/). Surfaces ``pdf_url``
  for documents inside your subscription scope and does not require the
  scraping opt-in.
* Scraping fallback — set ``THESISAGENTS_ENABLE_IEEE_SCRAPING=1``. Calls
  the public website's ``/rest/search`` endpoint and the document page.
  ToS-grey, paced, opt-in only.

At least one of the two env vars must be set or the plugin refuses to
load (the search pipeline catches the ConfigError and skips the source).
"""

from .fetcher import IeeeFetcher

fetcher_class = IeeeFetcher

__all__ = ["fetcher_class"]
