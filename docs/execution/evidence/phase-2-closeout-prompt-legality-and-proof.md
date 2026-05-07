# Phase 2 Closeout Prompt Legality and Proof Routing Evidence

Status: Reference

selected phase: Phase 2
current phase page: docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md
selected work packages: P2-WP1, P2-WP2, P2-WP3
summary-only: no
delegated slices: listed
slice id: phase2-runtime-materialization
slice type: edit
owned surfaces: apps/api/app/runtime/contracts.py, apps/api/app/runtime/launch/projection.py, apps/api/app/runtime/projection/state.py, apps/api/app/runtime/projection/materialize.py, apps/api/tests/integration/test_phase2_runtime_bootstrap.py, apps/api/tests/unit/test_runtime_prompt_rendering.py, apps/api/app/runtime/resources.py
touched surfaces: apps/api/app/runtime/contracts.py, apps/api/app/runtime/launch/projection.py, apps/api/app/runtime/projection/state.py, apps/api/app/runtime/projection/materialize.py, apps/api/tests/integration/test_phase2_runtime_bootstrap.py, apps/api/tests/unit/test_runtime_prompt_rendering.py
slice id: phase2-prompt-assets
slice type: edit
owned surfaces: apps/api/app/runtime/prompt/sections.py, apps/api/app/runtime/prompt/assets/blocks/autoclaw_parent_worker_split_v1.txt, apps/api/app/runtime/prompt/assets/blocks/autoclaw_system_block_v1.txt, apps/api/app/runtime/prompt/assets/blocks/runtime_legality_block_parent_v1.txt, docs/redesign/prompt-layer/README.md, docs/redesign/prompt-layer/INDEX.md, docs/redesign/prompt-layer/contract.md, docs/redesign/prompt-layer/field-renderers.md, docs/redesign/prompt-layer/source-and-sections.md, docs/redesign/prompt-layer/composition-example.md, docs/redesign/prompt-layer/machine-contract.md, docs/redesign/prompt-layer/prompt-pack/README.md, docs/redesign/prompt-layer/prompt-pack/runtime-rule-blocks.md, docs/redesign/prompt-layer/prompt-pack/system-and-provider-block.md, docs/current/architecture/manifest-projection-and-acknowledgement.md, docs/current/architecture/task-roots-and-materialized-paths.md
touched surfaces: apps/api/app/runtime/prompt/sections.py, apps/api/app/runtime/prompt/assets/blocks/autoclaw_parent_worker_split_v1.txt, apps/api/app/runtime/prompt/assets/blocks/autoclaw_system_block_v1.txt, apps/api/app/runtime/prompt/assets/blocks/runtime_legality_block_parent_v1.txt, docs/redesign/prompt-layer/README.md, docs/redesign/prompt-layer/INDEX.md, docs/redesign/prompt-layer/contract.md, docs/redesign/prompt-layer/field-renderers.md, docs/redesign/prompt-layer/source-and-sections.md, docs/redesign/prompt-layer/composition-example.md, docs/redesign/prompt-layer/machine-contract.md, docs/redesign/prompt-layer/prompt-pack/README.md, docs/redesign/prompt-layer/prompt-pack/runtime-rule-blocks.md, docs/redesign/prompt-layer/prompt-pack/system-and-provider-block.md, docs/current/architecture/manifest-projection-and-acknowledgement.md, docs/current/architecture/task-roots-and-materialized-paths.md
slice id: phase2-docs-tooling
slice type: edit
owned surfaces: docs/redesign/prompt-layer/render-and-persistence.md, docs/redesign/prompt-layer/prompt-catalog.yaml, docs/redesign/architecture/manifest-contract.md, docs/redesign/architecture/worker-context-contract.md, docs/redesign/prompt-layer/generated/rendered-examples.md, docs/redesign/prompt-layer/generated/inventory.md, docs/redesign/prompt-layer/prompt-resource-usage-appendix.md, scripts/docs/prompt_catalog_tools.py, docs/current/interfaces/prompt-layer-and-worker-delivery.md
touched surfaces: docs/redesign/prompt-layer/render-and-persistence.md, docs/redesign/prompt-layer/prompt-catalog.yaml, docs/redesign/architecture/manifest-contract.md, docs/redesign/architecture/worker-context-contract.md, docs/redesign/prompt-layer/generated/rendered-examples.md, docs/redesign/prompt-layer/generated/inventory.md, docs/redesign/prompt-layer/prompt-resource-usage-appendix.md, scripts/docs/prompt_catalog_tools.py, docs/current/interfaces/prompt-layer-and-worker-delivery.md
slice id: phase2-closeout-artifacts
slice type: edit
owned surfaces: docs/execution/plans/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/evidence/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/reviews/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/plans/phase-2-prompt-bootstrap-contract-repair.md, docs/execution/evidence/phase-2-prompt-bootstrap-contract-repair.md, docs/execution/reviews/phase-2-prompt-bootstrap-contract-repair.md
touched surfaces: docs/execution/plans/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/evidence/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/reviews/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/plans/phase-2-prompt-bootstrap-contract-repair.md, docs/execution/evidence/phase-2-prompt-bootstrap-contract-repair.md, docs/execution/reviews/phase-2-prompt-bootstrap-contract-repair.md
slice id: phase2-audit
slice type: review-only
owned surfaces: none
touched surfaces: none
slice id: phase2-closeout-cleanup
slice type: edit
owned surfaces: apps/api/app/runtime/launch/projection.py, docs/execution/plans/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/evidence/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/reviews/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/plans/phase-2-prompt-bootstrap-contract-repair.md, docs/execution/evidence/phase-2-prompt-bootstrap-contract-repair.md, docs/execution/reviews/phase-2-prompt-bootstrap-contract-repair.md
touched surfaces: apps/api/app/runtime/launch/projection.py, docs/execution/plans/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/evidence/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/reviews/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/plans/phase-2-prompt-bootstrap-contract-repair.md, docs/execution/evidence/phase-2-prompt-bootstrap-contract-repair.md, docs/execution/reviews/phase-2-prompt-bootstrap-contract-repair.md
slice id: phase2-minimal-e2e
slice type: edit
owned surfaces: apps/api/tests/e2e/*
touched surfaces: apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py

## Slice identity

- selected phase: Phase 2
- work package or slice: authoritative evidence routing for the live Phase 2
  closeout topics plus the 2026-05-07 cleanup refresh
- date: 2026-05-07
- owned surface:
  `docs/execution/evidence/phase-2-closeout-prompt-legality-and-proof.md`
- execution mode for this refresh: runtime helper cleanup plus authoritative
  evidence refresh
- commands run in this refresh:
  - focused Phase 2 runtime bootstrap or prompt-render proof
  - targeted shipped-path SQLite reset or readiness proof
  - targeted lint, typing, and pyright gates for
    `apps/api/app/runtime/launch/projection.py`
  - shared-worktree readback for `apps/api/tests/e2e`
- validation run in this refresh:
  - targeted runtime, reset, lint, typing, and shared-worktree readback

## Plan and review links

- approved plan: `../plans/phase-2-closeout-prompt-legality-and-proof.md`
- mandatory review: `../reviews/phase-2-closeout-prompt-legality-and-proof.md`
- review artifact: `../reviews/phase-2-closeout-prompt-legality-and-proof.md`

## Authoritative evidence rule

- this file is the authoritative Phase 2 closeout-path evidence record inside
  the owned surfaces
- the older prompt-bootstrap evidence chain is historical support only after
  this chain lands:
  `../evidence/phase-2-prompt-bootstrap-contract-repair.md`

## Parent attachment contract

- this file now records the exact integrated command results for the selected
  Phase 2 proof lanes
- any remaining blocker statement below is backed by an executed command or by
  exact repo truth

## Phase-local proof obligations

- proof lane:
  - prompt legality, prompt-family or node-kind legality, and
    `same_session_continue` transport-only truth
  - result: satisfied by `31 passed`
  - phase mapping: `P2-WP1`
- proof lane:
  - criteria-owner consumption from Phase 1 into Phase 2 runtime or prompt
    surfaces without rewriting durable criteria ownership
  - result: satisfied by `31 passed`
  - phase mapping: `P2-WP2`
- proof lane:
  - raw delivery-state truth stays observability-only and out of ordinary
    `current_relevant_paths`, worker context, and criteria-satisfaction proof
  - result: satisfied by `34 passed`
  - phase mapping: `P2-WP2`
- proof lane:
  - reset-gate applicability and shipped-path reset or readiness proof for the
    integrated task-root or manifest or bootstrap changes
  - result: applicable and satisfied by `2 passed`
  - phase mapping: `P2-WP2`, `P2-WP3`
- proof lane:
  - package-install verification when narrow prompt-asset package-data changed
  - result: not triggered because no prompt-asset package-data or install-path
    change landed in the integrated Phase 2 slice
  - phase mapping: `P2-WP1`, `P2-WP3`
- proof lane:
  - minimal e2e lane when viable
  - result: satisfied by `1 passed` after the shared worktree landed
    `apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py`
  - phase mapping: `P2-WP3`

## Commands run

### 2026-05-07 cleanup refresh

- `./.venv/bin/pytest -q apps/api/tests/integration/test_phase2_runtime_bootstrap.py apps/api/tests/unit/test_runtime_prompt_rendering.py`
  - result: `34 passed`
- `./.venv/bin/pytest -q apps/api/tests/integration/test_db_reset_db.py apps/api/tests/integration/test_readyz_real_db.py`
  - result: `2 passed`
- `./.venv/bin/ruff format apps/api/app/runtime/launch/projection.py`
  - result: `1 file reformatted`
- `./.venv/bin/ruff format --check apps/api/app/runtime/launch/projection.py`
  - result: `1 file already formatted`
- `./.venv/bin/ruff check apps/api/app/runtime/launch/projection.py`
  - result: `All checks passed!`
- `./.venv/bin/mypy apps/api/app/runtime/launch/projection.py`
  - result: `Success: no issues found in 1 source file`
- `make pyright-api`
  - result: `0 errors, 0 warnings, 0 informations`
- `find apps/api/tests/e2e -maxdepth 1 -type f -printf '%P\n' | sort`
  - result:
    - `.gitkeep`
    - `test_phase2_minimal_runtime_lane.py`
    - `test_phase3_normal_lane.py`
- `./.venv/bin/pytest -q apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py`
  - result: `1 passed`

### Earlier integrated proof retained

- `./.venv/bin/python scripts/docs/prompt_catalog_tools.py generate`
  - result: completed and refreshed the generated prompt inventory and rendered
    examples
- `./.venv/bin/python scripts/docs/prompt_catalog_tools.py validate`
  - result: `Prompt catalog validation passed.`
- `./.venv/bin/ruff check scripts/docs`
  - result: passed
- `./.venv/bin/mypy scripts/docs`
  - result: passed
- `make test-api-db`
  - result: `161 passed`

## Historical support retained

- superseded historical plan:
  `../plans/phase-2-prompt-bootstrap-contract-repair.md`
- superseded historical evidence:
  `../evidence/phase-2-prompt-bootstrap-contract-repair.md`
- superseded historical review:
  `../reviews/phase-2-prompt-bootstrap-contract-repair.md`
- scope note:
  - those files retain earlier prompt or bootstrap or artifact-routing context
  - they are not the final closeout evidence authority once this chain exists

## Validation for this refresh

- read-only sanity:
  - verified the exact parseable labels remain at line start
  - verified the superseded prompt-bootstrap chain is referenced as historical
    support only
  - verified the reset-gate outcome is explicit rather than `not decided`
  - verified package-install is truthfully marked `not triggered`
  - verified minimal-e2e now points at the landed runnable lane and exact
    command result

## Review link

- review artifact:
  `../reviews/phase-2-closeout-prompt-legality-and-proof.md`
