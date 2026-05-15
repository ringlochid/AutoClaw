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

The controller regenerates the canonical prompt on every dispatch. Canonical v1 and the shipped Phase 4A runtime mint a fresh Gateway `sessionKey` and a fresh `runId` for each dispatch. The `same_session_continue` transport shape remains reserved adapter plumbing only and does not describe a live controller path today.

## Source Of Truth Split

- Controller/DB runtime state remains the source of execution truth.
- Gateway `sessionKey` is the adapter-private transcript/context lane for one dispatch in the shipped runtime.
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

- `sessionKey` is the primary private binding key for callback authorization
- `runId` is the live-run correlation key for `agent.wait` and `sessions.abort`
- callback authority must be resolved server-side from trusted session context
- prompt-visible context must not carry callback tokens, auth-file paths, or caller-visible dispatch-binding secrets

## Identity Split

- `dispatch_id` = one AutoClaw controller dispatch path
- `attempt_id` = one current execution attempt on one assignment
- `assignment_key` = one current mission contract
- `sessionKey` = one adapter-private Gateway context lane
- `runId` = one live Gateway execution inside that session
- provider `session_key` or `previous_response_id` = adapter-native transport detail only

Most important distinctions:

- changing `runId` does not automatically mean new attempt
- changing `attempt_id` always means new attempt lineage
- reusing `sessionKey` means history/context reuse only
- reusing the same live `runId` is not part of the canonical v1 architecture

## Gateway Session And Run Rule

Canonical session/run mapping in v1 is:

- same node + same assignment + same attempt + later redispatch:
  - fresh `sessionKey`
  - new `runId`
- new attempt:
  - new `sessionKey`
  - new `runId`
- fresh child assignment:
  - new `sessionKey`
  - new `runId`

This keeps optional durable internal context reuse separate from live execution reuse and keeps one replacement dispatch tied to one trusted execution context.

## Same-Attempt Recovery

Same-attempt recovery keeps the same semantic execution lineage:

- `attempt_id`
- `assignment_key`

Controller action remains:

- `redispatch_same_attempt`

Canonical same-attempt dispatch rule:

- mint a fresh Gateway `sessionKey`
- create a fresh Gateway `runId`
- rebuild the prompt from current authoritative runtime truth
- keep any continuity-sideband bookkeeping adapter-private and non-canonical

Same-attempt recovery must not be described as retry lineage.

Additional rules:

- the prior dispatch must already be closed or superseded before a new same-attempt run is created
- the prior run must already be terminal or abort-confirmed before the replacement run is allowed

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
   - `redispatch_same_attempt` with a fresh `sessionKey` and a new `runId`
   - `create_new_attempt` with a new `sessionKey` and a new `runId`
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

The prompt/transport model still reserves provider-native continuity fields such as `same_session_continue` and `previous_response_id`, but the shipped Phase 4A runtime does not emit that send mode.

Keep that reserved shape below the core lock:

- it is adapter-private
- it does not change the core replacement-dispatch rule above
- it never widens the canonical recovery-action family
- any later activation must reopen canon in the owning phase before docs describe it as live behavior

## Related Contracts

- [OpenClaw continuity and send modes](openclaw-continuity-and-send-modes.md)
- [OpenClaw Gateway RPC subset](openclaw-gateway-rpc-subset.md)
- [Watchdog and recovery contract](watchdog-and-recovery-contract.md)
- [Runtime records and lifecycle](runtime-records-and-lifecycle.md)
