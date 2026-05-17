# Current watchdog and runtime monitoring

Status: Current

Last verified: 2026-05-17

This page defines the shipped watchdog-state and runtime-monitoring contract
that remains in the current repo.

Current watchdog state is controller-owned and surfaced through observability
projections.

## `CurrentWatchdogContract`

Current repo-visible watchdog truth is the `DispatchWatchdogStateModel` record
plus the derived `_runtime/dispatch/<dispatch_id>/watchdog-state.json`
projection.

This tree no longer ships the older dedicated `WatchdogService`,
`watchdog_queries.py`, or watchdog recovery endpoints that older docs cited.

## Current execution shape

Current repo-visible watchdog state is created and updated through normal
controller paths:

- dispatch opening seeds a watchdog-state row
- dispatch materialization writes the corresponding JSON projection
- operator observability reads expose the current file ref

The shipped router does not expose a dedicated public or internal watchdog
action lane.

## `CurrentWatchdogCandidateRule`

The repo-visible watchdog surface is dispatch-scoped, not flow-loop-scoped.

The persisted watchdog row carries:

- `watchdog_state`
- `current_watchdog_kind`
- `current_watchdog_reason`
- `recovery_action`
- `recovery_reason`
- previous, recovery, and superseding dispatch lineage

## Current stall detection

Current monitoring still combines:

- controller-owned dispatch rows
- continuity-state and delivery-state rows
- provider-event records
- watchdog-state rows
- task-root observability projections

## `CurrentWatchdogRecoveryLadder`

The current repo does not expose the older detailed recovery ladder as a
standalone implementation surface.

Current operator-facing recovery remains:

- inspect runtime task state
- inspect operator snapshot and trace
- inspect observability refs, including `watchdog-state.json`
- use shipped operator controls such as `continue`, `pause`, or `cancel` when
  current controller truth allows them

## `CurrentOperatorAfterAmbiguityRule`

Current observability is intentionally not runtime truth.

After ambiguous or stale delivery state, current operator guidance is:

- inspect runtime state before steering the flow
- inspect recent checkpoints, trace entries, and observability refs
- do not treat `watchdog-state.json` as the authority over controller rows
- use the shipped operator controls rather than assuming hidden recovery lanes

## Current monitoring inputs

Current monitoring relies on:

- controller-owned runtime rows
- checkpoints
- staged dispatch rows
- node sessions
- append-only provider dispatch events
- dispatch delivery-state, continuity-state, and watchdog-state rows
- generated observability projections under `_runtime/dispatch/<dispatch_id>/`

## Current operator and audit surfaces

Current monitoring drilldown uses:

- runtime task read
- operator snapshot
- operator trace
- observability file refs

These are read models over controller-owned records. They are not a separate
monitoring truth layer.

## Minimal example

```text
dispatch opens
  -> controller seeds watchdog-state row
  -> `_runtime/dispatch/<dispatch_id>/watchdog-state.json` is materialized
  -> operator reads the surfaced watchdog-state ref
```

## Expanded example

```text
dispatch observability reread
  -> operator reads `/runtime/tasks/{task_id}`
  -> operator reads `/operator/tasks/{task_id}/trace`
  -> operator reads `/observability/tasks/{task_id}/watchdog-state`
  -> treat the file ref as derived observability, then steer the flow through
     shipped operator controls
```

## Evidence

- inspected code in `apps/api/app/runtime/control/dispatch/opening.py`
- inspected code in `apps/api/app/runtime/projection/dispatch/materialization.py`
- inspected code in `apps/api/app/runtime/control/observability.py`
- inspected code in `apps/api/app/db/models/runtime/dispatch/states.py`
- inspected code in `apps/api/app/api/routes/observability.py`
- inspected code in `apps/api/app/schemas/runtime/observability.py`
- inspected tests in `apps/api/tests/integration/phase2/bootstrap/test_dispatch.py`
- inspected tests in `apps/api/tests/integration/phase3/routes/test_surface_contract.py`

## Related current pages

- `runtime-control-plane.md`
- `runtime-read-models-and-operator-surfaces.md`
- `parent-retry-and-operator-control.md`
- `openclaw-dispatch-and-session-contract.md`

## Redesign pointer

For the target monitor, watchdog, and health-rollup contract, see
`../../redesign/architecture/watchdog-and-recovery-contract.md`,
`../../redesign/architecture/runtime-observability-and-boundary-log.md`, and
`../../redesign/architecture/runtime-monitoring-and-watchdog-automation.md`.
