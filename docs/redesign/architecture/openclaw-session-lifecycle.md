# OpenClaw Session Lifecycle

Status: Target

## Purpose

This page freezes the v1 OpenClaw Gateway session and run lifecycle, the private node-MCP attachment boundary, and the same-attempt versus new-attempt recovery split.

## Need To Lock

1. Controller-owned prompt regeneration.
2. Gateway session versus Gateway run identity split.
3. Same-attempt replacement without live-run reuse.
4. New-attempt creation versus same-attempt redispatch.
5. Reserved provider-native continuity detail.
6. Trusted execution context and callback-authorization identity.

## Core Rule

The controller regenerates the canonical prompt on every dispatch. Canonical v1
uses the Gateway `sessionKey` as the private continuity and node/callback
authority identity. Parent/root same-attempt redispatch keeps that same
`sessionKey`, sends a fresh Gateway `agent` request with a fresh
`idempotencyKey`, and resends the full regenerated prompt package. Gateway then
returns a fresh `runId` for that live execution. Worker retry, fresh child
assignment, and any new attempt still mint a fresh `sessionKey`, send a fresh
launch request, and receive a fresh `runId`. Any stale
`same_session_continue` transport shape is historical adapter debt only, does
not describe the locked live controller path, and should be deleted when code
cleanup reaches it.

The Gateway transport boundary itself should stay compact:

- one canonical session-key normalizer owns agent scoping and validation
- one wire-facing launch input owns `sessionKey + message + idempotencyKey`
- controller dispatch metadata stays outside that wire-facing contract

## Source Of Truth Split

- Controller/DB runtime state remains the source of execution truth.
- Gateway `sessionKey` is the adapter-private transcript/context lane and the authority value validated behind v1 static node-MCP tool calls for one current execution context.
- Gateway `runId` is one live execution inside that session.
- Generated files such as `continuity-state.json` and `delivery-state.json` are projections of controller-owned support truth, not the authority.

## Trusted Execution Context

Each current controller dispatch resolves to one trusted OpenClaw execution context:

- `task_id`
- `assignment_key`
- `attempt_id`
- `dispatch_id`
- `sessionKey`
- current live `runId`

Rules:

- `sessionKey` is the continuity identity and the backend authority value used by v1 static node-MCP tool validation
- `runId` is the live-run correlation key for `agent.wait` and `sessions.abort`
- `runId` is the primary live-run discriminator for worker-lane provider-event routing and liveness
- `sessionKey` is continuity identity and an additional transport guard only; it must not be treated as sessionKey-only liveness proof when same-attempt parent/root redispatch reuses the session
- callback authority must be resolved server-side from runtime truth using the supplied v1 tool-call context
- v1 static node-MCP may surface `task_id` and `sessionKey` in dispatch-local prompt state for tool calls
- prompt-visible context may carry dispatch-local `task_id` and `sessionKey`
  for static v1 node-tool calls, but must not carry callback headers,
  auth-file paths, or other hidden binding secrets

Launch-ordering rule:

- for the launched run, OpenClaw returns the accepted response with authoritative `runId` before same-run agent/chat events for that run
- that does not create a connection-wide quiet period; unrelated broadcasts may still interleave on the same socket
- worker-lane dispatch therefore ignores pre-accept socket noise for liveness unless it is already provably bound to the accepted `runId`

## Identity Split

- `dispatch_id` = one AutoClaw controller dispatch path
- `attempt_id` = one current execution attempt on one assignment
- `assignment_key` = one current mission contract
- `sessionKey` = one adapter-private Gateway context and authority lane
- `runId` = one live Gateway execution inside that session
- provider `session_key` or `previous_response_id` = adapter-native transport detail only

Most important distinctions:

- changing `runId` does not automatically mean new attempt
- changing `attempt_id` always means new attempt lineage
- reusing `sessionKey` means history/context reuse only
- reusing the same live `runId` is not part of the canonical v1 architecture

## Gateway Session And Run Rule

Canonical session/run mapping in v1 is:

- same parent/root node + same assignment + same attempt + later redispatch:
  - same `sessionKey`
  - fresh `idempotencyKey`
  - new returned `runId`
- same worker node + same assignment + same attempt + later redispatch:
  - fresh `sessionKey`
  - fresh `idempotencyKey`
  - new returned `runId`
- new attempt:
  - new `sessionKey`
  - fresh `idempotencyKey`
  - new returned `runId`
- fresh child assignment:
  - new `sessionKey`
  - fresh `idempotencyKey`
  - new returned `runId`

This keeps parent/root continuity explicit without reusing the live run and keeps new-attempt and worker retry lineage separate from same-attempt parent/root redispatch.

## Same-Attempt Recovery

Same-attempt recovery keeps the same semantic execution lineage:

- `attempt_id`
- `assignment_key`

Controller action remains:

- `redispatch_same_attempt`

Canonical same-attempt dispatch rule for parent/root redispatch:

- keep the same Gateway `sessionKey`
- send a fresh Gateway `agent` request with a fresh `idempotencyKey`
- rebuild the full prompt from current authoritative runtime truth
- resend that full regenerated prompt package in the Gateway `agent` `message` field
- accept the fresh returned `runId` from Gateway as the new live execution handle
- keep any continuity-sideband bookkeeping adapter-private and non-canonical

Same-attempt recovery must not be described as retry lineage.

Transport-handle rule:

- canonical target worker-lane dispatch uses a dispatch-scoped runtime RPC handle
- one live dispatch owns one websocket connection or equivalent live transport handle, one reader, and one correlated ingest queue/worker
- startup compatibility probing may reuse transport primitives, but it is not the same thing as a shared process-global live dispatch client

Additional rules:

- the prior dispatch must already be closed or superseded before a new same-attempt run is created
- the prior run must already be terminal or abort-confirmed before the replacement run is allowed
- worker retry and any new attempt do not use this same-session path
- if the continuity basis is no longer trustworthy, this path is no longer
  legal and controller recovery must escalate or use another explicitly legal
  runtime action rather than minting a fresh-session same-attempt redispatch

## New Attempt Creation

New-attempt creation means:

- the earlier attempt is closed
- a new `attempt_id` is minted on the same assignment
- the new attempt uses a new Gateway `sessionKey`
- the new attempt opens a fresh Gateway `runId`
- the prior terminal checkpoint becomes the durable retry handover

This is different from same-attempt recovery and must be tracked separately by watchdog and operator tooling.

## Abort And Replacement Rule

When the current run may still be live:

1. call `sessions.abort`
2. mark local dispatch `abort_requested`
3. wait for terminal confirmation through `agent.wait` and/or canonical session event/history confirmation
4. if confirmed, mark the old dispatch non-current and terminal
5. only then choose either:
   - parent/root `redispatch_same_attempt` with the same `sessionKey`, a fresh `idempotencyKey`, and a fresh returned `runId`
   - `create_new_attempt` with a new `sessionKey`, a fresh `idempotencyKey`, and a fresh returned `runId`
6. if terminal confirmation never arrives before deadline, mark the slot `ambiguous` and escalate

Boundary consequence:

- accepted parent `yield` or child `green` still requires the old run to be proven inactive before the next live dispatch opens
- natural terminal completion is enough
- otherwise the controller must abort and fence the old run first

Drain-window policy:

- when parent/root replacement might still be avoidable, the controller should first enter a bounded drain window instead of aborting immediately
- that drain window is represented by `control_state = live` plus `control_deadline_at`; it is not a second persisted control-state enum in this lock
- default drain timeout is `30` seconds
- the controller should listen for Gateway lifecycle end/error for that exact `runId` and may also call `agent.wait`
- either confirmation source ends the drain window immediately
- the controller should not blindly sleep the whole window when terminal confirmation already arrived
- only if the drain window expires without terminal confirmation should the controller escalate to abort or ambiguity handling

Config placement rule:

- `dispatch_drain_timeout_seconds` is a runtime/controller knob and belongs under `[runtime]` in the canonical local `config.toml`
- if later implementation needs more session/drain tuning knobs, add them to the same config owner surface instead of hardcoding them in runtime modules, CLI flows, or OpenClaw wrapper docs

See [Install and onboard](../how-to/install-and-onboard.md) for the canonical config owner page.

There is no `parent_gate` resume path in this lifecycle, and there is no canonical "resume the stopped run" path in v1.

## Reserved Provider Continuity Detail

Canonical v1 parent/root redispatch does not depend on provider-native continuity fields such as `same_session_continue` or `previous_response_id`.

If any stale adapter branch still carries residue in those names, keep it below the core lock:

- it is historical adapter-private debt only
- it does not replace the core same-session plus full-resend rule above
- it never widens the canonical recovery-action family
- any later activation would have to reopen canon in the owning phase before docs describe it as live behavior
- the current shipped/runtime-facing contract should not teach those fields as expected live residue

## Related Contracts

- [OpenClaw continuity and send modes](openclaw-continuity-and-send-modes.md)
- [OpenClaw Gateway RPC subset](openclaw-gateway-rpc-subset.md)
- [Watchdog and recovery contract](watchdog-and-recovery-contract.md)
- [Runtime records and lifecycle](runtime-records-and-lifecycle.md)
