# Flow 07 — Controller-Driven Implementation Loop

## Problem this flow addresses

The runtime is now flow-first and functionally correct, but it is still possible for the flow to pause between safe control transitions until another explicit `continue` call happens.

That is safe, but it is not the right long-term operator experience for persistent implementation work.

## Current implemented baseline

Today, the code behaves roughly like this:

- `continue_flow()` is the main advancement engine
- manifest acknowledgement starts the current `node_attempt`
- `needs_approval` or explicit approval creation blocks the flow
- approval `approved` / `not_required` unblocks the flow, but the actual resume still happens on the next `continue`
- `green` marks the current attempt succeeded and the current node done, but another advancement step is still needed to release the next runnable node
- `retry` marks the current attempt failed and makes the node retryable, but another advancement step is still needed to project the next retry attempt

This baseline is safe and auditable, but it can leave the flow accidentally idle.

## Target next-stage behavior

Use a controller-side helper such as:

```text
advance_flow_until_boundary(flow_id, cause)
```

The controller should call it after safe control transitions and keep moving the flow until it reaches a real external boundary.

## Boundaries

Advancement stops only when the flow reaches a meaningful boundary:

1. a projected `context_manifest` is waiting for acknowledgement
2. a pending approval exists
3. a node attempt is actively running
4. the flow is paused
5. the flow is terminal (`failed`, `succeeded`, `cancelled`)
6. no runnable node exists and no policy-defined recovery step applies

## Safe triggers for advancement

The controller should invoke advancement after:

- explicit operator `continue`
- `context_manifest` acknowledgement
- approval resolution (`approved`, `not_required`)
- `green` checkpoint
- `retry` checkpoint
- operator retry action
- adopted revision / replan activation
- safe watchdog recovery

## Bounded implementation-loop contract

For a loop-owner node such as an implementation loop, the runtime should make the loop contract explicit.

### Loop cycle

```text
project context -> acknowledge context -> run node attempt -> emit checkpoint
-> controller evaluates next step -> advance until next boundary
```

### Valid next steps from a checkpoint

- `green`
  - current attempt succeeds
  - loop may exit, continue to review, or continue to another cycle depending on policy
- `retry`
  - current attempt fails
  - controller may create another attempt if retry budget allows
- `needs_approval`
  - controller stops at approval boundary
- `blocked`
  - controller stops at explicit wait boundary

### Loop budgets

A loop-owner should have explicit limits such as:

- max retry count
- max watchdog wake count
- max replan count before escalation
- required evidence count/quality before `sync`

The point is not to create a second state model. The point is to stop hiding loop behavior inside scattered code branches.

## Governance gate before `sync`

The `sync` path should become an explicit gate, not a prompt habit.

Typical requirements:

- required review/security/validation checkpoints are green
- required approvals are resolved
- required evidence is present on the flow/node/attempt path
- retry/replan budget has not already escalated the node back to planning

## Session continuity

Keep continuity anchored to existing runtime records:

- `flow` remains the execution container
- `flow_node` remains the execution owner within the graph
- `node_attempt` remains the execution slice
- `node_session` provides delegated-session continuity where appropriate

Do **not** add a separate global “active session state” model.

## Thin event surface

A small typed event layer is useful for console timelines and auditability:

- `approval_requested`
- `approval_resolved`
- `checkpoint_recorded`
- `watchdog_blocked`
- `revision_adopted`
- `sync_ready`

These are facts for observability. They should not replace checkpoint/approval/runtime rules as the control truth.

## Non-goals

- no global mode-state system
- no plugin/hook framework as the runtime core
- no transcript-driven control decisions
- no repeated “continue” prompt spam to delegated workers
