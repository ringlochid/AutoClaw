# Workspace model

Task start resolves authored roots into real host paths. Explicit bindings are part of task-compose launch input, but roots are optional.

## Root kinds

Current task-compose input can bind two authored roots:

- `workspace`
- `context`

If roots are omitted, AutoClaw uses task-owned default paths for both roots. Each explicit root can choose one of three modes:

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

See [write a task-compose file](../guides/write-a-task-compose.md) for concrete root binding examples.
