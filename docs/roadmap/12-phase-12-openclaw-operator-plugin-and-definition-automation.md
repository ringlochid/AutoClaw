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
- tasks, task-resource bindings, task images, task composes, workspace/context roots
- flows, flow revisions, nodes, attempts, checkpoints, approvals
- runtime images, runtime containers, mounts, typed runtime events, and bounded raw logs
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

1. read-only inspect APIs/tools
2. draft/edit/validate/compile-preview APIs/tools
3. publish flows with strict auth + CAS protection
4. task/runtime operator controls
5. only then, carefully scoped automation on top

## Success criteria

This phase is complete when all of these are true:

- OpenClaw can inspect AutoClaw definitions/runtime through typed, bounded surfaces
- OpenClaw can help author drafts and run validation/compile preview without bypassing AutoClaw truth
- publish/runtime-control flows remain auditable, scoped, and stale-write safe
- AutoClaw remains the single control-plane truth even when OpenClaw becomes a powerful operator client
- the richer integration increases operator leverage without hiding or weakening the underlying runtime contract
