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

- `approved`:
  - waiting node becomes `ready`
  - scheduler may create a new `node_attempt` or resume policy-defined work
- `rejected|expired`:
  - current node -> `failed`
  - flow -> `failed` unless explicit bypass policy exists
- `not_required`:
  - unblock without manual intervention

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

Target watchdog behavior:

- detect stalled attempts (missing checkpoints / timeouts)
- emit operator-visible wait reason
- support safe wake/retry without losing attempt history
- preserve revision and provenance context during recovery
