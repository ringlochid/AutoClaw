# Phase 1 Registry Current-Doc and Proof Repair

Status: Reference

selected phase: Phase 1
current phase page: docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md
selected work packages: P1-WP1, P1-WP2, P1-WP3, P1-WP4
summary-only: no
delegated slices: listed
slice id: phase1-current-doc-and-record-refresh
slice type: edit
owned surfaces: docs/current/interfaces/definition-and-task-compose-yaml-contract.md, docs/execution/plans/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/evidence/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/reviews/phase-1-closeout-criteria-ownership-and-wp4.md
touched surfaces: docs/current/interfaces/definition-and-task-compose-yaml-contract.md, docs/execution/plans/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/evidence/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/reviews/phase-1-closeout-criteria-ownership-and-wp4.md
slice id: phase1-proof-revalidation
slice type: review-only
owned surfaces: apps/api/app/compiler/**, apps/api/app/registry/**, apps/api/app/schemas/definitions/**, apps/api/tests/unit/definition_schemas/**, apps/api/tests/unit/workflow_compiler/**, apps/api/tests/integration/definition_registry/**
touched surfaces: none

## Slice identity

- selected phase: Phase 1
- work package or slice: merged Phase 1 current-contrast repair, execution-record
  authority repair, and compiler/registry proof revalidation
- date: 2026-05-12
- execution mode: current-doc and execution-record repair plus code proof revalidation

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`

## Objective

- replace the stale monolith-era Phase 1 authority chain with live Phase 1
  package, current-contrast, and test paths only
- keep the required Phase 1 current-contrast repair aligned to the live
  registry/compiler/launch layout
- rerun the live compiler/registry proof lanes to confirm no Phase 1 code drift remains
- keep this triplet as the only authoritative `summary-only: no` Phase 1
  execution-record chain for the full Phase 1 work-package set
- remove the obsolete registry-reseed repair family because it no longer adds
  routing value after the authoritative replacement
- include the final current-contrast repair outcome in this authoritative chain

## Owned execution surfaces

- owned current-contrast doc:
  `docs/current/interfaces/definition-and-task-compose-yaml-contract.md`
- authoritative plan:
  `docs/execution/plans/phase-1-closeout-criteria-ownership-and-wp4.md`
- authoritative evidence:
  `docs/execution/evidence/phase-1-closeout-criteria-ownership-and-wp4.md`
- authoritative review:
  `docs/execution/reviews/phase-1-closeout-criteria-ownership-and-wp4.md`

## Surviving Phase 1 authority surfaces

- registry-backed currentness and revision truth:
  `apps/api/app/registry/current.py`,
  `apps/api/app/registry/upsert.py`,
  `apps/api/app/registry/seeds.py`, and
  `apps/api/app/registry/revisions/`
- authored schema and validation truth:
  `apps/api/app/schemas/definitions/`
- compiler normalization and legality truth:
  `apps/api/app/compiler/`
- current proof lanes for the split tree:
  `apps/api/tests/unit/definition_schemas/`,
  `apps/api/tests/unit/workflow_compiler/`, and
  `apps/api/tests/integration/definition_registry/`

## Proof routing

- static validation and Phase 1 split-suite proof are recorded only with live
  package or directory paths
- monolith-era references such as flat registry service files, flat unit test
  files, and flat integration test files are removed from this chain
- this authoritative chain claims the final owned current-doc repair that
  landed alongside the record rewrite:
  `docs/current/interfaces/definition-and-task-compose-yaml-contract.md`
- the already-repaired Phase 0 current-doc unlock set remains a prerequisite
  input to this chain, not an extra owned edit surface reopened here

## Validation checkpoints

- no missing Phase 1-owned repo paths remain in this plan, the matching
  evidence, or the matching review
- the `docs_freeze` failures that remain after this repair must come from
  current docs or later-phase execution records outside this slice
- no obsolete Phase 1 repair record remains authoritative after this repair

## Stop conditions

- stop if truthful repair would require edits outside the owned Phase 1
  execution records or the exact allowed Phase 1 current-contrast page above
- stop if current-doc drift or later-phase record drift must be fixed here
  instead of in their owning slices

## Cross-links

- evidence artifact:
  `../evidence/phase-1-closeout-criteria-ownership-and-wp4.md`
- review artifact:
  `../reviews/phase-1-closeout-criteria-ownership-and-wp4.md`
