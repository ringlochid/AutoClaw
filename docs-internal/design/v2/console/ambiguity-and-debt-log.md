# Console Ambiguity And Debt Log

Status: Target

This page records the unresolved items from audit and planning and locks how
each one is resolved, routed, or blocked for implementation.

## Decision Table

| Item | Decision or route | Block status | Exit criteria |
| --- | --- | --- | --- |
| Task Detail SSE browser auth | Use fetch-based SSE with `X-AutoClaw-API-Key` in the shared API layer. Native `EventSource` is blocked for protected streams. | Blocks Task Detail/SSE implementation closure until foundation implements and tests fetch streaming. | API foundation proves header auth, parsing, cursor resume, abort, and `cursor_reset_required` reset with MSW/integration tests. |
| Runtime config and `/console/config` | Initial console uses centralized Vite env config. Do not call `/console/config` until backend route and API truth exist. | Does not block initial page slices; blocks same-origin runtime-config deployment if required before release. | Either release accepts env-based config, or a backend/API prerequisite adds `/console/config` and console consumes it through the shared config owner. |
| Empty MSW/integration fixture lanes | Foundation owns MSW setup, fixture families, and at least one meaningful integration test. | Blocks API-backed page closure until real integration coverage exists. | `make console-test-integration` runs non-empty tests covering shared API behavior and fixture conventions. |
| Empty visual fixture lane | Page slices own screenshots and visual evidence for their states; release review owns suite evidence index. | Blocks page release readiness when visual parity is in scope. | Desktop and narrow screenshots or browser notes exist for required states and design anchors. |
| Task Detail visual anchor caveat | `task-detail.png` is not trusted; referenced last-known-good JPEG is absent. Use semantic docs, HTML, modal PNG, and fresh capture. | Blocks final Task Detail visual release readiness, not semantic implementation start. | Fresh promoted Task Detail capture or explicit visual-review replacement anchor is recorded. |
| OperationFailure and FastAPI validation normalization | Foundation must normalize OperationFailure-style bodies, `HTTPValidationError`, auth, stale, cursor reset, network, and non-JSON failures. | Blocks all API-backed page slices from closing. | Shared `ConsoleErrorView` or equivalent is implemented and covered by unit/integration tests. |
| Stale task-compose drafts | Existing task-compose YAML remains draft material. `draft_frontend_launches` owns refresh after these docs. | Blocks implementation launch. | Refreshed compose bundle cites current docs and delivery plan and is reviewed. |
| Live registry currentness | Verify current frontend workflows/roles/policies through approved registry path before launching implementation tasks. | Blocks implementation launch. | Launch-readiness notes name current registry revisions or route upload/refresh before start. |
| Current/v1 authoring-route summary omission | Treat as docs drift. Use public route map, routers, and generated OpenAPI as current route truth. | Nonblocking for frontend implementation. | Optional current/v1 cleanup may add `/authoring/*` to the omitted summary; implementation does not wait. |

## Standing Debt Policy

Implementation slices may carry only explicit, phase-bounded debt that:

- does not contradict controller route or payload truth
- does not weaken API key or secret handling
- does not hide stale/currentness conflicts
- does not bypass accessibility basics
- does not turn mocks into claimed shipped behavior
- has an owner route and exit condition

Any backend/API prerequisite must be routed as a prerequisite. Frontend slices
must not invent missing routes, payload fields, auth modes, runtime config
surfaces, server-side previews, or controller-owned currentness tokens.

## Handoff To Launch Drafting

`draft_frontend_launches` must consume:

- this directory
- `references/frontend/frontend_delivery_plan.md`
- the surfaced source audit artifact
- `tmp/autoclaw-frontend/00-plan-contract-lock/frontend_contract_docs.md`

It must refresh task-compose files so implementation slices start only after:

- foundation owns API/config/errors/SSE/fixtures
- Task Detail is blocked on the fetch-SSE foundation proof
- page slices cite the correct doc set and visual anchors
- registry currentness is verified or routed
- existing compose draft staleness is removed
