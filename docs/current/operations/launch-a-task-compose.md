# Launch a task compose in the current system

Status: Current

Last verified: 2026-05-12

This page describes the current shipped task-compose launch reality.

## Current status

The current task-compose payload shape still exists, but only as an internal
runtime launch contract.

The shipped checkout does not expose a public task-compose start route or CLI
command today.

Current code therefore does not provide a user-facing procedure equivalent to:

- `POST /tasks/composes/start`
- `autoclaw task-compose start <file>`

## What still exists

- `TaskComposeInput` remains the current typed launch payload
- the runtime launch service can still consume that payload internally
- tests and helpers still use task-compose inputs to seed runtime scenarios

For the exact current YAML shape, see
`../interfaces/definition-and-task-compose-yaml-contract.md`.

## Current operator implication

If you need a public launch flow in this checkout, there is no current
operator-facing task-compose surface to call.

Treat task-compose as an internal launch contract until the later public ingest
phase lands.

## Evidence

- inspected code in `apps/api/app/runtime/launch/service.py`
- inspected code in `apps/api/app/runtime/contract_models/primitives.py`
- inspected current route map in `../interfaces/api-surface-and-route-map.md`
- inspected current task-compose contract in
  `../interfaces/definition-and-task-compose-yaml-contract.md`
