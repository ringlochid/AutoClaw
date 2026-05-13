# Current runtime read models and operator surfaces

Status: Current

Last verified: 2026-05-12

This page defines the current read-model and operator-query surfaces for task
runtime inspection, operator summary, trace drilldown, and task-scoped
observability.

Operator here means a trusted runtime-steering principal, not a callback caller
and not the controller itself.

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
- current support-path refs such as the workflow manifest

Current operator trace returns:

- dispatch history
- checkpoint history
- boundary history
- current support-path refs
- cursor pagination

Current operator trace supports:

- `scope=current|whole`
- `q`
- `cursor`
- `limit`
- `sort=occurred_at_desc|occurred_at_asc`

## Current observability rule

Current observability endpoints do not return assembled runtime truth directly.
They return file refs to task-scoped generated projections under:

- `_runtime/dispatch/<dispatch_id>/delivery-state.json`
- `_runtime/dispatch/<dispatch_id>/continuity-state.json`
- `_runtime/dispatch/<dispatch_id>/watchdog-state.json`
- `_runtime/dispatch/<dispatch_id>/provider-events.ndjson`

If a task has no current open dispatch, observability lookup falls back to the
most recently rendered dispatch for that task.

## Current read-model rule

Read models are not runtime truth. They are assembled views over
controller-owned runtime records and generated task-root projections.

That means:

- runtime list/read is a convenience surface, not the authority
- operator snapshot is a summary surface, not the authority
- operator trace is a drilldown surface, not the authority
- observability file refs point at generated projections, not the authority

## Current gaps versus older docs

Current code does not ship the older per-flow operator drilldown, internal
runtime-slice/timeline/audit style reads, legacy bundle reads, or legacy
registry snapshot/validation routes anymore.

Current code also does not expose a dedicated manifest-ack query surface or the
older bundle-read contract.

## Evidence

- inspected code in `apps/api/app/runtime/control/observability.py`
- inspected code in `apps/api/app/runtime/control/flow/listing.py`
- inspected code in `apps/api/app/runtime/control/flow/service.py`
- inspected code in `apps/api/app/api/routes/runtime.py`
- inspected code in `apps/api/app/api/routes/operator.py`
- inspected code in `apps/api/app/api/routes/observability.py`
- inspected code in `apps/api/app/runtime/effects/worker.py`
- inspected tests in `apps/api/tests/integration/phase3/routes/test_query_contract.py`
- inspected tests in `apps/api/tests/integration/phase3/routes/test_surface_contract.py`

## Related current pages

- [Runtime control plane](runtime-control-plane.md)
- [Manifest projection and acknowledgement](manifest-projection-and-acknowledgement.md)
- [Prompt layer and worker delivery](../interfaces/prompt-layer-and-worker-delivery.md)
