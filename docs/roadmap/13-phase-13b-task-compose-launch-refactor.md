# 13B — Phase 13B: Task-compose Launch Refactor

## Goal

Finish the launch-model refactor after persistence truth is clean.

Phase 13B makes public non-UI launch task-compose-first and stops treating thin task creation as the runnable-task contract.

## Problem statement

Even with persistence cleaned up, launch remains wrong if the system still starts from workflow-first requests plus a thin task payload.

13B fixes the launch contract so the public backend/runtime start model matches the architecture truth.

## Scope

### In scope

1. task-compose-first non-UI create/start API
2. explicit request/response contract for launch
3. no separate user-authored task definition upload before start
4. launch payload carries lean task-compose fields: metadata, workflow, input, roots, context refs, and optional skill dependencies
5. `task` is materialized internally from task-compose start and surfaced in the response/read model

### Out of scope

- legacy persistence removal work already completed by 13A
- final policy/replan cleanup
- final bridge smoke closeout

## Canonical gaps owned by 13B

13B closes these gaps from Phase 13:

- B1
- B2
- B3
- B4
- C1 (launch-surface parts)
- C2 (launch-input parts)
- C3
- G3 (launch-side parts)
- H2 (launch-side parts)

## Required launch decisions

### 1. Public API contract

Required direction:

- primary surface: `POST /task-composes/start` (or an equivalent task-compose-first start route)
- payload contains the lean task-compose start spec
- the user does not upload/create a separate task definition first
- response returns task, task_compose, flow, and flow_revision

If an older workflow-first start path remains temporarily, it must be explicitly marked transitional and removed or deprecated clearly within the broader Phase 13 closeout.

### 2. Required launch payload shape

Launch input must stay small and explicit.

Launch input should carry:

- `metadata`
- `workflow`
- `entrypoint` optional
- `input`
- `roots` / task-owned root creation intent
- `context_refs`
- `skill_dependencies` optional

This must be explicit in schemas, routes, services, and tests.

### 3. Requested vs resolved semantics

13B must ensure the launch path distinguishes clearly between:

- caller-requested launch input
- resolved launch state persisted into `task_composes`

## Concrete code surface inventory

13B should expect to touch, at minimum:

- runtime schemas
- create/start routes
- task/flow start services
- task compose presenters/read models if launch shape changes them
- start-path tests
- docs/runbooks with launch examples

## Explicit implementation plan

### Step 1. Lock the task-compose-first API contract

Implement:

- final schema for `POST /tasks/start`
- explicit request/response examples
- route/service contract built around task compose

Must be true before moving on:

- the chosen launch contract is concrete enough that tests can be rewritten against it without guesswork

### Step 2. Remove separate-task-as-user-start behavior

Implement:

- user-facing start no longer requires a separate task definition upload/create step
- any thin `TaskCreate` shape remains an internal helper only
- launch logic materializes `task` from task compose start

Must be true before moving on:

- public launch truth clearly lives in task compose

### Step 3. Wire launch semantics through services and persistence

Implement:

- metadata, workflow, input, roots, context refs, and skill dependencies flow through the launch path cleanly
- the system materializes `task`, then persists canonical `task_compose`, then starts runtime

Must be true before moving on:

- launch path and persisted task compose agree on the same model

### Step 4. Verify launch contract end-to-end

Implement:

- route/service test updates
- fixture/helper cleanup where launch assumptions changed
- docs/runbook examples aligned with the implemented contract

Must be true to finish 13B:

- focused tests pass
- launch contract is explicit in code and docs
- no stale workflow-first launch truth remains as the primary path

## Done criteria

13B is only done when all of these are true:

- public non-UI create/start is task-compose-first
- thin `TaskCreate` is no longer treated as the runnable-task contract
- launch input can carry task, entrypoint, context, skills, and resources
- requested vs resolved launch semantics are explicit enough in code/tests/docs
- focused tests pass
- the repo is left in a coherent launch-contract state
