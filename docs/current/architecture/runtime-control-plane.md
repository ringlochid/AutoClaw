# Current runtime control plane

Status: Current

Last verified: 2026-04-26

Current runtime truth is controller-owned and record-first. Transcript text, provider transport state, and assembled read models are not the authoritative source of control state.

Current runtime also works over the full active revision graph, not a lazy subtree-only runtime model.

## Keywords

- current control plane
- advance_flow_until_boundary
- boundary precedence
- wait reason
- flow status
- controller truth

## Current runtime truth

The current authoritative runtime spine includes:

- `Task`
- `TaskCompose`
- `WorkspaceRoot`
- `ContextSpace`
- `ManifestRoot`
- `TaskResourceBinding`
- `Flow`
- `FlowRevision`
- `FlowNode`
- `FlowEdge`
- `NodeAttempt`
- `NodeCheckpoint`
- `Approval`
- `NodePlanRevision`
- `NodeSession`
- `ContextItem`
- `ContextManifest`

`ContextManifest` is part of current implementation truth only. The redesign later demotes it to a transitional/private packaging record rather than a canonical runtime owner.

## Current derived views

Current operator snapshot, runtime slice, timeline slice, audit view, and worker bundle are assembled read models over those runtime records.

They are useful operational surfaces, but they do not outrank the controller-owned rows above.

## Current control facts

The controller advances through durable facts:

- task-compose launch and root materialization
- manifest projection and current manifest-acknowledgement lineage
- checkpoint writes
- approval creation and resolution
- replan requests and adoption
- watchdog stall detection and recovery
- operator actions

Primary code paths:

- `autoclaw-main/apps/api/app/runtime/runner.py`
- `autoclaw-main/apps/api/app/runtime/dispatcher.py`
- `autoclaw-main/apps/api/app/runtime/checkpoints.py`
- `autoclaw-main/apps/api/app/runtime/replan.py`
- `autoclaw-main/apps/api/app/runtime/watchdog.py`

## Current controller loop

The current shared controller loop is `advance_flow_until_boundary(...)`.

At a high level it:

1. locks the flow
2. loads the full active graph
3. checks whether the flow is already at a stop reason
4. if not, releases the next runnable node
5. creates the next blocked attempt
6. projects the next context manifest
7. refreshes flow state
8. stops at the next current boundary reason

## `CurrentBoundaryReasonPrecedence`

Current stop reasons come from `flow_boundary_snapshot().boundary_reason()` in this exact order:

| Priority | Condition                                          | Boundary reason       |
| -------- | -------------------------------------------------- | --------------------- |
| 1        | any node is currently `RUNNING`                    | `running`             |
| 2        | any projected manifest exists                      | `projected-manifests` |
| 3        | any pending approval exists                        | `pending-approvals`   |
| 4        | any waiting node resolves to `WaitReason.WATCHDOG` | `watchdog`            |
| 5        | any waiting node resolves to `WaitReason.APPROVAL` | `pending-approvals`   |
| 6        | any waiting node resolves to `WaitReason.OPERATOR` | `operator`            |
| 7        | all nodes are done                                 | `all-nodes-done`      |
| 8        | none of the above                                  | no boundary reason    |

Current code therefore has an implicit boundary loop, but it is precedence-based rather than a target-style typed boundary taxonomy.

## `CurrentWaitReasonResolution`

Current node wait resolution is not the same as flow boundary resolution.

`waiting_block_reason()` resolves only explicit current-attempt wait causes in this order:

| Priority | Condition                                                          | Result                      |
| -------- | ------------------------------------------------------------------ | --------------------------- |
| 1        | pending approval exists for current node/attempt                   | `WaitReason.APPROVAL`       |
| 2        | latest visible checkpoint has explicit `wait_reason`               | that checkpoint wait reason |
| 3        | latest visible checkpoint has `recommended_next_action == "retry"` | `WaitReason.OPERATOR`       |
| 4        | none of the above                                                  | no resolved wait reason     |

`current_wait_reason()` then adds one more inference layer for waiting nodes:

| Priority | Condition                                                                                 | Result                    |
| -------- | ----------------------------------------------------------------------------------------- | ------------------------- |
| 1        | `waiting_block_reason()` already resolved a current-attempt reason                        | that resolved wait reason |
| 2        | node is waiting, no explicit attempt wait reason exists, and dependencies are unsatisfied | `WaitReason.DEPENDENCY`   |
| 3        | none of the above                                                                         | no resolved wait reason   |

Important current fact:

- dependency wait is inferred per node
- dependency is inferred only by `current_wait_reason()`
- dependency wait is not promoted to a first-class flow boundary reason today
- approval wait and operator wait are distinct current wait reasons with different control consequences

## `CurrentFlowStatusPrecedence`

`refresh_flow_status()` uses this exact order:

| Priority | Condition                                  | Flow status               |
| -------- | ------------------------------------------ | ------------------------- |
| 1        | flow already `CANCELLED` or `FAILED`       | unchanged terminal status |
| 2        | all nodes done                             | `SUCCEEDED`               |
| 3        | any node paused                            | `PAUSED`                  |
| 4        | any pending approval or projected manifest | `BLOCKED`                 |
| 5        | any node running                           | `RUNNING`                 |
| 6        | any blocked wait reason exists             | `BLOCKED`                 |
| 7        | any ready node exists                      | `RUNNING`                 |
| 8        | any waiting node exists                    | `BLOCKED`                 |
| 9        | none of the above                          | `PENDING`                 |

## Minimal example

```text
continue
  -> controller loads active graph
  -> releases next runnable node
  -> creates attempt
  -> projects manifest
  -> stops at projected-manifests
```

## Expanded example

```text
task compose start
  -> compile/load plan
  -> materialize full flow graph
  -> return start response

continue
  -> enter advance_flow_until_boundary
  -> create next runnable attempt
  -> project manifest
  -> stop at projected-manifests
  -> dispatch to OpenClaw

checkpoint.green or checkpoint.retry
  -> apply checkpoint fact
  -> re-enter advance_flow_until_boundary
  -> stop at next running/projected-manifest/pending-approval/operator/all-done reason
```

## Evidence note

Inspected tests:

- `autoclaw-main/apps/api/tests/integration/test_runtime_api.py`
- `autoclaw-main/apps/api/tests/unit/test_watchdog_service.py`

These tests were inspected for coverage shape. They were not executed in this workspace as part of this docs rewrite.

## Redesign pointer

For the current OpenClaw dispatch and watchdog specifics, see [OpenClaw dispatch and session contract](openclaw-dispatch-and-session-contract.md) and [Watchdog and runtime monitoring](watchdog-and-runtime-monitoring.md).

For the target packet and work-order model, observability layer, operator hold boundary, and canonical controller loop, see [Runtime records and lifecycle](../../redesign/architecture/runtime-records-and-lifecycle.md), [Watchdog and recovery contract](../../redesign/architecture/watchdog-and-recovery-contract.md), [Runtime boundary and controller loop contract](../../redesign/architecture/runtime-boundary-and-controller-loop-contract.md), and [Runtime observability and boundary log](../../redesign/architecture/runtime-observability-and-boundary-log.md).
