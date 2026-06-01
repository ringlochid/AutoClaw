# Current OpenClaw dispatch and session contract

Status: Current

Last verified: 2026-05-24

This page defines the current delegated worker contract between AutoClaw runtime, the OpenClaw bridge boundary, and the shipped session-authority model.

Current delegated execution is OpenClaw-first, prompt-regenerated, and session-bound.

This is current shipped lineage behavior only. It is not the design's canonical `/callback` API contract or its observability-only continuity model. Any session reuse, callback lineage, or continuity residue described here is contrast-only shipped behavior, not protected design target truth.

It is also not the design's canonical owner page for static v1 `node MCP`. That current v1 surface already exists in this tree, but its target contract still lives under `docs-internal/design/v1/**`.

It is also not the target canonical dispatch-control page. Current shipped transport already uses the OpenClaw Gateway WS RPC subset for `connect`, `agent`, `agent.wait`, and `sessions.abort`; this page documents that shipped path as current-tree truth only.

Current/debt residues such as projected-manifest heuristics, older `bootstrap` wording, or other first-dispatch-versus-later-redispatch teaching in this page are shipped contrast only. They are not design dispatch canon.

Current dispatch truth is staged and controller-owned:

- `prepared`
- `accepted`
- callback- or watchdog-driven progress after acceptance

Those states are persisted through dispatch, delivery-state, continuity-state, watchdog-state, and provider-event rows, with live node-session authority rows present only when local acceptance persistence succeeds cleanly.

## Current dispatch candidate rule

Current dispatch walks the ordered active graph and selects the first OpenClaw-ready latest attempt.

The current candidate rules are reflected across the controller-side dispatch opening, continuity-state, and prompt-projection surfaces:

- use ordered active-revision nodes
- inspect only the latest attempt for each node
- if the latest attempt has a projected manifest and is `blocked` or `running`, current code treats the next open as the first dispatch for that attempt
- if the latest attempt is `running` and has no projected manifest, current code treats the next open as a later redispatch on current runtime truth
- otherwise the node is not OpenClaw-ready

Current dispatch therefore does not scan arbitrary old attempts or old manifests. Current docs should treat the projected-manifest heuristic as shipped implementation residue, not as a canonical `bootstrap | execution` dispatch phase contract.

## Current first-dispatch vs later-redispatch context

### First dispatch for an attempt

The first dispatch for an attempt opens from launch/materialization truth before a later checkpoint handoff drives the prompt.

Current first-dispatch prompt context includes:

- flow id
- flow node id
- node attempt id
- current manifest projection
- current assignment projection
- dispatch-local `task_id` and `session_key` node-tool context

### Later redispatch on the same attempt

Later redispatch happens when the latest attempt is already running and the current prompt should continue from current runtime truth.

Current later-redispatch prompt context includes:

- flow id
- flow node id
- node attempt id
- current manifest projection
- latest relevant checkpoint context when available
- dispatch-local `task_id` and `session_key` node-tool context

Current later redispatch resends the full delegated worker text. It does not switch between full resend and a second compact continuation wrapper family.

## Current session and authority binding

Current session authority is rooted in the accepted dispatch's Gateway `sessionKey`.

Current shipped rules are:

- the Gateway `agent` acceptance path persists `DispatchTurn.gateway_session_key` and `DispatchTurn.gateway_run_id`
- the same acceptance path normally creates one live `NodeSessionModel` row for that dispatch with `node_session_id = node-session.<dispatch_id>`
- callback HTTP and static `node MCP` both validate the same presented `session_key` plus `task_id` against live `NodeSession`, current dispatch, current flow, current assignment, and current attempt truth
- missing, stale, revoked, inactive, mismatched-task, or non-current session usage is rejected through one shared validator path

Current session identity and current dispatch truth are related but not identical:

- `NodeSessionModel` is the live session-authority row
- `DispatchTurnModel` records the current dispatch lifecycle, Gateway session key, and current `runId`
- `DispatchDeliveryStateModel`, `DispatchContinuityStateModel`, and `ProviderEventRecordModel` are transport and observability projections derived from that controller-owned truth

Current session reuse is narrower than the older flow-node-scoped model:

- each accepted dispatch that completes local acceptance persistence cleanly gets its own `NodeSessionModel` row
- parent/root same-attempt redispatch reuses the previous fenced dispatch's Gateway `sessionKey` when that continuity basis remains lawful and otherwise falls back to a fresh Gateway `sessionKey`
- that reuse does not reuse the previous node-session row; a new accepted dispatch normally gets a fresh node-session row tied to the new dispatch id when local acceptance persistence succeeds cleanly
- worker retry, child dispatch, and fresh-attempt recovery flows mint a fresh Gateway `sessionKey`

## Current manifest and callback lineage

Current prompt reread still uses the manifest projection as shared workflow context, but callback and node-tool writes are no longer manifest-keyed at the HTTP or MCP boundary.

Current shipped facts are:

- prompt rendering still surfaces the current manifest, current assignment, and latest relevant checkpoint context
- callback HTTP routes accept only the task path, the semantic payload, and explicit `session_key`
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
- any request-local compatibility residue such as empty `observed_events` fields is not current runtime truth and does not participate in dispatch binding, liveness, or provider-event persistence

## Current transport continuity rule

Current transport continuity is explicit and narrow.

Current code facts are:

- live dispatches send `full_prompt` only
- the prompt package includes dispatch-local `task_id` and `session_key` node-tool context
- the bridge does not populate a `previous_response_id` chain
- parent/root same-attempt redispatch reuses the earlier fenced dispatch's Gateway `sessionKey` when that continuity basis remains lawful and otherwise falls back to a fresh Gateway `sessionKey`; either way it gets a fresh `runId`, sends a fresh `idempotencyKey`, and resends the full regenerated prompt package
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

Current shipped contrast:

- `last_provider_signal_at` now moves on committed, liveness-relevant provider progress from the dispatch-scoped ingest seam
- current execution-stale anchoring can use committed provider-signal time as one of the progress anchors, but raw socket receipt and uncommitted queue state still do not become controller truth
- `agent.wait` remains terminal confirmation and timeout or terminal metadata reconciliation; it is not the first mid-run provider-progress write path
- current code uses a dispatch-scoped queue plus ingester after acceptance commit rather than request-local `agent` or `agent.wait` event buffering as runtime truth
- current code now accepts current OpenClaw raw labels such as `assistant.delta`, `assistant.message`, optional `thinking.delta`, `tool.call.started|delta|completed|failed`, and `run.completed|failed|cancelled|timed_out`, while still tolerating older `response.*` and bare `tool.call` labels as compatibility input

Current controller does not treat those hints as execution truth. Checkpoints, boundaries, current dispatch truth, and current session authority still outrank provider-side transport activity.

## Current dispatch event truth

Current bridge persists:

- one prepared dispatch record before send
- accepted provider handoff after acceptance
- append-only provider-event records from the Gateway transport layer
- provider terminal outcome when known

Current parent/root same-attempt watchdog replacement also preserves a valid dispatch-local staged child basis when the fenced prior dispatch is being lawfully reopened on the same assignment and attempt lineage. That staged child basis still belongs to the dispatch turn, not to the attempt.

That means current transport outcomes are controller-owned observability records, not transient bridge-only details.

## Current streaming and timeout behavior

Current OpenClaw transport expects Gateway WS RPC request and response envelopes rather than direct SSE.

Current bridge behavior distinguishes:

- pre-send transport failure
- post-send normalization failure
- accepted run followed by successful `agent.wait`
- accepted run followed by bare live `agent.wait` timeout with no terminal metadata
- accepted run followed by terminal `agent.wait` timeout metadata or failure
- accepted run cleaned up through `sessions.abort`

These all stay transport outcomes until a controller-owned write or watchdog action records the fact. Current accepted-boundary running cleanup may also finish as controller `fenced` while preserving `delivery_status = transport_ambiguous` when timeout cleanup proves the slot must be cleaned up even though transport certainty was not achieved.

Current adapter compatibility also accepts current Gateway terminal metadata on `agent.wait`, including string `error` plus fields such as `stopReason`, `livenessState`, `aborted`, and `yielded`. Only a bare `status=timeout` without terminal metadata remains the non-terminal polling outcome.

## Current dispatch return-shape note

Current repo-visible code and routes revalidated for this page use detached/background Gateway handoff plus controller-owned acceptance, progress, and observability state.

Older docs mentioned an optional synchronous wait-for-response transport lane. This Phase 0 current-behavior pass did not revalidate a shipped synchronous dispatch mode, so current behavioral teaching should not rely on it.

## Minimal example

```text
latest attempt still carries projected-manifest residue
  -> select latest attempt
  -> treat this as the first dispatch for that attempt
  -> prepare dispatch turn
  -> render full_prompt bundle
  -> send Gateway `agent` request with sessionKey + message + idempotencyKey
  -> persist accepted runId + gateway session key
  -> create live node-session row for that dispatch when local acceptance persistence succeeds cleanly
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
- inspected code in `apps/api/app/runtime/control/dispatch/gateway/__init__.py`
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
- inspected tests in `apps/api/tests/integration/phase4a/runtime_dispatch_gateway/test_launch_integration.py`, `apps/api/tests/integration/phase4a/runtime_dispatch_gateway/test_cleanup_integration.py`, and `apps/api/tests/integration/phase4a/runtime_dispatch_gateway/test_ingest_integration.py`
- inspected tests in `apps/api/tests/integration/phase4b/mcp/node_server`

## Related current pages

- `runtime-control-plane.md`
- `openclaw-and-bridge-plugin.md`
- `manifest-projection-and-acknowledgement.md`
- `watchdog-and-runtime-monitoring.md`

## Design pointer

For the target OpenClaw-first worker boundary, monitoring contract, and controller loop, see `../../../design/v1/architecture/openclaw-worker-and-gateway-contract.md`, `../../../design/v1/architecture/runtime-monitoring-and-watchdog-automation.md`, and `../../../design/v1/architecture/runtime-boundary-and-controller-loop-contract.md`.

For the exact target session lifecycle and resend rules, see [OpenClaw session lifecycle](../../../design/v1/architecture/openclaw-session-lifecycle.md), [OpenClaw continuity and send modes](../../../design/v1/architecture/openclaw-continuity-and-send-modes.md), and [Prompt contract](../../../design/v1/prompt-layer/contract.md).
