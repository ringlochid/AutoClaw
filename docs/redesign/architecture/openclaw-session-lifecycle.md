# OpenClaw Session Lifecycle

Status: Target

## Purpose

This page freezes the v1 OpenClaw Gateway session and run lifecycle, plus the same-attempt versus new-attempt recovery split.

## Need To Lock

1. Controller-owned prompt regeneration.
2. Gateway session versus Gateway run identity split.
3. Same-attempt session reuse without live-run reuse.
4. New-attempt creation versus same-attempt redispatch.
5. Optional provider-native continuity demotion.

## Core Rule

The controller regenerates the canonical prompt on every dispatch. Durable internal context reuse means reusing the same Gateway `sessionKey`. It does not mean continuing the same live Gateway `runId`.

## Source Of Truth Split

- Controller/DB runtime state remains the source of execution truth.
- Gateway `sessionKey` is the durable internal transcript/context lane.
- Gateway `runId` is one live execution inside that session.
- Generated files such as `continuity-state.json` and `delivery-state.json` are projections of controller-owned support truth, not the authority.

## Identity Split

- `dispatch_id` = one AutoClaw controller dispatch path
- `attempt_id` = one current execution attempt on one assignment
- `assignment_key` = one current mission contract
- `sessionKey` = one durable Gateway context lane
- `runId` = one live Gateway execution inside that session
- provider `session_key` or `previous_response_id` = optional adapter-native transport detail only

Most important distinctions:

- changing `runId` does not automatically mean new attempt
- changing `attempt_id` always means new attempt lineage
- reusing `sessionKey` means history/context reuse only
- reusing the same live `runId` is not part of the canonical v1 architecture

## Gateway Session And Run Rule

Canonical session/run reuse in v1 is:

- same node + same assignment + same attempt + later redispatch:
  - fresh `sessionKey`
  - new `runId`
- new attempt:
  - new `sessionKey`
  - new `runId`
- fresh child assignment:
  - new `sessionKey`
  - new `runId`

This keeps durable internal context reuse separate from live execution reuse.

## Same-Attempt Recovery

Same-attempt recovery keeps the same semantic execution lineage:

- `attempt_id`
- `assignment_key`

Controller action remains:

- `redispatch_same_attempt`

Canonical same-attempt dispatch rule:

- mint a fresh Gateway `sessionKey` by default
- create a fresh Gateway `runId`
- rebuild the prompt from current authoritative runtime truth
- if implementation retains same-session continuity, that remains adapter-private and non-canonical

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

- when same-session parent/root continuity is still desirable, the controller should first enter a bounded drain window instead of aborting immediately
- that drain window is represented by `control_state = live` plus `control_deadline_at`; it is not a second persisted control-state enum in this lock
- default drain timeout is `30` seconds
- the controller should listen for Gateway lifecycle end/error for that exact `runId` and may also call `agent.wait`
- either confirmation source ends the drain window immediately
- the controller should not blindly sleep the whole window when terminal confirmation already arrived
- only if the drain window expires without terminal confirmation should the controller escalate to abort or ambiguity handling

Suggested target config:

```toml
[runtime]
dispatch_drain_timeout_seconds = 30
```

There is no `parent_gate` resume path in this lifecycle, and there is no canonical "resume the stopped run" path in v1.

## Optional Provider Continuity Detail

If implementation retains provider-native transport reuse such as `same_session_continue`, keep it below the core lock:

- it is adapter-private
- it does not change the core replacement-dispatch rule above
- it never widens the canonical recovery-action family

## Related Contracts

- [OpenClaw continuity and send modes](openclaw-continuity-and-send-modes.md)
- [Watchdog and recovery contract](watchdog-and-recovery-contract.md)
- [Runtime records and lifecycle](runtime-records-and-lifecycle.md)
