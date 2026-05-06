# Phase 3 Runtime Contract and Control Repair Evidence

Status: Reference

## Slice identity

- selected phase: Phase 3
- work package or slice: `P3-WP3` authoritative artifact refresh for stale-basis conflicts, relational direct-child authority, drain-window visible-dispatch semantics, and final proof closeout
- date: 2026-05-06

## Plan link

- approved plan: `../plans/phase-3-runtime-contract-and-control-repair.md`

## Delegated slice return log

- historical Phase 3 implementation returns retained for this refresh:
  - `P3-WP1` runtime record and foreground control-state repair
    - slice type: `edit`
    - returned evidence retained:
      - stale assignment and stale checkpoint evidence families now map to
        `409`
      - replacement dispatch and cancel keep visible-dispatch truth until the
        drain-window inactivity proof completes
      - same-session root `release_blocked` remains a terminal precondition,
        not a continuation outcome
    - parent ownership-boundary check result: passed
  - `P3-WP2` parent review, closure, and read-surface alignment
    - slice type: `edit`
    - returned evidence retained:
      - read surfaces now align cancel and yield wording with
        drain-window visible-dispatch semantics
      - stale checkpoint-only closure wording is no longer carried as Phase 3
        truth
      - semantic missing dependency/provider/current artifact/file-missing
        failures remain explicit `422` lanes while missing ids/entities remain
        explicit `404` lanes
    - parent ownership-boundary check result: passed
  - `P3-WP3` parent-owned structural replan and direct-child authority
    - slice type: `edit`
    - returned evidence retained:
      - relational ids now drive direct-child decisions and structural replan
      - `parent_node_key` and `child_node_keys_json` remain synchronized
        compatibility mirrors only
      - `provider-events.ndjson` remains a normalized observability export and
        is not authoritative controller truth
    - parent ownership-boundary check result: passed
  - historical review-only audit coverage
    - slice type: `review-only`
    - returned evidence retained:
      - the missing inactivity-proof/cancel-to-fenced foreground path was
        surfaced before closure
      - stale artifact wording was identified before the authoritative refresh
    - parent ownership-boundary check result: passed; no file edits returned

- authoritative artifact refresh follow-up on 2026-05-06:
  - `no subagents`; this slice stayed inside:
    - `docs/execution/plans/phase-3-runtime-contract-and-control-repair.md`
    - `docs/execution/evidence/phase-3-runtime-contract-and-control-repair.md`
    - `docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md`
  - stale wording removed in this refresh:
    - stale higher-numbered Phase 3 work-package ids
    - any stale docs-freeze rerun wording
    - any parent-rerun-pending wording
    - any wording that elevated `provider-events.ndjson` into controller
      authority
  - current truth recorded in this refresh:
    - stale assignment/checkpoint evidence lane: `409`
    - direct-child authority: relational ids
    - drain-window visible-dispatch semantics: aligned across the owned read
      surfaces
    - runtime schema contract lane: `8 passed`
    - focused Phase 3 bundle: `55 passed`
    - `make pyright-api`: `0 errors, 0 warnings, 0 informations`
    - `make test-api-db`: `152 passed`

## Parent integration and validation log

- this artifact-only refresh did not edit current docs, scripts, app code,
  tests, or Phase 1/2 artifacts
- the parent preserved the owned-surface boundary and rewrote only the three
  owned Phase 3 artifact files
- the parent normalized the plan/evidence/review wording to the real
  `P3-WP1` through `P3-WP3` work-package set and the current proof values
- the parent then completed a read-only sanity pass on the owned files only

## Commands run

- read-only sanity command:
  - `rg -n 'P3-WP(4|5|6|7)|docs[_]freeze_validate|pending parent .* rerun|must .* rerun' docs/execution/plans/phase-3-runtime-contract-and-control-repair.md docs/execution/evidence/phase-3-runtime-contract-and-control-repair.md docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md`
  - outcome: no matches
- read-only sanity command:
  - `rg -n 'P3-WP1|P3-WP2|P3-WP3|409|relational|direct-child|drain-window|visible-dispatch|not authoritative|8 passed|55 passed|0 errors|152 passed' docs/execution/plans/phase-3-runtime-contract-and-control-repair.md docs/execution/evidence/phase-3-runtime-contract-and-control-repair.md docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md`
  - outcome: expected current-truth labels and proof values are present in the owned files
- read-only sanity command:
  - `sed -n '1,220p' docs/execution/plans/phase-3-runtime-contract-and-control-repair.md`
  - outcome: readback completed
- read-only sanity command:
  - `sed -n '1,220p' docs/execution/evidence/phase-3-runtime-contract-and-control-repair.md`
  - outcome: readback completed
- read-only sanity command:
  - `sed -n '1,220p' docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md`
  - outcome: readback completed

## Retained proof values

- runtime schema contract lane:
  - `./.venv/bin/pytest -q apps/api/tests/integration/test_runtime_schema_contract.py`
  - recorded current outcome: `8 passed`
- focused Phase 3 bundle:
  - `./.venv/bin/pytest -q apps/api/tests/integration/test_runtime_schema_contract.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py apps/api/tests/integration/test_phase3_runtime_db.py`
  - recorded current outcome: `55 passed`
- minimal + normal workflow lane:
  - `./.venv/bin/pytest -q apps/api/tests/integration/test_phase3_runtime_db.py::test_phase3_minimal_root_closure_remains_readable apps/api/tests/integration/test_phase3_runtime_db.py::test_phase3_parent_worker_flow_and_replan_state`
  - recorded current outcome: `2 passed`
- SQLite shipped-path proof:
  - `./.venv/bin/pytest -q apps/api/tests/unit/test_cli.py::test_init_writes_minimal_config_and_db_file apps/api/tests/unit/test_cli.py::test_db_upgrade_bootstraps_seeded_sqlite_database_on_shipped_path apps/api/tests/unit/test_cli.py::test_db_reset_recreates_sqlite_database`
  - recorded current outcome: `3 passed`
- docs-freeze validator:
  - `./.venv/bin/python scripts/docs/docs_freeze_validate.py`
  - recorded current outcome: `Docs freeze validation passed.`
- language gate:
  - `make pyright-api`
  - recorded current outcome: `0 errors, 0 warnings, 0 informations`
- Postgres or Docker strong verification:
  - `make test-api-db`
  - recorded current outcome: `152 passed`

## Gate and validator summary

- this artifact-only refresh ran read-only sanity on the owned files only
- docs-freeze validator rerun is now explicitly recorded as passed in this
  Phase 3 closeout wording
- the authoritative retained proof values now record:
  - runtime schema contract lane: `8 passed`
  - focused Phase 3 bundle: `55 passed`
  - `docs_freeze_validate.py`: passed
  - `make pyright-api`: `0 errors`
  - `make test-api-db`: `152 passed`

## Test lanes

- runtime schema contract: `8 passed`
- focused Phase 3 bundle: `55 passed`
- minimal + normal workflow lane: `2 passed`
- SQLite shipped-path proof: `3 passed`
- docs-freeze validator: passed
- Postgres or Docker strong verification: `152 passed`

## Artifacts

- `docs/execution/plans/phase-3-runtime-contract-and-control-repair.md`
- `docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md`

## Blockers

- none for this 2026-05-06 Phase 3 artifact refresh
- no code-side or current-doc blocker was required to make the owned artifacts
  truthful on the current tree

## Review link

- review artifact: `../reviews/phase-3-runtime-contract-and-control-repair.md`
