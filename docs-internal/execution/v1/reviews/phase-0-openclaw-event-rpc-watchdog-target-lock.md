# Phase 0 OpenClaw Event, RPC, And Watchdog Target-Lock Review

Status: Reference

selected phase: Phase 0
current phase page: docs-internal/execution/v1/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP2, P0-WP3
summary-only: no
delegated slices: none

## Slice identity

- work package or slice: OpenClaw event, RPC, and watchdog target-lock canon fix
- date: 2026-05-19

## Phase-local contract

- current phase page: `docs-internal/execution/v1/phases/phase-0-docs-contract-freeze-and-setup.md`
- implementation file lock map: `docs-internal/execution/v1/maps/file-priority-map.md`

## Scope

- reviewed plan: `../plans/phase-0-openclaw-event-rpc-watchdog-target-lock.md`
- reviewed evidence: `../evidence/phase-0-openclaw-event-rpc-watchdog-target-lock.md`

## Verdict

- pass/fail: pass
- summary: canon now locks the researched OpenClaw run-ordering and event-correlation rules, the preferred dispatch-scoped worker-lane transport model, and the committed-ingest watchdog target while keeping current-behavior docs truthful about the still-buffered shipped baseline.

## Findings

- the Phase 4A owner docs now pin accepted `runId` first for the launched run, while still allowing unrelated broadcasts to interleave on the same socket
- the target transport architecture is now explicitly dispatch-scoped rather than a process-global fan-out registry
- the Phase 4B owner docs now state that watchdog truth begins at controller-owned ingest commit, not at raw socket receipt
- the current-contrast pages now state explicitly that shipped code still buffers provider events inside `agent` / `agent.wait`
- the broken historical 4B review replacement links now point at a real authoritative Phase 0 review artifact

## Delegated-slice compliance

- `no subagents`
- owned-surface compliance: pass
- authoritative proof link: `../evidence/phase-0-openclaw-event-rpc-watchdog-target-lock.md`

## Proof lanes relied on

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- focused repo search for the event, RPC, watchdog, and replacement-link terms named in the approved plan

## Stale-logic search proof

- commands or search terms: `phase-0-gateway-rpc-event-ingest-truth-repair`, `runId`, `sessionKey`, `agent.wait`, `sessions.abort`, `response.delta`, `presence`, `last_provider_signal_at`, `provider_signal_seen`
- outcome: broken replacement links were removed, and the touched target/current pages now use the new run-ordering and committed-ingest wording

## Kill-list proof

- phase kill-list source: `docs-internal/execution/v1/phases/phase-0-docs-contract-freeze-and-setup.md`
- terms checked: split docs authority and overlapping phase ownership
- outcome: satisfied; the slice remains Phase 0 canon with Phase 4A/4B owner-doc collateral only

## Docs answer-sourcing proof

- design owners relied on:
  - `docs-internal/design/v1/architecture/openclaw-gateway-rpc-subset.md`
  - `docs-internal/design/v1/architecture/openclaw-worker-and-gateway-contract.md`
  - `docs-internal/design/v1/architecture/openclaw-session-lifecycle.md`
  - `docs-internal/design/v1/architecture/openclaw-continuity-and-send-modes.md`
  - `docs-internal/design/v1/architecture/watchdog-and-recovery-contract.md`
  - `docs-internal/design/v1/architecture/runtime-observability-and-boundary-log.md`
  - `docs-internal/design/v1/architecture/runtime-database-and-object-contract.md`
- current-contrast pages relied on:
  - `docs-internal/current/v1/architecture/openclaw-dispatch-and-session-contract.md`
  - `docs-internal/current/v1/architecture/watchdog-and-runtime-monitoring.md`
  - `docs-internal/current/v1/architecture/runtime-control-plane.md`
- code or tests inspected:
  - `apps/api/app/runtime/openclaw/adapter.py`
  - `apps/api/app/runtime/openclaw/transport.py`
  - `apps/api/app/runtime/effects/dispatch_reconcile.py`
  - `apps/api/app/runtime/control/dispatch/authority.py`
  - `tmp/openclaw-gateway-contract-report-2026-05-19.md`
- canon gap or explicit `none`: none

## Phase-bounded STYLE exceptions

- none

## Reset-gate outcome

- not applicable

## Remaining exact blockers

- none
