# Launch a task compose in the current system

Status: Current

Last verified: 2026-04-25

This page describes the current public task-compose launch path.

## Procedure

1. Prepare a task-compose YAML file that matches the current `TaskComposeStartCreate` contract in `../interfaces/definition-and-task-compose-yaml-contract.md`.
2. Start the API with `autoclaw up` or an equivalent local server path.
3. Launch the task compose with `autoclaw task-compose start <file>`.

## Current route surface

The current public route is:

- `POST /tasks/composes/start`

The current CLI validates the YAML locally and then posts the request to that route.

## Evidence

- inspected code in `autoclaw-main/apps/api/app/api/routes/tasks.py`
- inspected code in `autoclaw-main/apps/api/app/cli.py`

## Current limitation

This is still the current launch surface, not the redesign target task-compose contract.

For the exact current task-compose YAML shape, see `../interfaces/definition-and-task-compose-yaml-contract.md`.
