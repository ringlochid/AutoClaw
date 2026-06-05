# runtime read models and operator surfaces

Status: Reference

Last verified: 2026-05-21

This page defines the current read-model and operator-query surfaces for task runtime inspection, operator summary, trace drilldown, and task-scoped observability.

Operator here means a trusted runtime-steering principal, not a callback caller and not the controller itself.

## Keywords

- current runtime list
- operator snapshot
- operator trace
- observability file refs
- dispatch history
- current paths

## Current runtime and operator read surfaces

Current read surfaces are:

- runtime task list
- runtime task read
- operator snapshot
- operator trace
- observability file refs

Current routes are:

- `GET /runtime/tasks`
- `GET /runtime/tasks/{task_id}`
- `GET /operator/tasks/{task_id}/snapshot`
- `GET /operator/tasks/{task_id}/trace`
- `GET /observability/tasks/{task_id}/delivery-state`
- `GET /observability/tasks/{task_id}/continuity-state`
- `GET /observability/tasks/{task_id}/watchdog-state`
- `GET /observability/tasks/{task_id}/provider-events`

## Current response shape facts

Current runtime list/read responses include:

- task id, title, and summary
- workflow key
- flow status
- active flow revision id
- workflow manifest ref
- current node key
- active attempt id
- updated timestamp

Current operator snapshot returns:

- the runtime flow read
- one or more top actionable items
- `current_paths` readback refs for the current semantic task view
- the workflow manifest is always included in `current_paths`
- dispatch-scoped observability refs appear in `current_paths` only while a current open dispatch exists; these refs are readback aids only and do not define semantic currentness

Current operator trace returns:

- dispatch history
- checkpoint history
- boundary history
- `current_paths` readback refs for the current semantic task view
- the workflow manifest is always included in `current_paths`
- dispatch-scoped observability refs appear in `current_paths` only while a current open dispatch exists; these refs are readback aids only and do not define semantic currentness
- cursor pagination

Current operator trace supports:

- `scope=current|whole`
- `q`
- `cursor`
- `limit`
- `sort=occurred_at_desc|occurred_at_asc`

## Current observability rule

Current observability endpoints do not return assembled runtime truth directly. They return file refs to task-scoped generated projections under:

- `_runtime/dispatch/<dispatch_id>/delivery-state.json`
- `_runtime/dispatch/<dispatch_id>/continuity-state.json`
- `_runtime/dispatch/<dispatch_id>/watchdog-state.json`
- `_runtime/dispatch/<dispatch_id>/provider-events.ndjson`

If a task has no current open dispatch, observability lookup falls back to the most recently rendered dispatch for that task.

That fallback is limited to the task-scoped `/observability/...` file-ref routes. Operator snapshot and trace `current_paths` do not reuse the latest rendered dispatch when there is no current open dispatch; in that state they surface only semantic-current readback refs such as the workflow manifest.

Those observability support refs may therefore diverge from semantic currentness such as `current_node_key` or the next resumable attempt. They remain operator/readback aids only.

These GET surfaces are pure rereads. They resolve task-root bindings, reference the current manifest/dispatch files if present, and do not `mkdir()` or rematerialize deleted projections inline.

## Current read-model rule

Read models are not runtime truth. They are assembled views over controller-owned runtime records and generated task-root projections.

That means:

- runtime list/read is a convenience surface, not the authority
- operator snapshot is a summary surface, not the authority
- operator trace is a drilldown surface, not the authority
- observability file refs point at generated projections, not the authority

## Current gaps versus older docs

Current code does not ship the older per-flow operator drilldown, internal runtime-slice/timeline/audit style reads, legacy bundle reads, or legacy registry snapshot/validation routes anymore.

Current code also does not expose a dedicated manifest-ack query surface or the older bundle-read contract.

## Evidence

- inspected code in `apps/api/src/autoclaw/runtime/observability/__init__.py`
- inspected code in `apps/api/src/autoclaw/runtime/flow/listing.py`
- inspected code in `apps/api/src/autoclaw/runtime/flow/service.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/runtime.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/operator.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/observability.py`
- inspected code in `apps/api/src/autoclaw/runtime/post_commit/worker.py`
- inspected tests in `apps/api/tests/integration/phase3/routes/test_query_contract.py`
- inspected tests in `apps/api/tests/integration/phase3/routes/test_surface_contract.py`

## Related pages

- `../api/api-surface-and-route-map.md`
- `openclaw-and-bridge-plugin.md`
