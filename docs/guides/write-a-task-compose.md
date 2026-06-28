# Write a task-compose file

Status: Reference

Use task-compose when you are ready to launch one concrete task from reusable AutoClaw definitions.

## Minimal shape

A task-compose file needs a task, a workflow, and roots:

```yaml
task:
  key: first-run
  title: First local AutoClaw run
  summary: Prove the seeded minimal workflow on a bounded local task.
  instruction: >
    Use the shipped minimal workflow to prove local launch, task-root creation,
    and runtime materialization.
workflow:
  key: minimal-implement-change
roots:
  workspace:
    mode: ensure_task_default
  context:
    mode: ensure_task_default
```

Use this shape for first-run work and isolated local experiments.

## Choose the workflow

Set `workflow.key` to the reusable workflow you want to launch.

Use [write a workflow](write-a-workflow.md) when the shipped examples do not match your automation. `workflow.key` can point at any seeded or uploaded workflow definition.

## Write the task instruction

Keep task instruction concrete and scoped:

- say what this run should accomplish
- name important constraints or deferrals
- avoid reusable role or policy behavior
- avoid secrets and private credentials

If the same instruction should apply to many tasks, it probably belongs in a role, policy, or workflow instead.

## Bind roots

Task-compose root bindings decide whether AutoClaw creates task-local paths or binds directly to existing host paths.

### Default task-local binding

Use `ensure_task_default` when you want AutoClaw to create task-owned roots:

```yaml
roots:
  workspace:
    mode: ensure_task_default
  context:
    mode: ensure_task_default
```

This is the cleanest first-run lane because every task gets isolated roots.

### Explicit host-path binding

Use `ensure_host_path` when you want a specific host path and you are okay with AutoClaw creating it if needed:

```yaml
roots:
  workspace:
    mode: ensure_host_path
    host_path: /home/ubuntu/workspaces/autoclaw-task
  context:
    mode: ensure_task_default
```

### Existing host-path binding

Use `use_existing_host` when the path must already exist:

```yaml
roots:
  workspace:
    mode: use_existing_host
    host_path: /home/ubuntu/projects/real-repo
  context:
    mode: use_existing_host
    host_path: /home/ubuntu/projects/real-repo/docs
```

Use this for real project work where the task should operate against existing repository or context material.

## Start the task

Run:

```bash
autoclaw task-compose start --file ./task-compose.yaml --json
```

## Reference examples

- [Minimal task-compose reference](../reference/definitions/task-compose/minimal.md)
- [Bound workspace task-compose reference](../reference/definitions/task-compose/bound-workspace.md)
- [Copied e2e workspace task-compose reference](../reference/definitions/task-compose/copied-e2e-workspace.md)
