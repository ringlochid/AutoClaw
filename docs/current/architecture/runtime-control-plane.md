# Current runtime control plane

Status: Current

Last verified: 2026-05-21

Current runtime truth is controller-owned and relational. Prompt text, observability files, and other generated task-root artifacts are derived projections, not the authoritative source of control state.

Support-state readback details and other legacy fields below are documented here as shipped contrast only. They do not redefine the redesign target, which deletes or demotes several of those surfaces.

## Keywords

- current control plane
- dispatch turn
- assignment and attempt
- node session
- release precondition
- controller truth

## Current runtime truth

The current authoritative runtime spine includes these controller-owned record families:

- task and compose rows
- task resource bindings and manifest root rows
- workspace root lease rows
- compiled-plan rows
- flow, flow revision, flow node, and flow edge rows
- assignment, attempt, checkpoint, consumed-ref, produced-ref, and criteria-ref rows
- dispatch turn, node session, delivery-state, continuity-state, and watchdog-state rows
- artifact publication and current-pointer rows
- provider-event rows

Generated files under `_runtime/`, `outputs/`, `context/criteria/`, or `context/wiki/` are materialized from those records.

## Current control owners

Current runtime control is split across these grouped services:

- launch and task-root materialization: `apps/api/app/runtime/launch/**`
- operator controls: `apps/api/app/runtime/control/flow/service.py`
- checkpoint and boundary writes plus release legality: `apps/api/app/runtime/control/boundary/**`, `apps/api/app/runtime/control/checkpoint/recording.py`, and `apps/api/app/runtime/control/release/**`
- parent/root tools and child-assignment staging: `apps/api/app/runtime/control/assignment/**` and `apps/api/app/runtime/control/parent_tools.py`
- callback and node-tool session validation: `apps/api/app/runtime/control/dispatch/authority.py` and `apps/api/app/runtime/control/node_operations.py`
- prompt and manifest materialization: `apps/api/app/runtime/projection/**`
- post-commit sync output application and lifecycle reconciliation: `apps/api/app/runtime/effects/**`, `apps/api/app/runtime/control/observability.py`, and `apps/api/app/runtime/task_root/**`

There is no shared boundary-advance helper loop in the shipped tree.

## Current dispatch and attempt model

Current runtime works around one active flow plus one current open dispatch:

- `FlowModel.current_open_dispatch_id` points at the live dispatch when one is open
- `FlowModel.current_node_key` points at the node currently bound for control
- each `AssignmentModel` points at one `current_attempt_id`
- retries create a new `AttemptModel` for the same assignment
- callback HTTP and static `node MCP` access are bound to `NodeSessionModel.session_key` plus the current live dispatch, assignment, and attempt lineage for that task

Current dispatch replacement is explicit:

- a replacement dispatch is illegal while the previous dispatch is still in `launching`, `live`, `abort_requested`, or `ambiguous`
- a replacement dispatch requires the previous dispatch to be fenced first

Current dispatch control-state facts include:

- initial open state: `launching`
- confirmed live state: `live`
- cancel handshake state: `abort_requested`
- timeout or escalation state: `ambiguous`
- fenced or closed state: `fenced`
- the shipped cancel path does not fence the dispatch immediately; cancel requests `abort_requested`, sets a control deadline, makes further session-rooted callback and node-tool writes illegal, keeps the current dispatch controller-truth-visible, and keeps the workspace lease held until inactivity is proven or the control deadline expires

Current dispatch observation/drain facts include:

- accepted-boundary waiting is not a persisted control-state enum and is not carried as a distinct raw `delivery-state.json` observation value; the raw delivery projection stays transport-focused while controller truth still waits for inactivity proof
- the shipped boundary-accept path does not fence the dispatch immediately; it sets `control_deadline_at` and leaves the accepted dispatch controller-truth-visible until inactivity is proven or the control deadline expires
- current watchdog/lifecycle timing now keys off acceptance time, committed controller semantic progress, and committed provider-signal progress; checkpoint time alone does not extend the execution-stale deadline
- current automatic watchdog recovery stays limited to `redispatch_same_attempt` or `escalate`; it does not auto-mint a new attempt
- current runtime uses a dispatch-scoped Gateway reader plus controller-owned event ingester after acceptance commit; provider progress becomes runtime truth only after normalization and DB commit, not on raw socket receipt

## Current operator and callback controls

Current operator controls include:

- list runtime tasks
- inspect one runtime task
- continue a paused or resumable task runtime
- pause the current dispatch
- cancel the current task flow

Current callback and node-tool controls include:

- `record_checkpoint`
- `yield`
- `green`
- `retry`
- `blocked`
- parent/root tools such as `assign_child`, `add_child`, `update_child`, `remove_child`, `release_green`, and `release_blocked`

Current callback legality facts include:

- parent/root structural edits resolve role and policy refs through controller-side definition registry rows during validation; there is no separate shipped callback registry-read lane
- `yield` requires exactly one staged child assignment and does not open the child dispatch until accepted-boundary waiting proves the prior dispatch inactive and fenced
- operator pause does not consume a staged child assignment; only an accepted `yield` can later consume that staged child into the child dispatch path
- accepted-boundary waiting is not a persisted control-state enum; raw `delivery-state.json` stays transport-focused while the controller derives the waiting meaning from dispatch truth
- parent/root `retry` is illegal
- terminal boundaries require a terminal checkpoint whose outcome matches the requested boundary
- `green` for parent/root requires `release_green` first
- root `blocked` requires `release_blocked` first

## Current drift against target

Current shipped behavior no longer externalizes ordinary workflow progression through operator `continue`.

That means:

- after accepted `yield`, worker `green`, or accepted `retry`, current shipped progression to the next dispatch now reopens internally after inactivity proof or fencing
- that internalization now matches the target direction on ordinary post-boundary advancement
- `continue` is reserved for pause-resume only

Current shipped pause is also only a partially immediate hard stop:

- it revokes further session-rooted callback and node-tool writes immediately
- it blocks replacement dispatch progression immediately
- but it may still leave the old dispatch controller-visible as `abort_requested` or accepted-boundary waiting until inactivity proof or timeout resolves the old run

## Current status behavior

Current flow statuses are:

- `pending`
- `running`
- `blocked`
- `paused`
- `succeeded`
- `cancelled`

Current high-level status transitions are:

- launch opens the first/root dispatch and marks the flow `running`
- pause acts as a hard controller stop for further node writes and replacement progression, marks the flow `paused`, and if inactivity is not already proven it keeps the current dispatch controller-truth-visible as `abort_requested` until proof or timeout
- continue resumes a paused flow only; it is illegal on running, blocked, cancelled, or succeeded flows
- continue performs the foreground inactivity-proof step for paused-flow resume before any replacement dispatch opens
- cancel marks the current dispatch `abort_requested`, closes the current attempt when needed, makes further session-rooted callback and node-tool writes illegal, keeps the current dispatch controller-truth-visible, and marks the flow `cancelled`
- workspace lease release for a cancelled or terminal flow waits until the prior foreground dispatch is fenced by inactivity proof or timed out as `ambiguous`
- worker `green` points current controller truth back to the parent when one exists, otherwise the flow succeeds; the later parent dispatch now reopens internally after inactivity proof
- worker `retry` opens a new attempt for the same assignment and switches semantic currentness to that new attempt immediately; the later retry dispatch now reopens internally after inactivity proof
- parent/root `yield` stages the child assignment basis, switches semantic currentness to that child immediately at boundary acceptance, and reopens the child dispatch internally after accepted-boundary inactivity proof
- root terminal `blocked` or top-level terminal `green` can close the whole flow

## Current generated-file rule

Current generated files are support surfaces only:

- `_runtime/workflow-manifest.{json,md}`
- `_runtime/attempts/<attempt_id>/*`
- `_runtime/dispatch/<dispatch_id>/*`
- `outputs/artifacts/**`

They are useful for runtime sharing and observability, but they do not outrank the controller-owned DB rows above.

## Current post-commit effect rule

Current runtime write timing follows the local-tool-first split:

- ordinary runtime, checkpoint, boundary, retry, redispatch, structural, and operator writes commit controller-owned rows first
- the same request then applies the owned task-root file writes synchronously before returning
- those synchronous writes cover manifest, attempt and checkpoint indexes, artifact-current pointers, dispatch prompt and observability projections, and transient or external localization
- launch returns only after the stable root manifest, root attempt files, and opened-dispatch projections are readable
- operator snapshot and trace plus observability GET routes still expose current file refs as-is and do not recreate or repair missing files inline

Generated runtime files therefore remain derived projections, but the taught task-root reread surfaces are written before route success.

## Minimal example

```text
launch_task_runtime
  -> seed task + compiled plan + flow rows
  -> create root assignment and attempt
  -> open first/root dispatch
  -> commit controller truth
  -> write workflow-manifest, root attempt, and dispatch projections before return
  -> return API response

worker retry
  -> record terminal retry checkpoint
  -> accept boundary retry
  -> create new attempt for same assignment
  -> write follow-up attempt, manifest, and closed-dispatch projections before return
  -> wait through accepted-boundary drain / inactivity proof
  -> the lifecycle path reopens the replacement dispatch internally after the
     prior dispatch is fenced

parent yield
  -> stage exactly one child assignment
  -> accept boundary yield
  -> wait through accepted-boundary drain / inactivity proof
  -> the lifecycle path reopens the child dispatch internally after the prior
     dispatch is fenced

parent structural callback or node tool
  -> adopt the new structural revision/currentness
  -> commit controller truth
  -> rewrite stable workflow-manifest files before return
```

## Evidence

- inspected code in `apps/api/app/runtime/launch/service.py`
- inspected code in `apps/api/app/runtime/launch/persistence/runtime.py`
- inspected code in `apps/api/app/runtime/control/flow/service.py`
- inspected code in `apps/api/app/runtime/control/boundary/service.py`
- inspected code in `apps/api/app/runtime/control/parent_tools.py`
- inspected code in `apps/api/app/runtime/control/release/preconditions.py`
- inspected code in `apps/api/app/runtime/control/dispatch/authority.py`
- inspected code in `apps/api/app/runtime/control/node_operations.py`
- inspected code in `apps/api/app/runtime/effects/cases.py`
- inspected code in `apps/api/app/runtime/control/observability.py`
- inspected code in `apps/api/app/runtime/effects/worker.py`
- inspected code in `apps/api/app/db/session.py`
- inspected code in `apps/api/app/runtime/effects/queue.py`
- inspected tests in `apps/api/tests/integration/phase3/contracts/test_assignment_cases.py`
- inspected tests in `apps/api/tests/integration/phase3/contracts/test_parent_checkpoint_handoff_cases.py`
- inspected tests in `apps/api/tests/integration/phase3/contracts/test_structural_manifest_cases.py`
- inspected tests in `apps/api/tests/integration/phase3/routes/test_surface_contract.py`
- inspected tests in `apps/api/tests/integration/phase3/control/test_abort_cases.py`
- inspected tests in `apps/api/tests/integration/phase3/contracts/test_callback_cases.py`
- inspected tests in `apps/api/tests/integration/phase4b/mcp/node_server`
- inspected tests in `apps/api/tests/integration/runtime_schema_contract/test_database.py`
