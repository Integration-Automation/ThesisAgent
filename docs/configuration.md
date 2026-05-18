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
| `AUTOPAPERTOPPT_S2_API_KEY` | unset | Higher rate limit on the Semantic Scholar plugin (1/s anonymous → 10/s with key). **Also used by the OA resolver's S2 `openAccessPdf` lookup step** — without the key the resolver's S2 calls hit the anonymous tier and rate-limit fast. Free key at <https://www.semanticscholar.org/product/api>. |
| `AUTOPAPERTOPPT_NCBI_API_KEY` | unset | Raises PubMed's anonymous limit from 3 req/s to 10 req/s. |
| `AUTOPAPERTOPPT_IEEE_API_KEY` | unset | Switches the IEEE plugin from the scrape fallback to the official Xplore API (`ieeexploreapi.ieee.org`). Surfaces `pdf_url` for papers in your subscription scope. Apply at <https://developer.ieee.org/>. |
| `AUTOPAPERTOPPT_DISABLE_IEEE_SCRAPING` | unset | **IEEE plugin is now default-ON.** Set `=1` to opt out of the scrape fallback. IEEE Xplore ToS are grey on automated traffic — set this if you don't want the scrape path running. |
| `AUTOPAPERTOPPT_SPRINGER_API_KEY` | unset | Free key from <https://dev.springernature.com/>. **Required** for the Springer plugin — it raises `ConfigError` at construction without a key, which the pipeline silently skips. |
| `AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN` | unset | Crossref Plus subscriber token. Attached to requests as `Crossref-Plus-API-Token: Bearer <token>`. Raises rate limits and improves cache freshness on the `acm` and `crossref` plugins. |
| `AUTOPAPERTOPPT_DISABLE_SCHOLAR_SCRAPING` | unset | **Scholar plugin is now default-ON.** Set `=1` to opt out. Google's ToS forbids automated access; default-on for coverage, opt-out if you'd rather not take the captcha / IP-block risk. |
| `AUTOPAPERTOPPT_DISABLE_WEBRUNNER` | unset | The Scholar plugin defaults to driving a real Chrome through **WebRunner** (`je_web_runner` is a default dependency) — Google's bot-detection is far less aggressive on real browsers. Set `=1` to force the httpx scrape path even when WebRunner is available (useful for CI / Docker containers without a Chrome binary, or latency-sensitive runs where Chrome's 5-10 s boot isn't worth it). When set, the plugin's existing captcha-cooldown logic kicks in for the httpx path. |
| `AUTOPAPERTOPPT_CHROME_PROFILE_DIR` | unset | When set, passes `--user-data-dir=<path>` to Chrome so cookies / login state / captcha clearance survive across CLI invocations. A one-time interactive Google sign-in seeded into this profile dir reliably suppresses Scholar captchas on subsequent headless runs. See the **Suppressing Scholar captchas with a persistent profile** recipe below. |
| `AUTOPAPERTOPPT_CHROME_HEADLESS` | `1` (headless) | Set `=0` to open Chrome visibly. Used ONLY for the one-time interactive Google sign-in that seeds `AUTOPAPERTOPPT_CHROME_PROFILE_DIR`. Subsequent runs should drop this env var so Chrome stays headless. |
| `AUTOPAPERTOPPT_CORE_API_KEY` | unset | Free key from <https://core.ac.uk/services/api>. Enables the OA resolver's CORE.ac.uk lookup step (200M+ institutional / regional OA repository items). Skipped silently when unset (the other OA strategies — Unpaywall, Semantic Scholar, arXiv — still run). |
| `AUTOPAPERTOPPT_CONTACT_EMAIL` | unset | Sent to Crossref / OpenAlex as the `mailto=` parameter (entry into their polite pool), to NCBI as `tool` / `email` headers, **and to Unpaywall as `email=`** for the post-dedup OA PDF resolver. Highly recommended — without it the resolver skips Unpaywall lookups entirely, which is the single biggest PDF coverage win for IEEE / ACM / Springer / Elsevier paywalled papers (typical lift 40-70%). |

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

## Suppressing Scholar captchas with a persistent Chrome profile

Google flags an IP after a few automated Scholar requests even with
WebRunner's real-browser path. The reliable workaround is to seed a
persistent Chrome profile with a real Google sign-in once; subsequent
headless runs reuse the same session cookies, which Google trusts.

**One-time setup:**

```powershell
# 1. Pick a directory anywhere on disk
$env:AUTOPAPERTOPPT_CHROME_PROFILE_DIR = "D:\autopapertoppt-scholar-profile"

# 2. Open Chrome visibly and trigger one Scholar request
$env:AUTOPAPERTOPPT_CHROME_HEADLESS = "0"
autopapertoppt --query "any keywords" --source scholar --max 1 --out .\tmp\

# Chrome opens. Sign into your Google account, accept any consent
# banners, complete any captcha. The window holds open for 60s.
```

**Every run after that:**

```powershell
$env:AUTOPAPERTOPPT_CHROME_PROFILE_DIR = "D:\autopapertoppt-scholar-profile"
Remove-Item Env:\AUTOPAPERTOPPT_CHROME_HEADLESS   # back to headless
autopapertoppt --query "..." --out .\exports\
```

Chrome boots headless but loads the same profile dir, sends your
authenticated Google session cookie, and Scholar serves real results
instead of a captcha page.

**Caveats:**

- Only one Chrome process can hold the profile dir at a time. If you
  have a regular Chrome open on the same profile path, the
  WebRunner instance will fail to start. Use a dedicated path.
- The session cookie is a real authentication credential. Treat the
  profile directory like a secret — back it up if you re-image the
  machine, restrict file permissions.
- Cookie eventually expires (~1-2 months for Google). Re-do the
  interactive sign-in then.

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
