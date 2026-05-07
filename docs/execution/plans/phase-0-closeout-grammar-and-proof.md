# Phase 0 Closeout Grammar and Proof

Status: Reference

selected phase: Phase 0
current phase page: docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP2, P0-WP3
summary-only: no
delegated slices: none

## Slice identity

- work package or slice: execution-record grammar, validator enforcement, and
  historical replacement-link truth for the remaining Phase 0 closeout fixes
- slice type: edit
- owner: Codex
- date: 2026-05-07

## Goal

- make execution canon describe one exact top-of-file execution-record block
- make summary-only routing explicit for both phase-local historical artifacts
  and cross-phase aggregate summaries
- make `docs_freeze_validate.py` enforce the real header order, the
  `## Artifacts changed` evidence heading used by this closeout path, the
  allowed Phase 0 current-doc unlock set, and truthful replacement links
- rewrite the authoritative Phase 0 chain and the owned historical Phase 0
  summaries so their touched-surface, validation, delegation, and replacement
  claims remain accurate

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`

## Locked surfaces

- primary owned surfaces:
  - `docs/execution/README.md`
  - `docs/execution/gates/mandatory-review-gate.md`
  - `docs/execution/gates/phase-done-gate.md`
  - `docs/execution/maps/file-priority-map.md`
  - `docs/execution/maps/redesign-code-landing-map.md`
  - `docs/execution/how-to/use-this-pack-for-implementation.md`
  - `scripts/docs/docs_freeze_validate.py`
  - `docs/execution/plans/phase-0-closeout-grammar-and-proof.md`
  - `docs/execution/evidence/phase-0-closeout-grammar-and-proof.md`
  - `docs/execution/reviews/phase-0-closeout-grammar-and-proof.md`
  - `docs/execution/plans/phase-0-canon-current-contrast-repair.md`
  - `docs/execution/evidence/phase-0-canon-current-contrast-repair.md`
  - `docs/execution/reviews/phase-0-canon-current-contrast-repair.md`
  - `docs/execution/plans/phase-0-3-closeout.md`
  - `docs/execution/evidence/phase-0-3-closeout.md`
  - `docs/execution/reviews/phase-0-3-closeout.md`
  - `docs/execution/reviews/phase-0-3-closeout-review-exceptions.md`
- allowed collateral surfaces:
  - `README.md` only if root routing truth needs a Phase 0 wording repair
- do not edit or defer surfaces:
  - `apps/**`
  - `docs/execution/plans/phase-plan-template.md`
  - `docs/execution/evidence/phase-evidence-template.md`
  - `docs/execution/reviews/phase-review-template.md`
  - phase-scoped Phase 1, Phase 2, and Phase 3 artifacts other than the
    historical Phase 0 aggregate summaries named above

## Required reads completed

- `AGENTS.md`
- `STYLE.md`
- `docs/execution/README.md`
- `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- `docs/execution/maps/file-priority-map.md`
- `docs/execution/maps/redesign-code-landing-map.md`
- `docs/execution/gates/mandatory-review-gate.md`
- `docs/execution/gates/phase-done-gate.md`
- `docs/execution/gates/reset-gate.md`
- `docs/execution/how-to/use-this-pack-for-implementation.md`
- `scripts/docs/docs_freeze_validate.py`
- owned historical Phase 0 and `phase-0-3` closeout artifacts

## Success criteria

- execution canon describes one exact top-of-file block and the same
  summary-only rules the validator enforces
- the landing map no longer understates the Phase 0 current-doc unlock set
- `docs_freeze_validate.py` rejects reordered or displaced header blocks on
  execution artifacts
- `docs_freeze_validate.py` checks truthful `## Authoritative replacements`
  links on summary-only artifacts in the execution record homes
- the Phase 0 authoritative plan, evidence, and review truthfully describe the
  touched surfaces and required proof lanes for this slice
- the owned historical artifacts point only to authoritative `summary-only: no`
  replacements

## Deliverables and milestones

- deliverables:
  - updated execution grammar canon
  - updated Phase 0 landing-map wording
  - updated docs freeze validator
  - truthful authoritative and historical Phase 0 closeout artifacts
- milestones:
  - grammar and sentinel wording aligned
  - validator tightened without widening into non-owned surfaces
  - historical replacement links cleaned up
  - Phase 0 proof rerun and recorded

## Ordered work packages

- `P0-WP2`: tighten execution-record grammar wording in the execution pack and
  closeout gates
- `P0-WP3`: tighten validator behavior, reconcile the Phase 0 unlock map, and
  rewrite the owned historical Phase 0 closeout artifacts

## Validation checkpoints

- the top-of-file block stays exact on every touched execution artifact
- `phase-0-3-closeout*` uses the cross-phase sentinel grammar and truthful
  authoritative replacements
- `phase-0-canon-current-contrast-repair*` stays historical and points back to
  the authoritative Phase 0 chain
- no touched artifact claims validation that was not rerun in this shell

## Required tests and validators

- `./.venv/bin/python scripts/docs/docs_freeze_validate.py`
- `./.venv/bin/ruff check scripts/docs`
- `./.venv/bin/mypy scripts/docs`

## Required docs and examples

- `docs/execution/README.md`
- `docs/execution/how-to/use-this-pack-for-implementation.md`
- `docs/execution/gates/mandatory-review-gate.md`
- `docs/execution/gates/phase-done-gate.md`
- `docs/execution/maps/file-priority-map.md`
- `docs/execution/maps/redesign-code-landing-map.md`

## Exit evidence

- evidence artifact:
  `../evidence/phase-0-closeout-grammar-and-proof.md`
- review artifact:
  `../reviews/phase-0-closeout-grammar-and-proof.md`

## Rollback or stop conditions

- stop if the fix requires edits under `apps/**`
- stop if making the shared execution-record templates match the new Phase 0
  grammar is required before closeout, because those templates are outside this
  slice's owned surfaces
