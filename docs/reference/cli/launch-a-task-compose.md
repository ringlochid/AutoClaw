# Launch a task

This page describes the shipped task-start surface.

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
- operator MCP parity `start_task(task_compose_path)` loads one local file and submits that same `TaskStartRequest` body to the task-start handler
- root CLI parity `autoclaw task-compose start --file <task_compose_path>` loads one local file and submits that same `TaskStartRequest` body to the task-start handler
- tests and helpers still use the same task-compose shape to seed runtime scenarios
- there is no separate staged task-file upload surface in the current shipped tree

For the exact YAML shape, see [Definition and task-compose YAML contract](../api/definition-and-task-compose-yaml-contract.md).

## Current operator implication

If you need a real operator-facing launch flow in this checkout, use:

- `POST /tasks/start`
- `start_task(task_compose_path)` when you are using the operator MCP parity surface
- `autoclaw task-compose start --file <task_compose_path>` when you want the current root CLI wrapper

If you want the end-to-end runbook around that route, use [Run real e2e workflow lanes](../maintainers/run-real-e2e-workflow-lanes.md).
