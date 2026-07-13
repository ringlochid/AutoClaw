# Console API and view-model boundary

Status: Target

This page owns how the console consumes finalized Control API and task-event contracts and maps them into render-ready runtime views. It does not define wire fields, routes, controller currentness, or event payloads.

## Core rule

Source-row reads own current state. Task events own chronology. View-model mappers keep those roles separate.

Page components consume generated API types and explicit render mappers; they do not parse raw controller payloads, event frames, or failures deep inside JSX.

## Data sources

| Console need | Canonical source |
| --- | --- |
| current task, attempt, dispatch, plan, progress, provider, recovery, and current waits | `GET /control/tasks/{task_id}` |
| operator-ready current summary and stream anchor | `GET /control/tasks/{task_id}/snapshot` |
| graph and dispatch/checkpoint/boundary history | `GET /control/tasks/{task_id}/trace` |
| ordered plan revisions, provider-control attempts, waits, checkpoints, and boundaries | task event list and SSE |
| complete human-request source and resolution | human-request list route |
| complete command-run source, terminal result, and cancellation provenance | command-run list and detail routes |
| authorized command output on explicit inspection | dedicated command-run log route |

No mapper reads currentness from support files, provider streams, provider events, or client-local timestamps.

## Current runtime mapping

The task runtime view maps only fields supplied by `RuntimeFlowRead` and its finalized nested reads.

### Plan

Current plan rendering uses `current_plan` exactly:

- `attempt_id`
- `revision`
- `explanation`
- ordered `steps`
- `updated_by_dispatch_id`
- `updated_at`

Plan history uses `plan_updated` event payloads. The mapper keys snapshots by `(attempt_id, revision)`, orders them by `event_seq`, and preserves attempts as separate histories. It does not derive a revision from step differences or display local unsaved plan state.

### Progress

Semantic progress uses `current_dispatch.last_progress_at`. A relative label is a pure display of that timestamp. It does not become a second stored progress value or an inferred watchdog state.

### Provider provenance

Provider provenance uses:

- `current_dispatch.requested_provider`
- `current_dispatch.resolved_provider`

These two fields are the finalized minimum resolution provenance. A mapper may derive a display fact such as `isFallback = requested_provider != resolved_provider`, but it must not add a fallback chain, model, run id, or provider health field.

### Provider control

Current provider-control display uses the persisted nested read:

- `operation`
- `state`
- `attempt`
- `max_attempts`
- `next_retry_at`
- `last_error_summary`
- `updated_at`

The bounded `reason` comes from the corresponding `dispatch_control_updated` event. It belongs to the control chronology, not the persisted current read. The console may associate it with the matching dispatch, operation, and attempt for display, but a source refresh remains authoritative for current control state.

The countdown is `max(0, next_retry_at - client_now)` for presentation. A timer expiry triggers neither provider control nor optimistic state mutation.

### Recovery

Recovery display uses:

- `watchdog_restart_count`
- task `status`
- `pause_reason`
- current or most recent dispatch state and close reason
- current provider-control readback

`pause_reason = runtime_recovery_exhausted` selects the exhausted-recovery presentation and ordinary continue action. No view-model-only recovery state is added.

### External waits

The task read supplies `waiting_cause`, `current_human_request`, and `current_command_run` for compact current state. Dedicated source routes supply full request items, resolutions, command-run detail, and terminal provenance.

Task-event payloads may update chronology and prompt a source refresh. They do not replace the full source record or authorize an action.

## Event mapping

The event client preserves the complete `task_event` envelope, especially `event_id`, `event_seq`, `event_type`, `occurred_at`, `dispatch_id`, `attempt_id`, and `payload`.

Rules:

- order by `event_seq`, not arrival time
- deduplicate by event identity without collapsing distinct revisions or attempts
- render only documented event families
- keep `plan_updated` snapshots intact for revision history
- keep `dispatch_control_updated.reason` attached to its chronology row
- fetch source detail for complete human answers and command logs
- never translate provider output into synthetic task events

## Cursor reset

`cursor_reset_required` is a distinct client transition.

The console:

1. stops applying the stale stream
2. clears event-derived current display assumptions
3. refetches the task runtime read and snapshot
4. refetches selected human-request or command-run detail when needed
5. resets ordering and deduplication around the fresh snapshot
6. reconnects after `stream_head_event_id`

The reset does not fold retained events into current state. Event history visible after reset is whatever the event owner lawfully returns; source rows remain sufficient for the current runtime view.

## Mutation boundary

Pause, continue, cancel, human-request resolve, and command-run cancel use generated request/response contracts and fresh currentness guards.

Rules:

- no optimistic mutation claims a controller transition before success
- normalized stale or illegal-state failures trigger a targeted source refresh
- continue is offered only for controller states where the Control API defines it
- human requests and command runs use their own resolution or cancellation routes
- task cancel and command-run cancel remain distinct actions

## Error boundary

The client normalizes:

- structured runtime failures
- request validation failures
- HTTP authorization and status errors
- network and abort errors
- cursor-reset failures
- malformed event frames

Render views consume the normalized failure summary, retryability, field path where available, and suggested next step. They never expose raw provider exceptions, stack traces, credentials, or process environment.

## Data exclusions

Frontend API state, view models, fixtures, and persisted browser storage must not add:

- raw provider events, output, tool streams, or logs
- provider credentials or authentication state
- `provider_session_hint`
- provider run ids or adapter-private handles
- `NodeMcpInvocation` rows
- unsupported counts, percentages, ETA, throughput, or health labels
- support-file-derived currentness

Fixtures may model only finalized controller fields, states, events, and errors.

## Owner boundary

This page owns client-side source selection and mapping. The [Control API](../interfaces/control-api.md) owns fields and routes, the [task event stream](../interfaces/task-event-stream.md) owns event payloads and reset semantics, and [Console runtime surfaces](../interfaces/console-runtime-surfaces.md) owns product presentation meaning.

## Related contracts

- [Console target](README.md)
- [Page state contracts](page-state-contracts.md)
- [Console runtime surfaces](../interfaces/console-runtime-surfaces.md)
- [Control API](../interfaces/control-api.md)
- [Task event stream](../interfaces/task-event-stream.md)
- [Human request and approval contract](../interfaces/human-request-and-approval-contract.md)
- [Command run and external wait](../architecture/command-run-and-external-wait.md)
