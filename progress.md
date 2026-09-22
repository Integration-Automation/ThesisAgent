# progress.md: ThesisAgents

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: S-5, X-15).

## Open

- **#1** Merge PR #19 (dev→main, the backlog committed on 2026-09-22 plus the mcp 1.x pin); merging starts the release workflow. CI, pytest, ruff, bandit and the search and single-paper smoke gates passed on 2026-09-23 (workspace S-5).
- **#2** `ci.yml:78` and `README.md:451` run bandit on `sources/`, which no longer exists at the top level (`AGENTS.md:284` scans only `thesisagents/`).
- **#3** The GUI does not remember its window size and position (`docs/gui.md:219`).
- **#4** The search-quality evaluator exists but no benchmark judgement file (qrels) is committed.
- **#5** [DECIDE] `je_web_runner>=0.0.60` is declared only to pull in selenium (`thesisagents/fetchers/webrunner_browser.py:3-17`): depend on selenium directly or really use WebRunner. `CLAUDE.md` (≈:215) says `mcp__webrunner__*` is registered for this project, but it is only registered for the old path `D:/Codes/AutoPaperToPPT` (workspace X-15).
- **#6** SonarCloud's quality gate is red on PR #19 and one condition is left: `thesisagents/evaluation/search_quality.py:103` is reported under `pythonsecurity:S8707` as path traversal from LLM-supplied CLI arguments. That file is the offline evaluator; naming the benchmark file is what its user is supposed to do. Security rules ignore `# NOSONAR`, so it has to be marked WONTFIX with a reason in the SonarCloud UI or API (needs a token with the right permission). The duplication condition is handled: `.sonarcloud.properties` keeps the one-shot `scripts/**` out of the CPD metric.
