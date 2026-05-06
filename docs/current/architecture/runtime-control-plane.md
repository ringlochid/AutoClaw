# Current runtime control plane

Status: Current

Last verified: 2026-05-05

Current runtime truth is controller-owned and relational. Prompt text,
observability files, and other generated task-root artifacts are derived
projections, not the authoritative source of control state.

## Keywords

- current control plane
- dispatch turn
- assignment and attempt
- callback binding
- release precondition
- controller truth

## Current runtime truth

The current authoritative runtime spine includes these controller-owned record
families:

- task and compose rows
- task resource bindings and manifest root rows
- workspace root lease rows
- compiled-plan rows
- flow, flow revision, flow node, and flow edge rows
- assignment, attempt, checkpoint, consumed-ref, produced-ref, and criteria-ref rows
- dispatch turn, callback binding, delivery-state, continuity-state, and
  watchdog-state rows
- artifact publication and current-pointer rows
- provider-event rows

Generated files under `_runtime/`, `outputs/`, `context/criteria/`, or
`context/wiki/` are materialized from those records.

## Current control owners

Current runtime control is split across these grouped services:

- launch/bootstrap: `apps/api/app/runtime/launch/**`
- operator controls: `apps/api/app/runtime/control/flows.py`
- checkpoint and boundary writes: `apps/api/app/runtime/control/boundary.py`
- parent/root tools and release preconditions:
  `apps/api/app/runtime/control/parent_tools.py` and `release.py`
- callback/session support: `apps/api/app/runtime/control/support.py`
- prompt and manifest materialization: `apps/api/app/runtime/projection/**`

There is no shared boundary-advance helper loop in the shipped tree.

## Current dispatch and attempt model

Current runtime works around one active flow plus one current open dispatch:

- `FlowModel.current_open_dispatch_id` points at the live dispatch when one is open
- `FlowModel.current_node_key` points at the node currently bound for control
- each `AssignmentModel` points at one `current_attempt_id`
- retries create a new `AttemptModel` for the same assignment
- callback access is bound to a `DispatchCallbackBindingModel` session key

Current dispatch replacement is explicit:

- a replacement dispatch is illegal while the previous dispatch is still in
  `launching`, `live`, `abort_requested`, or `ambiguous`
- a replacement dispatch requires the previous dispatch to be fenced first

Current dispatch control-state facts include:

- initial open state: `launching`
- confirmed live state: `live`
- accepted-terminal waiting state: `boundary_accepted_waiting_terminal`
- cancel handshake state: `abort_requested`
- timeout/escalation state: `ambiguous`
- fenced/closed state: `fenced`
- the shipped boundary-accept path does not fence the dispatch immediately; it
  revokes callback access and leaves the accepted dispatch controller-truth-visible
  until inactivity is proven or the control deadline expires
- the shipped cancel path does not fence the dispatch immediately; cancel requests `abort_requested`, sets a control deadline, revokes callback access, keeps the current dispatch controller-truth-visible, and keeps the workspace lease held until inactivity is proven or the control deadline expires

## Current operator and callback controls

Current operator controls include:

- list runtime tasks
- inspect one runtime task
- continue a paused or resumable task runtime
- pause the current dispatch
- cancel the current task flow

Current callback controls include:

- `record_checkpoint`
- `yield`
- `green`
- `retry`
- `blocked`
- parent/root tools such as `assign_child`, `add_child`, `update_child`,
  `remove_child`, `release_green`, and `release_blocked`

Current callback legality facts include:

- `yield` requires exactly one staged child assignment
- parent/root `retry` is illegal
- terminal boundaries require a terminal checkpoint whose outcome matches the
  requested boundary
- `green` for parent/root requires `release_green` first
- root `blocked` requires `release_blocked` first

## Current status behavior

Current flow statuses are:

- `pending`
- `running`
- `blocked`
- `paused`
- `succeeded`
- `failed`
- `cancelled`

Current high-level status transitions are:

- launch opens the root bootstrap dispatch and marks the flow `running`
- pause fences the current dispatch, revokes callback access, and marks the
  flow `paused`
- continue resumes a paused flow or reopens a resumable dispatch for the
  current attempt when the expected active flow revision still matches
- continue also performs the foreground inactivity-proof step for accepted
  terminal dispatches; it fences them only after proof and promotes them to
  `ambiguous` if the control deadline has already expired
- cancel marks the current dispatch `abort_requested`, closes the current
  attempt when needed, revokes callback access, keeps the current dispatch
  controller-truth-visible, and marks the flow `cancelled`
- workspace lease release for a cancelled or terminal flow now waits until the
  prior foreground dispatch is fenced by inactivity proof or timed out as
  `ambiguous`
- worker `green` redispatches the parent when one exists, otherwise the flow
  succeeds
- worker `retry` opens a new attempt for the same assignment and reopens a new
  dispatch
- parent/root `yield` opens the staged child assignment dispatch
- root terminal `blocked` or top-level terminal `green` can close the whole
  flow

## Current generated-file rule

Current generated files are support surfaces only:

- `_runtime/workflow-manifest.{json,md}`
- `_runtime/attempts/<attempt_id>/*`
- `_runtime/dispatch/<dispatch_id>/*`
- `outputs/artifacts/**`

They are useful for runtime sharing and observability, but they do not outrank
the controller-owned DB rows above.

## Minimal example

```text
launch_task_runtime
  -> seed task + compiled plan + flow rows
  -> create root assignment and attempt
  -> open bootstrap dispatch
  -> materialize workflow-manifest and prompt artifact

worker retry
  -> record terminal retry checkpoint
  -> accept boundary retry
  -> create new attempt for same assignment
  -> open replacement dispatch after the prior dispatch is fenced

parent yield
  -> stage exactly one child assignment
  -> accept boundary yield
  -> open child dispatch
```

## Evidence

- inspected code in `apps/api/app/runtime/launch/service.py`
- inspected code in `apps/api/app/runtime/control/flows.py`
- inspected code in `apps/api/app/runtime/control/boundary.py`
- inspected code in `apps/api/app/runtime/control/parent_tools.py`
- inspected code in `apps/api/app/runtime/control/release.py`
- inspected code in `apps/api/app/runtime/control/support.py`
- inspected code in `apps/api/app/runtime/projection/materialize.py`
- inspected tests in `apps/api/tests/integration/test_phase3_runtime_routes.py`
- inspected tests in `apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
- inspected tests in `apps/api/tests/integration/test_runtime_schema_contract.py`
