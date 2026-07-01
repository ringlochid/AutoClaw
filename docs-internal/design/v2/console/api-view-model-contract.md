# Console API And View-Model Contract

Date: 2026-06-30

This document locks the frontend API boundary. Keep backend normalization and
view-model mapping outside page components where the current source already has
shared boundaries.

## Backend Authority

The authoritative route map is
`docs/reference/api/api-surface-and-route-map.md`, with generated OpenAPI types
used as the TypeScript source for schema shape. Backend/OpenAPI truth wins for
schemas, routes, action legality, auth, currentness, and state names.

Protected console requests use `X-AutoClaw-API-Key`. Backend schema wins over
visual mock data when fields, states, route names, validation shape, or action
legality conflict with design examples.

## Current Source Surfaces

- `apps/console/src/app/config.ts`: frontend runtime config, API base URL, and
  API key normalization.
- `apps/console/src/api/client.ts`: JSON request helper, API-key header,
  route resolution, cursor helpers, and normalized errors.
- `apps/console/src/api/routes.ts`: typed route helpers for runtime, control,
  definition, authoring, and task-start routes.
- `apps/console/src/api/sse.ts`: fetch-based SSE/event stream handling with
  API-key header, frame parsing, ordering/deduplication, cursor reset,
  reconnect, abort, and invalid-event behavior.
- `apps/console/src/api/view-models.ts`: page-facing models for tasks, task
  events, human requests, command runs, definitions, draft sets, and task-start
  results.
- `apps/console/src/mocks/handlers.ts` and `apps/console/tests/fixtures/`:
  local fixture and MSW contract surfaces.
- `apps/console/tests/integration/`: API and page integration contract tests.

Older docs that describe `sse.ts` as only a URL helper or mocks/tests as empty
are stale and must not guide implementation.

## Error And Validation Shape

The client boundary must normalize:

- backend operation failures;
- FastAPI/Pydantic validation responses;
- HTTP status errors;
- network errors;
- aborts;
- cursor reset responses;
- malformed or invalid SSE/event payloads.

Pages should render mapped error views and recovery actions rather than parsing
raw backend error bodies inline.

## Route Boundaries By Page

- Tasks: runtime task list route.
- Task Detail: runtime task detail, control snapshot, trace, event list, event
  stream, and pause/continue/cancel routes.
- Human Requests: task-scoped list and resolve routes.
- Command Runs: task-scoped list, detail, log, and cancel routes.
- Definitions: per-kind definition list, detail, and version-history routes.
- Task Start: workflow definition read routes plus `POST /tasks/start`.
- Definition Editor: authoring draft-set routes.

No current route map or OpenAPI evidence supports `/console/config`. Runtime
config remains frontend environment driven unless backend docs add a route.

## View-Model Rules

- Convert backend records into stable page models in shared mappers or
  feature data/model layers, not deep inside JSX.
- Preserve backend state names in data and only map to display copy at the
  presentation boundary.
- Do not add fields such as counts, ETAs, progress, or support-file truth unless
  backend schema exposes them.
- Cursor/reset semantics must remain explicit to the page state machine.
- Currentness tokens and flow revision ids must be kept close to action
  legality and cannot be guessed from stale snapshots.

## Fixture Rules

Fixtures may represent backend states and errors that are defined by OpenAPI or
route docs. They may not introduce design-only fields as product truth.

Required fixture coverage by release:

- API key present/missing behavior.
- Tasks list states.
- Task Detail snapshot, trace, event list, stream, cursor reset, and actions.
- Human-request kind matrix and resolve outcomes.
- Command-run state matrix, logs, and cancel outcomes.
- Definition kind matrix and version history.
- Task-start validation and success outcomes.
- Draft-set authoring lifecycle, validation, preview, apply, reset, and
  rematerialize outcomes.
