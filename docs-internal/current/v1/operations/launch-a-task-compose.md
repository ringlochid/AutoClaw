# Launch a task in the current system

Status: Current

Last verified: 2026-05-18

This page describes the current shipped task-start reality.

## Current status

The current public task-start route is:

- `POST /tasks/start`

The request body is still the current `TaskComposeInput` shape.

The shipped checkout still does not expose:

- `POST /tasks/composes/start`

## What exists today

- `TaskComposeInput` remains the current typed launch payload
- `TaskStartRequest` publicly reuses that payload shape over HTTP
- `POST /tasks/start` launches a task and waits for initial runtime effects
- operator MCP parity `start_task(task_compose_path)` loads one local file and submits that same `TaskStartRequest` body to the canonical backend task-start handler
- root CLI parity `autoclaw task-compose start --file <task_compose_path>` loads one local file and submits that same `TaskStartRequest` body to the canonical backend task-start handler
- tests and helpers still use the same task-compose shape to seed runtime scenarios
- there is no separate staged task-file upload surface in the current shipped tree

For the exact current YAML shape, see `../interfaces/definition-and-task-compose-yaml-contract.md`.

## Current operator implication

If you need a real operator-facing launch flow in this checkout, use:

- `POST /tasks/start`
- `start_task(task_compose_path)` when you are using the operator MCP parity surface
- `autoclaw task-compose start --file <task_compose_path>` when you want the current root CLI wrapper

If you want the current end-to-end runbook around that route, use [Run real e2e workflow lanes](run-real-e2e-workflow-lanes.md).

## Evidence

- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/tasks.py`
- inspected code in `apps/api/src/autoclaw/runtime/contracts/start.py`
- inspected code in `apps/api/src/autoclaw/runtime/launch/service.py`
- inspected code in `apps/api/src/autoclaw/runtime/contracts/primitives.py`
- inspected current route map in `../interfaces/api-surface-and-route-map.md`
- inspected current task-compose contract in `../interfaces/definition-and-task-compose-yaml-contract.md`
