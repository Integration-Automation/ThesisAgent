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
thesisagents/sources/<your_name>/
├── __init__.py        # exports fetcher_class
├── fetcher.py         # Fetcher subclass + FetcherConfig, endpoint + rate-limit constants
└── parser.py          # raw payload → Paper
```

The directory `thesisagents/sources/<your_name>/` must match the
**source name** the user will pass to `--source <your_name>`. Stick
to lowercase, underscores allowed (e.g. `semantic_scholar`).

The pipeline finds your plugin with a plain
`importlib.import_module(f"thesisagents.sources.{name}")` — see
`load_fetcher` in `thesisagents/fetchers/base.py`. It imports the
package, reads its `fetcher_class` attribute, and instantiates it.
Because plugins live inside the installed package, there is no
`sys.path` manipulation anywhere, at runtime or in the test suite —
if your package imports, your plugin is discoverable.

## Step-by-step

### 1. Pick a name and register it

Add your source name to `thesisagents/core/constants.py`. Names are
declared once as `SOURCE_*` constants and reused everywhere:

```python
SOURCE_YOUR_NAME: str = "your_name"

PLUGIN_SOURCES: tuple[str, ...] = (
    SOURCE_SCHOLAR,
    SOURCE_PUBMED,
    SOURCE_IEEE,
    SOURCE_ACM,
    SOURCE_DBLP,
    SOURCE_CROSSREF,
    SOURCE_OPENAIRE,
    SOURCE_SPRINGER,
    SOURCE_EUROPEPMC,
    SOURCE_DOAJ,
    SOURCE_HAL,
    SOURCE_CORE,
    # ⇣ your new source
    SOURCE_YOUR_NAME,
)
```

`ALL_SOURCES = CORE_SOURCES + PLUGIN_SOURCES` picks it up
automatically. As of today the project ships 15 sources and **all of
them sit in `DEFAULT_SOURCES`** — including the key-gated ones. That
works because a plugin whose requirements aren't met (e.g. `springer`
or `core` without their API keys) raises `ConfigError` at
construction, and the pipeline catches that and silently skips the
source. So add yours to `DEFAULT_SOURCES` too if it's ToS-friendly
for automated use; the soft-skip mechanism means a missing key never
breaks the default mix.

### 2. Declare the rate limit + endpoint

These live at the top of `thesisagents/sources/your_name/fetcher.py`
(there is no separate `config.py` — module constants plus a
`FetcherConfig` class attribute on your fetcher carry everything):

```python
from thesisagents.fetchers.base import Fetcher, FetcherConfig
from thesisagents.fetchers.rate_limit import RateLimit

_SOURCE_NAME = "your_name"
_ENDPOINT = "https://api.your-source.example/v1/search"


class YourFetcher(Fetcher):
    config = FetcherConfig(
        name=_SOURCE_NAME,
        rate_limit=RateLimit(
            requests_per_second=2.0,  # match upstream's published ToS
            burst=1,                  # how many can fire back-to-back
            jitter_seconds=0.3,       # random delay added per request
        ),
        requires_api_key=False,
        enabled_by_default=True,
        # opt_in_env_var="THESISAGENTS_YOUR_NAME_API_KEY",  # key-gated sources
        # opt_out_env_var="THESISAGENTS_DISABLE_...",       # default-on scrapers
    )
```

Mirror a real plugin: `thesisagents/sources/doaj/fetcher.py` and
`thesisagents/sources/openaire/fetcher.py` are the models for a
simple keyless source. Pick a conservative rate limit. The bucket is
the only thing protecting you from getting your IP blocked; if your
source publishes "10 req/s" you should run at 5 req/s with jitter to
account for short bursts. You do not declare a User-Agent — the
shared client registry in `thesisagents/fetchers/http.py` assigns a
per-source `ThesisAgents/... (+source=<name>)` UA automatically (and
a browser UA for the scrape-based `ieee` / `scholar` sources).

### 3. Write the parser

`thesisagents/sources/your_name/parser.py`:

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
  `year`, `venue`, `abstract`, `url`. They are required constructor
  arguments on the `Paper` dataclass, so omitting one is a
  `TypeError` at parse time (`year` / `venue` may be `None`, but you
  must pass them).
- **Strip versioning** from `arxiv_id` (`2401.08741v2 → 2401.08741`).
- **Strip URL prefixes** from `doi` (`https://doi.org/10.x/y → 10.x/y`).
- **HTTPS only** for `pdf_url`. The downloader refuses non-HTTPS.
- Keep the raw payload in `raw` so the LLM-as-agent flow and
  debug logging can use it.

### 4. Write the fetcher

The rest of `thesisagents/sources/your_name/fetcher.py`. The base
class is `thesisagents.fetchers.base.Fetcher`, whose one abstract
method is `async def search(self, query: Query) -> list[Paper]`.
(`fetch_by_id` is optional — override it only if your source supports
direct-by-ID lookup; the default raises `NotImplementedError`.)

```python
from __future__ import annotations

import os
from typing import Any

from thesisagents.core.exceptions import (
    ConfigError, ParseError, RateLimitError, SourceUnavailableError,
)
from thesisagents.core.models import Paper, Query
from thesisagents.fetchers.base import Fetcher, FetcherConfig
from thesisagents.fetchers.http import get_client
from thesisagents.fetchers.rate_limit import RateLimit

from .parser import parse_search_payload

_SOURCE_NAME = "your_name"
_ENDPOINT = "https://api.your-source.example/v1/search"


class YourFetcher(Fetcher):
    """Plugin for the YourSource search API."""

    config = FetcherConfig(
        name=_SOURCE_NAME,
        rate_limit=RateLimit(requests_per_second=2.0, burst=1, jitter_seconds=0.3),
        requires_api_key=True,
        enabled_by_default=True,
        opt_in_env_var="THESISAGENTS_YOUR_NAME_API_KEY",
    )

    def __init__(self) -> None:
        super().__init__()  # builds the token bucket from config.rate_limit
        # OPTIONAL: enforce env-var presence here. `load_fetcher` catches
        # the ConfigError and the pipeline silently skips your plugin.
        self._api_key = os.environ.get("THESISAGENTS_YOUR_NAME_API_KEY")
        if self._api_key is None:
            raise ConfigError(
                "THESISAGENTS_YOUR_NAME_API_KEY not set; YourSource plugin disabled"
            )

    async def search(self, query: Query) -> list[Paper]:
        await self.bucket.acquire()  # token-bucket pacing, from config.rate_limit
        client = await get_client(_SOURCE_NAME)
        try:
            response = await client.get(
                _ENDPOINT,
                params={
                    "q": query.keywords,
                    "limit": query.max_results,
                    "year_from": query.year_from,
                    "year_to": query.year_to,
                },
                headers={"X-API-Key": self._api_key},
            )
        except Exception as err:
            raise SourceUnavailableError(
                _SOURCE_NAME, f"network error: {err}"
            ) from err

        if response.status_code == 429:
            raise RateLimitError(_SOURCE_NAME, "YourSource rate limit hit")
        if response.status_code >= 500:
            raise SourceUnavailableError(
                _SOURCE_NAME, f"server error {response.status_code}"
            )
        if response.status_code >= 400:
            raise ParseError(
                _SOURCE_NAME, f"client error {response.status_code}"
            )

        try:
            payload: dict[str, Any] = response.json()
        except ValueError as err:
            raise ParseError(_SOURCE_NAME, f"invalid JSON: {err}") from err

        return parse_search_payload(payload)[: query.max_results]
```

Notes on the contract:

- Every `FetchError` subclass takes `(source, message)` — the source
  name prefixes the message so multi-source runs stay debuggable.
- Mapping 429 to `RateLimitError` matters: the pipeline retries
  rate-limited sources with exponential backoff
  (`RATE_LIMIT_RETRY_ATTEMPTS` in `thesisagents/core/constants.py`)
  while other sources keep running, but only if it can recognise the
  429. `ParseError` and `SourceUnavailableError` are not retried.
- `await get_client("your_name")` is the only legal way to hit the
  network. It returns the per-source HTTPS-only `httpx.AsyncClient`
  with the source's User-Agent already applied. **Do not construct
  your own `httpx.AsyncClient` or call `httpx.get` / `requests.get`
  directly.**
- `await self.bucket.acquire()` before every request. The bucket is
  built by `Fetcher.__init__` from `config.rate_limit`, which is why
  a custom `__init__` must call `super().__init__()`.

### 5. Wire up the registration

`thesisagents/sources/your_name/__init__.py`:

```python
from .fetcher import YourFetcher

fetcher_class = YourFetcher

__all__ = ["fetcher_class"]
```

`load_fetcher` in `thesisagents/fetchers/base.py` imports the package
and reads `fetcher_class` from its `__init__.py`, then instantiates
it. The attribute name is fixed; the class name is free.

### 6. Save a fixture and write the test

Tests are **hermetic** — no live HTTP. Every fetcher test replays a
recorded fixture through a mock HTTP transport monkeypatched in place
of the real client.

Fixtures are plain files under `tests/fixtures/<your_name>/`, saved
**by hand** from the upstream API: run the search query once against
the real endpoint (curl / browser), prune the response down to a few
representative entries, strip any personal tokens from it, and commit
the file (`.json`, or `.xml` / `.html` for non-JSON sources). See
`tests/fixtures/doaj/llm_security.json` for the shape.

Then write the test. Plugin tests live flat under `tests/sources/` as
`tests/sources/test_your_name.py` (one file covering fetcher +
parser), and share the mock-transport helpers in
`tests/sources/_mock.py` — `MockTransport` is an
`httpx.AsyncBaseTransport` subclass that returns a canned response
and records the request, and `install_mock` monkeypatches
`get_client` inside your fetcher module and clears the shared client
registry (`thesisagents.fetchers.http._CLIENTS`) so the mock is
observed. `pyproject.toml` sets `asyncio_mode = "auto"`, so test
functions are plain `async def` with no decorator:

```python
# tests/sources/test_your_name.py
"""YourSource plugin tests against the recorded fixture."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.sources._mock import MockTransport, install_mock
from thesisagents.core.exceptions import (
    ParseError, RateLimitError, SourceUnavailableError,
)
from thesisagents.core.models import Query
from thesisagents.sources.your_name.fetcher import YourFetcher

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "your_name"
_FIXTURE_BYTES = (_FIXTURE_DIR / "transformer_attention.json").read_bytes()


def _install(monkeypatch, transport):
    install_mock(monkeypatch, "thesisagents.sources.your_name.fetcher", transport)


async def test_search_returns_papers(monkeypatch):
    monkeypatch.setenv("THESISAGENTS_YOUR_NAME_API_KEY", "test-key")
    transport = MockTransport(200, _FIXTURE_BYTES)
    _install(monkeypatch, transport)
    papers = await YourFetcher().search(
        Query(keywords="transformer attention", sources=("your_name",), max_results=5)
    )
    assert len(papers) > 0
    assert papers[0].source == "your_name"
    assert papers[0].title  # always present
    assert papers[0].url.startswith("https://")
    # MockTransport records the request, so assert on the outgoing URL too.
    assert "transformer" in str(transport.received_url)


async def test_search_raises_on_rate_limit(monkeypatch):
    monkeypatch.setenv("THESISAGENTS_YOUR_NAME_API_KEY", "test-key")
    transport = MockTransport(429, b"")
    _install(monkeypatch, transport)
    with pytest.raises(RateLimitError):
        await YourFetcher().search(
            Query(keywords="x", sources=("your_name",), max_results=1)
        )
```

(The arXiv tests, which predate the shared helper, live flat at
`tests/test_arxiv_fetcher.py` / `tests/test_arxiv_parser.py` and
write the same `_MockTransport` + monkeypatched `get_client` +
`_CLIENTS`-clearing pattern out inline — same mechanics, older
layout. New plugins use the shared helper.)

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

### 7. Verify

Run the full chain:

```bash
# Unit tests for your plugin
python -m pytest tests/sources/test_your_name.py

# Integration: the loader can import and construct your plugin
python -c "from thesisagents.fetchers.base import load_fetcher; \
    print(load_fetcher('your_name').config.name)"
# (or eyeball `python -m thesisagents --list-sources`)

# Live smoke (only if you have credentials):
THESISAGENTS_YOUR_NAME_API_KEY=... \
    python -m thesisagents --query "diffusion models" --source your_name \
                   --max 5 --out ./smoke/your_name/

# Lint + security
python -m ruff check thesisagents/sources/your_name/ tests/sources/test_your_name.py
python -m bandit -c pyproject.toml -r thesisagents/
```

All of these must pass before commit (the project's Definition of
Done — the `-c pyproject.toml` flag on bandit is required, without it
bandit ignores the project's skip config and produces false
positives).

### 8. Update docs

- Add your source to the table in [Configuration](configuration.md)
  with its rate limit + any required env var.
- Add your source to the "Available source plugins" table in
  [CLI](cli.md).
- Document any caveats (e.g. "results are limited to titles +
  abstracts; full text not available via the API").

## Common pitfalls

### Constructing your own `httpx.AsyncClient`

**Don't.** Use `await get_client(your_source_name)`. It applies:

- HTTPS-only enforcement (refuses plain HTTP, even after redirect).
- A per-source User-Agent that respects upstream attribution rules
  (browser UA only for the scrape-based `ieee` / `scholar` sources).
- One shared connection pool per source, so concurrent requests
  from the same plugin reuse sockets.

Rate limiting rides alongside it, not inside it: your declared
token bucket paces requests via `await self.bucket.acquire()`, and
the pipeline retries `RateLimitError` with exponential backoff at
the orchestration layer. Constructing your own client bypasses the
HTTPS guard and the shared UA, and skipping the bucket gets you
IP-blocked within a day.

### Hardcoding an API key

**Don't.** Load from `os.environ.get("THESISAGENTS_..._API_KEY")`,
name the same variable in your `FetcherConfig.opt_in_env_var`, and
document it in [Configuration](configuration.md). If the key should
be editable from the desktop GUI, also add a row to the explicit
field list in `thesisagents/gui/pages/settings.py` — the Settings
page maps each known env var to a labelled input, it does not
discover new `THESISAGENTS_*` variables automatically.

### Returning records without `source_id`

`source_id` is a required `Paper` field: the dedup pass keeps the
first-seen record as canonical and preserves its `source` /
`source_id` / `url`, so a missing or unstable ID breaks provenance
and by-ID re-fetching. Note that dedup matches on *every* identity a
record carries — `doi`, `arxiv_id` and a fuzzy
`hash(title + first author + year)`, all at once (see
`Paper.identity_keys`) — so also populate `doi` / `arxiv_id` whenever
the upstream provides them. Omitting a DOI your source actually had
does not just weaken the match, it can *block* one: two records whose
DOIs disagree are deliberately never merged on a fuzzy title match
alone, and a record missing its DOI cannot contribute the exact-key
match that would have resolved the pair.

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
selectors live in `thesisagents/sources/your_name/parser.py`. They
never go under `thesisagents/core/`.

## When a plugin should be promoted to core

You'll know it's time when:

- Every user wants the plugin enabled (no gating env var).
- The plugin uses only the core dep set.
- The upstream has stable rate limits and a stable contract.
- The plugin has had no breaking changes in 6+ months.

To promote: move the name from `PLUGIN_SOURCES` to `CORE_SOURCES` in
`thesisagents/core/constants.py`. That's the whole change — core
sources (`arxiv`, `semantic_scholar`, `openalex`) live under
`thesisagents/sources/<name>/` and load through the same
`load_fetcher` as everything else, so no files move and no imports
change. The user-visible interface (the `--source <name>` flag)
doesn't change either.

This has happened exactly zero times to date — the plugin pattern
turns out to be the right home for most sources permanently.

## Worked examples in-tree

- `thesisagents/sources/arxiv/` — Atom feed (XML) parsed via
  `defusedxml`, no API key, very low rate limit (~1 request per 3
  seconds). Good starting point for a simple read-only source.
- `thesisagents/sources/pubmed/` — XML response, optional API key
  (`THESISAGENTS_NCBI_API_KEY` raises the rate cap), two-step flow
  (esearch → efetch full records). Good example of multi-call
  patterns.
- `thesisagents/sources/ieee/` — dual path: official API when
  `THESISAGENTS_IEEE_API_KEY` is set, otherwise a default-on scrape
  path with a `THESISAGENTS_DISABLE_IEEE_SCRAPING=1` opt-out. Good
  example of runtime path selection + `opt_out_env_var`.
- `thesisagents/sources/scholar/` — pure HTML scrape, default-on with
  a `THESISAGENTS_DISABLE_SCHOLAR_SCRAPING=1` opt-out, plus captcha
  detection and a process-level cooldown. Good example of when not to
  do this — the code is fragile by necessity.
- `thesisagents/sources/springer/` — `ConfigError` at construction
  when the key is missing. Good example of soft-skip integration.
- `thesisagents/sources/europepmc/` — open REST API, no key, JSON.
  Clean example of the over-fetch-then-year-post-filter pattern +
  structured-vs-flat author fallback.
- `thesisagents/sources/doaj/` — open API where the **query rides in
  the URL path** (percent-encoded), not a query parameter. Good
  example of a non-standard endpoint shape.
- `thesisagents/sources/hal/` — Solr-backed API whose fields are
  arrays even when single-valued. Good example of defensive
  array-or-scalar unwrapping.
- `thesisagents/sources/core/` — opt-in via
  `THESISAGENTS_CORE_API_KEY` passed as a Bearer header. Good example
  of header-based auth + soft-skip.
