# Current API route families and lane map

Status: Current

Last verified: 2026-04-26

This page owns the exact current route families, route nouns, and public/internal/bootstrap grouping for the shipped FastAPI surface.

For operator-role meaning and lane authority, see `api-trust-lanes.md`.

## Ownership rule

Use this page for current path families, namespace split, and browser bootstrap routing.

Use `api-trust-lanes.md` for role meaning, caller authority, and operator versus worker/controller boundaries.

## Current route families

Current router families are:

- `health`
- `tasks`
- `flows`
- `approvals`
- `registry`
- internal `compiler`

The route split is implemented in `autoclaw-main/apps/api/app/api/router.py`.

## Current public/operator routes

Public/operator lane is protected by `require_api_key`.

Current grouped surfaces:

- `/flows/*`
- `/tasks/*`
- `/approvals/*`
- `/registry/*`

This includes:

- flow inspect and operator snapshot
- continue, pause, cancel, retry
- task uploads and task-compose start
- approval read and resolve
- public registry reads
- public workflow validation preview
- current public role, policy, workflow, and skill draft writes
- current public role, policy, workflow, and skill publish surfaces

This is the standard current public/operator lane, but its nouns remain legacy implementation truth rather than the redesign's canonical `/runtime`, `/definitions`, and `/tasks` split.

## Current controller-private routes

Internal lane is protected by `require_internal_api_key`.

Current grouped surfaces:

- `/internal/flows/*`
- `/internal/approvals/*`
- `/internal/registry/*`
- `/internal/tasks/*`
- `/internal/workflows/*` through the compiler router

Current controller-private surfaces include a mixed callback/controller lane and deeper observability/admin surfaces:

- checkpoint writes
- manifest acknowledgement
- context publication
- worker bundle reads
- runtime slice, timeline slice, audit, checkpoints, replans
- watchdog run and watchdog recover
- OpenClaw dispatch
- registry snapshot
- bootstrap

This is a mixed internal namespace used by controller/callback paths and deeper trusted operator tooling. The redesign later splits these responsibilities into `/callback/...` and `/observability/...`.

## Current browser bootstrap

Current browser bootstrap is:

- `GET /console/config`

Current contract:

- no reusable operator key in browser-visible config
- browser gets base URL, header/auth hints, refresh interval, and `supportsAuthoring`
- server-advertised browser authoring is disabled in `/console/config` today
- the bundled console UI still exposes mutation actions when the operator supplies a valid API key through manual or proxy-header auth

## Current route-shape facts

Current public/internal noun family is still legacy/current:

- `registry`
- `flows`
- `tasks`
- `approvals`

Current docs must treat this as implementation truth only. It is not the clean-break target API surface.

## Minimal example

```text
public/operator:
  /flows/{flow_id}
  /tasks/composes/start
  /approvals/{approval_id}/resolve

internal/controller-private:
  /internal/flows/{flow_id}/worker-bundle
  /internal/flows/{flow_id}/watchdog
  /internal/flows/{flow_id}/watchdog/recover
  /internal/registry/bootstrap
```

## Expanded example

```text
task launch
  -> public POST /tasks/composes/start

worker callback/controller lane
  -> internal manifest ack
  -> internal checkpoint write
  -> internal context publication

operator deep query
  -> internal runtime slice
  -> internal timeline slice
  -> internal flow audit
  -> internal registry snapshot
```

## Evidence

- inspected code in `autoclaw-main/apps/api/app/api/router.py`
- inspected code in `autoclaw-main/apps/api/app/api/routes/tasks.py`
- inspected code in `autoclaw-main/apps/api/app/api/routes/flows.py`
- inspected code in `autoclaw-main/apps/api/app/api/routes/approvals.py`
- inspected code in `autoclaw-main/apps/api/app/api/routes/registry.py`
- inspected code in `autoclaw-main/apps/api/app/api/routes/compiler.py`
- inspected code in `autoclaw-main/apps/api/app/main.py`
- inspected code in `autoclaw-main/apps/console/src/App.tsx`

## Related current pages

- `api-trust-lanes.md`
- `../architecture/runtime-read-models-and-operator-surfaces.md`
- `definition-registry-and-publish-lifecycle.md`
- `cli-surface-and-config-precedence.md`

## Redesign pointer

For the clean-break target API noun families and trust-lane map, see `../../redesign/interfaces/api-surface-and-trust-lane-map.md`.
