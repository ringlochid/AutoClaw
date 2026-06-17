# Async job and long-running boundary

Status: Target

This page defines how Vnext handles long-running commands, background jobs, and other work that cannot safely stay inside one model turn.

## Core rule

The controller must treat long-running work as an explicit async boundary, not as "sleep inside the turn until something happens."

## Async job model

An async job is controller-owned work that was started by a legal node action, persists independently of the current model turn, and later wakes the same task lineage with a terminal job result.

Canonical async job states are:

- `pending_start`
- `running`
- `succeeded`
- `failed`
- `timed_out`
- `cancelled`

Rules:

- one job belongs to exactly one task lineage
- job status is controller truth, not process-local truth
- logs and produced artifacts may continue to accumulate while the task is waiting, but the task does not reopen ordinary node execution until the job reaches a terminal state or is explicitly cancelled
- support files may mirror job state, but controller-owned async-job records stay authoritative

## Start behavior

Starting an async job must:

1. validate that the current node policy allows async job creation
2. persist a new async-job record with controller-owned identity
3. persist the controller waiting cause as `waiting_for_async_job`
4. emit operator events for job creation and task waiting
5. return control without keeping the model turn open

The start path must also persist:

- the task lineage identifiers needed for wake
- the normalized command or job kind
- any declared timeout
- any declared output or artifact destination contract

## Terminal behavior

When the job reaches a terminal state, the controller must:

1. persist the terminal async-job state
2. persist any normalized result summary plus log and artifact refs
3. emit the matching terminal operator event
4. create a `resume_trigger_record` with cause `async_job_terminal`
5. recompute legality and wake the same task lineage when the task is still current

The wake path must not mint a new task lineage merely because the job completed later.

## Cancellation and timeout

Timeout and cancellation are first-class terminal outcomes.

Rules:

- timeout must be controller-visible and persisted even if the underlying worker process disappears without a clean callback
- operator cancellation and controller cancellation both land as `cancelled`, but the event payload must distinguish who initiated it
- timeout, cancellation, and failure all wake the same task lineage through the same terminal-job resume path

## Log and artifact handling

Async jobs may emit:

- append-only logs
- structured result summaries
- produced artifact refs

Rules:

- large logs stay out of ordinary prompt truth unless surfaced intentionally later
- operator/UI reads may inspect job logs directly
- prompt surfaces should consume compact summaries or deliberate refs, not raw log streams by default

## Non-goals

This contract does not define:

- the concrete local process runner
- the concrete remote queue or worker technology
- any adapter-specific job transport

Those implementation details must fit beneath this controller-owned contract.

## Related contracts

- [Controller contract and resumable execution](controller-contract-and-resumable-execution.md)
- [Human request and approval contract](../interfaces/human-request-and-approval-contract.md)
- [Operator UI API and event stream](../interfaces/operator-ui-api-and-event-stream.md)
- [Capability, security, and audit](../interfaces/capability-security-and-audit.md)
