# Research workflow next-step roadmap

> Planning PR only. This branch intentionally contains the implementation design and acceptance criteria for the next research-workflow increment; feature code should land in follow-up commits/PRs after the design is agreed.

## Goal

Evolve ThesisAgents from a stateless keyword-search/export pipeline into a traceable research workflow that can:

1. reject unverifiable bibliography records before export;
2. expose and improve relevance decisions instead of treating ranking as a final opaque order;
3. make source coverage observable per query;
4. expand a seed set through citations/references ("snowballing");
5. retain a reusable literature library across executions; and
6. let users control the visual language of generated decks without forking the exporter.

The existing pipeline is:

`Query → fetch → normalise → dedup → rank → filters → OA resolution → export`

The proposed pipeline becomes:

`Query → fetch → source metrics → normalise/dedup → relevance score → optional pruning → citation/snowball expansion → library merge → export validation → export`

---

## 1. URL / DOI verification as the default export preflight

### Current state

The repository already documents URL/DOI verification as a mandatory authoring rule, and `Paper` carries `url` and optional `doi`. However, `export_collection()` currently dispatches directly to exporters, so the documented rule is not a hard runtime gate.

### Design

Add a single reusable preflight boundary, e.g. `thesisagents/core/export_validation.py`:

- validate every paper's canonical URL when `url` is HTTP(S);
- validate DOI syntax/canonicalisation separately from URL reachability;
- prefer DOI resolution when a DOI is present;
- follow redirects but keep the final URL separate from the bibliographic URL;
- use bounded concurrency and short timeouts;
- classify failures as `invalid`, `unreachable`, `timeout`, or `skipped`;
- never silently rewrite a paper's citation metadata from a redirect target;
- cache verification results for the duration of one export and, later, in the persistent library.

### Export contract

`export_collection()` should run:

`validate → fail/continue according to policy → exporter`

Default policy: **strict**. Any paper with a supplied URL/DOI that fails verification blocks export and returns a structured report identifying the paper and failed identifier.

Provide an explicit opt-out for offline/air-gapped workflows, e.g. `verify_identifiers=False` in `ExportOptions`, exposed as a CLI/MCP option. The opt-out should be visible in logs/output rather than silently inferred.

### Tests

- valid URL + valid DOI passes;
- malformed DOI fails without a network request;
- HTTP redirect is accepted but original DOI/URL is preserved;
- timeout is reported distinctly;
- one invalid paper blocks strict export;
- opt-out allows export;
- mocked verification is bounded/concurrent and deterministic.

---

## 2. Relevance scoring + automatic pruning recommendations

### Current state

`core/ranking.py` already combines query relevance, recency, and citation count. The missing layer is an explainable per-paper relevance result and a recommendation for what can be removed.

### Design

Refactor the ranking internals around an explicit result model:

```text
RelevanceScore
  total
  relevance
  recency
  citation
  matched_terms
  matched_phrases
  reasons
```

Keep the current conservative relevance behaviour, including stemming, phrase adjacency, acronym expansion, and CJK tokenisation.

Add a pruning/recommendation stage that is **advisory by default**:

- detect low-relevance papers;
- detect near-duplicate/coverage-redundant papers after dedup;
- detect papers that are weak on all configured axes;
- recommend `keep`, `review`, or `prune`;
- include an explanation and threshold that caused the recommendation.

Do not automatically delete records in the first iteration. A later policy can opt into hard pruning after the scoring contract is proven.

### Proposed API

`rank_with_scores(papers, keywords, policy) -> RankedPaper`

`recommend_pruning(ranked, policy) -> tuple[PruningRecommendation, ...]`

MCP/CLI output should expose scores and recommendations without changing the existing `papers` payload shape unless the caller explicitly requests diagnostics.

### Tests

- relevance dominates an off-topic high-citation paper;
- phrase matches explain their bonus;
- acronym/long-form matches are represented in reasons;
- low-score papers receive `review/prune` recommendations;
- top-ranked papers are not recommended for pruning solely because of low citation counts;
- recommendations are stable for identical inputs.

---

## 3. `list_sources`: return per-query result counts

### Current state

`list_sources()` is discovery/configuration only. Search runs each source concurrently, but source-level result counts are not retained as query telemetry.

### Design

Keep `list_sources()` backward-compatible as a discovery tool.

Add per-search source metrics to the `search` response:

```json
{
  "source_stats": [
    {
      "source": "arxiv",
      "requested": 25,
      "returned": 23,
      "after_dedup": 19,
      "status": "ok"
    }
  ]
}
```

At minimum the requested feature is `returned` for the current query. The additional `requested`, `after_dedup`, and `status` fields make failures and dedup effects observable without another API.

Do not overload `list_sources` with query state. The query-specific counts belong to `search` (and optionally a separate `source_stats` diagnostic tool later).

### Implementation point

Change `run_search()` to retain source/result pairs rather than flattening immediately. Preserve the existing failure-containment behaviour: a failed source reports `status=failed`, `returned=0`, and does not abort other sources.

### Tests

- one source returns N → stats report N;
- failed source reports zero + failure status;
- multiple sources retain independent counts;
- dedup count is lower than raw returned count when records overlap;
- existing `papers` output remains unchanged.

---

## 4. Citation and snowball searching

### Goal

Starting from a seed paper set, expand the literature graph through:

- **backward snowballing**: references cited by a seed paper;
- **forward snowballing**: papers citing a seed paper.

### Design

Introduce a source-neutral citation interface rather than embedding citation logic in each exporter/search plugin:

`CitationProvider`

- `references(paper)`
- `cited_by(paper)`

Provider priority should use sources that already expose citation relationships (for example Semantic Scholar/OpenAlex/Crossref where available), with graceful fallback when a provider cannot resolve a paper.

Add a bounded expansion API:

```text
snowball(
  seeds,
  direction="both",
  depth=1,
  max_per_seed=20,
  min_relevance=None,
)
```

Safety/quality constraints:

- depth defaults to 1;
- hard cap total discovered papers;
- deduplicate by the existing multi-key identity model;
- preserve provenance: `seed → direction → provider → depth`;
- score newly discovered papers using the same relevance scorer;
- never recurse indefinitely;
- do not treat citation count as proof of relevance.

### Suggested model addition

Add a lightweight relationship record rather than bloating `Paper`:

`PaperRelation(source_key, target_key, relation, provider, depth)`

This can later power a citation graph view and explain why a paper entered the library.

### Tests

- forward expansion returns citing papers;
- backward expansion returns references;
- both directions respect depth and caps;
- duplicate paths collapse to one paper;
- provenance records the shortest/first discovered path;
- provider failure does not abort the entire expansion.

---

## 5. Persistent literature library across executions

### Goal

Turn each search/export run into reusable research state rather than a disposable `PaperCollection`.

### Design

Introduce a local library abstraction under `thesisagents/library/`:

```text
Library
  papers
  relations
  verification cache
  run metadata
```

Recommended first backend: **SQLite**, because it is included with Python, transactional, queryable, and avoids introducing a server dependency.

Use stable identity keys already defined by `Paper.identity_keys()`. Store:

- canonical paper metadata;
- field provenance;
- relevance/score snapshots;
- URL/DOI verification state;
- citation relationships;
- originating query/run IDs;
- timestamps.

A run should be append/merge oriented. Re-running a query should update provenance/observations rather than create uncontrolled duplicates.

### CLI/MCP surface

CLI:

- `--library PATH`
- `--library-add`
- `--library-search QUERY`
- `--library-export ...`

MCP:

- `library_add`
- `library_search`
- optionally `library_stats`

The initial implementation can keep the library opt-in. Once the schema is stable, a user-local default database can become the normal mode.

### Tests

- add/search round trip;
- repeated add is idempotent on identity;
- provenance from multiple sources is retained;
- citation relations survive restart;
- verification cache survives restart;
- concurrent readers do not corrupt the database;
- migration/version handling is explicit.

---

## 6. Customisable presentation templates

### Current state

`ExportOptions.pptx_template` already exists and `PptxExporter` can open a supplied PowerPoint template. This is a useful foundation, but it is currently closer to "supply a file" than a documented/customisable template contract.

### Design

Formalise a template contract instead of allowing arbitrary PPTX files to become an undocumented dependency.

Support two levels:

1. **PPTX template file** — user supplies a deck containing named layouts/placeholders.
2. **Template configuration** — optional TOML/JSON describing semantic roles such as:
   - slide size;
   - font families;
   - title/body/meta styles;
   - colours;
   - margins;
   - named layouts for cover/section/content/table/reference/Q&A.

The exporter should map semantic roles to template placeholders rather than hard-coding slide layout indices.

Add validation:

`validate_template(path) -> TemplateValidationReport`

It should identify missing required roles before a long export starts.

### Compatibility

Keep the current generated navy-band theme as the built-in default. Existing `pptx_template` callers continue to work.

The first implementation should not attempt a full PowerPoint theme editor. Focus on stable semantic placeholders and style overrides.

### Tests

- built-in template still renders unchanged;
- valid custom template renders;
- missing required placeholder produces an actionable preflight error;
- custom fonts/styles are applied;
- non-16:9 templates are either normalised explicitly or rejected with a clear message;
- round-trip deck opens with `python-pptx`.

---

## Recommended implementation order

### Phase 1 — correctness + observability

1. **Export identifier preflight**
2. **Explainable relevance scores + pruning recommendations**
3. **Per-source query statistics**

These have low coupling and immediately improve trust in current search/export behaviour.

### Phase 2 — research expansion

4. **Citation provider abstraction**
5. **Bounded forward/backward snowball search**

Do this before the persistent library so the relationship model is designed once.

### Phase 3 — persistence

6. **SQLite literature library**

Persist papers, provenance, relationships, and verification results together.

### Phase 4 — presentation

7. **Template contract + validation**
8. CLI/MCP/GUI exposure and documentation

This can proceed independently, but should reuse the existing `ExportOptions.pptx_template` field.

---

## Cross-cutting API changes

| Area | Proposed change |
|---|---|
| `Paper` | Keep identity model; add optional relationship/provenance records outside the core paper object |
| `PaperCollection` | Add optional run/source diagnostics without breaking serialisation |
| `ExportOptions` | Add strict identifier verification policy + template validation/config |
| `run_search()` | Return source telemetry and optionally relevance diagnostics |
| `ranking.py` | Expose score breakdowns, not only sorted papers |
| `mcp.search` | Add `source_stats`, optional diagnostics, and snowball controls |
| `mcp.export` | Add identifier verification controls and template validation |
| CLI | Add library/snowball/diagnostic/template options |
| Persistence | New SQLite schema with explicit schema version |
| Docs | Update README, MCP, CLI, data model, architecture, and localized docs after API stabilises |

---

## Definition of Done for the implementation series

- [ ] URL/DOI verification is a default export preflight with strict + offline modes.
- [ ] Every ranked paper can expose an explainable score breakdown.
- [ ] Pruning is advisory by default and deterministic.
- [ ] Search returns per-source result counts.
- [ ] Citation forward/backward expansion is bounded, deduplicated, and provenance-aware.
- [ ] A SQLite literature library persists across process executions.
- [ ] Repeated imports merge instead of duplicating papers.
- [ ] Verification state and citation relationships persist.
- [ ] PPTX templates have a documented semantic contract and preflight validation.
- [ ] CLI, MCP, and GUI surfaces remain coherent.
- [ ] Unit/integration tests cover all new behaviour.
- [ ] `pytest tests/`, `ruff check .`, and `bandit -c pyproject.toml -r thesisagents/` are clean.
- [ ] Exporter changes include a real PPTX round-trip/overflow review.
- [ ] README + MCP + CLI + architecture/data-model docs are updated together.

## Suggested follow-up PR split

To keep reviewable changes small, implement this roadmap as:

1. `feat: add export identifier preflight and verification cache`
2. `feat: expose explainable relevance scores and pruning recommendations`
3. `feat: report per-source search result statistics`
4. `feat: add citation graph and bounded snowball search`
5. `feat: add persistent SQLite literature library`
6. `feat: formalize customizable PPTX templates`

The current PR is the umbrella design/roadmap and should remain **Draft** until the architecture and API contracts are agreed.
