# Task event stream

Status: Target

This page owns V2 append-only task chronology, event payloads, cursor backfill, Server-Sent Events delivery, and replay/reset behavior. Source-row reads and operator mutations belong to the [Control API](control-api.md).

## Core rule

Task events are bounded chronology emitted from committed controller state. They are authoritative for ordering, backfill, and audit-chain verification, but never for runtime currentness, mutation legality, provider retry scheduling, or external-wait continuation.

Replaying an event must never execute provider control, rerun a command, reopen a wait, or reapply a semantic mutation.

## Event record

Every event has this envelope:

```yaml
task_event:
    event_id: string
    event_seq: integer
    task_id: string
    event_type: string
    event_source: controller | control_api | operator_mcp | node
    occurred_at: timestamp
    flow_revision_id: string | null
    dispatch_id: string | null
    attempt_id: string | null
    node_key: string | null
    actor_ref: string | null
    payload: object
    prev_event_hash: string | null
    event_hash: string
```

Rules:

- `event_seq` is strictly increasing and unique within one task
- `event_source` identifies the controller-facing invocation lane; human or automation identity belongs in `actor_ref`
- provider and adapter are not event sources in V2
- payload fields are bounded semantic summaries, not source-row replacements
- hash chaining covers the canonical serialized event and prior hash
- one source mutation and its event commit in the same controller transaction where practical

Provider output, native tool events, token streams, disconnects, and terminal frames never produce main task events.

## Backfill route

`GET /control/tasks/{task_id}/events` accepts:

```yaml
task_event_list_query:
    cursor: string | null
    limit: 1..500
    through_event_id: string | null
```

It returns:

```yaml
task_event_list_response:
    task_id: string
    items: task_event[]
    next_cursor: string | null
    through_event_id: string | null
```

Events are ordered by ascending `event_seq`. `cursor` is exclusive. `through_event_id` freezes the inclusive high-water mark for deterministic multi-page backfill. A caller keeps the first response's high-water mark through the remaining pages.

Cursor tokens may encode task and sequence identity. They are opaque to clients.

## SSE route

`GET /control/tasks/{task_id}/events/stream` delivers standard SSE:

```text
id: <event_id>
event: <event_type>
data: <complete task_event JSON>

```

Resume rules:

- the client may send `cursor=<event_id>` or `Last-Event-ID`
- when both are present they must identify the same event
- the resume cursor is exclusive
- no cursor means live tail from the head observed during stream setup
- transport reconnect never changes task state

SSE may use polling or database notification internally. The transport choice does not change event or runtime semantics.

## Replay and reset

If a cursor is valid and retained, list and SSE continue after it without duplicates in the logical sequence.

If a cursor is missing, from another task, invalid, or older than retained history, the server returns the structured `cursor_reset_required` failure with the task identifier and a fresh snapshot path.

The HTTP status is `410 Gone`.

The client reset flow is:

1. read `GET /control/tasks/{task_id}`
2. read `GET /control/tasks/{task_id}/snapshot`
3. optionally read trace or source-specific detail
4. reconnect after `stream_head_event_id`

Events arriving after the snapshot high-water mark are then delivered normally. The reset path never rebuilds current state by folding the event log.

## Event catalog

The minimum V2 families are:

```text
task_started
dispatch_opened
dispatch_control_updated
plan_updated
checkpoint_recorded
boundary_accepted

child_assignment_staged
child_assignment_committed
structural_revision_adopted

human_request_opened
human_request_resolved
human_request_timed_out
human_request_cancelled

command_run_started
command_run_progressed
command_run_cancel_requested
command_run_succeeded
command_run_failed
command_run_timed_out
command_run_cancelled

task_paused
task_resumed
task_cancelled
```

There is no provider-resolution event, provider-lifecycle event, adapter event, generic MCP-call event, or per-invocation event.

## Task start event

`task_started` is emitted after the controller commits the task lineage, current flow revision, root attempt basis, and workflow manifest:

```yaml
task_started:
    task_title: string
    task_summary: string
    workflow_key: string | null
    initial_node_key: string
    workflow_manifest_ref: ref
```

It is the task-lineage bootstrap event, not provider preflight or a UI-only toast.

## Dispatch events

`dispatch_opened` is emitted when the controller commits the new dispatch, prompt request, and NodeSession authority:

```yaml
dispatch_opened:
    dispatch_id: string
    previous_dispatch_id: string | null
    assignment_id: string
    assignment_key: string
    attempt_id: string
    node_key: string
    status: starting
    requested_provider: openclaw | codex | claude
    resolved_provider: openclaw | codex | claude
    workflow_manifest_ref: ref
    reason: >-
      initial_dispatch | external_wait_continuation | watchdog_recovery |
      operator_continue | semantic_retry
```

This event does not mean the provider started or the agent made progress.

Material provider-control readback changes emit exactly:

```yaml
dispatch_control_updated:
    operation: start | stop
    state: queued | attempting | retry_scheduled | succeeded | failed
    provider: openclaw | codex | claude
    attempt: integer
    max_attempts: integer
    next_retry_at: timestamp | null
    last_error_summary: string | null
    reason: initial_dispatch | watchdog_recovery | operator_cancel | shutdown
```

Rules:

- `attempt` is the current provider-control call number
- for `operation = start`, use `watchdog_recovery` only for a watchdog replacement and `initial_dispatch` for every other newly committed dispatch; the more specific lineage cause remains on `dispatch_opened.reason`
- for `operation = stop`, use `watchdog_recovery` for stale replacement, `operator_cancel` for explicit pause or task cancellation, and `shutdown` for lifespan cleanup
- combinations outside those operation-specific mappings are invalid
- retry scheduling emits the next retry time so UI and CLI can show a countdown
- errors are sanitized bounded summaries
- the event is a projection over persisted provider-control readback
- consuming or replaying the event never schedules a retry
- provider-native acceptance, completion, or failure is not another event family

## Plan and checkpoint events

Each accepted changed plan emits:

```yaml
plan_updated:
    attempt_id: string
    revision: integer
    explanation: string | null
    steps:
        - step: string
          status: pending | in_progress | completed
    updated_by_dispatch_id: string
    updated_at: timestamp
```

The payload is bounded because a plan contains at most nine steps. An identical `update_plan` call changes neither revision nor `last_progress_at` and emits no `plan_updated` event.

`checkpoint_recorded` carries:

```yaml
checkpoint_recorded:
    checkpoint_id: string
    checkpoint_kind: progress | terminal
    outcome: green | retry | blocked | null
    summary: string
    next_step: string | null
    blockers: string[]
    risks: string[]
    produced_artifact_refs: ref[]
    transient_refs: ref[]
    checkpoint_path: string
    latest_checkpoint_path: string
```

It does not carry task-memory search hints or raw artifact bodies.

`boundary_accepted` carries the explicit controller transition:

```yaml
boundary_accepted:
    boundary: yield | green | retry | blocked
    latest_checkpoint_path: string
    previous_node_key: string
    next_node_key: string | null
    next_attempt_id: string | null
    resulting_flow_status: >-
      pending | running | blocked | paused | succeeded | cancelled | null
```

It has no provider terminal state or reopen-after-inactivity flag.

## External-wait events

Human-request events carry request identifier, kind, title, status or resolution kind, requester node, timestamps, and actor provenance when terminal. They do not inline complete answered item bodies or structured response payloads.

`human_request_opened` comes from the same transaction that commits the source wait and closes the dispatch. Terminal events come from the source owner's terminal transition. No separate provider-response-ended event exists.

Command-run events use these bounded payloads:

```yaml
command_run_started:
    run_id: string
    state: pending_start | running
    command: string
    description: string
    workdir: string | null
    timeout_seconds: integer | null

command_run_progressed:
    run_id: string
    state: running
    summary: string
    log_ref: string | null
    occurred_at: timestamp

command_run_cancel_requested:
    run_id: string
    state: cancellation_requested
    summary: string
    actor_ref: string | null
    occurred_at: timestamp

command_run_terminal:
    run_id: string
    state: succeeded | failed | timed_out | cancelled
    summary: string
    exit_code: integer | null
    signal: string | null
    log_ref: string | null
    ended_at: timestamp
```

The terminal envelope is used under the matching concrete terminal event type. Raw logs remain behind the dedicated Control API route.

External-wait terminal events are chronology. The controller continues only after rereading the terminal source row, matching waiting cause, task currentness, and legality.

## Task-control events

`task_paused` carries:

```yaml
task_paused:
    pause_reason: paused_by_operator | runtime_recovery_exhausted
    actor_ref: string | null
    summary: string
```

`runtime_recovery_exhausted` is the exact runtime pause reason after provider control or watchdog restart exhaustion.

`task_resumed` records accepted operator continue after legality recomputation. It does not represent a human-request answer, command-run completion, or provider reconnect.

`task_cancelled` records terminal controller cancellation. Later provider output or source callbacks cannot append progression events that reopen the task.

## Structural events

Assignment and structural events remain bounded summaries over their owning controller mutations:

- `child_assignment_staged`
- `child_assignment_committed`
- `structural_revision_adopted`

Their exact assignment and revision payloads remain owned by the controller and definition contracts. Event emission never becomes a second structural commit.

## Consumer behavior

UI, CLI, and support consumers combine:

- source-row reads for current state
- task events for ordered chronology and live updates
- source-specific detail routes for complete human answers and command logs

A consumer may render:

```text
Connecting to Claude - attempt 3/6
Retrying in 4 seconds
```

from `dispatch_control_updated`. It must refresh source state after reconnect or cursor reset and must not infer provider health from the absence of events.

## Required invariants

- event order is per task and append-only
- event replay has no semantic side effects
- every event derives from committed controller source state
- provider events and individual MCP invocations are absent
- no-op plan updates emit no event
- external-wait events do not replace source-row currentness
- retry countdown events never own provider-control scheduling
- cursor reset returns consumers to source-row reads, not event folding

## Validation scenarios

The event contract must prove:

- dispatch, plan, checkpoint, wait, and boundary chronology works with provider stream ingestion disabled
- human-request and command-run terminal events are followed by a new same-attempt `dispatch_opened` only after source legality recomputation
- cursor backfill and SSE resume preserve sequence without logical duplicates
- expired or invalid cursors produce the reset flow
- retry events expose bounded call count and next retry time
- an identical plan update emits nothing
- recovery exhaustion emits failed control readback then `task_paused` with `runtime_recovery_exhausted`
- no hidden provider question or approval event is required for progression

## Related contracts

- [Control API](control-api.md)
- [Runtime records and control state](../architecture/runtime-records-and-control-state.md)
- [Runtime lifecycle and watchdog](../architecture/runtime-lifecycle-and-watchdog.md)
- [Attempt plan and checkpoint contract](../architecture/attempt-plan-and-checkpoint-contract.md)
- [Human request and approval contract](human-request-and-approval-contract.md)
- [Command run and external wait](../architecture/command-run-and-external-wait.md)
- [Capability, security, and audit](capability-security-and-audit.md)
