# Configuration reference

Every knob the user can turn — environment variables, CLI flags
that map to env vars, GUI Settings page fields, and the on-disk
QSettings store. This page is the single source of truth; other
docs link here.

## Environment variables

All env vars are read **at the moment a fetcher or extra is
constructed**, not lazily — so a `set ANTHROPIC_API_KEY=...`
after the CLI is running has no effect. Set them in the shell
before launching, or use the GUI's Settings page, which mirrors
each value into `os.environ` before any fetcher initialises.

### LLM enrichment

| Variable | Default | Effect |
|---|---|---|
| `ANTHROPIC_API_KEY` | unset | Required for the Python `--enrich` pipeline. Triggers auto-enrichment when set (override with `--lightweight`). Never needed for the LLM-as-agent flow over MCP. |
| `AUTOPAPERTOPPT_LLM_MODEL` | `claude-opus-4-7` | Override the model used when `--enrich` is on. `--llm-model` on the CLI takes precedence. |

### Source plugin keys

| Variable | Default | Effect |
|---|---|---|
| `AUTOPAPERTOPPT_S2_API_KEY` | unset | Higher rate limit on the Semantic Scholar plugin (1/s anonymous → 10/s with key). |
| `AUTOPAPERTOPPT_NCBI_API_KEY` | unset | Raises PubMed's anonymous limit from 3 req/s to 10 req/s. |
| `AUTOPAPERTOPPT_IEEE_API_KEY` | unset | Switches the IEEE plugin from the scrape fallback to the official Xplore API (`ieeexploreapi.ieee.org`). Surfaces `pdf_url` for papers in your subscription scope. Apply at <https://developer.ieee.org/>. |
| `AUTOPAPERTOPPT_ENABLE_IEEE_SCRAPING` | unset | Must be `=1` to enable the IEEE scrape fallback. Not needed when `AUTOPAPERTOPPT_IEEE_API_KEY` is set. IEEE Xplore terms of use are grey on automated traffic — opt in deliberately. |
| `AUTOPAPERTOPPT_SPRINGER_API_KEY` | unset | Free key from <https://dev.springernature.com/>. **Required** for the Springer plugin — it raises `ConfigError` at construction without a key, which the pipeline silently skips. |
| `AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN` | unset | Crossref Plus subscriber token. Attached to requests as `Crossref-Plus-API-Token: Bearer <token>`. Raises rate limits and improves cache freshness on the `acm` and `crossref` plugins. |
| `AUTOPAPERTOPPT_ENABLE_SCHOLAR_SCRAPING` | unset | Must be `=1` to enable the Google Scholar plugin. Scholar's terms of use forbid scraping — off by default. |
| `AUTOPAPERTOPPT_CONTACT_EMAIL` | unset | Sent to Crossref / OpenAlex as the `mailto=` parameter (entry into their polite pool) and to NCBI as `tool` / `email` headers. Set this for any non-trivial workload. |

### PDF download

| Variable | Default | Effect |
|---|---|---|
| `AUTOPAPERTOPPT_PDF_COOKIES_FILE` | unset | Path to a Netscape-format `cookies.txt`. When set, cookies whose `domain` field matches the host of an outbound PDF download are attached to that request only. **You** are responsible for compliance with the relevant publisher's terms of service. A startup warning fires when the env var is loaded. |

### Logging / debug

| Variable | Default | Effect |
|---|---|---|
| `AUTOPAPERTOPPT_LOG_LEVEL` | `INFO` | Set to `DEBUG` for verbose tracing — every HTTP request, every fetcher cache hit/miss, every rate-limit wait. `WARNING` quiets the normal per-paper progress line. |

### Qt / GUI

These are read by Qt itself (not by AutoPaperToPPT), but the GUI
sets sensible defaults when they're absent. See the [GUI doc](gui.md)
for the full HiDPI story.

| Variable | Default | Effect |
|---|---|---|
| `QT_ENABLE_HIGHDPI_SCALING` | `1` (set by app.py if unset) | Enables Qt's HiDPI scaling. |
| `QT_SCALE_FACTOR_ROUNDING_POLICY` | `PassThrough` (set by app.py if unset) | Lets fractional scale factors (125%, 150%) flow through unchanged. |
| `QT_QPA_PLATFORM` | OS default | Set to `offscreen` for headless / CI runs of the GUI. |

## QSettings on-disk store

When the GUI's **Settings → Save** is clicked, the values land
in a per-OS persistent store **and** are mirrored into
`os.environ` for the current process. Each subsequent launch
of the GUI calls `apply_saved_env()` at startup, so the env
vars are re-applied automatically.

### Storage locations

| OS | Path |
|---|---|
| Windows | `HKEY_CURRENT_USER\Software\AutoPaperToPPT\AutoPaperToPPT` |
| macOS | `~/Library/Preferences/com.AutoPaperToPPT.AutoPaperToPPT.plist` |
| Linux | `~/.config/AutoPaperToPPT/AutoPaperToPPT.conf` |

The QSettings organisation name is `AutoPaperToPPT` and the
application name is `AutoPaperToPPT`. Tests inject a temporary
storage path via `QSettings.setPath(...)` so they never touch
the user's real store.

### Keys

| QSettings key | Env var mirrored to | Type |
|---|---|---|
| `api/anthropic` | `ANTHROPIC_API_KEY` | string |
| `api/semantic_scholar` | `AUTOPAPERTOPPT_S2_API_KEY` | string |
| `api/ncbi` | `AUTOPAPERTOPPT_NCBI_API_KEY` | string |
| `api/ieee` | `AUTOPAPERTOPPT_IEEE_API_KEY` | string |
| `api/springer` | `AUTOPAPERTOPPT_SPRINGER_API_KEY` | string |
| `api/crossref_plus` | `AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN` | string |
| `contact/email` | `AUTOPAPERTOPPT_CONTACT_EMAIL` | string |
| `pdf/cookies_file` | `AUTOPAPERTOPPT_PDF_COOKIES_FILE` | string (absolute path) |
| `ui/language` | (not mirrored) | string — a BCP-47 code from the 14 supported languages |

## CLI flags ↔ env var equivalents

Many CLI flags have an environment-variable counterpart so
unattended deployments don't need to pass long argument lists.

| CLI flag | Env var | Notes |
|---|---|---|
| `--llm-model MODEL` | `AUTOPAPERTOPPT_LLM_MODEL` | CLI wins if both are set. |

That's the only one today; everything else is per-source plugin
config above. The CLI explicitly does NOT read API keys via
flags (no `--anthropic-key`) — passing a key on the command
line writes it to shell history, which is a security footgun.

## CLI defaults

Behaviour you don't see in `--help` because it's hard-coded:

| Setting | Value | Where |
|---|---|---|
| Default page size (`--max`) | `25` | `autopapertoppt.core.constants.DEFAULT_PAGE_SIZE` |
| Max results per source (`--max` ceiling) | `200` | `autopapertoppt.core.constants.MAX_RESULTS_PER_SOURCE` |
| Default cache TTL | `86400` seconds (24 h) | `autopapertoppt.core.constants.CACHE_TTL_SECONDS` |
| Default output dir | `./exports` | `autopapertoppt.cli._DEFAULT_OUT_DIR` |
| Default export formats (`--query`) | `pptx, xlsx, bibtex` | `autopapertoppt.cli._DEFAULT_EXPORTS_SEARCH` |
| Default export formats (`--paper`) | `pptx, bibtex` | `autopapertoppt.cli._DEFAULT_EXPORTS_SINGLE` |
| Default slide language (`--lang`) | `en` | `autopapertoppt.exporters.i18n.DEFAULT_LANGUAGE` |
| Default max slides per paper | `25` | `autopapertoppt.cli` (`--max-slides`) |
| Paywall warning threshold | `0.30` (30%) | `autopapertoppt.cli.DEFAULT_PAYWALL_THRESHOLD` |
| Top-tier-only filter | on (off via `--all-venues`) | `autopapertoppt.cli` |

## Per-source rate limits

Defined in each plugin's `config.py`; enforced by a per-source
token bucket in `autopapertoppt.fetchers.rate_limit`. The
defaults match each upstream's published or observed soft limit:

| Source | Rate | Jitter | Notes |
|---|---|---|---|
| `arxiv` | 1 req / 3 s | 0.5 s | Matches arXiv's API ToS. |
| `semantic_scholar` | 1 req / s | 0.1 s | Anonymous limit; 10/s with API key. |
| `openalex` | 10 req / s | 0.1 s | Polite pool (with `AUTOPAPERTOPPT_CONTACT_EMAIL`). |
| `pubmed` | 3 req / s | 0.1 s | Anonymous; 10/s with `AUTOPAPERTOPPT_NCBI_API_KEY`. |
| `acm` (via crossref) | 50 req / s | 0.05 s | Crossref public; Plus token raises further. |
| `dblp` | 1 req / 2 s | 0.5 s | Conservative — DBLP is single-server. |
| `crossref` | 50 req / s | 0.05 s | Polite pool with `mailto`. |
| `openaire` | 2 req / s | 0.2 s | Conservative — OpenAIRE rate limits are not published. |
| `ieee` (API) | 10 req / s | 0.1 s | Per the IEEE Xplore API ToS. |
| `ieee` (scrape) | 1 req / 5 s | 1.0 s | ToS-grey — extra-conservative. |
| `springer` | 5 req / s | 0.2 s | Per the Springer Meta API ToS. |
| `scholar` | 1 req / 10 s | 2.0 s | ToS forbids scraping — extra-conservative. |

These are enforced by a decorator on the HTTP client; retries on
429 / 5xx also go through the bucket so a burst can't slip past
the limit.

## Cache layout

`autopapertoppt.core.cache` (used internally by fetchers) keys
every raw response by `sha256(source + normalised_query + page)`
and stores under `${XDG_CACHE_HOME:-~/.cache}/autopapertoppt/`.
Override via:

| Variable | Default | Effect |
|---|---|---|
| `AUTOPAPERTOPPT_CACHE_DIR` | `~/.cache/autopapertoppt` (Linux), `~/Library/Caches/autopapertoppt` (macOS), `%LOCALAPPDATA%\autopapertoppt\Cache` (Windows) | Override the cache root. The autouse `_isolate_user_paths` test fixture redirects this to `tmp_path` so tests never write to your real cache. |

Clear the cache by deleting the directory; AutoPaperToPPT
re-creates it on demand.

## Settings the project explicitly does NOT have

By design — listing them so a contributor doesn't accidentally
add them.

- **No `--anthropic-key` / `--ieee-key` / etc. CLI flag.** Keys on
  the command line land in shell history, a screen-sharing reveal,
  and process listings. Use env vars or the GUI.
- **No global rate-limit override.** Per-source buckets are the
  enforcement boundary; a global override would let users break a
  single source's ToS by upping the wrong limit.
- **No "skip robots.txt" flag.** The scrape-based plugins are
  off-by-default precisely because of robots / ToS concerns.
- **No `--insecure` / `--allow-http` flag.** All egress is HTTPS,
  enforced by the project's transport wrapper. Plain-HTTP URLs are
  refused even after a redirect.
