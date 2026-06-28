# Start a task

Status: Reference

This tutorial starts one local task with the shipped minimal workflow. It uses task-local roots so the first run stays isolated and easy to inspect.

## Before you start

Make sure the local install and OpenClaw integration are healthy:

```bash
autoclaw onboard
autoclaw doctor
autoclaw openclaw check
```

The shipped onboarding path seeds the packaged definition fixtures, including the minimal workflow used here.

## Create `task-compose.yaml`

Create this file in an empty working directory:

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

This task-compose file does three things:

- describes one task
- selects the `minimal-implement-change` workflow
- asks AutoClaw to create isolated task-local `workspace` and `context` roots

## Start the task

Run:

```bash
autoclaw task-compose start --file ./task-compose.yaml --json
```

The command reads one local file and starts the same task body that the public task-start API accepts.

## What success looks like

- the command returns a task id
- a task root is materialized on disk
- `_runtime/workflow-manifest.md` exists under the task root
- the first assignment and checkpoint surfaces become inspectable

## Next step

Use [inspect a task](inspect-a-task.md) to read the generated runtime surfaces and operator-facing outputs.
