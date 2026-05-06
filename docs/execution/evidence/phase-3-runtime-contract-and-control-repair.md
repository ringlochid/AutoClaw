# Phase 3 Runtime Contract and Control Repair Evidence

Status: Reference

## Slice identity

- selected phase: Phase 3
- work package or slice: runtime DB truth, control-state handshake, replan/API semantics, and exact route/readback proof
- date: 2026-05-06

## Plan link

- approved plan: `../plans/phase-3-runtime-contract-and-control-repair.md`

## Delegated wave evidence

- wave 4 delegated slices:
  - runtime DB/object-contract and schema proof
  - foreground control-state handshake and delivery-state projection
  - replan/API semantics and contract-fix regressions
  - route/readback proof tightening
  - review-only Phase 3 audit
- wave 4 integration result:
  - parent integrated the DB/object-contract changes
  - parent integrated the control-state changes
  - parent integrated the replan/API and route-proof changes
  - parent patched broader integration fallout in bootstrap persistence, callback helper behavior, workspace-lease expectations, and route query assumptions
  - parent updated the current runtime-control contrast page and the Phase 0 validator expectation to the new shipped behavior

## Commands run

- `./.venv/bin/ruff format --check apps/api/app/db/models/runtime/flow.py apps/api/app/db/models/runtime/assignment.py apps/api/app/db/models/runtime/dispatch.py apps/api/app/db/models/runtime/shared.py apps/api/app/runtime/control/boundary.py apps/api/app/runtime/control/flows.py apps/api/app/runtime/control/release.py apps/api/app/runtime/projection/materialize.py apps/api/app/runtime/replan/service.py apps/api/app/schemas/runtime/parent_tools.py apps/api/app/api/errors.py apps/api/app/runtime/control/observability.py apps/api/tests/integration/test_runtime_schema_contract.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
  - outcome: passed
- `./.venv/bin/ruff check apps/api/app/db/models/runtime/flow.py apps/api/app/db/models/runtime/assignment.py apps/api/app/db/models/runtime/dispatch.py apps/api/app/db/models/runtime/shared.py apps/api/app/runtime/control/boundary.py apps/api/app/runtime/control/flows.py apps/api/app/runtime/control/release.py apps/api/app/runtime/projection/materialize.py apps/api/app/runtime/replan/service.py apps/api/app/schemas/runtime/parent_tools.py apps/api/app/api/errors.py apps/api/app/runtime/control/observability.py apps/api/tests/integration/test_runtime_schema_contract.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
  - outcome: passed
- `./.venv/bin/mypy apps/api/app/db/models/runtime/flow.py apps/api/app/db/models/runtime/assignment.py apps/api/app/db/models/runtime/dispatch.py apps/api/app/db/models/runtime/shared.py apps/api/app/runtime/control/boundary.py apps/api/app/runtime/control/flows.py apps/api/app/runtime/control/release.py apps/api/app/runtime/projection/materialize.py apps/api/app/runtime/replan/service.py apps/api/app/schemas/runtime/parent_tools.py apps/api/app/api/errors.py apps/api/app/runtime/control/observability.py apps/api/tests/integration/test_runtime_schema_contract.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
  - outcome: passed
- `make pyright-api`
  - outcome: passed
- `./.venv/bin/python scripts/docs/docs_freeze_validate.py`
  - outcome: passed
- `./.venv/bin/pytest -q apps/api/tests/integration/test_phase2_runtime_bootstrap.py`
  - outcome: `8 passed`
- `./.venv/bin/pytest -q apps/api/tests/integration/test_phase3_runtime_contract_fixes.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_routes.py`
  - outcome: `19 passed`
- `./.venv/bin/pytest -q apps/api/tests/integration/test_runtime_schema_contract.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py apps/api/tests/integration/test_definition_registry_db.py`
  - outcome: `33 passed`
- `./.venv/bin/pytest -q apps/api/tests/unit/test_cli.py::test_init_writes_minimal_config_and_db_file apps/api/tests/unit/test_cli.py::test_db_upgrade_bootstraps_seeded_sqlite_database_on_shipped_path apps/api/tests/unit/test_cli.py::test_db_reset_recreates_sqlite_database`
  - outcome: `3 passed`
- `make test-api-db`
  - outcome: `107 passed`

## Gate and validator summary

- docs or prompt validators: `docs_freeze_validate.py` passed
- language gates: `ruff`, `mypy`, and `pyright` passed
- reset or package checks: SQLite shipped-path proof and Docker/Postgres strong verification passed

## Test lanes

- unit: covered via repo-native phase proofs where relevant
- integration: focused Phase 3 suites passed
- e2e:
  - minimal lane command passed
  - normal lane command passed
- SQLite: shipped-path `init`, `db upgrade`, and `db reset` proof passed
- Postgres or Docker: `make test-api-db` passed

## Artifacts

- `docs/execution/plans/phase-3-runtime-contract-and-control-repair.md`
- `docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md`

## Blockers

- none for this Phase 3 slice
- full live same-session continuity selection remains explicitly out of scope for Phase 4A, not a Phase 3 blocker

## Review link

- review artifact: `../reviews/phase-3-runtime-contract-and-control-repair.md`
