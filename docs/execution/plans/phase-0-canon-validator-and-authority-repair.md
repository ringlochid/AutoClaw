# Phase 0 Canon Validator and Authority Repair

Status: Reference

selected phase: Phase 0
current phase page: docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP1, P0-WP2, P0-WP3
summary-only: no
delegated slices: listed
slice id: phase0-validator-entrypoints
slice type: edit
owned surfaces: scripts/docs/docs_freeze/** and scripts/docs/prompt_catalog/** helpers required to make python -m validator entrypoints real
touched surfaces: scripts/docs/docs_freeze/**, scripts/docs/prompt_catalog/**
slice id: phase0-docs-freeze-stale-path-audit
slice type: edit
owned surfaces: scripts/docs/docs_freeze/** path validation and phase-record summary-only enforcement helpers
touched surfaces: scripts/docs/docs_freeze/repo_refs.py, scripts/docs/docs_freeze/validation/inventory.py, scripts/docs/docs_freeze/validation/docs.py, scripts/docs/docs_freeze/phase_records/rules.py, scripts/docs/docs_freeze/content/markers_execution.py
slice id: phase0-execution-pack-ownership-repair
slice type: edit
owned surfaces: docs/execution/README.md, docs/execution/gates/**, docs/execution/phases/**, docs/execution/maps/**
touched surfaces: docs/execution/README.md, docs/execution/gates/**, docs/execution/phases/**, docs/execution/maps/**
slice id: phase0-current-doc-unlocks-and-record-cleanup
slice type: edit
owned surfaces: Phase 0 current-doc cleanup under docs/current/** plus Phase 0-owned execution-record and aggregate summary-only files
touched surfaces: docs/current/**, docs/execution/plans/phase-0-canon-validator-and-authority-repair.md, docs/execution/evidence/phase-0-canon-validator-and-authority-repair.md, docs/execution/reviews/phase-0-canon-validator-and-authority-repair.md, docs/execution/plans/phase-0-closeout-grammar-and-proof.md, docs/execution/evidence/phase-0-closeout-grammar-and-proof.md, docs/execution/reviews/phase-0-closeout-grammar-and-proof.md, docs/execution/plans/phase-0-3-layout-and-shim-removal-program.md, docs/execution/evidence/phase-0-3-layout-and-shim-removal-program.md, docs/execution/reviews/phase-0-3-layout-and-shim-removal-program.md

## Slice identity

- work package or slice: merged Phase 0 validator, execution-pack, current-doc unlock, and authority-repair wave
- slice type: edit
- owner: Codex
- date: 2026-05-12

## Goal

- refresh the six explicit Phase 0 current-doc unlocks so they stop citing deleted or pseudo repo paths
- make the documented docs validators real executable `python -m` entrypoints
- extend docs-freeze so stale repo-path drift and aggregate summary misuse fail validation explicitly
- repair stale execution-pack package-split ownership claims inside Phase 0-owned canon
- repair the Phase 1 collateral-ownership canon so truthful current-contrast
  repair can stay phase-scoped
- replace stale Phase 0 closure authority with a truthful Phase 0 plan, evidence, and review chain for this repair slice
- prune redundant aggregate or superseded historical records so one minimal summary-only router family remains

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`

## Locked surfaces

- owned current docs:
  - `docs/current/interfaces/definition-precedence-and-skill-version-defaults.md`
  - `docs/current/interfaces/definitions-compiler-and-launch.md`
  - `docs/current/interfaces/definition-registry-and-publish-lifecycle.md`
  - `docs/current/architecture/runtime-control-plane.md`
  - `docs/current/architecture/current-architecture.md`
  - `docs/current/architecture/openclaw-dispatch-and-session-contract.md`
- owned execution records:
  - the new authoritative Phase 0 triplet for this slice
  - the superseded Phase 0 closeout triplet it replaces
  - aggregate summary-only records retained under `docs/execution/plans/`,
    `docs/execution/evidence/`, and `docs/execution/reviews/`
- owned tooling and canon:
  - `scripts/docs/docs_freeze/**`
  - `scripts/docs/prompt_catalog/**`
  - `docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md`
  - `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
  - `docs/execution/maps/file-priority-map.md`
  - `docs/execution/maps/redesign-code-landing-map.md`
- do not edit:
  - later-phase current docs outside the six explicit Phase 0 unlocks
  - runtime code
  - non-Phase-0 phase-scoped records for Phases 1-3

## Ordered work

1. make `scripts.docs.docs_freeze` and `scripts.docs.prompt_catalog` real `python -m` validator entrypoints
2. replace deleted prompt-catalog script-path calls and add repo-path / aggregate-summary validation to `docs_freeze`
3. repair Phase 1 and Phase 2 package-split ownership drift inside Phase
   0-owned execution canon
4. replace deleted, moved, or pseudo-path references in the six unlocked current docs with live package paths only
5. create the authoritative Phase 0 repair triplet for this merged wave
6. downgrade the older authoritative Phase 0 closeout triplet to summary-only history
7. delete redundant stale aggregate or superseded historical records that no longer help routing
8. keep exactly one useful aggregate summary-only router family and repoint it at the new authoritative Phase 0 triplet

## Validation and stop conditions

- required validator:
  - `./.venv/bin/python -m scripts.docs.docs_freeze.cli validate`
- optional prompt validator:
  - `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate` only if prompt-owned surfaces change
- required tooling gates when `scripts/docs/**` changes:
  - `./.venv/bin/ruff check scripts/docs`
  - `./.venv/bin/mypy scripts/docs`
  - `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
- stop if the remaining stale references are confined to later-phase current docs or phase-scoped records not owned by this slice
