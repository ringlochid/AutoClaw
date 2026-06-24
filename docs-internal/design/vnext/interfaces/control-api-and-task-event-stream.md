# Control API and task event stream

Status: Target

This page defines the Vnext control-plane read, control, and realtime task-event contract.

## Core rule

The control plane is the external task runtime surface for UI clients, human operators, operator agents such as Orin, trusted automation, and audit/debug tooling.

It is not node authority and it is not controller truth by itself.

REST is the canonical snapshot and query surface.

SSE is the canonical live task event stream.

WebSocket may exist later, but it must remain a transport alternative over the same controller-owned task event model rather than a separate truth lane.

## Naming rule

Vnext uses `control` for the external task-control lane and `task_event` for the replayable timeline.

Rules:

- `operator` names a principal or role, not the route lane or persisted event record
- a human operator, Orin, another operator agent, or trusted automation may all use the control lane when authorized
- V1 `/operator` routes or `operator MCP` tools may remain compatibility or parity surfaces, but `/control` is the Vnext canonical API lane
- task events belong to the task timeline, not to a human operator

## Canonical read and control families

Vnext control route families are:

- `GET /control/tasks/{task_id}`
- `GET /control/tasks/{task_id}/snapshot`
- `GET /control/tasks/{task_id}/trace`
- `GET /control/tasks/{task_id}/events`
- `GET /control/tasks/{task_id}/human-requests`
- `GET /control/tasks/{task_id}/command-runs`
- `GET /control/tasks/{task_id}/events/stream`
- `POST /control/tasks/{task_id}/pause`
- `POST /control/tasks/{task_id}/continue`
- `POST /control/tasks/{task_id}/cancel`
- `POST /control/tasks/{task_id}/human-requests/{request_id}/resolve`
- `POST /control/tasks/{task_id}/command-runs/{run_id}/cancel`

Rules:

- `continue` remains pause-resume only
- human-request resolution is a dedicated control surface and must not be tunneled through `continue`
- command-run cancellation is a dedicated control surface and must not be represented as generic cancel of the whole task unless that is the actual intent
- V1 `/operator/...` compatibility aliases, if retained, must map onto the same controller behavior and must not define separate route semantics

## Canonical envelope rule

The Vnext control API must freeze request and response envelopes for the named route families. Route names alone are not enough.

Envelope style should stay consistent with shipped AutoClaw API patterns:

- typed query params for list and read surfaces
- typed request bodies for state-changing writes
- typed response carriers with explicit `items` and `next_cursor` when a route paginates
- controller-minted stale or illegal-state errors rather than ad hoc frontend-only error shapes

## Event record shape

The canonical persisted task event shape is:

```yaml
task_event:
  event_id: string
  event_seq: integer
  task_id: string
  event_type: string
  event_source: controller | control_api | node | provider | adapter
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

- `event_id` is stable and opaque
- `event_id` is the dedupe key
- `event_seq` is the controller-owned order key inside the task stream
- `occurred_at` is controller commit time for the persisted record
- `event_source` identifies the normalized source lane; human or automation identity belongs in `actor_ref` or event provenance, not in the event-family name
- adapter or provider timestamps may survive inside `payload` as secondary evidence only
- `event_hash` and `prev_event_hash` form the tamper-evident chain required by the capability, security, and audit contract
- `event_hash` is computed over the canonical serialized event record with `event_hash` excluded and `prev_event_hash` included
- task events are authoritative for UI replay, audit sequence, and "what changed"; they do not replace controller source rows for currentness or legality

## Event backfill envelope

`GET /control/tasks/{task_id}/events` should expose a typed paginated read:

```yaml
task_event_list_response:
  task_id: string
  items:
    - task_event
  next_cursor: string | null
  through_event_id: string | null
```

Query expectations are:

- `cursor: string | null`
- `limit: integer`
- `through_event_id: string | null`

Rules:

- `items` are returned in ascending `event_seq`
- `cursor` means "start strictly after this event"
- `next_cursor` is opaque to clients
- when `through_event_id` is present, the server must stop the backfill at that controller event even if newer events already exist
- when `through_event_id` is absent, the server may return newer events up to the response-time head
- `through_event_id` is the bootstrap handoff anchor described below; it is not a second dedupe key

## SSE contract

The canonical live stream is:

- `GET /control/tasks/{task_id}/events/stream`

Rules:

- SSE `id:` must equal the persisted `event_id`
- clients keep the SSE connection open while they want live task updates
- clients may resume by sending either `cursor=<event_id>` or `Last-Event-ID: <event_id>`
- if both are present and differ, the request must fail
- opening the SSE stream without a cursor starts a live tail from current controller head; it is not an implicit full-history fetch
- replay returns only events strictly after the supplied cursor
- replay order is ascending `event_seq` for that task stream
- dedupe is by stable `event_id`, never by timestamp, provider sequence, or client-local arrival order

## Cursor and replay semantics

`GET /control/tasks/{task_id}/events` and the SSE stream both use the same opaque cursor contract.

Rules:

- `cursor` points to the last event the client has durably processed
- backfill returns all later persisted events in ascending `event_seq`
- controller order is task-stream `event_seq` order; dispatch-local or provider-local order may appear as secondary fields only
- the controller must not guess or synthesize a new resume point from timestamps when the cursor is missing

If the supplied cursor cannot be resumed safely:

- the server must reject the request with `410 Gone`
- the machine-readable error code must be `cursor_reset_required`
- the client must refetch current task truth through REST, then reconnect without the old cursor

The required reset path is:

1. `GET /control/tasks/{task_id}`
2. `GET /control/tasks/{task_id}/snapshot`
3. `GET /control/tasks/{task_id}/trace`
4. reconnect to the SSE stream without the stale cursor

## Existing-task open and refresh flow

When a UI opens, refreshes, or reopens an already-started task, it should rebuild current state from REST first and treat the SSE stream as the live tail.

`GET /control/tasks/{task_id}/snapshot` should expose one controller-minted bootstrap anchor:

```yaml
stream_head_event_id: string | null
```

This is the latest committed `event_id` reflected by that snapshot read model.

Recommended client flow is:

1. `GET /control/tasks/{task_id}`
2. `GET /control/tasks/{task_id}/snapshot` and record `stream_head_event_id`
3. `GET /control/tasks/{task_id}/trace`
4. if the UI needs prior task chronology, read `GET /control/tasks/{task_id}/events` with `through_event_id=<stream_head_event_id>` rather than trying to infer history from snapshot or trace
5. once the client has durably processed history through that anchor, connect to `GET /control/tasks/{task_id}/events/stream` with `cursor=<stream_head_event_id>`

Rules:

- a fresh open with no bootstrap anchor may connect to SSE without a cursor and treat it as live-only delivery from that point forward
- when `stream_head_event_id` is present, the client should use it as the single handoff point between REST readback and SSE live delivery
- a refresh or reconnect with a durable last processed `event_id` should resume through `cursor` or `Last-Event-ID`
- the client must not claim gap-free chronology across refresh or reopen unless it has either resumed from a durable cursor or backfilled through an explicit `through_event_id` anchor
- the UI may combine REST readback, backfill, and SSE subscription in one startup path, but it must dedupe strictly by `event_id`
- snapshot and trace are current read models, not substitutes for event backfill

## Minimum event families

The task event stream must include these families:

- `task_started`
- `dispatch_opened`
- `provider_resolution_recorded`
- `checkpoint_recorded`
- `boundary_accepted`
- `child_assignment_staged`
- `child_assignment_committed`
- `provider_event_normalized`
- `human_request_opened`
- `human_request_resolved`
- `human_request_timed_out`
- `human_request_cancelled`
- `command_run_started`
- `command_run_progressed`
- `command_run_succeeded`
- `command_run_failed`
- `command_run_timed_out`
- `command_run_cancelled`
- `task_paused`
- `task_resumed`
- `task_cancelled`

Progressive UI rendering may group these families visually, but it must not merge or reinterpret them as different controller events.

## Provider-resolution event payload

When the controller resolves provider preference for a dispatch attempt, it should emit `provider_resolution_recorded`.

Minimum payload expectations are:

- `requested_provider`
- `resolved_provider`
- `dispatch_id`
- `attempt_id`

Rules:

- the event records the requested provider and the provider that actually accepted the attempt
- once the attempt is accepted, later provider changes must not be represented as silent mutation of the same attempt
- fallback detail may stay in support-state or observability lanes until a later contract proves it needs first-class task-event status

## Structured rejection responses

Illegal `human_request` or `command_run` calls should return structured errors from the invoked surface.

Minimum expectations are:

- the rejected capability target, for example `human_request.review` or `command_run`
- a detailed error message
- the next legal action when one exists

Rules:

- rejected special-lane calls do not emit standalone task events in the minimum contract
- the UI and API must not reconstruct deny meaning from prompt text, missing tools, or local heuristics
- provider launch incompatibility, missing MCP transport support, or ordinary node-tool absence still fail or fall back before dispatch acceptance rather than becoming special-lane rejection events

## Human-request read and resolve envelopes

`GET /control/tasks/{task_id}/human-requests` should expose a typed read:

```yaml
human_request_list_response:
  task_id: string
  items:
    - pending_human_request
```

Rules:

- the current open request, when one exists, is represented as the item whose `status` is `open`
- the route may also include terminal request records for the same task when the control surface wants nearby request history
- this route is the canonical request read surface for UI bootstrap and operator inspection

`POST /control/tasks/{task_id}/human-requests/{request_id}/resolve` should expose a typed request and response:

```yaml
human_request_resolve_request:
  resolution_kind: answered | timed_out | cancelled
  item_responses:
    - item_id: string
      selected_option: string | null
      freeform_answer: string | null
      extra_notes: string | null
      response_payload: object | null

human_request_resolve_response:
  task_id: string
  resolution:
    human_request_resolution
```

Rules:

- the resolve request carries only the operator or UI supplied resolution fields; controller-owned fields such as `resolved_at` and `resolved_by_actor_ref` are minted by the server
- the response returns the persisted controller-owned resolution record
- if `request_id` is not the current open request for the task anymore, the write must fail as a structured stale or currentness conflict instead of silently resolving the wrong request
- the client follows ordinary task reread or SSE progression after a successful resolve; the resolve response is not a second live history lane

## Human request UI behavior

When the UI receives `human_request_opened`, it should surface the request as an active control-plane work item.

Expected behavior:

- show a browser notification when notification permission is available
- open a popup, modal, drawer, or equivalent focused request surface, or reveal the selected human-request pane in the task-detail view
- render the request kind, title, summary, requester node, item count, active item prompt, active item options, active item recommendation, freeform-answer affordance, timeout/default behavior, and suggested human instruction
- when a request has multiple items, render compact previous and next controls so the human can move through item-scoped prompts and responses
- submit typed resolution through `POST /control/tasks/{task_id}/human-requests/{request_id}/resolve`
- keep listening to the task event stream for cancellation, timeout, or resolution from another control surface

Rules:

- when a pending request is discovered from initial REST readback or historical event backfill, the UI should surface it as current work without replaying a second browser notification for the same request
- popup or notification behavior is for newly observed live openings after current state has been established, not for every replayed historical `human_request_opened` event
- if a request is already open when the user lands on the task, the UI should route directly to the same request surface without waiting for a new live event

The UI may provide convenience summaries, but it must not infer hidden truth from support files or local UI state.

## Command-run UI behavior

The UI may treat command runs as a sibling selectable surface beside execution, not as a permanently dense inline panel inside the execution thread.

Rules:

- show run state, latest summary, and logs when present
- render `command_run_progressed` as a textual stage or progress update when controller-owned progress detail exists
- do not assume percent complete, ETA, elapsed time, or metrics dashboards unless later controller contracts add those fields explicitly
- do not fabricate progress rings or runtime counters from local UI heuristics

## Command-run event payloads

The controller should emit bounded command-run event payloads that mirror controller-owned run truth.

Minimum payload expectations are:

- `command_run_started`: `run_id`, `command`, `description`, `workdir`, `state`, `timeout_seconds`
- `command_run_progressed`: `run_id`, `summary`, `log_ref`, `occurred_at`, `state`
- `command_run_succeeded | command_run_failed | command_run_timed_out | command_run_cancelled`: `run_id`, `state`, `summary`, `exit_code`, `signal`, `ended_at`, `log_ref`

Rules:

- `summary` is the compact controller explanation, not a raw log slice
- command runs should expose `exit_code` and `signal` through terminal events when those fields exist
- large raw outputs should stay in logs, not inlined into every event payload

## Command-run read semantics

`GET /control/tasks/{task_id}/command-runs` and any later per-run detail reads should expose controller truth for:

- run id and state
- command and description
- workdir when present
- created, started, and ended timestamps
- declared timeout
- latest bounded update when present
- terminal summary
- exit code or signal when present
- log ref when present
- cancellation, timeout, or failure provenance when relevant

Rules:

- the command-run list row should be derivable from controller fields such as `command`, `description`, `state`, and latest or terminal summary
- full logs may be linked by ref instead of inlined into the control response
- inline control responses must not pretend that missing raw log bytes mean missing controller truth

Minimum list and cancel envelopes are:

```yaml
command_run_list_response:
  task_id: string
  items:
    - run_id: string
      state: string
      command: string
      description: string | null
      workdir: string | null
      created_at: timestamp
      started_at: timestamp | null
      ended_at: timestamp | null
      timeout_seconds: integer | null
      summary: string | null
      exit_code: integer | null
      signal: string | null
      log_ref: string | null
  next_cursor: string | null

command_run_cancel_response:
  task_id: string
  run:
    run_id: string
    state: string
    command: string
    description: string | null
    workdir: string | null
    created_at: timestamp
    started_at: timestamp | null
    ended_at: timestamp | null
    timeout_seconds: integer | null
    summary: string | null
    exit_code: integer | null
    signal: string | null
    log_ref: string | null
```

Rules:

- `GET /control/tasks/{task_id}/command-runs` uses typed pagination with `cursor` and `limit`
- `POST /control/tasks/{task_id}/command-runs/{run_id}/cancel` returns the controller-known run record after cancel acceptance
- the cancel response may still show a non-terminal state when cancellation has been accepted but terminal command-run closure has not yet committed

## Support-file boundary

Support files may still exist for deep observability, but the task event stream must not rely on clients parsing support files to reconstruct ordinary task history.

Rules:

- support files remain support-only
- the task event stream is the canonical live history for UI replay
- when the stream and a support file disagree, controller-owned task events win for event chronology and controller source rows win for current task truth

## Related contracts

- [Controller contract and resumable execution](../architecture/controller-contract-and-resumable-execution.md)
- [Human request and approval contract](human-request-and-approval-contract.md)
- [Command run and long-running boundary](../architecture/command-run-and-long-running-boundary.md)
- [Capability, security, and audit](capability-security-and-audit.md)
- [Control UI runtime and authoring surfaces](control-ui-runtime-and-authoring-surfaces.md)
