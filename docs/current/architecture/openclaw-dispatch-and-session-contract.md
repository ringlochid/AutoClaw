# Current OpenClaw dispatch and session contract

Status: Current

Last verified: 2026-05-17

This page defines the current delegated worker contract between AutoClaw runtime, the OpenClaw bridge boundary, and the shipped session-authority model.

Current delegated execution is OpenClaw-first, manifest-first, and session-bound.

This is current shipped lineage behavior only. It is not the redesign's canonical `/callback` API contract or its observability-only continuity model. Any session reuse, callback lineage, or continuity residue described here is contrast-only shipped behavior, not protected redesign target truth.

It is also not the redesign's canonical owner page for static v1 `node MCP`. That current v1 surface already exists in this tree, but its target contract still lives under `docs/redesign/**`.

It is also not the target canonical dispatch-control page. Current shipped transport already uses the OpenClaw Gateway WS RPC subset for `connect`, `agent`, `agent.wait`, and `sessions.abort`; this page documents that shipped path as current-tree truth only.

Current dispatch truth is staged and controller-owned:

- `prepared`
- `accepted`
- callback- or watchdog-driven progress after acceptance

Those states are persisted through dispatch, node-session, delivery-state, continuity-state, watchdog-state, and provider-event rows.

## Current dispatch candidate rule

Current dispatch walks the ordered active graph and selects the first OpenClaw-ready latest attempt.

The current candidate rules are reflected across the controller-side dispatch opening, continuity-state, and prompt-projection surfaces:

- use ordered active-revision nodes
- inspect only the latest attempt for each node
- if the latest attempt has a projected manifest and is `blocked` or `running`, dispatch in bootstrap shape
- if the latest attempt is `running` and has no projected manifest, dispatch in execution shape
- otherwise the node is not OpenClaw-ready

Current dispatch therefore does not scan arbitrary old attempts or old manifests.

## Current bootstrap vs execution shapes

### Bootstrap

Bootstrap dispatch happens when the attempt still has a projected manifest to acknowledge.

Current bootstrap prompt context includes:

- flow id
- flow node id
- node attempt id
- current manifest projection
- current assignment projection
- dispatch-local `task_id` and `session_key` node-tool context

### Execution

Execution redispatch happens when the latest attempt is already running and the current prompt should continue from current runtime truth.

Current execution prompt context includes:

- flow id
- flow node id
- node attempt id
- current manifest projection
- latest relevant checkpoint context when available
- dispatch-local `task_id` and `session_key` node-tool context

Current execution redispatch resends the full delegated worker text. It does not switch between full resend and a second compact continuation wrapper family.

## Current session and authority binding

Current session authority is rooted in the accepted dispatch's Gateway `sessionKey`.

Current shipped rules are:

- the Gateway `agent` acceptance path persists `DispatchTurn.gateway_session_key` and `DispatchTurn.gateway_run_id`
- the same acceptance path creates one live `NodeSessionModel` row for that dispatch with `node_session_id = node-session.<dispatch_id>`
- callback HTTP and static `node MCP` both validate the same presented `session_key` plus `task_id` against live `NodeSession`, current dispatch, current flow, current assignment, and current attempt truth
- missing, stale, revoked, inactive, mismatched-task, or non-current session usage is rejected through one shared validator path

Current session identity and current dispatch truth are related but not identical:

- `NodeSessionModel` is the live session-authority row
- `DispatchTurnModel` records the current dispatch lifecycle, Gateway session key, and current `runId`
- `DispatchDeliveryStateModel`, `DispatchContinuityStateModel`, and `ProviderEventRecordModel` are transport and observability projections derived from that controller-owned truth

Current session reuse is narrower than the older flow-node-scoped model:

- each accepted dispatch gets its own `NodeSessionModel` row
- parent/root same-attempt redispatch may reuse the previous fenced dispatch's Gateway `sessionKey`
- that reuse does not reuse the previous node-session row; the new accepted dispatch gets a fresh node-session row tied to the new dispatch id
- worker retry, child dispatch, and fresh-attempt recovery flows mint a fresh Gateway `sessionKey`

## Current manifest and callback lineage

Current prompt lineage is still manifest-first, but callback and node-tool writes are no longer manifest-keyed at the HTTP or MCP boundary.

Current shipped facts are:

- prompt rendering still surfaces the current manifest, current assignment, and latest relevant checkpoint context
- callback HTTP routes accept only the task path, the semantic payload, and `X-Autoclaw-Session-Key`
- static `node MCP` tools accept explicit `session_key` and `task_id` tool arguments
- the runtime no longer asks callers to echo `manifest_id`, `manifest_hash`, or `ack_checkpoint_id` back through callback or node-tool writes

Current docs must not imply that callers author manifest lineage directly on write requests. The controller-owned runtime derives legality from current DB truth and current prompt projections instead.

## Current OpenClaw request shape

Current transport projection and persisted dispatch truth assume the OpenClaw Gateway WS RPC subset rather than the older plain HTTP `/v1/responses` bridge call.

Current shipped request sequence is:

- `connect`
- `agent`
- `agent.wait`
- `sessions.abort`

Current `agent` payload includes:

- `sessionKey`
- `message`
- `idempotencyKey`

Current controller mapping is:

- `sessionKey` is the agent-scoped Gateway session key persisted on the dispatch row
- `message` is the joined prompt package from `instructions_text` plus `input_text`
- `idempotencyKey` is fresh per dispatch, currently `dispatch:<dispatch_id>`
- accepted responses return a fresh `runId`, which is also persisted on the dispatch row

## Current transport continuity rule

Current transport continuity is explicit and narrow.

Current code facts are:

- live dispatches send `full_prompt` only
- the prompt package includes dispatch-local `task_id` and `session_key` node-tool context
- the bridge does not populate a `previous_response_id` chain
- parent/root same-attempt redispatch reuses the earlier fenced dispatch's Gateway `sessionKey`, gets a fresh `runId`, sends a fresh `idempotencyKey`, and resends the full regenerated prompt package
- worker retry, child dispatch, and fresh-attempt recovery flows stay fresh-session
- persisted continuity-state truth is limited to `session_key_present` plus `invalidation_reason`

Current OpenClaw continuity therefore does not model:

- compact continuation vs full resend
- a second prompt-wrapper family for same-session redispatch
- previous-response-chain continuity
- broad persisted continuity catalogs beyond session-key presence and invalidation

## Current provider hint rule

Current watchdog may use provider-side transport activity only as a bounded hint.

Current controller-owned hint facts include:

- provider acceptance
- successful or failed `agent.wait`
- later normalized provider-event history

Current controller does not treat those hints as execution truth. Checkpoints, boundaries, current dispatch truth, and current session authority still outrank provider-side transport activity.

## Current dispatch event truth

Current bridge persists:

- one prepared dispatch record before send
- accepted provider handoff after acceptance
- append-only provider-event records from the Gateway transport layer
- provider terminal outcome when known

That means current transport outcomes are controller-owned observability records, not transient bridge-only details.

## Current streaming and timeout behavior

Current OpenClaw transport expects Gateway WS RPC request and response envelopes rather than direct SSE.

Current bridge behavior distinguishes:

- pre-send transport failure
- post-send normalization failure
- accepted run followed by successful `agent.wait`
- accepted run followed by timeout or failure during `agent.wait`
- accepted run cleaned up through `sessions.abort`

These all stay transport outcomes until a controller-owned write or watchdog action records the fact.

## Detached vs synchronous dispatch

Current internal dispatch route supports two delivery modes.

### Detached dispatch

Default internal dispatch:

- prepares the dispatch
- commits local handoff state
- spawns a detached background Gateway request
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
  -> prepare dispatch turn
  -> render full_prompt bundle
  -> send Gateway `agent` request with sessionKey + message + idempotencyKey
  -> persist accepted runId + gateway session key
  -> create live node-session row for that dispatch
  -> callback or node MCP writes validate the same task_id + session_key authority
```

## Expanded example

```text
root dispatch accepted with Gateway session key S1
  -> root yields to a child
  -> child dispatch opens with its own Gateway session key S2
  -> child finishes green and the parent/root redispatch path reopens the root node
  -> the new root dispatch gets a fresh dispatch id and fresh runId
  -> the reopened root dispatch reuses Gateway session key S1
  -> the reopened root prompt is still sent as full_prompt
```

## Evidence

- inspected code in `apps/api/app/runtime/control/dispatch/authority.py`
- inspected code in `apps/api/app/runtime/control/dispatch/gateway.py`
- inspected code in `apps/api/app/runtime/control/dispatch/gateway_launch_state.py`
- inspected code in `apps/api/app/runtime/control/dispatch/opening.py`
- inspected code in `apps/api/app/runtime/control/node_operations.py`
- inspected code in `apps/api/app/runtime/projection/dispatch/prompt.py`
- inspected code in `apps/api/app/runtime/projection/dispatch/materialization.py`
- inspected code in `apps/api/app/db/models/runtime/dispatch/turns.py`
- inspected code in `apps/api/app/db/models/runtime/dispatch/states.py`
- inspected code in `apps/api/app/db/models/runtime/dispatch/support.py`
- inspected code in `apps/api/app/api/routes/callback.py`
- inspected code in `apps/api/autoclaw/openclaw/node_server.py`
- inspected tests in `apps/api/tests/integration/phase2/bootstrap/test_dispatch.py`
- inspected tests in `apps/api/tests/integration/phase4a/test_foreground_lifecycle_gateway.py`
- inspected tests in `apps/api/tests/integration/phase4a/test_runtime_dispatch_gateway_integration.py`
- inspected tests in `apps/api/tests/integration/phase4b/mcp/test_node_server.py`

## Related current pages

- `runtime-control-plane.md`
- `openclaw-and-bridge-plugin.md`
- `manifest-projection-and-acknowledgement.md`
- `watchdog-and-runtime-monitoring.md`

## Redesign pointer

For the target OpenClaw-first worker boundary, monitoring contract, and controller loop, see `../../redesign/architecture/openclaw-worker-and-gateway-contract.md`, `../../redesign/architecture/runtime-monitoring-and-watchdog-automation.md`, and `../../redesign/architecture/runtime-boundary-and-controller-loop-contract.md`.

For the exact target session lifecycle and resend rules, see [OpenClaw session lifecycle](../../redesign/architecture/openclaw-session-lifecycle.md), [OpenClaw continuity and send modes](../../redesign/architecture/openclaw-continuity-and-send-modes.md), and [Prompt contract](../../redesign/prompt-layer/contract.md).
