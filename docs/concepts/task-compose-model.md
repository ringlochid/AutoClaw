# Task-compose model

Status: Reference

Task-compose is the launch body for one AutoClaw task. It connects the user's concrete request to reusable definition registry state and real host paths.

## What task-compose owns

Task-compose owns task-specific launch truth:

- task key, title, summary, and instruction
- selected workflow key
- root bindings for `workspace` and `context`

It should stay small. Put reusable behavior in roles, policies, and workflows. Put one-off task detail in task-compose.

## What task-compose does not own

Task-compose does not define role behavior, policy capabilities, workflow structure, runtime checkpoints, artifacts, or operator decisions.

After launch, controller-owned runtime state becomes the authority for the task.

## Root bindings

Root bindings decide where task material lives:

- `workspace`: the working material for the task
- `context`: supporting context the task can read

Each root can be task-local or bound to a host path. The concept is about ownership and isolation; the YAML recipes live in the task-compose guide.

## Related pages

- [Workspace model](workspace-model.md)
- [Write a task-compose file](../guides/write-a-task-compose.md)
- [Task-compose reference examples](../reference/definitions/task-compose/README.md)
