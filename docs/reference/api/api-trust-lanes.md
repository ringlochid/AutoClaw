# operator roles and API trust lanes

Status: Reference

Last verified: 2026-05-21

This page owns the exact current operator definition, trust-lane split, and the difference between operator, callback caller, node-tool caller, worker, parent/root, and controller in the shipped tree.

For the exact current path families and route nouns, see `api-surface-and-route-map.md`.

## `CurrentOperatorDefinitionContract`

In the current system, `operator` means a trusted principal allowed to inspect, mutate, or launch trusted runtime and definition-service work through the API-key-protected HTTP surfaces.

An operator may be:

- a human using HTTP or future UI clients with the configured API key
- a trusted automation client authenticated into the API-key-protected HTTP surfaces

Operator is defined by authority and allowed actions, not by embodiment alone.

## `CurrentUserVsOperatorContract`

- `user` supplies task intent, task root, or surrounding product inputs
- `operator` starts tasks, manages definition-service HTTP surfaces, inspects runtime state, or steers live runtime control through API-key-protected HTTP routes

The same human may play both roles, but the authority is different.

## `RoleBoundaryMatrix`

| Role         | Current meaning                                         | Owns                                                                                       | Does not own                                       |
| ------------ | ------------------------------------------------------- | ------------------------------------------------------------------------------------------ | -------------------------------------------------- |
| `operator`   | trusted runtime-steering principal                      | `/definitions`, `/tasks/start`, `/runtime`, `/operator`, and `/observability` HTTP actions | callback or node write authority, controller truth |
| `worker`     | current worker-node caller                              | checkpoint and boundary writes for the bound dispatch                                      | operator reads, parent/root tools                  |
| `parent`     | current parent-node caller                              | parent/root tool calls and parent/root boundary decisions                                  | operator reads, controller truth                   |
| `root`       | current root-node caller                                | root-only `release_blocked` and root closure decisions                                     | operator reads, delegated worker execution         |
| `controller` | runtime truth owner                                     | DB rows, dispatch and session bindings, legality checks, materialization                   | delegated execution content                        |
| `provider`   | continuity and provider-event concept only in this tree | transport-state and provider-event projections                                             | API-lane authority or controller truth             |

`worker` is never `operator`.

`parent` or `root` on the callback or node-tool lane is still not `operator`.

## `OperatorLaneMatrix`

| Lane               | Typical caller                       | Current capability level                                                                                                          | Notes                                                                   |
| ------------------ | ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| health lane        | any caller                           | `/healthz`, `/readyz`                                                                                                             | unauthenticated                                                         |
| operator HTTP lane | operator                             | definition discovery and upload, task start, runtime list/read, continue, pause, cancel, snapshot, trace, observability file refs | protected by `X-AutoClaw-API-Key`                                       |
| callback HTTP lane | bound worker, parent, or root caller | checkpoint writes, boundary acceptance, parent/root tools                                                                         | explicit `session_key` query parameter + route `task_id`                |
| node MCP mount     | bound worker, parent, or root caller | current-only definition reads plus checkpoint, boundary, and parent/root tools                                                    | explicit `session_key` + `task_id`, mounted at `/node/mcp` when enabled |
| internal-key gap   | none on the shipped HTTP router      | none                                                                                                                              | `require_internal_api_key()` exists but is unused                       |

Lane and role are not identical in the current system.

The callback and node-tool lanes are scoped to one live dispatch. They are not general trusted operator lanes.

## Current trust lanes

### 1. Operator HTTP lane

Protected by `X-AutoClaw-API-Key` via `require_api_key`.

Current grouped surfaces:

- `/definitions/*`
- `/tasks/start`
- `/runtime/*`
- `/operator/*`
- `/observability/*`

Current operator actions on this lane include:

- list, inspect, or upload definitions
- start a task from the definition service
- list or inspect runtime tasks
- continue, pause, or cancel a task runtime
- read operator snapshot and trace views
- fetch task-scoped observability file refs

Current operator GET routes are read-only in the shipped tree: they surface current file refs but do not repair or rematerialize projections inline. `POST /definitions` and `POST /tasks/start` are trusted API-key write paths on the same lane.

### 2. Callback HTTP lane

Current live authority is explicit `session_key` plus route `task_id`.

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
- controller-side validation resolves structural role and policy refs from current registry rows during validation; the callback lane does not expose a separate registry-read HTTP surface

This lane is explicitly non-operator. It is scoped to the currently live dispatch and becomes invalid when the dispatch is paused, cancelled, fenced, replaced, or otherwise no longer current.

The current implementation validates that the presented session key still matches live `NodeSession`, the live dispatch, and the persisted current assignment and attempt basis for that task before a callback write can commit. The callback route requires explicit `session_key` request input.

Most callback writes now return only after controller truth commits and the owned task-root file surfaces are refreshed synchronously. That includes manifest, attempt, dispatch, artifact-pointer, and observability projections for the cases that teach or return those refs.

Structural callback tools are stricter. `add_child`, `update_child`, and `remove_child` stage stable-manifest rewrites for the selected task. `commit_runtime_session()` commits controller truth first and then applies the owned `_runtime/workflow-manifest.*` writes synchronously before route success, so tool success still means the taught reread path is already refreshed. If the commit fails, `rollback_runtime_session()` clears the staged writes and preserves the last committed stable manifest.

### 3. Node MCP mount

Mounted under `/node/mcp` when MCP mounts are enabled.

Current grouped tools are:

- `search_definitions`
- `get_definition`
- `record_checkpoint`
- `return_boundary`
- `assign_child`
- `add_child`
- `update_child`
- `remove_child`
- `release_green`
- `release_blocked`

Current lane rules:

- every tool call must carry explicit `session_key` and `task_id`
- the same shared authority validator used by callback HTTP resolves that session against live `NodeSession` and current dispatch truth
- this lane is not the operator lane and does not inherit operator API-key authority
- this lane keeps node-only tool inventory separate from operator MCP inventory
- current shipped node-MCP wrapper now preserves the strict typed request and result shapes:
  - `assign_child`, `add_child`, `update_child`, and `remove_child` each take their own typed `payload` body, while `release_green` and `release_blocked` use only `expected_structural_revision_id?`
  - node-operation success surfaces typed `CheckpointRead`, `BoundaryRead`, `AssignChildSuccess`, `AddChildSuccess`, `UpdateChildSuccess`, `RemoveChildSuccess`, `ReleaseGreenSuccess`, and `ReleaseBlockedSuccess` bodies

### 4. Health lane

Unauthenticated:

- `GET /healthz`
- `GET /readyz`

### 5. No current browser bootstrap or legacy internal lane

Current code does not ship the older browser-bootstrap, internal, flow, approval, or legacy registry route families.

The config still carries `internal_api_key`, but no shipped HTTP router uses the internal-key dependency.

## `CurrentOperatorActionTable`

| Action                       | Current lane              | Current effect                                                                                                                                                                                                                               |
| ---------------------------- | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| list definitions             | operator HTTP             | read definition summaries by kind, filter, and page                                                                                                                                                                                          |
| inspect definition detail    | operator HTTP             | read one current definition revision                                                                                                                                                                                                         |
| inspect definition history   | operator HTTP             | read historical revisions for one definition                                                                                                                                                                                                 |
| upload definition            | operator HTTP             | create or update a definition revision                                                                                                                                                                                                       |
| start task                   | operator HTTP             | create a task from the definition service and wait for initial runtime effects                                                                                                                                                               |
| inspect runtime list         | operator HTTP             | read `GET /runtime/tasks`                                                                                                                                                                                                                    |
| inspect one task runtime     | operator HTTP             | read `GET /runtime/tasks/{task_id}`                                                                                                                                                                                                          |
| continue task runtime        | operator HTTP             | current shipped behavior: resume a paused task runtime when revision expectations match; ordinary accepted-boundary child handoff, parent wake, and retry progression now reopen internally after inactivity proof |
| pause task runtime           | operator HTTP             | mark the flow paused and keep replacement dispatch blocked until inactivity is proven or timed out                                                                                                                                           |
| cancel task runtime          | operator HTTP             | mark abort requested, close the current task flow, and keep the dispatch controller-visible until inactivity is proven or timed out                                                                                                          |
| inspect snapshot             | operator HTTP             | read `GET /operator/tasks/{task_id}/snapshot`                                                                                                                                                                                                |
| inspect trace                | operator HTTP             | read `GET /operator/tasks/{task_id}/trace`                                                                                                                                                                                                   |
| fetch observability file     | operator HTTP             | read task-scoped `delivery-state`, `continuity-state`, `watchdog-state`, or `provider-events` refs                                                                                                                                           |
| record checkpoint            | callback HTTP or node MCP | persist checkpoint truth and optional produced or transient refs                                                                                                                                                                             |
| accept boundary              | callback HTTP or node MCP | close the current dispatch with `yield`, `green`, `retry`, or `blocked`; any child or replacement dispatch still waits for the prior dispatch to be proven inactive                                                                          |
| call parent/root tool        | callback HTTP or node MCP | stage child work, mutate subtree structure, or mark release preconditions                                                                                                                                                                    |
| current-only definition read | node MCP                  | read current role or policy detail without switching to the operator HTTP lane                                                                                                                                                               |

## `CurrentMutationTimingRule`

- runtime writes, checkpoint writes, boundary writes, callback writes, node-tool writes, definition uploads, and task-start writes commit controller-owned rows first
- the same request then applies the owned task-root file writes synchronously before returning when that route family owns those projections
- launch returns only after the stable root workflow-manifest, root attempt files, and opened-dispatch projections are readable
- structural callback and node-tool writes return only after the stable manifest reread path is current
- operator and observability GET routes do not recreate deleted projection files inline

## `CurrentOperatorNegativeRule`

Operator is not:

- the callback caller by default
- the node-tool caller by default
- the worker
- the controller
- the provider
- a browser bootstrap client

## Evidence

- inspected code in `apps/api/src/autoclaw/interfaces/http/router.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/definitions.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/tasks.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/runtime.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/operator.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/callback.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/observability.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/dependencies.py`
- inspected code in `apps/api/src/autoclaw/interfaces/mcp/node/server.py`
- inspected code in `apps/api/src/autoclaw/runtime/dispatch/authority.py`
- inspected code in `apps/api/src/autoclaw/runtime/flow/service.py`
- inspected code in `apps/api/src/autoclaw/runtime/observability/__init__.py`
- inspected code in `apps/api/src/autoclaw/runtime/post_commit/cases.py`
- inspected code in `apps/api/src/autoclaw/runtime/post_commit/worker.py`
- inspected code in `apps/api/src/autoclaw/runtime/launch/service.py`
- inspected tests in `apps/api/tests/integration/phase3/contracts/test_session_authority_and_pause_cases.py`
- inspected tests in `apps/api/tests/integration/phase3/contracts/test_assignment_cases.py`
- inspected tests in `apps/api/tests/integration/phase3/contracts/test_structural_manifest_cases.py`
- inspected tests in `apps/api/tests/integration/phase3/routes/test_surface_contract.py`
- inspected tests in `apps/api/tests/integration/phase4b/mcp/node_server`
- inspected tests in `apps/api/tests/integration/phase5a/test_public_http_subset.py`
