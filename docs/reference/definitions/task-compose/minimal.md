# Minimal task-compose example

Status: Reference

Use this example to launch the shipped minimal workflow with task-local authored roots.

```yaml
task:
  key: first-run
  title: First local AutoClaw run
  summary: Prove the seeded minimal workflow on a bounded local task.
  instruction: >-
    Use the shipped minimal workflow to prove local launch, task-root creation, and runtime materialization.
workflow:
  key: minimal-implement-change
roots:
  workspace:
    mode: ensure_task_default
  context:
    mode: ensure_task_default
```
