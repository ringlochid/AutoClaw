# Phase 3 Runtime Contract and Control Repair

Status: Reference

## Slice identity

- selected phase: Phase 3
- work package or slice: runtime DB truth, control-state handshake, replan/API semantics, and exact route/readback proof
- owner: Codex
- date: 2026-05-06

## Delegated slices and return contract

- delegated slices:
  - runtime lineage and Phase 3 DB proof
    - slice type: `edit`
    - selected phase: Phase 3
    - owned surfaces: `apps/api/app/runtime/replan/support.py`, `apps/api/app/runtime/control/parent_tools.py`, `apps/api/tests/integration/test_runtime_schema_contract.py`, `apps/api/tests/integration/test_phase3_runtime_db.py`
    - do-not-edit surfaces: provider-event logic, API error mapping, docs, artifacts, and non-owned tests
    - required reads: the full Phase 3 required read set plus the owned lineage/test files
    - expected outputs: full structural lineage writes and runtime-value lineage assertions
    - required validators/tests: focused `ruff check` and focused pytest on the owned lineage/test files
    - dependencies: none
    - evidence to return: exact lineage fields landed and command outcomes
    - parent-owned decisions: artifact refresh and any doc wording that cites the landed semantics
    - stop conditions: stop and report if a needed change requires provider-event or API error surfaces
  - normalized provider-event materialization and route proof
    - slice type: `edit`
    - selected phase: Phase 3
    - owned surfaces: `apps/api/app/runtime/control/release.py`, `apps/api/app/runtime/projection/materialize.py`, any Phase 3-owned provider-event ingestion helper needed, and `apps/api/tests/integration/test_phase3_runtime_routes.py`
    - do-not-edit surfaces: lineage/adopt files, API error mapping, docs, artifacts, and non-owned tests
    - required reads: the full Phase 3 required read set plus runtime observability docs and the owned provider-event files/tests
    - expected outputs: normalized provider-event persistence and NDJSON readback proof
    - required validators/tests: focused `ruff check` and focused pytest on `test_phase3_runtime_routes.py`
    - dependencies: none
    - evidence to return: exact normalized event path, exact files changed, and command outcomes
    - parent-owned decisions: artifact refresh and any doc wording that cites the landed shape
    - stop conditions: stop and report if a needed change requires lineage/adopt or API error surfaces
  - semantic `422` lane
    - slice type: `edit`
    - selected phase: Phase 3
    - owned surfaces: `apps/api/app/api/errors.py`, `apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
    - do-not-edit surfaces: provider-event logic, lineage/adopt files, docs, artifacts, and non-owned tests
    - required reads: the full Phase 3 required read set plus the API appendix and owned error/test files
    - expected outputs: evaluated-but-semantic missing dependency/provider/current artifact/file-missing cases map to `422` while missing ids/entities stay `404`
    - required validators/tests: focused `ruff check` and focused pytest on the owned error/test files
    - dependencies: none
    - evidence to return: exact mappings changed, exact cases covered, and command outcomes
    - parent-owned decisions: artifact refresh and any doc wording that cites the landed lane
    - stop conditions: stop and report if a needed change requires provider-event or lineage/adopt surfaces
  - review-only Phase 3 artifact audit
    - slice type: `review-only`
    - selected phase: Phase 3
    - owned surfaces: none
    - do-not-edit surfaces: all files
    - required reads: the full Phase 3 required read set plus the authoritative Phase 3 plan/evidence/review artifacts and current Phase 3 tests
    - expected outputs: exact artifact deltas and exact proof-lane wording needed for closure
    - required validators/tests: none
    - dependencies: sibling edit slices
    - evidence to return: exact file/line references and a concise keep/fix checklist
    - parent-owned decisions: actual artifact edits and final verdict
    - stop conditions: review only; do not edit or revert anything
  - review-only Phase 3 integration audit
    - slice type: `review-only`
    - selected phase: Phase 3
    - owned surfaces: none
    - do-not-edit surfaces: all files
    - required reads: the full Phase 3 required read set plus the owned code/test files from sibling slices
    - expected outputs: integration audit checklist for lineage completeness, provider-event shape, `422` boundaries, and phase-boundary drift
    - required validators/tests: none
    - dependencies: sibling edit slices
    - evidence to return: exact file/line references and concise risk notes
    - parent-owned decisions: final integration verdict
    - stop conditions: review only; do not edit or revert anything

## Goal

- land the remaining authoritative runtime record, control-state, replan, and
  API truth required by the Phase 3 contract, including runtime-value lineage,
  normalized provider-event materialization, and exact semantic `422` proof

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
- runtime-value lineage proof is explicit in the Phase 3 workflow lanes
- `provider-events.ndjson` materializes normalized rows, not raw payload blobs
- semantic missing dependency/provider/current artifact/file-missing failures return `422` while missing ids/entities stay `404`

## Deliverables and milestones

- deliverables:
  - expanded runtime DB/object model
  - repaired control-state handshake
  - landed runtime-value lineage proof
  - landed normalized provider-event materialization
  - widened root descendant `add_child`
  - corrected API legality lane mapping
  - tightened route/readback proof
  - Phase 3 plan/evidence/review artifacts
- milestones:
  - DB/object truth aligned
  - control-state truth aligned
  - lineage/provider-event truth aligned
  - replan/API truth aligned
  - route/readback proof aligned
  - SQLite/Postgres and workflow proof lanes green

## Ordered work packages

- `P3-WP1`: runtime DB/object-contract repair
- `P3-WP2`: authoritative lineage/currentness FK repair
- `P3-WP3`: waiting/ambiguous control-state handshake repair
- `P3-WP4`: root descendant `add_child` and `422` legality mapping
- `P3-WP5`: normalized provider-event materialization and route/readback proof
- `P3-WP6`: runtime-value lineage proof tightening
- `P3-WP7`: Phase 3 evidence and review

## Validation checkpoints

- focused schema/control/route/contract suites pass
- `make pyright-api` passes
- current runtime-control contrast and validator expectations are updated to the landed shipped behavior
- explicit minimal and normal workflow proof commands are recorded
- runtime-value lineage assertions pass in the Phase 3 workflow lane
- normalized provider-event NDJSON assertions pass
- semantic `422` and companion `404` assertions pass
- SQLite shipped-path `init`/`db upgrade`/`db reset` proof passes
- Docker/Postgres strong verification passes

## Required tests and validators

- `./.venv/bin/ruff format --check apps/api/app/db/models/runtime/flow.py apps/api/app/db/models/runtime/assignment.py apps/api/app/db/models/runtime/dispatch.py apps/api/app/db/models/runtime/shared.py apps/api/app/runtime/control/boundary.py apps/api/app/runtime/control/flows.py apps/api/app/runtime/control/release.py apps/api/app/runtime/projection/materialize.py apps/api/app/runtime/replan/service.py apps/api/app/schemas/runtime/parent_tools.py apps/api/app/api/errors.py apps/api/app/runtime/control/observability.py apps/api/tests/integration/test_runtime_schema_contract.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
- `./.venv/bin/ruff check apps/api/app/db/models/runtime/flow.py apps/api/app/db/models/runtime/assignment.py apps/api/app/db/models/runtime/dispatch.py apps/api/app/db/models/runtime/shared.py apps/api/app/runtime/control/boundary.py apps/api/app/runtime/control/flows.py apps/api/app/runtime/control/release.py apps/api/app/runtime/projection/materialize.py apps/api/app/runtime/replan/service.py apps/api/app/schemas/runtime/parent_tools.py apps/api/app/api/errors.py apps/api/app/runtime/control/observability.py apps/api/tests/integration/test_runtime_schema_contract.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
- `./.venv/bin/mypy apps/api/app/db/models/runtime/flow.py apps/api/app/db/models/runtime/assignment.py apps/api/app/db/models/runtime/dispatch.py apps/api/app/db/models/runtime/shared.py apps/api/app/runtime/control/boundary.py apps/api/app/runtime/control/flows.py apps/api/app/runtime/control/release.py apps/api/app/runtime/projection/materialize.py apps/api/app/runtime/replan/service.py apps/api/app/schemas/runtime/parent_tools.py apps/api/app/api/errors.py apps/api/app/runtime/control/observability.py apps/api/tests/integration/test_runtime_schema_contract.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
- `make pyright-api`
- `./.venv/bin/python scripts/docs/docs_freeze_validate.py`
- minimal workflow proof: `./.venv/bin/pytest -q apps/api/tests/integration/test_phase3_runtime_db.py::test_phase3_minimal_root_closure_remains_readable`
- normal workflow proof: `./.venv/bin/pytest -q apps/api/tests/integration/test_phase3_runtime_db.py::test_phase3_parent_worker_flow_and_replan_state`
- focused Phase 3 suite: `./.venv/bin/pytest -q apps/api/tests/integration/test_runtime_schema_contract.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py apps/api/tests/integration/test_phase3_runtime_db.py`
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
