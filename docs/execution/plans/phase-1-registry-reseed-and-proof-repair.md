# Phase 1 Registry Reseed and Shipped-Path Proof Repair

Status: Reference

selected phase: Phase 1
current phase page: docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md
selected work packages: P1-WP1, P1-WP2, P1-WP3
summary-only: no
delegated slices: listed
slice id: registry-suite-narrowing
slice type: edit
owned surfaces: apps/api/tests/integration/test_definition_registry_db.py
touched surfaces: apps/api/tests/integration/test_definition_registry_db.py
slice id: dotted-id-opacity-regression
slice type: edit
owned surfaces: apps/api/tests/unit/test_workflow_compiler.py
touched surfaces: apps/api/tests/unit/test_workflow_compiler.py
slice id: phase-1-gate-audit
slice type: review-only
owned surfaces: none
touched surfaces: none

## Slice identity

- selected phase: Phase 1
- work package or slice: registry reseed semantics, registry-backed schema parity, compiler dotted-id opacity, and shipped-path `init` / `db upgrade` / `db reset` proof artifact rescope
- slice scope: registry reseed semantics, registry-backed schema parity,
  compiler dotted-id opacity, and shipped-path `init` / `db upgrade` /
  `db reset` proof
- artifact-rescope scope: repair the authoritative plan and review so they
  describe that landed Phase 1 slice truthfully without inventing extra
  work-package ids
- owner: Codex
- date: 2026-05-06

## Phase-local contract

- current phase page: `docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md`
- implementation file lock map: `docs/execution/maps/file-priority-map.md`

## Closeout focus

- closure objective: keep the authoritative Phase 1 closure artifacts aligned
  to the landed registry/compiler/reset/schema parity slice rather than
  reducing the work to a documentation-only refresh
- boundary verdict target: keep this artifact repair inside the owned execution
  records; do not reopen code or tests unless the evidence forces a
  contradiction
- proof-source rule: use 2026-05-06 focused reruns for the compiler lane and
  the registry or CLI or reset lane, and carry forward broader gate or
  Postgres-proof outcomes only where the evidence artifact explicitly records
  them
- scope guard: current-contrast pages remain answer-sourcing inputs here, not
  separate Phase 1 deliverables; `P1-WP4` examples and fixtures are outside
  this slice

## Delegated slices and return contract

- `registry-suite-narrowing`
  serves `P1-WP1` and `P1-WP2`
- do-not-edit surfaces: Phase 2 and Phase 3 tests, runtime code, compiler
  code, docs, and artifacts
- required reads: Phase 1 page, file lock map, authoritative Phase 1
  artifacts, and the current registry integration suite
- expected outputs: remove misowned runtime bootstrap/control proof while
  retaining Phase 1-valid registry, revision-currentness, and registry-backed
  validation proof
- required validators/tests: focused pytest for
  `apps/api/tests/integration/test_definition_registry_db.py`
- evidence to return: exact tests removed or retained and command outcomes
- parent-owned decisions: whether any remaining runtime bootstrap/control proof
  belongs in later-phase lanes instead

- `dotted-id-opacity-regression`
  serves `P1-WP3`
- do-not-edit surfaces: integration tests, compiler code, schema code, docs,
  and artifacts
- required reads: Phase 1 page, workflow/compiler docs, workflow schema
  appendix, and the compiler unit suite
- expected outputs: direct dotted-id regression proving explicit-tree
  parenthood and opaque dotted ids
- required validators/tests: focused pytest for
  `apps/api/tests/unit/test_workflow_compiler.py`
- evidence to return: exact test added and command outcomes
- parent-owned decisions: whether a compiler fix is needed if the regression
  fails

- `phase-1-gate-audit`
  serves `P1-WP1`, `P1-WP2`, and `P1-WP3`
- do-not-edit surfaces: all files
- required reads: Phase 1 page, file lock map, authoritative Phase 1
  plan/evidence/review artifacts, `test_cli.py`, `test_db_reset_db.py`,
  `test_definition_registry_db.py`, and `test_workflow_compiler.py`
- expected outputs: exact authoritative artifact deltas needed after suite
  narrowing and dotted-id repair
- required validators/tests: none
- evidence to return: exact file or line references, kept proof lanes, and
  residual ownership-containment gaps
- parent-owned decisions: artifact edits and final verdict
- stop conditions: review only; do not edit or revert anything

## Goal

- record the landed Phase 1 slice truthfully: controller-owned definition
  revision/currentness truth and shipped-path proof remain validated,
  registry-backed schema parity stays limited to the tested behaviors, dotted
  ids stay opaque, and the closure artifact set no longer includes misowned
  runtime bootstrap/control proof

## Locked surfaces

- underlying implementation surfaces already landed in this slice: internal
  registry persistence and lookup under `apps/api/app/db/*`,
  `apps/api/app/registry/*`, compiler-facing and shipped-path proof tests, and
  narrow current-contrast reads used for answer sourcing
- artifact repair surfaces in this pass:
  `docs/execution/plans/phase-1-registry-reseed-and-proof-repair.md` and
  `docs/execution/reviews/phase-1-registry-reseed-and-proof-repair.md`
- do not edit or defer surfaces:
  `docs/execution/evidence/phase-1-registry-reseed-and-proof-repair.md`,
  `scripts/docs/*`, app code/tests, and any Phase 0/2/3 docs or artifacts

## Success criteria

- `P1-WP1`: changed seed content appends or reuses immutable revisions
  correctly, preserves controller-selected currentness when reseed should not
  promote, and remains covered by shipped-path `init`, `db upgrade`, and
  `db reset` proof
- `P1-WP2`: schema-parity claims stay limited to the registry-backed
  validation and revision-pinning assertions retained in
  `test_definition_registry_db.py` and `test_registry_seed_authority.py`; no
  broader workflow, role, or policy schema completeness is claimed
- `P1-WP3`: dotted node ids are treated as opaque strings and parenthood comes
  only from explicit tree structure in the compiler lane
- Phase 1 closure evidence no longer includes the removed runtime
  bootstrap/control proofs
- the authoritative plan and review use only real Phase 1 work-package ids and
  truthful delegated-slice wording

## Deliverables

- truthful Phase 1 plan and mandatory review scoped to `P1-WP1`, `P1-WP2`, and
  `P1-WP3`
- retained proof-lane mapping for registry/currentness, shipped-path reset
  coverage, registry-backed validation parity, and compiler dotted-id opacity
- explicit note that broader gates and Postgres proof are relied on only as
  recorded in the evidence artifact

## Validation checkpoints

- focused registry persistence and registry-backed validation lane remains
  green in the evidence artifact
- focused CLI/reset/seed-authority lane remains green in the evidence artifact
- dotted-id regression remains green in the compiler unit suite in the
  evidence artifact
- broader docs, lint, type, and Postgres or Docker lanes are referenced only
  when the evidence artifact records them
- post-edit readback of the authoritative Phase 1 plan and review passes with
  real work-package ids and no scope overclaim

## Required tests and validators

- authoritative source:
  `docs/execution/evidence/phase-1-registry-reseed-and-proof-repair.md`
- rerun lanes already recorded there:
  - `./.venv/bin/pytest -q apps/api/tests/unit/test_workflow_compiler.py`
  - `./.venv/bin/pytest -q apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/integration/test_registry_seed_authority.py apps/api/tests/integration/test_db_reset_db.py apps/api/tests/unit/test_cli.py`
  - `./.venv/bin/pytest --collect-only -q apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/integration/test_registry_seed_authority.py apps/api/tests/integration/test_db_reset_db.py apps/api/tests/unit/test_cli.py`
- carried-forward broader proof recorded there:
  - `./.venv/bin/ruff format --check ...`
  - `./.venv/bin/ruff check ...`
  - `./.venv/bin/mypy ...`
  - `make pyright-api`
  - `./.venv/bin/python scripts/docs/docs_freeze_validate.py`
  - `make test-api-db`

## Required docs and examples

- required redesign owners for this slice: the Phase 1 page, workflow/compiler
  owner docs, and `docs/redesign/interfaces/role-and-policy-definition-schema.md`
- required current-contrast reads for this slice:
  `docs/current/interfaces/definition-registry-and-publish-lifecycle.md` and
  `docs/current/interfaces/definitions-compiler-and-launch.md`
- out of scope: `P1-WP4` example or fixture closure

## Exit evidence

- evidence artifact: `../evidence/phase-1-registry-reseed-and-proof-repair.md`

## Rollback or stop conditions

- stop if truthful rescope would require edits to the evidence artifact or any
  code/test surface
- stop if the evidence contradicts a claimed mapping to `P1-WP1`, `P1-WP2`, or
  `P1-WP3`
- stop if any required scope repair depends on claiming untested schema
  completeness or `P1-WP4` example coverage

## Cross-links

- evidence artifact: `../evidence/phase-1-registry-reseed-and-proof-repair.md`
- review artifact: `../reviews/phase-1-registry-reseed-and-proof-repair.md`
