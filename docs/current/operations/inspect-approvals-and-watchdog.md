# Inspect approvals and watchdog state in the current system

Status: Current

Last verified: 2026-04-26

This page describes the exact current approval and watchdog operator surfaces without projecting redesign semantics onto them.

## Approvals

Current public approval surfaces:

- `GET /approvals/{approval_id}`
- `POST /approvals/{approval_id}/resolve`

Current internal approval creation surface:

- `POST /internal/approvals`

### Watchdog route-to-effect map

| Route                                   | Current effect                                                         |
| --------------------------------------- | ---------------------------------------------------------------------- |
| `POST /internal/approvals`              | create pending approval and block current target flow/attempt          |
| `GET /approvals/{approval_id}`          | inspect one approval record                                            |
| `POST /approvals/{approval_id}/resolve` | apply approval outcome and re-enter `advance_flow_until_boundary(...)` |

### Resolve outcomes

| Outcome        | Current effect                                                                                  |
| -------------- | ----------------------------------------------------------------------------------------------- |
| `approved`     | refresh flow state and re-enter advancement                                                     |
| `not_required` | refresh flow state and re-enter advancement                                                     |
| `rejected`     | fail flow, fail open attempts, expire approvals, supersede manifests, then re-enter advancement |

Approval is current-only legacy behavior. It is not redesign review and not just pause/continue.

## Watchdog

Current watchdog surfaces are internal runtime controls rather than a polished public product flow.

Current operator-facing facts:

- watchdog blocks stale running attempts
- watchdog also blocks accepted bootstrap dispatches that never ack their manifest
- watchdog records blocked checkpoints with `wait_reason=watchdog`
- bootstrap no-ack recovery uses fresh attempt retry, not same-session wake
- same-session wake may be attempted once by default for post-ack running recovery
- timeout or failed wake escalates with operator guidance rather than silently retrying forever

### Route-to-effect map

| Route                                        | Current effect                                                                                                                                      |
| -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/internal/flows/{flow_id}/watchdog`         | classify stale running attempts or bootstrap no-ack attempts and create watchdog-blocked checkpoints                                                |
| `/internal/flows/{flow_id}/watchdog/recover` | attempt same-session wake recovery for running execution or fresh bootstrap retry for bootstrap no-ack; otherwise return explicit escalation reason |

### Important current exclusions

- approval wait is not a watchdog stall candidate
- operator wait is not a watchdog stall candidate
- dependency wait is not a watchdog stall candidate

### Operator expectation after ambiguity

If watchdog wake times out ambiguously or fails:

- inspect delegated session binding
- inspect recent checkpoints
- do not assume timeout proves failed delivery
- prefer explicit operator retry only after inspection

## Evidence

- inspected code in `autoclaw-main/apps/api/app/api/routes/approvals.py`
- inspected code in `autoclaw-main/apps/api/app/runtime/approvals.py`
- inspected code in `autoclaw-main/apps/api/app/runtime/watchdog.py`
- inspected code in `autoclaw-main/apps/api/app/runtime/watchdog_service.py`

## Related current pages

- `../architecture/parent-retry-and-operator-control.md`
- `../architecture/watchdog-and-runtime-monitoring.md`
- `../interfaces/api-trust-lanes.md`
