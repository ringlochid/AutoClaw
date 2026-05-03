# Watchdog And Recovery Contract

Status: Target

## Purpose

This page freezes the lean v1 watchdog classification and controller recovery model.

## Core rule

Watchdog is conservative and controller-truth-first.

- watchdog reads controller/DB state directly as ground truth
- generated files under `_runtime/dispatch/<dispatch_id>/` are observability projections only
- watchdog is a periodic controller-side loop with deterministic classification over current truth
- watchdog classifies delivery and liveness incidents tied to internal dispatch chronology
- watchdog does not redefine assignment result truth by itself
- watchdog does not scan projections as its source of truth
- watchdog is not a node action, callback action, or public boundary family
- detailed support-state enums and projection schemas remain below the core lock

Foreground-control separation:

- start/open and abort handshakes are foreground controller operations
- watchdog is the background reconciler/escalator for stale or ambiguous cases
- watchdog must not race a live foreground handshake on the same dispatch slot
- a bounded post-boundary drain window is also foreground controller behavior, not watchdog behavior

Ownership table:

| Lifecycle slice | Primary owner |
| --- | --- |
| launch handshake and live execution | foreground controller |
| bounded drain window while `control_state = live` | foreground controller |
| abort handshake while `control_state = abort_requested` | foreground controller |
| stale or ambiguous post-deadline cases | watchdog |

## Controller read basis

When watchdog classifies a live dispatch, it rereads current dispatch, assignment/attempt, Gateway session/run state, and checkpoint truth and computes controller-observed progress time from, in order:

- the latest visible checkpoint
- the latest dispatch progress marker
- dispatch prepared and accepted timestamps

This contract uses dispatch progress marker wording only. It does not depend on ack-era terminology.

Watchdog should also read:

- `DispatchTurn.control_state`
- `DispatchTurn.control_deadline_at`
- `DispatchTurn.gateway_session_key`
- `DispatchTurn.gateway_run_id`

## Watchdog trigger families

Canonical trigger families are:

- `bootstrap_pending_callback.bootstrap_callback_timeout`
- `bootstrap_pending_callback.terminal_provider_without_first_callback`
- `execution_running.execution_stale`
- `execution_running.delivery_path_rebound`
- `execution_running.terminal_provider_without_controller_checkpoint`

Not watchdog triggers:

- ordinary dependency waits
- explicit operator pause or cancel
- child business blockers already summarized in checkpoint
- parent/root review disagreement
- missing durable output discovered by release legality

## Recovery actions

Canonical watchdog recovery actions are:

- `redispatch_same_attempt`
- `create_new_attempt`
- `escalate`

Exact meanings:

| Recovery action           | Exact meaning                                                                                                                     |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `redispatch_same_attempt` | The controller keeps the same assignment and same attempt, then opens one fresh replacement dispatch.                             |
| `create_new_attempt`      | The controller keeps the same assignment, creates a new attempt, then starts a new Gateway `sessionKey` and a new Gateway `runId`. |
| `escalate`                | The controller does not auto-redispatch and instead returns control to the higher owner or operator path.                         |

Rules:

- `redispatch_same_attempt` and `create_new_attempt` are different controller actions and must not be collapsed into vague "resume" wording
- send mode does not widen this action family
- `create_new_attempt` always uses `full_prompt`
- callback-safe v1 dispatch separation uses a fresh Gateway `sessionKey` and fresh `runId` per replacement dispatch by default
- same-attempt redispatch, if internally limited, is a controller recovery budget rather than an authored policy field
- any retained same-session continuity remains adapter-private only and must not override callback-safe dispatch separation

## Recovery decision table

| Situation                                                                                                                        | Legal automatic action    | Illegal shorthand                                                  |
| -------------------------------------------------------------------------------------------------------------------------------- | ------------------------- | ------------------------------------------------------------------ |
| The same attempt is still current and bounded work should continue                                                               | `redispatch_same_attempt` | Calling it `retry` or inventing a transport-shaped recovery family |
| The same assignment should continue, but the current attempt lineage is no longer trustworthy                                    | `create_new_attempt`      | Describing it as a same-attempt resend                             |
| Budget exhausted, ambiguity persists, multiple candidates exist, no eligible candidate exists, or safe recovery cannot be proven | `escalate`                | Hidden provider retry loop                                         |

## Abort-confirm-before-replace

Canonical abort control uses Gateway WS RPC surfaces:

- `agent` opens the run
- `agent.wait` observes terminal completion
- `sessions.abort` is the canonical machine abort surface

Before replacement work can start on one execution slot:

1. call `sessions.abort`
2. mark local dispatch `abort_requested`
3. wait for terminal confirmation
4. if confirmed, mark the old dispatch non-current and terminal
5. only then open the replacement run

If terminal confirmation does not arrive before deadline:

- mark the slot `ambiguous`
- do not open a replacement run on that slot
- escalate/operator review

Drain-window rule:

- if same-session continuity preservation is still desired, the controller may wait through a bounded drain window before aborting
- default drain timeout is `30` seconds through target runtime config
- Gateway lifecycle terminal events and `agent.wait` results should short-circuit that window immediately
- watchdog only becomes relevant after the drain window is stale, abort is requested, or the slot is already `ambiguous`
- the slot remains replacement-blocked while still `live`, including that bounded drain-window subphase

Ownership rule:

- while `DispatchTurn.control_state` is `launching` or `abort_requested`, foreground control owns the handshake and watchdog should not issue competing recovery
- watchdog may intervene only when that state is stale past deadline or already `ambiguous`

Timeout and reconciliation rule:

- use event-driven confirmation first and deadlines second
- treat Gateway lifecycle terminal events as the primary fast signal
- use `agent.wait` as the confirmatory read before replacement or escalation
- reconcile controller truth before any retry or replacement decision
- do not use blind exponential resend loops for launch or abort control

## What watchdog may and may not do

Watchdog may:

- classify a real delivery or liveness problem
- choose exactly one controller recovery action
- commit recovery dispatch truth only through ordinary controller write paths
- open a new dispatch only after older dispatch truth is no longer current
- act only after the slot is no longer live, no longer inside an open drain window, or no longer abort-pending, unless it is already stale or `ambiguous`

Watchdog must not:

- interpret ordinary business blockers as transport stalls
- silently publish `green`, `retry`, or `blocked`
- invent a separate gate-era decision surface
- replace checkpoint as the durable handoff surface
- treat provider terminal success as proof that the assignment succeeded
- expose `dispatch_id` as a required node-facing or public operator input

## Escalation rule

`escalate` is required when:

- same-attempt redispatch is illegal
- new-attempt retry is illegal or the relevant internal limit is exhausted
- multiple watchdog-blocked candidates exist
- no eligible candidate exists
- same-session binding is missing, rebound, expired, or ambiguous and safe recovery cannot be proven
- structural or currentness basis is stale
- automatic recovery would rewrite or guess over ambiguous truth

After escalation:

- no automatic dispatch commit happens
- no hidden provider retry loop runs
- later handling proceeds through ordinary higher-owner or observability and operator surfaces
- if later agents must understand the incident durably, checkpoint or another surfaced durable file must summarize it

## Redispatch sequencing rule

Before watchdog-triggered redispatch:

1. reread authoritative dispatch, attempt, session, run, and currentness truth
2. require the old dispatch to already be `fenced` or otherwise terminal by stronger committed truth
3. commit any required supersession/readback truth
4. only then mint the new dispatch
5. only then allow the next live agent run

Same-attempt recovery therefore means same assignment plus same attempt under a fresh replacement dispatch. It does not mean continuing the stopped run, and it does not make `sessionKey` reuse part of the core semantic definition.

## Support-state demotion

This page intentionally does **not** freeze the full watchdog, delivery, or continuity support-state machine as core v1 truth.

The core lock owns only:

- trigger families
- recovery actions
- abort/replace sequencing
- ambiguity and escalation rules
- the single-live-run invariant

Detailed support enums, support projections, and transport-specific continuity catalogs may remain in support or adapter docs.

## Suggested target runtime config

The canonical target runtime config for watchdog/drain behavior is:

```toml
[runtime]
dispatch_drain_timeout_seconds = 30
watchdog_enabled = true
watchdog_interval_seconds = 15
watchdog_stale_after_seconds = 300
watchdog_execution_stale_after_seconds = 300
watchdog_bootstrap_ack_timeout_seconds = 120
watchdog_execution_hint_extension_seconds = 300
watchdog_bootstrap_hint_extension_seconds = 120
watchdog_auto_recover = true
watchdog_max_flows_per_tick = 50
watchdog_max_auto_recoveries_per_tick = 10
watchdog_bootstrap_max_auto_retries = 2
watchdog_max_auto_wakes = 1
```

Rules:

- these are runtime/controller knobs, not authored workflow grammar
- same-attempt redispatch and new-attempt retry legality still come from controller truth, not config alone
- observability surfaces may inspect the resulting watchdog state, but they do not trigger recovery

## Exact watchdog projection

`watchdog-state.json` uses this exact readback shape:

```json
{
  "dispatch_id": "dispatch.parent.01",
  "attempt_id": "attempt.parent.01",
  "assignment_key": "parent.assign-01",
  "node_key": "implementation_subtree",
  "watchdog_state": "clear",
  "current_watchdog_kind": null,
  "current_watchdog_reason": null,
  "recovery_action": null,
  "recovery_reason": null,
  "recovery_dispatch_id": null,
  "previous_dispatch_id": null,
  "superseded_by_dispatch_id": null,
  "classified_at": "2026-05-03T10:00:15Z",
  "updated_at": "2026-05-03T10:00:15Z"
}
```

That file remains an observability projection over controller truth. It is not the watchdog's source of truth.

Operator/public investigation should start from `task_id`; runtime/support tooling may resolve internal dispatch chronology and read the matching watchdog projection as needed.

## Related contracts

- [Runtime monitoring and watchdog automation](runtime-monitoring-and-watchdog-automation.md)
- [Runtime observability and boundary log](runtime-observability-and-boundary-log.md)
- [OpenClaw session lifecycle](openclaw-session-lifecycle.md)
- [OpenClaw continuity and send modes](openclaw-continuity-and-send-modes.md)
