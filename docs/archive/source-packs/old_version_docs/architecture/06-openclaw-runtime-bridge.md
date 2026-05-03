# 06 — OpenClaw Runtime Bridge

## Status

Draft — partially stale.

Current implementation reality:

- AutoClaw does perform a real OpenClaw dispatch through `POST /v1/responses`
- the current bridge uses native/plugin-backed callback handling
- per-request Responses API client tool definitions are **not** the current bridge model

Use `../../../../roadmap/08-phase-8-production-openclaw-bridge-and-native-plugin-adapter.md`, `../../../../roadmap/current.md`, and `../../../../e2e/phase8-happy-path.md` as the source of truth for the current shipping shape.

## Roadmap placement

This bridge design is intended to land as:

- `../../../../roadmap/08-phase-8-production-openclaw-bridge-and-native-plugin-adapter.md`

Phase 3 established the runtime contract and records for delegated execution.
Phase 8 is where the production transport/callback boundary is meant to become real.

Important boundary:

- main AutoClaw → OpenClaw dispatch remains `POST /v1/responses`
- an optional bounded OpenClaw plugin may improve native callback/UX behavior and provide deterministic worker-scoped query/bundle helpers when reliability requires them
- the plugin does **not** replace AutoClaw control truth or the main dispatch path
- the plugin may be semantics-thick for read/query/validation, but it remains authority-thin
- any later broader OpenClaw-side AutoClaw inspect/operator surface should be treated as a separate later-stage capability, not part of the core bridge contract

## Why this document exists

AutoClaw already models delegated execution relationally:

- `node_sessions`
- `context_manifests`
- `node_attempts`
- `node_checkpoints`
- `approvals`
- `node_plan_revisions`

The actual transport/runtime bridge into OpenClaw is no longer just a stub.

Current code includes:

- a real Gateway client in `apps/api/app/integrations/openclaw.py`
- controller-side bridge selection/build logic in `apps/api/app/services/openclaw_bridge.py`
- bootstrap/context/session preparation in:
  - `apps/api/app/runtime/runner.py` → `_bootstrap_node_attempt_context(...)`
  - `apps/api/app/runtime/dispatcher.py` → `ensure_node_session(...)`
  - `apps/api/app/runtime/dispatcher.py` → `project_context_manifest(...)`
  - `apps/api/app/runtime/dispatcher.py` → `acknowledge_context_manifest(...)`

So AutoClaw already creates the control-plane records **and** performs a real OpenClaw dispatch.

This document now serves two purposes:

- describe the intended long-term bridge contract
- preserve older alternative design ideas that should not be mistaken for the current shipping model

## Existing AutoClaw contract

AutoClaw docs already say the execution boundary should work like this:

1. create `node_attempt`
2. project `context_manifest`
3. dispatch bootstrap instructions to OpenClaw for read + acknowledge
4. only after acknowledgement, dispatch delegated node work to OpenClaw
5. record checkpoints/approvals/replans in AutoClaw relational truth

See:

- `../../../../architecture/02-authoring-compiler-runtime.md`
- `../../../../flows/02-default-runtime-lifecycle.md`
- `../../../../roadmap/03-phase-3-runtime-and-openclaw-integration.md`
- `../../../../architecture/03-control-plane-and-query-model.md`

The key invariant stays unchanged:

> OpenClaw is the delegated execution engine.
> AutoClaw remains the control-plane source of truth.

## Research findings from OpenClaw docs

### 1. OpenClaw has a real first-class agent runtime surface

Official docs describe the authoritative agent loop entry points as:

- Gateway RPC: `agent`, `agent.wait`
- HTTP: `POST /v1/responses`
- CLI: `openclaw agent`

Relevant docs:

- `https://docs.openclaw.ai/concepts/agent-loop`
- `https://docs.openclaw.ai/gateway/openresponses-http-api`
- `https://docs.openclaw.ai/cli/agent`

Important implication:

- do **not** shell out to `openclaw agent` from AutoClaw as the primary integration path
- use the Gateway runtime surface directly

### 2. `POST /v1/responses` is the cleanest backend integration surface for AutoClaw

OpenClaw’s Responses-compatible HTTP API:

- executes a normal Gateway agent run
- supports explicit agent routing (`x-openclaw-agent-id` or `model: openclaw/<agentId>`)
- supports explicit stable session routing (`x-openclaw-session-key`)
- supports streaming
- supports client-side function tools (`tools` + `function_call_output`)

This matters because AutoClaw is a Python backend and needs:

- a stable session per delegated node
- a narrow control callback surface
- no transcript scraping

Important current-state note:

- `/v1/responses` is still the correct transport
- but the current bridge uses native/plugin-backed callbacks rather than per-request client tool definitions

### 3. `/tools/invoke` is not the right primary bridge

OpenClaw’s HTTP tool-invoke surface is intentionally conservative.

The docs explicitly note a hard deny list that includes:

- `sessions_spawn`
- `sessions_send`
- `gateway`

Relevant doc:

- `https://docs.openclaw.ai/gateway/tools-invoke-http-api`

So the bridge should **not** be designed around “remote-call OpenClaw session tools over `/tools/invoke`”.

### 4. Multi-agent isolation is a feature, not a workaround

OpenClaw’s official multi-agent model gives each agent its own:

- workspace
- auth store (`agentDir`)
- session store
- tool policy

Relevant docs:

- `https://docs.openclaw.ai/concepts/multi-agent`
- `https://docs.openclaw.ai/tools/multi-agent-sandbox-tools`
- `https://docs.openclaw.ai/concepts/delegate-architecture`

This strongly suggests AutoClaw should target a **dedicated OpenClaw agent** for delegated work instead of reusing a personal/default agent.

### 5. Hooks/plugins are useful, and they are now part of the current bridge

OpenClaw hooks and plugins are real extension points.

Relevant docs:

- `https://docs.openclaw.ai/automation/hooks`
- `https://docs.openclaw.ai/plugins/architecture`

Earlier design thinking in this draft treated client-side function tools as the simplest first bridge.

Current implementation reality is different:

- the bridge now relies on a bounded native/plugin-backed callback surface
- dispatch still goes through `/v1/responses`
- AutoClaw still owns control truth

Treat later references in this draft to client-side function tools as an **older alternative model**, not the current shipping path.

## Later-stage expansion note

A future later-stage OpenClaw integration may reasonably expose richer AutoClaw inspect/operator surfaces from inside OpenClaw, including definition inspection, draft/validate/publish flows, and scoped runtime operator actions.

If that happens, keep the same hard rule:

- OpenClaw may become a powerful client of AutoClaw
- OpenClaw does **not** become the AutoClaw control plane
- all authoritative writes still go through typed AutoClaw APIs with audit and stale-write protection

## Recommended integration model

### 1. Transport: use OpenClaw Gateway `POST /v1/responses`

AutoClaw should call OpenClaw through the Gateway HTTP Responses API.

Why:

- easiest integration from Python
- official runtime surface
- stable session routing
- function-tool callback loop is already supported
- no subprocess orchestration
- no transcript scraping

Not recommended as the primary path:

- shelling out to `openclaw agent`
- `/hooks/agent` as the main runtime transport
- `/tools/invoke` as a fake session/runtime API

### 2. Session model: one `node_session` ↔ one OpenClaw session key

Use the existing AutoClaw `node_sessions` table as the durable binding to an OpenClaw session.

Rules:

- `node_sessions.provider_session_key` must become the **real** OpenClaw session key
- primary scope remains **per `flow_node`**, not per retry attempt
- retry attempts may reuse the same OpenClaw session when the node identity is unchanged
- replans that replace the node create a new `node_session` / session key binding

This matches AutoClaw’s current relational model and OpenClaw’s session continuity model.

In the lean target model, this OpenClaw session binding is a runtime read concern derived from `node_sessions` and manifests, not proof that AutoClaw needs a durable `RuntimeContainer` truth layer.

Current code boundary:

- `node_sessions` is the live durable session/runtime binding today
- workflow `image`, `compose`, and `container` resources may still compile/project as typed contract payloads, but they should not force a durable image/container persistence ontology
- Phase 9 persisted `task_images`, `task_composes`, `runtime_images`, and `runtime_containers`, but the durable value is in `task_composes`; Phase 12 should remove the thin image snapshots and derive live runtime state from `node_sessions` plus manifests instead of keeping separate runtime-container truth
- that keeps the bridge backend-agnostic without pretending Docker/OCI-style image/container tables are already the right durable boundary for every backend

### 3. Use a dedicated OpenClaw agent for AutoClaw workers

Create a dedicated OpenClaw agent such as `autoclaw-worker`.

That agent should have:

- its own workspace
- its own auth store
- a deliberately narrow tool policy
- instructions oriented around delegated node execution, not chat companionship

This gives:

- deterministic prompt/control behavior
- isolation from personal chat sessions
- cleaner audit/debugging
- room for later specialization (`autoclaw-sync`, `autoclaw-review`, etc.) if needed

### 4. Keep bootstrap and execution as separate phases

AutoClaw’s own docs already want a hard gate:

1. bootstrap/read context
2. acknowledge manifest
3. then execute work

Keep that shape.

### Bootstrap phase

AutoClaw sends a bootstrap request to the OpenClaw worker session with:

- node identity (`flow_id`, `flow_node_id`, `node_attempt_id`, `node_path`)
- role/policy/skill metadata
- `context_manifest` payload
- hashes / manifest id
- a very small allowed callback surface

The only control callback that must be available in this phase is:

- `ack_context_manifest`

Execution must **not** begin until AutoClaw records the acknowledgement.

### Execution phase

After ack succeeds, AutoClaw sends the execution request to the same OpenClaw session.

In this phase the worker may perform real delegated reasoning/tool work and may call a broader control surface.

### 5. Historical alternative: use OpenClaw client-side function tools as the control callback bridge

This section describes an older bridge design.
It is **not** the current shipping model.

Rather than adding a custom OpenClaw plugin first, this older design exposed a narrow function-tool contract in each `/v1/responses` request.

That would still have kept control truth in AutoClaw while letting OpenClaw ask for explicit controller actions.

### Historical minimum tool set

#### `ack_context_manifest`

Purpose:

- prove the worker has accepted the projected context slice

Suggested shape:

- `manifest_id`
- `manifest_hash`
- `summary`

Maps to:

- `POST /internal/flows/context-manifests/{manifest_id}/ack`

#### `record_checkpoint`

Purpose:

- emit a real execution boundary fact

Suggested shape:

- `flow_id`
- `flow_node_id`
- `node_attempt_id`
- `sequence_no`
- `status` (`green|retry|blocked|needs_approval`)
- `summary`
- `payload`
- `recommended_next_action`
- `failure_signature`
- `wait_reason`

Maps to:

- `POST /internal/flows/checkpoints`

#### `request_approval`

Purpose:

- request explicit operator approval without inventing transcript conventions

Maps to existing approval runtime/API behavior.

#### `request_replan`

Purpose:

- propose structural change through the existing `node_plan_revisions` / revision-adoption flow

Maps to existing replan runtime/API behavior.

### Optional later tools

Still later-phase, not required for the first bridge closeout:

- `sync_ready`
- `emit_observation`

Current implementation note:

- `publish_context_item` is already wired into the shipped plugin/API surface as a bounded typed handoff helper
- the plugin now capability-gates its broader operator surface: worker-lane installs register only bounded runtime tools by default
- opt-in operator/query helpers currently include `get_flow_operator`, `get_flow_runtime_slice`, `get_flow_timeline_slice`, `get_flow_audit`, `get_registry_snapshot`, `list_definition_versions`, and `validate_workflow_definition`
- opt-in registry write helpers currently include `put_definition_draft` and `publish_definition_version`
- broader control actions such as approval resolution, retry/cancel/continue, or revision adoption are still intentionally later-stage surfaces

### Typed handoff contract between nodes

Prompt construction should remain runtime-owned.
A worker should not directly inject a private free-form prompt into the next node's dispatch input.

Recommended default handoff channels:

- `record_checkpoint(..., summary, payload, recommended_next_action)` for real execution-boundary facts
- task workspace/context artifacts written into durable task roots
- explicit operator/runtime actions such as `request_approval` or `request_replan`

Current implementation note:

- runtime currently seeds `task-input` as a published `context_item`
- `GREEN` checkpoints publish shared `checkpoint-summary:*` context items that later manifests can project, including inline content when available
- `NEEDS_APPROVAL` / `BLOCKED` checkpoints do not auto-publish downstream handoff context today
- there is no first-class `message_for_next_node` field today
- a generic `publish_context_item` tool is now wired into the shipped bridge/plugin surface for typed handoff publication when checkpoint-only propagation is too thin

Recommended follow-through:

- keep transcript text non-authoritative
- if richer handoff is needed, add a typed `publish_context_item` / handoff tool rather than prompt residue
- let AutoClaw persist and scope the handoff item, for example flow-shared vs node-targeted, before projecting it into later manifests
- keep the runtime/controller responsible for filtering and projection, not the delegated worker

### 6. Controller behavior: tool calls are facts, transcript text is not

The controller should treat only these as control truth:

- function-tool calls returned by OpenClaw and validated by AutoClaw
- operator actions
- stored runtime records

The controller should **not** parse free-form OpenClaw text to infer:

- approvals
- retries
- replans
- success/failure
- governance readiness

Text may still be stored as audit/explanation, but not as the control source.

### 7. Phase 7 remains the owner of advancement

AutoClaw’s new controller-driven advancement stays in charge.

OpenClaw does not advance the flow directly.

The ownership boundary is:

- OpenClaw performs delegated work and requests control actions
- AutoClaw validates/persists the action
- AutoClaw runs `advance_flow_until_boundary(...)`

That preserves the Phase 7 control-plane-first design.

## Proposed request flow

## A. bootstrap request

AutoClaw → OpenClaw `/v1/responses`

Headers:

- `Authorization: Bearer ...`
- `x-openclaw-agent-id: autoclaw-worker`
- `x-openclaw-session-key: <node_session.provider_session_key>`

Body includes:

- system/developer instructions for delegated node bootstrap
- `context_manifest` contents
- function tools: `ack_context_manifest`

Expected result:

- OpenClaw calls `ack_context_manifest`
- AutoClaw validates hash/id and records acknowledgement
- if successful, controller may proceed to execution phase

## B. execution request

AutoClaw → OpenClaw `/v1/responses`

Same session key, same agent.

Body includes:

- node execution objective
- visible context references
- function tools:
  - `record_checkpoint`
  - `request_approval`
  - `request_replan`

Expected result:

- OpenClaw works until it reaches a real boundary
- boundary is emitted as one of the above tool calls
- AutoClaw writes the relational record
- controller advances from the new fact

## C. follow-up / retry / resume

AutoClaw sends another request to the same OpenClaw session key when:

- retrying the same node
- resuming after approval
- resuming after context or operator intervention
- continuing a loop-owner node

This preserves node-level working memory without making OpenClaw the source of runtime truth.

## Why this model is better than the alternatives

### Better than transcript scraping

Because all meaningful control actions are explicit and typed.

### Better than a custom OpenClaw plugin as step one

Because the Responses API already gives AutoClaw a callback loop via client tools.

### Better than shelling out to CLI

Because the Gateway is already the real runtime surface and session owner.

### Better than `/tools/invoke`

Because AutoClaw needs delegated agent turns with durable session continuity, not one-off operator tool RPCs.

## Official OpenClaw endpoint enablement and verification procedure

This section captures the exact host-preparation method from the official OpenClaw docs, so AutoClaw implementation work does not depend on chat memory.

### 1. Supported ways to edit Gateway config

OpenClaw docs describe four supported ways to change Gateway config in `~/.openclaw/openclaw.json`:

- interactive wizard: `openclaw onboard`, `openclaw configure`
- CLI one-liners: `openclaw config get/set/unset ...`
- Control UI → Config tab
- direct file edit of `~/.openclaw/openclaw.json`

For AutoClaw bridge bring-up, direct edit or a controlled config patch is usually the clearest.

### 2. Exact endpoint toggles from official docs

#### Enable OpenResponses

Official setting:

- `gateway.http.endpoints.responses.enabled: true`

Doc-backed JSON5 shape:

```json5
{
  gateway: {
    http: {
      endpoints: {
        responses: { enabled: true },
      },
    },
  },
}
```

This enables:

- `POST /v1/responses`

Docs also note that the same compatibility surface includes:

- `GET /v1/models`
- `GET /v1/models/{id}`
- `POST /v1/embeddings`
- `POST /v1/chat/completions`

#### Enable Chat Completions

Official setting:

- `gateway.http.endpoints.chatCompletions.enabled: true`

Doc-backed JSON5 shape:

```json5
{
  gateway: {
    http: {
      endpoints: {
        chatCompletions: { enabled: true },
      },
    },
  },
}
```

Docs state that when the OpenAI-compatible HTTP surface is enabled, it serves:

- `GET /v1/models`
- `GET /v1/models/{id}`
- `POST /v1/embeddings`
- `POST /v1/chat/completions`
- `POST /v1/responses`

#### Recommended combined enablement block for AutoClaw host prep

To avoid ambiguity across OpenClaw versions/config expectations, enable both endpoint families explicitly:

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

Why this combined block is the safest operational choice:

- AutoClaw needs `POST /v1/responses`
- `/v1/models` is the cleanest smoke test for agent-target discovery
- `/v1/chat/completions` and `/v1/embeddings` are useful compatibility/debug surfaces during bring-up
- disabling `responses.files.allowUrl` and `responses.images.allowUrl` keeps the HTTP surface tighter unless URL fetch is explicitly required later

### 3. Reload and restart behavior

Official OpenClaw config docs say:

- the Gateway watches `~/.openclaw/openclaw.json`
- default reload mode is `gateway.reload.mode = "hybrid"`
- `gateway.*` changes are restart-required changes
- in `hybrid`, restart-required changes are handled automatically
- `gateway.reload` itself is an exception and does not trigger restart

Operational implication:

- editing `gateway.http.endpoints.*` on a live host may trigger an automatic Gateway restart

For a no-surprise staging method, official behavior supports this sequence:

1. first set `gateway.reload.mode: "hot"`
2. then add the endpoint-enable block
3. expect the Gateway to log that a restart is needed, but not auto-restart
4. restart manually in a maintenance window

Staging snippet:

```json5
{
  gateway: {
    reload: { mode: "hot" },
  },
}
```

### 4. Authentication and routing assumptions

Official docs say these HTTP endpoints use normal Gateway auth:

- `Authorization: Bearer <token>`
- token/password modes are treated as trusted operator access for the Gateway instance

For AutoClaw bridge requests:

- use `model: "openclaw/default"` or `model: "openclaw/<agentId>"`
- or send `x-openclaw-agent-id`
- use `x-openclaw-session-key` for durable session routing
- use `x-openclaw-model` only when backend provider/model override is actually needed

### 5. Official verification procedure

The cleanest official smoke test for the OpenAI-compatible surface is:

```bash
curl -sS http://127.0.0.1:18789/v1/models \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

Expected result:

- returned models should include `openclaw/default`

Then verify the specific endpoints AutoClaw or operators intend to use.

#### Verify `/tools/invoke`

`/tools/invoke` is always enabled and is a good auth/path sanity check:

```bash
curl -sS http://127.0.0.1:18789/tools/invoke \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"tool":"sessions_list","args":{"limit":1}}'
```

Expected result:

- HTTP `200`
- JSON response body

#### Verify `/v1/responses`

```bash
curl -sS http://127.0.0.1:18789/v1/responses \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"model":"openclaw/default","input":"ping"}'
```

Expected result:

- HTTP `200`
- OpenResponses JSON payload

#### Verify `/v1/chat/completions`

```bash
curl -sS http://127.0.0.1:18789/v1/chat/completions \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"model":"openclaw/default","messages":[{"role":"user","content":"ping"}]}'
```

Expected result:

- HTTP `200`
- OpenAI-compatible JSON payload

#### Verify `/v1/embeddings`

```bash
curl -sS http://127.0.0.1:18789/v1/embeddings \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"model":"openclaw/default","input":"ping"}'
```

Expected result:

- HTTP `200`
- embeddings JSON payload

### 6. AutoClaw-specific host readiness gate

Before implementation work assumes the bridge is live, the target OpenClaw host should satisfy all of the following:

- authenticated `POST /tools/invoke` succeeds
- authenticated `GET /v1/models` returns `openclaw/default`
- authenticated `POST /v1/responses` succeeds
- if compatibility/debug surfaces are desired, authenticated `POST /v1/chat/completions` and `POST /v1/embeddings` also succeed
- the intended worker agent (for example `autoclaw-worker`) exists and is routable

Only after these checks pass should AutoClaw treat the host as bridge-ready.

## First implementation target inside AutoClaw

### `apps/api/app/integrations/openclaw.py`

This module should become a real client wrapper around the OpenClaw Responses API.

Minimum methods:

- `bootstrap_node_session(...)`
- `execute_node_attempt(...)`
- `continue_node_session(...)`

Supporting responsibilities:

- build `/v1/responses` request payloads
- map `node_sessions.provider_session_key` to OpenClaw session routing
- expose AutoClaw callback tools to the OpenClaw turn
- execute returned function calls against AutoClaw internal services/routes
- loop until a real control boundary is reached
- return structured results to runtime/controller code

### Runtime caller boundaries

Likely callers:

- `runner.py` after node attempt/context bootstrap
- later watchdog/retry/approval resume paths when delegated work should continue

The current `dispatcher.py` remains responsible for local relational setup:

- session binding row
- context projection
- manifest acknowledgement transition

The new integration layer becomes responsible for **remote delegated execution**.

## Explicit non-goals

- do not make OpenClaw the control-plane truth
- do not invent a second runtime state machine inside OpenClaw
- do not rely on transcript wording to infer control actions
- do not use the personal/default OpenClaw chat agent as the backend worker
- do not shell out to CLI as the main transport
- do not design around `/tools/invoke` session orchestration

## Open questions

These should be resolved during implementation:

1. whether bootstrap and execution should be two separate `/v1/responses` calls or a single multi-step call with a hard controller gate between tool outputs
   - recommended default: **two calls** for clarity and stronger enforcement
2. whether one dedicated agent is enough initially, or whether policy-separated agents are worth it from day one
   - recommended default: start with **one dedicated `autoclaw-worker` agent**
3. how much of `context_manifest` should go in prompt text versus attached files/input parts
   - prefer manifest metadata inline; attach large artifact content ephemerally when needed
4. whether streaming should be enabled for operator diagnostics in the first cut
   - recommended default: optional, not required for correctness

## Historical next implementation steps

This section captures the older client-side callback-tool implementation plan that preceded the current plugin-backed bridge.
It remains useful as design history, but it is **not** the current shipping checklist.

1. replace the `integrations/openclaw.py` placeholder with a real HTTP client wrapper
2. define the first callback-tool schemas:
   - `ack_context_manifest`
   - `record_checkpoint`
   - `request_approval`
   - `request_replan`
3. implement a bootstrap request flow against `/v1/responses`
4. implement an execution request flow against `/v1/responses`
5. wire the returned function calls into existing AutoClaw runtime services
6. keep `advance_flow_until_boundary(...)` as the only advancement owner after each recorded fact
