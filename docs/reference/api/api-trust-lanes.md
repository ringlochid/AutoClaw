# Operator roles and API trust lanes

Status: Reference

Last verified: 2026-06-28

This page owns the exact current operator authority, trust-lane split, and the difference between operator agent, human operator, callback caller, node-tool caller, worker, parent/root, and controller in the shipped tree.

For the exact current path families and route nouns, see [API route families and lane map](api-surface-and-route-map.md).

## Operator definition

In the current system, `operator` means a trusted principal allowed to inspect, mutate, or launch trusted runtime and definition-service work through operator-authorized surfaces.

The intended product shape is a trusted OpenClaw operator agent profile using operator MCP when possible. Human operators are also trusted operators, but their natural surface is the UI, which calls operator-authorized backend surfaces on their behalf.

An operator may be:

- a trusted OpenClaw operator agent profile using mounted operator MCP tools
- a human using UI clients backed by operator-authorized backend routes
- a trusted automation client authenticated into API-key-protected HTTP surfaces

Operator is defined by authority and allowed actions, not by embodiment alone. The interface still matters: operator agents use tools, humans use UI, and automation clients use APIs.

## User and operator roles

- `user` supplies task intent, task root, or surrounding product inputs
- `operator agent` starts tasks, inspects runtime state, resolves waits, and steers live runtime control through operator MCP or equivalent trusted operator tools
- `human operator` uses UI surfaces to review state, make decisions, approve or reject actions, resolve waits, and request recovery

The same human may supply user intent and later act as human operator, but the authority and surface are different.

## Role boundary matrix

| Role         | Current meaning                                         | Owns                                                                                       | Does not own                                       |
| ------------ | ------------------------------------------------------- | ------------------------------------------------------------------------------------------ | -------------------------------------------------- |
| `operator`   | trusted runtime-steering principal, preferably an OpenClaw operator agent profile | operator MCP plus `/definitions`, `/authoring`, `/tasks/start`, `/runtime`, `/operator`, `/control`, and `/observability` HTTP actions | callback or node write authority, controller truth |
| `worker`     | current worker-node caller                              | checkpoint and boundary writes for the bound dispatch                                      | operator reads, parent/root tools                  |
| `parent`     | current parent-node caller                              | parent/root tool calls and parent/root boundary decisions                                  | operator reads, controller truth                   |
| `root`       | current root-node caller                                | root-only `release_blocked` and root closure decisions                                     | operator reads, delegated worker execution         |
| `controller` | runtime truth owner                                     | DB rows, dispatch and session bindings, legality checks, materialization                   | delegated execution content                        |
| `provider`   | continuity and provider-event concept only in this tree | transport-state and provider-event projections                                             | API-lane authority or controller truth             |

`worker` is never `operator`.

`parent` or `root` on the callback or node-tool lane is still not `operator`.

## Lane boundary matrix

| Lane               | Typical caller                       | Current capability level                                                                                                          | Notes                                                                   |
| ------------------ | ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| health lane        | any caller                           | `/healthz`, `/readyz`                                                                                                             | unauthenticated                                                         |
| operator HTTP lane | operator                             | definition discovery and upload, definition authoring drafts, task start, runtime list/read, continue, pause, cancel, snapshot, trace, control events, human requests, command runs, observability file refs | protected by `X-AutoClaw-API-Key`                                       |
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
- `/authoring/*`
- `/tasks/start`
- `/runtime/*`
- `/operator/*`
- `/control/*`
- `/observability/*`

Current operator actions on this lane include:

- list, inspect, or upload definitions
- create, inspect, save, reset, re-materialize, validate, preview, apply, or delete backend-owned definition draft sets
- start a task from the definition service
- list or inspect runtime tasks
- continue, pause, or cancel a task runtime
- read operator snapshot and trace views
- read control snapshots, task events, human requests, and command runs
- request cancellation of the current active command run without cancelling the whole task
- fetch task-scoped observability file refs

Current operator GET routes are read-only in the shipped tree: they surface current file refs or current backend-owned draft state but do not repair or rematerialize projections inline. `POST /definitions`, `/authoring/definition-draft-sets/*`, and `POST /tasks/start` are trusted API-key write paths on the same lane.

Mounted operator MCP is a narrower operator surface over the same trusted principal. It exposes registry reads, definition upload, task start, runtime control/readback, support refs, and read-only draft-set discovery/detail tools. It does not expose draft-set create, delete, materialize, save, reset, re-materialize, validate, apply, or preview-task-compose tools; those remain HTTP `/authoring` workbench actions.

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
- `open_human_request`
- `start_command_run`
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
  - `open_human_request` and `start_command_run` each take their shared typed `request` body and create their external wait directly when current capability and dispatch authority allow it
  - node-operation success surfaces typed `CheckpointRead`, `BoundaryRead`, `HumanRequestOpenResponse`, `CommandRunStartResponse`, `AssignChildSuccess`, `AddChildSuccess`, `UpdateChildSuccess`, `RemoveChildSuccess`, `ReleaseGreenSuccess`, and `ReleaseBlockedSuccess` bodies

### 4. Health lane

Unauthenticated:

- `GET /healthz`
- `GET /readyz`

### 5. No current browser bootstrap or legacy internal lane

Current code does not ship the older browser-bootstrap, internal, flow, approval, or legacy registry route families.

The config still carries `internal_api_key`, but no shipped HTTP router uses the internal-key dependency.

## Operator action summary

| Action                       | Current lane              | Current effect                                                                                                                                                                                                                               |
| ---------------------------- | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| list definitions             | operator HTTP             | read definition summaries by kind, filter, and page                                                                                                                                                                                          |
| inspect definition detail    | operator HTTP             | read one current definition revision                                                                                                                                                                                                         |
| inspect definition history   | operator HTTP             | read historical revisions for one definition                                                                                                                                                                                                 |
| upload definition            | operator HTTP             | create or update a definition revision                                                                                                                                                                                                       |
| manage definition draft sets | operator HTTP             | create, inspect, save, reset, re-materialize, validate, preview, apply, or delete backend-owned draft-set state under the configured data dir                                                                                             |
| inspect definition draft sets | operator HTTP or operator MCP | list draft-set refs and inspect saved draft bodies, normalized content, and preview state without mutating local draft state                                                                                                              |
| start task                   | operator HTTP             | create a task from the definition service and wait for initial runtime effects                                                                                                                                                               |
| inspect runtime list         | operator HTTP             | read `GET /runtime/tasks`                                                                                                                                                                                                                    |
| inspect one task runtime     | operator HTTP             | read `GET /runtime/tasks/{task_id}`                                                                                                                                                                                                          |
| continue task runtime        | operator HTTP             | current shipped behavior: resume a paused task runtime when revision expectations match; ordinary accepted-boundary child handoff, parent wake, and retry progression now reopen internally after inactivity proof |
| pause task runtime           | operator HTTP             | mark the flow paused and keep replacement dispatch blocked until inactivity is proven or timed out                                                                                                                                           |
| cancel task runtime          | operator HTTP             | mark abort requested, close the current task flow, and keep the dispatch controller-visible until inactivity is proven or timed out                                                                                                          |
| inspect snapshot             | operator HTTP             | read `GET /operator/tasks/{task_id}/snapshot`                                                                                                                                                                                                |
| inspect trace                | operator HTTP             | read `GET /operator/tasks/{task_id}/trace`                                                                                                                                                                                                   |
| inspect control task events  | operator HTTP             | read `GET /control/tasks/{task_id}/events` or stream `GET /control/tasks/{task_id}/events/stream`                                                                                                                                             |
| inspect command runs         | operator HTTP             | read `GET /control/tasks/{task_id}/command-runs` for compact controller-owned command-run truth                                                                                                                                                |
| cancel current command run   | operator HTTP             | request `POST /control/tasks/{task_id}/command-runs/{run_id}/cancel`; accepted cancellation moves the run to `cancellation_requested` and leaves the task waiting for terminal command-run closure                                            |
| fetch observability file     | operator HTTP             | read task-scoped `delivery-state`, `continuity-state`, `watchdog-state`, or `provider-events` refs                                                                                                                                           |
| record checkpoint            | callback HTTP or node MCP | persist checkpoint truth and optional produced or transient refs                                                                                                                                                                             |
| accept boundary              | callback HTTP or node MCP | close the current dispatch with `yield`, `green`, `retry`, or `blocked`; any child or replacement dispatch still waits for the prior dispatch to be proven inactive                                                                          |
| start command run            | node MCP                  | persist controller-owned command-run truth, create `waiting_for_command_run`, emit `command_run_started`, and fence the current dispatch without accepting a workflow boundary                                                               |
| call parent/root tool        | callback HTTP or node MCP | stage child work, mutate subtree structure, or mark release preconditions                                                                                                                                                                    |
| current-only definition read | node MCP                  | read current role or policy detail without switching to the operator HTTP lane                                                                                                                                                               |

## Mutation timing

- runtime writes, checkpoint writes, boundary writes, callback writes, node-tool writes, definition uploads, definition draft-set apply writes, and task-start writes commit controller-owned rows first
- the same request then applies the owned task-root file writes synchronously before returning when that route family owns those projections
- launch returns only after the stable root workflow-manifest, root attempt files, and opened-dispatch projections are readable
- structural callback and node-tool writes return only after the stable manifest reread path is current
- operator and observability GET routes do not recreate deleted projection files inline

## What operator does not mean

Operator is not:

- the callback caller by default
- the node-tool caller by default
- the worker
- the controller
- the provider
- a browser bootstrap client
