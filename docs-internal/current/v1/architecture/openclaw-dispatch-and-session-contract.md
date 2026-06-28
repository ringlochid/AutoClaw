# Current OpenClaw dispatch and session contract

Status: Current

Last verified: 2026-06-28

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
- human-request and command-run terminal external-wait continuations may reuse the previous dispatch's Gateway `sessionKey` for any node when the previous dispatch is the explicit `previous_dispatch_id`, the task, node, assignment, and attempt lineage still match, the previous dispatch and node-session are fenced and closed, and the previous dispatch owns a terminal `pending_human_requests` or `command_runs` source row
- that reuse does not reuse the previous node-session row; a new accepted dispatch normally gets a fresh node-session row tied to the new dispatch id when local acceptance persistence succeeds cleanly
- ordinary worker retry, child dispatch, and fresh-attempt recovery flows mint a fresh Gateway `sessionKey`

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
- `extraSystemPrompt`
- `idempotencyKey`

Current controller mapping is:

- `sessionKey` is the agent-scoped Gateway session key persisted on the dispatch row
- `extraSystemPrompt` carries AutoClaw `instructions_text`: the AutoClaw-owned system/instruction layer for the dispatch
- `message` carries AutoClaw `input_text`: the regenerated node-facing dispatch input for the current turn
- `idempotencyKey` is fresh per dispatch, currently `dispatch:<dispatch_id>`
- accepted responses return a fresh `runId`, which is also persisted on the dispatch row
- any request-local compatibility residue such as empty `observed_events` fields is not current runtime truth and does not participate in dispatch binding, liveness, or provider-event persistence

The persisted `_runtime/dispatch/<dispatch_id>/prompt.md` artifact remains the combined human-readable readback rendered from the same split prompt with `# AutoClaw Dispatch Prompt`, `## Instructions`, and `## Dispatch Input` wrappers. That readback is not flattened into the live OpenClaw `message` payload.

Compatibility fallback:

- if an older Gateway explicitly rejects `extraSystemPrompt` before acceptance, AutoClaw may retry the same launch with the combined `prompt.md` readback in `message` and no `extraSystemPrompt`
- fallback is not used for accepted launches, ambiguous transport failures, post-send normalization failures, or ordinary provider errors

## Current transport continuity rule

Current transport continuity is explicit and narrow.

Current code facts are:

- live dispatches send `full_prompt` only
- the prompt package includes dispatch-local `task_id` and `session_key` node-tool context
- the bridge does not populate a `previous_response_id` chain
- parent/root same-attempt redispatch reuses the earlier fenced dispatch's Gateway `sessionKey` when that continuity basis remains lawful and otherwise falls back to a fresh Gateway `sessionKey`; either way it gets a fresh `runId`, sends a fresh `idempotencyKey`, and resends the full regenerated prompt package
- terminal human-request and command-run external-wait continuations use the same reuse rule for any node when the previous dispatch owns the terminal source row and the previous node-session is fenced and closed
- ordinary worker retry, child dispatch, and fresh-attempt recovery flows stay fresh-session
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

## Current launch retry and ambiguity behavior

Current dispatch launch failure is explicit controller state, not an accepted boundary and not a generic lifecycle wakeup.

Pre-send launch failure means the Gateway `agent` request was not sent. Current runtime records the dispatch as fenced with `delivery_status = transport_failed`, `launch_failure_phase = pre_send`, `launch_request_sent = false`, an incremented `launch_retry_count`, error provenance, and `next_launch_retry_at` when attempts remain. The lifecycle may reopen the same current semantic target after that backoff, using the original continuation source rather than the failed launch dispatch as the semantic boundary.

Post-send launch failure means the controller cannot prove whether the Gateway received the `agent` request or started work. Current runtime records `delivery_status = transport_ambiguous`, `control_state = ambiguous`, `launch_failure_phase = post_send`, `launch_request_sent = true`, and no `next_launch_retry_at`. The controller may request cleanup by session key, but it must not open a blind replacement without abort confirmation or other proof that no live Gateway work remains.

Rules:

- `pending` provider reconciliation means poll existing provider work by `gateway_run_id`; it does not mean retry launch.
- a failed pre-send launch dispatch is audit evidence, not a semantic continuation source
- retry-failed launch dispatches do not supersede the accepted or terminal boundary they attempted to reopen
- exhausted pre-send launch retries stop automatic reopen and leave operator recovery over controller truth
- post-send no-run-id ambiguity is replacement-blocking until cleanup proof or operator recovery

## Current dispatch return-shape note

Current repo-visible code and routes use detached/background Gateway handoff plus controller-owned acceptance, progress, and observability state.

Older docs mention an optional synchronous wait-for-response transport lane. The current repo does not show a shipped synchronous dispatch mode, so current behavioral teaching should not rely on it.

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

worker dispatch accepted with Gateway session key W1
  -> worker opens a human request or command run through a node tool
  -> the previous worker dispatch and node-session close as the external-wait boundary
  -> the human request or command run source row reaches terminal state
  -> the controller reopens the same worker assignment and attempt
  -> the reopened worker dispatch gets a fresh dispatch id and fresh runId
  -> the reopened worker dispatch reuses Gateway session key W1 when the source row and node-session authority still prove lawful continuity
```

## Evidence

- inspected code in `apps/api/src/autoclaw/runtime/dispatch/authority.py`
- inspected code in `apps/api/src/autoclaw/runtime/dispatch/gateway/session.py`
- inspected code in `apps/api/src/autoclaw/runtime/dispatch/gateway/__init__.py`
- inspected code in `apps/api/src/autoclaw/runtime/dispatch/gateway_launch_state.py`
- inspected code in `apps/api/src/autoclaw/runtime/dispatch/launch_retry.py`
- inspected code in `apps/api/src/autoclaw/runtime/dispatch/opening.py`
- inspected code in `apps/api/src/autoclaw/runtime/node_tools/node_operations.py`
- inspected code in `apps/api/src/autoclaw/runtime/projection/dispatch/prompt.py`
- inspected code in `apps/api/src/autoclaw/runtime/projection/dispatch/materialization.py`
- inspected code in `apps/api/src/autoclaw/persistence/models/runtime/dispatch/turns.py`
- inspected code in `apps/api/src/autoclaw/persistence/models/runtime/dispatch/states.py`
- inspected code in `apps/api/src/autoclaw/persistence/models/runtime/dispatch/support.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/callback.py`
- inspected code in `apps/api/src/autoclaw/interfaces/mcp/node/server.py`
- inspected tests in `apps/api/tests/integration/bootstrap/test_dispatch.py`
- inspected tests in `apps/api/tests/integration/gateway/test_foreground_lifecycle_gateway.py`
- inspected tests in `apps/api/tests/integration/gateway/runtime_dispatch_gateway/launch/test_integration.py`, `apps/api/tests/integration/gateway/runtime_dispatch_gateway/test_cleanup_integration.py`, and `apps/api/tests/integration/gateway/runtime_dispatch_gateway/test_ingest_integration.py`
- inspected tests in `apps/api/tests/integration/gateway/runtime_dispatch_gateway/launch/test_retry_integration.py`
- inspected tests in `apps/api/tests/integration/gateway/test_gateway_session_reuse.py`
- inspected tests in `apps/api/tests/integration/mcp/node_server`

## Related current pages

- `runtime-control-plane.md`
- `openclaw-and-bridge-plugin.md`
- `manifest-projection-and-acknowledgement.md`
- `watchdog-and-runtime-monitoring.md`

## Design pointer

For the target OpenClaw-first worker boundary, monitoring contract, and controller loop, see `../../../design/v1/architecture/openclaw-worker-and-gateway-contract.md`, `../../../design/v1/architecture/runtime-monitoring-and-watchdog-automation.md`, and `../../../design/v1/architecture/runtime-boundary-and-controller-loop-contract.md`.

For the exact target session lifecycle and resend rules, see [OpenClaw session lifecycle](../../../design/v1/architecture/openclaw-session-lifecycle.md), [OpenClaw continuity and send modes](../../../design/v1/architecture/openclaw-continuity-and-send-modes.md), and [Prompt contract](../../../design/v1/prompt-layer/contract.md).
