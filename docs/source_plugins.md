# Source plugin authoring guide

Adding a new academic source — your own institution's repository,
a vendor API, a regional preprint server — without touching the
core engine. Plugins are how ThesisAgents stays extensible
while keeping its dependency surface small.

## When to write a plugin

Write a source plugin when ANY of:

1. **The source needs a heavy or optional dependency** (vendor SDK,
   Selenium for JS-rendered pages). Putting it in core forces every
   user to install it; putting it in a plugin makes it opt-in.
2. **The source's failure mode could break the rest of the pipeline.**
   A flaky upstream should fail in isolation; aggregating other
   sources' results should still succeed.
3. **The source has independent release cadence.** A Scholar HTML
   layout change should be patchable without re-shipping the engine.

If your source uses only `httpx` and returns clean JSON, it's
arguably core material — but the plugin pattern is cheap, so going
through it is usually the right default.

## File layout

```
sources/<your_name>/
├── __init__.py        # exports fetcher_class
├── fetcher.py         # the actual plugin
├── parser.py          # raw payload → Paper
└── config.py          # RateLimit + endpoint URLs
```

The directory `sources/<your_name>/` must match the **source name**
the user will pass to `--source <your_name>`. Stick to lowercase,
underscores allowed (e.g. `semantic_scholar`).

The pipeline finds your plugin by injecting `sources/` into
`sys.path` at startup. The injection is done by
`thesisagents.app.source_manager` for runtime and by
`tests/conftest.py` for the test suite — you don't need to touch
either.

## Step-by-step

### 1. Pick a name and register it

Add your source name to `thesisagents/core/constants.py`:

```python
PLUGIN_SOURCES: tuple[str, ...] = (
    # existing plugin sources
    "ieee",
    "springer",
    "scholar",
    # ⇣ your new source
    "your_name",
)
```

`ALL_SOURCES = CORE_SOURCES + PLUGIN_SOURCES` picks it up
automatically. If your plugin should be in the default search mix
(no API key, ToS-friendly), also add it to `DEFAULT_SOURCES`. If
it needs an opt-in env var, leave it out — the pipeline will skip
it silently when its `Fetcher` raises `ConfigError` at
construction.

### 2. Declare the rate limit + endpoint

`sources/your_name/config.py`:

```python
from thesisagents.fetchers.rate_limit import RateLimit

ENDPOINT = "https://api.your-source.example/v1/search"

RATE_LIMIT = RateLimit(
    requests_per_second=2,    # match upstream's published ToS
    burst=4,                   # how many can fire back-to-back
    jitter_seconds=0.2,        # random delay added per request
)

USER_AGENT = "ThesisAgents/0.1 (+https://github.com/Integration-Automation/ThesisAgents)"
```

Pick a conservative rate limit. The bucket is the only thing
protecting you from getting your IP blocked; if your source
publishes "10 req/s" you should run at 5 req/s with jitter to
account for short bursts.

### 3. Write the parser

`sources/your_name/parser.py`:

```python
from __future__ import annotations

from typing import Any

from thesisagents.core.models import Paper


def parse_search_payload(payload: dict[str, Any]) -> list[Paper]:
    """Convert the source's raw search response into a list of Paper."""
    return [_parse_one(entry) for entry in payload.get("results", [])]


def _parse_one(entry: dict[str, Any]) -> Paper:
    return Paper(
        source="your_name",
        source_id=str(entry["id"]),
        title=entry["title"].strip(),
        authors=tuple(a["name"] for a in entry.get("authors", [])),
        year=entry.get("year"),
        venue=entry.get("venue"),
        abstract=entry.get("abstract", "") or "",
        url=entry["landing_page_url"],
        doi=entry.get("doi"),
        arxiv_id=entry.get("arxiv_id"),
        pdf_url=_pick_pdf_url(entry),
        citation_count=entry.get("citation_count"),
        raw=entry,
    )


def _pick_pdf_url(entry: dict[str, Any]) -> str | None:
    """Return the publicly-fetchable PDF URL or None."""
    for link in entry.get("links", []):
        if link.get("type") == "application/pdf" and link["url"].startswith("https://"):
            return link["url"]
    return None
```

Field rules:

- **Always** populate `source`, `source_id`, `title`, `authors`,
  `abstract`, `url`. The pipeline will reject papers missing any
  required field.
- **Strip versioning** from `arxiv_id` (`2401.08741v2 → 2401.08741`).
- **Strip URL prefixes** from `doi` (`https://doi.org/10.x/y → 10.x/y`).
- **HTTPS only** for `pdf_url`. The downloader refuses non-HTTPS.
- Keep the raw payload in `raw` so the LLM-as-agent flow and
  debug logging can use it.

### 4. Write the fetcher

`sources/your_name/fetcher.py`:

```python
from __future__ import annotations

import os
from typing import Any

from thesisagents.core.exceptions import (
    ConfigError, ParseError, RateLimitError, SourceUnavailableError,
)
from thesisagents.core.models import Paper, Query
from thesisagents.fetchers.base import Fetcher
from thesisagents.fetchers.http import get_client

from .config import ENDPOINT, RATE_LIMIT, USER_AGENT
from .parser import parse_search_payload


class YourFetcher(Fetcher):
    """Plugin for the YourSource search API."""

    name = "your_name"
    rate_limit = RATE_LIMIT
    user_agent = USER_AGENT

    def __init__(self) -> None:
        # OPTIONAL: enforce env-var presence here. The pipeline will
        # catch ConfigError and silently skip your plugin.
        self._api_key = os.environ.get("THESISAGENTS_YOUR_NAME_API_KEY")
        if self._api_key is None:
            raise ConfigError(
                "THESISAGENTS_YOUR_NAME_API_KEY not set; YourSource plugin disabled"
            )

    async def fetch(self, query: Query) -> list[Paper]:
        client = get_client("your_name")
        try:
            response = await client.get(
                ENDPOINT,
                params={
                    "q": query.keywords,
                    "limit": query.max_results,
                    "year_from": query.year_from,
                    "year_to": query.year_to,
                },
                headers={"X-API-Key": self._api_key},
            )
            response.raise_for_status()
        except RateLimitError:
            raise
        except Exception as err:
            raise SourceUnavailableError(f"YourSource unreachable: {err}") from err

        try:
            payload: dict[str, Any] = response.json()
        except ValueError as err:
            raise ParseError(f"YourSource returned non-JSON: {err}") from err

        return parse_search_payload(payload)
```

`get_client("your_name")` is the only legal way to hit the network.
It returns the per-source HTTPS-only `httpx.AsyncClient` with your
plugin's User-Agent + rate-limit decorator + retry policy already
applied. **Do not construct your own `httpx.AsyncClient` or call
`httpx.get` / `requests.get` directly.**

### 5. Wire up the registration

`sources/your_name/__init__.py`:

```python
from .fetcher import YourFetcher

fetcher_class = YourFetcher

__all__ = ["fetcher_class"]
```

The pipeline's plugin loader reads `fetcher_class` from each
source's `__init__.py` and instantiates it. The attribute name is
fixed; the class name is free.

### 6. Record a fixture and write the test

Tests are **hermetic** — no live HTTP. Every fetcher test uses a
recorded fixture loaded via a monkey-patched HTTP transport.

Record one fixture per test scenario:

```bash
python scripts/record_fixture.py --source your_name \
    --query "transformer attention" --max 5
```

This writes `tests/fixtures/your_name/transformer-attention.json`
(or `.html` / `.xml` for non-JSON sources). The recording script
strips any user-specific tokens from the request before saving.

Then write the test:

```python
# tests/sources/your_name/test_your_name.py
import json
from pathlib import Path

import pytest
from thesisagents.core.models import Query
from your_name.fetcher import YourFetcher


@pytest.fixture()
def transformer_fixture():
    p = Path(__file__).parent.parent.parent / "fixtures" / "your_name" / "transformer-attention.json"
    return json.loads(p.read_text(encoding="utf-8"))


def test_fetcher_parses_transformer_results(http_recorder, transformer_fixture, monkeypatch):
    monkeypatch.setenv("THESISAGENTS_YOUR_NAME_API_KEY", "test-key")
    http_recorder.add_response(
        url="https://api.your-source.example/v1/search",
        params={"q": "transformer attention", "limit": 5},
        json=transformer_fixture,
    )
    fetcher = YourFetcher()
    papers = await fetcher.fetch(
        Query(keywords="transformer attention", sources=("your_name",), max_results=5)
    )
    assert len(papers) > 0
    assert papers[0].source == "your_name"
    assert papers[0].title  # always present
    assert papers[0].url.startswith("https://")
```

Add tests for:

- **Happy path** (above) — recorded fixture parses cleanly.
- **Empty result set** — fixture with zero entries returns `[]`.
- **Missing optional fields** — entries with no DOI / no abstract /
  no year still parse without raising.
- **Malformed JSON** — `ParseError` raised on broken response.
- **HTTP 429** — `RateLimitError` raised.
- **HTTP 500** — `SourceUnavailableError` raised.
- **Unicode** — title / authors in CJK / Cyrillic / Devanagari
  parse cleanly.
- **No API key** (if your plugin needs one) — `ConfigError` raised
  at `__init__`.

The `http_recorder` fixture is defined in `tests/conftest.py`.

### 7. Verify

Run the full chain:

```bash
# Unit tests for your plugin
python -m pytest tests/sources/your_name/

# Integration: plugin shows up in the source list
python -c "from thesisagents.app.source_manager import list_sources; \
    print('your_name' in [s.name for s in list_sources()])"

# Live smoke (only if you have credentials):
THESISAGENTS_YOUR_NAME_API_KEY=... \
    thesisagents --query "diffusion models" --source your_name --max 5 \
                   --out ./smoke/your_name/

# Lint + security
python -m ruff check sources/your_name/
python -m bandit -c pyproject.toml -r sources/your_name/
```

All three must pass before commit (the project's Definition of Done).

### 8. Update docs

- Add your source to the table in [Configuration](configuration.md)
  with its rate limit + any required env var.
- Add your source to the "Available source plugins" table in
  [CLI](cli.md).
- Document any caveats (e.g. "results are limited to titles +
  abstracts; full text not available via the API").

## Common pitfalls

### Constructing your own `httpx.AsyncClient`

**Don't.** Use `get_client(your_source_name)`. It applies:

- HTTPS-only enforcement (refuses plain HTTP, even after redirect).
- Your declared rate-limit token bucket.
- Exponential backoff on 429 / 5xx (which also goes through the bucket).
- A per-source User-Agent that respects upstream attribution rules.

Constructing your own bypasses all four; you'll get IP-blocked
within a day.

### Hardcoding an API key

**Don't.** Load from `os.environ.get("THESISAGENTS_..._API_KEY")`
and document the variable in [Configuration](configuration.md).
The GUI's Settings page picks up any variable matching the
`THESISAGENTS_..._API_KEY` pattern automatically when extended.

### Returning records without `source_id`

The dedup pass uses `source_id` as a fallback when DOI / arXiv ID
are missing. Without it, every record from your source is treated
as a separate paper even when titles match.

### Returning HTML rendered into `abstract`

The exporter expects plain text. If your source returns HTML,
strip it with `beautifulsoup4`:

```python
from bs4 import BeautifulSoup

raw_html = entry.get("abstract_html", "")
abstract = BeautifulSoup(raw_html, "lxml").get_text(separator=" ").strip()
```

### Forgetting to set `pdf_url=None` when the link isn't public

A paywalled PDF link with `https://` will pass the HTTPS check but
return 403 at download time. Better to leave `pdf_url=None` so the
paywall gate triggers correctly.

### Using `xml.etree` on untrusted input

For sources that return XML (PubMed, arXiv Atom feed, ...), use
`defusedxml` not `xml.etree`. The bandit rule `B405` will flag the
unsafe usage at lint time.

### Putting source-specific HTML selectors in core

If your plugin needs to parse HTML with `bs4` selectors, those
selectors live in `sources/your_name/parser.py`. They never go
under `thesisagents/core/`.

## When a plugin should be promoted to core

You'll know it's time when:

- Every user wants the plugin enabled (no opt-in env var).
- The plugin uses only the core dep set.
- The upstream has stable rate limits and a stable contract.
- The plugin has had no breaking changes in 6+ months.

To promote: move the code into `thesisagents/core/<source>/`,
update the import paths in `core_manager`, and remove the entry
from `PLUGIN_SOURCES` in `core/constants.py`. The user-visible
interface (the `--source <name>` flag) doesn't change.

This has happened exactly zero times to date — the plugin pattern
turns out to be the right home for most sources permanently.

## Worked examples in-tree

- `sources/arxiv/` — JSON / Atom hybrid, no API key, low rate
  limit. Good starting point for a simple read-only source.
- `sources/pubmed/` — XML response, optional API key, two-step
  flow (search → fetch full record). Good example of multi-call
  patterns.
- `sources/ieee/` — dual API + scrape paths gated by different
  env vars. Good example of optional dependency handling.
- `sources/scholar/` — pure HTML scrape with Selenium fallback,
  ToS-opt-in. Good example of when not to do this — the code is
  fragile by necessity.
- `sources/springer/` — `ConfigError` at construction when key is
  missing. Good example of soft-skip integration.
- `sources/europepmc/` — open REST API, no key, JSON. Clean example of
  the over-fetch-then-year-post-filter pattern + structured-vs-flat
  author fallback.
- `sources/doaj/` — open API where the **query rides in the URL path**
  (percent-encoded), not a query parameter. Good example of a
  non-standard endpoint shape.
- `sources/hal/` — Solr-backed API whose fields are arrays even when
  single-valued. Good example of defensive array-or-scalar unwrapping.
- `sources/core/` — opt-in via `THESISAGENTS_CORE_API_KEY` passed as a
  Bearer header. Good example of header-based auth + soft-skip.
