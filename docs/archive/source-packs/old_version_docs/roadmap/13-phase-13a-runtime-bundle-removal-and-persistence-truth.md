# 13A — Phase 13A: Runtime Bundle Removal and Persistence Truth

## Goal

Finish the persistence-truth cleanup first.

Phase 13A removes the fake canonical runtime bundle layer and makes `task_composes` the sole persisted launch-binding and packaging record.

This phase must be completed fully before later Phase 13 launch/runtime-control work is considered implemented.

## Problem statement

The current codebase still keeps legacy runtime bundle structures alive:

- `task_images`
- `runtime_images`
- persisted `runtime_containers`

These structures keep the runtime model dishonest because they compete with the intended canonical truth.

The first job is to remove those structures cleanly, migrate the schema, and make persistence truth unambiguous.

## Scope

### In scope

1. remove `TaskImage`
2. remove `RuntimeImage`
3. remove persisted `RuntimeContainer`
4. expand or reshape `task_composes` so it is the sole persisted launch-binding / packaging record
5. migrate schema/data as needed
6. clean presenters/schemas/routes/tests/fixtures that still depend on the removed structures

### Out of scope

- task-compose-first public launch API refactor
- final policy/replan lifecycle cleanup
- final bridge smoke closeout

## Canonical gaps owned by 13A

13A closes these gaps from Phase 13:

- C1
- C2
- C3
- C4 (persistence-side parts)
- D1
- D2
- D3
- D4
- D5
- E1 (persistence-side parts)
- E3 (persistence-side parts)
- G1
- G2
- G3 (persistence-side parts)
- H2 (persistence-side parts)

## Required persistence decisions

### 1. `task_composes` is the only persisted packaging / launch-binding record

After 13A, persistence truth must be:

- `task_composes` = canonical task-scoped launch-binding record
- no competing persisted runtime bundle truth remains

### 2. Required persisted shape

`task_composes` should persist a lean task-scoped launch record, not a heavyweight package document.

Required fields:

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

Do **not** require a large `requested_spec` / `resolved_snapshot` split for 13A unless implementation proves it is necessary.

### 3. Compatibility posture

13A uses a **hard cutover in backend/runtime truth**.

That means:

- no long-lived dual-write model for `task_images`, `runtime_images`, or `runtime_containers`
- no pretending those legacy tables remain canonical
- if a temporary adapter exists during the change, it must be removed before 13A is considered complete

### 4. Migration posture

13A treats migration as first-class work.

Required migration sequence:

1. expand `task_composes` to the final persisted shape
2. backfill/normalize existing rows if needed
3. switch code paths and read surfaces to `task_composes`
4. remove legacy columns/tables
5. update fixtures/tests after the cutover

13A must explicitly decide whether backfill is required for the current environment or whether a hard-reset/dev-only migration posture is acceptable.

## Concrete code surface inventory

13A should expect to touch, at minimum:

- runtime DB models
- alembic migrations
- runtime schemas
- packaging code
- inspect/bundle/read models
- presenters
- runtime routes that still read legacy bundle truth
- runtime API tests
- task/start tests if they rely on old persistence shape
- fixtures/helpers that assume legacy runtime bundle truth

## Explicit implementation plan

### Step 1. Define final persisted task-compose shape

Implement:

- final DB model shape for `task_composes`
- lean normalized launch fields for workflow, input, refs, dependencies, and root URIs
- explicit materialization fields

Must be true before moving on:

- persisted task-compose truth is concrete enough that migrations and read surfaces are unambiguous without introducing a heavyweight compose document

### Step 2. Switch code paths to `task_composes`

Implement:

- packaging code writes canonical truth only to `task_composes`
- presenters/read surfaces stop depending on task/runtime image/container persistence

Must be true before moving on:

- code no longer needs legacy bundle persistence in the main runtime path

### Step 3. Remove legacy bundle structures

Implement:

- remove model/schema usage of `TaskImage`
- remove model/schema usage of `RuntimeImage`
- remove model/schema usage of persisted `RuntimeContainer`
- remove compatibility leftovers

Must be true before moving on:

- legacy runtime bundle persistence is gone from live code

### Step 4. Land migration-backed cleanup

Implement:

- alembic/schema cleanup
- any required backfill/normalization
- fixture/test updates after cutover

Must be true to finish 13A:

- migrations pass
- focused tests pass
- no stale references remain in code/tests/docs for the removed persistence truth

## Done criteria

13A is only done when all of these are true:

- `task_composes` is the sole persisted packaging / launch-binding record
- `task_images`, `runtime_images`, and persisted `runtime_containers` are removed from live code and schema
- code/tests/fixtures no longer depend on those legacy persisted structures
- migrations and focused tests pass
- the repo is left in a coherent post-cutover state
