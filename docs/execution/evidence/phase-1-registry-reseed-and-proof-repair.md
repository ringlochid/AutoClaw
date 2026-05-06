# Phase 1 Registry Reseed and Shipped-Path Proof Repair Evidence

Status: Reference

## Slice identity

- selected phase: Phase 1
- work package or slice: registry reseed semantics, shipped-path proof, and current-contrast parity
- date: 2026-05-05

## Plan link

- approved plan: `../plans/phase-1-registry-reseed-and-proof-repair.md`

## Delegated slice return log

- wave 2 delegated slices:
  - registry suite narrowing
    - slice type: `edit`
    - owned surfaces: `apps/api/tests/integration/test_definition_registry_db.py`
    - required reads: Phase 1 page, file lock map, and the current registry integration suite
    - expected outputs: Phase 1-valid registry/compiler proof retained and misowned runtime bootstrap/control proof removed
    - required validators/tests: focused pytest for `test_definition_registry_db.py`
    - dependencies: none
    - evidence requested: exact tests removed/retained and command outcomes
    - returned evidence: removed the three misowned runtime bootstrap/control proofs; retained the Phase 1-valid registry/compiler/revision-pinning proofs; `./.venv/bin/pytest -q apps/api/tests/integration/test_definition_registry_db.py` -> `8 passed`
    - parent ownership-boundary check result: passed
  - dotted-ID opacity regression
    - slice type: `edit`
    - owned surfaces: `apps/api/tests/unit/test_workflow_compiler.py`
    - required reads: Phase 1 page, workflow/compiler docs, workflow schema appendix, and the compiler unit suite
    - expected outputs: direct dotted-ID regression proving explicit-tree parenthood and opaque dotted ids
    - required validators/tests: focused pytest for `test_workflow_compiler.py`
    - dependencies: none
    - evidence requested: exact test added and command outcomes
    - returned evidence: added the dotted-ID opacity regression; `./.venv/bin/pytest -q apps/api/tests/unit/test_workflow_compiler.py` -> `10 passed`
    - parent ownership-boundary check result: passed
  - review-only Phase 1 audit
    - slice type: `review-only`
    - owned surfaces: none
    - required reads: Phase 1 page, file lock map, authoritative artifacts, `test_cli.py`, `test_db_reset_db.py`, `test_definition_registry_db.py`, and `test_workflow_compiler.py`
    - expected outputs: exact Phase 1 artifact deltas after suite narrowing and dotted-ID repair
    - required validators/tests: none
    - dependencies: sibling edit slices
    - evidence requested: exact file/line references, kept proof lanes, and residual ownership-containment gaps
    - returned evidence: Phase 1 artifacts must explicitly record ownership-containment restoration, keep `test_cli.py` for `db upgrade`, keep `test_db_reset_db.py` for `init`/`db reset`, and include the dotted-ID compiler suite
    - parent ownership-boundary check result: passed; no file edits returned

## Parent integration and validation log

- wave 2 integration result:
  - parent waited for the full delegated wave before integrating
  - parent reviewed every returned diff against owned surfaces and slice type
  - no out-of-scope edits or review-only edits required revert in this wave
  - parent merged the Phase 1 suite narrowing and dotted-ID regression
  - parent refreshed the authoritative Phase 1 artifacts to match the narrowed proof set

## Commands run

- `./.venv/bin/ruff format --check apps/api/app/registry/seeds.py apps/api/app/registry/service.py apps/api/app/registry/support.py apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/unit/test_cli.py`
  - outcome: passed
- `./.venv/bin/ruff check apps/api/app/registry/seeds.py apps/api/app/registry/service.py apps/api/app/registry/support.py apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/unit/test_cli.py`
  - outcome: passed
- `./.venv/bin/mypy apps/api/app/registry/seeds.py apps/api/app/registry/service.py apps/api/app/registry/support.py apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/unit/test_cli.py`
  - outcome: passed
- `make pyright-api`
  - outcome: passed
- `./.venv/bin/pytest -q apps/api/tests/unit/test_workflow_compiler.py`
  - outcome: `10 passed`
- `./.venv/bin/pytest -q apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/integration/test_registry_seed_authority.py apps/api/tests/integration/test_db_reset_db.py apps/api/tests/unit/test_cli.py`
  - outcome: `18 passed`
- `./.venv/bin/python scripts/docs/docs_freeze_validate.py`
  - outcome: passed
- `make test-api-db`
  - outcome: `102 passed`

## Gate and validator summary

- docs or prompt validators: `docs_freeze_validate.py` passed
- language gates: `ruff`, `mypy`, and `pyright` passed
- reset or package checks: SQLite shipped-path `init`/`db upgrade`/`db reset` proof and Postgres/Docker strong verification passed
- ownership containment: Phase 1 closure evidence no longer claims the removed runtime bootstrap/control proofs

## Test lanes

- unit: passed
- integration: passed
- e2e: not required in this phase
- SQLite: positive shipped-path `init`, `db upgrade`, and `db reset` proof passed
- Postgres or Docker: `make test-api-db` passed

## Artifacts

- `docs/execution/plans/phase-1-registry-reseed-and-proof-repair.md`
- `docs/execution/reviews/phase-1-registry-reseed-and-proof-repair.md`
- owning later-phase proof lanes: Phase 2 bootstrap/materialization tests and Phase 3 control-state tests

## Blockers

- none for this Phase 1 slice
- later Phase 2 and Phase 3 blockers remain open outside this phase

## Review link

- review artifact: `../reviews/phase-1-registry-reseed-and-proof-repair.md`
