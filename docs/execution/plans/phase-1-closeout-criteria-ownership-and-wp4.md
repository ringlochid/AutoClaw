# Phase 1 Closeout Criteria Ownership, WP4, and Proof Routing

Status: Reference

selected phase: Phase 1
current phase page: docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md
selected work packages: P1-WP1, P1-WP2, P1-WP3, P1-WP4
summary-only: no
delegated slices: listed
slice id: phase1-compiler-criteria-ownership
slice type: edit
owned surfaces: apps/api/app/compiler/contracts.py, apps/api/app/compiler/normalize.py, apps/api/tests/unit/test_workflow_compiler.py, docs/redesign/workflows/criteria-and-parent-verification.md, docs/redesign/workflows/compiler-contract-and-launch-materialization.md, docs/redesign/workflows/workflow-schema-appendix.md
touched surfaces: apps/api/app/compiler/contracts.py, apps/api/app/compiler/normalize.py, apps/api/tests/unit/test_workflow_compiler.py, docs/redesign/workflows/criteria-and-parent-verification.md, docs/redesign/workflows/compiler-contract-and-launch-materialization.md, docs/redesign/workflows/workflow-schema-appendix.md
slice id: phase1-examples-schema-proof
slice type: edit
owned surfaces: apps/api/tests/unit/test_definition_schemas.py, docs/redesign/workflows/workflow-definition-schema.md, docs/redesign/workflows/examples/minimal.md, docs/redesign/workflows/examples/normal.md, docs/redesign/workflows/examples/maximal.md, definitions/workflows/*.yaml, apps/api/app/resources/definitions/workflows/*.yaml
touched surfaces: apps/api/tests/unit/test_definition_schemas.py, docs/redesign/workflows/workflow-definition-schema.md
slice id: phase1-closeout-artifacts
slice type: edit
owned surfaces: docs/execution/plans/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/evidence/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/reviews/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/plans/phase-1-registry-reseed-and-proof-repair.md, docs/execution/evidence/phase-1-registry-reseed-and-proof-repair.md, docs/execution/reviews/phase-1-registry-reseed-and-proof-repair.md
touched surfaces: docs/execution/plans/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/evidence/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/reviews/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/plans/phase-1-registry-reseed-and-proof-repair.md, docs/execution/evidence/phase-1-registry-reseed-and-proof-repair.md, docs/execution/reviews/phase-1-registry-reseed-and-proof-repair.md
slice id: phase1-audit
slice type: review-only
owned surfaces: none
touched surfaces: none

## Slice identity

- selected phase: Phase 1
- work package or slice: authoritative closeout-path prep for criteria
  ownership, compiler proof, examples or fixtures closure, and phase-local
  proof routing across `P1-WP1` through `P1-WP4`
- owner: Codex
- date: 2026-05-06
- execution mode: owned execution-artifact rewrite only

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`

## Closeout focus

- make this chain the only `summary-only: no` Phase 1 closeout-path record in
  the owned surfaces
- keep authored criteria ownership explicit as Phase 1 truth rather than
  letting runtime projection wording blur that ownership
- route the new normalized criteria-owner contract through the authoritative
  Phase 1 closeout path so Phase 2 can consume it as a fixed upstream input
- route `P1-WP4` closure through examples, fixtures, and acceptance paths
  instead of leaving the older registry-reseed chain as the apparent Phase 1
  authority
- keep the Phase 1 shipped-path SQLite and Postgres or Docker proof
  obligations explicit without inventing outcomes that were not rerun here

## Scope mapping

- `P1-WP1`: controller-owned internal definition identity, revision, and
  currentness truth remain part of Phase 1 closeout because the phase-local
  proof still must show shipped-path `init`, `db upgrade`, and `db reset`
  behavior on the real path when persistence truth changed
- `P1-WP2`: authored criteria declarations, schema docs, and worked examples
  must stay aligned with the declaring-node ownership rule
- `P1-WP3`: normalized compiler output must preserve criteria ownership through
  legal direct-parent `child_defaults.criteria` expansion and keep that output
  test-backed
- `P1-WP4`: examples, fixtures, and acceptance paths must teach only the live
  tree-only model, including authored criteria ownership and direct-parent
  `child_defaults` expansion without hidden ancestor or runtime rewrite
  semantics

## Truths to encode

- authored criteria ownership is a Phase 1 contract: the node that declares a
  criteria slot owns that durable criteria contract, and legal direct-parent
  `child_defaults.criteria` expansion can project that contract only onto
  direct children
- runtime assignment `criteria`, `summary`, and `instruction` may surface or
  explain current criteria refs for one attempt, but they do not silently
  rewrite the authored baseline durable contract
- `P1-WP4` is still the Phase 1 closeout lane for copy-safe minimal, normal,
  and maximal workflow YAML plus any aligned packaged or fixture mirrors and
  regression or acceptance paths
- the older `phase-1-registry-reseed-and-proof-repair*` chain becomes
  historical support only after this chain lands and may not remain the
  apparent authority for Phase 1 closeout
- final closeout proof must stay phase-local and shipped-path-based where the
  phase page and reset gate require it

## Required proof before closeout

- example or fixture validation for minimal, normal, and maximal workflow YAML
  and any aligned packaged mirrors
- acceptance or regression proof that removed generic authored `skill_refs`
  semantics stay rejected or intentionally isolated
- shipped-path SQLite proof for `autoclaw init`, `autoclaw db upgrade`, and
  `autoclaw db reset` when the Phase 1 persistence truth is part of closure
- Postgres + Docker strong verification when the Phase 1 persistence truth is
  part of closure and the lane is viable

## Evidence routing

- this artifact does not claim final proof outcomes
- the parent will attach exact command results in
  `../evidence/phase-1-closeout-criteria-ownership-and-wp4.md` after
  integration
- the superseded registry-reseed evidence chain remains supporting history
  only:
  `../evidence/phase-1-registry-reseed-and-proof-repair.md`

## Validation checkpoints

- the top-level parseable label block stays exact
- this new chain is the only `summary-only: no` Phase 1 closeout-path artifact
  family in the owned surfaces
- the old registry-reseed chain is marked `summary-only: yes`
- no proof result is claimed here unless the new evidence artifact records the
  exact command outcome

## Stop conditions

- stop if truthful routing would require edits outside the owned Phase 1
  execution artifacts
- stop if closure would require changing Phase 0-owned gates, maps, or phase
  pages instead of recording the obligation here

## Cross-links

- evidence artifact:
  `../evidence/phase-1-closeout-criteria-ownership-and-wp4.md`
- review artifact:
  `../reviews/phase-1-closeout-criteria-ownership-and-wp4.md`
- superseded historical support:
  `../plans/phase-1-registry-reseed-and-proof-repair.md`
  `../evidence/phase-1-registry-reseed-and-proof-repair.md`
  `../reviews/phase-1-registry-reseed-and-proof-repair.md`
