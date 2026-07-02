# Inspect a task

After a task starts, inspect generated runtime files and operator read surfaces before reading logs or transcripts.

## Generated task-root surfaces

AutoClaw materializes these files under the task root:

- `_runtime/workflow-manifest.md`
- `_runtime/attempts/<attempt_id>/assignment.md`
- `_runtime/attempts/<attempt_id>/latest-checkpoint.md`
- `outputs/artifacts/`

The workflow manifest explains the current workflow shape. The assignment file shows the current node mission. The latest checkpoint records durable progress or terminal handoff. `outputs/artifacts/` holds published outputs.

## What to check

- the task used the workflow you expected
- the current assignment has explicit scope and evidence requirements
- the assigned node published the outputs the workflow declared
- the latest checkpoint matches the work that actually happened
- artifacts and surfaced evidence are consistent with runtime state
- any wait is a real human request or command run, not an absence of output

## Observability-only files

Dispatch-local support files can help debug transport and recovery, but they are not ordinary task truth:

- `_runtime/dispatch/<dispatch_id>/delivery-state.json`
- `_runtime/dispatch/<dispatch_id>/continuity-state.json`
- `_runtime/dispatch/<dispatch_id>/watchdog-state.json`

Use them after reading task-root evidence and operator readbacks.

## Operator read surfaces

Use the operator reference when you need controller readbacks beyond generated files:

- [Runtime read models and operator surfaces](../reference/operator/runtime-read-models-and-operator-surfaces.md)
- [Inspect approvals and watchdog state](../reference/operator/inspect-approvals-and-watchdog.md)

For the concept behind these files and read models, see the [runtime model](../concepts/runtime-model.md).

## Next step

If the seeded topic-research workflow makes sense, continue by writing your own [role](../guides/write-a-role.md), [policy](../guides/write-a-policy.md), or [workflow](../guides/write-a-workflow.md).
