# Console API And View-Model Contract

Status: Locked target for implementation planning.

This page defines how the console talks to AutoClaw APIs and how controller
payloads become renderable frontend view models.

## API Truth

Implementation must use generated OpenAPI types from
`apps/console/src/api/generated/openapi.ts` for controller-backed payloads,
operation parameters, and enums. Do not hand-maintain duplicate TypeScript API
contracts.

Current console route families:

- `GET /runtime/tasks`
- `GET /runtime/tasks/{task_id}` when a list-adjacent current read is needed
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
- `POST /definitions` only for direct upload flows that explicitly choose that
  lane
- `/authoring/definition-draft-sets/*`
- `POST /tasks/start`

The console must not call or expose callback, node MCP, operator MCP,
observability, or support-file routes as ordinary user-facing product
destinations. Observability refs may appear only when surfaced by
controller-backed read models.

## Generated Type Anchors

Current generated OpenAPI includes these contract anchors:

- `CommandRunState`: `pending_start`, `running`,
  `cancellation_requested`, `succeeded`, `failed`, `timed_out`, `cancelled`
- `HumanRequestKind`: `direction`, `approval`, `input`, `review`
- `DefinitionDraftFileStatus`: `clean`, `modified`, `added`, `stale`,
  `invalid`
- `TaskEventType`: task, dispatch, provider, checkpoint, boundary, child
  assignment, structural revision, human-request, command-run, pause, resume,
  and cancel event families
- `OperationFailureCode`: includes `cursor_reset_required`, stale/currentness,
  missing resource, capability, removed surface, budget, and internal error
  families
- task control writes require `expected_active_flow_revision_id`
- `TaskStartRequest` and `TaskStartResponse` own start request/readback shape

## Shared API Client

The API/config foundation slice must replace the placeholder client with one
shared client layer that owns:

- base URL resolution
- `X-AutoClaw-API-Key`
- optional `X-AutoClaw-Actor-Ref` only when a product contract names the
  current actor source
- JSON request and response handling
- query construction with typed parameter helpers
- generated OpenAPI response typing
- abort signals
- structured error normalization
- pagination helpers
- retry or reconnect policy only where this contract names it

Feature pages may define route-specific hooks, but they must not duplicate base
URL, auth header, JSON, error, pagination, currentness, or SSE parsing logic.

## Authentication

Current console HTTP route families, except health routes, are protected by
`X-AutoClaw-API-Key`.

Rules:

- Send the configured API key only through `X-AutoClaw-API-Key`.
- Do not place the key in query params, route state, localStorage, screenshots,
  evidence logs, fixture names, or rendered UI copy.
- Fixture values for auth assertions must be obvious placeholders.
- Missing API keys should surface backend access/auth errors, not empty data.

## SSE Transport Decision

Decision: initial Task Detail implementation must use a fetch-based SSE
transport in the shared API layer, not native `EventSource`.

Reason: `GET /control/tasks/{task_id}/events/stream` is protected by
`X-AutoClaw-API-Key`, and native browser `EventSource` cannot send arbitrary
request headers. The current `src/api/sse.ts` helper only builds a URL and is
not sufficient for a protected browser stream.

Required behavior:

- Open the stream through `fetch` with `Accept: text/event-stream` and
  `X-AutoClaw-API-Key`.
- Send `cursor=<event_id>` when resuming from a processed event id.
- Parse SSE frames incrementally from the response body.
- Treat `id:` as the controller `event_id`.
- Dedupe strictly by `event_id`.
- Preserve controller `event_seq` ordering when backfill and live events merge.
- Reconnect only from the last processed durable cursor.
- On `410 Gone` with `cursor_reset_required`, run the reset path: task read,
  snapshot, trace, event backfill as needed, then reconnect without the stale
  cursor.
- Abort the stream on route change, task id change, explicit refresh reset, or
  page unmount.
- Integration tests must prove API key header forwarding, frame parsing,
  dedupe, abort, reconnect, and cursor reset behavior.

Native `EventSource` remains blocked unless a later backend/API contract adds a
safe browser stream auth shape such as same-origin session auth. Query-string
API key auth is not allowed.

## Task Detail Startup

Task Detail must rebuild from REST before claiming live chronology:

1. `GET /control/tasks/{task_id}`
2. `GET /control/tasks/{task_id}/snapshot`
3. `GET /control/tasks/{task_id}/trace`
4. If `stream_head_event_id` exists, read
   `GET /control/tasks/{task_id}/events?through_event_id=<stream_head_event_id>`
   for history through that anchor.
5. Connect to SSE with `cursor=<stream_head_event_id>` after history through
   the anchor is processed.

If no bootstrap anchor exists, the page may connect without a cursor and label
the stream as live-only from that point forward. Snapshot and trace are current
read models, not substitutes for event backfill.

## Error Normalization

The shared client must normalize these failure families into one renderable
frontend error shape:

- AutoClaw `OperationFailure` style bodies when a response contains `code`,
  `summary`, `is_retryable`, or `suggested_next_step`
- FastAPI `HTTPValidationError` bodies with `detail[]`
- authentication and permission failures
- stale or illegal-state failures, including stale flow revision and stale
  human-request resolution
- `cursor_reset_required`
- missing resources
- network errors, aborts, and non-JSON or empty error bodies

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
    readonly source:
        "operation_failure" | "validation" | "http" | "network" | "abort";
}
```

Action pages must render stale/currentness conflicts as action failures that
preserve user context and request a reread. They must not silently replay the
action or clear local work.

## View-Model Boundary

Mappers must translate generated snake_case payloads into explicit camelCase
render models near the owning feature or shared API boundary. Do not pass raw
generated objects through arbitrary component trees.

Required mapper families:

- task list rows
- task detail header, graph nodes, event rows, selected detail, and action
  state
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
- Store source ids, refs, and currentness tokens even if default UI hides them.
- Do not derive unsupported counts, waiting causes, progress, launch readiness,
  author identity, or draft status.
- Keep UI labels and grouping out of API contracts.

## Pagination And Filtering

Cursor routes must be modeled as cursor routes:

- Use `next_cursor` as the only load-more continuation.
- Do not show total pages, fake counts, or page numbers unless the route later
  exposes total-count truth.
- Preserve active query, filter, sort, selected item, and current route context
  across load more, refresh, and stale detail rereads.

## Currentness And Actions

- Task pause, continue, and cancel require the latest
  `expected_active_flow_revision_id` from the current task read.
- Human-request resolution is legal only for the current open request id.
- Command-run cancel must target the current run id and respect controller-run
  state.
- Draft-set apply, reset, rematerialize-current, and task start must preserve
  their owning currentness and stale semantics.
- Draft-set truth does not become stored registry truth until apply succeeds.

The UI must reread current truth before retrying stale actions. It must not
infer currentness from local route params, timestamps, logs, or support files.

## Fixture Contract

Fixtures must be OpenAPI-shaped at the API boundary and scenario-shaped at the
test boundary.

Required scenario families are defined in
[Validation and evidence](validation-and-evidence.md). Fixtures may contain raw
controller-like fields, but component tests should consume view models when
testing pure presentation components.
