# MCP Tool Reference

Status: Target

Path note: this file path is retained for older plugin-routing links. The live surface model is MCP-based.

The canonical runtime term is `tool`. AutoClaw has exactly two canonical MCP tool surfaces:

1. `operator MCP`
2. `node MCP`

`plugin` and `bundle` remain packaging or parity-wrapper terminology only.

For the front-door boundary and CLI split, start with [MCP, plugin, and CLI boundary](mcp-plugin-and-cli-boundary.md).

One shared controller-owned internal definition service backs the Phase 5A
definition/task-start tools on `operator MCP` and the separate current-only
role/policy lookup path behind explicit v1 structural edits on `node MCP`.

## Product shape

The canonical MCP split is:

1. `operator MCP`
2. `node MCP`

Rules:

- `operator MCP` is the standard external parity surface
- `node MCP` is private, internal, and explicit-arg in v1
- no canonical shared MCP catalog or session may mix those two surfaces
- operator identity is not canonical runtime DB truth
- if task-scoped observability reads are exposed as tools, they belong to `operator MCP`, not to a third canonical MCP surface
- full external parity is phased:
  - Phase 4B lands the runtime, operator, and support subset only
  - Phase 5A extends that same `operator MCP` surface with definition-registry and task-start tools

## Quick boundary examples

- Need to start a task from one local file: `operator MCP`.
- Need to read a task runtime snapshot or trace: `operator MCP`.
- Need to call `assign_child` for a currently dispatched parent or root node:
  `node MCP` only.
- Need definition revision history for audit or provenance: `operator MCP` only.
- Need task-scoped watchdog inspection after a stalled runtime:
  `operator MCP` only when the wrapper intentionally exposes the observability read.
- Need a definition upload: `operator MCP`, not `node MCP`.

When OpenClaw is the worker transport:

- canonical controlled execution should use Gateway WS RPC machine surfaces such as `agent`, `agent.wait`, and `sessions.abort`
- HTTP `POST /v1/responses` remains compatibility/fallback transport only

## Operator-safe external lane

This lane is the canonical `operator MCP` surface.

## Operator MCP Phase 4B subset

`operator MCP` uses external `streamable-http`. In Phase 4B it mirrors only the runtime/operator/support lanes that already exist before Phase 5A public ingest/task-start closure.

| MCP tool                                                                                    | Contract                                                                      | Result                              |
| ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------- |
| `list_runtime_tasks(query?, limit?, cursor?, sort?, status?)`                               | filtered task runtime summary read                                            | `RuntimeFlowSummaryListResponse`    |
| `get_runtime_task(task_id)`                                                                 | current task runtime read                                                     | `RuntimeFlowRead`                   |
| `get_operator_snapshot(task_id)`                                                            | current task runtime summary                                                  | `OperatorFlowSnapshotResponse`      |
| `get_operator_trace(task_id, scope?, query?, limit?, cursor?, sort?)`                       | timeline and trace read                                                       | `OperatorFlowTraceResponse`         |
| `pause_task(task_id, expected_active_flow_revision_id)`                                     | task-scoped pause                                                             | `RuntimeFlowPauseResponse`          |
| `continue_task(task_id, expected_active_flow_revision_id)`                                  | task-scoped continue                                                          | `RuntimeFlowRead`                   |
| `cancel_task(task_id, expected_active_flow_revision_id)`                                    | task-scoped cancel                                                            | `RuntimeFlowRead`                   |

`operator MCP` rules:

- external control remains task-scoped
- there is no standard public node-level steering tool
- `operator MCP` must not widen into dispatch-bound runtime mutation
- when one OpenClaw package carries both MCP surfaces, operator-facing profiles or sessions must show only this inventory through `tools.effective` or an equivalent runtime inventory read
- prefer `tools.profile="minimal"` plus exact `tools.allow` entries for this inventory instead of broad profile inheritance

Worked example:

```text
pause_task("task_2026_0042", "flowrev_0007")
-> RuntimeFlowPauseResponse { flow: ... }
```

## Operator MCP Phase 5A extensions

Phase 5A adds the public ingest/start parity tools to this same `operator MCP` surface:

| MCP tool                                                                                    | Contract                                                                      | Result                              |
| ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------- |
| `search_definitions(kind, query?, limit?, cursor?, sort?, allowed_node_kind?, applies_to?)` | filtered discovery over `role`, `policy`, or `workflow` definitions           | `DefinitionSummaryListResponse`     |
| `get_definition(kind, key)`                                                                 | current definition detail                                                     | `DefinitionRevisionDetailResponse`  |
| `list_definition_versions(kind, key, limit?, cursor?, sort?)`                               | definition revision-history read for operator/audit/provenance use            | `DefinitionRevisionHistoryResponse` |
| `upload_definition(definition_path)`                                                        | local file path loaded as one canonical definition file with top-level `kind` | `DefinitionRevisionDetailResponse`  |
| `start_task(task_compose_path)`                                                             | local file path loaded as one `TaskStartRequest`                              | `TaskStartResponse`                 |

Phase 5A extension rules:

- file-path tools load one local file and submit the exact canonical body
- these tools are the operator/public search/get/history/upload/start surface over the shared internal definition service
- they reuse the same service as the HTTP and CLI surfaces rather than inventing plugin-owned registry logic
- `list_definition_versions(...)` remains operator/audit/provenance read only and is not part of the normal live parent/root node surface
- guarded definition writes use DB-serialized append-only revision semantics
- exact parameter names, defaults, enum values, and HTTP query-name mapping live in [api-machine-catalog.yaml](api-machine-catalog.yaml)
- Phase 4B implementations must stop and route forward if they need these tools before the Phase 5A public noun family lands

### Optional task-scoped observability reads

If task-scoped observability reads are surfaced as tools, they stay on `operator MCP`.

They remain operator/support reads and do not create a third canonical MCP surface.

The frozen Phase 4B support-state readback family is `delivery-state.json`,
`continuity-state.json`, `watchdog-state.json`, and
`provider-events.ndjson`, surfaced through the corresponding
`delivery_state_ref`, `continuity_state_ref`, `watchdog_state_ref`, and
`provider_events_ref` carriers only.

## Node MCP

`node MCP` is the static v1 node-tool surface. Server-side runtime truth resolves the current execution context from explicit `session_key` and `task_id`.

| MCP tool                               | Canonical runtime operation                    | Result              |
| -------------------------------------- | ---------------------------------------------- | ------------------- |
| `search_definitions(session_key, task_id, kind, query?, limit?, cursor?, sort?, allowed_node_kind?, applies_to?)` | current-only `role` / `policy` discovery on one live structural-edit lane | `DefinitionSummaryListResponse` |
| `get_definition(session_key, task_id, kind, key)` | current-only `role` / `policy` detail on one live structural-edit lane | `DefinitionRevisionDetailResponse` |
| `record_checkpoint(session_key, task_id, checkpoint)` | semantic checkpoint handoff write | `CheckpointRead` |
| `return_boundary(session_key, task_id, boundary)` | `yield`, `green`, `retry`, or `blocked` return | `BoundaryRead` |
| `call_parent_tool(session_key, task_id, tool_name, payload, expected_structural_revision_id?)` | parent/root control tool call | `ParentToolSuccess` |

Rules:

- `tool_name` is limited to:
  - `assign_child`
  - `add_child`
  - `update_child`
  - `remove_child`
  - `release_green`
  - `release_blocked`
- caller supplies `session_key` and `task_id` explicitly on every node tool call
- `session_key` is the primary authority input
- `task_id` is also required and must match controller truth for that `session_key`
- canonical node-facing MCP calls do not require caller-visible `dispatch_id` or `attempt_id`
- `record_checkpoint` writes the semantic handoff body plus any explicit `transient_refs`; runtime-managed checkpoint refs and surfaced durable rereads come back through read projections
- callback request and response payloads do not expose `manifest_id`, `manifest_hash`, `node_session_key`, or `ack_checkpoint_id`
- `ParentToolSuccess` is the tagged union `AssignChildSuccess | ParentToolMutationSuccess`
- `assign_child` success returns committed child assignment/attempt lineage and optional `child_assignment_ref`; it does not expose a child `dispatch_id`
- `BoundaryRead` returns `accepted_boundary`, `flow`, and optional `latest_checkpoint_ref`
- a fresh attempt may legitimately reread with `latest_checkpoint_ref: null`
- callback success carriers do not include `suggested_next_step`
- path-only surfaced refs remain canonical in returned read surfaces
- `search_definitions` and `get_definition` on `node MCP` are the only legal definition lookup tools on that surface, and they are current-only `role` / `policy` reads available on the shipped node surface
- `node MCP` must not expose `list_definition_versions`, `upload_definition`, or `start_task`
- when structural tools submit role/policy names, runtime resolves them through the same current-only lookup path and pins exact current revisions at commit time
- live parent/root planning should use surfaced current structural-edit choices first, then the current-only lookup lane when needed, rather than generic registry browsing or revision-history reads
- operator-safe automation must not be given this lane by default
- static node MCP config is stable in v1; the live `session_key` and `task_id` come from dispatch-local prompt state rather than hidden headers or plugin injection
- prefer `tools.profile="minimal"` plus exact `tools.allow` entries for this inventory instead of broad profile inheritance

Worked sequence:

```text
call_parent_tool(session_key, task_id, "assign_child", payload)
-> AssignChildSuccess { target_assignment_key: ..., target_attempt_id: ..., child_assignment_ref: ..., workflow_manifest_ref: ... }

return_boundary(session_key, task_id, "yield")
-> BoundaryRead { accepted_boundary: "yield", flow: ... }
```

This sequence is legal only when `session_key` and `task_id` resolve to the current live node execution context. It is not part of `operator MCP`.

In the filesystem-first v1 model, worker reread comes from surfaced manifest/assignment/checkpoint/ref paths in prompt and generated files rather than from a callback read helper.

## MCP, tool, and packaging rule

Use these terms exactly:

- `tool`: canonical semantic action such as `assign_child` or `record_checkpoint`
- `MCP surface`: one exposed tool inventory with one trust boundary
- `plugin` or `bundle`: one OpenClaw package or parity wrapper that may carry one or both MCP surfaces without collapsing them

Packaging or wrapper language must not rename the core runtime model into a plugin-owned truth model.

It also must not blur these two questions:

- "What may an external operator-safe automation client do?"
- "What may a currently dispatched node do inside one open dispatch?"

Those are different trust boundaries even when one package happens to carry both surfaces.

## Removed from the live tool-surface model

Do not keep these as the live surface model:

- one shared MCP catalog or session that mixes `operator MCP` and `node MCP`
- broad inherited tool profiles standing in for exact MCP-surface allowlists
- config-only bootstrap “success” without live runtime tool-inventory proof
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
- [OpenClaw Gateway RPC subset](../architecture/openclaw-gateway-rpc-subset.md)
- [Runtime boundary and controller loop contract](../architecture/runtime-boundary-and-controller-loop-contract.md)
