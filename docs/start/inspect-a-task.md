# Inspect a task

Status: Reference

After a task starts, the important proof is in the runtime outputs and operator read surfaces.

## Generated task-root surfaces

Start with these files inside the task root:

- `_runtime/workflow-manifest.md`
- `_runtime/attempts/<attempt_id>/assignment.md`
- `_runtime/attempts/<attempt_id>/latest-checkpoint.md`
- `outputs/artifacts/`

The workflow manifest explains the current workflow shape. The assignment file shows the current node mission. The latest checkpoint records durable progress or terminal handoff. `outputs/artifacts/` holds published outputs.

## Observability-only files

Dispatch-local support-state files are useful for debugging transport and recovery, but they are not the ordinary task source of truth:

- `_runtime/dispatch/<dispatch_id>/delivery-state.json`
- `_runtime/dispatch/<dispatch_id>/continuity-state.json`
- `_runtime/dispatch/<dispatch_id>/watchdog-state.json`

## Operator read surfaces

Use the operator reference when you want runtime readbacks beyond the task root:

- [Runtime read models and operator surfaces](../reference/operator/runtime-read-models-and-operator-surfaces.md)
- [Inspect approvals and watchdog state](../reference/operator/inspect-approvals-and-watchdog.md)

For the concept behind these files and read models, see the [runtime model](../concepts/runtime-model.md).

## What to check

- the task used the workflow you expected
- the assigned node published the outputs the workflow declared
- the latest checkpoint matches the work that actually happened
- artifacts and surfaced evidence are consistent with the runtime state

## Next step

If the seeded minimal workflow makes sense, continue by writing your own [role](../guides/write-a-role.md), [policy](../guides/write-a-policy.md), or [workflow](../guides/write-a-workflow.md).
