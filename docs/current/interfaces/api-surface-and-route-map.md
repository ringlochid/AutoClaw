# Current API route families and lane map

Status: Current

Last verified: 2026-05-12

This page owns the exact current route families, route nouns, and auth grouping
for the shipped FastAPI surface.

For operator-role meaning and lane authority, see `api-trust-lanes.md`.

## Ownership rule

Use this page for current path families, route nouns, and auth split.

Use `api-trust-lanes.md` for caller authority and the difference between
operator, callback, and controller roles.

## Current route families

Current router families are:

- `health`
- `runtime`
- `operator`
- `callback`
- `observability`

The split is implemented in `apps/api/app/api/router.py`.

## Current health routes

Unauthenticated health routes are:

- `GET /healthz`
- `GET /readyz`

`/readyz` performs a DB ping before returning ready.

## Current operator routes

The standard operator lane is protected by `X-AutoClaw-API-Key` via
`require_api_key`.

Current operator-visible routes are:

- `GET /runtime/tasks`
- `GET /runtime/tasks/{task_id}`
- `POST /runtime/tasks/{task_id}/continue`
- `POST /runtime/tasks/{task_id}/pause`
- `POST /runtime/tasks/{task_id}/cancel`
- `GET /operator/tasks/{task_id}/snapshot`
- `GET /operator/tasks/{task_id}/trace`
- `GET /observability/tasks/{task_id}/delivery-state`
- `GET /observability/tasks/{task_id}/continuity-state`
- `GET /observability/tasks/{task_id}/watchdog-state`
- `GET /observability/tasks/{task_id}/provider-events`

Current query-backed route details include:

- `/runtime/tasks` supports `q`, `limit`, `cursor`, `sort`, and `status`
- `/runtime/tasks/{task_id}/continue|pause|cancel` require
  `expected_active_flow_revision_id`
- `/operator/tasks/{task_id}/trace` supports `scope`, `q`, `limit`, `cursor`,
  and `sort`

## Current callback routes

The callback lane is protected by the live dispatch session key header
`X-Autoclaw-Session-Key`.

Current callback routes are:

- `POST /callback/tasks/{task_id}/checkpoint`
- `POST /callback/tasks/{task_id}/boundary`
- `POST /callback/tasks/{task_id}/tools/{tool_name}`

Current tool names are:

- `assign_child`
- `add_child`
- `update_child`
- `remove_child`
- `release_green`
- `release_blocked`

Callback auth is runtime-bound, not operator-bound:

- the route layer validates the session key against the current live callback
  binding
- stale, revoked, or inactive bindings are rejected
- structural callback tool success for `add_child`, `update_child`, and
  `remove_child` means the stable `_runtime/workflow-manifest.*` reread path
  was refreshed before the final commit completed

## Current route-shape facts

Current shipped route nouns are:

- `/runtime/*`
- `/operator/*`
- `/callback/*`
- `/observability/*`

Current docs must treat these as implementation truth only. They are not the
clean-break redesign surface.

Current code does not ship the older legacy flow, approval, registry, internal,
task-compose-start, or browser-bootstrap route families anymore.

Current code also keeps `require_internal_api_key()` in `app.api.deps`, but no
router currently uses it.

## Minimal example

```text
operator:
  GET  /runtime/tasks
  GET  /runtime/tasks/{task_id}
  POST /runtime/tasks/{task_id}/pause?expected_active_flow_revision_id=...
  GET  /operator/tasks/{task_id}/trace
  GET  /observability/tasks/{task_id}/delivery-state

callback:
  POST /callback/tasks/{task_id}/checkpoint
  POST /callback/tasks/{task_id}/boundary
  POST /callback/tasks/{task_id}/tools/assign_child
```

## Evidence

- inspected code in `apps/api/app/api/router.py`
- inspected code in `apps/api/app/api/routes/health.py`
- inspected code in `apps/api/app/api/routes/runtime.py`
- inspected code in `apps/api/app/api/routes/operator.py`
- inspected code in `apps/api/app/api/routes/callback.py`
- inspected code in `apps/api/app/api/routes/observability.py`
- inspected code in `apps/api/app/api/deps.py`
- inspected code in `apps/api/app/main.py`
- inspected tests in `apps/api/tests/integration/phase3/routes/test_query_contract.py`
- inspected tests in `apps/api/tests/integration/phase3/routes/test_surface_contract.py`

## Related current pages

- `api-trust-lanes.md`
- `../architecture/runtime-control-plane.md`
- `../architecture/runtime-read-models-and-operator-surfaces.md`

## Redesign pointer

For the clean-break target lane map, see
`../../redesign/interfaces/api-surface-and-trust-lane-map.md`.
