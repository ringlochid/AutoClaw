# Phase 1 Registry Reseed and Shipped-Path Proof Repair Evidence

Status: Reference

## Slice identity

- selected phase: Phase 1
- work package or slice: registry reseed semantics, shipped-path proof, and current-contrast parity
- date: 2026-05-05

## Plan link

- approved plan: `../plans/phase-1-registry-reseed-and-proof-repair.md`

## Delegated wave evidence

- wave 2 delegated slices:
  - registry reseed semantics and persistence tests
  - shipped-path init/upgrade/reset proof tests
  - current-contrast registry docs parity
  - review-only Phase 1 audit
- wave 2 integration result:
  - parent integrated the reseed semantics code/test changes
  - parent integrated the positive `autoclaw db upgrade` proof
  - parent aligned current docs to the landed behavior
  - parent updated the Phase 0 validator marker that had become stale after the new Phase 1 reseed behavior

## Commands run

- `./.venv/bin/ruff format --check apps/api/app/registry/seeds.py apps/api/app/registry/service.py apps/api/app/registry/support.py apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/unit/test_cli.py`
  - outcome: passed
- `./.venv/bin/ruff check apps/api/app/registry/seeds.py apps/api/app/registry/service.py apps/api/app/registry/support.py apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/unit/test_cli.py`
  - outcome: passed
- `./.venv/bin/mypy apps/api/app/registry/seeds.py apps/api/app/registry/service.py apps/api/app/registry/support.py apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/unit/test_cli.py`
  - outcome: passed
- `make pyright-api`
  - outcome: passed
- `./.venv/bin/pytest -q apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/integration/test_registry_seed_authority.py apps/api/tests/integration/test_db_reset_db.py apps/api/tests/unit/test_cli.py`
  - outcome: `20 passed`
- `./.venv/bin/python scripts/docs/docs_freeze_validate.py`
  - outcome: passed
- `make test-api-db`
  - outcome: `102 passed`

## Gate and validator summary

- docs or prompt validators: `docs_freeze_validate.py` passed
- language gates: `ruff`, `mypy`, and `pyright` passed
- reset or package checks: SQLite shipped-path `init`/`db upgrade`/`db reset` proof and Postgres/Docker strong verification passed

## Test lanes

- unit: passed
- integration: passed
- e2e: not required in this phase
- SQLite: positive shipped-path `init`, `db upgrade`, and `db reset` proof passed
- Postgres or Docker: `make test-api-db` passed

## Artifacts

- `docs/execution/plans/phase-1-registry-reseed-and-proof-repair.md`
- `docs/execution/reviews/phase-1-registry-reseed-and-proof-repair.md`

## Blockers

- none for this Phase 1 slice
- later Phase 2 and Phase 3 blockers remain open outside this phase

## Review link

- review artifact: `../reviews/phase-1-registry-reseed-and-proof-repair.md`
