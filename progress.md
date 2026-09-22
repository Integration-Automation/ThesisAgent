# progress.md: ThesisAgents

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: S-5, X-15).

## Open

- **#4** The search-quality evaluator exists but no benchmark judgement file (qrels) is committed.
- **#5** [DECIDE] `je_web_runner>=0.0.60` is declared only to pull in selenium (`thesisagents/fetchers/webrunner_browser.py:3-17`): depend on selenium directly or really use WebRunner. `CLAUDE.md` (≈:215) says `mcp__webrunner__*` is registered for this project, but it is only registered for the old path `D:/Codes/AutoPaperToPPT` (workspace X-15).
