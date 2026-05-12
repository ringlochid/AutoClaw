# Current operator roles and API trust lanes

Status: Current

Last verified: 2026-05-12

This page owns the exact current operator definition, trust-lane split, and
the difference between operator, callback caller, worker, parent/root, and
controller in the shipped API tree.

For the exact current path families and route nouns, see
`api-surface-and-route-map.md`.

## `CurrentOperatorDefinitionContract`

In the current system, `operator` means a trusted principal allowed to inspect
or steer runtime state through the API-key-protected operator routes.

An operator may be:

- a human using HTTP or future UI clients with the configured API key
- a trusted automation client authenticated into the operator routes

Operator is defined by authority and allowed actions, not by embodiment alone.

## `CurrentUserVsOperatorContract`

- `user` supplies task intent, task root, or surrounding product inputs
- `operator` inspects, continues, pauses, cancels, or reads task-scoped
  observability for the current runtime

The same human may play both roles, but the authority is different.

## `RoleBoundaryMatrix`

| Role         | Current meaning                                         | Owns                                                                 | Does not own                                  |
| ------------ | ------------------------------------------------------- | -------------------------------------------------------------------- | --------------------------------------------- |
| `operator`   | trusted runtime-steering principal                      | `/runtime`, `/operator`, `/observability` actions                    | callback write authority, controller truth    |
| `worker`     | current worker-node callback caller                     | checkpoint and boundary writes for the bound dispatch                | operator reads, parent/root tools             |
| `parent`     | current parent-node callback caller                     | parent/root tool calls and parent/root boundary decisions            | operator reads, controller truth              |
| `root`       | current root-node callback caller                       | root-only `release_blocked` and root closure decisions              | operator reads, delegated worker execution    |
| `controller` | runtime truth owner                                     | DB rows, dispatch/session bindings, legality checks, materialization | delegated execution content                   |
| `provider`   | continuity/provider-event concept only in this tree     | transport-state and provider-event projections                       | API-lane authority or controller truth        |

`worker` is never `operator`.

`parent` or `root` on the callback lane is still not `operator`.

## `OperatorLaneMatrix`

| Lane             | Typical caller                        | Current capability level                                                             | Notes                                                |
| ---------------- | ------------------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------------------- |
| health lane      | any caller                            | `/healthz`, `/readyz`                                                                | unauthenticated                                       |
| operator lane    | operator                              | runtime list/read, continue, pause, cancel, snapshot, trace, observability file refs | protected by `X-AutoClaw-API-Key`                    |
| callback lane    | bound worker, parent, or root caller  | checkpoint writes, boundary acceptance, parent/root tools                            | protected by `X-Autoclaw-Session-Key`                |
| internal-key gap | none on the shipped router            | none                                                                                 | `require_internal_api_key()` exists but is unused    |

Lane and role are not identical in the current system.

The callback lane is bound to one live dispatch. It is not a general trusted
operator lane.

## Current trust lanes

### 1. Operator lane

Protected by `X-AutoClaw-API-Key` via `require_api_key`.

Current grouped surfaces:

- `/runtime/*`
- `/operator/*`
- `/observability/*`

Current operator actions on this lane include:

- list or inspect runtime tasks
- continue, pause, or cancel a task runtime
- read operator snapshot and trace views
- fetch task-scoped observability file refs

Operator reads are read-only in the shipped tree: they surface current file
refs but do not repair or rematerialize projections inline.

### 2. Callback lane

Protected by the live callback binding header `X-Autoclaw-Session-Key`.

Current grouped surfaces:

- `/callback/tasks/{task_id}/checkpoint`
- `/callback/tasks/{task_id}/boundary`
- `/callback/tasks/{task_id}/tools/{tool_name}`

Current lane uses include:

- worker checkpoint publication
- worker terminal or retry boundary submission
- parent/root child-assignment staging
- parent/root structural subtree edits
- parent/root release-precondition marking
- controller-side validation resolves structural role/policy refs from current
  registry rows; the callback lane does not expose a separate registry-read surface

This lane is explicitly non-operator. It is scoped to the currently live
dispatch and becomes invalid when operator pause revokes it or the dispatch is
cancelled, fenced, or replaced.

The current implementation also validates that the trusted session binding
still matches the live dispatch plus the persisted current assignment and
attempt basis for that task before a callback write can commit.

Callback writes now return after controller truth and durable `runtime_effects`
rows commit. Manifest, attempt, dispatch, artifact-pointer, and observability
file regeneration follows asynchronously through the post-commit effect runner.

### 3. Health lane

Unauthenticated:

- `GET /healthz`
- `GET /readyz`

### 4. No current browser bootstrap or legacy internal lane

Current code does not ship the older browser-bootstrap, internal, flow,
approval, or registry route families.

The config still carries `internal_api_key`, but no current router uses the
internal-key dependency.

## `CurrentOperatorActionTable`

| Action                      | Current lane | Current effect                                                              |
| --------------------------- | ------------ | --------------------------------------------------------------------------- |
| inspect runtime list        | operator     | read `GET /runtime/tasks`                                                   |
| inspect one task runtime    | operator     | read `GET /runtime/tasks/{task_id}`                                         |
| continue task runtime       | operator     | reopen or resume the current task runtime when revision expectations match, but only after any pause or accepted-boundary inactivity wait is resolved |
| pause task runtime          | operator     | revoke callback access, mark the flow paused, and keep replacement dispatch blocked until inactivity is proven or timed out |
| cancel task runtime         | operator     | mark abort requested, revoke callback access, and close the current task flow while the dispatch stays controller-visible until inactivity is proven or timed out |
| inspect snapshot            | operator     | read `GET /operator/tasks/{task_id}/snapshot`                               |
| inspect trace               | operator     | read `GET /operator/tasks/{task_id}/trace`                                  |
| fetch observability file    | operator     | read task-scoped `delivery-state`, `continuity-state`, `watchdog-state`, or `provider-events` refs; accepted-boundary waiting remains controller-derived rather than a special raw delivery-state enum |
| record checkpoint           | callback     | persist checkpoint truth and optional produced/transient refs               |
| accept boundary             | callback     | close the current dispatch with `yield`, `green`, `retry`, or `blocked`; any child or replacement dispatch still waits for the prior dispatch to be proven inactive |
| call parent/root tool       | callback     | stage child work, mutate subtree structure, or mark release preconditions   |

## `CurrentMutationTimingRule`

- runtime and callback write routes commit controller-owned rows and any needed
  durable `runtime_effects` rows before returning
- materialized file surfaces are after-return projections, not synchronous
  route prerequisites
- operator and observability GET routes do not recreate deleted projection
  files inline

## `CurrentOperatorNegativeRule`

Operator is not:

- the callback caller by default
- the worker
- the controller
- the provider
- a browser bootstrap client

## Evidence

- inspected code in `apps/api/app/api/router.py`
- inspected code in `apps/api/app/api/routes/runtime.py`
- inspected code in `apps/api/app/api/routes/operator.py`
- inspected code in `apps/api/app/api/routes/callback.py`
- inspected code in `apps/api/app/api/routes/observability.py`
- inspected code in `apps/api/app/api/deps.py`
- inspected code in `apps/api/app/runtime/control/flows.py`
- inspected code in `apps/api/app/runtime/control/callbacks.py`
- inspected code in `apps/api/app/runtime/control/observability.py`
- inspected code in `apps/api/app/runtime/effects/worker.py`
- inspected tests in `apps/api/tests/integration/test_phase3_runtime_routes.py`
- inspected tests in `apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
