# AutoClaw Console Contracts

Status: Locked target for implementation planning.

This directory is the frontend contract surface for the AutoClaw V2 console.
Implementation workers must read it before touching `apps/console/**`.

The console is a React, TypeScript, Vite, and Tailwind app over
controller-owned AutoClaw truth. It must not invent runtime state, action
legality, metrics, route families, task counts, ETAs, registry currentness,
support-file currentness, or draft authoring semantics that the backend and
current contracts do not expose.

## Source Order

Use this order for every implementation or review slice:

1. Controller/API truth: FastAPI routers, generated OpenAPI types at
   `apps/console/src/api/generated/openapi.ts`, and
   `docs/reference/api/api-surface-and-route-map.md`.
2. Current V2 interface owners:
   `docs-internal/design/v2/interfaces/control-ui-runtime-and-authoring-surfaces.md`,
   `docs-internal/design/v2/interfaces/control-api-and-task-event-stream.md`,
   `docs-internal/design/v2/interfaces/human-request-and-approval-contract.md`,
   `docs-internal/design/v2/interfaces/definition-authoring-api-and-draft-set-contract.md`,
   `docs-internal/design/v2/interfaces/definition-authoring-workbench.md`, and
   `docs-internal/design/v2/architecture/command-run-and-long-running-boundary.md`.
3. This directory for console-specific behavior, API/view-model boundaries,
   components, config, validation, and routed ambiguity.
4. Visual and interaction references under `references/frontend_design/**` and
   `/home/ubuntu/leo/design/autoclaw-v2-ui/**`.
5. Existing `apps/console/**` implementation patterns after the contracts above
   have been consumed.

Design artifacts are visual, state, and interaction anchors only. They do not
override controller route names, payload fields, event names, state values,
currentness tokens, action legality, authentication, or persistence truth.

## Contract Inventory

- [Feature behavior](feature-behavior.md) owns page workflows, visible states,
  legal actions, forbidden UI states, labels, and page-specific behavior.
- [API and view-model contract](api-view-model-contract.md) owns route usage,
  generated OpenAPI consumption, API/SSE client responsibilities, error
  normalization, mappers, pagination, and currentness handling.
- [Component system](component-system.md) owns shell, primitives, responsive
  layout, accessibility, tokens, extraction, and visual-reference rules.
- [Environment and runtime config](environment-and-runtime-config.md) owns
  Vite env configuration, API base URL, API key handling, `/console/config`
  status, same-origin assumptions, and secret handling.
- [Validation and evidence](validation-and-evidence.md) owns command gates,
  fixture lanes, browser/manual proof, visual parity, accessibility checks, and
  release evidence indexing.
- [Ambiguity and debt log](ambiguity-and-debt-log.md) records every resolved,
  routed, blocking, or phase-bounded item that implementation must not
  rediscover or hide.

## Page And Route Inventory

All seven pages are required implementation targets. The current app already
has route placeholders for them, but every page is still a placeholder until it
is API-backed, fixture-backed, browser-verified, and reviewed.

| Page              | App route                       | Primary backend surfaces                                                          |
| ----------------- | ------------------------------- | --------------------------------------------------------------------------------- |
| Tasks             | `/tasks`                        | `GET /runtime/tasks`                                                              |
| Task Detail       | `/tasks/:taskId`                | `/control/tasks/{task_id}`, snapshot, trace, events, SSE, pause, continue, cancel |
| Human Requests    | `/tasks/:taskId/human-requests` | human-request list and resolve control routes                                     |
| Command Runs      | `/tasks/:taskId/command-runs`   | command-run list, detail, log, and cancel control routes                          |
| Definitions       | `/definitions`                  | role, policy, workflow list/detail/version reads                                  |
| Definition Editor | `/definitions/editor`           | `/authoring/definition-draft-sets/*` plus stored definition reads when needed     |
| Task Start        | `/task-start`                   | stored workflow reads and `POST /tasks/start`                                     |

`Tasks` is the only runtime entrypoint. `Task Detail`, `Human Requests`, and
`Command Runs` are task-scoped siblings beneath `Tasks`. `Definitions`,
`Definition Editor`, and `Task Start` are authoring surfaces and stay outside
task-scoped runtime breadcrumbs.

## Current Scaffold Truth

Current safe implementation facts:

- `apps/console` is a Vite/React/TypeScript/Tailwind app.
- `apps/console/src/app/router.tsx` routes all seven required pages plus the
  internal fixture gallery.
- The feature page files render route scaffolds and backing-route labels only.
- `src/api/client.ts` can issue JSON requests and attach
  `X-AutoClaw-API-Key`, but structured error normalization is incomplete.
- `src/api/sse.ts` only builds an event-stream URL and must be replaced by the
  fetch-based protected SSE transport defined here.
- `src/mocks`, `tests/fixtures`, `tests/integration`, and `tests/visual` contain
  only `.gitkeep` files.
- `make console-test-integration` currently passes with no tests because the
  integration lane is empty; this is a blocker, not proof.

## Implementation Boundary

The locked docs do not implement product frontend code. Later implementation
slices may edit `apps/console/**` only after these docs and the accepted
delivery plan are reviewed.

Implementation slices must preserve these ownership boundaries:

- `apps/console/src/api/**` owns base URL resolution, API key headers,
  generated OpenAPI consumption, JSON request handling, fetch-SSE transport,
  query construction, pagination helpers, structured error normalization, and
  reset/reconnect behavior.
- Feature folders own page orchestration, page-specific hooks, reducers,
  mappers, and components for their route family.
- Shared components own repeated shell, list, disclosure, dialog, form, chip,
  tab, status, and state patterns only when they remove real repetition or
  enforce accessibility/action legality.
- View-model mappers translate generated snake_case controller payloads into
  explicit camelCase render nouns near feature or API boundaries.
- Fixture and MSW handlers are proof surfaces. They must stay OpenAPI-shaped at
  the API boundary and scenario-named at the test boundary.

## Launch Readiness Rules

Frontend implementation launch remains blocked until a planning review accepts
the rewritten delivery plan and this locked docs set.

Launch and compose truth for this program is:

```text
/home/ubuntu/.openclaw/workspaces/orin/autoclaw/drafts/frontend-console-v2/README.md
/home/ubuntu/.openclaw/workspaces/orin/autoclaw/drafts/workflows/frontend_console_full_delivery.yaml
/home/ubuntu/.openclaw/workspaces/orin/autoclaw/drafts/task-compose/autoclaw_console_frontend_full_delivery/full-delivery.task-compose.yaml
```

Repo-local `references/frontend/task-compose` content is absent or empty for
launch purposes in the current repo. Do not claim refreshed repo-local
task-compose YAML files exist unless a later launch owner deliberately writes,
reviews, and routes them.

Before launching implementation, a launch/registry owner must verify or refresh
the Orin draft pack and name current live controller registry revisions for the
frontend workflows, roles, and policies. Unknown registry currentness blocks
implementation launch.

## Non-Goals

The console must not expose:

- a standalone runtime `Overview` page
- user-facing `Task Control Suite` labels
- generic chat-style human request resolution
- cross-task command-run dashboards
- support-file-derived currentness
- fake request counts, run counts, child counts, progress percentages, ETAs, or
  dashboard metrics
- draft-only task launch, unsaved definition execution, or browser-owned
  registry truth
