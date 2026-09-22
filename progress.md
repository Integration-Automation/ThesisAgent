# progress.md: ThesisAgents

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: S-5, X-15).

## Open

- **#1** Merge PR #19 (dev→main, the backlog committed on 2026-09-22 plus the mcp 1.x pin); merging starts the release workflow. CI, pytest, ruff, bandit and the search and single-paper smoke gates passed on 2026-09-23 (workspace S-5).
- **#19** SonarCloud 的品質門檻在 PR #19 上是紅的，還有一個條件要處理：`thesisagents/evaluation/search_quality.py:103` 被 `pythonsecurity:S8707` 判成「LLM 提供的 CLI 參數導致路徑穿越」。那支是離線評估器，benchmark 路徑本來就由使用者指定。安全類規則不吃 `# NOSONAR`，要在 SonarCloud 網站或 API 上標成 WONTFIX 並寫理由（需要有權限的 token）。重複率那個條件已經處理：`.sonarcloud.properties` 把一次性的 `scripts/**` 排除在 CPD 之外。
- **#2** `ci.yml:78` and `README.md:451` run bandit on `sources/`, which no longer exists at the top level (`AGENTS.md:284` scans only `thesisagents/`).
- **#3** The GUI does not remember its window size and position (`docs/gui.md:219`).
- **#4** The search-quality evaluator exists but no benchmark judgement file (qrels) is committed.
- **#5** [DECIDE] `je_web_runner>=0.0.60` is declared only to pull in selenium (`thesisagents/fetchers/webrunner_browser.py:3-17`): depend on selenium directly or really use WebRunner. `CLAUDE.md` (≈:215) says `mcp__webrunner__*` is registered for this project, but it is only registered for the old path `D:/Codes/AutoPaperToPPT` (workspace X-15).
