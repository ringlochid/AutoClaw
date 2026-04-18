# 12 — Phase 12: OpenClaw Operator Plugin and Definition Automation

## Goal

After AutoClaw itself is stable and working end-to-end, add a richer OpenClaw-side AutoClaw integration surface that can:

- inspect AutoClaw definitions and runtime state deeply
- help operators draft/validate/publish definitions
- help operators create/manage tasks and invoke runtime control actions
- do all of that **without** turning OpenClaw into the AutoClaw control plane

## Why this is later, not now

This is intentionally **not** the next core milestone.

AutoClaw should first be solid in its own right:

- runtime truth and recovery semantics must be stable
- compiler/resource/skill semantics must be explicit
- console/operator surfaces must already exist and be truthful
- task/resource ownership and manifest/runtime truth boundaries must already be trustworthy

If this plugin/operator surface lands too early, it risks hiding design flaws behind automation and creating source-of-truth confusion.

Note:

- bounded worker-scoped query/bundle surfaces may land earlier if they are needed for reliable delegated replan/review work
- this phase is about the broader operator/client surface, not those narrower reliability-oriented worker helpers

## Preconditions

Do not start this phase seriously until these are true:

- Phase 8 closeout is complete enough that the bridge is operationally honest
- Phase 9 local-first packaging/installability is real
- Phase 10 compiler semantics are explicit and fail-closed
- Phase 11 graph/operator/definition-authoring surfaces are real enough that AutoClaw can already be operated directly without relying on OpenClaw-side magic

## Core boundary

OpenClaw may become a **powerful client** of AutoClaw.
It must **not** become a second control plane.

For reliability, this later-stage client surface may still be semantics-thick:

- deterministic joins and bundle assembly are good
- transcript reconstruction as hidden control logic is not

That means:

- AutoClaw remains the owner of DB truth, runtime transitions, compiled plans, tasks, flows, revisions, manifests, approvals, and definition publishing
- OpenClaw interacts through typed AutoClaw APIs/tools
- OpenClaw must not write DB rows directly or invent a parallel state model

## In scope

### 1. Read-only inspect surfaces

Expose targeted inspect capability from OpenClaw into AutoClaw for:

- workflow/role/policy/skill definitions and versions
- compiled plans and effective-node payloads
- tasks, task-resource bindings, task composes, workspace/context roots
- flows, flow revisions, nodes, attempts, checkpoints, approvals
- derived live runtime state from node sessions/manifests/attempts, plus bounded typed events and raw logs
- context manifests and manifest-derived audit facts

The emphasis should be **targeted queryability**, stable snapshot/bundle semantics, and server-side joins, not dumping the entire AutoClaw world into every model context.

### 2. Draft/create/validate/compile-preview flows

Allow OpenClaw operator sessions to:

- create definition drafts
- update definition drafts
- run validation/compile preview
- inspect diffs/provenance/errors before publish

This should work through the same typed AutoClaw APIs that the console would use.

### 3. Publish flows with strict guardrails

Allow privileged OpenClaw operator sessions to publish definitions only through explicit guarded routes.

Publish operations should require:

- explicit target object/version intent
- compare-and-swap or equivalent expected-version protections
- actor/audit metadata
- clear separation from draft editing

### 4. Task/runtime operator actions

Allow privileged OpenClaw operator sessions to perform scoped operator actions such as:

- create/update task intent
- link or rebind task workspace/context roots
- request replans
- adopt validated replans
- resolve approvals
- retry/cancel flows

These actions must still feed AutoClaw’s own runtime state machine and audit records.

## Phase 12 runtime-model cleanup

Before Phase 12 widens the OpenClaw operator/plugin surface, AutoClaw should simplify the Phase 9 packaging/runtime persistence model.

Current code review findings:

- `ensure_task_compose_for_compiled_plan(...)` creates the `TaskImage` snapshot and `TaskCompose` together; the image is currently just a hash plus task binding snapshot, not an independently managed lifecycle layer
- `upsert_runtime_container(...)` creates the `RuntimeImage` snapshot and `RuntimeContainer` together; the image is currently just a hash plus compiled node/effective payload snapshot
- `RuntimeContainer` mostly denormalizes `node_sessions`, `node_attempts`, `flow_nodes`, and current context-manifest state, and is primarily used as a convenience read surface for worker bundles

Phase 12 should therefore:

1. keep `task_composes` as the sole persisted packaging record
2. fold former task-image fields into compose/task snapshot payloads
3. treat compiled workflow state (`compiled_plans` and effective node payload) as the immutable execution spec instead of persisting separate `runtime_images`
4. replace persisted `runtime_containers` with a derived runtime view assembled from `node_sessions`, flow/node state, attempts, and manifests
5. update worker bundle routes, presenters, schemas, and tests to expose `task_compose` plus that derived runtime view


## Permission model

Keep at least two capability lanes:

### Worker lane

For delegated execution workers, allow only the minimum slice needed for their node/task/runtime context.
Typical worker abilities should be narrow:

- inspect their own task/flow/node/manifest slice through compact typed bundles rather than raw transcript archaeology
- propose changes
- maybe create drafts
- maybe request approvals/replans/checkpoints through existing runtime paths

### Operator lane

For trusted operator sessions, allow broader read/write capability:

- inspect broader definition/runtime surfaces
- create/edit drafts
- validate/compile preview
- publish with guardrails
- perform scoped runtime operator actions

Do not hand full publish/operator control to every delegated worker session.
Default plugin installs should stay worker-lane by default, with broader operator/query and registry-write tools enabled only through explicit capability opt-ins.

## Audit and concurrency rules

Every write or control mutation should record:

- actor identity
- source session / agent / node attempt when applicable
- reason / intent
- expected base version or active revision token
- resulting object ids / version ids / revision ids

Use stale-write protection everywhere practical:

- draft updates
- publishes
- task rebinding
- replan adoption
- approval resolution when version-sensitive

## Explicit non-goals

This phase should **not**:

- move AutoClaw control truth into OpenClaw
- let OpenClaw write AutoClaw DB rows directly
- make every delegated worker a full-definition publisher
- replace the console/operator surface as AutoClaw’s primary truthful UI
- dump all definitions/runtime state into model context by default
- create a second scheduler or parallel runtime state model inside an OpenClaw plugin
- invent a second image/compose/container abstraction inside OpenClaw instead of consuming AutoClaw’s typed model

## Suggested implementation order

1. runtime packaging cleanup, migrate inspect/bundle surfaces from `task_images` / `runtime_images` / `runtime_containers` to `task_compose` + derived runtime view
2. read-only inspect APIs/tools
3. draft/edit/validate/compile-preview APIs/tools
4. publish flows with strict auth + CAS protection
5. task/runtime operator controls
6. only then, carefully scoped automation on top

## Success criteria

This phase is complete when all of these are true:

- OpenClaw can inspect AutoClaw definitions/runtime through typed, bounded surfaces
- the runtime/operator inspect surface no longer depends on redundant `task_images`, `runtime_images`, or `runtime_containers` persistence; `task_compose` is the packaged-task truth and live runtime state is derived from existing orchestration/session tables
- OpenClaw can help author drafts and run validation/compile preview without bypassing AutoClaw truth
- publish/runtime-control flows remain auditable, scoped, and stale-write safe
- AutoClaw remains the single control-plane truth even when OpenClaw becomes a powerful operator client
- the richer integration increases operator leverage without hiding or weakening the underlying runtime contract
