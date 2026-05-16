# Use the current OpenClaw bridge plugin

Status: Current

Last verified: 2026-05-12

This page describes the current bridge-facing surfaces that are provable from
this checkout and the limits of what this repo can currently verify.

## Keywords

- current bridge plugin
- request_approval
- operatorQueries
- registryWrites
- raw operator query tools
- skill writes

## Current checkout boundary

This repo proves the API-side callback and operator lanes that a bridge or
plugin must target.

It does not include the separate bridge-plugin package or its manifest, so this
page does not claim a revalidated plugin-local tool inventory.

## Repo-proven bridge-facing surfaces

Current callback lane:

- `POST /callback/tasks/{task_id}/checkpoint`
- `POST /callback/tasks/{task_id}/boundary`
- `POST /callback/tasks/{task_id}/tools/{tool_name}`

Current operator/support reads that an external bridge can rely on:

- `GET /runtime/tasks/{task_id}`
- `GET /operator/tasks/{task_id}/snapshot`
- `GET /operator/tasks/{task_id}/trace`
- `GET /observability/tasks/{task_id}/delivery-state`
- `GET /observability/tasks/{task_id}/continuity-state`
- `GET /observability/tasks/{task_id}/watchdog-state`
- `GET /observability/tasks/{task_id}/provider-events`

Current auth and session facts visible in this repo:

- callback writes are bound to `X-Autoclaw-Session-Key`
- operator reads are protected by `X-AutoClaw-API-Key`
- callback bindings are validated against the live dispatch/session contract

These are current shipped facts only. They are not the redesign target if v1 moves to a static `node MCP` surface with explicit `session_key` + `task_id` tool arguments.

## What this checkout does not prove

- a separate bridge-plugin manifest or source tree
- plugin-local capability flags such as `operatorQueries` or `registryWrites`
- browser-console component wiring beyond the placeholder `apps/console/src/`
  tree
- a revalidated worker-lane tool inventory outside the callback API contract

## Current config facts

- runtime config defaults still live in `apps/api/app/paths.py`
- callback and operator auth are enforced at the API layer, not in a
  plugin-local repo surface here
- if you need plugin packaging or manifest truth, you must inspect the separate
  bridge-plugin repo outside this checkout

## Target contrast

The redesign contract differs on purpose:

- target worker lane removes `request_approval`
- target standard operator-plugin reads collapse into operator-facing bundle surfaces instead of raw slice-by-slice names
- target standard operator-plugin writes exclude generic skill draft/publish

Use this page only for shipped current behavior. For the target contract, see [Plugin tool reference](../../redesign/interfaces/plugin-tool-reference.md).

## Evidence

- inspected code in `apps/api/app/api/routes/callback.py`
- inspected code in `apps/api/app/api/routes/runtime.py`
- inspected code in `apps/api/app/api/routes/operator.py`
- inspected code in `apps/api/app/api/routes/observability.py`
- inspected code in `apps/api/app/runtime/control/dispatch/callbacks.py`
- inspected current behavior docs in
  `../architecture/openclaw-dispatch-and-session-contract.md`
- inspected current behavior docs in `../interfaces/api-trust-lanes.md`
