# Current parent, retry, and operator control

Status: Current

Last verified: 2026-05-21

This page defines the shipped difference between callback parent/root control, worker retry, and operator runtime control.

Older approval-centric or operator-retry-centric docs do not describe the current shipped router.

## Current parenthood

Current implemented workflow schema supports recursive authored nodes.

A current authored node is structurally a parent when it has `children`.

Current bootstrap and manifest materialization then persist that tree as:

- `parent_node_key` metadata during normalization and bootstrap
- `parent_flow_node_id` in runtime flow-node rows
- a reconstructed parent/child manifest tree for prompt and readback surfaces

This is not the design's first-class runtime `parent.gate`.

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
- current shipped retry, child handoff, and parent wake progression now reopen internally after inactivity proof rather than through operator `continue`

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

- `continue` is now pause-resume only in shipped runtime control
- accepted-boundary retry progression, child handoff, and parent wake reopen internally after inactivity proof

Current callback parent/root control remains separate from operator control.

## Current public operator actions

Current public operator-facing surfaces include:

- runtime inspect and read views
- continue, pause, and cancel
- snapshot, trace, and observability reads

## Design contrast

Current implementation does not yet match the design target parent/review/replan model.

That means current code does not yet expose the target contract where:

- every non-leaf parent has a first-class runtime `parent.gate`
- review is internal findings work rather than an approval-style gate
- each parent may adopt subtree-local replans
- root owns final closure readiness and dispatches the final sync leaf

Current behavior is still controller advancement plus worker retry, operator steering, and callback-bound parent/root decisions rather than the design's explicit parent-verification and local-parent-replan contract.

## Evidence

- inspected code in `apps/api/src/autoclaw/runtime/launch/persistence/flows.py`
- inspected code in `apps/api/src/autoclaw/persistence/models/runtime/flow/graph.py`
- inspected code in `apps/api/src/autoclaw/runtime/projection/manifest/tree.py`
- inspected code in `apps/api/src/autoclaw/runtime/boundary/service.py`
- inspected code in `apps/api/src/autoclaw/runtime/boundary/transitions.py`
- inspected code in `apps/api/src/autoclaw/runtime/flow/service.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/runtime.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/callback.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/operator.py`
- inspected tests in `apps/api/tests/integration/runtime/contracts/test_session_authority_and_pause_cases.py`
- inspected tests in `apps/api/tests/integration/runtime/routes/test_surface_contract.py`
- inspected `../../../design/v1/workflows/parent-review-and-replan.md` as target-only contrast
- inspected `../../../design/v1/workflows/review-findings-contract.md` as target-only contrast
