# API route trust lanes

Phase 8 note: this is the explicit route-surface map for the current API.

## Trust lanes

### 1. Public / operator API
Protected by `X-AutoClaw-API-Key` via `require_api_key`.

Intended for operator-facing actions and normal product surfaces.

Current grouped surfaces:
- `/flows/*` operator flow control and inspect
- `/tasks/*` public task upload + compose start
- `/approvals/*` operator approval read/resolve
- `/registry/*` operator registry read/write surfaces

### 2. Internal callback / controller API
Protected by `X-AutoClaw-API-Key` via `require_internal_api_key`.

Intended for AutoClaw-controlled writes, worker/controller callbacks, bootstrap/import, watchdog/dispatch, and internal audit/query routes.

Current grouped surfaces:
- `/internal/flows/*`
- `/internal/approvals/*`
- `/internal/registry/*`
- `/internal/tasks/*`
- `/internal/compiler/*`

### 3. Browser console bootstrap
`GET /console/config`

Current hardening contract:
- the server does **not** inject a reusable operator API key into browser-visible config
- console config exposes only base URL + header name + auth mode hint
- browser sessions must provide auth manually or through a trusted reverse proxy/header injector
- `supportsAuthoring` is `false` until a safer browser-auth contract exists

## Capability grouping

### Task launch / import / upload
- public: `/tasks/{task_id}/uploads`, `/tasks/composes/start`
- internal: `/internal/tasks`, `/internal/tasks/{task_id}/uploads`

### Flow control
- public: `/flows/{flow_id}`, `/flows/{flow_id}/operator`, `/flows/{flow_id}/continue`, `/pause`, `/cancel`, node retry

### Worker callback / internal runtime mutation
- internal: checkpoint writes, manifest ack, replans, context publication, dispatch/watchdog controls, worker bundle reads

### Operator audit / query
- internal read-heavy slices remain under `/internal/flows/*`
- public operator-oriented reads stay under `/flows/*` and `/registry/*`

## Current cleanup rule

When a route exists in both public and internal spaces, it must be because the trust lane is genuinely different, not because the repo accumulated duplicate historical surfaces.

Deprecated or historical-only task creation stays internal-only.
