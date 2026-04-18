# 08 — Phase 8: Production OpenClaw Bridge and Native Plugin Adapter

## Goal

Turn the delegated-execution contract into a real production bridge between AutoClaw and OpenClaw, with an optional bounded native OpenClaw plugin adapter for ergonomics, callback standardization, and reliable worker-scoped query/bundle semantics.

This phase completes the part that earlier phases intentionally left as a design contract:

- AutoClaw remains the control-plane source of truth
- OpenClaw remains the delegated execution engine
- the transport/callback boundary becomes real, typed, and testable

## Why this phase exists

Phase 3 established the flow-first runtime and the relational records needed for delegated execution:

- `node_sessions`
- `context_manifests`
- `node_attempts`
- `node_checkpoints`
- `approvals`
- `node_plan_revisions`

Phase 7 then hardens controller-side advancement and loop-governance semantics so the controller is the clear owner of runtime movement.

The main bridge is no longer hypothetical.

Current code already includes a real Gateway client in:

- `apps/api/app/integrations/openclaw.py`

and a controller-side dispatch service in:

- `apps/api/app/services/openclaw_bridge.py`

So the codebase can already create a real `/v1/responses` dispatch with:

- stable session routing
- a bootstrap/execution phase split
- native plugin-backed callback handling
- real durable callback facts for approval/replan/checkpoint paths

The important remaining gap is now **closeout quality**, not “bridge exists vs does not exist.”

Latest verified state:

- SSE hardening landed in the bridge client
- live approval path passed
- live replan path passed
- the manifest-ack route was hardened for the observed malformed-but-recoverable extra-hyphen UUID callback shape
- typed handoff publication is available through `publish_context_item`
- bounded typed read bundles now include worker bundle, runtime slice, timeline slice, operator snapshot, and flow audit
- a fresh max-complexity flow reached terminal success end-to-end

What still prevents calling Phase 8 fully green is smaller but real:

- docs were still describing the bridge as fundamentally blocked
- runtime recovery semantics are now substantially frozen in code/tests:
  - `response.failed` is treated as terminal bridge failure
  - watchdog same-session wake dispatch failure returns the node to safe blocked state
  - watchdog same-session wake timeout is treated as ambiguous delivery, so the attempt stays resumable and operators get inspect-before-retry guidance
  - operator guidance is explicit for ambiguous timeout states
  - wake budget is tracked per node attempt
- watchdog still does not auto-create a fresh retry attempt after wake exhaustion; that remains an explicit operator path
- downstream governance/review nodes still need richer first-class evidence propagation for fully hands-off runs
- broader shared/untrusted-worker trust hardening is not fully closed yet

That means the bridge is now materially working and good enough to unblock Phase 9 local-first productization, while Phase 8 still carries a short closeout list.

This phase exists to finish that list cleanly.

## Why this is Phase 8, not Phase X

This work is not an unrelated research branch.
It is the next concrete implementation stage after controller hardening.

Reasons to treat it as **Phase 8**:

- it depends on the flow-first runtime established by phases 3–6
- it benefits from the controller ownership clarified in Phase 7
- it closes a known stub in the current codebase rather than exploring a speculative side architecture
- it should become the default delegated-execution path, not a side experiment

Use a numbered phase so the roadmap admits that this bridge is part of the main migration plan.

## Current verified state

Current verified bridge/runtime facts:

- AutoClaw dispatches to OpenClaw through Gateway `POST /v1/responses`
- native plugin-backed callbacks are the real callback path; per-request Responses API client tool definitions are not the current bridge model
- `node_sessions.provider_session_key` is the durable delegated-session binding
- bootstrap and execution are separate dispatch phases
- approval resolution, replan adoption, checkpoint writes, and manifest acknowledgement all feed back into controller-owned advancement
- the bridge/plugin surface now exposes typed handoff publication plus bounded worker/operator read bundles for deterministic replan/review work
- the fresh max-complexity bridge run succeeded end-to-end, with one known residual caveat: review/governance still needed an operator nudge because evidence propagation remains thinner than the target contract

## Assumptions entering this phase

Before this phase starts, the codebase should already have:

- flow-first runtime truth
- `node_sessions` as the durable delegated-session binding
- context manifest projection and acknowledgement semantics
- controller-owned advancement on safe mutation paths
- explicit checkpoint / approval / replan runtime records
- no transcript text treated as control truth

Do not use this phase to re-litigate the flow-first reset or invent a new top-level runtime model.

## In scope

### 1. Production AutoClaw → OpenClaw transport

Implement the real integration client in:

- `apps/api/app/integrations/openclaw.py`

Use OpenClaw Gateway `POST /v1/responses` as the primary transport.

Expected properties:

- explicit Gateway auth
- explicit OpenClaw agent routing
- explicit stable session routing via `x-openclaw-session-key`
- structured request/response handling
- retry/timeout/error classification suitable for backend runtime use
- optional streaming support only when it improves diagnostics; correctness must not depend on it

Do **not** make CLI subprocess execution the primary bridge.

Not acceptable as the main runtime path:

- shelling out to `openclaw agent`
- transcript scraping
- using `/tools/invoke` as a fake session/runtime API

### 1A. Host enablement method from official OpenClaw docs

Before implementation assumes the bridge is usable, enable and verify the Gateway HTTP surface on the target OpenClaw host.

Required official config keys:

- `gateway.http.endpoints.responses.enabled: true`
- `gateway.http.endpoints.chatCompletions.enabled: true` when the broader OpenAI-compatible surface should be available explicitly

Recommended combined block:

```json5
{
  gateway: {
    http: {
      endpoints: {
        responses: {
          enabled: true,
          files: { allowUrl: false },
          images: { allowUrl: false },
        },
        chatCompletions: { enabled: true },
      },
    },
  },
}
```

Operational notes from official docs:

- Gateway config lives at `~/.openclaw/openclaw.json`
- supported edit methods are wizard, CLI config commands, Control UI, or direct file edit
- `gateway.*` changes are restart-required changes
- default reload mode is `hybrid`, so editing these keys on a live host may trigger an automatic restart
- `gateway.reload` itself is a hot-applied exception

Recommended low-surprise staging method:

1. set `gateway.reload.mode: "hot"`
2. add the endpoint block
3. wait for the logged restart-needed warning
4. restart manually during the maintenance window

Verification gate before AutoClaw bridge implementation depends on the host:

- authenticated `POST /tools/invoke` succeeds
- authenticated `GET /v1/models` returns `openclaw/default`
- authenticated `POST /v1/responses` succeeds
- if compatibility/debug surface is desired, authenticated `POST /v1/chat/completions` and `POST /v1/embeddings` also succeed

### 2. Stable session binding and worker isolation

Use existing AutoClaw `node_sessions` as the durable binding to a real OpenClaw session.

Rules:

- `node_sessions.provider_session_key` must become the real OpenClaw `sessionKey`
- session continuity remains scoped to `flow_node`, not retry attempt
- retrying the same node may reuse the same OpenClaw session
- structural replans that replace the node create a new session binding

Use a dedicated OpenClaw worker agent such as:

- `autoclaw-worker`

That worker should have:

- isolated workspace / auth / sessions
- narrow tool policy
- instructions oriented around delegated execution rather than human chat

### 3. Two-phase delegated execution boundary

Keep bootstrap and execution as separate phases.

#### Bootstrap phase

AutoClaw sends bootstrap instructions to the worker session with:

- flow/node/attempt identity
- context-manifest payload and hash
- role/policy metadata
- a narrow callback surface

The worker must acknowledge the projected manifest before execution begins.

#### Execution phase

After acknowledgement succeeds, AutoClaw sends the execution request to the same OpenClaw session.

The worker may then perform delegated reasoning/tool work until it reaches a real boundary.

This preserves the existing invariant:

- no execution before context acknowledgement

### 4. Typed callback contract as control truth

The controller must treat only typed callback facts as control truth.

Minimum callback surface:

- `ack_context_manifest`
- `record_checkpoint`
- `request_approval`
- `request_replan`

These callbacks should map to existing AutoClaw internal services/routes and produce durable runtime records.

The controller should **not** infer control outcomes from free-form OpenClaw text.

Text may be retained for explanation/audit, but not as the authoritative source for:

- success
- retry
- approval
- replan
- sync readiness

### 5. Optional bounded OpenClaw plugin adapter

This phase may include an optional OpenClaw plugin such as:

- `autoclaw-bridge`

Its role is to make the bridge feel more native inside OpenClaw, not to absorb the AutoClaw engine.

Important nuance:

- bounded means authority-thin, not logic-free
- if reliability requires it, the plugin may own deterministic query/bundle assembly, validation, and invariant checks close to the tool surface
- it still must not own AutoClaw state transitions

Good plugin responsibilities:

- native OpenClaw tools that forward typed callbacks to AutoClaw
- worker-scoped query/bundle tools that assemble compact snapshots across definitions, resources, runtime state, manifests, checkpoints, approvals, and recent events/log slices
- canonical snapshot assembly and replan/review bundle construction for the current task/flow/node slice
- current examples include `get_worker_bundle`, `get_flow_runtime_slice`, `get_flow_timeline_slice`, `get_flow_operator`, and `get_flow_audit`
- validation and invariant checks around session/manifest/checkpoint bindings before callback forwarding
- optional human-facing commands such as `/flow ...`
- optional worker-only hooks or policy injection
- optional health/debug route
- centralized auth/retry/logging for AutoClaw callback calls from within OpenClaw

Bad plugin responsibilities:

- owning AutoClaw’s control-plane truth
- embedding the whole AutoClaw scheduler/controller/runtime inside Gateway
- turning OpenClaw plugin lifecycle into the workflow-engine lifecycle

Important boundary:

- the plugin may replace per-request callback tool definitions, provide nicer native UX, and expose deterministic read/query helpers for reliable delegated work
- the plugin does **not** replace AutoClaw → OpenClaw runtime dispatch over `/v1/responses`
- the plugin may be semantics-thick for reliability, but it remains authority-thin: AutoClaw still owns scheduling, approval resolution, replan adoption, and execution truth
- any later broader OpenClaw-side AutoClaw inspect/operator/plugin surface is a **separate later phase**, not part of this bounded bridge-adapter phase

### 6. Bridge observability and failure classification

Add enough observability to debug bridge failures without transcript archaeology.

Track and expose facts such as:

- `flow_id`
- `flow_node_id`
- `node_attempt_id`
- OpenClaw `agentId`
- OpenClaw `sessionKey`
- request/response correlation ids where available
- last bridge error class

At minimum, distinguish:

- auth failure
- transport failure
- OpenClaw routing/session failure
- model/provider failure
- callback validation failure
- controller rejection of invalid callback payload

### 7. Verification and rollout

This phase should end with integration-quality verification rather than prompt-only confidence.

Expected verification:

- tests for `integrations/openclaw.py` request building and response handling
- tests for callback validation and mapping into internal runtime services
- tests for session reuse rules
- tests for bootstrap gating on manifest acknowledgement
- tests proving checkpoint/approval/replan callbacks become durable runtime facts
- staged rollout behind a flag or controlled default if needed

## Explicit non-goals

- do not embed the full AutoClaw engine inside an OpenClaw plugin
- do not replace AutoClaw’s DB/controller truth with Gateway/session truth
- do not use transcript parsing as the control boundary
- do not use `/tools/invoke` as the primary delegated-runtime transport
- do not make a hook/plugin framework the primary runtime architecture
- do not reintroduce a session-scoped active-state model parallel to `flow` / `flow_node` / `node_attempt`
- do not remove `POST /v1/responses` as the main AutoClaw → OpenClaw dispatch path
- do not treat Phase 8’s bounded plugin adapter as the moment to add full-definition publish/operator automation from inside OpenClaw

## Allowed implementation shape

A good implementation shape is:

1. backend integration client in `apps/api/app/integrations/openclaw.py`
2. controller/runtime wiring that invokes that client after local bootstrap setup
3. typed callback handling that writes only through AutoClaw’s existing runtime services
4. optional bounded OpenClaw plugin adapter for native tools/UX and deterministic worker-scoped query/bundle semantics, without shifting control ownership

If the plugin complicates delivery, ship the backend bridge first.
The plugin is an optional adapter, not the prerequisite for correctness.

## Relationship to earlier phases

### Phase 3

Phase 3 established the runtime records and contract for delegated execution.
It did **not** need to finish the production transport.

Phase 8 completes that unfinished integration boundary.

### Phase 7

Phase 7 makes controller advancement and loop boundaries explicit.
That controller ownership is what lets Phase 8 keep the bridge clean:

- OpenClaw executes work
- AutoClaw records facts
- AutoClaw advances the flow

Do not let Phase 8 blur that ownership again.

## Exit criteria

The phase is complete when all of the following are true:

- `apps/api/app/integrations/openclaw.py` and `apps/api/app/services/openclaw_bridge.py` provide a fully working production bridge with explicit timeout/failure handling rather than ambiguous closeout gaps
- a delegated node can bootstrap and execute through a real OpenClaw Gateway session
- `node_sessions.provider_session_key` is the real durable OpenClaw session binding
- manifest acknowledgement is enforced before execution begins
- checkpoint / approval / replan facts arrive in AutoClaw through typed callback handling rather than transcript parsing
- controller advancement remains owned by AutoClaw after each recorded fact
- the documented operator rule for ambiguous timeout states is explicit and tested
- docs and E2E runbooks describe the real plugin-backed bridge model and current caveats honestly
- if a plugin exists, it is clearly a bounded authority-thin bridge adapter and does not replace `/v1/responses` dispatch or AutoClaw control truth
