# Workspace model

Task start resolves the task-compose `roots` mapping into real host paths. This mapping is launch input and is separate from the workflow `root` node.

## Named path bindings

Current task-compose input can bind two named paths:

- `workspace`
- `context`

If `roots` is omitted, AutoClaw uses task-owned default paths for both names. Each explicit binding can choose one of three modes:

- `ensure_task_default`
- `ensure_host_path`
- `use_existing_host`

## What the modes mean

- `ensure_task_default`: create the named path inside the task-owned default path
- `ensure_host_path`: use an explicit host path and create it if needed
- `use_existing_host`: use an explicit host path and fail if it does not already exist

## Why this matters

The workspace model decides whether the controller creates task-local directories or binds directly to existing host material. That choice affects isolation, repeatability, and how you inspect outputs later.

## Next step

See [write a task-compose file](../guides/write-a-task-compose.md) for concrete `roots` mapping examples.
