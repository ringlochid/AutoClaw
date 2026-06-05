# Inspect approval-related and watchdog state in the current system

Status: Reference

Last verified: 2026-05-21

This page describes the current shipped watchdog inspection surfaces and the approval-related gaps that remain in older current docs.

## Approvals

The shipped router no longer exposes dedicated approval routes.

Current code does not ship:

- `GET /approvals/{approval_id}`
- `POST /approvals/{approval_id}/resolve`
- `POST /internal/approvals`

Approval remains legacy vocabulary in some current-contrast pages, but the live inspection and control surfaces now flow through the runtime, operator, and observability route families instead.

### Current operator inspection surfaces

| Route                                          | Current effect                                               |
| ---------------------------------------------- | ------------------------------------------------------------ |
| `GET /runtime/tasks/{task_id}`                 | inspect current runtime summary, including active task state |
| `GET /operator/tasks/{task_id}/snapshot`       | inspect current operator summary                             |
| `GET /operator/tasks/{task_id}/trace`          | inspect dispatch, checkpoint, and boundary history           |
| `GET /observability/tasks/{task_id}/watchdog-state` | fetch the latest watchdog projection ref                |
| `POST /runtime/tasks/{task_id}/continue`       | continue after operator-side inspection when legal           |
| `POST /runtime/tasks/{task_id}/pause`          | pause the live runtime and revoke callback access            |
| `POST /runtime/tasks/{task_id}/cancel`         | cancel the live runtime                                      |

Approval-specific state is therefore inspected indirectly through the task runtime and operator views, not through standalone approval endpoints.

## Watchdog

Current watchdog state is exposed as an operator-facing observability surface, not as a dedicated recover endpoint.

Current operator-facing facts:

- watchdog blocks stale running attempts
- watchdog also tracks accepted first-dispatch turns that have not produced committed first progress yet
- watchdog projections are published under `_runtime/dispatch/<dispatch_id>/`
- watchdog escalation is surfaced for operator inspection rather than a standalone recover call

### Watchdog route-to-effect map

| Route                                     | Current effect                                                      |
| ----------------------------------------- | ------------------------------------------------------------------- |
| `GET /observability/tasks/{task_id}/watchdog-state` | return the latest task-scoped watchdog projection ref |
| `GET /operator/tasks/{task_id}/trace`     | expose the checkpoints and boundaries that explain the watchdog path |
| `POST /runtime/tasks/{task_id}/continue`  | resume a paused task after operator review when the runtime allows it |

### Important current exclusions

- operator wait is not a watchdog stall candidate
- dependency wait is not a watchdog stall candidate

### Operator expectation after ambiguity

If watchdog wake times out ambiguously or fails:

- inspect delegated session binding
- inspect recent checkpoints
- do not assume timeout proves failed delivery
- prefer explicit operator retry only after inspection

## Evidence

- inspected code in `apps/api/src/autoclaw/interfaces/http/router.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/runtime.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/operator.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/observability.py`
- inspected current behavior docs in `../api/api-surface-and-route-map.md`
- inspected current behavior docs in `openclaw-and-bridge-plugin.md`

## Related pages

- `../api/api-surface-and-route-map.md`
- `runtime-read-models-and-operator-surfaces.md`
- `openclaw-and-bridge-plugin.md`
- `../api/api-trust-lanes.md`
