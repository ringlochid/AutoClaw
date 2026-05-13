# Human and operator control surface

Status: Target

This page defines the frozen v1 human and operator control surface.

The core trust split is:

- human/operator surfaces are external
- AutoClaw has exactly two canonical MCP tool surfaces: `operator MCP` and
  `node MCP`
- `operator MCP` is external, operator-safe, and task-scoped
- `node MCP` is private, internal, and dispatch-bound
- `operator MCP` is canonically external `streamable-http`
- `node MCP` is canonically private internal HTTP/`streamable-http`
- bound node/runtime surfaces use callback semantics over private internal
  HTTP/`streamable-http`
- task-scoped observability reads stay operator-safe and, if surfaced as
  tools, attach to `operator MCP`
- no canonical shared MCP catalog or session may mix operator-safe tools and
  dispatch-bound node tools
- operator identity is external authority only; it is not canonical runtime DB
  truth

## Standard external surfaces

The frozen v1 external control surface has three layers:

1. root CLI for local install, onboarding, DB work, local checks, and path-based task start
2. public operator API for snapshot, trace, task-scoped control, and guarded registry writes
3. trusted external operator MCP for automation

Browser or UI console is not part of the frozen v1 contract.

## Quick trust-boundary examples

Use these concrete examples to keep the lanes separate:

- An operator wants to pause a running task runtime: use the public operator
  API or `operator MCP`.
- A parent node wants to stage `assign_child` during an open dispatch: use
  `node MCP` only.
- A worker wants to publish a terminal checkpoint and then close with `retry`:
  use `node MCP` only.
- A support engineer wants raw provider delivery traces for incident review:
  use the task-scoped observability lane through operator-safe reads, not
  `node MCP`.

## Surface responsibilities

### Root CLI

The frozen root CLI owns:

- local install and onboarding flows
- local DB migration flows
- local definition import flows
- local health and configuration checks
- path-based task-compose start

Phase 4 freezes the CLI boundary only. Phase 5 owns the detailed
lifecycle/style contract and should keep the CLI aligned with OpenClaw's CLI
posture.

Dispatch-bound runtime mutation is not a first-class root CLI family.
Definition-import commands are a local authoring front door over the guarded
registry lifecycle, not a second runtime-truth authority model.

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

Authenticated operator identity gates caller authority on these surfaces. It
does not become canonical runtime DB truth.

### Trusted external operator MCP

`operator MCP` mirrors the operator-safe external lanes only:

- definition registry reads and guarded writes
- task start
- task runtime reads
- task pause, continue, and cancel
- operator snapshot and trace

If task-scoped observability reads are exposed as tools, they also stay on
`operator MCP`.

`operator MCP` is:

- an automation-facing parity adapter
- external to the runtime controller/node trust lane
- not a second truth owner
- required to stay separate from `node MCP` in runtime-effective tool
  inventories such as `tools.effective`

`operator MCP` is not:

- `node MCP`
- a controller/node bridge
- a license to expose parent/root tool calls as ordinary operator actions

Concrete examples:

- legal MCP call: `start_task("C:/tasks/bugfix/task-compose.yaml")`
- legal MCP read: `get_operator_snapshot(task_id)`
- not legal as part of `operator MCP`: `call_parent_tool("assign_child", ...)`

### Private node MCP and callback lane

`node MCP` is the private dispatch-bound tool surface for controller or bound
node integration.

It may expose:

- semantic checkpoint handoff writes
- dispatch boundary return
- dispatch-local parent/root tool calls

`node MCP` is:

- controller/node-facing only
- not `operator MCP`
- not the canonical human/operator control surface
- not a public trust-lane widening

Concrete examples:

- `record_checkpoint(checkpoint)`
- `return_boundary(yield)`
- `call_parent_tool(assign_child, payload)`

This lane is canonically carried over private internal HTTP/`streamable-http`
and documented through the internal binding example
`/callback/tasks/{task_id}/...`. Canonical node-facing semantics do not
require caller-visible `dispatch_id`.

In the filesystem-first v1 model, the current node rereads surfaced files
directly and does not rely on a canonical callback read helper.

## Task-scoped observability reads

Implementation may retain deeper observability or debug helpers only when
needed for runtime correctness or incident investigation.

Those reads are not:

- the standard operator role
- `node MCP`
- a reason to weaken the public API boundaries

There is no third canonical observability MCP.

If public or operator observability routes are documented, they should be
task-scoped such as `/observability/tasks/{task_id}/...`. If they are surfaced
as tools, they attach to `operator MCP`.

If retained, watchdog inspection belongs here, not on `node MCP`. Watchdog
recovery itself remains internal controller behavior.

## Task-compose entry model

The canonical task-compose entry model is split by surface:

- HTTP operators submit `TaskStartRequest` directly to `POST /tasks/start`
- CLI reads one local task-compose file and submits the resulting body
- `operator MCP` reads one local task-compose file and submits the resulting
  body

Each surface reaches the same task-start contract, but they do not gain the same runtime authority after launch. Task-start parity does not imply dispatch-local steering parity.

## Trust-boundary rule

Use these terms exactly:

- `tool`: canonical runtime action such as `assign_child`,
  `record_checkpoint`, or `release_green`
- `MCP surface`: one exposed tool inventory with one trust boundary
- `plugin` or `bundle`: OpenClaw packaging or parity-wrapper terminology only

`operator MCP` may mirror operator-safe external routes. It must not silently
absorb `node MCP`.

## Related contracts

- [MCP, plugin, and CLI boundary](mcp-plugin-and-cli-boundary.md)
- [Operator definition and role boundary](operator-definition-and-role-boundary.md)
- [MCP tool reference](plugin-tool-reference.md)
- [API surface and trust-lane map](api-surface-and-trust-lane-map.md)
- [CLI surface and operator workflows](cli-surface-and-operator-workflows.md)
- [OpenClaw Gateway RPC subset](../architecture/openclaw-gateway-rpc-subset.md)
- [Runtime boundary and controller loop contract](../architecture/runtime-boundary-and-controller-loop-contract.md)
