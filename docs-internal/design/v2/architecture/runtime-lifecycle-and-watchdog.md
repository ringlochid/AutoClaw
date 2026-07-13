# Runtime lifecycle and watchdog

Status: Target

This page owns the V2 local runtime lifecycle, dispatch control states, provider-control retry policy, semantic progress clock, and watchdog recovery.

It does not own provider-specific start and stop mechanics, task-root file layout, node MCP payload schemas, human-request resolution, command execution, or public control routes. Those surfaces consume this lifecycle.

## Core rule

AutoClaw V2 is one local, same-host runtime. Controller records own lifecycle truth, and meaningful node MCP-backed commits own agent progress. Provider acceptance, output, events, native tool streams, disconnects, and terminal frames never advance progress or complete a dispatch.

One API lifespan owns one `LocalRuntimeSupervisor`. No request handler, watchdog helper, adapter module, or background monitor may create a second provider-control owner.

## Runtime boundary

The local process shape is:

```text
AutoClaw API lifespan
  -> LocalRuntimeSupervisor
      -> AgentControlManager
      -> provider-control retry scheduler
      -> watchdog
      -> managed Codex and Claude processes
  -> controller database
  -> node and operator MCP servers
  -> local task roots and workspaces

externally managed OpenClaw Gateway
  <- controlled through the OpenClaw adapter
```

The supervisor owns runtime coordination only. The database still owns canonical task, assignment, attempt, dispatch, wait, and boundary facts.

This phase does not support:

- remote workspaces or workspace synchronization
- message-queue delivery or distributed workers
- object-store task roots
- separately deployed provider-control services
- multiple active AutoClaw runtime processes over one controller database
- automatic OpenClaw installation or supervision

Different task lineages may run concurrently. One task lineage still has at most one current open dispatch.

## Runtime owners

### `LocalRuntimeSupervisor`

The API lifespan creates and closes exactly one supervisor. It owns:

- the `AgentControlManager`
- delayed retry scheduling
- watchdog scanning and recovery dispatch
- managed local agent-process cleanup
- shutdown ordering

It reconstructs pending local work from controller state after process restart. Its in-memory queue is scheduling machinery, not runtime truth.

### `AgentControlManager`

Every provider `start` and `stop` call passes through this one owner.

It owns:

- the central asynchronous command queue
- adapter instances and adapter-private live handles
- provider operation timeouts
- exponential retry
- duplicate stop coalescing
- cancellation of delayed starts when stop becomes desired
- bounded controller readback for current provider-control work

It does not interpret provider output as progress, completion, or workflow state. An adapter may privately drain SDK output or retain a connection when required to keep its process healthy.

## Dispatch states

`Dispatch.status` has exactly these values:

- `starting`
- `open`
- `closing`
- `closed`

`Dispatch.closed_reason`, when the dispatch is closed, has exactly these values:

- `boundary`
- `human_request_wait`
- `command_run_wait`
- `cancelled`
- `superseded`
- `control_failed`

Meanings:

| Status     | Meaning                                                                 |
| ---------- | ----------------------------------------------------------------------- |
| `starting` | controller truth and node authority exist; provider start is pending    |
| `open`     | provider start handed off successfully; semantic MCP work may commit    |
| `closing`  | controller has committed a provider-stop intent                         |
| `closed`   | this dispatch can no longer accept node MCP writes                       |

Rules:

- status changes come from controller commits, never provider event normalization
- `open` means provider start handed off successfully, not that the provider emitted a start event
- `closed_reason = boundary` requires an accepted controller boundary
- legal external waits close the dispatch rather than suspending it
- the old dispatch is closed before a watchdog replacement dispatch is committed
- a closed dispatch never becomes open again

## Dispatch start sequence

The controller opens a dispatch in this order:

1. Resolve provider preference and fallback to one `resolved_provider`.
2. Build the complete `PromptTransportRequest` from current controller truth.
3. Mint the existing task/node-recognition `NodeSession.session_key`.
4. Atomically commit the `Dispatch` in `starting`, its prompt request, and its open `NodeSession` authority.
5. Enqueue one `start` operation through `AgentControlManager`.
6. Retry transient control failures under the provider-operation budget.
7. After successful handoff, persist the effective `provider_session_hint`, set `adapter_started_at`, and move the dispatch to `open`.

The session key is created before launch so a fast agent can call node MCP immediately. It remains the existing AutoClaw task and node recognition value; V2 does not add a new provider-specific MCP credential or execution generation.

A current `starting` dispatch may accept node MCP calls through that authority during the launch-handoff race. A later start-success commit may move only a still-current `starting` dispatch to `open`; it must never reopen a dispatch that an early legal MCP wait or boundary already closed.

Provider fallback must finish before step 4. One dispatch never changes provider inside its six-call start budget. If fallback chooses another provider, that choice belongs to a new dispatch prepared from current controller truth.

Start retry time does not consume the agent work window. The 900-second clock begins only when `adapter_started_at` commits.

## Provider-control retry policy

The defaults are:

```toml
provider_control_max_attempts = 6
provider_control_initial_backoff_seconds = 1
provider_control_operation_timeout_seconds = 15
```

Six means six total calls:

| Call | Wait before the next call |
| ---- | ------------------------- |
| 1    | 1 second                  |
| 2    | 2 seconds                 |
| 3    | 4 seconds                 |
| 4    | 8 seconds                 |
| 5    | 16 seconds                |
| 6    | none                      |

The total configured backoff is 31 seconds, excluding each bounded operation timeout.

Rules:

- connection establishment and the requested start or stop share one attempt budget; retries must not nest
- delayed retries are scheduled back into the central queue; a queue worker never sleeps through the delay
- transient connection, timeout, and availability failures retry
- authentication, configuration, and invalid-request failures fail without spending the remaining transient retry budget
- repeated stop requests for one dispatch share one in-flight operation
- once a dispatch is stopped, later stop requests succeed as no-ops
- a queued stop cancels any delayed start for the same dispatch
- provider I/O occurs after desired controller state commits, never inside the database transaction

Controller readback exposes the operation, current call number, maximum calls, next retry time, and sanitized last error. The event/API owner decides the exact carrier, but the retry scheduler does not rely on an event stream to recover its state.

If the initial dispatch start exhausts its budget or fails with a non-retryable control error, the controller closes that dispatch with `closed_reason = control_failed` and pauses the task with `pause_reason = runtime_recovery_exhausted`. This initial failure does not increment the attempt's watchdog restart count. After the provider is repaired, ordinary operator continue prepares a new same-attempt dispatch.

## Semantic progress

`Dispatch.last_progress_at` is the one watchdog progress clock.

It records controller commit time, never an agent-supplied or provider-supplied timestamp.

It advances in the same transaction as a meaningful, accepted, current node MCP-backed semantic commit, including:

- a changed `AttemptPlan`
- an allowed progress or terminal checkpoint
- a successful assignment, structural, release, boundary-preparation, or external-wait mutation
- an accepted `return_boundary` commit
- another explicitly documented controller mutation that changes the current runtime lineage

It does not advance for:

- `get_current_context`, task-file listing, or task-file reading
- a failed, rejected, stale, or unauthorized tool call
- an identical `update_plan` request
- provider acceptance, output, tool streams, events, or terminal state
- MCP transport connectivity by itself
- task-event emission without an owning semantic state change

The minimal `NodeMcpInvocation` record shows whether a call started, completed, failed, and advanced progress. It does not create another activity clock.

## Watchdog eligibility and deadline

The default is:

```toml
watchdog_stale_after_seconds = 900
watchdog_restart_limit = 2
```

One dispatch is watchdog-eligible only when all of these are true:

- it is the current dispatch for the task lineage
- its status is `open`
- it has `adapter_started_at`
- the task is not terminal or operator-paused
- no current human-request or command-run source wait owns the task lineage
- recovery is not already active for the dispatch

The stale anchor is:

```text
last_progress_at ?? adapter_started_at
```

There is no separate provider-silence clock, bootstrap clock, read-activity clock, or parent/root deadline. Parent and root normally finish quickly; they follow the same dispatch rule without new prompt obligations.

## Normal completion

The happy path is:

```text
worker commits current plan and work
  -> worker records terminal checkpoint
  -> worker calls return_boundary
  -> controller validates and commits boundary
  -> controller closes NodeSession authority
  -> controller closes dispatch with reason boundary
  -> provider response ends naturally
```

The controller does not call adapter `stop` after an ordinary boundary. A provider terminal frame is neither required nor consumed.

## External waits

Human requests and long command runs are task-lineage-owned waits, not suspended provider executions.

The opening sequence is:

```text
worker records the required progress checkpoint
  -> worker opens the external-wait source through node MCP
  -> controller commits the source row and waiting cause
  -> controller closes NodeSession authority
  -> controller closes the dispatch with the matching wait reason
  -> provider response ends naturally
```

Rules:

- no terminal checkpoint is recorded for opening the wait
- no workflow boundary is returned
- no adapter stop is requested
- the task, assignment, attempt, and `AttemptPlan` stay current
- the ordinary dispatch watchdog has nothing open to inspect during the wait
- the human-request or command-run owner monitors its own record
- after a terminal resolution, the controller rereads currentness and opens a new dispatch on the same attempt when still legal

The exact request and command state machines belong to the [human-request owner](../interfaces/human-request-and-approval-contract.md) and the [command-run owner](command-run-and-external-wait.md).

## Watchdog recovery

Recovery is the only automatic stale-execution replacement lane.

For an eligible stale dispatch, the controller performs this sequence:

1. Acquire the task execution-slot recovery lock and reread currentness.
2. Close the stale dispatch's `NodeSession` authority so later node MCP writes are rejected.
3. Commit the stale dispatch to `closing` and enqueue provider `stop`.
4. Retry stop under the six-call provider-control policy until the adapter confirms that its active execution can no longer continue that turn.
5. Only after successful stop, close the stale dispatch with `closed_reason = superseded`.
6. Increment the current attempt's watchdog restart count.
7. Commit a replacement dispatch on the same assignment, attempt, and `AttemptPlan` using current controller context and the latest checkpoint.
8. Enqueue start under the six-call provider-control policy.
9. On successful handoff, persist the effective session hint and new `adapter_started_at`; semantic progress starts a fresh 900-second window.

The replacement may pass the prior opaque `provider_session_hint` only when the resolved provider is unchanged. If continuation fails, the adapter may start fresh and return a replacement hint. A provider change omits the incompatible hint. Correctness comes from the regenerated prompt, current plan, and checkpoint, not provider memory.

Normal successful completion and legal external waits never use this recovery stop lane.

If stop cannot establish its adapter-owned execution boundary, no replacement dispatch is created. Stop exhaustion follows the `control_failed` and `runtime_recovery_exhausted` path below.

## Recovery exhaustion

One automatic watchdog restart cycle contains one stop operation and one start operation, each with its own six-call budget. The default limit is two cycles per current attempt.

If stop or start exhausts its provider-control budget, or if the attempt exhausts its restart count:

1. close any current node-session authority
2. close the affected dispatch with `closed_reason = control_failed`
3. pause the task with `pause_reason = runtime_recovery_exhausted`
4. emit bounded controller readback describing the failed operation and call count

After repairing provider configuration or availability, the operator uses the ordinary continue control. Continue recomputes legality and opens a new same-attempt dispatch; it is not a special provider reconnect transition.

## Explicit cancellation and shutdown

The central stop path is called only for:

- watchdog recovery
- explicit operator cancellation of a dispatch, including pause or task cancel
- API lifespan shutdown cleanup

Explicit cancellation commits controller intent and closes node authority before provider I/O. It closes the dispatch as `cancelled` after the stop path. Shutdown uses the same manager and coalescing logic; it does not invent a second adapter cleanup path.

## Required invariants

- one task lineage has at most one current `starting`, `open`, or `closing` dispatch
- every provider-control call goes through `AgentControlManager`
- every current `starting` or `open` dispatch has one open `NodeSession`
- every `closing` or `closed` dispatch has closed node-session authority
- `adapter_started_at` exists before watchdog eligibility
- start retry delay never counts as semantic work time
- only meaningful accepted node MCP-backed commits advance `last_progress_at`
- legal external waits own no open provider dispatch
- watchdog replacement preserves assignment, attempt, and plan
- semantic `retry` alone creates a new attempt
- provider identity does not change inside one dispatch control budget
- provider terminal state never closes a controller boundary

## Related contracts

- [Controller contract and resumable execution](controller-contract-and-resumable-execution.md)
- [Runtime records and control state](runtime-records-and-control-state.md)
- [Attempt plan and checkpoint contract](attempt-plan-and-checkpoint-contract.md)
- [Adapter contract](adapter-contract.md)
- [Node and operator MCP surface contract](../interfaces/node-and-operator-mcp-surface-contract.md)
- [Human request and approval contract](../interfaces/human-request-and-approval-contract.md)
- [Command run and external wait](command-run-and-external-wait.md)
