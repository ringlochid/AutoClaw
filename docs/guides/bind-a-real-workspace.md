# Bind a real workspace

Status: Reference

Use task-compose root bindings to decide whether AutoClaw creates task-local paths or binds directly to existing host paths.

## Default task-local binding

Use `ensure_task_default` when you want AutoClaw to create task-owned roots.

```yaml
roots:
  workspace:
    mode: ensure_task_default
  context:
    mode: ensure_task_default
```

This is the cleanest first-run lane because every task gets isolated authored roots.

## Explicit host-path binding

Use `ensure_host_path` when you want a specific host path and you are okay with AutoClaw creating it if needed.

```yaml
roots:
  workspace:
    mode: ensure_host_path
    host_path: /home/ubuntu/workspaces/autoclaw-task
  context:
    mode: ensure_task_default
```

## Existing host-path binding

Use `use_existing_host` when the path must already exist.

```yaml
roots:
  workspace:
    mode: use_existing_host
    host_path: /home/ubuntu/projects/real-repo
  context:
    mode: use_existing_host
    host_path: /home/ubuntu/projects/real-repo/docs
```

## Reference examples

- [Minimal task-compose reference](../reference/definitions/task-compose/minimal.md)
- [Bound workspace task-compose reference](../reference/definitions/task-compose/bound-workspace.md)
- [Copied e2e workspace task-compose reference](../reference/definitions/task-compose/copied-e2e-workspace.md)
