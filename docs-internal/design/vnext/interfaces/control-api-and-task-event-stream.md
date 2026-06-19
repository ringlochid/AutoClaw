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
- `GET /control/tasks/{task_id}/async-jobs`
- `GET /control/tasks/{task_id}/events/stream`
- `POST /control/tasks/{task_id}/pause`
- `POST /control/tasks/{task_id}/continue`
- `POST /control/tasks/{task_id}/cancel`
- `POST /control/tasks/{task_id}/human-requests/{request_id}/resolve`
- `POST /control/tasks/{task_id}/async-jobs/{job_id}/cancel`

Rules:

- `continue` remains pause-resume only
- human-request resolution is a dedicated control surface and must not be tunneled through `continue`
- async-job cancellation is a dedicated control surface and must not be represented as generic cancel of the whole task unless that is the actual intent
- V1 `/operator/...` compatibility aliases, if retained, must map onto the same controller behavior and must not define separate route semantics

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

## SSE contract

The canonical live stream is:

- `GET /control/tasks/{task_id}/events/stream`

Rules:

- SSE `id:` must equal the persisted `event_id`
- clients keep the SSE connection open while they want live task updates
- clients may resume by sending either `cursor=<event_id>` or `Last-Event-ID: <event_id>`
- if both are present and differ, the request must fail
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

## Minimum event families

The task event stream must include these families:

- `task_started`
- `dispatch_opened`
- `checkpoint_recorded`
- `boundary_accepted`
- `child_assignment_staged`
- `child_assignment_committed`
- `capability_denied`
- `provider_event_normalized`
- `human_request_opened`
- `human_request_resolved`
- `human_request_timed_out`
- `human_request_cancelled`
- `async_job_started`
- `async_job_progressed`
- `async_job_succeeded`
- `async_job_failed`
- `async_job_timed_out`
- `async_job_cancelled`
- `task_paused`
- `task_resumed`
- `task_cancelled`

Progressive UI rendering may group these families visually, but it must not merge or reinterpret them as different controller events.

## Capability-denied event payload

When the controller emits `capability_denied`, the payload should include:

- the denied capability family and concrete target, for example `human_request.review` or `async_job`
- the attempted action kind
- the stable explanation string
- the current source basis for the deny or restriction
- the next legal action when one exists
- the current node or dispatch context needed for UI inspection and audit

The UI and API must not reconstruct these fields from prompt text, missing tools, or local heuristics.

## Human request UI behavior

When the UI receives `human_request_opened`, it should surface the request as an active control-plane work item.

Expected behavior:

- show a browser notification when notification permission is available
- open a popup, modal, drawer, or equivalent focused request surface, or reveal the selected human-request pane in the task-detail view
- render the request kind, title, summary, requester node, item count, active item prompt, active item options, active item recommendation, freeform-answer affordance, timeout/default behavior, evidence refs, and suggested human instruction
- when a request has multiple items, render compact previous and next controls so the human can move through item-scoped prompts and responses
- submit typed resolution through `POST /control/tasks/{task_id}/human-requests/{request_id}/resolve`
- keep listening to the task event stream for cancellation, timeout, or resolution from another control surface

The UI may provide convenience summaries, but it must not infer hidden truth from support files or local UI state.

## Async job UI behavior

The UI may treat async jobs as a sibling selectable surface beside execution, not as a permanently dense inline panel inside the execution thread.

Rules:

- show job state, latest summary, logs, and artifact refs when present
- render `async_job_progressed` as a textual stage or progress update when controller-owned progress detail exists
- do not assume percent complete, ETA, elapsed time, or metrics dashboards unless later controller contracts add those fields explicitly
- do not fabricate progress rings or runtime counters from local UI heuristics

## Async-job event payloads

The controller should emit bounded async-job event payloads that mirror controller-owned job truth.

Minimum payload expectations are:

- `async_job_started`: `job_id`, `job_kind`, `title`, `summary`, `requester_node`, `state`
- `async_job_progressed`: `job_id`, `progress_seq`, `summary`, `detail`, `log_ref`, `state`
- `async_job_succeeded | async_job_failed | async_job_timed_out | async_job_cancelled`: `job_id`, `state`, `termination_reason`, `summary`, `detail`, `exit_code`, `signal`, `artifact_refs`, `log_refs`

Rules:

- `summary` is the compact controller explanation, not a raw log slice
- command-like jobs should expose `exit_code` and `signal` through terminal events when those fields exist
- large raw outputs should be surfaced by ref rather than copied into every event payload

## Async job read semantics

`GET /control/tasks/{task_id}/async-jobs` and any later per-job detail reads should expose controller truth for:

- job id and state
- job kind, title, summary, and requester node
- command summary and launch ref when present
- created, started, and ended timestamps
- declared timeout and output contract
- normalized result summary
- latest textual progress or stage summary when present
- terminal termination reason plus exit code or signal when present
- small typed output payload when present
- artifact refs and log refs
- cancellation, timeout, or failure provenance when relevant

Rules:

- the async-job list row should be derivable from controller fields such as `title`, `summary`, `state`, and latest progress or terminal summary
- full raw result bodies or large logs may be linked by ref instead of inlined into the control response
- inline control responses must not pretend that missing raw result bytes mean missing controller truth

## Support-file boundary

Support files may still exist for deep observability, but the task event stream must not rely on clients parsing support files to reconstruct ordinary task history.

Rules:

- support files remain support-only
- the task event stream is the canonical live history for UI replay
- when the stream and a support file disagree, controller-owned task events win for event chronology and controller source rows win for current task truth

## Related contracts

- [Controller contract and resumable execution](../architecture/controller-contract-and-resumable-execution.md)
- [Human request and approval contract](human-request-and-approval-contract.md)
- [Async job and long-running boundary](../architecture/async-job-and-long-running-boundary.md)
- [Capability, security, and audit](capability-security-and-audit.md)
- [Control UI runtime and authoring surfaces](control-ui-runtime-and-authoring-surfaces.md)
