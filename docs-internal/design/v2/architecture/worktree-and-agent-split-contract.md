# Worktree and agent split contract

Status: Target

This page defines how V2 implementation work may split across multiple worktrees and agents without fragmenting the controller contract.

## Core rule

Contract work lands before feature implementation work.

Feature worktrees may implement, test, or validate a contract. They must not casually rename shared concepts, add parallel lifecycle states, or redefine runtime truth inside a feature branch.

## Contract promotion model

The pages in `docs-internal/design/v2` are the reviewed V2 contract base.

Use these stages from here:

1. Feature worktrees branch from the reviewed V2 contract base.
2. Contract changes discovered during implementation land as explicit contract patches before dependent feature work changes behavior.
3. Dependent feature branches rebase or update after the contract patch lands.

Implementation agents treat the V2 contract pages as authoritative unless they are assigned a contract-change task.

## Canonical worktree slices

The recommended split is explicit. Each slice owns one contract boundary and consumes the contracts below it.

| Slice                              | Owns                                                                                                                                                                      | Consumes                                                                                                    | Must not redefine                                                  |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `v2-contract-base`                 | shared lifecycle states, boundary state transitions, task event family names, core schemas, promotion docs                                                                | V2 contract docs                                                                                            | feature implementation behavior                                    |
| `v2-event-store`                   | persisted `task_event` records, `event_seq`, hash chain, cursorable query substrate                                                                                       | contract base, audit rules                                                                                  | REST/SSE transport semantics, task source truth                    |
| `v2-sse-api`                       | `GET /control/tasks/{task_id}/events`, SSE stream, replay/backfill/reset behavior                                                                                         | event store                                                                                                 | event persistence shape, task event family names                   |
| `v2-capability-audit`              | effective capability resolution, denial explanations, provenance, per-task auth checks                                                                                    | contract base, role/policy schema                                                                           | feature-specific business behavior                                 |
| `v2-human-request-node-tool`       | node MCP human-request tool, policy gate, pending request creation                                                                                                        | capability/audit, human request schema, event store                                                         | control resolve API, task-continue control semantics, generic chat |
| `v2-human-request-control-api`     | pending request reads, answered-resolution API, controller-owned terminal outcome readback, resolution provenance                                                         | human-request node tool, capability/audit, event store                                                      | node MCP creation path, caller-authored timeout/cancel semantics   |
| `v2-command-run-core`              | long-running command-run records, state machine, timeout/cancel/result truth, terminal continuation state                                                                 | capability/audit, event store                                                                               | concrete command runner                                            |
| `v2-command-runner`                | local long-running command runner, log refs, process cancellation, timeout implementation                                                                                 | command-run core                                                                                            | command-run state names, controller continuation semantics         |
| `v2-control-ui-runtime`            | runtime overview, task detail, execution thread, request pane, command-run pane over control APIs                                                                         | event store, sse api, human-request control api, command-run core                                           | controller truth, authoring behavior                               |
| `v2-definition-authoring-api`      | draft-set route envelopes, draft projection, YAML-body save, normalized JSON shadow or baseline generation, validate/apply or import, and preview API over registry truth | role/policy schema                                                                                          | registry truth model, runtime dispatch truth                       |
| `v2-definition-authoring-ui`       | authoring workbench UI over the API                                                                                                                                       | definition-authoring API, control runtime reads or task-event stream when post-apply start tracking matters | guarded apply or import semantics, draft truth model               |
| `v2-provider-support-setup-doctor` | shared provider support matrix, provider-specific compatibility pages, and provider-aware onboard/configure/doctor CLI/config/output semantics                            | provider runtime config, adapter contracts, current OpenClaw support truth                                  | controller truth, portable workflow schema                         |
| `v2-codex-adapter`                 | Codex app-server launch/session/event/human-request normalization                                                                                                         | adapter contract, event store, human-request control API, provider support docs                             | core controller vocabulary                                         |
| `v2-claude-adapter`                | Claude SDK permission/session/MCP normalization                                                                                                                           | adapter contract, event store, human-request control API, provider support docs                             | core controller vocabulary                                         |
| `v2-platform-services`             | macOS/Windows service packaging and installer parity                                                                                                                      | contract base                                                                                               | runtime controller contract unless explicitly assigned             |
| `v2-integration-e2e`               | cross-slice tests, migration smoke tests, real-provider scenarios                                                                                                         | merged feature slices                                                                                       | feature contracts                                                  |

The slice names are recommended branch/worktree names. A team may choose different git names, but the ownership boundaries above remain the contract.

## Dependency graph

Use this implementation dependency order:

```text
v2-contract-base
  -> v2-event-store
  -> v2-sse-api

v2-contract-base
  -> v2-event-store
  -> v2-capability-audit
  -> v2-human-request-node-tool
  -> v2-human-request-control-api

v2-event-store + v2-capability-audit
  -> v2-command-run-core
  -> v2-command-runner

v2-sse-api + v2-human-request-control-api + v2-command-run-core
  -> v2-control-ui-runtime

v2-contract-base
  -> v2-definition-authoring-api
  -> v2-definition-authoring-ui

v2-event-store + v2-human-request-control-api + v2-capability-audit
  -> v2-codex-adapter

v2-event-store + v2-human-request-control-api + v2-capability-audit
  -> v2-claude-adapter

v2-contract-base + v2-codex-adapter + v2-claude-adapter
  -> v2-provider-support-setup-doctor

all merged core slices
  -> v2-integration-e2e
```

Rules:

- `v2-event-store` must land before `v2-sse-api`.
- `v2-human-request-node-tool` and `v2-human-request-control-api` must stay separate because they sit on different trust surfaces.
- `v2-command-run-core` and `v2-command-runner` must stay separate because one owns controller truth and the other owns local execution plumbing.
- `v2-control-ui-runtime` consumes runtime contracts and must not invent unsupported metrics or workflow-editor semantics in the UI.
- `v2-control-ui-runtime` may choose `Vite + React + TypeScript + Tailwind CSS` for implementation speed, but that stack choice stays slice-local and must not leak into controller vocabulary, provider support claims, or runtime data contracts.
- when `v2-control-ui-runtime` uses `React + Tailwind`, it should contain the main development risks locally through a typed API or view-model layer, shared UI primitives, and centralized root/base-path handling rather than scattered literal paths or repeated utility-class sprawl.
- `v2-definition-authoring-api` owns the YAML-body plus normalized-JSON-shadow draft projection rules; UI or import helpers must not fork that draft truth model.
- `v2-provider-support-setup-doctor` owns the shared support-matrix vocabulary plus provider-specific compatibility docs; Codex or Claude support claims must not be frozen ahead of adapter or doctor proof.
- adapter slices start only after event normalization and human-request resolution paths are stable.
- UI slices consume APIs; they do not define controller truth.

## Slice contract headers

Every feature worktree must keep a short slice header in its planning note, PR body, or handoff note.

Template:

```md
Slice: v2-human-request-node-tool
Base: v2-contract-base
Depends on:

- v2-capability-audit
- v2-event-store

Owns:

- node MCP human request tool
- policy gate before request creation
- pending request creation path

Consumes:

- pending human request schema
- capability enum
- task event family names

Must not change:

- task event record shape
- SSE cursor semantics
- task continue control semantics
- control resolve API

Runtime isolation:

- AUTOCLAW_HOME=.runtime/v2-human-request-node-tool
- AUTOCLAW_PORT=<slice-specific port>
- database/log/artifact dirs are slice-local
```

## Shared contract vocabulary

These names are shared contract vocabulary and require a contract patch to change:

- waiting causes
- boundary state transitions
- pending human request kinds and terminal resolution kinds
- command-run states and terminal event mapping
- task event family names
- capability family names and enum values
- portable role and policy schema fields
- provider-preference and runtime-config schema fields
- provider support and compatibility page family plus shared support-status vocabulary
- adapter normalization lanes

Feature worktrees may add local implementation names beneath these concepts, but public docs, APIs, DB records, tests, and UI-visible labels should use the shared vocabulary unless the contract is updated first.

## Shared-file rule

High-collision files should be changed in `v2-contract-base` or by one assigned slice owner at a time.

Examples:

- controller state and lifecycle models
- database migrations for shared runtime records
- public/control API route registries
- node MCP, operator MCP, and control API tool registries
- event-family constants
- role/policy schema validators
- provider support matrix docs and provider-specific setup or doctor route registries
- prompt-family inventory or prompt-pack root metadata

If a feature branch needs to modify one of these files, the branch owner must state whether it is:

- consuming an already-reviewed contract
- proposing a contract patch
- adding a feature-local implementation under an existing contract

## Contract patch rule

When a feature slice discovers the reviewed contract is wrong or incomplete, it must stop treating the issue as local implementation detail.

The required path is:

1. open a contract patch against the relevant V2 contract page
2. name every dependent slice affected by the change
3. update shared vocabulary, schema, and event names in one place
4. rebase or update dependent feature branches after the contract patch lands

Examples that require a contract patch:

- adding a pending human request terminal state
- renaming a task event family
- changing SSE cursor semantics
- adding a capability enum value
- changing command-run terminal continuation behavior
- changing adapter session-scope rules

Examples that do not require a contract patch:

- changing an internal function name under an existing contract
- adding a local test helper
- changing UI layout while preserving API behavior
- improving an adapter retry implementation without changing normalized events

## Agent handoff requirement

Every implementation agent working from a feature worktree must return a short handoff note with:

- slice name
- feature worktree and branch name
- base commit or contract revision consumed
- contract pages consumed
- shared vocabulary touched
- shared files touched
- tests or checks run
- known contract drift risk
- next integration step

The note is part of the merge gate. A branch with unclear contract drift should not merge into the contract base.

## Runtime isolation rule

Parallel worktrees must not share mutable runtime state by default.

Each worktree should use distinct:

- service port
- runtime directory
- SQLite database or database schema
- log directory
- artifact/output directory
- local adapter session/cache directory

Parallel agents may share a running AutoClaw service only when the assigned task is explicitly integration testing shared-service behavior.

## Merge order

Recommended merge order:

1. `v2-contract-base`
2. `v2-event-store`
3. `v2-capability-audit`
4. `v2-sse-api`
5. `v2-human-request-node-tool`
6. `v2-human-request-control-api`
7. `v2-command-run-core`
8. `v2-command-runner`
9. `v2-control-ui-runtime`
10. `v2-definition-authoring-api`
11. `v2-definition-authoring-ui`
12. `v2-codex-adapter`
13. `v2-claude-adapter`
14. `v2-provider-support-setup-doctor`
15. `v2-platform-services`
16. `v2-integration-e2e`

This order keeps the controller contract, event substrate, and capability checks stable before features, UI, and adapters depend on them.

Independent documentation-only work may run earlier, but runtime behavior should not merge ahead of the contracts it consumes.

## Non-goals

This contract does not define:

- exact git branch names
- CI provider setup
- human team assignment
- implementation code layout

Those details may vary, but they must preserve the contract-first split above.

## Related contracts

- [Controller contract and resumable execution](controller-contract-and-resumable-execution.md)
- [Capability, security, and audit](../interfaces/capability-security-and-audit.md)
- [Control API and task event stream](../interfaces/control-api-and-task-event-stream.md)
- [Human request and approval contract](../interfaces/human-request-and-approval-contract.md)
- [Command run and long-running boundary](command-run-and-long-running-boundary.md)
- [Control UI runtime and authoring surfaces](../interfaces/control-ui-runtime-and-authoring-surfaces.md)
- [Adapter contract](adapter-contract.md)
