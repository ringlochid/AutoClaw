# Workspace model

Status: Reference

Task start binds authored roots into real host paths. That binding is part of the task-compose launch input.

## Root kinds

Current task-compose input has two authored roots:

- `workspace`
- `context`

Each root can choose one of three modes:

- `ensure_task_default`
- `ensure_host_path`
- `use_existing_host`

## What the modes mean

- `ensure_task_default`: create the root inside the task-owned default path
- `ensure_host_path`: use an explicit host path and create it if needed
- `use_existing_host`: use an explicit host path and fail if it does not already exist

## Why this matters

The workspace model decides whether the controller creates task-local directories or binds directly to existing host material. That choice affects isolation, repeatability, and how you inspect outputs later.

## Next step

See [bind a real workspace](../guides/bind-a-real-workspace.md) for concrete task-compose examples.
