# Command run and external wait

Status: Target

This page owns the V2 controller-managed command-run source record, runner lifecycle, and external-wait continuation.

## Core rule

A worker uses `start_command_run` for shell work expected to exceed about two minutes or for any command that requires controller-owned background execution, timeout, logs, or cancellation.

Starting a command run closes the current dispatch and ends the provider response. It does not terminate the task, assignment, attempt, or plan, and it is not a `return_boundary` outcome.

Short commands normally remain inside the provider's ordinary tool lane. The command-run source is not a record of every shell command.

## State machine

The states are exactly:

```text
pending_start -> running -> succeeded
                         -> failed
                         -> timed_out
                         -> cancelled

pending_start -> cancellation_requested -> cancelled
running       -> cancellation_requested -> cancelled
```

`cancellation_requested` is non-terminal. The task remains waiting until the runner commits one of:

- `succeeded`
- `failed`
- `timed_out`
- `cancelled`

Runner process state is evidence used to commit this controller state; it is not a second runtime truth lane.

## Start contract

The node-facing request is:

```yaml
command_run_start_request:
    command: string
    description: string
    workdir: string | null
    timeout_seconds: integer | null
```

Rules:

- `command` is the exact human-readable invocation
- `description` explains why the task needs the command
- `workdir` is task-relative and uses the task-file resolver; null selects the task's default command working directory
- `timeout_seconds`, when present, is a positive integer
- request fields do not carry artifact schemas, human-request identifiers, or provider control

The successful response is:

```yaml
command_run_start_response:
    run_id: string
    task_id: string
    state: pending_start | running
```

Success means the source row and external-wait transition committed. The response instructs the worker to stop its response immediately without a terminal checkpoint or `return_boundary`.

## Source record

The controller-owned record is:

```yaml
command_run:
    run_id: string
    task_id: string
    flow_id: string
    flow_revision_id: string
    flow_node_id: string
    assignment_id: string
    attempt_id: string
    dispatch_id: string
    requester_node: string
    command: string
    description: string
    workdir: string | null
    timeout_seconds: integer | null
    state: >-
      pending_start | running | cancellation_requested | succeeded | failed |
      timed_out | cancelled
    created_at: timestamp
    started_at: timestamp | null
    ended_at: timestamp | null
    latest_update: string | null
    latest_log_ref: string | null
    cancellation_requested_at: timestamp | null
    cancellation_requested_by_actor_ref: string | null
    terminal_result:
        summary: string
        exit_code: integer | null
        signal: string | null
        log_ref: string | null
    terminal_event_source: controller | control_api | operator_mcp | null
    terminal_actor_ref: string | null
```

`terminal_result`, `ended_at`, and `terminal_event_source` are present only in a terminal state. `latest_update` is a bounded summary, not copied stdout or stderr.

One current command run may own one current task lineage. Historical runs stay readable but cannot clear or replace the current wait.

## Start legality

Starting is legal only when all of these are true:

- task, node session, dispatch, assignment, and attempt are current
- the worker already recorded the required progress checkpoint
- no human-request or command-run source wait currently owns the lineage
- effective `command_run` capability is `allow`
- the request and task-relative working directory validate

A rejected call creates no command row, waiting cause, dispatch closure, or standalone task event and does not advance `last_progress_at`.

## Atomic external-wait transition

The same shared close-for-external-wait controller operation used by human requests commits, atomically:

1. the new `command_run` row in `pending_start` or `running`
2. waiting cause `waiting_for_command_run` pointing to `run_id`
3. closure of the current `NodeSession`
4. dispatch status `closed` with `closed_reason = command_run_wait`
5. semantic invocation completion and `last_progress_at`
6. bounded `command_run_started` chronology

The operation does not:

- record a terminal checkpoint
- call `return_boundary`
- call adapter `stop`
- synthesize provider completion or failure
- retain a suspended dispatch
- wait for provider reconnect or provider output

The provider response ends naturally. Task, assignment, attempt, and `AttemptPlan` remain current. The command-run owner, not the execution watchdog, then monitors the source row.

## Runner ownership

The command-run manager owns:

- claiming `pending_start` work
- launching the local process in the validated task-relative workdir
- recording `started_at`
- appending stdout and stderr to the run log
- publishing bounded progress summaries
- enforcing the declared timeout
- handling cancellation
- committing exactly one terminal result
- recovering locally owned non-terminal runs after API restart

V2 remains one-process and local-tool-first. This contract does not require a remote queue, distributed worker, or provider adapter to run commands.

## Progress and logs

A runner update is:

```yaml
command_run_progress_update:
    run_id: string
    summary: string
    log_ref: string | null
    occurred_at: timestamp
```

The runner may also record its locally owned process identifier internally. That identifier is support state, not portable task truth.

Rules:

- frequent output is coalesced into bounded `command_run_progressed` updates
- progress does not invent percent complete, ETA, or provider lifecycle
- full stdout and stderr remain append-only behind `log_ref`
- ordinary task, snapshot, trace, and event reads never inline raw log bytes
- the dedicated log route may expose the complete retained log to an authorized caller

Command-run progress updates do not update a closed dispatch's watchdog clock. The source wait is monitored by the command-run manager instead.

## Terminal result

Terminal completion normalizes to:

```yaml
command_run_terminal_result:
    run_id: string
    state: succeeded | failed | timed_out | cancelled
    summary: string
    exit_code: integer | null
    signal: string | null
    log_ref: string | null
    ended_at: timestamp
```

For command-style work, `exit_code` plus runner legality determines succeeded or failed. Timeout and cancellation may have no exit code. `summary` states what happened and what the next dispatch should know first.

The terminal state and result commit together with the matching event:

| State       | Event                    |
| ----------- | ------------------------ |
| `succeeded` | `command_run_succeeded`  |
| `failed`    | `command_run_failed`     |
| `timed_out` | `command_run_timed_out`  |
| `cancelled` | `command_run_cancelled`  |

A stale process callback cannot change a terminal run or reopen a no-longer current task lineage.

## Cancellation and timeout

The dedicated cancel control targets one current non-terminal command run. It does not cancel the task.

When cancellation cannot complete in the same transaction, the controller commits:

```yaml
state: cancellation_requested
cancellation_requested_at: timestamp
cancellation_requested_by_actor_ref: string | null
```

That intent survives refresh. It does not clear `waiting_for_command_run` or authorize redispatch. The runner later commits `cancelled` after process termination.

Timeout is a first-class runner-owned terminal transition. Task cancellation may also force the current run to `cancelled`; later runner callbacks remain stale and cannot continue the cancelled task.

## Continuation

A terminal command state is terminal only for the command run. It is not terminal for task, assignment, attempt, or plan.

After terminal state commits, the controller:

1. confirms the run still owns `waiting_for_command_run`
2. clears that waiting cause
3. rereads task, structure, assignment, attempt, plan, checkpoint, and capability currentness
4. regenerates the complete prompt from controller truth
5. opens a new dispatch on the same assignment, attempt, and plan when legal

The normalized continuation context includes:

```yaml
command_run_continuation_context:
    run_id: string
    command: string
    description: string
    workdir: string | null
    state: succeeded | failed | timed_out | cancelled
    created_at: timestamp
    started_at: timestamp | null
    ended_at: timestamp
    timeout_seconds: integer | null
    latest_update: string | null
    terminal_result:
        summary: string
        exit_code: integer | null
        signal: string | null
        log_ref: string | null
```

Raw logs are not injected into ordinary prompts. The next worker may inspect a surfaced task-relative log when the controller makes that path available.

Provider session-hint reuse is optional. Controller context, plan, and checkpoint remain sufficient when the provider starts a fresh session.

Operator `continue` does not complete or clear a command run.

## Read and event surfaces

The control API owns list, detail, log, and cancel routes. The main event stream contains:

- `command_run_started`
- `command_run_progressed`
- `command_run_cancel_requested`
- `command_run_succeeded`
- `command_run_failed`
- `command_run_timed_out`
- `command_run_cancelled`

Events are bounded chronology derived from committed source state. They do not drive the runner or continuation.

## Required invariants

- a successful start owns no live dispatch or node-session authority
- start and dispatch closure commit atomically
- a non-terminal run keeps the task waiting
- exactly one terminal result owns one run
- only the current terminal source row may authorize continuation
- one terminal source transition can prepare at most one continuation dispatch
- provider stop, provider completion, and `return_boundary` are absent from the external-wait path

## Related contracts

- [Controller contract and resumable execution](controller-contract-and-resumable-execution.md)
- [Runtime lifecycle and watchdog](runtime-lifecycle-and-watchdog.md)
- [Attempt plan and checkpoint contract](attempt-plan-and-checkpoint-contract.md)
- [Human request and approval contract](../interfaces/human-request-and-approval-contract.md)
- [Capability, security, and audit](../interfaces/capability-security-and-audit.md)
- [Control API](../interfaces/control-api.md)
- [Task event stream](../interfaces/task-event-stream.md)
