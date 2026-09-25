# progress.md: ThesisAgents

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (none open at the moment).

## Open

- **#4** The search-quality evaluator exists but no benchmark judgement file (qrels) is committed.
- **#5** [UNVERIFIED] The first release after U-20260925-01 builds cold (the cache key's paths changed). On the release after that, check the Nuitka log line `Compiled N C files using clcache with H cache hits` and the job time: if the build is warm, replace the expected ~5–10 min in `docs/releases.md` and the README (all 14 languages) with the measured value. If hits stay low, clcache's default 1 GiB size limit (`MaximumCacheSize` in Nuitka's inline `clcache/caching.py`) may be evicting objects.
