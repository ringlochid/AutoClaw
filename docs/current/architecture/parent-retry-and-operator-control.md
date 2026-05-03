# Current parent, retry, and operator control

Status: Current

Last verified: 2026-04-26

This page defines the current parenthood model, current approval lifecycle, current operator retry rule, and the difference between current operator behavior and the redesign target.

## Current parenthood

Current implemented workflow schema supports recursive authored nodes.

A current authored node is structurally a parent when it has `children`.

Current compiler/runtime materialization then flattens that tree into:

- `parent_node_key` metadata during nesting/flattening
- `parent_flow_node_id` in runtime records
- `node_path` in runtime records

This is not the redesign's first-class runtime `parent.gate`.

Current parenthood is structural metadata plus controller advancement, not a separate current operator role.

## Current operator contrast

Operator is an external trusted principal that steers runtime state through operator surfaces.

Operator is not:

- worker
- controller
- provider
- authored structural parent

See `../interfaces/api-trust-lanes.md` for the exact current operator role and lane split.

## Current retry behavior

Current checkpoint statuses are:

- `green`
- `retry`
- `blocked`
- `needs_approval`

Current runtime transitions applied from checkpoint writes are:

- `green` succeeds the node attempt, supersedes projected manifests, and ends the session
- `retry` fails the node attempt, makes the node ready again, and ends the session
- `blocked` blocks the attempt and idles the session
- `needs_approval` blocks the attempt, idles the session, and creates an approval record

## `LegacyApprovalContract`

Current approval is exact implementation truth, but it is legacy behavior.

It is:

- not redesign review
- not pause
- not generic operator hold

It is a current operator-resolved block path slated for later removal.

### Approval creation paths

Current approval may be created in two ways:

- worker checkpoint with `CheckpointStatus.NEEDS_APPROVAL`
- direct internal approval creation through `/internal/approvals`

### Approval pending effects

When approval becomes pending for the current attempt:

- the node attempt is blocked
- the node becomes waiting
- the delegated session is idled
- the flow becomes blocked after status refresh
- the flow exposes `pending-approvals` as current boundary reason

### Approval resolution outcomes

| Resolution     | Exact current effect                                                                                                  |
| -------------- | --------------------------------------------------------------------------------------------------------------------- |
| `approved`     | keep the attempt blocked/current as-is, refresh flow state, then re-enter `advance_flow_until_boundary(...)`          |
| `not_required` | same as approved for current control flow purposes: refresh and re-enter advancement                                  |
| `rejected`     | expire pending approvals, supersede projected manifests, fail the flow, fail open attempts, then re-enter advancement |
| `expired`      | terminal approval status only; not a public resolve action                                                            |

Important current fact:

- public approval resolve always re-enters `advance_flow_until_boundary(...)`
- approval does not merely flip a flag and wait for a later unrelated operator action

## `OperatorRetryRule`

Operator retry is exact current behavior, not a generic "retry any blocked node" action.

Current retry is legal only when:

| Current attempt state | Required wait reason    | Retryable? |
| --------------------- | ----------------------- | ---------- |
| `FAILED`              | n/a                     | yes        |
| `BLOCKED`             | `WaitReason.OPERATOR`   | yes        |
| `BLOCKED`             | `WaitReason.WATCHDOG`   | yes        |
| `BLOCKED`             | `WaitReason.APPROVAL`   | no         |
| `BLOCKED`             | `WaitReason.DEPENDENCY` | no         |

### Operator retry side effects

When operator retry is allowed and performed, current runtime:

- expires pending approvals on the current attempt
- supersedes projected manifests on the current attempt
- aborts the current attempt
- ends the current delegated session
- mints a fresh blocked attempt
- bootstraps fresh context for that new attempt

## Current public operator actions

Current public operator-facing surfaces include:

- flow inspect/operator views
- continue, pause, cancel
- node retry when current retry rule allows it
- approvals read and resolve
- selected public registry and task surfaces

## Redesign contrast

Current implementation does not yet match the redesigned target parent/review/replan model.

That means current code does not yet expose the target contract where:

- every non-leaf parent has a first-class runtime `parent.gate`
- review is internal findings work rather than an approval-style gate
- each parent may adopt subtree-local replans
- root owns final closure readiness and dispatches the final sync leaf

Current behavior is still controller advancement plus node-level retry, approval, watchdog, and operator handling rather than the redesign's explicit parent-verification and local-parent-replan contract.

## Evidence

- inspected code in `autoclaw-main/apps/api/app/runtime/checkpoints.py`
- inspected code in `autoclaw-main/apps/api/app/runtime/control.py`
- inspected code in `autoclaw-main/apps/api/app/runtime/approvals.py`
- inspected code in `autoclaw-main/apps/api/app/runtime/runner.py`
- inspected code in `autoclaw-main/apps/api/app/runtime/watchdog.py`
- inspected code in `autoclaw-main/apps/api/app/api/routes/approvals.py`
- inspected `../../redesign/workflows/parent-review-and-replan.md` as target-only contrast
- inspected `../../redesign/workflows/review-findings-contract.md` as target-only contrast
