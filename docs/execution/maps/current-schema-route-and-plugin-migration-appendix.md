# Current schema, route, and plugin migration appendix

Status: Reference

This appendix is the concrete current-to-target migration map for live schemas, HTTP routes, plugin tools, and surface boundaries.

It is implementation guidance only. If this appendix and `docs/redesign/` disagree, `docs/redesign/` wins.

Every current surface should land in exactly one outcome:

- `keep`
- `replace`
- `remove`
- `support-only lane`

## Current workspace note

- backend source in this checkout lives under `apps/api/app/*`
- backend tests live under `apps/api/tests/*`
- repo-root definitions live under `definitions/*`
- live development migrations currently resolve through `apps/api/alembic/*`
- packaged fallback resources live under `apps/api/app/resources/*`
- no `autoclaw-bridge-plugin-main/*` source tree exists in this checkout, so plugin migration here is a docs-driven boundary classification only

## Authoring schema migration

| Current code or concept              | Current shape                                  | Target outcome                                                                      |
| ------------------------------------ | ---------------------------------------------- | ----------------------------------------------------------------------------------- |
| authored control `edges`             | explicit authored control and dependency edges | `remove`; runtime edges derive from tree ownership plus typed inputs                |
| workflow `extends`                   | inheritance hook                               | `remove` from frozen v1 authoring                                                   |
| workflow or node `skill_refs`        | generic skill binding                          | `remove`; use provider-native capabilities and role or policy compatibility instead |
| workflow-authored task-root defaults | workflow carries launch root assumptions       | `replace`; root binding moves to task compose                                       |
| flat node arrays with dotted ids     | naming-driven hierarchy                        | `replace`; nested `children` ownership plus globally unique node ids                |
| authored worker `mode`               | explicit ordinary mode enum                    | `remove`; ordinary node type is inferred structurally                               |
| workflow-level policy fallback       | implied mixed current behavior                 | `replace`; effective policy is explicit node policy or role default                 |

## Task-start and runtime schema migration

| Current code or concept             | Current shape                                 | Target outcome                                                                        |
| ----------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------- |
| wrapper-style task-start payload    | launch body with extra wrapper fields         | `replace`; `TaskStartRequest` is the direct task compose body                         |
| launch `inputs` object              | arbitrary structured launch payload           | `remove` from frozen v1 public launch contract                                        |
| launch `context_refs`               | launch-time durable ref list                  | `remove`; support material enters through bound roots and authored task text          |
| separate task upload shapes         | staged task files and upload slots            | `remove`; no canonical task-file upload surface remains                               |
| boolean task roots                  | root toggles like workspace true or false     | `replace`; root-binding objects with `mode` and optional `host_path`                  |
| generic runtime content publication | catch-all mutation surface                    | `replace`; use typed artifacts, handoffs, result records, and review outputs          |
| approval rows and approval waits    | intervention-specific runtime model           | `remove`; replace with blocked outcomes, operator pause, and bounded parent decisions |
| generic replan patch payload        | mixed edges, nodes, skill, and resource edits | `replace`; local subtree patch over current authored workflow semantics               |

## Public route migration

| Current public route                              | Target route or outcome                                                        | Notes                                                                      |
| ------------------------------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------- |
| current registry list routes                      | `replace` with `GET /definitions/roles`, `/policies`, `/workflows`             | public noun family changes from current registry naming to `definitions/*` |
| current registry version-history routes           | `replace` with `GET /definitions/{kind}/{key}/versions`                        | unified under singular kind tokens                                         |
| current registry draft writes                     | `replace` with `POST /definitions`                                             | guarded upload uses DB-serialized append-only revisions; logical key comes from body `id` |
| current registry publish routes                   | `remove`; folded into guarded `POST /definitions` upload                       | no separate publish step remains in frozen v1                              |
| current workflow validate route                   | `remove` from the public surface                                               | validation stays internal to guarded upload and task start                 |
| current task compose start route                  | `replace` with `POST /tasks/start`                                             | authored task compose becomes the direct request body                      |
| current task upload route                         | `remove`                                                                       | no separate task-file upload surface in v1                                 |
| current flow list and detail routes               | `replace` with `GET /runtime/tasks` and `GET /runtime/tasks/{task_id}`         | public/runtime surfaces are task-scoped externally                         |
| current flow continue, pause, cancel routes       | `replace` with `/runtime/tasks/{task_id}/continue`, `/pause`, `/cancel`        | use `expected_active_flow_revision_id`                                     |
| current mixed operator read route                 | `replace` with `GET /operator/tasks/{task_id}/snapshot` and `/trace`           | split current summary from history                                         |
| current approval read and resolve routes          | `remove` from the standard public surface                                      | frozen v1 removes approval runtime lanes                                   |
| current public node retry or node steering routes | `remove` from standard public surface                                          | frozen operator control stays flow-scoped                                  |
| current public replan route                       | `remove` from standard public surface                                          | callback-bound internal replan route only                                  |

## Internal route migration

| Current internal route or concept                 | Target route or outcome                                                   | Notes                                                            |
| ------------------------------------------------- | ------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| internal pre-start task creation                  | `remove` from canonical API surface                                       | task start remains the public launch front door                  |
| internal task upload route                        | `remove`                                                                  | no canonical upload lane remains                                 |
| internal compile route                            | `support-only lane`                                                       | compile stays implementation detail, not product surface         |
| internal registry bootstrap route                 | `remove`                                                                  | reset and reseed stay CLI or service-owned rather than hidden API truth |
| internal registry snapshot route                  | `support-only lane`                                                       | useful for cleanup investigation, not part of frozen external contract |
| raw runtime slice, timeline slice, or audit reads | `support-only lane`                                                       | do not present as operator parity                                |
| internal worker bundle or worker-context lookup   | `replace` with filesystem-first surfaced paths plus write-only callback lane | current worker-facing machine projection is manifest, assignment, checkpoint, and surfaced refs |
| internal replan mutation route                    | `replace` with callback-bound parent/root structural tool calls           | guarded by bound execution context plus structural currentness echo |
| provider dispatch helper                          | `support-only lane`                                                       | dispatch opening stays an internal controller/adapter helper      |
| watchdog recovery helper                          | `support-only lane`                                                       | watchdog is controller automation, not a canonical dispatch action |
| internal approval creation route                  | `remove`                                                                  | no approval runtime lane remains in frozen v1                    |
| old approval internals                            | `remove`                                                                  | no approval runtime lane in frozen v1                            |

## Root CLI and install migration

| Current teaching or surface                            | Target outcome                                              | Notes                                                              |
| ------------------------------------------------------ | ----------------------------------------------------------- | ------------------------------------------------------------------ |
| repo-local install assumptions                         | `replace` with packaged install truth                       | root package plus bundled resources become canonical               |
| scattered onboarding notes                             | `replace` with root CLI install and doctor flow             | `autoclaw init`, `autoclaw doctor`, `autoclaw serve`               |
| path-based task start through non-canonical verbs      | `replace` with `autoclaw task-compose start --file ...`     | frozen root CLI launch entrypoint                                  |
| bundled Postgres lane as ad hoc setup                  | `replace` with packaged extra plus strong verification lane | `pipx install "autoclaw[postgres]"` and Docker-backed verification |
| future binary, npm, or Homebrew teaching as shipped v1 | `remove` from canonical teaching                            | remain future or non-canonical lanes                               |

## Plugin tool migration

| Current bridge tool or concept             | Target outcome                           | Notes                                                            |
| ------------------------------------------ | ---------------------------------------- | ---------------------------------------------------------------- |
| local plugin source tree in this checkout  | `replace` with Phase 4B near-greenfield rebuild | no repo-local plugin implementation survives to salvage today    |
| current worker-context lookup              | `replace` with filesystem-first surfaced paths plus write-only callback lane | manifest, assignment, checkpoint, and surfaced refs become the live worker read path; callback remains write-only |
| typed callback write                       | `replace` with semantic callback lane    | `record_checkpoint(...)`, `return_boundary(...)`, `call_parent_tool(...)` |
| generic content publish helper             | `replace` with typed runtime publication | artifacts, handoffs, results, and review outputs only            |
| current workflow validate helper           | `remove` from standard parity            | validation stays internal to guarded upload and task start      |
| task start helper                          | `replace` with path-based parity tool    | `start_task(task_compose_path)`                                  |
| missing definition history parity          | `add`                                    | `list_definition_versions(kind, key)` is part of standard parity |
| flow pause, continue, cancel parity gaps   | `add` or `replace`                       | standard operator parity requires all three                      |
| generic node steering helpers              | `remove` from standard parity            | not part of frozen operator scope                                |
| raw runtime drilldown helpers              | `support-only lane`                      | may exist internally but are not standard parity                 |
| guarded definition upload tools       | `keep` as dedicated guarded-write lane   | do not mix with worker bridge semantics                          |

## Implementation traps

- do not preserve current upload-era task-start assumptions under the new `POST /tasks/start` surface
- do not keep current generic mutation helpers alive as if they were part of the frozen redesign
- do not collapse operator-safe routes and internal worker routes into one mixed trust lane
- do not restore approval-era runtime nouns or node-level public steering just because current code still has them

## Related targets

- [Current-to-target mapping](current-to-target-mapping.md)
- [API surface and trust-lane map](../../redesign/interfaces/api-surface-and-trust-lane-map.md)
- [Plugin tool reference](../../redesign/interfaces/plugin-tool-reference.md)
- [Workflow definition schema](../../redesign/workflows/workflow-definition-schema.md)
