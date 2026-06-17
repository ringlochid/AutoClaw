# Controller contract and resumable execution

Status: Target

This page defines the Vnext controller model for resumable execution.

## Core rule

Controller-owned persisted state is the only runtime truth owner.

Provider streams, adapter callbacks, prompt artifacts, support files, UI caches, and local deployment bindings may explain or project that truth, but none of them replace it.

## Resumable execution model

Vnext keeps one controller-owned task lineage and expands the set of legal paused or waiting boundaries.

The controller must persist enough truth to continue the same task lineage after:

- typed human request resolution
- typed human structured input
- async job completion
- async job failure
- async job timeout
- operator pause and later operator resume
- adapter disconnect or reconnect where the controller can safely continue

The controller must not model these continuations as generic chat continuation.

## Continuation rule

Human requests, async jobs, and other external waits must continue the same controller lineage when they are still current and legal.

For a human request, continuation means:

- same `task_id`
- same current flow lineage
- same assignment and attempt when still current
- same pending human request record until it reaches terminal state
- a terminal human-request state transition after answer, timeout, cancellation, or supersession
- controller legality recomputed before opening the next dispatch

Provider or adapter session reuse is useful continuity context, but it is not the continuation authority.

Rules:

- reuse provider or adapter session scope when it is lawful and available
- do not depend on provider chat memory for correctness
- if provider session continuity is stale, unavailable, or unsafe, redispatch from controller truth with a fresh provider/session scope
- a continued human request must never become generic chat continuation
- a timed-out human request still terminates the wait and may redispatch the same controller lineage using the request's timeout/default behavior

## Canonical waiting causes

The controller may place a task lineage into an externally waiting state only for these causes:

- `paused_by_operator`
- `waiting_for_human_request`
- `waiting_for_async_job`
- `waiting_for_internal_fencing`
- `waiting_for_adapter_reconnect`

Rules:

- only one canonical waiting cause may be active for the current task lineage at a time
- historical evidence may show prior waits, but current controller truth names one active cause or none
- ordinary post-boundary workflow progression is not a waiting cause and must remain controller-owned internal work
- `continue_task` or any future equivalent remains pause-resume only and must not become the generic continuation path for the other waiting causes

## Boundary state transitions

Continuing from an external wait is a controller decision over committed database state.

Canonical terminal or clearing transitions are:

- `operator_resume`
- `human_request_terminal`
- `async_job_terminal`
- `adapter_reconnected`
- `internal_fencing_cleared`

Rules:

- the source row owns the transition, for example a pending human request reaching terminal state or an async job reaching terminal state
- the source row and waiting-cause state are the database truth the controller loop evaluates
- the controller recomputes current legality from persisted truth before opening any next dispatch
- the controller may continue only when the referenced task lineage is still current and the waiting cause still matches
- stale, superseded, or already-terminal source transitions must not open work again
- no separate transition-record truth family is required
- adapter or provider launch calls may still use transport idempotency keys below the controller boundary transition

## New persisted controller records

Vnext adds these controller-owned persisted families:

- `pending_human_requests`
- `async_jobs`
- `task_events`

`pending_human_requests` and `async_jobs` own their source truth.

`task_events` are the append-only controller event log for UI replay, SSE cursors, "what changed" history, and audit chronology. They are authoritative for event chronology, but they do not replace task, flow, assignment, pending-human-request, or async-job source rows for currentness or legality.

These records must not be reconstructed from prompt prose, support files, or adapter-native histories.

## Truth precedence

When surfaces disagree, use this order:

1. controller-owned task, flow, assignment, attempt, and waiting-cause truth
2. controller-owned pending-human-request and async-job source truth
3. controller-owned task events for event chronology plus controller-generated read models and prompt projections over source truth
4. support-state or observability files
5. adapter-native or provider-native transport detail

## Boundaries that do not change

Vnext does not reopen these V1 invariants:

- public workflow egress still centers on controller-owned boundaries rather than provider success
- provider transport success still does not equal assignment success
- support files and observability histories remain downstream evidence only
- local deployment bindings do not become controller truth after launch

## Related contracts

- [Capability, security, and audit](../interfaces/capability-security-and-audit.md)
- [Human request and approval contract](../interfaces/human-request-and-approval-contract.md)
- [Async job and long-running boundary](async-job-and-long-running-boundary.md)
- [Control API and task event stream](../interfaces/control-api-and-task-event-stream.md)
- [Worktree and agent split contract](worktree-and-agent-split-contract.md)
- [V1 runtime boundary and controller loop](../../v1/architecture/runtime-boundary-and-controller-loop-contract.md)
