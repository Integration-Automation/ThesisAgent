# progress.md: ThesisAgents

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: S-5, X-15).

## Open

- **#1** 80 files are uncommitted (dedup rewrite with multi-identity keys and field provenance, the search-quality evaluator, per-paper robustness in `pdf_download` / `oa_resolver`, the `--export pdf` fix, docs synced to 15 sources and 13 tools in 14 languages, new rules, thesis-defence scripts and figures). Run `dod-verify`, commit in stages, then open the dev→main PR (workspace S-5).
- **#2** `ci.yml:78` and `README.md:451` run bandit on `sources/`, which no longer exists at the top level (`AGENTS.md:284` scans only `thesisagents/`).
- **#3** The GUI does not remember its window size and position (`docs/gui.md:219`).
- **#4** The search-quality evaluator exists but no benchmark judgement file (qrels) is committed.
- **#5** [DECIDE] `je_web_runner>=0.0.60` is declared only to pull in selenium (`thesisagents/fetchers/webrunner_browser.py:3-17`): depend on selenium directly or really use WebRunner. `CLAUDE.md` (≈:215) says `mcp__webrunner__*` is registered for this project, but it is only registered for the old path `D:/Codes/AutoPaperToPPT` (workspace X-15).
