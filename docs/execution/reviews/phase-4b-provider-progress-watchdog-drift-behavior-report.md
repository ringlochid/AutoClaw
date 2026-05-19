# Phase 4B Provider-Progress Watchdog Drift Behavior Report

Status: Reference

selected phase: Phase 4B
current phase page: docs/execution/phases/phase-4b-watchdog-operator-plugin-and-support-state.md
selected work packages: P4B-WP1
summary-only: yes
delegated slices: none

## Authoritative replacements

- `../reviews/phase-0-openclaw-event-rpc-watchdog-target-lock.md`

## Historical status

This artifact remains a useful historical drift review, but the authoritative docs-first closeout for the target-lock step now lives on the Phase 0 OpenClaw event/RPC/watchdog target-lock chain.

## Slice identity

- work package or slice: review-only drift analysis of provider-progress buffering vs watchdog-visible liveness anchoring
- date: 2026-05-19

## Phase-local contract

- current phase page: `docs/execution/phases/phase-4b-watchdog-operator-plugin-and-support-state.md`
- implementation file lock map: `docs/execution/maps/file-priority-map.md`

## Scope

- reviewed plan: `../plans/phase-4b-provider-progress-watchdog-refactor.md`
- reviewed evidence: `../evidence/phase-4b-provider-progress-watchdog-drift-behavior-report.md`

## Verdict

- pass/fail: fail against the immediate-anchor expectation; pass for the narrower current buffered controller-write model
- summary: current code advances `last_provider_signal_at` only after buffered provider events from `agent` or `agent.wait` are normalized and committed. The watchdog rereads persisted delivery-state and provider-event rows only. That creates a bounded but real lag between raw correlated provider progress and watchdog-visible liveness.

## Findings

- High: watchdog liveness anchoring is DB-backed, not transport-buffer-backed. `_load_watchdog_context()` loads `DispatchDeliveryStateModel` and `ProviderEventRecordModel` rows in `apps/api/app/runtime/watchdog/service.py:199-217`, and `_progress_anchor()` uses `delivery_state.last_provider_signal_at` in `apps/api/app/runtime/watchdog/classification.py:285-292`. The watchdog cannot observe uncommitted `observed_events`.
- High: the adapter buffers raw Gateway event frames until the matching response envelope arrives. `receive_response()` appends `OpenClawObservedEvent` values until it sees the expected response `id` in `apps/api/app/runtime/openclaw/transport.py:35-70`. `launch_run()` and `wait_for_run()` then return those buffered events as batch payloads in `apps/api/app/runtime/openclaw/adapter.py:77-125`. This is the primary mechanical source of the drift.
- High: controller writes occur only in the acceptance or reconcile path after the batch returns. In the reviewed draft branch, `record_dispatch_provider_acceptance()` consumed `launch_result.observed_events`, the steady-state path persisted `wait_result.observed_events` only after `agent.wait` returned, and `record_gateway_provider_progress()` advanced `last_provider_signal_at` inside that batch loop. The field therefore reflected the latest correlated event in the processed batch, not immediate raw-frame arrival.
- Medium: the docs mostly match the controller-owned buffered model and are not the main cause of the drift. The current contract says provider hints include later normalized provider-event history and that transport outcomes remain such until a controller-owned write records them in `docs/current/architecture/openclaw-dispatch-and-session-contract.md:154-194`. The redesign contract also talks about unrelated buffered events before the final `agent.wait` response in `docs/redesign/architecture/openclaw-worker-and-gateway-contract.md:152-156`.
- Medium: the docs under-specify latency semantics and can be misread as immediate per-event anchoring. `docs/current/architecture/watchdog-and-runtime-monitoring.md:59-61` says provider-signal movement extends the stale deadline and that `last_provider_signal_at` is a primary anchor, but it does not state that current movement becomes watchdog-visible only after buffered `agent` or `agent.wait` events are normalized and committed. This is an expectation gap, not a direct contradiction.
- Low: the watchdog implementation itself is not the root defect if controller-owned DB truth is the intended model. The watchdog reread basis in `docs/redesign/architecture/watchdog-and-recovery-contract.md:38-56` is consistent with the code. Moving the watchdog to ephemeral adapter buffers would bypass controller-owned truth instead of fixing ingest latency.

## Root-Cause Attribution

- primary cause: current adapter and dispatch-reconcile batching architecture
- secondary cause: docs ambiguity about when provider-signal movement becomes watchdog-visible
- not primary cause: watchdog classification read logic, which is consistent with controller-owned persisted truth
- not primary cause: `last_provider_signal_at` field meaning, which remains consistently documented as normalized provider progress-or-terminal time in `docs/redesign/architecture/runtime-observability-and-boundary-log.md:82-88`

## Suggested Corrections

- preferred implementation fix: introduce a controller-owned event-ingest path that normalizes and persists correlated provider progress as soon as the transport receives it, then commits and wakes the watchdog. Keep the watchdog DB-backed.
- minimum-risk interim fix: reduce `agent.wait` polling latency only if a larger ingest refactor is not yet viable. This shrinks the drift but does not remove it.
- required docs fix: update the current and redesign OpenClaw and watchdog pages to state explicitly that current provider-progress anchoring becomes watchdog-visible when buffered `observed_events` from `agent` or `agent.wait` are normalized and committed, not on raw WebSocket frame receipt.
- required test fix: add one regression test that proves the current batch-visibility boundary and one future target test for immediate anchor movement if the ingest path is refactored.
- review guardrail: do not move the watchdog to ephemeral adapter memory. If the product requirement is immediate anchoring, the fix belongs at the transport-to-controller write seam.

## Delegated-slice compliance

- `no subagents` or delegated-slice summary: `no subagents`
- owned-surface compliance: pass; the report stayed inside execution-artifact docs and inspected only Phase 4B-owned plus allowed-collateral surfaces
- review-only compliance: pass; this slice did not edit runtime code or tests
- wave integration proof: not applicable; single review-only slice
- authoritative proof link: `../evidence/phase-4b-provider-progress-watchdog-drift-behavior-report.md`

## Proof lanes relied on

- repo search for `record_gateway_provider_progress`, `last_provider_signal_at`, `record_dispatch_provider_acceptance`, `record_gateway_wait_terminal`, and watchdog context loads
- direct code inspection of the OpenClaw transport buffering path, dispatch reconcile path, provider-progress persistence path, and watchdog service/classification path
- direct doc inspection of current and redesign provider-progress, watchdog, and observability contracts
- attempted repo-wide docs validators, with failures attributable to pre-existing worktree findings outside this new report pair

## Stale-logic search proof

- commands or search terms: `record_gateway_provider_progress`, `last_provider_signal_at =`, `record_dispatch_provider_acceptance`, `observed_events`, `provider progress`, `watchdog`
- outcome: the only live mid-run write path for `last_provider_signal_at` is the batched provider-progress normalization flow plus the terminal and cleanup fallback writes already documented in the evidence artifact

## Kill-list proof

- phase kill-list source: `docs/execution/phases/phase-4b-watchdog-operator-plugin-and-support-state.md`
- terms checked: raw transport state treated as controller truth, mixed worker/operator assumptions, support-state readbacks inferred from prose alone
- outcome: satisfied; the drift comes from delayed controller truth materialization, not from treating raw transport buffers as controller truth

## Docs answer-sourcing proof

- redesign owners relied on: `docs/redesign/architecture/watchdog-and-recovery-contract.md`, `docs/redesign/architecture/runtime-observability-and-boundary-log.md`, `docs/redesign/architecture/runtime-database-and-object-contract.md`, `docs/redesign/architecture/openclaw-worker-and-gateway-contract.md`
- supporting redesign reads or appendix owners relied on: `docs/redesign/architecture/runtime-monitoring-and-watchdog-automation.md`, `docs/redesign/architecture/watchdog-and-provider-recovery.md`, `docs/redesign/architecture/provider-worker-and-operator-boundary.md`, `docs/redesign/decisions/ADR-0004-openclaw-adapter-normalization-and-worker-transport-boundary.md`
- current-contrast pages relied on: `docs/current/architecture/watchdog-and-runtime-monitoring.md`, `docs/current/architecture/openclaw-dispatch-and-session-contract.md`, `docs/current/architecture/runtime-control-plane.md`
- code or tests inspected: `apps/api/app/runtime/openclaw/transport.py`, `apps/api/app/runtime/openclaw/adapter.py`, the then-live draft progress helper under `apps/api/app/runtime/control/dispatch/`, `apps/api/app/runtime/effects/dispatch_reconcile.py`, `apps/api/app/runtime/watchdog/service.py`, `apps/api/app/runtime/watchdog/classification.py`
- canon gap or explicit `none`: none; the gap is timing specificity, not missing ownership docs

## Phase-bounded STYLE exceptions

- `none`

## Reset-gate outcome

- not applicable; this is a review-only drift report with no runtime-code or schema change landed in this slice

## Remaining exact blockers

- the current transport-to-controller seam has no immediate controller-owned persist path between raw Gateway frame receipt and `agent.wait` batch completion
- the current and redesign docs do not yet freeze the exact latency semantics for when provider progress becomes watchdog-visible
- the repo-wide docs validator lane is currently blocked by pre-existing Phase 4B draft-artifact inventory issues and unrelated style-audit findings in the dirty worktree

## Cross-links

- aggregate historical summary, if any: `../reviews/phase-4b-provider-progress-watchdog-refactor.md`
- companion exceptions page, if any: none
