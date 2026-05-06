# Phase 3 Runtime Contract and Control Repair Evidence

Status: Reference

## Slice identity

- selected phase: Phase 3
- work package or slice: runtime DB truth, control-state handshake, replan/API semantics, and exact route/readback proof
- date: 2026-05-06

## Plan link

- approved plan: `../plans/phase-3-runtime-contract-and-control-repair.md`

## Delegated slice return log

- wave 4 delegated slices:
  - runtime lineage and Phase 3 DB proof
    - slice type: `edit`
    - owned surfaces: `apps/api/app/runtime/replan/support.py`, `apps/api/app/runtime/control/parent_tools.py`, `apps/api/tests/integration/test_runtime_schema_contract.py`, `apps/api/tests/integration/test_phase3_runtime_db.py`
    - required reads: the full Phase 3 required read set plus the owned lineage/test files
    - expected outputs: full structural lineage writes and runtime-value lineage assertions
    - required validators/tests: focused `ruff check` and focused pytest on the owned lineage/test files
    - dependencies: none
    - evidence requested: exact lineage fields landed and command outcomes
    - returned evidence: structural adopt now persists revision lineage, adopted nodes carry `flow_id`/`flow_revision_id`, carried and staged assignments carry `flow_id`/`flow_revision_id`/`flow_node_id`, and focused lineage/schema pytest passed
    - parent ownership-boundary check result: passed
  - normalized provider-event materialization and route proof
    - slice type: `edit`
    - owned surfaces: `apps/api/app/runtime/control/release.py`, `apps/api/app/runtime/projection/materialize.py`, Phase 3-owned provider-event helper path, and `apps/api/tests/integration/test_phase3_runtime_routes.py`
    - required reads: the full Phase 3 required read set plus runtime observability docs and the owned provider-event files/tests
    - expected outputs: normalized provider-event persistence and NDJSON readback proof
    - required validators/tests: focused `ruff check` and focused pytest on `test_phase3_runtime_routes.py`
    - dependencies: none
    - evidence requested: exact normalized event path, exact files changed, and command outcomes
    - returned evidence: dispatch accept now appends a normalized provider-event row; `provider-events.ndjson` materializes normalized keys and excludes raw payload blobs; focused route pytest passed
    - parent ownership-boundary check result: passed
  - semantic `422` lane
    - slice type: `edit`
    - owned surfaces: `apps/api/app/api/errors.py`, `apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
    - required reads: the full Phase 3 required read set plus the API appendix and owned error/test files
    - expected outputs: evaluated-but-semantic missing dependency/provider/current artifact/file-missing cases map to `422` while missing ids/entities stay `404`
    - required validators/tests: focused `ruff check`, focused `mypy`, and focused pytest on the owned error/test files
    - dependencies: none
    - evidence requested: exact mappings changed, exact cases covered, and command outcomes
    - returned evidence: `missing artifact provider...`, `missing current artifact...`, and `produced artifact does not exist: ...` now map to `422`; explicit `404` unknown-id regression added; focused route-free contract-fix pytest passed
    - parent ownership-boundary check result: passed
  - review-only Phase 3 artifact audit
    - slice type: `review-only`
    - owned surfaces: none
    - required reads: the full Phase 3 required read set plus the authoritative Phase 3 artifacts and current Phase 3 tests
    - expected outputs: exact artifact deltas and exact proof-lane wording needed for closure
    - required validators/tests: none
    - dependencies: sibling edit slices
    - evidence requested: exact file/line references and a concise keep/fix checklist
    - returned evidence: exact Phase 3 artifact changes needed for delegated-slice proof, proof-lane wording, and closure-grade evidence
    - parent ownership-boundary check result: passed; no file edits returned
  - review-only Phase 3 integration audit
    - slice type: `review-only`
    - owned surfaces: none
    - required reads: the full Phase 3 required read set plus the owned code/test files from sibling slices
    - expected outputs: integration audit checklist for lineage completeness, provider-event shape, `422` boundaries, and phase-boundary drift
    - required validators/tests: none
    - dependencies: sibling edit slices
    - evidence requested: exact file/line references and concise risk notes
    - returned evidence: integration audit highlighted the need to confirm runtime-value lineage assertions, NDJSON content assertions, and the narrowed `422`/`404` lane in the final proof set
    - parent ownership-boundary check result: passed; no file edits returned

## Parent integration and validation log

- wave 4 integration result:
  - parent waited for the full delegated wave before integrating
  - parent reviewed every returned diff against owned surfaces and slice type
  - no out-of-scope edits or review-only edits required revert in this wave
  - parent integrated the lineage, provider-event, and semantic `422` slices
  - parent will rerun the focused Phase 3 suites plus SQLite/Postgres/normal-lane proof before closure

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
- `./.venv/bin/pytest -q apps/api/tests/integration/test_phase3_runtime_db.py::test_phase3_minimal_root_closure_remains_readable`
  - outcome: pending parent rerun after integration
- `./.venv/bin/pytest -q apps/api/tests/integration/test_phase3_runtime_db.py::test_phase3_parent_worker_flow_and_replan_state`
  - outcome: pending parent rerun after integration
- `./.venv/bin/pytest -q apps/api/tests/integration/test_runtime_schema_contract.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py apps/api/tests/integration/test_phase3_runtime_db.py`
  - outcome: pending parent rerun after integration
- `./.venv/bin/pytest -q apps/api/tests/unit/test_cli.py::test_init_writes_minimal_config_and_db_file apps/api/tests/unit/test_cli.py::test_db_upgrade_bootstraps_seeded_sqlite_database_on_shipped_path apps/api/tests/unit/test_cli.py::test_db_reset_recreates_sqlite_database`
  - outcome: pending parent rerun after integration
- `make test-api-db`
  - outcome: pending parent rerun after integration

## Gate and validator summary

- docs or prompt validators: `docs_freeze_validate.py` passed
- language gates: focused `ruff`, `mypy`, and `pyright` proof passed; parent full rerun pending after integration
- reset or package checks: SQLite shipped-path proof and Docker/Postgres strong verification must be rerun and recorded after integration

## Test lanes

- unit: covered via repo-native phase proofs where relevant
- integration: slice-level Phase 3 proof passed; parent integrated rerun pending
- e2e:
  - minimal lane command pending parent rerun after integration
  - normal lane command pending parent rerun after integration
- SQLite: shipped-path `init`, `db upgrade`, and `db reset` proof pending parent rerun after integration
- Postgres or Docker: `make test-api-db` pending parent rerun after integration

## Artifacts

- `docs/execution/plans/phase-3-runtime-contract-and-control-repair.md`
- `docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md`

## Blockers

- none for this Phase 3 slice
- full live same-session continuity selection remains explicitly out of scope for Phase 4A, not a Phase 3 blocker

## Review link

- review artifact: `../reviews/phase-3-runtime-contract-and-control-repair.md`
