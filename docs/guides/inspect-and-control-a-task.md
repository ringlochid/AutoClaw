# Inspect and control a task

Status: Reference

Once a task is running, use runtime outputs first and operator read surfaces second.

## Start with the task root

Inspect the generated files:

- `_runtime/workflow-manifest.md`
- `_runtime/attempts/<attempt_id>/assignment.md`
- `_runtime/attempts/<attempt_id>/latest-checkpoint.md`
- `outputs/artifacts/`

## Then use operator read surfaces

For broader runtime visibility, continue into the operator reference:

- [Runtime read models and operator surfaces](../reference/operator/runtime-read-models-and-operator-surfaces.md)
- [Inspect approvals and watchdog state](../reference/operator/inspect-approvals-and-watchdog.md)
- [OpenClaw integration boundary](../reference/operator/openclaw-integration-boundary.md)

## What to decide during inspection

- whether the current assignment stayed inside scope
- whether checkpoints and artifacts prove the intended progress
- whether a parent/root reviewer has enough evidence to close green
- whether the task is blocked and needs recovery, not just more waiting
