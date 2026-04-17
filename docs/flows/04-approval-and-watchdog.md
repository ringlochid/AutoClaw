# Flow 04 — Approval and Watchdog

## Gate principle

All high-impact control changes happen through:

1. a checkpoint event,
2. an approval resolution,
3. or an explicit operator action.

No state transition should depend on transcript interpretation.

---

## Runtime status model

### Flow status

- `pending`
- `running`
- `blocked`
- `paused`
- `failed`
- `succeeded`
- `cancelled`

### Flow node state

- `ready`
- `running`
- `waiting`
- `paused`
- `done`
- `failed`

### Node attempt status

- `pending`
- `running`
- `blocked`
- `failed`
- `succeeded`
- `cancelled`
- `aborted`

Status meaning:

- `failed` = executed and ended unsuccessfully, including retryable failure
- `aborted` = invalidated or interrupted by control flow (operator cancel, superseded revision, forced stop)

### Wait reasons

Use checkpoint or node payload to distinguish why a node is waiting:

- `approval`
- `dependency`
- `watchdog`
- `operator`
- `context`

---

## Bootstrap/context gate

Before delegated execution starts:

1. controller projects a policy-filtered `context_manifest` for the `node_attempt`
2. delegated session reads the required context slice first
3. controller waits for manifest acknowledgement

If required context is missing, stale, or unreadable:

- keep the attempt blocked or return it to waiting
- set `wait_reason = context`
- surface unresolved context explicitly for operator or planner repair

Manifest acknowledgement is the pre-execution gate.
Do not treat a natural-language prompt request to "read these notes first" as sufficient enforcement by itself.

---

## Explicit transitions

### From checkpoint

- `green`:
  - current `node_attempt` -> `succeeded`
  - `flow_node` -> `done` or next node becomes runnable
- `retry`:
  - current `node_attempt` -> `failed`
  - controller creates a new `node_attempt` for the same node
- `blocked`:
  - current `node_attempt` -> `blocked`
  - `flow_node` -> `waiting`
  - `flow` -> `blocked`
- `needs_approval`:
  - current `node_attempt` -> `blocked`
  - `flow_node` -> `waiting`
  - create approval row scoped to flow/node/attempt
  - `flow` -> `blocked`

### From approval

Current implemented baseline:

- `approved`:
  - flow leaves blocked state
  - on the next controller `continue`, the same blocked attempt is resumed
- `rejected|expired`:
  - current node/attempt path fails
  - flow fails unless explicit bypass policy exists
- `not_required`:
  - unblock like `approved`

Next-stage target:

- safe approval resolution should trigger controller advancement automatically until the next real boundary instead of waiting for a separate manual continue call
- post-approval behavior that varies by workflow/node should be policy-driven rather than scattered in hardcoded branches

### From context acknowledgement

- acknowledged manifest:
  - delegated node may enter the execution phase
  - controller may release the real work instruction/tool phase
- unresolved context:
  - node remains blocked with `wait_reason = context`
  - scheduler should not treat the node as execution-ready

### From operator

- pause flow:
  - running/waiting nodes -> `paused`
  - flow -> `paused`
- cancel flow:
  - open attempts -> `cancelled`
  - flow -> `cancelled`
- continue flow:
  - scheduler reevaluates runnable nodes and may create a new `node_attempt`

---

## Watchdog

Current implemented baseline:

- scan `running` attempts for stale checkpoint activity
- current staleness detection is checkpoint/start-time based, not a richer session lease or progress-heartbeat model yet
- if an attempt stays stale past the watchdog threshold, mark the attempt `blocked`
- set the node to `waiting`
- idle the delegated session
- record a blocked checkpoint with `wait_reason = watchdog`
- require explicit operator/runtime recovery rather than silently pretending the node is still healthy

Target watchdog behavior:

- detect stalled attempts (missing checkpoints / timeouts)
- emit operator-visible wait reason
- preserve revision and provenance context during recovery
- attempt **controller-owned recovery** in bounded steps rather than relying on chatty natural-language nudges

Preferred recovery order:

1. **safe wake**
   - only if the same delegated session is still valid/bound
   - only if no approval/context boundary is blocking
   - only within a bounded wake budget
   - **current implementation:** watchdog recovery issues a same-session wake through the normal OpenClaw bridge path
   - if wake dispatch succeeds, the node returns to `running`
   - if wake dispatch times out, the runtime currently treats that as **ambiguous delivery** and keeps the same attempt/session resumable so late callbacks can still land; operators should inspect before retrying
   - if wake dispatch fails with a definite bridge/request error, the node is returned to safe `blocked` / `waiting` state and the delegated session is idled again
2. **safe retry**
   - if wake is exhausted or clearly invalid
   - create a new `node_attempt`, preserving attempt history
   - **current implementation note:** this remains an operator-triggered path; watchdog does not auto-create the fresh attempt yet
3. **operator escalation**
   - if state is ambiguous, recovery budget is exceeded, or the runtime cannot prove the wake/retry path is safe
   - **current implementation:** recovery returns explicit reason/detail/next-step guidance for timeout, dispatch failure, missing session binding, or multiple eligible blocked nodes

Current watchdog operator rules:

- on wake timeout: inspect the delegated session and recent checkpoints before retrying; do **not** blind-retry another wake
- on wake dispatch failure: inspect the failure detail and delegated session state before deciding on operator retry
- wake budget is tracked per `node_attempt`, not globally per node, so a fresh retry attempt starts with a fresh wake budget

Guardrail:

- do **not** solve liveness by blindly sending repeated natural-language “continue” prompts to delegated workers
- watchdog recovery should remain a controller-owned typed action, not transcript improvisation
