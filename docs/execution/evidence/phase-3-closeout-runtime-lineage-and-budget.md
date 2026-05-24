# Phase 3 Local-Tool-First Runtime, Closure, And Replan Evidence

Status: Reference

selected phase: Phase 3
current phase page: docs/execution/phases/phase-3-runtime-parent-review-and-replan.md
selected work packages: P3-WP1, P3-WP2, P3-WP3
summary-only: no
delegated slices: listed
slice id: phase3-current-surface-and-launch-readability
slice type: edit
owned surfaces: apps/api/app/runtime/control/assignment/**, apps/api/app/runtime/control/boundary/**, apps/api/app/runtime/control/release/**, apps/api/app/runtime/control/observability.py, apps/api/app/runtime/effects/validation.py, apps/api/app/runtime/launch/**, apps/api/app/runtime/task_root/**, apps/api/tests/integration/phase3/contracts/**, apps/api/tests/integration/phase3/db/**, apps/api/tests/integration/runtime_schema_contract/**, apps/api/tests/e2e/phase3/normal_lane/**
touched surfaces: apps/api/app/runtime/control/assignment/staging.py, apps/api/app/runtime/control/boundary/release_descendant_refs.py, apps/api/app/runtime/control/boundary/transitions.py, apps/api/app/runtime/control/observability.py, apps/api/app/runtime/control/release/basis.py, apps/api/app/runtime/control/release/preconditions.py, apps/api/app/runtime/effects/validation.py, apps/api/app/runtime/launch/service.py, apps/api/app/runtime/launch/persistence/runtime.py, apps/api/app/runtime/task_root/reads.py, apps/api/tests/integration/phase3/contracts/test_assignment_pending_materialization_cases.py, apps/api/tests/integration/phase3/contracts/test_release_pending_projection_cases.py, apps/api/tests/integration/phase3/routes/test_surface_contract.py, apps/api/tests/integration/phase3/db/test_checkpoint_cases.py, apps/api/tests/integration/phase3/db/test_release_root_cases.py, apps/api/tests/e2e/phase3/normal_lane/flow.py
slice id: phase3-handoff-and-failure-family
slice type: edit
owned surfaces: apps/api/app/api/runtime_exception_mapping.py, apps/api/app/runtime/control/dispatch/opening.py, apps/api/app/runtime/projection/manifest/**, apps/api/app/runtime/projection/attempt_materialization.py, apps/api/app/runtime/projection/dispatch/materialization.py, apps/api/app/runtime/launch/bootstrap/projection.py, apps/api/tests/integration/phase2/bootstrap/**, apps/api/tests/integration/phase3/contracts/**
touched surfaces: apps/api/app/api/runtime_exception_mapping.py, apps/api/app/runtime/control/dispatch/opening.py, apps/api/app/runtime/projection/manifest/checkpoint_handoff.py, apps/api/app/runtime/projection/manifest/context.py, apps/api/app/runtime/projection/manifest/current_context_queries.py, apps/api/app/runtime/projection/attempt_materialization.py, apps/api/app/runtime/projection/dispatch/materialization.py, apps/api/app/runtime/launch/bootstrap/projection.py, apps/api/tests/integration/phase2/bootstrap/test_manifest.py, apps/api/tests/integration/phase2/bootstrap/test_manifest_checkpoint_handoff.py, apps/api/tests/integration/phase3/contracts/, apps/api/tests/integration/phase3/contracts/test_failure_mapping_cases.py, apps/api/tests/integration/phase3/contracts/test_parent_checkpoint_handoff_cases.py
slice id: phase3-structural-manifest-and-thin-route
slice type: edit
owned surfaces: apps/api/app/api/routes/callback.py, apps/api/app/runtime/control/parent_tools.py, apps/api/app/runtime/effects/cases.py, apps/api/app/runtime/effects/worker.py, apps/api/app/runtime/projection/__init__.py, apps/api/tests/integration/phase3/contracts/test_structural_manifest_cases.py, apps/api/tests/integration/phase3/routes/test_surface_contract.py
touched surfaces: apps/api/app/api/routes/callback.py, apps/api/app/runtime/control/parent_tools.py, apps/api/app/runtime/effects/cases.py, apps/api/app/runtime/effects/worker.py, apps/api/app/runtime/projection/__init__.py, apps/api/tests/integration/phase3/contracts/test_structural_manifest_cases.py, apps/api/tests/integration/phase3/routes/test_surface_contract.py
slice id: phase3-current-doc-and-closeout-refresh
slice type: edit
owned surfaces: docs/current/architecture/runtime-control-plane.md, docs/current/interfaces/api-trust-lanes.md, docs/current/interfaces/api-surface-and-route-map.md, docs/current/architecture/runtime-read-models-and-operator-surfaces.md, docs/current/architecture/manifest-projection-and-acknowledgement.md, docs/current/interfaces/prompt-layer-and-worker-delivery.md, docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md
touched surfaces: docs/current/architecture/runtime-control-plane.md, docs/current/interfaces/api-trust-lanes.md, docs/current/interfaces/api-surface-and-route-map.md, docs/current/architecture/runtime-read-models-and-operator-surfaces.md, docs/current/architecture/manifest-projection-and-acknowledgement.md, docs/current/interfaces/prompt-layer-and-worker-delivery.md, docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md

## Slice identity

- selected phase: Phase 3
- approved work packages served by this evidence chain: `P3-WP1`, `P3-WP2`, and `P3-WP3`
- closure follow-through in this evidence refresh: current-doc repair plus authoritative proof refresh after the merged runtime slices landed
- date: 2026-05-13
- owned surface: `docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md`

## Plan and review links

- approved plan: `../plans/phase-3-closeout-runtime-lineage-and-budget.md`
- mandatory review: `../reviews/phase-3-closeout-runtime-lineage-and-budget.md`
- review artifact: `../reviews/phase-3-closeout-runtime-lineage-and-budget.md`

## Authoritative evidence rule

- this file is the authoritative `summary-only: no` Phase 3 closeout evidence record
- it records fresh proof for the merged Phase 3 runtime, launch, handoff, structural-sync, current-doc, SQLite, reset, Postgres, typing, and representative pytest lanes
- it does not claim Phase 4 gateway, watchdog, plugin, or support-state work

## Artifacts changed

- runtime control and validation surfaces under: `apps/api/app/runtime/control/**`, `apps/api/app/runtime/effects/validation.py`, `apps/api/app/runtime/launch/**`, and `apps/api/app/runtime/task_root/**`
- checkpoint-handoff and failure-family surfaces under: `apps/api/app/api/runtime_exception_mapping.py`, `apps/api/app/runtime/control/dispatch/opening.py`, and `apps/api/app/runtime/projection/**`
- structural manifest timing and thin-route surfaces under: `apps/api/app/api/routes/callback.py`, `apps/api/app/runtime/effects/cases.py`, `apps/api/app/runtime/control/parent_tools.py`, `apps/api/app/runtime/effects/worker.py`, and `apps/api/app/runtime/projection/__init__.py`
- merged Phase 3 proof tests under: `apps/api/tests/integration/phase3/**`, `apps/api/tests/integration/runtime_schema_contract/**`, and `apps/api/tests/e2e/phase3/normal_lane/**`
- truthful current-doc surfaces under: `docs/current/architecture/runtime-control-plane.md`, `docs/current/interfaces/api-trust-lanes.md`, `docs/current/interfaces/api-surface-and-route-map.md`, `docs/current/architecture/runtime-read-models-and-operator-surfaces.md`, `docs/current/architecture/manifest-projection-and-acknowledgement.md`, and `docs/current/interfaces/prompt-layer-and-worker-delivery.md`

## Merged Phase 3 changes captured by this evidence

- current-surface validation no longer treats delayed or missing projection work as readable current evidence for criteria, checkpoints, or artifacts
- launch now commits controller truth and then materializes the stable root manifest plus root attempt files inline before return
- parent `yield` and closed-dispatch stable-manifest rereads now carry the controller-selected checkpoint handoff instead of inferring it from surfaced checkpoint order
- staged-child continuation failures now normalize to the same semantic family, and owned launch/materialization paths now raise typed runtime failures instead of raw semantic `ValueError`
- structural callback-tool manifest reread timing now lives in the control-side commit/rollback path rather than in callback route-local orchestration
- current docs now describe the live timing, handoff, and pure-read behavior truthfully without overclaiming later-phase work

## Proof run for this rebuild

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli validate`
  - result: `Docs freeze validation passed.`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
  - result: `No findings.` The report also recorded zero sibling-prefix layout families, zero cross-module private-helper imports, zero file-size threshold violations, and zero function-size threshold violations.
- exact repo search:
  - `rg -n "from .* import _|import .*\\._" apps/api/app/api/runtime_exception_mapping.py apps/api/app/api/routes/callback.py apps/api/app/runtime/control apps/api/app/runtime/effects apps/api/app/runtime/launch apps/api/app/runtime/projection apps/api/app/runtime/task_root apps/api/tests/integration/phase2/bootstrap apps/api/tests/integration/phase3 apps/api/tests/integration/runtime_schema_contract apps/api/tests/e2e/phase3/normal_lane`
  - result: no matches; `rg` exited with status `1`, which is the expected no-match result for this private-symbol and underscore-private import search
- `./.venv/bin/ruff check apps/api/app/api/runtime_exception_mapping.py apps/api/app/api/routes/callback.py apps/api/app/runtime/control apps/api/app/runtime/effects apps/api/app/runtime/launch apps/api/app/runtime/projection apps/api/app/runtime/task_root apps/api/tests/integration/phase2/bootstrap apps/api/tests/integration/phase3 apps/api/tests/integration/runtime_schema_contract apps/api/tests/e2e/phase3/normal_lane`
  - result: `All checks passed!`
- `./.venv/bin/mypy apps/api/app/api/runtime_exception_mapping.py apps/api/app/api/routes/callback.py apps/api/app/runtime/control apps/api/app/runtime/effects apps/api/app/runtime/launch apps/api/app/runtime/projection apps/api/app/runtime/task_root apps/api/tests/integration/phase2/bootstrap apps/api/tests/integration/phase3 apps/api/tests/integration/runtime_schema_contract`
  - result: `Success: no issues found in 125 source files`
- `make pyright-api`
  - result: `0 errors, 0 warnings, 0 informations`
- `./.venv/bin/pytest -q apps/api/tests/unit/test_cli.py -k 'packaged_seed_definitions_are_available or init_writes_minimal_config_and_db_file or db_reset_recreates_sqlite_database or db_upgrade_bootstraps_seeded_sqlite_database_on_shipped_path'`
  - result: `4 passed, 3 deselected in 8.52s`
- `make test-api-db`
  - result: `262 passed in 666.45s (0:11:06)`
- `./.venv/bin/pytest -q apps/api/tests/integration/phase3 apps/api/tests/integration/runtime_schema_contract apps/api/tests/e2e/phase3/normal_lane`
  - result: `105 passed in 729.09s (0:12:09)`
- `make docker-down`
  - result: passed; the temporary Postgres verification stack was stopped and removed after the strong-lane run

## Current-doc repair captured by this evidence

- `docs/current/architecture/runtime-control-plane.md` now states that launch returns only after the stable root manifest and root attempt files are readable and that the taught task-root reread surfaces are written before route success
- `docs/current/architecture/manifest-projection-and-acknowledgement.md` now states that closed-dispatch stable-manifest rereads reuse the most recent controller-selected checkpoint handoff for the same attempt and that the stable manifest is rewritten through synchronous post-commit writers
- `docs/current/interfaces/api-trust-lanes.md` and `docs/current/interfaces/api-surface-and-route-map.md` now describe the callback route as thin and attribute the structural reread guarantee to the control-side commit/rollback path
- `docs/current/architecture/runtime-read-models-and-operator-surfaces.md` now makes the pure-reread, no-rematerialize GET behavior explicit
- `docs/current/interfaces/prompt-layer-and-worker-delivery.md` now states that stable-manifest renders without an open dispatch still reuse the most recent controller-selected handoff for the same attempt

## Residual blockers

- none
