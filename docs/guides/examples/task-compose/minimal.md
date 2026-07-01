# Minimal task-compose guide example

Use this example when you want AutoClaw to create task-local authored roots and prove the smallest launch path.

This example teaches:

- `ensure_task_default` is the cleanest first-run binding mode
- the task body names the concrete launch while the workflow key picks the reusable workflow
- the wrapper reads one local file and submits the same backend task-start body as the canonical route

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
