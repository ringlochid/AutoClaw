# Bound workspace task-compose guide example

Status: Reference

Use this example when a task should target a real host path instead of an AutoClaw-created task-local root.

This example teaches:

- `ensure_host_path` binds to an explicit host path and creates it if needed
- you can mix host-bound workspace roots with task-local context roots
- launch input is where host placement becomes concrete

```yaml
task:
  key: host-bound-review
  title: Run a host-bound normal workflow
  summary: Bind the task workspace to an explicit host path.
  instruction: >-
    Run the normal workflow against a real host workspace and keep the task scoped to that path.
workflow:
  key: normal-parent-first-release
roots:
  workspace:
    mode: ensure_host_path
    host_path: /home/ubuntu/workspaces/autoclaw-host-bound
  context:
    mode: ensure_task_default
```
