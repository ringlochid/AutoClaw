# Phase 0 OpenClaw Event And Watchdog Canon-Fix Review

Status: Reference

selected phase: Phase 0
current phase page: docs-internal/execution/v1/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP2, P0-WP3
summary-only: no
delegated slices: none

## Slice identity

- work package or slice: stronger OpenClaw event and watchdog canon-fix
- date: 2026-05-18

## Phase-local contract

- current phase page: `docs-internal/execution/v1/phases/phase-0-docs-contract-freeze-and-setup.md`
- implementation file lock map: `docs-internal/execution/v1/maps/file-priority-map.md`

## Scope

- reviewed plan: `../plans/phase-0-openclaw-event-watchdog-canon-fix.md`
- reviewed evidence: `../evidence/phase-0-openclaw-event-watchdog-canon-fix.md`

## Verdict

- pass/fail: pass
- summary: the stronger OpenClaw event-handling and watchdog timing contract is now locked in canon without falsely claiming the code has already landed the design. The 4A owner docs pin the raw-envelope versus normalization split, the 4B owner docs move stale-timeout anchoring away from checkpoint time, the config owner page adopts first-progress wording, and the current-contrast pages stay truthful about the shipped gap.

## Findings

- the docs now reject a guessed upstream raw run-event contract and instead freeze the AutoClaw-owned normalization layer over the generic Gateway event envelope
- the watchdog contract now treats provider progress and node semantic writes as the liveness anchors while preserving the closed trigger-family and recovery-action sets
- delivery-state field meanings and examples now align with the stronger target semantics, including `provider_signal_seen`
- the current-contrast pages now state explicitly that shipped code still records `last_provider_signal_at` from terminal `agent.wait` confirmation and still ignores provider progress in the current execution-stale anchor
- the Phase 0 docs-freeze allowlist now explicitly permits the watchdog current-contrast page in authoritative Phase 0 artifact chains

## Delegated-slice compliance

- `no subagents`
- owned-surface compliance: pass
- authoritative proof link: `../evidence/phase-0-openclaw-event-watchdog-canon-fix.md`

## Proof lanes relied on

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- `./.venv/bin/ruff check scripts/docs`
- `./.venv/bin/mypy scripts/docs`
- focused repo search over the stale wording named in the approved plan

## Stale-logic search proof

- commands or search terms: `watchdog_bootstrap_ack_timeout_seconds`, `latest visible checkpoint`, `response.delta`, `run.started`, `run.completed`, `presence`, `last_provider_signal_at`, `provider_signal_seen`
- outcome: the touched target pages now use the stronger normalized-event and provider-progress wording; the old bootstrap timeout name remains documented only as a temporary compatibility alias

## Kill-list proof

- phase kill-list source: `docs-internal/execution/v1/phases/phase-0-docs-contract-freeze-and-setup.md`
- terms checked: overlapping phase ownership and split docs authority
- outcome: satisfied; the lock remains Phase 0 canon with 4A/4B collateral owner docs only

## Docs answer-sourcing proof

- design owners relied on:
  - `scripts/docs/docs_freeze/record_rules.py`
  - `docs-internal/design/v1/architecture/openclaw-gateway-rpc-subset.md`
  - `docs-internal/design/v1/architecture/openclaw-worker-and-gateway-contract.md`
  - `docs-internal/design/v1/architecture/watchdog-and-recovery-contract.md`
  - `docs-internal/design/v1/architecture/runtime-observability-and-boundary-log.md`
  - `docs-internal/design/v1/architecture/runtime-database-and-object-contract.md`
  - `docs-internal/design/v1/how-to/install-and-onboard.md`
- current-contrast pages relied on:
  - `docs-internal/current/v1/architecture/openclaw-dispatch-and-session-contract.md`
  - `docs-internal/current/v1/architecture/watchdog-and-runtime-monitoring.md`
  - `docs-internal/current/v1/architecture/runtime-control-plane.md`
- code or tests inspected:
  - `apps/api/app/runtime/openclaw/transport.py`
  - `apps/api/app/runtime/control/dispatch/gateway_observability.py`
  - `apps/api/app/runtime/watchdog/classification.py`
  - `apps/api/tests/integration/phase4b/watchdog/test_stale_classification.py`
- canon gap or explicit `none`: none

## Phase-bounded STYLE exceptions

- none

## Reset-gate outcome

- not applicable

## Remaining exact blockers

- none
