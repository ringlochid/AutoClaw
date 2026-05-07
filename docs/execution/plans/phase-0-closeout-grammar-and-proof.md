# Phase 0 Closeout Grammar and Proof

Status: Reference

selected phase: Phase 0
current phase page: docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP1, P0-WP2, P0-WP3
summary-only: no
delegated slices: none

## Slice identity

- work package or slice: root-routing re-audit plus execution-record grammar,
  validator enforcement, and historical replacement-link truth for the
  remaining Phase 0 closeout fixes
- slice type: edit
- owner: Codex
- date: 2026-05-07

## Goal

- make execution canon describe one exact top-of-file execution-record block
- re-audit the root authority and routing surfaces so the front-door docs do
  not keep stale Phase 0.5 baseline claims alive
- make summary-only routing explicit for both phase-local historical artifacts
  and cross-phase aggregate summaries
- remove any remaining execution-template wording drift that would mislead
  future reviewers about the live evidence shape
- make `docs_freeze_validate.py` enforce the real header order, the
  `## Artifacts changed` evidence heading used by this closeout path, the
  allowed Phase 0 current-doc unlock set, and truthful replacement links
- make execution canon require unused-code audit proof for touched Python
  surfaces and exact justification for any retained flagged private helper or
  redundant branch
- legalize the exact Phase 2/3 test collateral and Phase 2 current-doc
  collateral the later closeout chains need, instead of leaving those edits
  out of scope and then recording them anyway
- rewrite the authoritative Phase 0 chain and the owned historical Phase 0
  summaries so their touched-surface, validation, delegation, and replacement
  claims remain accurate
- confirm the suspected Phase 0.5 closure-authority gap is either real in
  canon or already ruled out by conditional Phase 1 dependency wording

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`

## Locked surfaces

- primary owned surfaces:
  - `docs/README.md`
  - `README.md`
  - `docs/execution/README.md`
  - `docs/execution/evidence/README.md`
  - `docs/execution/evidence/phase-evidence-template.md`
  - `docs/execution/gates/mandatory-review-gate.md`
  - `docs/execution/gates/phase-done-gate.md`
  - `docs/execution/maps/file-priority-map.md`
  - `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
  - `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
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
  - none
- do not edit or defer surfaces:
  - `apps/**`
  - `docs/execution/plans/phase-plan-template.md`
  - `docs/execution/reviews/phase-review-template.md`
  - phase-scoped Phase 1, Phase 2, and Phase 3 artifacts other than the
    historical Phase 0 aggregate summaries named above

## Required reads completed

- `AGENTS.md`
- `STYLE.md`
- `docs/execution/README.md`
- `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- `docs/execution/phases/phase-0.5-cleanup-and-salvage-baseline.md`
- `docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md`
- `docs/execution/maps/file-priority-map.md`
- `docs/execution/maps/redesign-code-landing-map.md`
- `docs/execution/gates/mandatory-review-gate.md`
- `docs/execution/gates/phase-done-gate.md`
- `docs/execution/gates/reset-gate.md`
- `docs/execution/evidence/README.md`
- `docs/execution/evidence/phase-evidence-template.md`
- `docs/execution/how-to/use-this-pack-for-implementation.md`
- `scripts/docs/docs_freeze_validate.py`
- owned historical Phase 0 and `phase-0-3` closeout artifacts

## Success criteria

- execution canon describes one exact top-of-file block and the same
  summary-only rules the validator enforces
- execution canon now requires unused-code audit proof for touched Python
  surfaces in mandatory review
- root docs routing no longer describes the repo as a Phase 0.5-only minimal
  baseline when that is no longer current tree truth
- the landing map no longer understates the Phase 0 current-doc unlock set
- the lock map and Phase 2/3 pages now legalize the exact test and
  current-contrast collateral those closeout chains need
- `docs_freeze_validate.py` rejects reordered or displaced header blocks on
  execution artifacts
- `docs_freeze_validate.py` checks truthful `## Authoritative replacements`
  links on summary-only artifacts in the execution record homes
- the Phase 0 authoritative plan, evidence, and review truthfully describe the
  touched surfaces and required proof lanes for this slice
- the owned historical artifacts point only to authoritative `summary-only: no`
  replacements
- the Phase 1 dependency wording is confirmed to keep Phase 0.5 conditional
  rather than silently demanding a missing unconditional closeout chain
- the shared evidence README and template use the same residual-blocker wording
  as the live authoritative evidence surfaces

## Deliverables and milestones

- deliverables:
  - updated execution grammar canon
  - cleaned root routing summary
  - aligned evidence-home template wording
  - repaired Phase 2/3 collateral rules for tests and exact current-doc
    contrasts
  - dead-code audit rule added to execution canon
  - updated Phase 0 landing-map wording
  - updated docs freeze validator
  - truthful authoritative and historical Phase 0 closeout artifacts
- milestones:
  - root routing and authority re-audit aligned
  - grammar and sentinel wording aligned
  - record-home template drift removed
  - validator tightened without widening into non-owned surfaces
  - historical replacement links cleaned up
  - Phase 0 proof rerun and recorded

## Ordered work packages

- `P0-WP1`: re-audit root authority and routing surfaces, and remove any
  stale root README claims that contradict the current tree or execution-pack
  routing truth
- `P0-WP2`: tighten execution-record grammar wording in the execution pack and
  closeout gates, and remove evidence-home template wording drift that would
  misdescribe the live closeout evidence shape
- `P0-WP3`: tighten validator behavior, reconcile the Phase 0 unlock map,
  legalize the exact Phase 2/3 collateral the later closeout chains need, and
  rewrite the owned historical Phase 0 closeout artifacts

## Validation checkpoints

- the top-of-file block stays exact on every touched execution artifact
- root routing points readers to `docs/README.md`, `docs/execution/README.md`,
  `AGENTS.md`, and `STYLE.md` instead of stale baseline prose
- `phase-0-3-closeout*` uses the cross-phase sentinel grammar and truthful
  authoritative replacements
- `phase-0-canon-current-contrast-repair*` stays historical and points back to
  the authoritative Phase 0 chain
- the suspected Phase 0.5 closure-authority gap is resolved as either a canon
  fix or a verified false positive before closeout is claimed
- the mandatory review gate explicitly requires unused-code audit proof and
  exact justification for retained flagged private helpers
- no touched artifact claims validation that was not rerun in this shell

## Required tests and validators

- `./.venv/bin/python scripts/docs/docs_freeze_validate.py`
- `./.venv/bin/ruff check scripts/docs`
- `./.venv/bin/mypy scripts/docs`

## Required docs and examples

- `docs/execution/README.md`
- `docs/README.md`
- `README.md`
- `docs/execution/how-to/use-this-pack-for-implementation.md`
- `docs/execution/gates/mandatory-review-gate.md`
- `docs/execution/gates/phase-done-gate.md`
- `docs/execution/maps/file-priority-map.md`
- `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
- `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
- `docs/execution/maps/redesign-code-landing-map.md`

## Exit evidence

- evidence artifact:
  `../evidence/phase-0-closeout-grammar-and-proof.md`
- review artifact:
  `../reviews/phase-0-closeout-grammar-and-proof.md`

## Rollback or stop conditions

- stop if the fix requires edits under `apps/**`
- stop if resolving a real remaining blocker requires non-Phase-0 runtime or
  product-contract changes
