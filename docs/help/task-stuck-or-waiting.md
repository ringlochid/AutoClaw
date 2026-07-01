# Task stuck or waiting

Use this page when a task exists but appears stuck, waiting, stale, paused, or unclear.

## Observe first

Read controller-owned runtime state before using a control action.

Recommended reads:

- runtime task read
- operator snapshot
- operator trace
- pending human requests
- command runs
- watchdog state only when support-file inspection is needed

If you use operator MCP, the observe-first sequence is:

- `get_runtime_task`
- `get_operator_snapshot`
- `get_operator_trace`

Use observability refs only after current runtime state is understood.

## Waiting on human request

A human request is a controller-visible typed wait for human judgment. It can be:

- `direction`
- `approval`
- `input`
- `review`

Check:

- `GET /control/tasks/{task_id}/human-requests`
- operator snapshot actionable items
- operator trace around the wait-opening dispatch

Fix:

- resolve the pending human request through the control or operator surface
- answer the request narrowly
- do not use human requests as status updates or generic chat continuation
- do not resolve it by editing task-root files or continuing an unrelated chat

## Waiting on command run

A command run is controller-managed long command work. It is separate from ordinary inline shell use.

Check:

- `GET /control/tasks/{task_id}/command-runs`
- command-run state, terminal summary, exit code, signal, and log ref

Fix:

- inspect the command-run log ref when present
- request command-run cancellation only for the active nonterminal run
- do not cancel the whole task when only the command run is the problem

Ordinary commands should run inline and finish comfortably under about two minutes. Long command runs are for command work that needs controller-owned progress, logs, terminal state, or cancellation.

## Paused or cancelled task

Check current runtime state and active flow revision:

- `GET /runtime/tasks/{task_id}`
- `GET /operator/tasks/{task_id}/snapshot`

Use continue only as a mutating control action, not as a polling command. It needs a fresh `expected_active_flow_revision_id` from a current runtime read.

## Watchdog or stale dispatch

Do not treat quiet output as proof that a task is stuck.

Check:

- operator trace
- latest checkpoint
- current boundary history
- `GET /observability/tasks/{task_id}/watchdog-state` when deeper support-file inspection is needed

Support-state files are readback aids. Controller-owned runtime state wins when a support reread disagrees with current runtime truth.

## Retry, replan, or block

Use retry when the assignment shape is still correct and another attempt can make progress.

Use replan when the workflow shape is wrong for the task.

Block when required facts, permissions, tools, or external state are unavailable and retry would repeat the same failure.

## Related pages

- [Recover or replan a task](../guides/recover-or-replan-a-task.md)
- [Use human requests](../guides/use-human-requests.md)
- [Use long command runs](../guides/use-long-command-runs.md)
- [Runtime read models and operator surfaces](../reference/operator/runtime-read-models-and-operator-surfaces.md)
