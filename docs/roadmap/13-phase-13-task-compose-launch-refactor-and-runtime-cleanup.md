# 13 — Phase 13: Task-compose Launch Refactor and Runtime Cleanup

## Goal

Finish every remaining non-UI backend/runtime gap that earlier phases left open, and make the docs/code line up honestly.

Phase 13 is the carry-forward phase for unfinished non-UI backend/runtime work from earlier phases. It owns the remaining implementation work around:

- fresh bridge verification
- task-compose-first create/start
- task compose as the sole launch-binding and packaging record
- legacy runtime bundle removal
- runtime inspect/bundle cleanup
- policy/replan boundary enforcement
- final non-UI verification

## Problem statement

The docs now describe a cleaner model than the code actually implements.

The core model to lock is:

- **workflow** is the reusable orchestration definition
- **task compose** is the small task-scoped start surface and launch record
- **task** is created/materialized by the system from task compose start, not uploaded separately by the user
- **runtime** is the live execution state

But the current implementation still mixes these layers.

The main concrete problems are:

1. launch is still too workflow-first instead of task-compose-first
2. `task_composes` exists but is not yet the real runnable-task contract
3. legacy runtime bundle structures still exist in code and schema
4. inspect/bundle semantics still depend too much on those legacy structures
5. policy/replan boundaries are clearer in docs than in code
6. bridge auth is fixed, but fresh live end-to-end proof is still missing

This phase exists to close those gaps in one coherent backend/runtime pass.

## Canonical non-UI gap inventory

This section is the single source of truth for the remaining non-UI backend/runtime gaps.

### A. Bridge / plugin / execution proof

#### A1. Plugin auth wiring

**Status:** fixed in code.

What is already true:

- internal API key is wired
- bridge requests send gateway bearer token plus internal API key

What Phase 13 still needs:

- keep this as required runtime truth
- verify it with a fresh live bridge smoke

#### A2. Fresh live bridge smoke proof

**Status:** still required.

Need one fresh end-to-end proof of:

- plugin/tool call
- Gateway
- AutoClaw internal API
- successful response

This is now a verification gap, not an architecture gap.

### B. Launch surface / task start model

#### B1. Public create/start is still workflow-first

Current issue:

- public start still centers workflow start plus a thin task payload

Target:

- public non-UI create/start is task-compose-first

#### B2. Separate user-authored task creation should not be the start surface

Current issue:

- hidden/deprecated task creation remains distinct from actual launch needs
- the docs still imply a public split between task creation and launch that the product should avoid

Target:

- the user starts work with task compose
- `task` is materialized internally from task compose start and remains a runtime/control-plane record
- any thin `TaskCreate` shape is an internal helper only, not a user-facing authored contract

#### B3. Public launch input should stay small, not become a heavyweight compose spec

Current issue:

The earlier roadmap version over-modeled task compose as a large requested-vs-resolved launch bundle.

Target:

- launch input should stay small and explicit
- the user-facing task compose should carry only the fields needed to start real work cleanly:
  - metadata/title/description/labels
  - starting workflow and optional entrypoint
  - task input payload
  - task-owned root creation/binding intent for workspace/context/manifests
  - context refs
  - skill dependencies when needed
- avoid a heavy package/image/container abstraction in the public task compose contract unless a later real need appears

#### B4. No first-class task-compose-centric start API

Current issue:

- backend still lacks a proper non-UI start surface built around task compose

Target:

- a first-class task-compose-centric create/start API exists and is verified

### C. Task compose model gaps

#### C1. `task_composes` is not yet the real launch contract

Current issue:

- `task_composes` exists, but not yet as the primary runnable-task binding contract

Target:

- `task_composes` becomes the canonical task-scoped launch image

#### C2. Task compose should be a small launch record, not a heavyweight package document

Current issue:

The docs and target model have drifted too far toward a large launch bundle.

Target:

Task compose should represent only the durable task-scoped start facts that matter:

- task metadata
- workflow key and optional entrypoint
- task input payload
- context refs
- task-owned roots/bindings for workspace/context/manifests
- optional skill/runtime dependencies
- materialization metadata such as created paths/timestamps

But the current code does not yet model this cleanly.

#### C3. Task compose should stay simple unless a stronger requested-vs-resolved split is proven necessary

Current issue:

- current code overloads one payload field
- the earlier roadmap target over-corrected toward a large requested-vs-resolved dual document

Target:

- keep task compose simple by default
- store explicit normalized launch fields and small materialization metadata rather than forcing a large `requested_spec` / `resolved_snapshot` contract immediately
- only add a stronger split later if compose remint/repro/history needs actually require it

#### C4. Task compose lifecycle rules are not fully implemented

Target rules:

- retries reuse the same compose when launch meaning is unchanged
- launch-meaning/resource changes mint a new compose

Current code does not yet enforce this cleanly.

### D. Legacy runtime bundle layer cleanup

#### D1. `TaskImage` still exists
#### D2. `RuntimeImage` still exists
#### D3. Persisted `RuntimeContainer` still exists

These should all be removed.

#### D4. Runtime bundle/read surfaces still depend on legacy concepts

Current issue:

- schemas
- presenters
- routes
- tests

still reflect the legacy bundle ontology.

#### D5. No completed migration removes the legacy bundle tables/columns

Current issue:

- migration-backed cleanup is still missing

Target:

- live code and schema no longer depend on those tables/columns

### E. Workflow / task compose / runtime boundary gaps

#### E1. Boundaries are clearer in docs than in code

Target boundary:

- workflow = reusable orchestration image
- task compose = task-scoped launch image
- runtime = live execution state

Current code still blurs these layers.

#### E2. Session/runtime state can still leak into the wrong conceptual layer

Target:

- session belongs to runtime, not workflow/task-compose truth

#### E3. Runtime inspect/bundle semantics are still too tied to legacy packaging state

Target:

- live state derives from flows, revisions, attempts, sessions, manifests, approvals, checkpoints, and replans
- not from fake persisted runtime-container truth

### F. Policy / replan boundary gaps

#### F1. Policy boundary is documented but not fully enforced by the launch model

Target:

- policy remains workflow / compiled-plan-node level
- task compose carries only task-scoped launch constraints

#### F2. Replan boundary is documented but not fully implemented

Target:

- replan remains runtime-side unless launch meaning or task-scoped resources/dependencies materially change

#### F3. Replan / compose relationship is not operationally clean yet

Target:

- runtime-only structural replan and launch-binding-changing replan are handled differently and explicitly

### G. Runtime packaging / resource binding gaps

#### G1. `task_composes` is not yet the sole persisted packaging record
#### G2. Packaging logic still carries extra legacy layers
#### G3. Resource/dependency binding is not yet centered on task compose

These all need to be resolved together.

### H. Verification / completion gaps

#### H1. All non-UI backend/runtime gaps are not yet actually closed in code
#### H2. Docs are still ahead of code in important areas
#### H3. Final end-to-end verification is incomplete

## In scope

Phase 13 includes all non-UI backend/runtime work needed to close the gaps above.

### Included

1. fresh live bridge smoke verification
2. task-compose-first launch refactor
3. task compose model cleanup
4. legacy runtime bundle removal
5. inspect/bundle/runtime truth cleanup
6. policy/replan boundary cleanup
7. migration-backed schema cleanup
8. focused test and verification closeout

### Excluded

- UI / console polish
- first-class reusable compose registry objects if task compose is sufficient for now
- skill artifact upload if skills remain reference-only

## Carry-forward from previous phases

### Phase 3 carry-forward

- any still-open runtime/model cleanup where the target flow-scoped runtime contract is documented but not yet fully realized in code

### Phase 4 carry-forward

- any still-open non-UI backend/runtime operator-surface semantics that remain relevant to inspect/bundle/runtime truth

### Phase 5 carry-forward

- post-approval invariant vs configurable-policy cleanup if still unfinished
- typed runtime/operator event surface follow-up if still unfinished

### Phase 6.5 carry-forward

- any still-open non-UI backend/runtime stabilization or surface-cleanup debt from the pre-Phase-7 pass

### Phase 7 carry-forward

- any still-open non-UI backend/runtime looping/governance follow-up that was left as remaining-gap text rather than fully completed implementation

### Phase 8 carry-forward

- fresh live bridge smoke verification still required as explicit evidence
- bridge closeout should be shown with current auth/runtime wiring, not only older docs

### Phase 9 carry-forward

- `task_composes` is not yet the sole persisted packaging / launch-binding record
- `task_images`, `runtime_images`, and persisted `runtime_containers` still exist in code
- migration-backed removal of those legacy tables/columns is still unfinished

### Phase 10 carry-forward

- public create/start is still workflow-first instead of task-compose-first
- the runnable-task contract is still too thin
- task compose does not yet fully express launch-time task intent/context/resources/dependencies

### Phase 11 carry-forward

- runtime inspect/bundle semantics still reflect legacy packaging/runtime-container thinking
- policy boundary is documented more clearly than implemented
- replan vs task-compose lifecycle rules are documented more clearly than implemented

### Phase 12 carry-forward

- runtime-model cleanup is planned but not yet fully landed in code
- worker bundle/read surfaces still need to move from legacy runtime bundle persistence to task compose plus derived runtime view
- docs are ahead of code and need to become honest again by finishing the implementation

## Concrete code surface inventory

Phase 13 should expect to touch, at minimum, the following backend/runtime surfaces if the current codebase remains similar:

- runtime DB models
- alembic migrations
- runtime schemas
- packaging code
- task/flow start services
- create/start routes
- inspect/bundle routes
- presenters/read models
- policy/replan lifecycle code
- runtime API tests
- task/start tests
- fixtures/helpers that currently assume legacy runtime bundle truth
- bridge verification docs/tests/runbooks

If implementation avoids touching one of these categories, that should be a conscious decision rather than an accident.

## Gap-to-workstream mapping

### Workstream 1: Bridge closeout

Closes:

- A2
- H3 (bridge portion)

### Workstream 2: Launch refactor

Closes:

- B1
- B2
- B3
- B4
- C1
- C2
- C3
- C4
- G3

### Workstream 3: Legacy runtime bundle removal

Closes:

- D1
- D2
- D3
- D4
- D5
- G1
- G2

### Workstream 4: Runtime truth / inspect cleanup

Closes:

- E1
- E2
- E3
- H2 (partly)

### Workstream 5: Policy / replan boundary cleanup

Closes:

- F1
- F2
- F3

### Workstream 6: Migration + verification closeout

Closes:

- H1
- H2
- H3

## Explicit implementation decisions

### 1. `task_composes` persistence shape

Phase 13 should lock a lean persisted task compose record rather than a heavyweight package document.

Required persisted shape should stay small and explicit:

- `task_id`
- `workflow_version_id` and/or `compiled_plan_id`
- `entrypoint` nullable
- `status`
- `metadata` JSON
- `input_payload` JSON
- `context_refs` JSON
- `skill_dependencies` JSON
- `workspace_root_uri` nullable
- `context_root_uri` nullable
- `manifest_root_uri` nullable
- `materialization_root`
- `created_at`
- `updated_at`
- `superseded_at` nullable only if remint lineage is needed now

Do **not** require a large `requested_spec` / `resolved_snapshot` split for Phase 13 unless implementation proves it is necessary.

### 2. Public API contract

Phase 13 should choose a task-compose-centric public non-UI launch contract and make it explicit.

Required direction:

- primary surface: `POST /task-composes/start` (or an equivalent task-compose-first start route)
- payload contains the lean task compose start spec
- the user does **not** upload/create a separate task definition first
- the system materializes `task`, then persists `task_compose`, then creates `flow` and `flow_revision`
- response returns task, task_compose, flow, and flow_revision

`POST /tasks/composes/start` is the public launch contract. Older workflow-first public start has been removed.

### 3. Compatibility posture

Phase 13 should default to a **hard cutover in backend/runtime truth**, with compatibility retained only when necessary to keep tests or consumers moving during the transition.

That means:

- no long-lived dual-write model for `task_images` / `runtime_images` / `runtime_containers`
- no pretending legacy runtime bundle tables remain canonical
- if temporary compatibility adapters exist, they should be marked transitional and removed before Phase 13 closeout
- compatibility should be treated as a short migration aid, not as a second source of truth

### 4. Worker bundle target contract

Phase 13 should define the target worker-bundle/read shape explicitly.

Worker bundle must contain:

- flow
- task
- compiled_plan
- current_node
- current_attempt
- current_session
- current_manifest
- task_compose
- recent_checkpoints
- approvals
- recent_manifests
- context_items
- events

Worker bundle should not contain persisted runtime-container truth.

### 5. Replan remint rule

Phase 13 should implement this decision rule explicitly:

- **structural-only replan** that changes flow topology/execution plan but not launch binding -> new flow revision only
- **launch-binding-changing replan** that changes task-scoped resources, dependencies, or effective launch meaning -> mint a new task compose

This rule should exist in code/tests/docs, not just prose.

### 6. Migration posture

Phase 13 should treat migration as a first-class workstream.

Expected migration sequence:

1. expand `task_composes` to carry the final launch-binding shape
2. backfill/normalize data if needed
3. switch code paths and read surfaces to the new truth
4. remove legacy columns/tables
5. update tests/fixtures after the cutover

The implementation should make an explicit decision on whether backfill is required for existing rows or whether a hard-reset/dev-only migration posture is acceptable for the current environment.

### 7. Test and fixture scope

Phase 13 test work must explicitly include:

- fixture/helper cleanup
- runtime API assertion updates
- launch-path tests
- migration-sensitive tests where needed
- bridge smoke evidence/update

### 8. Evidence location for bridge closeout

Phase 13 must record bridge closeout evidence in a stable place.

Acceptable locations:

- an e2e/runbook doc
- a dedicated test note or verification section
- roadmap closeout notes

Do not leave the bridge smoke as a verbal claim only.

## Target model

### Workflow

Reusable orchestration definition:

- graph
- role refs
- skill refs
- policy refs
- node defaults

### Task compose

Small task-scoped start surface and launch record:

- metadata/title/description/labels
- starting workflow and optional entrypoint
- task input payload
- context refs
- task-owned roots/bindings for workspace/context/manifests
- optional skill/runtime dependencies
- materialization metadata

### Task

Materialized runtime/control-plane record created by the system from task compose start:

- stable task identity
- task status
- task input payload
- relationships to task-owned roots and runtime state

### Runtime

Live execution facts:

- flow
- flow revisions
- flow nodes
- node attempts
- node sessions
- context manifests
- approvals
- checkpoints
- replans

## Execution split

Phase 13 stays one roadmap phase, but it should be implemented as three completion-grade subphases so each one can be reviewed, cleaned up, refactored properly, and tested before the next one starts.

### 13A

See `13-phase-13a-runtime-bundle-removal-and-persistence-truth.md`.

Boundary:

- persisted truth
- migration-backed removal of the legacy runtime bundle layer
- `task_composes` as the sole persisted launch-binding and packaging record

### 13B

See `13-phase-13b-task-compose-launch-refactor.md`.

Boundary:

- public non-UI launch contract
- task-compose-first create/start
- thin task creation reduced to task-record role only

### 13C

See `13-phase-13c-runtime-truth-policy-replan-and-verification.md`.

Boundary:

- runtime truth / inspect/bundle cleanup
- policy/replan boundary enforcement
- fresh bridge smoke and final verification closeout

Implementation means: complete one subphase fully before claiming that subphase done.

## Done criteria by gap cluster

### Bridge closeout is done when

- plugin auth remains wired
- one fresh live bridge smoke passes end-to-end
- evidence is recorded in docs/tests/runbook notes

### Launch refactor is done when

- public non-UI create/start is task-compose centric
- thin `TaskCreate` is no longer treated as the runnable-task contract
- launch input can carry task intent, entrypoint, context, skills, and resources

### Task compose model is done when

- `task_composes` is the canonical task-scoped launch image
- payload shape matches the architecture docs
- requested vs resolved launch meaning is clear enough in code/tests/docs
- lifecycle rules around reuse vs remint are explicit

### Runtime bundle cleanup is done when

- `task_images`, `runtime_images`, and persisted `runtime_containers` are removed from live code and schema
- presenters/schemas/routes/tests no longer depend on them
- migrations cover the removal honestly

### Runtime truth cleanup is done when

- worker bundle / inspect surfaces read task compose plus derived runtime state
- live state is derived from real orchestration/session tables
- no fake persisted runtime-container truth remains

### Policy / replan cleanup is done when

- policy meaning stays workflow/compiled-node level
- task compose carries only task-scoped launch constraints
- runtime replan lifecycle handling matches the documented model

### Final closeout is done when

- focused tests and migrations pass
- docs are no longer ahead of code for this area
- it is honest to say all non-UI backend/runtime gaps tracked here are implemented

## Overall done criteria

Phase 13 is only done when all of these are true:

- plugin auth is wired and a fresh live bridge smoke passes
- public non-UI create/start is task-compose centric
- `task_composes` is the sole persisted launch-binding and packaging record
- `task_images`, `runtime_images`, and persisted `runtime_containers` are removed from live code and schema
- inspect/bundle/runtime read surfaces use task compose plus derived runtime state
- policy and replan boundaries match the documented model
- focused tests and migrations pass
- previous phases no longer carry stale unfinished backend/runtime items that now belong to Phase 13
