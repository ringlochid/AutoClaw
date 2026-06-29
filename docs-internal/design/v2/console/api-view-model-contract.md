# Console API And View-Model Contract

Status: Target

This page locks how the console talks to AutoClaw APIs and how controller
payloads become renderable frontend view models.

## API Truth

Implementation must use generated OpenAPI types from
`apps/console/src/api/generated/openapi.ts` for controller-backed payloads and
operation parameters. Do not hand-maintain duplicate TypeScript API contracts.

The current route families for the console are:

- `GET /runtime/tasks`
- `GET /control/tasks/{task_id}`
- `GET /control/tasks/{task_id}/snapshot`
- `GET /control/tasks/{task_id}/trace`
- `GET /control/tasks/{task_id}/events`
- `GET /control/tasks/{task_id}/events/stream`
- `POST /control/tasks/{task_id}/pause`
- `POST /control/tasks/{task_id}/continue`
- `POST /control/tasks/{task_id}/cancel`
- `GET /control/tasks/{task_id}/human-requests`
- `POST /control/tasks/{task_id}/human-requests/{request_id}/resolve`
- `GET /control/tasks/{task_id}/command-runs`
- `GET /control/tasks/{task_id}/command-runs/{run_id}`
- `GET /control/tasks/{task_id}/command-runs/{run_id}/log`
- `POST /control/tasks/{task_id}/command-runs/{run_id}/cancel`
- `GET /definitions/roles`
- `GET /definitions/policies`
- `GET /definitions/workflows`
- `GET /definitions/{kind}/{key}`
- `GET /definitions/{kind}/{key}/versions`
- `POST /definitions`
- `/authoring/definition-draft-sets/*`
- `POST /tasks/start`

The console must not call or expose callback, node MCP, or observability routes
as ordinary user-facing product surfaces. Observability refs may appear only as
controller-backed refs when surfaced by read models.

## Shared API Client

The foundation slice must replace the placeholder client with one shared client
layer that owns:

- base URL resolution
- `X-AutoClaw-API-Key`
- optional `X-AutoClaw-Actor-Ref` only where the shipped operation supports it
- JSON request/response handling
- query construction with typed parameter helpers
- generated OpenAPI response typing
- abort signals
- structured error normalization
- retry or reconnect policy only where the contract names it

Feature pages may define route-specific hooks, but they must not duplicate base
URL, auth header, JSON, error, pagination, currentness, or SSE parsing logic.

## Authentication

Current console HTTP routes are protected by `X-AutoClaw-API-Key` except health.
The browser console uses the configured API key in the shared API client.

Do not put API keys in route query params, localStorage, screenshots, evidence
logs, fixture names, or rendered UI copy. Test fixtures must use placeholder
values only.

## SSE Transport Decision

Decision: initial Task Detail implementation must use a fetch-based SSE
transport in the shared API layer, not native `EventSource`.

Reason: the current stream route is protected by `X-AutoClaw-API-Key`, and
native browser `EventSource` cannot send arbitrary request headers. The current
`src/api/sse.ts` helper only builds a URL and is not sufficient for a protected
browser stream.

Required behavior:

- Open `GET /control/tasks/{task_id}/events/stream` through `fetch` with
  `Accept: text/event-stream` and `X-AutoClaw-API-Key`.
- Send `cursor=<event_id>` when resuming from a processed event id.
- Parse SSE frames incrementally from the response body.
- Treat `id:` as the controller `event_id`.
- Dedupe strictly by `event_id`.
- Preserve controller `event_seq` ordering when backfill and live events merge.
- Reconnect only from the last processed durable cursor.
- On `410 Gone` with `cursor_reset_required`, run the reset path: task read,
  snapshot, trace, then reconnect without the stale cursor.
- Abort the stream on route change, task id change, explicit refresh reset, or
  page unmount.
- Integration tests must prove that the API key header is sent and that stream
  chunks parse correctly.

Native `EventSource` remains blocked unless a later backend/API contract adds a
safe browser stream auth shape such as same-origin session auth. Query-string
API key auth is not allowed by this contract.

## Task Detail Startup

The Task Detail page must rebuild from REST before claiming live chronology:

1. `GET /control/tasks/{task_id}`
2. `GET /control/tasks/{task_id}/snapshot`
3. `GET /control/tasks/{task_id}/trace`
4. If `stream_head_event_id` exists, read
   `GET /control/tasks/{task_id}/events?through_event_id=<stream_head_event_id>`
   for backfill.
5. Connect to SSE with `cursor=<stream_head_event_id>` after history through
   that anchor is processed.

If no bootstrap anchor exists, the page may connect without a cursor and label
the stream as live-only from that point forward.

## Error Normalization

The shared client must normalize these failure families into one renderable
frontend error shape:

- AutoClaw `OperationFailure` style bodies when a response contains
  `code`, `summary`, `is_retryable`, or `suggested_next_step`.
- FastAPI `HTTPValidationError` bodies with `detail[]`.
- authentication and permission failures.
- stale or illegal-state failures, including stale flow revision and stale
  human-request resolution.
- `cursor_reset_required`.
- missing resources.
- network errors, aborts, and non-JSON or empty error bodies.

Minimum renderable shape:

```ts
interface ConsoleErrorView {
    readonly code: string;
    readonly title: string;
    readonly summary: string;
    readonly status: number | null;
    readonly isRetryable: boolean;
    readonly suggestedNextStep: string | null;
    readonly fieldErrors: readonly ConsoleFieldError[];
    readonly source: "operation_failure" | "validation" | "http" | "network" | "abort";
}
```

Action pages must render stale/currentness conflicts as action failures that
preserve user context and request a reread; they must not silently replay the
action or clear the user's state.

## View-Model Boundary

Mappers must translate generated snake_case payloads into explicit render
models near the owning feature or shared API boundary. Do not pass raw generated
objects through arbitrary component trees.

Required mapper families:

- task list rows
- task detail header, graph nodes, event rows, selected detail, and action state
- human request queue items, focused item, draft item responses, and terminal
  readback
- command-run rows, detail, log state, and cancel action state
- definition list rows, selected detail, version rows, and authoring pivots
- draft-set summaries, draft file rows, editor state, validation issues,
  preview state, and apply result
- task-start workflow choices, root bindings, preview, and result

Mapper rules:

- Keep controller enum values exact in API-facing state.
- Use camelCase fields in render models.
- Store source ids, refs, and currentness tokens even if the default UI hides
  them.
- Do not derive unsupported counts, waiting causes, progress, launch readiness,
  author identity, or draft status.
- Keep UI labels and grouping out of API contracts.

## Pagination And Filtering

Cursor routes must be modeled as cursor routes:

- Use `next_cursor` as the only load-more continuation.
- Do not show total pages, fake counts, or page numbers unless the route later
  exposes total-count truth.
- Preserve active query, filter, sort, and selected item context across load
  more, refresh, and stale detail rereads.

## Currentness And Actions

Task pause, continue, and cancel require the latest
`expected_active_flow_revision_id` from the current task read. The UI must
reread current task truth before retrying a stale action.

Human-request resolution is legal only for the current open request id. A stale
or terminal request must render terminal readback or conflict state rather than
submitting again.

Command-run cancel must target the current run id and respect controller-backed
run state. The UI must not infer cancellability from local time or log output.

Definition apply, reset, rematerialize-current, and task start must preserve
their owning currentness and stale semantics. Draft-set truth does not become
stored registry truth until apply succeeds.

## Fixture Contract

Fixtures must be OpenAPI-shaped at the API boundary and scenario-shaped at the
test boundary. Required scenario families are defined in
[Validation and evidence](validation-and-evidence.md).

Fixtures may contain raw controller-like fields, but component tests should
consume view models when testing pure presentation components.
