# Phase 0 OpenClaw Event, RPC, And Watchdog Target-Lock Plan

Status: Reference

selected phase: Phase 0
current phase page: docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP2, P0-WP3
summary-only: no
delegated slices: none

## Purpose

Lock the OpenClaw event, RPC, and watchdog target design in canon before any new code work resumes.

This slice exists to:

- repair broken execution-authority links after the reset
- freeze the OpenClaw-side run ordering and event-correlation contract in the Phase 4A owner docs
- freeze the preferred dispatch-scoped runtime transport architecture in the Phase 4A owner docs
- freeze committed-ingest watchdog semantics in the Phase 4B owner docs
- keep current-behavior contrast pages truthful about the shipped buffered baseline

## Owned surfaces

- `docs/redesign/architecture/openclaw-gateway-rpc-subset.md`
- `docs/redesign/architecture/openclaw-worker-and-gateway-contract.md`
- `docs/redesign/architecture/openclaw-session-lifecycle.md`
- `docs/redesign/architecture/openclaw-continuity-and-send-modes.md`
- `docs/redesign/architecture/watchdog-and-recovery-contract.md`
- `docs/redesign/architecture/runtime-observability-and-boundary-log.md`
- `docs/redesign/architecture/runtime-database-and-object-contract.md`
- `docs/current/architecture/openclaw-dispatch-and-session-contract.md`
- `docs/current/architecture/watchdog-and-runtime-monitoring.md`
- `docs/current/architecture/runtime-control-plane.md`
- `docs/execution/plans/phase-0-openclaw-event-rpc-watchdog-target-lock.md`
- `docs/execution/evidence/phase-0-openclaw-event-rpc-watchdog-target-lock.md`
- `docs/execution/reviews/phase-0-openclaw-event-rpc-watchdog-target-lock.md`

## Allowed collateral surfaces

- historical execution-review artifacts under `docs/execution/reviews/` when broken `## Authoritative replacements` links must be repaired to truthful live targets

## Ordered work

1. Repair the broken historical Phase 4B review replacement links and keep those review artifacts historical-only.
2. Lock the OpenClaw-side contract in the 4A owner docs:
   - accepted `agent` response with authoritative `runId` first for the launched run
   - unrelated broadcasts may still interleave on the same socket
   - `agent.wait` is terminal confirmation only
   - `sessions.abort` may emit events before its RPC response
   - `runId` is the live-run discriminator
   - `sessionKey` is routing context and an additional guard only
3. Lock the preferred worker-lane transport architecture:
   - dispatch-scoped runtime RPC handle
   - one live dispatch owns one reader and one correlated ingest queue/worker
   - request-local `observed_events` are debug/compatibility material only
   - no process-global fan-out registry as target canon
   - no inline DB ingest inside the transport reader
4. Lock the 4B watchdog/support-state target:
   - watchdog remains DB-backed
   - provider progress becomes watchdog-visible only after controller-owned ingest commit
   - stale anchoring uses accepted/rendered time, provider progress, and node semantic writes
   - checkpoint remains semantic truth only
   - `tool_event` is persisted observability and not a liveness anchor
5. Patch the current-contrast pages so they state explicitly that shipped code is still on the buffered `agent` / `agent.wait` baseline.

## Validation

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- exact repo searches for:
  - `runId`
  - `sessionKey`
  - `agent.wait`
  - `sessions.abort`
  - `response.delta`
  - `presence`
  - `last_provider_signal_at`
  - `provider_signal_seen`
  - broken `## Authoritative replacements` links
- `ruff check scripts/docs` and `mypy scripts/docs` only if `scripts/docs/*` changes

## Stop conditions

- stop if the truthful fix requires app-code edits
- stop if the truthful fix requires widening beyond Phase 0 plus allowed collateral docs surfaces
- stop if the OpenClaw-side research can no longer support the pinned runId-first launched-run ordering
