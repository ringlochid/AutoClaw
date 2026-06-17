# Operator UI API and event stream

Status: Target

This page defines the Vnext operator-facing read, control, and realtime event contract.

## Core rule

REST is the canonical snapshot and query surface.

SSE is the canonical live operator event stream.

WebSocket may exist later, but it must remain a transport alternative over the same controller-owned event model rather than a separate truth lane.

## Canonical read and control families

Vnext operator-facing route families are:

- `GET /runtime/tasks/{task_id}`
- `GET /operator/tasks/{task_id}/snapshot`
- `GET /operator/tasks/{task_id}/trace`
- `GET /operator/tasks/{task_id}/events`
- `GET /operator/tasks/{task_id}/pending-requests`
- `GET /operator/tasks/{task_id}/async-jobs`
- `GET /operator/tasks/{task_id}/events/stream`
- `POST /runtime/tasks/{task_id}/pause`
- `POST /runtime/tasks/{task_id}/continue`
- `POST /runtime/tasks/{task_id}/cancel`
- `POST /operator/tasks/{task_id}/pending-requests/{request_id}/resolve`
- `POST /operator/tasks/{task_id}/async-jobs/{job_id}/cancel`

Rules:

- `continue` remains pause-resume only
- human-request resolution is a dedicated control surface and must not be tunneled through `continue`
- async-job cancellation is a dedicated control surface and must not be represented as generic cancel of the whole task unless that is the actual intent

## Event record shape

The canonical persisted operator event shape is:

```yaml
operator_event:
  event_id: string
  event_seq: integer
  task_id: string
  event_type: string
  event_source: controller | operator | provider | adapter
  occurred_at: timestamp
  flow_revision_id: string | null
  dispatch_id: string | null
  attempt_id: string | null
  node_key: string | null
  payload: object
  prev_event_hash: string | null
  event_hash: string
```

Rules:

- `event_id` is stable and opaque
- `event_id` is the dedupe key
- `event_seq` is the controller-owned order key inside the task stream
- `occurred_at` is controller commit time for the persisted record
- adapter or provider timestamps may survive inside `payload` as secondary evidence only
- `event_hash` and `prev_event_hash` form the tamper-evident chain required by the capability, security, and audit contract
- `event_hash` is computed over the canonical serialized event record with `event_hash` excluded and `prev_event_hash` included

## SSE contract

The canonical live stream is:

- `GET /operator/tasks/{task_id}/events/stream`

Rules:

- SSE `id:` must equal the persisted `event_id`
- clients may resume by sending either `cursor=<event_id>` or `Last-Event-ID: <event_id>`
- if both are present and differ, the request must fail
- replay returns only events strictly after the supplied cursor
- replay order is ascending `event_seq` for that task stream
- dedupe is by stable `event_id`, never by timestamp, provider sequence, or client-local arrival order

## Cursor and replay semantics

`GET /operator/tasks/{task_id}/events` and the SSE stream both use the same opaque cursor contract.

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

1. `GET /runtime/tasks/{task_id}`
2. `GET /operator/tasks/{task_id}/snapshot`
3. `GET /operator/tasks/{task_id}/trace`
4. reconnect to the SSE stream without the stale cursor

## Minimum event families

The operator event stream must include these families:

- `task_started`
- `dispatch_opened`
- `checkpoint_recorded`
- `boundary_accepted`
- `child_assignment_staged`
- `child_assignment_committed`
- `provider_event_normalized`
- `human_request_opened`
- `human_request_resolved`
- `human_request_timed_out`
- `human_request_cancelled`
- `human_request_superseded`
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

## Human request UI behavior

When the UI receives `human_request_opened`, it should surface the request as an active operator work item.

Expected behavior:

- show a browser notification when notification permission is available
- open a popup, modal, drawer, or equivalent focused request surface
- render the request kind, title, summary, requester node, risk level, options, recommended option, freeform-answer affordance, expected effect, timeout/default behavior, evidence refs, and suggested human instruction
- submit typed resolution through `POST /operator/tasks/{task_id}/pending-requests/{request_id}/resolve`
- keep listening to the event stream for cancellation, timeout, supersession, or resolution from another operator surface

The UI may provide operator convenience summaries, but it must not infer hidden truth from support files or local UI state.

## Support-file boundary

Support files may still exist for deep observability, but the operator event stream must not rely on clients parsing support files to reconstruct ordinary task history.

Rules:

- support files remain support-only
- the operator event stream is the canonical live history for UI replay
- when the stream and a support file disagree, controller-owned persisted event records win

## Related contracts

- [Controller contract and resumable execution](../architecture/controller-contract-and-resumable-execution.md)
- [Human request and approval contract](human-request-and-approval-contract.md)
- [Async job and long-running boundary](../architecture/async-job-and-long-running-boundary.md)
- [Capability, security, and audit](capability-security-and-audit.md)
