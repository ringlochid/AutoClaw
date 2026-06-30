# Console Ambiguity And Debt Log

Status: Locked target for implementation planning.

This page records unresolved items from audit and planning and locks how each
one is resolved, routed, or blocked for implementation.

## Decision Table

| Item                                                  | Decision or route                                                                                                                                                      | Block status                                                                                                 | Exit criteria                                                                                                                            |
| ----------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Console docs lock                                     | This directory is rewritten against the current source audit and delivery plan.                                                                                        | Blocks implementation until strict planning review accepts the docs.                                         | `review_planning_contracts` accepts the plan/docs as implementation-ready or routes exact gaps.                                          |
| Placeholder page implementations                      | All seven pages are required implementation targets; current route files are placeholders only.                                                                        | Blocks product release.                                                                                      | Each page is API-backed, fixture-backed, browser-verified, reviewed, and documented in evidence.                                         |
| Task Detail SSE browser auth                          | Use fetch-based SSE with `X-AutoClaw-API-Key` in the shared API layer. Native `EventSource` is blocked for protected streams.                                          | Blocks Task Detail/SSE closure until foundation implements and tests fetch streaming.                        | API foundation proves header auth, frame parsing, cursor resume, dedupe, abort, reconnect, and `cursor_reset_required` reset with tests. |
| Runtime config and `/console/config`                  | Initial console uses centralized Vite env config. Do not call `/console/config` until backend route and API truth exist.                                               | Does not block initial page slices; blocks same-origin runtime-config deployment if required before release. | Either release accepts env-based config, or backend/API adds `/console/config` and console consumes it through the shared config owner.  |
| Empty MSW/integration fixture lanes                   | Foundation owns MSW setup, fixture families, and meaningful integration tests.                                                                                         | Blocks API-backed page closure.                                                                              | `make console-test-integration` runs non-empty tests covering shared API behavior and fixture conventions.                               |
| Empty visual fixture lane                             | Page slices own screenshots and visual evidence for required states; release review owns suite evidence index.                                                         | Blocks page release readiness when visual parity is in scope.                                                | Desktop and narrow screenshots or browser notes exist for required states and design anchors.                                            |
| Task Detail visual anchor caveat                      | `task-detail.png` is not trusted; referenced last-known-good JPEG is absent. Use semantic docs, HTML, modal PNG, and fresh capture.                                    | Blocks final Task Detail visual release readiness, not semantic implementation start.                        | Fresh promoted Task Detail capture or explicit visual-review replacement anchor is recorded.                                             |
| OperationFailure and FastAPI validation normalization | Foundation must normalize OperationFailure-style bodies, `HTTPValidationError`, auth, stale, cursor reset, network, abort, and non-JSON failures.                      | Blocks all API-backed page slices from closing.                                                              | Shared `ConsoleErrorView` or equivalent is implemented and covered by unit/integration tests.                                            |
| Repo-local task-compose YAML content                  | Current repo-local `references/frontend/task-compose` content is absent or empty for launch purposes. Do not route implementation through nonexistent repo-local YAML. | Blocks implementation launch if still unresolved at launch time.                                             | Launch owner names the current Orin draft-pack path or writes/reviews a repo-local compose bundle deliberately.                          |
| Orin draft-pack currentness                           | Current launch pointer is Orin's draft pack under `/home/ubuntu/.openclaw/workspaces/orin/autoclaw/drafts/`.                                                           | Blocks implementation launch until inspected/refreshed by launch owner.                                      | Launch-readiness note names exact compose/draft paths and confirms they cite accepted plan/docs.                                         |
| Live registry currentness                             | Verify current frontend workflows, roles, and policies through approved registry path before launching implementation tasks.                                           | Blocks implementation launch.                                                                                | Launch-readiness notes name current registry revisions or route upload/refresh before start.                                             |
| Current/v1 authoring-route summary omission           | Treat as docs drift. Use route map, routers, generated OpenAPI, and V2 authoring contract as current route truth.                                                      | Nonblocking for frontend implementation.                                                                     | Optional current/v1 cleanup may add `/authoring/*`; implementation does not wait.                                                        |

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
surfaces, server-side previews, metrics, support-file currentness, or
controller-owned currentness tokens.

## Implementation Dispatch Blockers

Implementation should not launch until these have either exited or been
accepted by strict planning review as nonblocking for a named first slice:

- planning/contract review accepts the rewritten delivery plan and this docs
  set
- launch owner verifies or refreshes the Orin draft pack or explicitly authors
  a reviewed repo-local compose bundle
- approved registry path names current frontend workflow, role, and policy
  revisions or routes upload/refresh

API-backed page closure remains blocked until the foundation slice implements:

- shared API/config/error client
- fetch-based SSE with API-key auth
- OpenAPI-shaped fixtures and MSW handlers
- non-empty integration tests

Task Detail visual release remains blocked until fresh visual proof exists.

## Handoff To Launch Readiness

A launch-readiness owner must consume:

- this directory
- `references/frontend/frontend_delivery_plan.md`
- the surfaced source audit artifact
- `references/frontend/autoclaw-launch-plan.md`

It must publish a launch-readiness note under:

```text
/home/ubuntu/leo/projects/autoclaw/tmp/autoclaw-frontend/full-delivery/00-launch-readiness/
```

That note must name exact compose/draft paths, registry currentness result,
blockers, and the implementation slice that may safely start first.
