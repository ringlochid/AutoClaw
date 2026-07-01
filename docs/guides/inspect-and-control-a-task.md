# Inspect and control a task

Use runtime outputs first and operator read surfaces second. A provider run finishing is not enough; AutoClaw task progress is proven by assignment-scoped evidence.

## Inspection order

1. Confirm the selected workflow and current node in the manifest.
2. Read the current assignment.
3. Read the latest checkpoint for that attempt.
4. Inspect published artifacts.
5. Check provider or harness tool usage.
6. Read operator snapshot and trace when the task needs broader state context.
7. Inspect human requests or command runs if the task is waiting.

## Task-root files

Start with the generated files:

- `_runtime/workflow-manifest.md`
- `_runtime/attempts/<attempt_id>/assignment.md`
- `_runtime/attempts/<attempt_id>/latest-checkpoint.md`
- `outputs/artifacts/`

The manifest explains the current workflow shape. The assignment file shows the bounded mission. The checkpoint records progress or terminal handoff. Artifacts hold durable outputs that later nodes and operators can inspect.

If a generated file and controller readback disagree, trust controller/runtime state.

## Provider and tool usage

Inspect the real harness surface when tool behavior matters. In the OpenClaw adapter path, use OpenClaw console/session views to confirm:

- the expected tools were available
- the node actually used the required tools
- command output or browser evidence matches the checkpoint
- visual, PDF, browser, or service tools worked in the real environment
- the model did not silently skip a required verification step

This catches workflow design mistakes that task-root files alone may not reveal, such as a missing browser configuration, unavailable local tool, or unsupported provider capability.

## Operator read surfaces

For broader runtime visibility, continue into operator readbacks:

- [Runtime read models and operator surfaces](../reference/operator/runtime-read-models-and-operator-surfaces.md)
- [Inspect approvals and watchdog state](../reference/operator/inspect-approvals-and-watchdog.md)
- [OpenClaw integration boundary](../reference/operator/openclaw-integration-boundary.md)

Use snapshot and trace to answer:

- which node is current?
- which assignment and attempt are current?
- is the task waiting on human input or command completion?
- did retry or replan occur?
- what events led to the current state?

## What to validate

Check the run against the workflow contract:

- did each node do the work its assignment asked for?
- did the node stay inside scope?
- did tool usage match the workflow assumptions?
- did produced artifacts match declared slots?
- did the checkpoint explain progress, criteria status, and residual risk?
- did the boundary match the checkpoint?
- did parent/root release only after inspecting current child evidence?
- did retry or replan happen for the right reason?

## Waiting tasks

If a task is waiting, identify the source wait:

- human request: inspect request kind, question, allowed resolution path, and response
- command run: inspect command state, logs, timeout/cancellation state, and continuation

Do not treat "quiet" as stuck. A quiet task may be correctly waiting on a controller-owned human request or command run.

## When to intervene

Intervene when:

- the assignment is wrong or too broad
- required tools are unavailable
- checkpoint evidence is weak or inconsistent with artifacts
- a child returned green without satisfying criteria
- repeated retries show the assignment shape is wrong
- the task is waiting on a request or command that needs operator action

Use retry for another attempt at the same assignment shape. Use replan when the workflow shape is wrong.

## Related pages

- [Runtime model](../concepts/runtime-model.md)
- [Recover or replan a task](recover-or-replan-a-task.md)
- [Use human requests](use-human-requests.md)
- [Use long command runs](use-long-command-runs.md)
