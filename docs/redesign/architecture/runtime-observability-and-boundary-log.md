# Runtime Observability And Boundary Log

Status: Target

## Purpose

This page freezes the v1 observability lane for runtime boundaries, dispatch delivery, continuity, watchdog classification, and provider-event history.

## Core Observability Rule

- controller/DB state is the authoritative runtime truth
- `_runtime/dispatch/<dispatch_id>/...` files are controller-generated observability projections over that truth
- observability refs use the shared `support_runtime_file_ref` family
- observability refs are legal on `/observability/...` and selected `/operator/...` carriers only; `/runtime`, `/callback`, manifest, assignment, checkpoint, and ordinary prompt context do not surface them
- provider transport events never redefine assignment success, retry lineage, blocked meaning, or release legality

## Shared Observability Ref Family

```yaml
support_runtime_file_ref:
  kind: delivery_state | continuity_state | watchdog_state | provider_events
  path: string
  description: string
```

## Canonical Dispatch Observability Files

```text
_runtime/
  dispatch/
    <dispatch_id>/
      delivery-state.json
      continuity-state.json
      watchdog-state.json
      provider-events.ndjson
```

| Surface                  | Exact meaning                                                                                               | Must not be confused with                                          |
| ------------------------ | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `delivery-state.json`    | Latest controller delivery rollup for one dispatch path.                                                    | Checkpoint, attempt result, machine failure contract               |
| `continuity-state.json`  | Latest controller continuity-state projection for one dispatch/attempt lineage.                             | Retry lineage, assignment lineage, or node-visible runtime context |
| `watchdog-state.json`    | Latest watchdog classification and controller recovery-action projection for one dispatch.                  | Attempt `blocked` truth                                            |
| `provider-events.ndjson` | Append-only normalized provider/adapter event stream for one dispatch.                                      | Checkpoint stream, artifact log, or transcript                     |
| boundary log             | Chronological record of public boundary facts such as `dispatch`, `yield`, `green`, `retry`, and `blocked`. | Provider-event chronology or watchdog heuristics                   |

## Support-State Readback Shapes

These files are controller-generated support projections. The file family and the behavior-defining fields called out below remain part of the live observability contract, but retained non-behavioral readback residue does not. If current code still emits fields such as `controller_observation_state` or broad `continuity_state` catalogs, treat them as current/debt cleanup targets rather than frozen v1 surfaces.

`delivery-state.json`

```json
{
  "dispatch_id": "dispatch.parent.01",
  "attempt_id": "attempt.parent.01",
  "assignment_key": "parent.assign-01",
  "node_key": "implementation_subtree",
  "transport_family": "openclaw_gateway_ws_rpc",
  "transport_state": "provider_signal_seen",
  "controller_observation_state": "live",
  "last_provider_event_kind": "output_delta",
  "provider_final_status": null,
  "provider_error": null,
  "previous_dispatch_id": null,
  "superseded_by_dispatch_id": null,
  "prepared_at": "2026-05-03T10:00:00Z",
  "accepted_at": "2026-05-03T10:00:01Z",
  "last_provider_signal_at": "2026-05-03T10:00:12Z",
  "last_controller_progress_at": "2026-05-03T10:00:15Z",
  "last_controller_terminal_at": null,
  "updated_at": "2026-05-03T10:00:15Z"
}
```

Accepted-boundary waiting remains a controller-derived interpretation over the
live dispatch, accepted boundary, and inactivity-proof state. The raw
`delivery-state.json` projection stays a transport/control rollup and does not
mint a separate `boundary_accepted_waiting_terminal` observation enum.

If `controller_observation_state` is still present, it remains an observability mirror only and is a deletion target once code cleanup reaches the readback surface. Live runtime behavior is governed by `DispatchTurn.control_state` and `DispatchTurn.delivery_status`, not by a second target-facing observation state machine.

Stronger-design field meanings:

- `accepted_at` is the first accepted transport timestamp for the dispatch
- `last_provider_signal_at` is the latest normalized provider progress-or-terminal signal timestamp
- `last_provider_event_kind` is the latest normalized provider progress-or-terminal kind
- `last_controller_progress_at` is the latest node semantic write timestamp in the stronger design; current code may still use narrower or older semantics until the follow-on implementation lands
- stale-timeout anchoring uses `accepted_at`, `last_provider_signal_at`, and the latest node semantic write timestamp rather than checkpoint time

`continuity-state.json`

```json
{
  "dispatch_id": "dispatch.parent.01",
  "attempt_id": "attempt.parent.01",
  "assignment_key": "parent.assign-01",
  "node_key": "implementation_subtree",
  "continuity_state": "candidate",
  "session_key_present": true,
  "invalidation_reason": null,
  "updated_at": "2026-05-03T10:00:15Z"
}
```

`continuity-state.json` remains a narrow observability projection. Its target-facing emphasis is session presence and invalidation only; transport continuation catalogs and broad `continuity_state` taxonomies are current/debt details rather than live target truth and may be deleted during cleanup.

`watchdog-state.json`

```json
{
  "dispatch_id": "dispatch.parent.01",
  "attempt_id": "attempt.parent.01",
  "assignment_key": "parent.assign-01",
  "node_key": "implementation_subtree",
  "watchdog_state": "clear",
  "current_watchdog_kind": null,
  "current_watchdog_reason": null,
  "recovery_action": null,
  "recovery_reason": null,
  "recovery_dispatch_id": null,
  "previous_dispatch_id": null,
  "superseded_by_dispatch_id": null,
  "classified_at": "2026-05-03T10:00:15Z",
  "updated_at": "2026-05-03T10:00:15Z"
}
```

Live `recovery_action` values are `redispatch_same_attempt`, `escalate`, or
`null`. Older `create_new_attempt` recovery-state history is current/debt
contrast only and is not live Phase 4.5 canon.

`current_watchdog_kind` is `null` or one of the closed v1 trigger-family strings from [Watchdog and recovery contract](watchdog-and-recovery-contract.md):

- `bootstrap_pending_callback.bootstrap_callback_timeout`
- `bootstrap_pending_callback.terminal_provider_without_first_callback`
- `execution_running.execution_stale`
- `execution_running.delivery_path_rebound`
- `execution_running.terminal_provider_without_controller_checkpoint`

`provider-events.ndjson`

One UTF-8 JSON object per line in controller-observed order. Every line uses this exact frozen field set:

```json
{"dispatch_id":"dispatch.parent.01","attempt_id":"attempt.parent.01","event_no":1,"event_source":"provider","event_kind":"accepted","provider_event_name":"response.created","summary":"Provider transport accepted the current dispatch path.","detail":null,"provider_occurred_at":"2026-05-03T10:00:01Z","observed_at":"2026-05-03T10:00:01Z"}
{"dispatch_id":"dispatch.parent.01","attempt_id":"attempt.parent.01","event_no":2,"event_source":"provider","event_kind":"output_delta","provider_event_name":"response.output_text.delta","summary":"Provider emitted output for the current dispatch path.","detail":{"delta_chars":128},"provider_occurred_at":"2026-05-03T10:00:11Z","observed_at":"2026-05-03T10:00:12Z"}
{"dispatch_id":"dispatch.parent.01","attempt_id":"attempt.parent.01","event_no":3,"event_source":"provider","event_kind":"response_completed","provider_event_name":"response.completed","summary":"Provider transport ended normally for the current dispatch path.","detail":{"finish_reason":"stop"},"provider_occurred_at":"2026-05-03T10:00:22Z","observed_at":"2026-05-03T10:00:22Z"}
```

Rules:

- `event_no` is a per-dispatch append-only sequence number
- `event_source` identifies the normalized source family for the line
- `event_kind` uses the canonical normalized monitoring enums
- `provider_event_name` preserves the raw provider or OpenClaw event label as debug detail only
- `detail` and `provider_occurred_at` are part of the frozen readback field set even when their value is `null`
- these lines explain delivery chronology only and do not redefine checkpoint, boundary, attempt, or assignment truth
- unrelated buffered events that cannot be correlated to the active dispatch/run are not normalized into liveness progress and do not advance `last_provider_signal_at`

## Boundary Log Rule

Boundary log answers:

- which node was dispatched
- which attempt and assignment were current
- when the dispatch closed
- whether closure was `yield`, `green`, `retry`, or `blocked`

Boundary log does not answer provider SSE ordering, same-session legality, or watchdog recovery choice. Those belong to the observability lane.

## Observability Read Order

1. Read controller/DB truth or an operator read model over that truth.
2. Read boundary history and latest dispatch/attempt facts.
3. Read the dispatch observability projections in this order: `delivery-state.json`, `continuity-state.json`, `watchdog-state.json`, `provider-events.ndjson`.
4. Read manifest, assignment, latest checkpoint, or surfaced evidence only if the incident changes durable task understanding.

If a transport incident matters durably, summarize it in checkpoint or surfaced refs rather than leaving it discoverable only by scanning `_runtime/dispatch/`.

## Reconstruction Rules

Operator tooling correlates histories by `dispatch_id` first and `attempt_id` second. Ordering uses controller-observed UTC timestamps and `provider-events.ndjson.event_no` within one dispatch stream. If controller/DB state and a generated file disagree, controller/DB state wins.

## OpenClaw Normalization Rule

- raw OpenClaw event names may survive only as debug detail such as `provider_event_name`
- canonical observability families use normalized enums
- `tool` remains the runtime term
- `plugin` remains adapter-specific terminology only

## Related Contracts

- [Runtime boundary and controller loop contract](runtime-boundary-and-controller-loop-contract.md)
- [Runtime database and object contract](runtime-database-and-object-contract.md)
- [Watchdog and recovery contract](watchdog-and-recovery-contract.md)
- [OpenClaw continuity and send modes](openclaw-continuity-and-send-modes.md)
- [OpenClaw worker and gateway contract](openclaw-worker-and-gateway-contract.md)
