# Phase 0 Canon and Current-Contrast Repair

Status: Reference

## Slice identity

- selected phase: Phase 0
- work package or slice: reconcile Phase 0 phase-scoped artifacts back to
  `P0-WP1`, `P0-WP2`, and `P0-WP3`
- slice type: `edit`
- owner: Codex
- date: 2026-05-06

## Slice scope

- refresh the authoritative Phase 0 plan, evidence, and review artifacts so
  they describe only the Phase 0 work already scoped by `P0-WP1`, `P0-WP2`,
  and `P0-WP3`
- refresh the summary-only
  `docs/execution/reviews/phase-0-3-closeout-review-exceptions.md` page so it
  remains historical and non-authoritative
- remove invented later Phase 0 work-package claims from the owned artifacts
- remove stale blocker, validator, and file-size prose that this slice cannot
  re-prove from the owned surfaces
- keep delegated-slice wording truthful for this artifact-reconciliation slice

## Delegation decision

- subagents decision: `no subagents`
- rationale: this slice is limited to four Phase 0 artifact files, and the
  required reconciliation is narrower and safer than opening another delegated
  wave

## Goal

- make the owned Phase 0 artifacts truthful about closure authority, work
  package scope, delegated-slice usage, and summary-only history without
  changing canon outside the owned surfaces

## Phase-local contract

- current phase page: `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`
- required reads completed: yes

## Owned surfaces for this slice

- `docs/execution/plans/phase-0-canon-current-contrast-repair.md`
- `docs/execution/evidence/phase-0-canon-current-contrast-repair.md`
- `docs/execution/reviews/phase-0-canon-current-contrast-repair.md`
- `docs/execution/reviews/phase-0-3-closeout-review-exceptions.md`

## Do not edit surfaces for this slice

- `AGENTS.md`
- `STYLE.md`
- `docs/execution/phases/*`
- `docs/execution/maps/*`
- `docs/execution/gates/*`
- `scripts/docs/*`
- `docs/current/*`
- app code and tests

## Success criteria

- the authoritative Phase 0 artifact chain names exactly one selected phase:
  Phase 0
- the authoritative Phase 0 artifact chain maps its statements back to
  `P0-WP1`, `P0-WP2`, and `P0-WP3` only
- no owned artifact invents later unapproved Phase 0 work-package ids
- no owned artifact claims current-slice edits or delegated ownership outside
  the four owned files
- delegated-slice wording is internally consistent and truthful for this slice
- `phase-0-3-closeout-review-exceptions.md` remains summary-only and
  non-authoritative

## Phase 0 work-package anchors

- `P0-WP1`: canonical root instruction and coding-standard surfaces
- `P0-WP2`: execution prompts, router pages, and phase-boundary rules
- `P0-WP3`: validation tooling, landing coverage, root routing, and the
  explicit Phase 0 current-doc unlock list

This slice does not create a new Phase 0 work package. It reconciles the owned
artifacts back to the existing `P0-WP1` through `P0-WP3` contract.

## Validation checkpoints

- read-only sanity over the four owned artifacts confirms that later
  unapproved Phase 0 work-package claims are removed
- read-only sanity over the four owned artifacts confirms that delegated-slice
  wording is consistent with `no subagents`
- read-only sanity over the four owned artifacts confirms that the summary-only
  exceptions page stays non-authoritative
- post-edit readback of the four owned artifacts passes

## Required validation for this slice

- `rg`
- `sed`
- `nl`

Use those read-only checks on the owned files only. Do not run repo-wide
validators or mutate other surfaces in this slice.

## Required docs

- `AGENTS.md`
- `STYLE.md`
- `docs/execution/README.md`
- `docs/execution/phases/overview.md`
- `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- `docs/execution/maps/file-priority-map.md`
- `docs/execution/maps/redesign-code-landing-map.md`
- `docs/execution/gates/mandatory-review-gate.md`
- `docs/execution/gates/phase-done-gate.md`
- `docs/execution/reviews/README.md`
- the four owned artifacts

## Exit evidence

- evidence artifact: `../evidence/phase-0-canon-current-contrast-repair.md`
- review artifact: `../reviews/phase-0-canon-current-contrast-repair.md`
- summary-only historical page:
  `../reviews/phase-0-3-closeout-review-exceptions.md`

## Stop conditions

- stop if truthful reconciliation would require edits outside the four owned
  surfaces
- stop if the owned artifacts cannot express the needed Phase 0 truth without a
  canon change to the phase page, gate pages, or lock map
