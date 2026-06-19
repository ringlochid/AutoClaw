# Async job and long-running boundary

Status: Target

This page defines how Vnext handles long-running commands, background jobs, and other work that cannot safely stay inside one model turn.

## Core rule

The controller must treat long-running work as an explicit async boundary, not as "sleep inside the turn until something happens."

## Async job model

An async job is controller-owned work that was started by a legal node action, persists independently of the current model turn, and later allows the controller to continue the same task lineage from a terminal job result.

Canonical async job states are:

- `pending_start`
- `running`
- `succeeded`
- `failed`
- `timed_out`
- `cancelled`

Canonical terminal task-event mapping:

| Job state | Task event |
| --- | --- |
| `succeeded` | `async_job_succeeded` |
| `failed` | `async_job_failed` |
| `timed_out` | `async_job_timed_out` |
| `cancelled` | `async_job_cancelled` |

Rules:

- one job belongs to exactly one task lineage
- job status is controller truth, not process-local truth
- logs and produced artifacts may continue to accumulate while the task is waiting, but the controller does not open the next ordinary node dispatch until the job reaches a terminal state or is explicitly cancelled
- support files may mirror job state, but controller-owned async-job records stay authoritative
- `async_job_progressed` may exist as a controller-owned progress event family, but the contract does not require percent complete, ETA, elapsed time, or other numeric progress metrics

## Controller-owned source shape

The controller should persist async-job truth in an explicit shape such as:

```yaml
async_job:
  job_id: string
  task_id: string
  flow_revision_id: string
  dispatch_id: string
  attempt_id: string | null
  requester_node: string
  job_kind: string
  title: string
  summary: string
  command_summary: string | null
  launch_ref: string | null
  state: pending_start | running | succeeded | failed | timed_out | cancelled
  created_at: timestamp
  started_at: timestamp | null
  ended_at: timestamp | null
  timeout:
    requested_seconds: integer | null
    deadline_at: timestamp | null
  output_contract:
    artifact_slots:
      - string
    result_schema: object | null
  latest_progress:
    progress_seq: integer
    summary: string
    detail: string | null
    log_ref: string | null
    occurred_at: timestamp
  terminal_result:
    termination_reason: completed | non_zero_exit | signal | launch_failed | timed_out | cancelled
    summary: string | null
    detail: string | null
    exit_code: integer | null
    signal: string | null
    output_payload: object | null
    artifact_refs:
      - string
    log_refs:
      - string
```

Rules:

- `title` is the compact UI label for the job, for example `run-targeted-pytest`
- `summary` is why the job exists in task terms, not a raw log excerpt
- `command_summary` is the compact human-readable invocation summary when the job is command-like; the full raw invocation may live behind `launch_ref`
- `command_summary` and `launch_ref` are null when the job is not command-like
- `output_contract` names what later readers expect from the job, for example artifact slots or a small typed result payload
- `latest_progress` is the current compact controller summary, not an append-only log replacement, and may be null before the first progress update
- `terminal_result` is null until the job reaches a terminal state

## Start request shape

The node-facing async-job start path should normalize into a bounded controller request such as:

```yaml
async_job_start_request:
  job_kind: string
  title: string
  summary: string
  command_summary: string | null
  launch_ref: string | null
  timeout:
    requested_seconds: integer | null
  output_contract:
    artifact_slots:
      - string
    result_schema: object | null
  prior_human_request_id: string | null
```

Rules:

- the start request should explain both what will run and why the task needs it
- `launch_ref` may point to a saved invocation spec, script, or runner-owned payload when the full launch body is too large or too implementation-specific for the controller row
- `prior_human_request_id` is the audit link when the job start followed an explicit human approval or direction step

## Start behavior

Starting an async job must:

1. validate that the current node policy allows async job creation
2. persist a new async-job record with controller-owned identity
3. persist the controller waiting cause as `waiting_for_async_job`
4. emit task events for job creation and task waiting
5. return control without keeping the model turn open

The start path must also persist:

- the task lineage identifiers needed for controller continuation
- the normalized command or job kind plus compact human-readable title and summary
- any declared timeout
- any declared output or artifact destination contract

## Risk judgment rule

Async-job start does not depend on AutoClaw parsing command text to detect destructive or privileged behavior.

Instead:

- node, role, policy, workflow, and prompt instructions teach the model when a job is risky enough to ask for human approval first
- the node may open a typed human request before starting the job when policy allows it
- the async-job start payload may carry a prior human-request reference when the start followed an approval or direction step
- the controller validates declared state and capability, but it does not treat raw shell syntax as canonical risk truth
- concrete runners may add local safety checks, but those checks are implementation guardrails below the controller contract

## Progress-update shape

When the controller persists a progress update or emits `async_job_progressed`, the normalized payload should look like:

```yaml
async_job_progress_update:
  job_id: string
  progress_seq: integer
  summary: string
  detail: string | null
  log_ref: string | null
  occurred_at: timestamp
```

Rules:

- progress is textual stage/reporting truth, not an implied percent-complete model
- `summary` should be short enough to render in a job list row or event thread
- `detail` may add bounded context such as the current test phase or capture stage
- if the runner emits frequent output, the controller should coalesce it into bounded progress updates rather than mirror every raw line as controller truth

## Terminal behavior

When the job reaches a terminal state, the controller must:

1. persist the terminal async-job state
2. persist any normalized result summary plus log and artifact refs, plus any small typed fields the controller needs for later legality or continuation
3. emit the matching terminal task event
4. leave the task lineage in database state that the controller loop can evaluate
5. open the next dispatch only when the task lineage is still current and the waiting cause still matches

The terminal-job path must not mint a new task lineage merely because the job completed later.

## Command-style normalization

Many async jobs are long-running command-style executions such as `pytest`, `pnpm test`, `ruff check`, browser capture scripts, or packaging commands.

For command-like jobs:

- `command_summary` should name the human-readable invocation, for example `pytest apps/api/tests/unit/runtime -q`
- controller success or failure should be derived from the declared success contract, usually command exit status plus any runner-specific legality checks
- `terminal_result.termination_reason`, `terminal_result.exit_code`, and `terminal_result.signal` are the minimum normalized terminal fields for later prompt continuation and UI inspection
- controller truth should store a compact verdict summary such as `2 tests failed during collection` or `all targeted tests passed` instead of forcing later readers to reconstruct the outcome from raw stdout
- full stdout/stderr, junit XML, screenshots, or bulky machine output may live behind refs rather than inline in controller rows

## Terminal result shape

Terminal async-job completion should normalize into a bounded controller result such as:

```yaml
async_job_terminal_result:
  job_id: string
  state: succeeded | failed | timed_out | cancelled
  termination_reason: completed | non_zero_exit | signal | launch_failed | timed_out | cancelled
  summary: string
  detail: string | null
  exit_code: integer | null
  signal: string | null
  output_payload: object | null
  artifact_refs:
    - string
  log_refs:
    - string
  ended_at: timestamp
```

Rules:

- `state` is the controller outcome class; `termination_reason` is the lower-level normalized reason
- `summary` should answer "what happened and what should the next dispatch know first"
- `output_payload` is for small typed fields only, for example a test-count summary or a compact capture manifest
- the controller should not inline bulky raw output into `output_payload`

## Cancellation and timeout

Timeout and cancellation are first-class terminal outcomes.

Rules:

- timeout must be controller-visible and persisted even if the underlying worker process disappears without a clean callback
- operator cancellation and controller cancellation both land as `cancelled`, but the event payload must distinguish who initiated it
- timeout, cancellation, and failure all land through the same terminal-job database-state path

## Log and artifact handling

Async jobs may emit:

- append-only logs
- structured result summaries
- produced artifact refs

Rules:

- controller-owned async-job records own normalized job truth, not every raw byte emitted by the runner
- full raw result bodies, bulky JSON payloads, stdout/stderr dumps, and similar large outputs should usually live in task-root result or log files referenced from the async-job record
- large logs stay out of ordinary prompt truth unless surfaced intentionally later
- control UI/API reads may inspect job logs directly
- control UI/API may show textual latest progress or stage summaries when they exist, but must not invent numeric progress displays that the controller did not persist
- control UI/API should default to compact summaries first and let humans inspect full result files or logs through explicit follow-up reads when needed
- file-backed raw outputs are convenience and audit surfaces, not replacements for controller-owned job state and normalized summary
- prompt surfaces should consume compact summaries or deliberate refs, not raw log streams by default

## Continuation prompt contract

When a terminal async job triggers continuation of the same task lineage, the next dispatch prompt should receive a normalized controller packet such as:

```yaml
async_job_continuation_context:
  job_id: string
  job_kind: string
  title: string
  summary: string
  requester_node: string
  command_summary: string | null
  output_contract:
    artifact_slots:
      - string
    result_schema: object | null
  terminal_result:
    state: succeeded | failed | timed_out | cancelled
    termination_reason: completed | non_zero_exit | signal | launch_failed | timed_out | cancelled
    summary: string
    detail: string | null
    exit_code: integer | null
    signal: string | null
    output_payload: object | null
    artifact_refs:
      - string
    log_refs:
      - string
  latest_progress:
    progress_seq: integer
    summary: string
    detail: string | null
    log_ref: string | null
    occurred_at: timestamp
```

Rules:

- the continuation prompt must include the original job purpose (`title` and `summary`), not only the terminal outcome
- command-like jobs such as `pytest` must carry `exit_code` and a compact verdict summary so the next dispatch can reason without scraping logs
- `output_payload` and produced artifact refs are the structured handoff for later node work
- large logs stay out of ordinary prompt truth by default; prompt truth should use `summary`, bounded `detail`, and deliberate refs

## Non-goals

This contract does not define:

- the concrete local process runner
- the concrete remote queue or worker technology
- any adapter-specific job transport

Those implementation details must fit beneath this controller-owned contract.

## Related contracts

- [Controller contract and resumable execution](controller-contract-and-resumable-execution.md)
- [Human request and approval contract](../interfaces/human-request-and-approval-contract.md)
- [Control API and task event stream](../interfaces/control-api-and-task-event-stream.md)
- [Capability, security, and audit](../interfaces/capability-security-and-audit.md)
