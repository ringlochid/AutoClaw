# Current parent, retry, and operator control

Status: Current

Last verified: 2026-05-12

This page defines the shipped difference between callback parent/root control, worker retry, and operator runtime control.

Older approval-centric or operator-retry-centric docs do not describe the current shipped router.

## Current parenthood

Current implemented workflow schema supports recursive authored nodes.

A current authored node is structurally a parent when it has `children`.

Current bootstrap and manifest materialization then persist that tree as:

- `parent_node_key` metadata during normalization and bootstrap
- `parent_flow_node_id` in runtime flow-node rows
- a reconstructed parent/child manifest tree for prompt and readback surfaces

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

Current shipped retry surfaces are narrow:

- worker callback may close the current node with `retry`, but only after a terminal retry checkpoint exists for the current attempt
- parent/root `retry` is illegal
- the operator lane does not expose a public retry endpoint
- the operator steers runtime through `continue`, `pause`, `cancel`, `snapshot`, `trace`, and observability reads

Current retry consequences remain controller-owned:

- retry keeps the same assignment
- retry mints a fresh attempt for that assignment
- retry waits for prior dispatch inactivity proof and fencing before a replacement dispatch opens
- operator pause, continue, and cancel remain separate operator controls, not retry aliases
- current shipped contrast still externalizes some ordinary post-boundary progression through operator `continue`; the desired target keeps retry, child handoff, and parent wake internal to controller progression

## Current operator-control fact

The shipped router no longer exposes the older public approval routes, internal approval-creation routes, or a dedicated operator retry endpoint.

Current operator controls are:

- `GET /runtime/tasks`
- `GET /runtime/tasks/{task_id}`
- `POST /runtime/tasks/{task_id}/continue`
- `POST /runtime/tasks/{task_id}/pause`
- `POST /runtime/tasks/{task_id}/cancel`
- `GET /operator/tasks/{task_id}/snapshot`
- `GET /operator/tasks/{task_id}/trace`
- task-scoped observability reads under `/observability/*`

Current shipped contrast note:

- `continue` is not only pause-resume today; it also still resolves some accepted-boundary progression once inactivity proof is satisfied
- the desired target reserves `continue` for paused-flow resume only

Current callback parent/root control remains separate from operator control.

## Current public operator actions

Current public operator-facing surfaces include:

- runtime inspect and read views
- continue, pause, and cancel
- snapshot, trace, and observability reads

## Redesign contrast

Current implementation does not yet match the redesigned target parent/review/replan model.

That means current code does not yet expose the target contract where:

- every non-leaf parent has a first-class runtime `parent.gate`
- review is internal findings work rather than an approval-style gate
- each parent may adopt subtree-local replans
- root owns final closure readiness and dispatches the final sync leaf

Current behavior is still controller advancement plus worker retry, operator steering, and callback-bound parent/root decisions rather than the redesign's explicit parent-verification and local-parent-replan contract.

## Evidence

- inspected code in `apps/api/app/runtime/launch/persistence/flows.py`
- inspected code in `apps/api/app/db/models/runtime/flow/graph.py`
- inspected code in `apps/api/app/runtime/projection/manifest/tree.py`
- inspected code in `apps/api/app/runtime/control/boundary/service.py`
- inspected code in `apps/api/app/runtime/control/boundary/transitions.py`
- inspected code in `apps/api/app/runtime/control/flow/service.py`
- inspected code in `apps/api/app/api/routes/runtime.py`
- inspected code in `apps/api/app/api/routes/callback.py`
- inspected code in `apps/api/app/api/routes/operator.py`
- inspected tests in `apps/api/tests/integration/phase3/contracts/test_callback_cases.py`
- inspected tests in `apps/api/tests/integration/phase3/routes/test_surface_contract.py`
- inspected `../../redesign/workflows/parent-review-and-replan.md` as target-only contrast
- inspected `../../redesign/workflows/review-findings-contract.md` as target-only contrast
