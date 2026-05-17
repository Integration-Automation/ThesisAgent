# Releases

The auto-release pipeline, what triggers it, and how to opt out.

## The pipeline

```
Push to main
   │
   ▼ ci.yml runs (matrix: Ubuntu + Windows × Python 3.12 / 3.13 / 3.14)
   │
   ▼ CI passes → workflow_run fires release.yml
   │
   ▼
┌──────────────┐
│ bump-version │  patch +1 in pyproject.toml, push back to main via GITHUB_TOKEN
└──────────────┘
   │
   ▼
┌──────────────┐
│ publish-pypi │  python -m build + twine upload (PYPI_API_TOKEN)
└──────────────┘
   │
   ▼
┌──────────────────────┐
│ create-draft-release │  GitHub Release at tag v<X.Y.Z>, draft: true
└──────────────────────┘
   │
   ▼
┌──────────────┐
│ build-nuitka │  Windows .zip with the standalone bundle
└──────────────┘
   │
   ▼
┌────────────────┐
│ publish-release│  unmarks the draft, release appears in sidebar
└────────────────┘
```

## What gets published per release

| Artefact | Where | Size |
|---|---|---|
| **`autopapertoppt-<version>.tar.gz`** (sdist) | PyPI | ~120 KB |
| **`autopapertoppt-<version>-py3-none-any.whl`** | PyPI | ~140 KB |
| **`autopapertoppt-windows-x86_64.zip`** | GitHub Release | ~250-350 MB (Nuitka bundle + PySide6) |
| **`autopapertoppt-windows-x86_64.zip.sha256`** | GitHub Release | 80 bytes |

The PyPI artefacts work on Linux / macOS / Windows; the zip is
the standalone Windows bundle for users who don't want a Python
install.

## Version bump strategy

Patch +1 on every CI-success push to `main`:

```
0.1.0 → 0.1.1 → 0.1.2 → 0.1.3 → …
```

The `bump-version` job:

1. Reads the current `version = "X.Y.Z"` from `pyproject.toml`.
2. Increments `Z` by 1.
3. Commits the bump back to `main` as
   `chore: bump version to X.Y.<Z+1>` via the workflow's
   `GITHUB_TOKEN`.
4. Outputs the new SHA, which downstream jobs check out.

The bump commit's push **does not re-trigger CI** — GitHub's
rule that `GITHUB_TOKEN`-driven pushes can't start new workflow
runs naturally terminates the loop.

For a minor or major bump, edit `pyproject.toml` manually in a
PR (`0.1.5 → 0.2.0`); the bump-version job sees that the version
changed but its patch logic still adds `+1` to the patch, so a
manual `0.2.0` becomes `0.2.1` on the next CI success. Plan
accordingly.

## Opting out of a release: `[skip release]`

Include `[skip release]` anywhere in a commit message and the
auto-bump + every downstream job are gated off:

```bash
git commit -m "Tweak docs typo [skip release]"
git push
```

Use this for:

- Docs / typo / comment-only changes.
- Refactors that don't change behaviour.
- Test-only changes that don't gate functionality.
- Anything where the version number would just be noise.

CI still runs (it always runs on push to any branch). Only the
release pipeline is skipped.

## Loop prevention

Two layers of belt + suspenders:

1. **GitHub's native rule**: pushes via `GITHUB_TOKEN` don't
   trigger workflows. So the bump commit's push doesn't fire CI,
   doesn't fire `workflow_run`, and the release pipeline can't
   re-enter.
2. **Defensive check**: `bump-version` calls `git log -1 --pretty=%B`
   and skips if the previous commit message starts with
   `chore: bump version to`. Survives even if GitHub's rule
   changes.

## Why `--standalone` not `--onefile`

The Nuitka build uses `--standalone` (produces a
`autopapertoppt.dist/` folder, which we zip) rather than
`--onefile` (single self-extracting `.exe`).

Reasons:

| Concern | `--onefile` | `--standalone` |
|---|---|---|
| Startup latency | Self-extracts to `%TEMP%` on every launch (~1-3 s) | Runs in place, no extraction (sub-second) |
| Antivirus | Self-extracting binary often flagged | Folder + .exe, treated normally |
| Locked-down corporate machines | `%TEMP%` write or exec sometimes blocked | No `%TEMP%` write needed |
| Distribution | Just the .exe | A .zip the user unzips once |
| Update mechanism | Replace the whole .exe | Replace the folder (rsync-friendly) |

The zip pattern is the standard for Qt apps on Windows (Krita,
OBS, KeePass all ship this way).

## Why Windows only

Linux + macOS users install from PyPI. Shipping Nuitka binaries
for those platforms just inflates the release page without
serving a real use case — `pip install autopapertoppt` is already
the one-command install path. Windows is the only platform where
"download and double-click" is the common install pattern.

## Build timings

| Stage | Cold (no cache) | Warm (cache hit) |
|---|---|---|
| `bump-version` | ~5 s | ~5 s |
| `publish-pypi` | ~3-5 min | ~3-5 min |
| `create-draft-release` | ~10 s | ~10 s |
| `build-nuitka` | **~50-70 min** | ~5-10 min |
| `publish-release` | ~5 s | ~5 s |
| Total | ~55-75 min | ~10-15 min |

The Nuitka cold build dominates because PySide6 + Qt are a huge
amount of C++ to link. The cache (keyed on `pyproject.toml` +
version) cuts subsequent builds dramatically. The timeout cap is
90 min — generous for the cold case.

## Repo settings the pipeline needs

Configure once after forking / first deploy:

1. **`Settings → Actions → General → Workflow permissions`** →
   "Read and write permissions". The `bump-version` job pushes
   the version commit via `GITHUB_TOKEN`; default `read-only`
   permissions would block it.

2. **`Settings → Secrets and variables → Actions → New repository
   secret`** → `PYPI_API_TOKEN`. Generate a project-scoped token
   at <https://pypi.org/manage/account/token/>.

3. No GitHub Environment is needed. The `publish-pypi` job
   intentionally does NOT attach `environment: pypi` — that would
   make GitHub treat the run as a Deployment and surface a
   "Deployments" sidebar widget, which is noise alongside the
   real Release entry.

## Recovering from a failed release

The pipeline is stage-fail-fast. If `build-nuitka` times out
after `publish-pypi` succeeded:

- **PyPI** has the new version. It cannot be re-published with
  the same version number (PyPI is immutable).
- **GitHub** has a draft release at `v<version>`. It can be
  deleted: `gh release delete v0.1.X --yes`.
- **`pyproject.toml`** on `main` has the new version. The next
  push to `main` will bump to the next patch.

So a failed release just "skips" a version number — the gap
(`v0.1.1` skipped between `v0.1.0` and `v0.1.2`) is cosmetic.
Don't try to recycle the PyPI version; bump to the next number
and try again.

## Branch protection (recommended)

Optional but recommended for shared forks:

- Require PR review before merging to `main`.
- Require CI to pass before merging.
- Require linear history (rebases) for cleaner version-bump
  commits.

The `bump-version` push uses the GitHub Actions bot identity, so
branch protections that require a CODEOWNER review will block
the bump. Add an exception for the GitHub Actions bot or use a
"Restrict who can push" rule that allows the bot.

## Watching a release in progress

```bash
gh run watch                              # latest run, any workflow
gh run list --workflow=release.yml -L 5   # last 5 release runs
gh run view <run-id> --log                # all logs
gh run view <run-id> --log-failed         # only failed-step logs
```

The pipeline's stages are linear — if `bump-version` runs but
`publish-pypi` is skipped, look at the `bump-version` outputs;
that's usually a `[skip release]` tag triggering the skip path.
