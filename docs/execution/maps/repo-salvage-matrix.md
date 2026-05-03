# Repo salvage matrix

Status: Reference

This matrix is the searchable owner for Phase 0.5 keep/rewrite/delete decisions.

Use only these fixed labels:

- `keep`
- `rewrite in place`
- `delete`
- `quarantine support-only`
- `plugin rebuild`

## Main application surfaces

| Subsystem                             | Current signal                                                                                 | Decision                  | Reason                                                                 | Target owner phase |
| ------------------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------- | ---------------------------------------------------------------------- | ------------------ |
| API route shell and dependency wiring | useful framework/integration shell exists                                                      | `rewrite in place`        | routing structure is reusable, but old nouns/contracts must be removed | Phase 3-5A         |
| public task routes                    | old task upload and `/tasks/composes/start` model                                              | `delete`                  | target task-start contract is incompatible                             | Phase 5A           |
| public/internal flow routes           | old `/flows/*`, retry, raw slices, mixed operator/debug routes                                 | `rewrite in place`        | shell may remain, contract must be replaced aggressively               | Phase 3-5A         |
| runtime schemas                       | `input_payload`, `context_refs`, approval/session-era shapes                                   | `rewrite in place`        | too much target-incompatible contract shape survives                   | Phase 2-5A         |
| runtime DB models                     | old resource/task/runtime truth and stale enums                                                | `rewrite in place`        | infra patterns are useful, contract shape is not                       | Phase 2-5A         |
| compiler core                         | useful normalization/validation/code structure exists, but stale flat/skill-ref logic survives | `rewrite in place`        | keep compiler shell, replace contract logic                            | Phase 1            |
| registry services                     | useful persistence/query shell exists, but old skill surfaces survive                          | `rewrite in place`        | definitions lifecycle remains, stale skill semantics do not            | Phase 1 and 5A     |
| CLI/config/init/package shell         | strong infra value                                                                             | `keep`                    | config/install/service scaffolding is worth preserving                 | Phase 0.5 and 5B   |
| console                               | current console is tied to stale runtime/operator shapes                                       | `quarantine support-only` | do not let it define target runtime shape during cleanup               | Later optional     |
| docs under repo-local subrepos        | historical context only                                                                        | `quarantine support-only` | canonical docs pack owns target truth                                  | Phase 0.5          |

## Plugin surfaces

| Subsystem                 | Current signal                                             | Decision         | Reason                                                               | Target owner phase |
| ------------------------- | ---------------------------------------------------------- | ---------------- | -------------------------------------------------------------------- | ------------------ |
| plugin entry shell        | small and reusable                                         | `keep`           | skeleton registration surface is still useful                        | Phase 4B           |
| plugin tool inventory     | old approval/raw-slice/skill-write/runtime-bundle contract | `plugin rebuild` | target plugin contract changed too much for safe incremental cleanup | Phase 4B           |
| plugin test harness       | basic TS test shell is reusable                            | `keep`           | test shell is useful, old assertions are not                         | Phase 0.5 and 4B   |
| old plugin contract tests | lock stale tool families and paths                         | `delete`         | they preserve the wrong target                                       | Phase 0.5          |

## Test inventory defaults

| Test family                       | Current signal                        | Decision                                                                      | Reason                                                | Target owner phase |
| --------------------------------- | ------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------- | ------------------ |
| config/init/install/package tests | mostly redesign-agnostic infra        | `keep with small edits`                                                       | valuable infra coverage                               | Phase 0.5 and 5B   |
| compiler tests                    | many can be reused structurally       | `rewrite in place`                                                            | target authoring contract is different                | Phase 1            |
| runtime/API contract tests        | many encode old nouns/routes/payloads | `rewrite in place`                                                            | coverage shell is useful but contract is wrong        | Phase 2-5A         |
| approval-era tests                | stale target semantics                | `delete`                                                                      | target removes approval-era surfaces                  | Phase 0.5          |
| skill-registry target tests       | stale standard target semantics       | `delete` or `rewrite in place` only if testing retained support-only behavior | target canon removed them from standard surface       | Phase 0.5          |
| plugin tool inventory tests       | stale target contract                 | `rewrite in place`                                                            | preserve harness, rewrite around target-only tool set | Phase 4B           |

## Migration history

| Subsystem               | Current signal                                                                    | Decision                       | Reason                                           | Target owner phase |
| ----------------------- | --------------------------------------------------------------------------------- | ------------------------------ | ------------------------------------------------ | ------------------ |
| current Alembic history | already acts like a large fresh snapshot baseline, but encodes old contract truth | `delete` as redesign authority | replace with one new redesign baseline migration | Phase 0.5          |
| Alembic plumbing        | useful infra                                                                      | `keep`                         | migration framework still useful                 | Phase 0.5          |
