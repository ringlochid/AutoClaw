# Plugin Tool Reference

Status: Target

This page defines the frozen v1 adapter-specific plugin-facing tool families.

The canonical runtime term is `tool`. `plugin` is adapter-specific only and means one concrete automation-facing surface that exposes canonical reads or tools.

## Product shape

The standard external plugin keeps two canonical lanes only:

1. definition registry lane
2. operator-safe external lane

If an implementation also keeps internal bound-node semantic actions or support recovery lanes, those may bind privately to `/callback` and `/observability` transport families. They stay separate, non-standard, and outside the standard external plugin contract.

## Quick plugin-boundary examples

- Need to start a task from one local file: standard external plugin lane.
- Need to read a task runtime snapshot or trace: standard external plugin lane.
- Need to call `assign_child` for a currently dispatched parent/root node: internal `/callback` lane only.
- Need watchdog inspection after a stalled task runtime: optional `/observability` lane only.
- Need a definition upload: standard external plugin registry lane, not the internal runtime lane.

When OpenClaw is the worker transport:

- canonical controlled execution should use Gateway WS RPC machine surfaces such as `agent`, `agent.wait`, and `sessions.abort`
- HTTP `POST /v1/responses` remains compatibility/fallback transport only

## Definition registry lane

This lane mirrors the canonical guarded definition reads and writes. If it is carried over HTTP, it maps to `/definitions/...`.

| Plugin tool                                                                                              | Contract                                                             | Result                              |
| -------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- | ----------------------------------- |
| `search_definitions(kind, query?, limit?, cursor?, sort?, allowed_node_kind?, applies_to?)` | filtered discovery over `role`, `policy`, or `workflow` definitions | `DefinitionSummaryListResponse`     |
| `get_definition(kind, key)`                                                                             | current definition detail                                            | `DefinitionRevisionDetailResponse`  |
| `list_definition_versions(kind, key, limit?, cursor?, sort?)`                                          | definition revision-history read for operator/audit/provenance use   | `DefinitionRevisionHistoryResponse` |
| `upload_definition(definition_path)`                                                                     | local file path loaded as one canonical definition file with top-level `kind`          | `DefinitionRevisionDetailResponse`  |

Rules:

- file-path tools load one local file, validate top-level `kind`, and submit the exact canonical body through the guarded registry lifecycle
- guarded definition writes use DB-serialized append-only revision semantics
- the plugin must reject malformed or kind-mismatched input rather than pretending to succeed
- exact parameter names, defaults, enum values, and HTTP query-name mapping live in [api-machine-catalog.yaml](api-machine-catalog.yaml)
- standard parent/root planning parity uses `search_definitions(...)` plus `get_definition(...)`
- `list_definition_versions(...)` is not a normal parent/root planning primitive; it exists for operator, audit, provenance, or trusted-automation investigation

Worked example:

```text
upload_definition("C:/defs/workflow/retry-review.yaml")
-> DefinitionRevisionDetailResponse { revision_no: 8, ... }
```

## Operator-safe external lane

This lane mirrors the canonical operator-safe read and control surfaces. If it is carried over HTTP, it maps to `/tasks/start`, `/runtime/tasks/...`, and `/operator/tasks/...`.

| Plugin tool                                                           | Contract                                                | Result                           |
| --------------------------------------------------------------------- | ------------------------------------------------------- | -------------------------------- |
| `start_task(task_compose_path)`                                       | local file path loaded as one `TaskStartRequest`        | `TaskStartResponse`              |
| `list_runtime_tasks(query?, limit?, cursor?, sort?, status?)`         | filtered task runtime summary read                      | `RuntimeFlowSummaryListResponse` |
| `get_runtime_task(task_id)`                                           | current task runtime read                               | `RuntimeFlowRead`                |
| `get_operator_snapshot(task_id)`                                      | current task runtime summary                            | `OperatorFlowSnapshotResponse`   |
| `get_operator_trace(task_id, scope?, query?, limit?, cursor?, sort?)` | timeline and trace read                                 | `OperatorFlowTraceResponse`      |
| `pause_task(task_id, expected_active_flow_revision_id)`               | task-scoped pause                                       | `RuntimeFlowPauseResponse`       |
| `continue_task(task_id, expected_active_flow_revision_id)`            | task-scoped continue                                    | `RuntimeFlowRead`                |
| `cancel_task(task_id, expected_active_flow_revision_id)`              | task-scoped cancel                                      | `RuntimeFlowRead`                |

Operator-safe rules:

- public operator/plugin control is task-scoped externally
- there is no standard public node-level steering tool
- the standard external plugin must not silently widen an operator-safe external tool into an observability/debug helper or dispatch-bound runtime mutation

Worked example:

```text
start_task("C:/tasks/bugfix/task-compose.yaml")
-> TaskStartResponse { task_id: "task_2026_0042", workflow_manifest_ref: ... }

pause_task("task_2026_0042", "flowrev_0007")
-> RuntimeFlowPauseResponse { flow: ... }
```

## Optional internal bound-node callback lane

Some implementations may also expose a separate internal adapter lane for controller/node integration.

That lane is not the standard external plugin. It is a controller/node-facing bridge only. If it is carried over HTTP, any shown route shape is an internal adapter-binding example such as `/callback/tasks/{task_id}/...`, not a canonical public semantic contract.

If present, it may expose canonical runtime operations through plugin transport:

| Internal adapter tool                | Canonical runtime operation          | Result                |
| ------------------------------------ | ------------------------------------ | --------------------- |
| `record_checkpoint(checkpoint)`      | semantic checkpoint handoff write    | `CheckpointRead`      |
| `return_boundary(boundary)`          | `yield`, `green`, `retry`, or `blocked` return | `BoundaryRead`        |
| `call_parent_tool(tool_name, payload)` | parent/root control tool call      | `ParentToolSuccess`   |

Rules:

- `tool_name` is limited to:
  - `assign_child`
  - `add_child`
  - `update_child`
  - `remove_child`
  - `release_green`
  - `release_blocked`
- caller identity is implicit from the bound node session/execution context
- canonical node-facing plugin calls do not require caller-visible `dispatch_id`
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

This sequence is legal only for the currently bound node session/execution context. It is not part of the standard external plugin parity contract.

In the filesystem-first v1 model, worker reread comes from surfaced manifest/assignment/checkpoint/ref paths in prompt and generated files rather than from a callback read helper.

## Tool versus plugin rule

Use these terms exactly:

- `tool` canonical semantic action such as `assign_child` or `record_checkpoint`
- `plugin` one concrete adapter that exposes those actions or reads

The plugin must not rename the core runtime model into a plugin-owned truth model.

It also must not blur these two questions:

- "What may an external operator-safe automation client do?"
- "What may a currently dispatched node do inside one open dispatch?"

Those are different trust lanes even when a concrete adapter happens to expose both through one implementation.

## Optional observability tooling

Implementation may retain a separate observability lane only when it is needed for runtime correctness or support investigation. If it is carried over HTTP, it should be task-scoped such as `/observability/tasks/{task_id}/...`.

If retained, they are:

- outside the standard operator parity contract
- not required for ordinary automation
- not substitutes for canonical runtime surfaces

If retained, observability/debug tooling may expose inspection helpers such as:

| Observability/debug helper         | Canonical meaning                                                  | Result                     |
| ---------------------------------- | ------------------------------------------------------------------ | -------------------------- |
| `get_task_delivery_state(task_id)` | read generated delivery rollup for support investigation           | `delivery_state_ref`       |
| `get_task_continuity_state(task_id)` | read generated continuity rollup for support investigation       | `continuity_state_ref`     |
| `get_task_watchdog_state(task_id)` | read generated watchdog projection for support investigation       | `watchdog_state_ref`       |
| `get_task_provider_events(task_id)` | read normalized provider event log                                | `provider_events_ref`      |

Rules:

- these helpers are observability-facing only
- they are not part of the standard external plugin parity contract
- they are not part of the `/callback` dispatch-bound node adapter lane
- `delivery_state_ref`, `continuity_state_ref`, `watchdog_state_ref`, and `provider_events_ref` remain observability-only readback; they do not become ordinary callback or public-runtime context
- watchdog recovery is internal controller behavior and must not be taught as a plugin control action

## Removed from the live plugin reference

Do not keep these as the live plugin surface model:

- one standard plugin that mixes operator-safe external parity with the internal dispatch-bound runtime adapter lane
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

- [Human and operator control surface](human-and-operator-control-surface.md)
- [Operator definition and role boundary](operator-definition-and-role-boundary.md)
- [API surface and trust-lane map](api-surface-and-trust-lane-map.md)
- [API schema appendix](api-schema-appendix.md)
- [Guarded registry and runtime writes](guarded-registry-and-runtime-writes.md)
- [Runtime boundary and controller loop contract](../architecture/runtime-boundary-and-controller-loop-contract.md)
