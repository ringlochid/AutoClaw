# API route families and lane map

Status: Reference

Last verified: 2026-05-21

This page owns the exact current HTTP route families, mounted surface nouns, and auth grouping for the shipped FastAPI tree.

For operator-role meaning and lane authority, see `api-trust-lanes.md`.

## Ownership rule

Use this page for current path families, route nouns, and auth split.

Use `api-trust-lanes.md` for caller authority and the difference between operator, callback, node-tool, and controller roles.

## Current route families

Current router families are:

- `health`
- `definitions`
- `tasks`
- `runtime`
- `operator`
- `callback`
- `observability`

The split is implemented in `apps/api/src/autoclaw/interfaces/http/router.py`.

Mounted MCP app surfaces are enabled separately in `apps/api/src/autoclaw/main.py`:

- `/operator` mounted operator MCP app when MCP mounts are enabled
- `/node/mcp` mounted static node MCP app when MCP mounts are enabled

## Current health routes

Unauthenticated health routes are:

- `GET /healthz`
- `GET /readyz`

`/readyz` performs a DB ping before returning ready.

## Current definition and task-start routes

The current definition and task-start HTTP subset is protected by `X-AutoClaw-API-Key` via `require_api_key`.

Current routes are:

- `GET /definitions/roles`
- `GET /definitions/policies`
- `GET /definitions/workflows`
- `GET /definitions/{kind}/{key}`
- `GET /definitions/{kind}/{key}/versions`
- `POST /definitions`
- `POST /tasks/start`

Current query-backed route details include:

- `/definitions/roles|policies|workflows` support the shared definition list query contract
- `/definitions/{kind}/{key}/versions` supports history paging and sort queries
- `POST /definitions` returns `201 Created` for a new revision and `200 OK` for a no-op replay
- `POST /tasks/start` waits for initial runtime effects before returning the task start readback

## Current operator routes

The runtime, operator, and observability HTTP subset is protected by `X-AutoClaw-API-Key` via `require_api_key`.

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
- `/runtime/tasks/{task_id}/continue|pause|cancel` require `expected_active_flow_revision_id`
- `/operator/tasks/{task_id}/trace` supports `scope`, `q`, `limit`, `cursor`, and `sort`

## Current callback routes

The callback lane requires the live `session_key` query parameter together with the route `task_id`.

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

- the route layer validates the session key against the current live `NodeSession` plus current dispatch, flow, assignment, and attempt truth
- stale, revoked, inactive, or mismatched-task session usage is rejected
- structural callback tool success for `add_child`, `update_child`, and `remove_child` means the stable `_runtime/workflow-manifest.*` reread path was refreshed through the control-side commit and rollback helpers before the final commit completed

## Current mounted node MCP surface

When MCP mounts are enabled, the current node-tool surface is mounted at `/node/mcp`.

Current node-tool inventory is:

- `search_definitions`
- `get_definition`
- `record_checkpoint`
- `return_boundary`
- `assign_child`
- `add_child`
- `update_child`
- `remove_child`
- `release_green`
- `release_blocked`

Mounted node facts:

- every tool input schema requires explicit `session_key` and `task_id`
- mounted node tools use the same shared authority path as callback HTTP writes
- mounted node inventory stays separate from operator MCP inventory
- mounted node tools now preserve the strict surfaced wrapper contracts:
  - `assign_child`, `add_child`, `update_child`, and `remove_child` each take their own typed `payload` body, while `release_green` and `release_blocked` use only `expected_structural_revision_id?`
  - `record_checkpoint`, `return_boundary`, and the split structural mutation tools return typed structured success bodies

## Current route-shape facts

Current shipped path families are:

- `/definitions/*`
- `/tasks/*`
- `/runtime/*`
- `/operator/*`
- `/callback/*`
- `/observability/*`
- `/node/mcp`

Current code does not ship the older legacy flow, approval, registry-internal, task-compose-start, or browser-bootstrap route families anymore.

Current code still keeps `require_internal_api_key()` in `app.api.deps`, but no shipped HTTP router currently uses it.

## Minimal example

```text
operator HTTP:
  GET  /definitions/roles
  POST /tasks/start
  GET  /runtime/tasks
  GET  /runtime/tasks/{task_id}
  POST /runtime/tasks/{task_id}/pause?expected_active_flow_revision_id=...
  GET  /operator/tasks/{task_id}/trace
  GET  /observability/tasks/{task_id}/delivery-state

callback HTTP:
  POST /callback/tasks/{task_id}/checkpoint
  POST /callback/tasks/{task_id}/boundary
  POST /callback/tasks/{task_id}/tools/assign_child

mounted node MCP:
  assign_child(session_key, task_id, payload, expected_structural_revision_id?)
```

## Evidence

- inspected code in `apps/api/src/autoclaw/interfaces/http/router.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/health.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/definitions.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/tasks.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/runtime.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/operator.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/callback.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/observability.py`
- inspected code in `apps/api/src/autoclaw/interfaces/mcp/node/server.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/dependencies.py`
- inspected code in `apps/api/src/autoclaw/main.py`
- inspected tests in `apps/api/tests/integration/runtime/routes/test_query_contract.py`
- inspected tests in `apps/api/tests/integration/runtime/routes/test_surface_contract.py`
- inspected tests in `apps/api/tests/integration/mcp/node_server`
- inspected tests in `apps/api/tests/integration/public_surfaces/test_public_http_subset.py`

## Related pages

- `api-trust-lanes.md`
- `../operator/runtime-read-models-and-operator-surfaces.md`
