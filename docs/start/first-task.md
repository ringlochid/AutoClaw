# Run your first task

Status: Reference

This guide proves the local launch path with the shipped minimal workflow fixture.

## Before you start

Make sure this path is already healthy:

```bash
autoclaw onboard
autoclaw doctor
autoclaw openclaw check
```

The shipped onboarding flow seeds the packaged definition fixtures, including the minimal workflow.

## Create a minimal task-compose file

Create `task-compose.yaml`:

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

## Start the task

```bash
autoclaw task-compose start --file ./task-compose.yaml --json
```

That wrapper reads one local file and submits the same task-start body as `POST /tasks/start`.

## What success looks like

- the command returns a task id and runtime start result
- a task root is materialized on disk
- the runtime writes `_runtime/workflow-manifest.md`
- the first assignment and checkpoint surfaces become inspectable

## Next step

Use [inspect your first run](inspect-your-first-run.md) to read the generated runtime surfaces and operator-facing outputs.
