# Phase 3 Runtime Contract and Control Repair

Status: Reference

## Slice identity

- selected phase: Phase 3
- work package or slice: runtime DB truth, control-state handshake, replan/API semantics, and exact route/readback proof
- owner: Codex
- date: 2026-05-06

## Subagents decision

- delegated slices:
  - runtime DB/object-contract and schema proof
  - foreground control-state handshake and delivery-state projection
  - replan/API semantics and contract-fix regressions
  - route/readback proof tightening
  - review-only Phase 3 audit

## Goal

- land the remaining authoritative runtime record, control-state, replan, and
  API truth required by the Phase 3 contract

## Phase-local contract

- current phase page: `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
- implementation file lock map: `docs/execution/maps/file-priority-map.md`
- required reads completed: yes

## Locked surfaces

- owned surfaces: runtime DB models, runtime control/replan services, runtime schemas/presenters/routes, and Phase 3 runtime tests
- allowed collateral surfaces:
  - `apps/api/app/cli.py` only for shipped-path proof where needed
  - current runtime-control contrast wording and Phase 0 validator expectations needed to keep current-behavior docs truthful after the landed Phase 3 changes
- do not edit or defer surfaces: gateway/session continuity implementation beyond explicit deferral, wider Phase 4B watchdog/plugin ownership, public ingest or broader package/release surfaces

## Success criteria

- runtime DB truth matches canon for structural lineage, runtime-node state, assignment lineage/supersession, immutable publication-currentness, and normalized provider events
- authoritative lineage/currentness relations are DB-enforced where canon requires
- replacement dispatch cannot open until inactivity is proven
- boundary-accepted waiting and deadline-driven ambiguous states are real production behavior and project correctly into delivery-state/readback payloads
- cancel does not release the workspace lease early
- root can add a child under an explicit descendant parent
- dependency-legality callback rejects return `422`
- route/readback and contract tests assert exact payload/schema behavior

## Deliverables and milestones

- deliverables:
  - expanded runtime DB/object model
  - repaired control-state handshake
  - widened root descendant `add_child`
  - corrected API legality lane mapping
  - tightened route/readback proof
  - Phase 3 plan/evidence/review artifacts
- milestones:
  - DB/object truth aligned
  - control-state truth aligned
  - replan/API truth aligned
  - route/readback proof aligned
  - SQLite/Postgres and workflow proof lanes green

## Ordered work packages

- `P3-WP1`: runtime DB/object-contract repair
- `P3-WP2`: authoritative lineage/currentness FK repair
- `P3-WP3`: waiting/ambiguous control-state handshake repair
- `P3-WP4`: root descendant `add_child` and `422` legality mapping
- `P3-WP5`: route/readback proof tightening
- `P3-WP6`: Phase 3 evidence and review

## Validation checkpoints

- focused schema/control/route/contract suites pass
- `make pyright-api` passes
- current runtime-control contrast and validator expectations are updated to the landed shipped behavior
- explicit minimal and normal workflow proof commands are recorded
- SQLite shipped-path `init`/`db upgrade`/`db reset` proof passes
- Docker/Postgres strong verification passes

## Required tests and validators

- `./.venv/bin/ruff format --check apps/api/app/db/models/runtime/flow.py apps/api/app/db/models/runtime/assignment.py apps/api/app/db/models/runtime/dispatch.py apps/api/app/db/models/runtime/shared.py apps/api/app/runtime/control/boundary.py apps/api/app/runtime/control/flows.py apps/api/app/runtime/control/release.py apps/api/app/runtime/projection/materialize.py apps/api/app/runtime/replan/service.py apps/api/app/schemas/runtime/parent_tools.py apps/api/app/api/errors.py apps/api/app/runtime/control/observability.py apps/api/tests/integration/test_runtime_schema_contract.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
- `./.venv/bin/ruff check apps/api/app/db/models/runtime/flow.py apps/api/app/db/models/runtime/assignment.py apps/api/app/db/models/runtime/dispatch.py apps/api/app/db/models/runtime/shared.py apps/api/app/runtime/control/boundary.py apps/api/app/runtime/control/flows.py apps/api/app/runtime/control/release.py apps/api/app/runtime/projection/materialize.py apps/api/app/runtime/replan/service.py apps/api/app/schemas/runtime/parent_tools.py apps/api/app/api/errors.py apps/api/app/runtime/control/observability.py apps/api/tests/integration/test_runtime_schema_contract.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
- `./.venv/bin/mypy apps/api/app/db/models/runtime/flow.py apps/api/app/db/models/runtime/assignment.py apps/api/app/db/models/runtime/dispatch.py apps/api/app/db/models/runtime/shared.py apps/api/app/runtime/control/boundary.py apps/api/app/runtime/control/flows.py apps/api/app/runtime/control/release.py apps/api/app/runtime/projection/materialize.py apps/api/app/runtime/replan/service.py apps/api/app/schemas/runtime/parent_tools.py apps/api/app/api/errors.py apps/api/app/runtime/control/observability.py apps/api/tests/integration/test_runtime_schema_contract.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
- `make pyright-api`
- `./.venv/bin/python scripts/docs/docs_freeze_validate.py`
- minimal workflow proof: `./.venv/bin/pytest -q apps/api/tests/integration/test_phase2_runtime_bootstrap.py`
- normal workflow proof: `./.venv/bin/pytest -q apps/api/tests/integration/test_phase3_runtime_contract_fixes.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_routes.py`
- focused Phase 3 suite: `./.venv/bin/pytest -q apps/api/tests/integration/test_runtime_schema_contract.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py apps/api/tests/integration/test_definition_registry_db.py`
- SQLite shipped-path proof: `./.venv/bin/pytest -q apps/api/tests/unit/test_cli.py::test_init_writes_minimal_config_and_db_file apps/api/tests/unit/test_cli.py::test_db_upgrade_bootstraps_seeded_sqlite_database_on_shipped_path apps/api/tests/unit/test_cli.py::test_db_reset_recreates_sqlite_database`
- Postgres or Docker strong verification: `make test-api-db`

## Required docs and examples

- runtime DB/object contract docs
- runtime lifecycle/control-state docs
- replan/release/readback docs
- current runtime-control contrast docs

## Exit evidence

- evidence artifact: `../evidence/phase-3-runtime-contract-and-control-repair.md`

## Rollback or stop conditions

- stop if any required continuity or gateway behavior crosses into full Phase 4A ownership instead of a narrow Phase 3 compatibility boundary
- stop if the normal workflow proof lane becomes ambiguous rather than executable and record the exact blocker instead of claiming closure

## Cross-links

- evidence artifact: `../evidence/phase-3-runtime-contract-and-control-repair.md`
- review artifact: `../reviews/phase-3-runtime-contract-and-control-repair.md`
