# Current runtime control plane

Status: Current

Last verified: 2026-05-12

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
- durable `runtime_effects` rows that queue post-commit file/projection work

Generated files under `_runtime/`, `outputs/`, `context/criteria/`, or
`context/wiki/` are materialized from those records.

## Current control owners

Current runtime control is split across these grouped services:

- launch/bootstrap: `apps/api/app/runtime/launch/**`
- operator controls: `apps/api/app/runtime/control/flows.py`
- checkpoint/boundary writes and release legality:
  `apps/api/app/runtime/control/{boundary.py,checkpoint_recording.py,release.py,release_preconditions.py}`
- parent/root tools and child-assignment staging:
  `apps/api/app/runtime/control/{assign_child.py,parent_tools.py,assignment_persistence.py,assignment_staging.py}`
- callback/session validation: `apps/api/app/runtime/control/callbacks.py`
- prompt and manifest materialization: `apps/api/app/runtime/projection/**`
- post-commit effect staging and read-surface guards:
  `apps/api/app/runtime/{post_commit.py}` and
  `apps/api/app/runtime/control/{surfaces.py,observability.py}`

There is no shared boundary-advance helper loop in the shipped tree.

## Current dispatch and attempt model

Current runtime works around one active flow plus one current open dispatch:

- `FlowModel.current_open_dispatch_id` points at the live dispatch when one is open
- `FlowModel.current_node_key` points at the node currently bound for control
- each `AssignmentModel` points at one `current_attempt_id`
- retries create a new `AttemptModel` for the same assignment
- callback access is bound to a `DispatchCallbackBindingModel` session key plus
  the current live dispatch, assignment, and attempt lineage for that task

Current dispatch replacement is explicit:

- a replacement dispatch is illegal while the previous dispatch is still in
  `launching`, `live`, `abort_requested`, or `ambiguous`
- a replacement dispatch requires the previous dispatch to be fenced first

Current dispatch control-state facts include:

- initial open state: `launching`
- confirmed live state: `live`
- cancel handshake state: `abort_requested`
- timeout/escalation state: `ambiguous`
- fenced/closed state: `fenced`
- the shipped cancel path does not fence the dispatch immediately; cancel requests `abort_requested`, sets a control deadline, revokes callback access, keeps the current dispatch controller-truth-visible, and keeps the workspace lease held until inactivity is proven or the control deadline expires

Current dispatch observation/drain facts include:

- accepted-boundary waiting is not a persisted control-state enum and is not
  carried as a distinct raw `delivery-state.json` observation value; the raw
  delivery projection stays `transport_state: accepted` and
  `controller_observation_state: live` while controller truth still waits for
  inactivity proof
- the shipped boundary-accept path does not fence the dispatch immediately; it
  revokes callback access, sets `control_deadline_at`, and leaves the accepted
  dispatch controller-truth-visible until inactivity is proven or the control
  deadline expires

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

- parent/root structural edits resolve role and policy refs through controller-side
  definition registry rows during validation; there is no separate shipped callback
  registry-read lane
- `yield` requires exactly one staged child assignment and does not open the
  child dispatch until accepted-boundary waiting proves the prior dispatch
  inactive and fenced
- operator pause does not consume a staged child assignment; only an accepted
  `yield` can later consume that staged child into the child dispatch path
- accepted-boundary waiting is not a persisted control-state enum; raw
  `delivery-state.json` stays `controller_observation_state: live` while the
  controller derives the waiting meaning from dispatch truth
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
- pause closes the current dispatch for operator control, revokes callback
  access, marks the flow `paused`, and if inactivity is not already proven it
  keeps the dispatch controller-truth-visible as `abort_requested` until proof
  or timeout
- continue resumes a paused flow or reopens a resumable dispatch for the
  current attempt when the expected active flow revision still matches
- continue performs the foreground inactivity-proof step for pause and accepted
  boundary waits before any replacement dispatch opens; it fences the prior
  dispatch only after proof, promotes timed-out waits to `ambiguous`, and lets
  only an accepted `yield` consume staged child work into a child dispatch
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
- parent/root `yield` stages the child as the next current node, but the child
  dispatch opens only after accepted-boundary waiting proves the prior
  dispatch inactive and fenced
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

## Current post-commit effect rule

Current runtime write timing is strict controller-truth first:

- runtime and callback write routes commit controller-owned rows first
- the same transaction also stages durable `runtime_effects` rows for any file
  copy, manifest, dispatch, artifact-current-pointer, or attempt
  materialization work
- `RuntimeAsyncSession.commit()` wakes an app-lifespan effect runner after the
  DB commit returns
- the effect runner drains ready rows after return in priority order:
  `file_copy`, `manifest_materialization`, `dispatch_materialization`,
  `artifact_current_pointer_materialization`, then
  `attempt_materialization`
- operator snapshot/trace and observability GET routes expose the current file
  refs but do not recreate or repair missing files inline

Generated runtime files therefore remain derived projections, and they may lag
the API response briefly until the effect runner drains the queued work.

## Minimal example

```text
launch_task_runtime
  -> seed task + compiled plan + flow rows
  -> create root assignment and attempt
  -> open bootstrap dispatch
  -> queue workflow-manifest and attempt materialization
  -> commit controller truth + runtime_effects rows
  -> return API response
  -> effect runner writes workflow-manifest and attempt files after return

worker retry
  -> record terminal retry checkpoint
  -> accept boundary retry
  -> create new attempt for same assignment
  -> queue follow-up projection/materialization work
  -> wait through accepted-boundary drain / inactivity proof
  -> open replacement dispatch after the prior dispatch is fenced

parent yield
  -> stage exactly one child assignment
  -> accept boundary yield
  -> wait through accepted-boundary drain / inactivity proof
  -> open child dispatch after the prior dispatch is fenced
```

## Evidence

- inspected code in `apps/api/app/runtime/launch/service.py`
- inspected code in `apps/api/app/runtime/control/flows.py`
- inspected code in `apps/api/app/runtime/control/boundary.py`
- inspected code in `apps/api/app/runtime/control/parent_tools.py`
- inspected code in `apps/api/app/runtime/control/release.py`
- inspected code in `apps/api/app/runtime/control/callbacks.py`
- inspected code in `apps/api/app/runtime/control/observability.py`
- inspected code in `apps/api/app/runtime/post_commit.py`
- inspected code in `apps/api/app/db/session.py`
- inspected code in `apps/api/app/db/models/runtime/effects.py`
- inspected tests in `apps/api/tests/integration/test_phase3_runtime_routes.py`
- inspected tests in `apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
- inspected tests in `apps/api/tests/integration/test_runtime_schema_contract.py`
