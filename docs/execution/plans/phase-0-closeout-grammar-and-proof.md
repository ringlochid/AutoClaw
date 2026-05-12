# Phase 0 Structural Debt Canon and Audit Proof

Status: Reference

selected phase: Phase 0
current phase page: docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP2, P0-WP3
summary-only: no
delegated slices: listed
slice id: phase0-canon-audit-rules
slice type: edit
owned surfaces: AGENTS.md, STYLE.md, docs/execution/gates/mandatory-review-gate.md, docs/execution/maps/file-priority-map.md, docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md, docs/execution/plans/phase-0-closeout-grammar-and-proof.md, docs/execution/evidence/phase-0-closeout-grammar-and-proof.md, docs/execution/reviews/phase-0-closeout-grammar-and-proof.md
touched surfaces: AGENTS.md, STYLE.md, docs/execution/gates/mandatory-review-gate.md, docs/execution/maps/file-priority-map.md, docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md, docs/execution/plans/phase-0-closeout-grammar-and-proof.md, docs/execution/evidence/phase-0-closeout-grammar-and-proof.md, docs/execution/reviews/phase-0-closeout-grammar-and-proof.md
slice id: phase0-docs-freeze-entrypoint-split
slice type: edit
owned surfaces: scripts/docs/docs_freeze/**, scripts/docs/markdown_format/**
touched surfaces: scripts/docs/docs_freeze/**, scripts/docs/markdown_format/**
slice id: phase0-prompt-catalog-and-audit-tool-entrypoint-split
slice type: edit
owned surfaces: scripts/docs/prompt_catalog/**, scripts/docs/style_audit/**
touched surfaces: scripts/docs/prompt_catalog/**, scripts/docs/style_audit/**
slice id: phase0-structural-debt-audit
slice type: review-only
owned surfaces: none
touched surfaces: none
slice id: phase0-docs-freeze-second-split
slice type: edit
owned surfaces: scripts/docs/docs_freeze/**, scripts/docs/markdown_format/**
touched surfaces: scripts/docs/docs_freeze/**, scripts/docs/markdown_format/**
slice id: phase0-prompt-catalog-and-audit-tool-second-split
slice type: edit
owned surfaces: scripts/docs/prompt_catalog/**, scripts/docs/style_audit/**
touched surfaces: scripts/docs/prompt_catalog/**, scripts/docs/style_audit/**
slice id: phase0-tooling-followup-review
slice type: review-only
owned surfaces: none
touched surfaces: none

## Slice identity

- work package or slice: integrated structural-debt cleanup canon and docs
  tooling split for shared helper naming, module layout, function ordering,
  execution-record validation, prompt-catalog validation, and audit proof
- slice type: edit
- owner: Codex
- date: 2026-05-07

## Goal

- require helpers imported across modules to use public non-underscored names
- add explicit module-layout and top-level function-ordering rules to
  `STYLE.md`
- add a repo-native structural-debt inventory command at
  `./.venv/bin/python -m scripts.docs.style_audit.cli`
- make Phase 0 canon require both repo-native backend type proof via
  `make pyright-api` and structural-debt inventory proof for later cleanup
  slices
- split the `scripts/docs` validator and prompt-catalog entrypoints into thin
  commands plus named helper modules that no longer violate the `STYLE.md`
  thresholds
- rewrite the authoritative Phase 0 plan, evidence, and review triplet so it
  truthfully describes this integrated slice and its delegated work

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`

## Locked surfaces

- primary owned surfaces:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs/execution/gates/mandatory-review-gate.md`
  - `docs/execution/maps/file-priority-map.md`
  - `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
  - `scripts/docs/docs_freeze/**`
  - `scripts/docs/prompt_catalog/**`
  - `scripts/docs/style_audit/**`
  - `scripts/docs/markdown_format/**`
  - `docs/execution/plans/phase-0-closeout-grammar-and-proof.md`
  - `docs/execution/evidence/phase-0-closeout-grammar-and-proof.md`
  - `docs/execution/reviews/phase-0-closeout-grammar-and-proof.md`
- allowed collateral surfaces:
  - none
- do not edit or defer surfaces:
  - `apps/**`
  - Phase 1, Phase 2, and Phase 3 code or tests

## Required reads completed

- `AGENTS.md`
- `STYLE.md`
- `docs/execution/README.md`
- `docs/execution/phases/overview.md`
- `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- `docs/execution/maps/file-priority-map.md`
- `docs/execution/gates/mandatory-review-gate.md`
- `docs/execution/plans/phase-0-closeout-grammar-and-proof.md`
- `docs/execution/evidence/phase-0-closeout-grammar-and-proof.md`
- `docs/execution/reviews/phase-0-closeout-grammar-and-proof.md`
- `docs/execution/reviews/phase-1-closeout-criteria-ownership-and-wp4.md`
- `docs/execution/reviews/phase-2-closeout-prompt-legality-and-proof.md`
- `docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md`
- `scripts/docs/docs_freeze/**`
- `scripts/docs/prompt_catalog/**`

## Success criteria

- `AGENTS.md` and `STYLE.md` state that helpers imported across modules must use
  public non-underscored names and keep underscore-prefixed names module-local
- `STYLE.md` contains explicit module-layout and top-level function-ordering
  rules
- `./.venv/bin/python -m scripts.docs.style_audit.cli` inventories
  cross-module underscore imports, zero-reference private helpers, and
  file/function threshold debt across the Phase 0-3 cleanup scope
- the mandatory review gate, file lock map, and Phase 0 phase contract require
  both `make pyright-api` and the structural-debt audit command in the right
  contexts
- Phase 0 canon keeps `scripts/docs/*` lint and typing proof separate from the
  backend Python audit command
- no `scripts/docs` file or function touched by this slice remains over the
  `STYLE.md` thresholds
- the authoritative Phase 0 plan, evidence, and review describe only this slice
  and its owned surfaces
- no owned artifact claims validator or audit proof that was not rerun in this
  shell

## Deliverables and milestones

- deliverables:
  - updated `AGENTS.md` helper-naming canon
  - updated `STYLE.md` module-layout and function-ordering rules
  - updated mandatory review gate and Phase 0 canon for repo-native backend
    Python proof plus structural-debt inventory proof
  - thin `scripts/docs` entrypoints for docs-freeze and prompt-catalog
  - split `scripts/docs` helper modules below the `STYLE.md` thresholds
  - new `execution_style_audit.py` command plus helper modules
  - truthful authoritative Phase 0 closeout artifacts for this slice
- milestones:
  - shared-helper naming rule aligned
  - structural-debt style rules aligned
  - audit-proof rule aligned across the review gate and Phase 0 canon
  - docs tooling split below Phase 0 threshold debt
  - Phase 0 proof rerun and recorded

## Ordered work packages

- `P0-WP2`: tighten shared canon and mandatory review wording for structural
  debt cleanup, including shared-helper naming, module layout, function
  ordering, backend Python proof expectations, and structural-debt inventory
  proof expectations
- `P0-WP3`: align the lock map and Phase 0 phase contract with the repo-native
  audit proof, split the docs tooling entrypoints into responsibility modules,
  and refresh the authoritative Phase 0 closeout records for this slice

## Validation checkpoints

- the top-of-file block stays exact on every touched execution artifact
- `AGENTS.md` and `STYLE.md` reserve underscore-private helper names for
  module-local use only
- the mandatory review gate and Phase 0 canon explicitly require
  `make pyright-api` for touched backend Python surfaces and the structural
  debt audit command for later cleanup slices
- the Phase 0 canon keeps `scripts/docs/*` proof lanes explicit instead of
  implying that `make pyright-api` covers them
- the touched `scripts/docs` modules stay below the `STYLE.md` thresholds
- the authoritative plan, evidence, and review do not claim touched surfaces
  outside this slice
- no touched artifact claims validation that was not rerun in this shell

## Required tests and validators

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate`
- `./.venv/bin/python -m scripts.docs.style_audit.cli`
- `./.venv/bin/ruff check scripts/docs`
- `./.venv/bin/mypy scripts/docs`
- `make pyright-api`

## Required docs and examples

- `AGENTS.md`
- `STYLE.md`
- `docs/execution/README.md`
- `docs/execution/gates/mandatory-review-gate.md`
- `docs/execution/maps/file-priority-map.md`
- `docs/execution/phases/overview.md`
- `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- `docs/execution/reviews/phase-1-closeout-criteria-ownership-and-wp4.md`
- `docs/execution/reviews/phase-2-closeout-prompt-legality-and-proof.md`
- `docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md`
- `scripts/docs/docs_freeze_*.py`
- `scripts/docs/prompt_catalog_*.py`
- `scripts/docs/execution_style_audit*.py`

## Exit evidence

- evidence artifact:
  `../evidence/phase-0-closeout-grammar-and-proof.md`
- review artifact:
  `../reviews/phase-0-closeout-grammar-and-proof.md`

## Rollback or stop conditions

- stop if the fix requires edits under `apps/**`
- stop if resolving a real remaining blocker requires non-Phase-0 canon changes
  outside the owned surfaces
