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

## Start behavior

Starting an async job must:

1. validate that the current node policy allows async job creation
2. persist a new async-job record with controller-owned identity
3. persist the controller waiting cause as `waiting_for_async_job`
4. emit task events for job creation and task waiting
5. return control without keeping the model turn open

The start path must also persist:

- the task lineage identifiers needed for controller continuation
- the normalized command or job kind
- any declared timeout
- any declared output or artifact destination contract

## Risk judgment rule

Async-job start does not depend on AutoClaw parsing command text to detect destructive or privileged behavior.

Instead:

- node, role, policy, workflow, and prompt instructions teach the model when a job is risky enough to ask for human approval first
- the node may open a typed human request before starting the job when policy allows it
- the async-job start payload may carry requester-declared risk metadata and a human-request reference
- the controller validates declared state and capability, but it does not treat raw shell syntax as canonical risk truth
- concrete runners may add local safety checks, but those checks are implementation guardrails below the controller contract

## Terminal behavior

When the job reaches a terminal state, the controller must:

1. persist the terminal async-job state
2. persist any normalized result summary plus log and artifact refs
3. emit the matching terminal task event
4. leave the task lineage in database state that the controller loop can evaluate
5. open the next dispatch only when the task lineage is still current and the waiting cause still matches

The terminal-job path must not mint a new task lineage merely because the job completed later.

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

- large logs stay out of ordinary prompt truth unless surfaced intentionally later
- control UI/API reads may inspect job logs directly
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
- [Control API and task event stream](../interfaces/control-api-and-task-event-stream.md)
- [Capability, security, and audit](../interfaces/capability-security-and-audit.md)
