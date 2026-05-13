# Current OpenClaw dispatch and session contract

Status: Current

Last verified: 2026-05-12

This page defines the current delegated worker contract between AutoClaw runtime, the OpenClaw bridge, and the current node session model.

Current delegated execution is OpenClaw-first, manifest-first, and session-bound.

This is current shipped lineage behavior only. It is not the redesign's canonical `/callback` API contract or its observability-only continuity model.

It is also not the target canonical dispatch-control path. Current shipped transport still dispatches through Gateway HTTP `POST /v1/responses`, while the target redesign should prefer Gateway WS RPC for start/wait/abort control.

Current dispatch truth is now staged and controller-owned:

- `prepared`
- `accepted`
- callback-driven progress after manifest ack or checkpoints

Those states are persisted through OpenClaw dispatch records plus provider event records.

## Current dispatch candidate rule

Current dispatch walks the ordered active graph and selects the first
OpenClaw-ready latest attempt.

The current candidate rules are reflected across the controller-side dispatch
opening, continuity-state, and prompt-projection surfaces:

- use ordered active-revision nodes
- inspect only the latest attempt for each node
- if the latest attempt has a projected manifest and is `blocked` or `running`, dispatch in `bootstrap` phase
- if the latest attempt is `running` and has no projected manifest, dispatch in `execution` phase
- otherwise the node is not OpenClaw-ready

Current dispatch therefore does not scan arbitrary old attempts or old manifests.

## Current bootstrap vs execution phases

### Bootstrap

Bootstrap dispatch happens when the attempt has a projected manifest.

Current bootstrap envelope includes:

- flow id
- flow node id
- node attempt id
- node session key
- manifest id
- manifest hash
- serialized manifest payload
- explicit instruction that the first action should be acknowledging the projected manifest

Bootstrap is therefore lineage-first. Normal execution should not continue until the projected manifest is acknowledged.

### Execution

Execution redispatch happens when the latest attempt is already `running` and the latest manifest is acknowledged.

Current execution envelope includes:

- flow id
- flow node id
- node attempt id
- node session key
- next suggested checkpoint sequence
- latest acknowledged manifest id
- latest acknowledged manifest hash
- latest acknowledged `ack_checkpoint_id`
- latest acknowledged manifest payload

Current execution redispatch keeps using the latest acknowledged lineage. It does not mint a new manifest only because the worker is being resumed or woken.

Current execution redispatch also resends full delegated worker text through `input`. It does not yet switch between full resend and compact continuation modes.

## Current session binding

Current dispatch always ensures a current `NodeSession` through `ensure_node_session(...)`.

Current rules are:

- one current delegated session is bound to the current latest attempt for the flow node
- if no session exists, one is created with a generated OpenClaw session key
- if a session exists, it is rebound to the current attempt
- ended sessions are re-opened by clearing `ended_at`
- the session status is reset to `idle` before dispatch preparation

Current runtime therefore already assumes one current delegated session per current attempt.

Current session identity and current dispatch truth are related but not identical:

- `NodeSession` binds the delegated session identity to the current attempt
- `OpenClawDispatch` records one prepared or accepted provider handoff for that attempt
- `OpenClawDispatchEvent` records provider-side acceptance and stream-hint events

Current `NodeSession` storage is effectively flow-node scoped, but operationally rebound to the latest attempt for that node.

That means:

- the durable session row is attached to the flow node
- dispatch preparation rebinds that row to the latest attempt
- same-session continuity may survive within the node across current implementation retries
- current code does not yet enforce the target redesign's attempt-scoped session remint policy

Important current watchdog fact:

- bootstrap watchdog auto-retry currently remints the attempt and manifest lineage
- it does not yet guarantee a fresh provider session key on every bootstrap retry
- fresh bootstrap retry session remint remains desired target behavior, not current implementation truth

## Current manifest and callback lineage

Current callback lineage is strict.

Bootstrap callbacks use:

- `node_session_key`
- `manifest_id`
- `manifest_hash`

Execution callbacks and worker-bundle reads use:

- `node_session_key`
- `manifest_id`
- `manifest_hash`
- latest valid `ack_checkpoint_id` when the route requires acknowledged execution binding

Current docs must not imply that older checkpoint lineage or older manifests are reusable. The bridge prompt explicitly tells the worker to keep using the latest acknowledged manifest lineage from the envelope.

## Current OpenClaw request shape

Current transport projection and persisted continuity state still assume this
OpenClaw/Gateway-style request shape:

- `POST /v1/responses`
- `Authorization: Bearer <gateway token>`
- internal AutoClaw API key header for callback authorization
- `x-openclaw-session-key`
- `x-openclaw-agent-id`
- `Accept: text/event-stream`

Current request payload includes:

- `model: openclaw/<agent_id>`
- `input`
- `stream: true`
- optional instructions
- optional previous response id
- optional tool list and tool choice
- optional user
- optional max output tokens

## Current transport continuity rule

Current transport continuity is intentionally light.

Current code facts are:

- the bridge always sends delegated worker text through `input`
- the bridge does not currently populate top-level `instructions`
- the bridge does not currently populate `previous_response_id`
- continuity is therefore mostly stable `session_key` reuse plus current runtime lineage, not a first-class prompt-continuity contract
- current continuity/session reuse still belongs to the shipped manifest/session acknowledgement model, not the redesign's canonical transport-only `same_session_continue` rule

Current OpenClaw session reuse exists, but the bridge does not yet model:

- an execution-contract hash
- compact continuation vs full resend
- previous-response-chain continuity
- session continuity state as a first-class runtime concept

## Current provider hint rule

Current watchdog may use provider-side stream activity only as a bounded hint.

Current controller-owned hint facts include:

- provider acceptance
- first meaningful SSE data event
- later output or tool-related SSE activity

Current controller does not treat those hints as execution truth.

Manifest ack and checkpoints still outrank provider-side activity.

## Current dispatch event truth

Current bridge persists:

- one prepared dispatch record before send
- accepted provider handoff after provider acceptance
- append-only provider hint events from the local SSE reader
- provider terminal outcome when known

That means current transport outcomes are no longer only transient bridge details. They are now controller-owned observability records.

## Current streaming and timeout behavior

Current OpenClaw transport expects SSE and reads terminal `response.completed` or `response.failed` events.

Current bridge behavior distinguishes:

- request timeout
- transport failure
- non-success HTTP response
- streaming response without terminal event
- streaming failed response

These all stay transport outcomes. They do not become runtime truth until a controller-owned write or watchdog action records a fact.

## Detached vs synchronous dispatch

Current internal dispatch route supports two delivery modes.

### Detached dispatch

Default internal dispatch:

- prepares the dispatch
- commits local handoff state
- spawns a detached background request
- returns `202 Accepted`

This is the normal non-blocking delivery mode.

### Synchronous dispatch

Optional `wait_for_response=true`:

- prepares the dispatch
- waits for the OpenClaw response
- returns bridge response metadata inline

This is a transport convenience mode. It does not change runtime truth ownership.

## Minimal example

```text
projected manifest exists
  -> select latest attempt
  -> ensure current node session
  -> build bootstrap envelope
  -> send POST /v1/responses with x-openclaw-session-key
  -> worker must ack manifest before normal execution
```

## Expanded example

```text
continue
  -> controller projects manifest
  -> internal dispatch route prepares OpenClaw request
  -> detached dispatch returns 202 Accepted
  -> worker acks manifest with manifest_id + manifest_hash + node_session_key
  -> later execution redispatch uses latest acknowledged manifest lineage
  -> worker records checkpoints with the same acknowledged lineage
```

## Evidence

- inspected code in `apps/api/app/runtime/control/dispatch/opening.py`
- inspected code in `apps/api/app/runtime/projection/dispatch/prompt.py`
- inspected code in `apps/api/app/runtime/projection/dispatch/materialization.py`
- inspected code in `apps/api/app/db/models/runtime/dispatch/turns.py`
- inspected code in `apps/api/app/db/models/runtime/dispatch/states.py`
- inspected code in `apps/api/app/db/models/runtime/dispatch/support.py`
- inspected code in `apps/api/app/api/routes/callback.py`
- inspected tests in `apps/api/tests/integration/phase2/bootstrap/test_dispatch.py`
- inspected tests in `apps/api/tests/integration/phase3/routes/test_surface_contract.py`

## Related current pages

- `runtime-control-plane.md`
- `openclaw-and-bridge-plugin.md`
- `manifest-projection-and-acknowledgement.md`
- `watchdog-and-runtime-monitoring.md`

## Redesign pointer

For the target OpenClaw-first worker boundary, monitoring contract, and controller loop, see `../../redesign/architecture/openclaw-worker-and-gateway-contract.md`, `../../redesign/architecture/runtime-monitoring-and-watchdog-automation.md`, and `../../redesign/architecture/runtime-boundary-and-controller-loop-contract.md`.

For the exact target session lifecycle and resend rules, see [OpenClaw session lifecycle](../../redesign/architecture/openclaw-session-lifecycle.md), [OpenClaw continuity and send modes](../../redesign/architecture/openclaw-continuity-and-send-modes.md), and [Prompt contract](../../redesign/prompt-layer/contract.md).
