# AutoClaw Console Contracts

Status: Target

This directory locks the V2 AutoClaw console frontend contracts that later
implementation slices must consume before touching `apps/console/**`.

The console is a React/Vite/TypeScript implementation over controller-owned
AutoClaw truth. It must not invent runtime state, action legality, metrics,
route families, or draft authoring semantics that the backend and current
contracts do not expose.

## Source Order

Use this order when implementing or reviewing a console slice:

1. Controller-owned API truth: FastAPI routers, generated OpenAPI types in
   `apps/console/src/api/generated/openapi.ts`, and
   `docs/reference/api/api-surface-and-route-map.md`.
2. V2 target contracts under `docs-internal/design/v2/interfaces/**` and
   `docs-internal/design/v2/architecture/**`.
3. Current shipped contrast under `docs-internal/current/v1/**` only when it
   does not conflict with fresher route map, router, or OpenAPI truth.
4. Design references under `references/frontend_design/**` and
   `/home/ubuntu/leo/design/autoclaw-v2-ui/**` for visual language,
   navigation, page-state shape, density, and interaction cadence.
5. Existing `apps/console/**` implementation patterns for React, routing,
   component extraction, tokens, testing, and local code organization.

External design artifacts are visual, state, and interaction anchors only.
They do not override controller route names, payload fields, currentness
tokens, action legality, authentication, or persistence truth.

## Contract Inventory

- [Feature behavior](feature-behavior.md) owns page workflows, visible states,
  legal actions, forbidden UI states, and page-specific behavior.
- [API and view-model contract](api-view-model-contract.md) owns route usage,
  generated OpenAPI consumption, API client responsibilities, view-model mapper
  boundaries, error normalization, SSE, pagination, and currentness handling.
- [Component system](component-system.md) owns shell, primitive, layout,
  responsive, accessibility, token, and design-reference rules.
- [Environment and runtime config](environment-and-runtime-config.md) owns
  environment variables, API base URL, API key handling, `/console/config`
  status, same-origin assumptions, and secret handling.
- [Validation and evidence](validation-and-evidence.md) owns fixture lanes,
  commands, browser/manual evidence, visual parity, accessibility checks, and
  release evidence indexing.
- [Ambiguity and debt log](ambiguity-and-debt-log.md) records every routed or
  resolved planning ambiguity that must not be rediscovered inside
  implementation work.

## Page And Route Inventory

| Page | App route | Primary backend surfaces |
| --- | --- | --- |
| Tasks | `/tasks` | `GET /runtime/tasks` |
| Task Detail | `/tasks/:taskId` | `GET /control/tasks/{task_id}`, snapshot, trace, events, SSE, pause, continue, cancel |
| Human Requests | `/tasks/:taskId/human-requests` | `GET /control/tasks/{task_id}/human-requests`, resolve |
| Command Runs | `/tasks/:taskId/command-runs` | command-run list, detail, log, cancel control routes |
| Definitions | `/definitions` | `GET /definitions/roles`, policies, workflows, detail, versions |
| Definition Editor | `/definitions/editor` | `/authoring/definition-draft-sets/*`, plus stored definition reads when needed |
| Task Start | `/task-start` | workflow stored reads and `POST /tasks/start` |

`Tasks` is the only runtime entrypoint. `Task Detail`, `Human Requests`, and
`Command Runs` are task-scoped siblings beneath `Tasks`. `Definitions`,
`Definition Editor`, and `Task Start` are authoring surfaces and stay outside
task-scoped runtime breadcrumbs.

## Implementation Boundary

The locked docs do not implement product frontend code. Later slices may edit
`apps/console/**` only after consuming these docs and refreshed task-compose
launches.

Implementation slices must preserve these boundaries:

- `apps/console/src/api/**` owns base URL resolution, API key headers, SSE
  transport, generated OpenAPI consumption, structured error normalization,
  and query construction.
- Feature folders own page orchestration, mappers, hooks, reducers, and
  page-specific components for their route family.
- Shared components own repeated shell, list, disclosure, dialog, form, chip,
  tab, status, and state patterns only after a second real use appears or the
  pattern is clearly cross-page from this contract.
- View models translate controller snake_case payloads into explicit camelCase
  render nouns at feature or shared API boundaries. Raw controller payloads
  must not be passed through component trees as generic objects.
- Fixture and MSW handlers are implementation proof surfaces, not controller
  truth. They must stay OpenAPI-shaped and scenario-named.

## Launch Readiness Rules

No implementation task-compose launch is final until `draft_frontend_launches`
refreshes it against this directory and the delivery plan. The current
`references/frontend/task-compose/*.yaml` files are draft material only.

Before launching implementation slices, verify through the approved registry
path that the live controller registry has current revisions for the frontend
slice workflows and roles named by the refreshed compose files.

## Non-Goals

The console must not expose:

- a standalone runtime `Overview` page
- user-facing `Task Control Suite` labels
- generic chat-style human request resolution
- cross-task command-run dashboards
- support-file-derived currentness
- fake request counts, run counts, progress percentages, ETAs, or metrics
- draft-only task launch, unsaved definition execution, or browser-owned
  registry truth
