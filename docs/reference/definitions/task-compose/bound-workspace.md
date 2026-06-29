# Bound workspace task-compose example

Status: Reference

Use this example when the task should bind to a specific host path and create it if needed.

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
