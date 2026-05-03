# Current watchdog and runtime monitoring

Status: Current

Last verified: 2026-04-26

This page defines the exact current watchdog contract, current stall detection behavior, and the exact operator expectations after watchdog ambiguity or failure.

Current watchdog behavior is OpenClaw-shaped and same-session-biased.

## `CurrentWatchdogContract`

Current watchdog is a stale-running-attempt detector plus same-session auto-wake helper.

It is not a generic recovery engine over every blocked or waiting state.

Current watchdog is now stage-aware:

- `bootstrap_pending_ack`
- `execution_running`

## Current execution shape

Current watchdog runs as a simple background loop in `WatchdogService.run_forever()`.

Current service behavior:

- start once during app lifespan when `watchdog_enabled=true`
- sleep for `watchdog_interval_seconds` between ticks
- scan candidate flows
- run stall classification
- optionally run auto-recovery
- log tick outcomes

Current watchdog does not mutate state outside the normal runtime write paths. It still writes controller-owned records through the runtime layer.

## `CurrentWatchdogCandidateRule`

Current candidate lookup lives in `watchdog_queries.py`.

Current query rules are:

- inspect flows in `running` or `blocked`
- load the active graph and ordered nodes
- inspect latest attempts only
- treat a current attempt as candidate-worthy when:
  - running execution has no controller progress past the execution stale threshold
  - accepted bootstrap dispatch has still not acknowledged its manifest past the bootstrap ack timeout
  - the bound node session no longer points at the current attempt
  - provider returned a terminal response without the required controller callback

Important current exclusions:

- approval wait is not a watchdog stall candidate
- operator wait is not a watchdog stall candidate
- dependency wait is not a watchdog stall candidate
- already blocked or pending attempts are not stall candidates
- except accepted bootstrap-pending-ack attempts, which are intentionally watchdog-visible

## Current stall detection

Current stall detection in `run_flow_watchdog(...)` uses:

- running latest attempt status or accepted bootstrap-pending-ack state
- last visible checkpoint time
- latest acked manifest time when execution has started but no visible checkpoint exists yet
- provider accepted-at and bounded provider stream hints
- current node-session binding
- separate bootstrap and execution watchdog thresholds from settings

When a node is classified as stalled, current watchdog:

- marks the attempt `blocked`
- sets the node state to `waiting`
- idles the node session
- records a `blocked` checkpoint with:
  - summary `watchdog stalled attempt`
  - stage-specific reason and dispatch ref
  - execution stale or bootstrap ack timeout facts
  - last controller progress and last provider hint timestamps where relevant
  - recommended next action `retry`
  - wait reason `watchdog`

## `CurrentWatchdogRecoveryLadder`

Current recovery lives in `recover_flow_watchdog(...)`.

Current exact ladder is:

1. find watchdog-blocked waiting nodes
2. if no eligible node exists, return `no-eligible-node`
3. if more than one eligible node exists, escalate
4. if the node is bootstrap-pending-ack, use fresh retry logic instead of same-session wake
5. otherwise require the delegated session to still exist and still bind to the current attempt
6. enforce the relevant recovery budget
7. bootstrap no-ack recovery mints a fresh attempt and fresh manifest lineage; current code may still reuse the existing `NodeSession` row and provider session key
8. running execution recovery dispatches a same-session OpenClaw wake
9. if recovery fails or delivery is ambiguous, escalate

## Wake budget

Current documented default is:

- one same-session auto-wake per attempt
- two fresh bootstrap auto-retries after the original bootstrap dispatch

Current code exposes a configurable `max_auto_wakes` parameter, but the exact current default behavior is still one wake per attempt.

Current implementation debt:

- desired target bootstrap retry behavior is `fresh attempt + fresh session`
- current code does not yet remint a fresh provider session key for bootstrap auto-retry
- current implementation also does not yet do the redesign's one-session-recover plus one-fresh-retry ladder

## `CurrentWatchdogEscalationReasons`

Current recovery can escalate for these exact reasons:

- `no-active-revision`
- `no-eligible-node`
- `multiple-watchdog-blocked-nodes`
- `missing-or-rebound-session`
- `wake-budget-exhausted`
- `bootstrap-retry-budget-exhausted`
- `bootstrap-retry-dispatch-timeout`
- `bootstrap-retry-dispatch-failed`
- `wake-dispatch-timeout`
- `wake-dispatch-failed`

## `CurrentOperatorAfterAmbiguityRule`

Current timeout escalation is intentionally ambiguous-delivery aware.

It does not prove the worker failed to receive the wake.

After ambiguous timeout or wake failure, current operator guidance is:

- inspect session binding before retry
- inspect recent checkpoints before retry
- do not assume timeout proves failed delivery
- prefer explicit operator retry only after inspection

## Current monitoring inputs

Current monitoring and recovery rely on:

- controller-owned runtime rows
- visible checkpoints
- node session status and timestamps
- staged OpenClaw dispatch rows
- append-only provider dispatch events
- flow status and node state
- OpenClaw dispatch outcomes

Current implementation does not yet expose the redesign's normalized provider-event log, session-hint confidence model, or boundary-log health taxonomy.

## Current operator and audit surfaces

Current monitoring drilldown uses:

- flow operator snapshot
- runtime slice
- timeline slice
- flow audit
- checkpoints
- replans

These are read models over controller-owned records. They are not a separate monitoring truth layer.

## Minimal example

```text
running attempt
  -> no visible progress past threshold
  -> watchdog blocks attempt
  -> watchdog checkpoint recorded
  -> same-session wake may be attempted once by default
```

## Expanded example

```text
watchdog tick
  -> list candidate flow ids
  -> inspect running latest attempts and accepted bootstrap-pending-ack attempts
  -> detect stale running execution or bootstrap no-ack from checkpoints/session binding/dispatch hints
  -> block attempt and record watchdog checkpoint
  -> if auto recover enabled and budget allows:
       either dispatch same-session OpenClaw wake
       or mint a fresh bootstrap retry
  -> if recovery times out ambiguously or recovery fails:
       escalate with operator_next_step
       inspect session binding and recent checkpoints before retry
```

## Evidence

- inspected code in `autoclaw-main/apps/api/app/runtime/watchdog.py`
- inspected code in `autoclaw-main/apps/api/app/runtime/watchdog_service.py`
- inspected code in `autoclaw-main/apps/api/app/runtime/watchdog_queries.py`
- inspected code in `autoclaw-main/apps/api/app/api/routes/flows.py`
- inspected code in `autoclaw-main/apps/api/app/schemas/runtime.py`
- inspected tests in `autoclaw-main/apps/api/tests/unit/test_watchdog_service.py`

## Related current pages

- `runtime-control-plane.md`
- `runtime-read-models-and-operator-surfaces.md`
- `parent-retry-and-operator-control.md`
- `openclaw-dispatch-and-session-contract.md`

## Redesign pointer

For the target monitor, watchdog, and health-rollup contract, see `../../redesign/architecture/watchdog-and-recovery-contract.md`, `../../redesign/architecture/runtime-observability-and-boundary-log.md`, and `../../redesign/architecture/runtime-monitoring-and-watchdog-automation.md`.
