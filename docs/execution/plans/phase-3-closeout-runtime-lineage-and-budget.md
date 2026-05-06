# Phase 3 Closeout Runtime Lineage and Budget

Status: Reference

selected phase: Phase 3
current phase page: docs/execution/phases/phase-3-runtime-parent-review-and-replan.md
selected work packages: P3-WP1, P3-WP2, P3-WP3
summary-only: no
delegated slices: none

## Slice identity

- work package or slice: authoritative Phase 3 closeout-path prep for the live
  runtime-lineage and budget blocker set
- slice type: edit
- owner: Codex
- date: 2026-05-06

## Goal

- establish the authoritative Phase 3 closeout chain at the
  `phase-3-closeout-runtime-lineage-and-budget*` path
- constrain that chain to the live blocker set only:
  - checkpoint ordering
  - lineage preservation
  - callback lineage
  - budget and failure taxonomy
  - raw delivery-state and control-state handoff
  - runtime DB lineage hardening
- demote `phase-3-runtime-contract-and-control-repair*` to historical support
  only
- keep proof outcomes unclaimed until parent integration attaches the final
  command results

## Locked surfaces

- primary owned surfaces:
  - `docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md`
  - `docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md`
  - `docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md`
- allowed historical-demotion surfaces:
  - `docs/execution/plans/phase-3-runtime-contract-and-control-repair.md`
  - `docs/execution/evidence/phase-3-runtime-contract-and-control-repair.md`
  - `docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md`
- do not edit surfaces:
  - `apps/api/app/**`
  - `apps/api/tests/**`
  - `scripts/docs/**`
  - Phase 0, Phase 1, and Phase 2 execution artifacts

## Required reads completed

- `AGENTS.md`
- `STYLE.md`
- `docs/execution/README.md`
- `docs/execution/maps/file-priority-map.md`
- `docs/execution/maps/redesign-code-landing-map.md`
- `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
- `docs/execution/gates/mandatory-review-gate.md`
- `docs/execution/gates/reset-gate.md`
- `docs/execution/gates/phase-done-gate.md`
- `docs/redesign/architecture/runtime-records-and-lifecycle.md`
- `docs/redesign/architecture/checkpoint-contract.md`
- `docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md`
- `docs/redesign/architecture/runtime-database-and-object-contract.md`
- `docs/redesign/architecture/runtime-observability-and-boundary-log.md`
- `docs/redesign/workflows/parent-review-and-replan.md`
- `docs/redesign/workflows/parent-root-release-and-closure.md`
- `docs/redesign/workflows/review-findings-contract.md`
- `docs/redesign/workflows/runtime-structural-replan.md`
- existing `phase-3-runtime-contract-and-control-repair*` execution artifacts

## Live blocker routing

- `P3-WP1` owns:
  - callback lineage
  - budget and failure taxonomy
  - raw delivery-state and control-state handoff
  - runtime DB lineage hardening on dispatch, delivery, continuity, watchdog,
    and budget families
- `P3-WP2` owns:
  - checkpoint ordering
  - parent or review handoff wording that depends on attempt-local checkpoint
    truth
- `P3-WP3` owns:
  - lineage preservation across parent-owned structural replan and staged child
    assignment flow

## Success criteria

- the authoritative Phase 3 closeout chain lives only at the
  `phase-3-closeout-runtime-lineage-and-budget*` path
- each authoritative file uses the exact top-level parseable labels at line
  start
- the authoritative chain stays limited to the six live blocker families and
  does not reopen older broad repair framing
- the old `phase-3-runtime-contract-and-control-repair*` chain is marked
  `summary-only: yes` and routed as historical support only
- the authoritative evidence and review files record only read-only sanity
  results from this slice plus explicit parent-integration placeholders for
  final proof lanes
- no final runtime, DB, reset, or gate outcome is claimed before parent
  integration attaches command results

## Validation checkpoints

- read-only sanity confirms exact header grammar on the new authoritative Phase
  3 chain
- read-only sanity confirms `summary-only: yes` on the demoted historical Phase
  3 chain
- read-only sanity confirms the new authoritative chain names only the six live
  blocker families
- read-only sanity confirms no final proof outcomes are claimed in the new
  authoritative evidence or review files

## Required validation for this slice

- `rg`
- `sed`

## Exit evidence

- evidence artifact:
  `../evidence/phase-3-closeout-runtime-lineage-and-budget.md`
- review artifact:
  `../reviews/phase-3-closeout-runtime-lineage-and-budget.md`

## Stop conditions

- stop if truthful routing requires edits to execution validator or gate docs
- stop if the closeout-path rewrite would need current-doc, code, test, or
  script changes outside the owned surfaces
