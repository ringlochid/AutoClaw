# Command run and long-running boundary

Status: Target

This page defines how V2 handles long-running command executions such as `pytest`, builds, linters, capture scripts, and other shell work that is expected to exceed about two minutes or otherwise cannot safely stay inside one model turn.

## Core rule

The controller must treat a long-running command start as a special node MCP action that opens a controller-owned async wait.

A node should use this lane when the command is expected to exceed about two minutes or otherwise needs controller-managed async waiting. Shorter command work should usually stay inline inside the ordinary dispatch execution path rather than opening controller-owned command-run state.

It is not:

- "sleep inside the turn until something happens"
- an ordinary workflow egress boundary such as `yield`, `green`, `retry`, or `blocked`

## Command-run model

A command run is a controller-owned long-running command execution started by a legal node action and later resumed from controller-owned terminal command truth.

Canonical command-run states are:

- `pending_start`
- `running`
- `cancellation_requested`
- `succeeded`
- `failed`
- `timed_out`
- `cancelled`

Canonical terminal task-event mapping:

| Job state | Task event |
| --- | --- |
| `succeeded` | `command_run_succeeded` |
| `failed` | `command_run_failed` |
| `timed_out` | `command_run_timed_out` |
| `cancelled` | `command_run_cancelled` |

Rules:

- one job belongs to exactly one task lineage
- one command run record represents one command execution
- one command run record is for controller-managed long command work, not every incidental short shell step
- job status is controller truth, not process-local truth
- command-run start creates `waiting_for_command_run` directly rather than through workflow boundary acceptance
- command-run start does not require a prior accepted workflow boundary
- the controller does not open the next ordinary node dispatch until the command reaches a terminal state
- support files may mirror command-run state, but controller-owned command-run records stay authoritative
- `command_run_progressed` may exist as a controller-owned update family, but the contract does not require percent complete, ETA, elapsed time, or other invented progress metrics
- accepted cancellation may move the run into `cancellation_requested`, but that non-terminal state still keeps the task waiting until final command-run closure commits

## Controller-owned source shape

The controller should persist command-run truth in an explicit shape such as:

```yaml
command_run:
  run_id: string
  task_id: string
  dispatch_id: string
  attempt_id: string | null
  command: string
  description: string
  workdir: string | null
  state: pending_start | running | cancellation_requested | succeeded | failed | timed_out | cancelled
  created_at: timestamp
  started_at: timestamp | null
  ended_at: timestamp | null
  timeout_seconds: integer | null
  latest_update: string | null
  latest_log_ref: string | null
  terminal_result:
    summary: string | null
    exit_code: integer | null
    signal: string | null
    log_ref: string | null
```

Rules:

- `command` is the human-readable invocation, for example `pytest apps/api/tests/unit/runtime -q`
- `description` is why this command exists in task terms
- `workdir` is null when the current task root or default working directory is sufficient
- `latest_update` is a bounded controller summary, not a raw log stream
- `terminal_result` is null until the command reaches a terminal state

## Start request shape

The node-facing command-run start path should normalize into a bounded controller request such as:

```yaml
command_run_start_request:
  command: string
  description: string
  workdir: string | null
  timeout_seconds: integer | null

command_run_start_response:
  run_id: string
  task_id: string
  state: pending_start | running
```

Rules:

- the start request should explain what will run and why the task needs it
- nodes should open `command_run` when they expect the command to exceed about two minutes or otherwise need controller-managed async waiting
- command-run start is not coupled to the human-request lane
- command-run start does not carry artifact-slot contracts, result schemas, or human-request references
- the start response is an acknowledgement that controller truth was persisted; it is not the source of current command-run state

## Start behavior

Starting a command run must:

1. validate that the current node policy allows command-run creation
2. persist a new command-run record with controller-owned identity
3. persist the controller waiting cause as `waiting_for_command_run`
4. emit task events for command-run creation and task waiting
5. return control without keeping the model turn open

This path creates the external wait directly. It does not use workflow boundary-acceptance semantics, and later continuation comes from `command_run_terminal`, not from an accepted workflow egress boundary.

The start path must also persist:

- the task lineage identifiers needed for controller continuation
- the command and description
- the working directory when relevant
- any declared timeout

## Progress-update shape

When the controller persists a progress update or emits `command_run_progressed`, the normalized payload should look like:

```yaml
command_run_progress_update:
  run_id: string
  summary: string
  log_ref: string | null
  occurred_at: timestamp
```

Rules:

- progress is a bounded textual update, not a pseudo-metrics model
- `summary` should be short enough to render in a job list row or event thread
- if the runner emits frequent output, the controller should coalesce it into bounded updates rather than mirror every raw line as controller truth

## Terminal behavior

When the command reaches a terminal state, the controller must:

1. persist the terminal command-run state
2. persist a compact normalized terminal result plus any log ref needed for later inspection
3. emit the matching terminal task event
4. leave the task lineage in database state that the controller loop can evaluate
5. open the next dispatch only when the task lineage is still current and the waiting cause still matches

The terminal-job path must not mint a new task lineage merely because the command completed later.

Provider session continuation may be reused for the redispatch when lawful, but controller command-run lineage continuation is the required behavior.

## Command result normalization

For command-style jobs such as `pytest`, `pnpm test`, `ruff check`, browser captures, or packaging commands:

- controller success or failure should be derived from command exit status plus any runner-specific legality checks
- `exit_code` and `signal` are the minimum normalized terminal fields for later prompt continuation and UI inspection
- controller truth should store a compact verdict summary such as `all targeted tests passed` or `2 tests failed during collection`
- full stdout/stderr or other bulky output may live in logs referenced by `log_ref` rather than inline in controller rows

## Terminal result shape

Terminal command-run completion should normalize into a bounded controller result such as:

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

Rules:

- `state` is the controller outcome class
- `summary` should answer "what happened and what should the next dispatch know first"
- `exit_code` is null for non-exit-based terminal states such as controller timeout or operator cancellation

## Cancellation and timeout

Timeout and cancellation are first-class terminal outcomes.

Rules:

- timeout must be controller-visible and persisted even if the underlying worker process disappears without a clean callback
- operator task pause and task cancel remain separate runtime controls; they are not command-run start legality checks
- a dedicated operator or UI command-run cancel action may target the currently running command run without cancelling the whole task
- when the controller accepts cancellation before terminal worker closure is committed, it should persist `state: cancellation_requested` as the durable non-terminal current state
- `cancellation_requested` survives refresh and reread so other control surfaces do not have to infer accepted cancel intent from local UI memory
- `cancellation_requested` is not terminal and must not clear the waiting cause or reopen the next dispatch by itself
- task cancellation may close the current command run as `cancelled`, and any later callback for that old run must not reopen work when the task lineage is no longer current
- operator cancellation and controller cancellation both land as `cancelled`, but the event payload must distinguish who initiated it
- timeout, cancellation, and failure all land through the same terminal-job database-state path

## Log handling

Command runs may emit append-only logs.

Rules:

- controller-owned command-run records own normalized command truth, not every raw byte emitted by the runner
- full stdout/stderr and similar bulky output should live in logs referenced from the command-run record
- large logs stay out of ordinary prompt truth unless surfaced intentionally later
- control UI/API reads may inspect job logs directly through the dedicated follow-up route family `GET /control/tasks/{task_id}/command-runs/{run_id}` and `GET /control/tasks/{task_id}/command-runs/{run_id}/log`
- the pre-UI lane does not truncate or reduce persisted command-run logs or terminal summaries before those controller-owned reads expose them
- control UI/API should default to compact summaries first and let humans inspect logs through explicit follow-up reads when needed
- prompt surfaces should consume compact summaries and deliberate log refs, not raw log streams by default

## Continuation prompt contract

When a terminal command run triggers continuation of the same task lineage, the next dispatch prompt should receive a normalized controller packet such as:

```yaml
command_run_continuation_context:
  run_id: string
  command: string
  description: string
  workdir: string | null
  state: succeeded | failed | timed_out | cancelled
  created_at: timestamp
  started_at: timestamp | null
  ended_at: timestamp | null
  timeout_seconds: integer | null
  latest_update: string | null
  terminal_result:
    summary: string
    exit_code: integer | null
    signal: string | null
    log_ref: string | null
```

Rules:

- the continuation prompt must include the original command and description, not only the terminal outcome
- command-like jobs such as `pytest` must carry `exit_code` plus a compact verdict summary so the next dispatch can reason without scraping logs
- created, started, ended, and timeout fields are part of the continuation truth because they explain whether the command completed, failed fast, or hit timeout
- large logs stay out of ordinary prompt truth by default; prompt truth should use the terminal summary plus a deliberate `log_ref` when needed
- provider or adapter session scope should be reused when it is still lawful and available, but a stale or unsafe provider session must not outrank controller-owned command-run source truth

## Non-goals

This contract does not define:

- the concrete local process runner
- the concrete remote queue or worker technology
- any adapter-specific job transport

Those implementation details must fit beneath this controller-owned contract.

## Related contracts

- [Controller contract and resumable execution](controller-contract-and-resumable-execution.md)
- [Control API and task event stream](../interfaces/control-api-and-task-event-stream.md)
- [Capability, security, and audit](../interfaces/capability-security-and-audit.md)
