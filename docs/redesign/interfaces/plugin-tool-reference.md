# MCP Tool Reference

Status: Target

Path note: this file path is retained for older plugin-routing links. The live
surface model is MCP-based.

The canonical runtime term is `tool`. AutoClaw has exactly two canonical MCP
tool surfaces:

1. `operator MCP`
2. `node MCP`

`plugin` and `bundle` remain packaging or parity-wrapper terminology only.

For the front-door boundary and CLI split, start with
[MCP, plugin, and CLI boundary](mcp-plugin-and-cli-boundary.md).

## Product shape

The canonical MCP split is:

1. `operator MCP`
2. `node MCP`

Rules:

- `operator MCP` is the standard external parity surface
- `node MCP` is private, internal, and dispatch-bound
- no canonical shared MCP catalog or session may mix those two surfaces
- operator identity is not canonical runtime DB truth
- if task-scoped observability reads are exposed as tools, they belong to
  `operator MCP`, not to a third canonical MCP surface

## Quick boundary examples

- Need to start a task from one local file: `operator MCP`.
- Need to read a task runtime snapshot or trace: `operator MCP`.
- Need to call `assign_child` for a currently dispatched parent or root node:
  `node MCP` only.
- Need task-scoped watchdog inspection after a stalled runtime:
  `operator MCP` only when the wrapper intentionally exposes the
  observability read.
- Need a definition upload: `operator MCP`, not `node MCP`.

When OpenClaw is the worker transport:

- canonical controlled execution should use Gateway WS RPC machine surfaces such as `agent`, `agent.wait`, and `sessions.abort`
- HTTP `POST /v1/responses` remains compatibility/fallback transport only

## Operator-safe external lane

This lane is the canonical `operator MCP` surface.

## Operator MCP

`operator MCP` mirrors the external operator-safe lanes. If it rides HTTP, it
maps to `/definitions/...`, `/tasks/start`, `/runtime/...`, and
`/operator/...`.

| MCP tool | Contract | Result |
| --- | --- | --- |
| `search_definitions(kind, query?, limit?, cursor?, sort?, allowed_node_kind?, applies_to?)` | filtered discovery over `role`, `policy`, or `workflow` definitions | `DefinitionSummaryListResponse`     |
| `get_definition(kind, key)`                                                                             | current definition detail                                            | `DefinitionRevisionDetailResponse`  |
| `list_definition_versions(kind, key, limit?, cursor?, sort?)`                                          | definition revision-history read for operator/audit/provenance use   | `DefinitionRevisionHistoryResponse` |
| `upload_definition(definition_path)`                                  | local file path loaded as one canonical definition file with top-level `kind` | `DefinitionRevisionDetailResponse` |
| `start_task(task_compose_path)`                                       | local file path loaded as one `TaskStartRequest`        | `TaskStartResponse`              |
| `list_runtime_tasks(query?, limit?, cursor?, sort?, status?)`         | filtered task runtime summary read                      | `RuntimeFlowSummaryListResponse` |
| `get_runtime_task(task_id)`                                           | current task runtime read                               | `RuntimeFlowRead`                |
| `get_operator_snapshot(task_id)`                                      | current task runtime summary                            | `OperatorFlowSnapshotResponse`   |
| `get_operator_trace(task_id, scope?, query?, limit?, cursor?, sort?)` | timeline and trace read                                 | `OperatorFlowTraceResponse`      |
| `pause_task(task_id, expected_active_flow_revision_id)`               | task-scoped pause                                       | `RuntimeFlowPauseResponse`       |
| `continue_task(task_id, expected_active_flow_revision_id)`            | task-scoped continue                                    | `RuntimeFlowRead`                |
| `cancel_task(task_id, expected_active_flow_revision_id)`              | task-scoped cancel                                      | `RuntimeFlowRead`                |

`operator MCP` rules:

- file-path tools load one local file and submit the exact canonical body
- guarded definition writes use DB-serialized append-only revision semantics
- exact parameter names, defaults, enum values, and HTTP query-name mapping
  live in [api-machine-catalog.yaml](api-machine-catalog.yaml)
- external control remains task-scoped
- there is no standard public node-level steering tool
- `operator MCP` must not widen into dispatch-bound runtime mutation

Worked example:

```text
start_task("C:/tasks/bugfix/task-compose.yaml")
-> TaskStartResponse { task_id: "task_2026_0042", workflow_manifest_ref: ... }

pause_task("task_2026_0042", "flowrev_0007")
-> RuntimeFlowPauseResponse { flow: ... }
```

### Optional task-scoped observability reads

If task-scoped observability reads are surfaced as tools, they stay on
`operator MCP`.

They remain operator/support reads and do not create a third canonical MCP
surface.

## Node MCP

`node MCP` is the private dispatch-bound tool surface for the currently bound
node execution context. If it rides HTTP, any shown route shape is an internal
binding example such as `/callback/tasks/{task_id}/...`.

| MCP tool | Canonical runtime operation | Result |
| --- | --- | --- |
| `record_checkpoint(checkpoint)`      | semantic checkpoint handoff write    | `CheckpointRead`      |
| `return_boundary(boundary)`          | `yield`, `green`, `retry`, or `blocked` return | `BoundaryRead` |
| `call_parent_tool(tool_name, payload)` | parent/root control tool call | `ParentToolSuccess` |

Rules:

- `tool_name` is limited to:
  - `assign_child`
  - `add_child`
  - `update_child`
  - `remove_child`
  - `release_green`
  - `release_blocked`
- caller identity is implicit from the bound node session/execution context
- canonical node-facing MCP calls do not require caller-visible `dispatch_id`
- `record_checkpoint` writes the semantic handoff body plus any explicit `transient_refs`; runtime-managed checkpoint refs and surfaced durable rereads come back through read projections
- callback request and response payloads do not expose `manifest_id`, `manifest_hash`, `node_session_key`, or `ack_checkpoint_id`
- `ParentToolSuccess` is the tagged union `AssignChildSuccess | ParentToolMutationSuccess`
- `assign_child` success returns committed child assignment/attempt lineage and optional `child_assignment_ref`; it does not expose a child `dispatch_id`
- `BoundaryRead` returns `accepted_boundary`, `flow`, and optional `latest_checkpoint_ref`
- a fresh attempt may legitimately reread with `latest_checkpoint_ref: null`
- callback success carriers do not include `suggested_next_step`
- path-only surfaced refs remain canonical in returned read surfaces
- operator-safe automation must not be given this lane by default

Worked sequence:

```text
call_parent_tool("assign_child", payload)
-> AssignChildSuccess { target_assignment_key: ..., target_attempt_id: ..., child_assignment_ref: ..., workflow_manifest_ref: ... }

return_boundary("yield")
-> BoundaryRead { accepted_boundary: "yield", flow: ... }
```

This sequence is legal only for the currently bound node session or execution
context. It is not part of `operator MCP`.

In the filesystem-first v1 model, worker reread comes from surfaced manifest/assignment/checkpoint/ref paths in prompt and generated files rather than from a callback read helper.

## MCP, tool, and packaging rule

Use these terms exactly:

- `tool`: canonical semantic action such as `assign_child` or `record_checkpoint`
- `MCP surface`: one exposed tool inventory with one trust boundary
- `plugin` or `bundle`: one OpenClaw package or parity wrapper that may carry
  one or both MCP surfaces without collapsing them

Packaging or wrapper language must not rename the core runtime model into a
plugin-owned truth model.

It also must not blur these two questions:

- "What may an external operator-safe automation client do?"
- "What may a currently dispatched node do inside one open dispatch?"

Those are different trust boundaries even when one package happens to carry both
surfaces.

## Removed from the live tool-surface model

Do not keep these as the live surface model:

- one shared MCP catalog or session that mixes `operator MCP` and `node MCP`
- old `/internal/runtime/...` callback naming
- old `/internal/support/...` or `/support/...` observability naming
- dispatch-keyed callback helper signatures
- `get_worker_context(binding_id)`
- `post_worker_callback(binding_id, node_attempt_id, event)`
- callback-era `progress | result | parent_decision | replan_request` event families
- `retry_child`
- `reissue_child`
- public reassignment control
- `scope_key`
- flow/scope manifest split
- plugin-first truth ownership

## Related contracts

- [MCP, plugin, and CLI boundary](mcp-plugin-and-cli-boundary.md)
- [Human and operator control surface](human-and-operator-control-surface.md)
- [Operator definition and role boundary](operator-definition-and-role-boundary.md)
- [API surface and trust-lane map](api-surface-and-trust-lane-map.md)
- [API schema appendix](api-schema-appendix.md)
- [Guarded registry and runtime writes](guarded-registry-and-runtime-writes.md)
- [Runtime boundary and controller loop contract](../architecture/runtime-boundary-and-controller-loop-contract.md)
