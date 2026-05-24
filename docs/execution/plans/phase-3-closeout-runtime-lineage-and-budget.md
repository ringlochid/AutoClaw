# Phase 3 Local-Tool-First Runtime, Closure, And Replan Plan

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
- approved execution brief for `P3-WP1`, `P3-WP2`, and `P3-WP3`
- current-doc repair and authoritative record normalization for the merged Phase 3 runtime slice set
- date: 2026-05-13

## Phase-local contract

- current phase page: `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
- implementation file lock map: `docs/execution/maps/file-priority-map.md`
- landing map rows used for answer-sourcing and proof routing: `runtime records, currentness, and projections` and `parent verification, review, closure, and replan`

## Objective

- keep this triplet as the authoritative `summary-only: no` Phase 3 plan/evidence/review chain for the merged runtime work
- record the actual landed Phase 3 repairs:
  - current-surface validation now requires readable checkpoint, criteria, and artifact projections instead of queue-era delayed projection assumptions
  - bootstrap launch now returns only after the stable root manifest and root attempt files are readable
  - redispatch checkpoint handoff now stays controller-selected even when no dispatch is open
  - structural and ordinary task-root reread timing now lives in synchronous post-commit case functions rather than in a generic queue or route-local workaround
  - current docs now describe the shipped timing, handoff, and readback behavior truthfully
- rerun and record the strong proof lanes required by the phase page, the mandatory review gate, and the reset gate

## Scope and truth constraints

- owned edit surfaces for this slice:
  - `docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md`
  - `docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md`
  - `docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md`
  - `docs/current/architecture/runtime-control-plane.md`
  - `docs/current/interfaces/api-trust-lanes.md`
  - `docs/current/interfaces/api-surface-and-route-map.md`
  - `docs/current/architecture/runtime-read-models-and-operator-surfaces.md`
  - narrow collateral current docs: `docs/current/architecture/manifest-projection-and-acknowledgement.md` and `docs/current/interfaces/prompt-layer-and-worker-delivery.md`
- landed Phase 3 code and test surfaces that this chain must describe truthfully:
  - runtime control, effects, projection, launch, and task-root surfaces under `apps/api/app/runtime/**`
  - runtime presenters and callback route surfaces under `apps/api/app/api/**`
  - merged proof under `apps/api/tests/integration/phase3/**`, `apps/api/tests/integration/runtime_schema_contract/**`, and `apps/api/tests/e2e/phase3/normal_lane/**`
- do not claim:
  - Phase 4 gateway, watchdog, or support-state work
  - prompt-layer owner-doc changes outside the allowed current docs
  - a route-local structural manifest workaround that no longer ships
  - a no-open-dispatch checkpoint-order fallback that no longer ships

## Delegated slice briefs

### phase3-current-surface-and-launch-readability

- do-not-edit surfaces:
  - callback route orchestration under `apps/api/app/api/routes/**`
  - prompt-layer owner docs under `docs/redesign/prompt-layer/**`
  - execution artifacts outside the selected Phase 3 triplet
- required reads:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs/execution/README.md`
  - `docs/execution/maps/file-priority-map.md`
  - `docs/execution/maps/redesign-code-landing-map.md`
  - `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
  - `docs/execution/gates/mandatory-review-gate.md`
  - `docs/execution/gates/reset-gate.md`
  - `docs/execution/gates/code-quality-gate.md`
  - `docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md`
  - `docs/redesign/architecture/runtime-database-and-object-contract.md`
  - `docs/redesign/architecture/runtime-records-and-lifecycle.md`
  - `docs/redesign/architecture/checkpoint-contract.md`
  - `docs/redesign/workflows/parent-root-release-and-closure.md`
  - `docs/current/architecture/runtime-control-plane.md`
  - `docs/current/architecture/runtime-read-models-and-operator-surfaces.md`
  - the live runtime surfaces under `apps/api/app/runtime/control/**`, `apps/api/app/runtime/effects/validation.py`, `apps/api/app/runtime/launch/**`, and `apps/api/app/runtime/task_root/**`
- required tests/validators:
  - `./.venv/bin/ruff check apps/api/app/runtime/control apps/api/app/runtime/effects apps/api/app/runtime/launch apps/api/app/runtime/task_root apps/api/tests/integration/phase3 apps/api/tests/integration/runtime_schema_contract apps/api/tests/e2e/phase3/normal_lane`
  - `./.venv/bin/mypy apps/api/app/runtime/control apps/api/app/runtime/effects apps/api/app/runtime/launch apps/api/app/runtime/task_root apps/api/tests/integration/phase3 apps/api/tests/integration/runtime_schema_contract`
  - `./.venv/bin/pytest -q apps/api/tests/integration/phase3/contracts/test_assignment_pending_materialization_cases.py apps/api/tests/integration/phase3/contracts/test_release_pending_projection_cases.py apps/api/tests/integration/phase3/routes/test_surface_contract.py apps/api/tests/integration/phase3/db/test_checkpoint_cases.py apps/api/tests/integration/phase3/db/test_release_root_cases.py`
- expected outputs:
  - current-surface validation rejects missing readable evidence even when follow-up effects are queued
  - bootstrap launch reread surfaces are readable before return
  - task-scoped GET/read surfaces stay pure rereads
- dependencies:
  - Phase 2 complete
- evidence to return:
  - changed runtime/test inventory
  - command results for the current-surface and launch-readability lanes
- parent-owned decisions:
  - whether any remaining unreadable-after-return behavior is Phase 3-owned runtime truth or a later-phase external-lane concern
- stop conditions:
  - stop if the truthful fix requires gateway/session continuity, watchdog, or prompt-owner changes outside the Phase 3 lock

### phase3-handoff-and-failure-family

- do-not-edit surfaces:
  - route orchestration outside the specific callback/runtime failure translation surfaces
  - current docs and execution artifacts
- required reads:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs/execution/README.md`
  - `docs/execution/maps/file-priority-map.md`
  - `docs/execution/maps/redesign-code-landing-map.md`
  - `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
  - `docs/redesign/architecture/checkpoint-contract.md`
  - `docs/redesign/architecture/worker-context-contract.md`
  - `docs/redesign/prompt-layer/source-and-sections.md`
  - `docs/redesign/workflows/parent-review-and-replan.md`
  - `docs/redesign/workflows/parent-root-release-and-closure.md`
  - `docs/redesign/prompt-layer/prompt-pack/validation-and-reject-blocks.md`
  - the live handoff/failure surfaces under `apps/api/app/runtime/control/dispatch/opening.py`, `apps/api/app/runtime/projection/manifest/**`, `apps/api/app/runtime/projection/attempt_materialization.py`, `apps/api/app/runtime/projection/dispatch/materialization.py`, `apps/api/app/runtime/launch/bootstrap/projection.py`, and `apps/api/app/api/runtime_exception_mapping.py`
- required tests/validators:
  - `./.venv/bin/ruff check apps/api/app/api/runtime_exception_mapping.py apps/api/app/runtime/control/dispatch/opening.py apps/api/app/runtime/projection apps/api/app/runtime/launch/bootstrap apps/api/tests/integration/phase2/bootstrap apps/api/tests/integration/phase3/contracts`
  - `./.venv/bin/mypy apps/api/app/api/runtime_exception_mapping.py apps/api/app/runtime/control/dispatch/opening.py apps/api/app/runtime/projection apps/api/app/runtime/launch/bootstrap apps/api/tests/integration/phase2/bootstrap`
  - `./.venv/bin/pytest -q apps/api/tests/integration/phase2/bootstrap/test_manifest.py apps/api/tests/integration/phase2/bootstrap/test_manifest_checkpoint_handoff.py apps/api/tests/integration/phase3/contracts/ apps/api/tests/integration/phase3/contracts/test_failure_mapping_cases.py apps/api/tests/integration/phase3/contracts/test_parent_checkpoint_handoff_cases.py`
- expected outputs:
  - child redispatch handoff stays controller-selected for both open-dispatch and closed-dispatch manifest builds
  - staged-child and similar continuation failures map to one semantic family
  - owned launch/materialization paths use typed runtime failures instead of raw semantic `ValueError`
- dependencies:
  - `P3-WP1`
- evidence to return:
  - changed handoff/failure surface inventory
  - command results for the checkpoint-handoff and failure-contract lanes
- parent-owned decisions:
  - whether a remaining reject-family mismatch belongs to Phase 3 runtime failures or later external-lane HTTP translation
- stop conditions:
  - stop if the truthful fix requires prompt-owner or Phase 4 continuity changes outside the Phase 3 lock

### phase3-structural-manifest-and-thin-route

- do-not-edit surfaces:
  - broader runtime current-doc surfaces
  - prompt-layer owner docs
  - package/install surfaces outside the existing shipped path
- required reads:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs/execution/README.md`
  - `docs/execution/maps/file-priority-map.md`
  - `docs/execution/maps/redesign-code-landing-map.md`
  - `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
  - `docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md`
  - `docs/redesign/workflows/runtime-structural-replan.md`
  - `docs/current/interfaces/api-trust-lanes.md`
  - `docs/current/architecture/manifest-projection-and-acknowledgement.md`
  - the live structural-manifest surfaces under `apps/api/app/api/routes/callback.py`, `apps/api/app/runtime/control/parent_tools.py`, `apps/api/app/runtime/effects/cases.py`, `apps/api/app/runtime/effects/worker.py`, and `apps/api/app/runtime/projection/__init__.py`
- required tests/validators:
  - `./.venv/bin/ruff check apps/api/app/api/routes/callback.py apps/api/app/runtime/control/parent_tools.py apps/api/app/runtime/effects/cases.py apps/api/app/runtime/effects/worker.py apps/api/app/runtime/projection/__init__.py apps/api/tests/integration/phase3/contracts/test_structural_manifest_cases.py apps/api/tests/integration/phase3/routes/test_surface_contract.py`
  - `./.venv/bin/mypy apps/api/app/api/routes/callback.py apps/api/app/runtime/control/parent_tools.py apps/api/app/runtime/effects/cases.py apps/api/app/runtime/effects/worker.py`
  - `./.venv/bin/pytest -q apps/api/tests/integration/phase3/contracts/test_structural_manifest_cases.py apps/api/tests/integration/phase3/routes/test_surface_contract.py`
- expected outputs:
  - callback route stays thin
  - structural stable-manifest reread timing lives in control-side commit/rollback helpers
  - remaining eager projection-barrel usage on the touched Phase 3 path is gone
- dependencies:
  - `P3-WP1`, `P3-WP2`
- evidence to return:
  - changed route/control/effect surface inventory
  - command results for the structural-manifest and callback-route proof
- parent-owned decisions:
  - whether any remaining orchestration wording belongs in current docs or in a later-phase API surface rewrite
- stop conditions:
  - stop if the truthful fix requires reopening prompt-owner docs or widening into Phase 4 watchdog/plugin ownership

### phase3-current-doc-and-closeout-refresh

- do-not-edit surfaces:
  - runtime code
  - `scripts/docs/**`
  - prompt-layer owner docs
  - non-current docs outside the owned and allowed collateral surfaces
- required reads:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs/execution/README.md`
  - `docs/execution/maps/file-priority-map.md`
  - `docs/execution/maps/redesign-code-landing-map.md`
  - `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
  - `docs/execution/gates/mandatory-review-gate.md`
  - `docs/execution/gates/reset-gate.md`
  - `docs/execution/gates/code-quality-gate.md`
  - the current Phase 3 plan, evidence, and review
  - `docs/current/architecture/runtime-control-plane.md`
  - `docs/current/interfaces/api-trust-lanes.md`
  - `docs/current/interfaces/api-surface-and-route-map.md`
  - `docs/current/architecture/runtime-read-models-and-operator-surfaces.md`
  - `docs/current/architecture/manifest-projection-and-acknowledgement.md`
  - `docs/current/interfaces/prompt-layer-and-worker-delivery.md`
  - `docs/current/operations/run-docker-postgres-verification.md`
  - the merged runtime behavior in `apps/api/app/runtime/effects/**`, `apps/api/app/runtime/control/**`, `apps/api/app/runtime/projection/**`, `apps/api/app/runtime/task_root/**`, `apps/api/app/runtime/launch/**`, and `apps/api/app/api/routes/callback.py`
- required tests/validators:
  - `./.venv/bin/python -m scripts.docs.docs_freeze.cli validate`
  - `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
  - exact repo search for underscore-private imports across the touched Phase 3 code paths
  - `make pyright-api`
  - shipped-path SQLite init/upgrade/reset proof subset
  - `make test-api-db`
  - a representative merged Phase 3 pytest batch
- expected outputs:
  - validator-compliant delegated-slice body briefs for all listed Phase 3 slices
  - rewritten evidence and review text that record fresh `style_audit`, exact repo search, SQLite, reset, Postgres strong-lane, backend typing, and representative merged Phase 3 pytest proof
  - current docs that no longer teach route-local structural manifest sync, closed-dispatch checkpoint-order fallback, or old launch manifest timing
- dependencies:
  - the repo-local Phase 3 current docs, code, tests, and the selected Phase 3 triplet listed above
  - fresh final proof-lane results
- evidence to return:
  - updated current docs and authoritative Phase 3 triplet
  - command results for docs-freeze, style-audit, exact repo search, SQLite, Postgres, typing, and representative merged pytest proof
- parent-owned decisions:
  - whether any failing final gate is a true Phase 3 blocker or an out-of-scope later-phase issue
- stop conditions:
  - stop if truthful current-doc repair would require reopening runtime code or prompt-layer owner docs outside the listed surfaces

## Validation checkpoints

- delegated-slice body briefs exist for every listed Phase 3 slice and include every required brief field from the validator
- the rewritten evidence and review include truthful `style_audit` proof, exact repo search or underscore-private proof language, SQLite proof, reset proof, and `make test-api-db` strong-lane proof
- current docs no longer teach:
  - route-local structural manifest sync
  - no-open-dispatch checkpoint-order fallback
  - launch returning before the stable root manifest/attempt reread path is readable
- `docs_freeze` no longer reports Phase 3-specific execution-record errors

## Required validation for this chain

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli validate`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
- exact repo search for underscore-private imports across touched Phase 3 code paths
- `make pyright-api`
- `./.venv/bin/pytest -q apps/api/tests/unit/test_cli.py -k 'packaged_seed_definitions_are_available or init_writes_minimal_config_and_db_file or db_reset_recreates_sqlite_database or db_upgrade_bootstraps_seeded_sqlite_database_on_shipped_path'`
- `make test-api-db`
- `./.venv/bin/pytest -q apps/api/tests/integration/phase3 apps/api/tests/integration/runtime_schema_contract apps/api/tests/e2e/phase3/normal_lane`

## Exit criteria

- the authoritative Phase 3 triplet remains the only `summary-only: no` closeout chain for the merged Phase 3 runtime work
- current docs stay truthful to the merged shipped behavior without claiming unrelated future-phase work
- current-surface validation, checkpoint handoff, structural sync ownership, and launch stable reread timing all match the current live tree
- strong proof lanes for docs-freeze, style-audit, SQLite shipped-path reset, `make test-api-db`, backend typing, and representative merged Phase 3 pytest proof are recorded with fresh results

## Stop conditions

- stop if truthful repair requires editing runtime code, `scripts/docs/**`, prompt-layer owner docs, or non-current docs outside the owned and allowed collateral surfaces
- stop if final proof reveals a real Phase 3 runtime defect that belongs in a new code slice rather than this closeout/documentation refresh

## Cross-links

- evidence artifact: `../evidence/phase-3-closeout-runtime-lineage-and-budget.md`
- review artifact: `../reviews/phase-3-closeout-runtime-lineage-and-budget.md`
