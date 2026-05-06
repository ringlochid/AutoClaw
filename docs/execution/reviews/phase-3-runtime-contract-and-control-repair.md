# Phase 3 Runtime Contract and Control Repair Review

Status: Reference

## Slice identity

- selected phase: Phase 3
- work package or slice: `P3-WP3` authoritative artifact refresh for stale-basis conflicts, relational direct-child authority, drain-window visible-dispatch semantics, and final proof closeout
- date: 2026-05-06

## Phase-local contract

- current phase page: `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
- implementation file lock map: `docs/execution/maps/file-priority-map.md`

## Scope

- reviewed plan: `../plans/phase-3-runtime-contract-and-control-repair.md`
- reviewed evidence: `../evidence/phase-3-runtime-contract-and-control-repair.md`

## Verdict

- pass/fail: pass
- summary: the authoritative Phase 3 artifacts now use only `P3-WP1` through
  `P3-WP3`, record the current proof values exactly, and stop treating
  `provider-events.ndjson` or stale rerun prose as controller truth.

## Findings

- stale assignment and stale checkpoint evidence is now recorded on the `409`
  conflict lane, while semantic `422` and missing-id `404` behavior stays
  explicit
- direct-child authority is now recorded as relational-id authority; shadow
  `parent_node_key` and `child_node_keys_json` values remain mirrors only
- drain-window visible-dispatch semantics now align across the owned
  plan/evidence/review read surfaces
- `provider-events.ndjson` is now described as a normalized observability
  export, not authoritative controller truth
- the retained proof lanes now record the current values exactly:
  - runtime schema contract lane: `8 passed`
  - focused Phase 3 bundle: `55 passed`
  - `make pyright-api`: `0 errors`
  - `make test-api-db`: `152 passed`
- no stale higher-numbered Phase 3 work-package ids or docs-freeze rerun
  wording remains in the owned artifacts

## Delegated-slice compliance

- `no subagents` or delegated-slice summary:
  - the historical Phase 3 implementation waves remain retained in evidence
  - this 2026-05-06 authoritative artifact refresh used `no subagents`
- owned-surface compliance:
  - this refresh stayed inside the three owned Phase 3 artifact files only
- review-only compliance:
  - not applicable for this refresh; no review-only slice ran
- wave integration proof:
  - the parent performed a read-only sanity pass on the owned files after the
    rewrite
- authoritative proof link:
  - `../evidence/phase-3-runtime-contract-and-control-repair.md`

## Proof lanes relied on

- retained proof lane:
  - `./.venv/bin/pytest -q apps/api/tests/integration/test_runtime_schema_contract.py`
  - recorded current outcome: `8 passed`
- retained proof lane:
  - `./.venv/bin/pytest -q apps/api/tests/integration/test_runtime_schema_contract.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py apps/api/tests/integration/test_phase3_runtime_db.py`
  - recorded current outcome: `55 passed`
- retained proof lane:
  - `./.venv/bin/pytest -q apps/api/tests/integration/test_phase3_runtime_db.py::test_phase3_minimal_root_closure_remains_readable apps/api/tests/integration/test_phase3_runtime_db.py::test_phase3_parent_worker_flow_and_replan_state`
  - recorded current outcome: `2 passed`
- retained proof lane:
  - `./.venv/bin/pytest -q apps/api/tests/unit/test_cli.py::test_init_writes_minimal_config_and_db_file apps/api/tests/unit/test_cli.py::test_db_upgrade_bootstraps_seeded_sqlite_database_on_shipped_path apps/api/tests/unit/test_cli.py::test_db_reset_recreates_sqlite_database`
  - recorded current outcome: `3 passed`
- retained proof lane:
  - `./.venv/bin/python scripts/docs/docs_freeze_validate.py`
  - recorded current outcome: `Docs freeze validation passed.`
- retained proof lane:
  - `make pyright-api`
  - recorded current outcome: `0 errors, 0 warnings, 0 informations`
- retained proof lane:
  - `make test-api-db`
  - recorded current outcome: `152 passed`

## Stale-logic search proof

- commands or search terms:
  - `rg -n 'P3-WP(4|5|6|7)|docs[_]freeze_validate|pending parent .* rerun|must .* rerun' docs/execution/plans/phase-3-runtime-contract-and-control-repair.md docs/execution/evidence/phase-3-runtime-contract-and-control-repair.md docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md`
  - search for wording that elevates `provider-events.ndjson` into controller authority in the three owned artifacts
- outcome:
  - no stale Phase 3 work-package ids remain
  - no stale rerun wording remains
  - no authoritative `provider-events.ndjson` wording remains

## Kill-list proof

- checked for `attempt identity detached from assignment identity`, `review treated as an external gate`, `structural replan adopted outside parent authority`, and `runtime truth split across both Phase 2 and Phase 3`
- outcome: the authoritative Phase 3 artifacts now describe controller-owned runtime truth, parent-owned replan, and dispatch/assignment lineage without reintroducing those kill-list terms as live behavior

## Docs answer-sourcing proof

- redesign owner relied on:
  - `docs/redesign/architecture/runtime-observability-and-boundary-log.md`
- execution canon relied on:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs/execution/README.md`
  - `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
  - `docs/execution/maps/file-priority-map.md`
- owned artifacts read back:
  - `docs/execution/plans/phase-3-runtime-contract-and-control-repair.md`
  - `docs/execution/evidence/phase-3-runtime-contract-and-control-repair.md`
  - `docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md`
- canon gap or explicit `none`:
  - none

## Phase-bounded STYLE exceptions

### `apps/api/app/runtime/launch/persistence.py`

- phase-bounded reason: the file still exceeds the `>600` line no-growth threshold while launch, registry-pinning, lease, and bootstrap persistence remain concentrated in one ownership path
- authoritative exception home: this Phase 3 review

### `apps/api/tests/integration/test_phase3_runtime_db.py`

- phase-bounded reason: the file still exceeds the `>600` line no-growth threshold while multiple runtime DB regression lanes remain concentrated in one integration suite
- authoritative exception home: this Phase 3 review

## Reset-gate outcome

- not rerun by this artifact-only refresh:
  - the retained current proof values already recorded in evidence include
    SQLite shipped-path proof at `3 passed`, docs-freeze validation passed, and
    Postgres/Docker strong verification at `152 passed`

## Remaining exact blockers

- none for this 2026-05-06 Phase 3 artifact refresh
- no stop condition fired; the owned artifacts were made truthful without
  widening into current docs or code/test surfaces

## Cross-links

- aggregate historical summary, if any:
  - `./phase-0-3-closeout.md`
- companion exceptions page, if any:
  - `./phase-0-3-closeout-review-exceptions.md`
