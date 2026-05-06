# Phase 3 Runtime Contract and Control Repair

Status: Reference

## Slice identity

- selected phase: Phase 3
- work package or slice: `P3-WP3` authoritative artifact refresh for stale-basis conflicts, relational direct-child authority, drain-window visible-dispatch semantics, and final proof closeout
- owner: Codex
- date: 2026-05-06

## Subagents decision

- `no subagents`

## Delegated slice contract

- none; this refresh is bounded to the three owned Phase 3 artifact files and records already-landed Phase 3 truth only

## Wave integration rule

- parent no-edit during wave: not applicable; no delegated wave ran for this refresh
- full-wave wait rule: not applicable
- ownership-boundary and slice-type review: only the three owned Phase 3 artifact files may change
- revert rule for out-of-scope or review-only edits: stop and report instead of widening into current docs, scripts, app code, tests, or earlier-phase artifacts
- validation and review before next wave: complete a read-only sanity pass on the owned files before closeout

## Goal

- rewrite the authoritative Phase 3 execution artifacts so they use the real
  `P3-WP1` through `P3-WP3` work-package ids only, record the current Phase 3
  proof values exactly, and describe controller authority/read-surface truth
  without stale rerun or non-authoritative-runtime wording

## Phase-local contract

- current phase page: `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
- implementation file lock map: `docs/execution/maps/file-priority-map.md`
- required reads completed: yes

## Locked surfaces

- owned surfaces:
  - `docs/execution/plans/phase-3-runtime-contract-and-control-repair.md`
  - `docs/execution/evidence/phase-3-runtime-contract-and-control-repair.md`
  - `docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md`
- allowed collateral surfaces:
  - read-only use of `AGENTS.md`, `STYLE.md`, `docs/execution/README.md`, the
    Phase 3 phase page, the file-priority map, the current Phase 3
    plan/evidence/review artifacts, and
    `docs/redesign/architecture/runtime-observability-and-boundary-log.md`
- do not edit or defer surfaces:
  - current docs
  - `scripts/docs/*`
  - app code or tests
  - Phase 1 or Phase 2 execution artifacts

## Success criteria

- the Phase 3 plan/evidence/review use only `P3-WP1`, `P3-WP2`, and `P3-WP3`
- stale assignment and stale checkpoint evidence is recorded on the `409`
  conflict lane
- direct-child authority is described as relational-id authority; shadow
  `parent_node_key` and `child_node_keys_json` values are mirrors only
- drain-window visible-dispatch semantics are aligned across the owned read
  surfaces
- `provider-events.ndjson` is described as a normalized observability export,
  not authoritative controller truth
- the current proof values are recorded exactly:
  - runtime schema contract lane: `8 passed`
  - focused Phase 3 bundle: `55 passed`
  - `make pyright-api`: `0 errors`
  - `make test-api-db`: `152 passed`
- no stale higher-numbered Phase 3 work-package references remain
- no stale docs-freeze rerun or parent-rerun-pending wording remains

## Deliverables and milestones

- deliverables:
  - refreshed Phase 3 plan
  - refreshed Phase 3 evidence
  - refreshed Phase 3 review
- milestones:
  - real Phase 3 work-package ids restored
  - authority wording corrected
  - current proof values recorded
  - stale rerun language removed

## Ordered work packages

- `P3-WP1`: align runtime record transitions, foreground control-state
  handshake, and assignment/attempt semantics
- `P3-WP2`: align parent verification, review outputs, and closure evidence
- `P3-WP3`: align parent-owned structural replan and adoption flow, then record
  the authoritative final artifact refresh for the landed Phase 3 tree

## Validation checkpoints

- the owned artifacts use template-compatible parseable labels
- the owned artifacts reference only `P3-WP1` through `P3-WP3`
- the owned artifacts record `409`, relational direct-child authority,
  drain-window visible-dispatch semantics, and non-authoritative
  `provider-events.ndjson` wording
- the owned artifacts record the current `8 passed`, `55 passed`, `0 errors`,
  and `152 passed` proof values exactly
- read-only sanity over the owned files passes

## Required tests and validators

- `rg -n 'P3-WP(4|5|6|7)|docs[_]freeze_validate|pending parent .* rerun|must .* rerun' docs/execution/plans/phase-3-runtime-contract-and-control-repair.md docs/execution/evidence/phase-3-runtime-contract-and-control-repair.md docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md`
- `rg -n 'P3-WP1|P3-WP2|P3-WP3|409|relational|direct-child|drain-window|visible-dispatch|not authoritative|8 passed|55 passed|0 errors|152 passed' docs/execution/plans/phase-3-runtime-contract-and-control-repair.md docs/execution/evidence/phase-3-runtime-contract-and-control-repair.md docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md`
- `sed -n '1,220p' docs/execution/plans/phase-3-runtime-contract-and-control-repair.md`
- `sed -n '1,220p' docs/execution/evidence/phase-3-runtime-contract-and-control-repair.md`
- `sed -n '1,220p' docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md`

## Required docs and examples

- `AGENTS.md`
- `STYLE.md`
- `docs/execution/README.md`
- `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
- `docs/execution/maps/file-priority-map.md`
- `docs/redesign/architecture/runtime-observability-and-boundary-log.md`
- the current Phase 3 plan, evidence, and review artifacts

## Exit evidence

- evidence artifact: `../evidence/phase-3-runtime-contract-and-control-repair.md`

## Rollback or stop conditions

- stop if truthful refresh would require current-doc, script, code, or test
  changes outside the three owned Phase 3 artifact files
- stop if the owned artifacts cannot be made truthful without a new code-side
  or current-doc fix and report that blocker instead of patching forward

## Cross-links

- evidence artifact: `../evidence/phase-3-runtime-contract-and-control-repair.md`
- review artifact: `../reviews/phase-3-runtime-contract-and-control-repair.md`
