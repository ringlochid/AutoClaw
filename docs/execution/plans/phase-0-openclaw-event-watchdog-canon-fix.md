# Phase 0 OpenClaw Event And Watchdog Canon-Fix Plan

Status: Reference

selected phase: Phase 0
current phase page: docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP2, P0-WP3
summary-only: no
delegated slices: none

## Purpose

Lock the stronger OpenClaw event-handling and watchdog contract in canon without claiming the follow-on implementation has already landed.

This slice exists to:

- freeze the OpenClaw raw-envelope versus AutoClaw-normalization split in the 4A owner docs
- freeze provider-progress-based watchdog timing in the 4B owner docs
- keep current-contrast docs truthful until code follow-on lands
- update the canonical runtime-config owner page so the bootstrap timeout wording matches the stronger design

## Owned surfaces

- `docs/redesign/architecture/openclaw-gateway-rpc-subset.md`
- `docs/redesign/architecture/openclaw-worker-and-gateway-contract.md`
- `docs/redesign/architecture/watchdog-and-recovery-contract.md`
- `docs/redesign/architecture/runtime-observability-and-boundary-log.md`
- `docs/redesign/architecture/runtime-database-and-object-contract.md`
- `docs/redesign/how-to/install-and-onboard.md`
- `docs/current/architecture/openclaw-dispatch-and-session-contract.md`
- `docs/current/architecture/watchdog-and-runtime-monitoring.md`
- `docs/current/architecture/runtime-control-plane.md`
- `scripts/docs/docs_freeze/record_rules.py`
- `docs/execution/plans/phase-0-openclaw-event-watchdog-canon-fix.md`

## Ordered work

1. Patch the 4A OpenClaw docs so they pin the generic Gateway event envelope and the AutoClaw-owned normalization layer rather than inventing a new upstream raw run-event contract.
2. Patch the 4B watchdog and observability docs so stale-timeout anchoring uses acceptance time, provider progress, and node semantic writes instead of checkpoint time.
3. Patch delivery-state field meanings so `last_provider_signal_at` and `last_provider_event_kind` describe normalized provider progress-or-terminal signals, and `last_controller_progress_at` is documented as a transitional node semantic write timestamp.
4. Patch the canonical config owner page so the target bootstrap timeout name is `watchdog_bootstrap_first_progress_timeout_seconds` and the old `watchdog_bootstrap_ack_timeout_seconds` name is documented only as a compatibility alias.
5. Patch the named current-contrast pages so they explicitly state that current code still uses the older provider-signal and watchdog semantics.
6. Record this docs-only canon-fix through one Phase 0 plan/evidence/review chain.

## Validation

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- `./.venv/bin/ruff check scripts/docs`
- `./.venv/bin/mypy scripts/docs`
- exact repo searches over the stale terms named in the approved plan
- manual consistency review across the touched 4A, 4B, current-contrast, and config-owner pages

## Stop conditions

- stop if the truthful fix requires app-code edits
- stop if the truthful fix requires widening into non-Phase-0-owned execution surfaces
- stop if the stronger design cannot be locked without changing the frozen watchdog trigger-family or recovery-action sets
