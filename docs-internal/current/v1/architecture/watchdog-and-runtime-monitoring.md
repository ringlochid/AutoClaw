# Current watchdog and runtime monitoring

Status: Current

Last verified: 2026-06-28

This page defines the shipped watchdog-state and runtime-monitoring contract that remains in the current repo.

Current watchdog state is controller-owned and surfaced through observability projections.

## `CurrentWatchdogContract`

Current watchdog truth is the `DispatchWatchdogStateModel` record family plus the derived `_runtime/dispatch/<dispatch_id>/watchdog-state.json` projection.

The shipped repo includes the watchdog reconciliation loop under `apps/api/src/autoclaw/runtime/watchdog/**`. The loop classifies committed controller rows; it does not make support files authoritative.

## Current execution shape

Current watchdog state is created, classified, recovered, cleared, and projected through controller paths:

- dispatch opening seeds a watchdog-state row
- delivery, continuity, checkpoint, provider-event, human-request, and command-run rows provide classification context
- `reconcile_watchdog_truth` classifies or clears watchdog rows
- recovery may redispatch the same attempt or escalate according to the classification
- dispatch materialization writes the corresponding JSON projection
- operator observability reads expose the current file ref

The shipped router does not expose a dedicated public watchdog action lane. Operator control still goes through runtime/control surfaces rather than direct watchdog mutation.

## `CurrentWatchdogCandidateRule`

The repo-visible watchdog surface is dispatch-scoped, not flow-loop-scoped.

The persisted watchdog row carries:

- `watchdog_state`
- `current_watchdog_kind`
- `current_watchdog_reason`
- `recovery_action`
- `recovery_reason`
- previous, recovery, and superseding dispatch lineage

When present, live `recovery_action` values are only `redispatch_same_attempt` or `escalate`.

For current parent/root same-attempt recovery, the replacement dispatch preserves a dispatch-local staged child basis only when the fenced prior dispatch still proves that staged child assignment through current controller truth. That continuation basis remains dispatch-bound rather than attempt-bound.

## Current external-wait boundary handling

Human-request and command-run dispatches are legal external-wait boundaries.

Current monitoring therefore treats a dispatch as an external-wait source dispatch when it owns a committed `pending_human_requests` or `command_runs` row. That source-row check applies to both open or running waits and terminal waits that will drive continuation.

Rules:

- the watchdog uses source rows, not `control_state_reason`, prompt text, or provider labels, to recognize external-wait boundaries
- an external-wait source dispatch remains clear instead of being escalated as a terminal-provider-without-callback failure
- ordinary terminal-provider failures still classify when no human-request or command-run source row exists for the dispatch
- operator read models may show the wait and its events, but controller rows remain the currentness and legality source

## Current stall detection

Current monitoring combines:

- controller-owned dispatch rows
- continuity-state and delivery-state rows
- latest attempt checkpoint rows
- provider-event records
- human-request and command-run source rows
- watchdog-state rows
- task-root observability projections

Current shipped contrast:

- execution-stale timing keys off acceptance time, committed controller semantic progress, and committed provider-signal progress
- checkpoint time alone does not extend the current execution-stale deadline
- `last_provider_signal_at` contributes to the committed stale-progress anchor after controller normalization and commit
- current watchdog-visible provider progress moves only after controller normalization and commit, not on raw transport receipt
- external waits are recognized from controller-owned source rows before terminal-provider failure classification runs

## `CurrentWatchdogRecoveryLadder`

The current repo exposes recovery through the runtime watchdog loop, not a public watchdog mutation API.

Current operator-facing recovery remains:

- inspect runtime task state
- inspect operator snapshot and trace
- inspect observability refs, including `watchdog-state.json`
- use shipped operator controls such as `continue`, `pause`, or `cancel` when current controller truth allows them

## `CurrentOperatorAfterAmbiguityRule`

Current observability is intentionally not runtime truth.

After ambiguous or stale delivery state, current operator guidance is:

- inspect runtime state before steering the flow
- inspect recent checkpoints, trace entries, source rows, and observability refs
- do not treat `watchdog-state.json` as the authority over controller rows
- use the shipped operator controls rather than assuming hidden recovery lanes

## Current monitoring inputs

Current monitoring relies on:

- controller-owned runtime rows
- checkpoints
- staged dispatch rows
- node sessions
- append-only provider dispatch events
- pending human requests
- command runs
- dispatch delivery-state, continuity-state, and watchdog-state rows
- generated observability projections under `_runtime/dispatch/<dispatch_id>/`

## Current operator and audit surfaces

Current monitoring drilldown uses:

- runtime task read
- operator snapshot
- operator trace
- observability file refs
- human-request and command-run control readbacks when relevant

These are read models over controller-owned records. They are not a separate monitoring truth layer.

## Minimal example

```text
dispatch opens
  -> controller seeds watchdog-state row
  -> watchdog reconciles committed dispatch and delivery rows
  -> `_runtime/dispatch/<dispatch_id>/watchdog-state.json` is materialized
  -> operator reads the surfaced watchdog-state ref
```

## Expanded example

```text
worker dispatch opens a human request
  -> pending_human_requests row owns the source wait
  -> dispatch reaches terminal provider shape for that wait-opening turn
  -> watchdog sees the dispatch-owned human-request source row
  -> watchdog leaves the dispatch clear instead of escalating terminal-provider state
  -> human request resolves
  -> controller continues the same task lineage when currentness still matches
```

## Evidence

- inspected code in `apps/api/src/autoclaw/runtime/watchdog/service.py`
- inspected code in `apps/api/src/autoclaw/runtime/watchdog/task_rows.py`
- inspected code in `apps/api/src/autoclaw/runtime/watchdog/classification.py`
- inspected code in `apps/api/src/autoclaw/runtime/watchdog/recovery.py`
- inspected code in `apps/api/src/autoclaw/runtime/dispatch/opening.py`
- inspected code in `apps/api/src/autoclaw/runtime/projection/dispatch/materialization.py`
- inspected code in `apps/api/src/autoclaw/runtime/observability/__init__.py`
- inspected code in `apps/api/src/autoclaw/persistence/models/runtime/dispatch/states.py`
- inspected code in `apps/api/src/autoclaw/persistence/models/runtime/human_requests.py`
- inspected code in `apps/api/src/autoclaw/persistence/models/runtime/command_runs.py`
- inspected code in `apps/api/src/autoclaw/persistence/models/runtime/waiting.py`
- inspected code in `apps/api/src/autoclaw/runtime/contracts/observability.py`
- inspected tests in `apps/api/tests/integration/watchdog/test_stale_classification.py`
- inspected tests in `apps/api/tests/integration/watchdog/test_recovery_actions.py`
- inspected tests in `apps/api/tests/integration/runtime/routes/test_human_request_continuation.py`
- inspected tests in `apps/api/tests/integration/runtime/routes/test_command_run_control_api.py`

## Related current pages

- `runtime-control-plane.md`
- `runtime-read-models-and-operator-surfaces.md`
- `parent-retry-and-operator-control.md`
- `openclaw-dispatch-and-session-contract.md`
- `watchdog-and-openclaw-bridge.md`

## Design pointer

For the target monitor, watchdog, and health-rollup contract, see `../../../design/v2/architecture/controller-contract-and-resumable-execution.md`, `../../../design/v2/interfaces/human-request-and-approval-contract.md`, `../../../design/v2/architecture/command-run-and-long-running-boundary.md`, and the V1 baseline pages `../../../design/v1/architecture/watchdog-and-recovery-contract.md`, `../../../design/v1/architecture/runtime-observability-and-boundary-log.md`, and `../../../design/v1/architecture/runtime-monitoring-and-watchdog-automation.md`.
