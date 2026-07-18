---
name: "autoclaw-runtime-operator"
description: "Operate existing AutoClaw tasks through operator MCP: inspect runtime state, resolve human requests, handle command runs, control tasks, and read or start definitions when explicitly asked. Use when the user mentions a task id or a running/waiting/stuck/paused AutoClaw task, asks why a task is waiting, or wants a task paused, continued, cancelled, or recovered. Not the entry point for new 'use AutoClaw to do X' requests — route those to autoclaw-task-interview and autoclaw-work-orchestrator."
---

# autoclaw-runtime-operator

Use this skill when the user asks you to inspect, monitor, control, recover, or launch AutoClaw tasks as an operator.

This is an AutoClaw usage skill. Do not turn routine operation into implementation debugging unless the user explicitly asks for that different job.

Scope guard: this skill operates tasks that already exist. When the user asks to use AutoClaw for new work ("use AutoClaw to build X"), that is intake, not operation — route to `autoclaw-task-interview` and `autoclaw-work-orchestrator`.

## Operating Model

AutoClaw separates four planes:

- authoring: reusable role, policy, and workflow definitions
- launch: one task-compose body
- runtime: controller-owned task, flow, assignment, checkpoint, artifact, boundary, wait, and replan truth
- operator: trusted read/control surfaces over runtime truth

Your default operator lane is AutoClaw operator MCP. HTTP routes are fallback or explicit API work. Task-root files and support refs are useful readbacks, but controller/runtime truth wins when they disagree.

## Tool Lanes

Use operator MCP for:

- finding tasks: `list_runtime_tasks`
- status/currentness: `get_runtime_task`
- current operator view: `get_operator_snapshot`
- chronology: `get_operator_trace`
- human requests: `get_human_requests`, `resolve_human_request`
- command runs: `get_command_runs`, `get_command_run`, `get_command_run_log`, `cancel_command_run`
- task controls: `pause_task`, `continue_task`, `cancel_task`
- definition registry reads: `search_definitions`, `get_definition`, `list_definition_versions`
- trusted writes when explicitly authorized: `upload_definition`, `start_task`
- definition draft authoring stays on the trusted HTTP `/authoring` API, not operator MCP
- support refs for deep diagnosis: `get_delivery_state_ref`, `get_continuity_state_ref`, `get_watchdog_state_ref`, `get_provider_events_ref`

Do not use Node MCP for operator work. Node operations such as `record_checkpoint`, `return_boundary`, `assign_child`, `release_green`, and `release_blocked` belong to the current node dispatch. For experimental OpenClaw, the user configures the `/node/mcp` compatibility server and its tool policy; AutoClaw does not inject or maintain that OpenClaw configuration. Every compatibility call supplies the full current `task_id` and `dispatch_id`. Those IDs select controller scope and do not grant operator authority. Operator MCP is a separate locally admitted surface and never inherits Node authority.

## Inspection Order

Answer every status question from a fresh read, never from conversation memory — task state moves between turns. When the user names a task loosely ("the MVP task"), resolve it with `list_runtime_tasks` instead of assuming an id.

When the user gives a `task_id`, inspect before changing anything:

1. `get_runtime_task` for status, current node, and fresh `active_flow_revision_id`.
2. `get_operator_snapshot` for current actionable state and current paths.
3. `get_operator_trace` when chronology matters.
4. `get_human_requests` if status or snapshot indicates a human wait.
5. `get_command_runs` if status or snapshot indicates a command-run wait.
6. Support refs only for deeper diagnosis: delivery, continuity, watchdog, provider events.

Do not use `continue_task` as polling. It is a pause-resume write and needs fresh currentness.

## Human Requests

Human requests are typed waits for human judgment: `direction`, `approval`, `input`, or `review`.

Resolution path:

1. Inspect runtime state and the current open request.
2. Read every request item, options, recommendation, timeout/default behavior, and suggested human instruction.
3. If the user must decide, ask the smallest useful question and include the available options. Do not silently choose for the user unless they explicitly authorized that choice.
4. Submit the answer with `resolve_human_request` using item-scoped `selected_option` or `freeform_answer`, plus `extra_notes` or `response_payload` only when needed.
5. Re-read task runtime/snapshot after resolution.

Do not resolve a human request with `continue_task`. Do not treat human requests as status updates or ordinary chat continuation.

## Command Runs

Command runs are controller-managed long command work. They are for commands expected to exceed a normal dispatch, roughly over two minutes, or that need controller-owned logs, terminal state, or cancellation.

Operator path:

1. Use `get_command_runs` to find the run id and state.
2. Use `get_command_run` for detail when needed.
3. Use `get_command_run_log` only when a log ref exists.
4. Use `cancel_command_run` only for the command run itself; do not cancel the whole task when only the command run is the problem.
5. Re-read task runtime/snapshot after terminal command-run state.

Do not invent progress percentages, ETA, or pseudo-metrics. Use controller summaries and logs.

## Task Controls

Pause, continue, and cancel are mutating operator controls.

Rules:

- inspect first
- use a fresh `expected_active_flow_revision_id`
- pause only to intentionally stop forward progress
- continue only to resume a paused task
- cancel only when the user wants the task stopped
- prefer narrow controls, such as human-request resolution or command-run cancel, when they match the problem

Task cancellation may close pending waits. It is not a substitute for answering a human request or cancelling one command run.

## Recovery And Replan Judgment

Start with evidence, not waiting time:

- quiet dispatch is not proof of stuckness
- child green is evidence, not automatic closure
- child blocked is routing input, not automatic whole-flow failure
- support refs are diagnostics, not semantic truth

Use retry when the assignment shape is still correct and another attempt can progress.

Use replan when the workflow shape is wrong: missing work lane, invalid dependency path, repeated failure from the same assignment shape, or intent mismatch between user purpose and current flow.

Use blocked closure when required facts, permissions, tools, or external state are unavailable and retry would repeat the same failure. Blocked closure should have current terminal evidence.

## Definition And Task Start Writes

Registry and task-start writes are external AutoClaw mutations.

Before `upload_definition` or `start_task`:

- inspect current registry candidates when selection matters
- confirm the local file path is the intended artifact
- check that the user has asked to upload/start, or ask for explicit approval
- prefer task-compose launch for one run; do not put reusable behavior in task-compose

After `start_task`, capture the task id, confirm the task is running with one readback, report it to the user, and stop. Do not keep polling, watching, or resolving waits on your own; the user will ask for status or results when they want them. Supervise continuously only when the user explicitly asked for that.

## Status And Result Queries

When the user later asks how a task is going or what it produced, answer from a fresh read: `get_runtime_task` and `get_operator_snapshot` for status, then artifact refs and the task workspace paths for results. Report open waits (human requests, command runs) as part of status, but act on them only when the user says to.

## Related Skills

- Use `autoclaw-task-interview` when the user asks for new AutoClaw work and scope, workflow shape, or `roots` paths are unconfirmed.
- Use `autoclaw-work-orchestrator` when the question is how to shape a user request into AutoClaw work.
- Use `autoclaw-definition-author` when the task requires role, policy, workflow, or task-compose YAML.
