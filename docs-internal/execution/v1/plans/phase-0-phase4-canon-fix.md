# Phase 0 Phase 4 Canon-Fix Plan

Status: Reference

selected phase: Phase 0
current phase page: docs-internal/execution/v1/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP2, P0-WP3
summary-only: no
delegated slices: listed
slice id: phase0-phase4-canon-seam-edit
slice type: edit
owned surfaces: docs-internal/execution/v1/phases/phase-4a-openclaw-gateway-session-and-continuity.md, docs-internal/execution/v1/phases/phase-4b-watchdog-operator-plugin-and-support-state.md, docs-internal/execution/v1/maps/file-priority-map.md, docs-internal/execution/v1/plans/phase-0-phase4-canon-fix.md
touched surfaces: docs-internal/execution/v1/phases/phase-4a-openclaw-gateway-session-and-continuity.md, docs-internal/execution/v1/phases/phase-4b-watchdog-operator-plugin-and-support-state.md, docs-internal/execution/v1/maps/file-priority-map.md, docs-internal/execution/v1/plans/phase-0-phase4-canon-fix.md
slice id: phase0-phase4-canon-review
slice type: review-only
owned surfaces: docs-internal/execution/v1/phases/phase-4a-openclaw-gateway-session-and-continuity.md, docs-internal/execution/v1/phases/phase-4b-watchdog-operator-plugin-and-support-state.md, docs-internal/execution/v1/maps/file-priority-map.md, docs-internal/execution/v1/plans/phase-0-phase4-canon-fix.md, docs-internal/execution/v1/evidence/phase-0-phase4-canon-fix.md, docs-internal/execution/v1/reviews/phase-0-phase4-canon-fix.md
touched surfaces: none

## Purpose

Legalize the kept Phase 4 execution/doc seam without widening into app-code or design-owner rewrites.

This slice exists to:

- make the Phase 4A versus Phase 4B execution ownership split explicit in the execution pack
- keep the already-in-flight config, startup, and repo-local wrapper collateral legal under the file-lock map
- make the Phase 4 closeout boundary truthful: two phase-scoped closure chains, no blended Phase 4 closure record

## Owned surfaces

- `docs-internal/execution/v1/phases/phase-4a-openclaw-gateway-session-and-continuity.md`
- `docs-internal/execution/v1/phases/phase-4b-watchdog-operator-plugin-and-support-state.md`
- `docs-internal/execution/v1/maps/file-priority-map.md`
- `docs-internal/execution/v1/plans/phase-0-phase4-canon-fix.md`

## Delegated slice briefs

### phase0-phase4-canon-seam-edit

- slice type: `edit`
- owned surfaces:
  - `docs-internal/execution/v1/phases/phase-4a-openclaw-gateway-session-and-continuity.md`
  - `docs-internal/execution/v1/phases/phase-4b-watchdog-operator-plugin-and-support-state.md`
  - `docs-internal/execution/v1/maps/file-priority-map.md`
  - `docs-internal/execution/v1/plans/phase-0-phase4-canon-fix.md`
- do not edit:
  - app code under `apps/**`
  - `docs-internal/execution/v1/evidence/**`
  - `docs-internal/execution/v1/reviews/**`
  - `docs-internal/design/v1/**`
- required reads:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs-internal/execution/v1/README.md`
  - `docs-internal/execution/v1/phases/overview.md`
  - `docs-internal/execution/v1/phases/phase-0-docs-contract-freeze-and-setup.md`
  - `docs-internal/execution/v1/maps/file-priority-map.md`
  - `docs-internal/execution/v1/maps/design-code-landing-map.md`
  - `docs-internal/archive/execution/plans/phase-4a-openclaw-gateway-session-and-continuity-implementation.md`
  - `docs-internal/archive/execution/plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md`
  - `tmp/PLAN_FIX_CLOSE_P4.md`
  - `tmp/findings.5.14.2.md`
- required tests/validators:
  - `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- dependencies:
  - none
- expected outputs:
  - corrected Phase 4 ownership wording
  - corrected lock-map wording for the canon-fix seam
  - authoritative Phase 0 plan artifact for this seam
- evidence to return:
  - changed file list
  - command output for `docs_freeze`
- parent-owned decisions:
  - whether the seam is sufficient to proceed into later phase execution before the final independent review wave
- stop conditions:
  - stop if the fix requires app-code edits
  - stop if the fix requires design-owner doc rewrites under `docs-internal/design/v1/**`
  - stop if the truthful fix would require ownership outside the Phase 0 execution-canon surfaces

### phase0-phase4-canon-review

- slice type: `review-only`
- owned surfaces:
  - the owned Phase 0 seam surfaces above
  - `docs-internal/execution/v1/evidence/phase-0-phase4-canon-fix.md`
  - `docs-internal/execution/v1/reviews/phase-0-phase4-canon-fix.md`
- do not edit repo-tracked files
- required reads:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs-internal/execution/v1/README.md`
  - `docs-internal/execution/v1/phases/phase-0-docs-contract-freeze-and-setup.md`
  - `docs-internal/execution/v1/maps/file-priority-map.md`
  - `docs-internal/execution/v1/maps/design-code-landing-map.md`
  - `tmp/PLAN_FIX_CLOSE_P4.md`
  - `tmp/findings.5.14.2.md`
- required tests/validators:
  - inspect the docs-freeze result and repo diff only; no new broad validators
- dependencies:
  - `phase0-phase4-canon-seam-edit`
- expected outputs:
  - independent findings and verdict
  - draft review artifact body for the matching review file
- evidence to return:
  - findings with exact file references
  - draft review artifact content
- parent-owned decisions:
  - whether to transcribe the returned draft directly or hold it as degraded until a later review wave
- stop conditions:
  - stop if proving a finding requires app-code or design-owner edits

## Ordered work

1. Patch Phase 4A wording so it owns gateway/session/continuity plus dispatch-bound callback and node-session support, not external MCP/package attachment proof.
2. Patch Phase 4B wording so it owns watchdog recovery, MCP surface exposure, package/profile attachment proof, support-state freeze, and keeps the definition-registry/task-start `operator MCP` extensions deferred to Phase 5A.
3. Patch the file-lock map so the same ownership split and phase-scoped closeout artifact allowance are explicit.
4. Record this canon-fix through one Phase 0 plan/evidence/review artifact chain that closes only this seam.

## Validation

- no broad test lanes
- focused doc sanity only if useful for the touched execution surfaces
- final review is repo diff plus execution-record grammar sanity on the new Phase 0 plan/evidence/review artifact triplet

## Stop conditions

- stop if the fix requires app-code edits
- stop if the fix requires design-owner doc rewrites under `docs-internal/design/v1/**`
- stop if the truthful fix would require ownership outside the Phase 0-owned execution-canon surfaces
