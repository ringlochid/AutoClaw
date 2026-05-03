# Human and operator control surface

Status: Target

This page defines the frozen v1 human and operator control surface.

The core trust split is:

- human/operator surfaces are external
- bound node/runtime surfaces use the callback semantic lane and may bind to HTTP privately
- observability surfaces use task-scoped operator/support reads when carried over HTTP
- the standard external plugin does not widen into either the callback lane or the observability lane

## Standard external surfaces

The frozen v1 external control surface has three layers:

1. root CLI for local install, onboarding, DB work, local checks, and path-based task start
2. public operator API for snapshot, trace, task-scoped control, and guarded registry writes
3. trusted external operator plugin parity adapter for automation

Browser or UI console is not part of the frozen v1 contract.

## Quick trust-boundary examples

Use these concrete examples to keep the lanes separate:

- An operator wants to pause a running task runtime: use the public operator API or the standard external plugin parity lane.
- A parent node wants to stage `assign_child` during an open dispatch: use the internal dispatch-bound adapter lane only.
- A worker wants to publish a terminal checkpoint and then close with `retry`: use the internal dispatch-bound adapter lane only.
- A support engineer wants raw provider delivery traces for incident review: use the observability lane, not the operator snapshot lane.

## Surface responsibilities

### Root CLI

The frozen root CLI owns:

- local install and onboarding flows
- local DB migration flows
- local definition import flows
- local health and configuration checks
- path-based task-compose start

It does not freeze dispatch-bound runtime mutation as a first-class root CLI family. Definition-import commands are a local authoring front door over the guarded registry lifecycle, not a second runtime-truth authority model.

Concrete examples:

- `autoclaw definitions import --file C:/defs/review-role.yaml` is a local authoring front door over the guarded definition upload lifecycle.
- `autoclaw definitions import` is the canonical shallow current-working-directory import front door for top-level definition YAML files.
- `autoclaw task-compose start --file C:/tasks/bugfix/task-compose.yaml` loads one local file and submits the exact `TaskStartRequest` body.

### Public operator API

The public operator API owns:

- definition list and revision-history reads
- task start
- task runtime reads
- task pause, continue, and cancel
- operator snapshot and trace
- guarded definition uploads

Public operator routes are task-scoped externally. Internal flow lineage remains controller-owned.

When OpenClaw is the worker transport, the canonical machine control path for dispatch lifecycle is Gateway WS RPC (`agent`, `agent.wait`, `sessions.abort`), not HTTP OpenResponses.

Concrete examples:

- legal operator action: `POST /runtime/tasks/{task_id}/pause?expected_active_flow_revision_id=...`
- legal operator read: `GET /operator/tasks/{task_id}/snapshot`
- illegal operator shortcut: calling `assign_child` for one current parent node through a public flow route

### Trusted external operator plugin parity adapter

The standard external plugin mirrors the operator-safe external lanes only:

- definition registry reads and guarded writes
- task start
- task runtime reads
- task pause, continue, and cancel
- operator snapshot and trace

The standard external plugin is:

- an automation-facing parity adapter
- external to the runtime controller/node trust lane
- not a second truth owner

The standard external plugin is not:

- the internal dispatch-bound adapter lane
- a controller/node bridge
- a license to expose parent/root tool calls as ordinary operator actions

Concrete examples:

- legal plugin parity call: `start_task("C:/tasks/bugfix/task-compose.yaml")`
- legal plugin parity read: `get_operator_snapshot(task_id)`
- not legal as part of the standard external plugin: `call_parent_tool("assign_child", ...)`

## Internal dispatch-bound callback lane

Implementation may retain an internal dispatch-bound callback lane for controller or bound-node integration.

That lane may expose:

- semantic checkpoint handoff writes
- dispatch boundary return
- dispatch-local parent/root tool calls

That lane is:

- controller/node-facing only
- not the standard external plugin
- not the canonical human/operator control surface
- not a public trust-lane widening

Concrete examples:

- `record_checkpoint(checkpoint)`
- `return_boundary(yield)`
- `call_parent_tool(assign_child, payload)`

If carried over HTTP, this lane should be documented only as an internal adapter-binding example such as `/callback/tasks/{task_id}/...`. Canonical node-facing semantics do not require caller-visible `dispatch_id`.

In the filesystem-first v1 model, the current node rereads surfaced files directly and does not rely on a canonical callback read helper.

## Non-standard observability/debug lane

Implementation may retain deeper observability or debug helpers only when needed for runtime correctness or incident investigation.

That lane is not:

- the standard operator role
- the standard external plugin parity contract
- a reason to weaken the public API boundaries

If public/operator observability routes are documented, they should be task-scoped such as `/observability/tasks/{task_id}/...`.

If retained, watchdog inspection belongs here, not on the callback lane. Watchdog recovery itself remains internal controller behavior.

## Task-compose entry model

The canonical task-compose entry model is split by surface:

- HTTP operators submit `TaskStartRequest` directly to `POST /tasks/start`
- CLI reads one local task-compose file and submits the resulting body
- the standard external plugin reads one local task-compose file and submits the resulting body

Each surface reaches the same task-start contract, but they do not gain the same runtime authority after launch. Task-start parity does not imply dispatch-local steering parity.

## Trust-boundary rule

Use these terms exactly:

- `tool` canonical runtime action such as `assign_child`, `record_checkpoint`, or `release_green`
- `plugin` one adapter-specific automation surface

The standard external plugin may mirror operator-safe external routes. It must not silently absorb the dispatch-bound internal runtime adapter lane.

## Related contracts

- [Operator definition and role boundary](operator-definition-and-role-boundary.md)
- [Plugin tool reference](plugin-tool-reference.md)
- [API surface and trust-lane map](api-surface-and-trust-lane-map.md)
- [CLI surface and operator workflows](cli-surface-and-operator-workflows.md)
- [Runtime boundary and controller loop contract](../architecture/runtime-boundary-and-controller-loop-contract.md)
