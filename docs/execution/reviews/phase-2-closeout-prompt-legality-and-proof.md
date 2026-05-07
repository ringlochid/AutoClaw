# Phase 2 Closeout Prompt Legality and Proof Routing Review

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
- work package or slice: authoritative closeout-path review for the live Phase
  2 closeout topics plus the 2026-05-07 cleanup refresh
- date: 2026-05-07

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`

## Scope

- reviewed plan: `../plans/phase-2-closeout-prompt-legality-and-proof.md`
- reviewed evidence: `../evidence/phase-2-closeout-prompt-legality-and-proof.md`
- reviewed superseded historical support:
  `../plans/phase-2-prompt-bootstrap-contract-repair.md`
  `../evidence/phase-2-prompt-bootstrap-contract-repair.md`
  `../reviews/phase-2-prompt-bootstrap-contract-repair.md`

## Verdict

- pass/fail: pass
- summary: the authoritative Phase 2 chain is correct, the focused Phase 2
  proof lanes passed, reset-gate applicability is now explicit and satisfied,
  package-install truth was not triggered, the sibling-landed minimal e2e lane
  now passes, and the duplicate prompt-family mapping in
  `launch/projection.py` is gone.

## Findings

- the new `phase-2-closeout-prompt-legality-and-proof*` chain is now the only
  `summary-only: no` Phase 2 closeout-path family in the owned surfaces
- the older `phase-2-prompt-bootstrap-contract-repair*` chain is now
  `summary-only: yes`, so it can no longer read as mandatory-review,
  reset-gate, or phase-done authority
- the authoritative closeout scope is now limited to the live Phase 2 issues
  only instead of mixing earlier bootstrap summary claims into the current
  closeout path
- prompt legality is now routed as an explicit Phase 2 proof obligation rather
  than an implied side effect of earlier bootstrap wording
- criteria-owner consumption is now routed as a required Phase 1 to Phase 2
  contract handoff instead of being left implicit in prompt or manifest wording
- raw `delivery-state.json` truth is now routed explicitly as observability-only
  support truth and not as ordinary worker-visible runtime context
- reset-gate applicability is now explicit:
  - applicable because the integrated Phase 2 slice changed task-root
    bootstrap and manifest or task-root projection behavior
  - satisfied by shipped-path SQLite reset or readiness proof in
    `apps/api/tests/integration/test_db_reset_db.py` and
    `apps/api/tests/integration/test_readyz_real_db.py`
- package-install truth was not triggered because this integrated slice changed
  neither prompt assets nor package-data wiring
- the current shared worktree now contains a runnable Phase 2 minimal e2e lane
  at `apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py`, and that lane
  passed
- the earlier downstream control-state blocker is now resolved on the
  integrated tree; raw `delivery-state.json` remains observability-only and the
  later Phase 3 tests now read the waiting meaning from controller truth
- `apps/api/app/runtime/launch/projection.py` now reuses
  `app.runtime.contracts.prompt_family_for_node_kind` instead of carrying a
  local duplicate prompt-family mapping

## Delegated-slice compliance

- the phase used seven bounded slices: runtime/materialization, prompt-assets,
  docs/tooling, minimal e2e, closeout artifacts, closeout cleanup, and one
  review-only audit
- the review verified that each edit slice stayed inside its owned surfaces and
  that the review-only slice returned no edits

## Proof lanes relied on

- `./.venv/bin/pytest -q apps/api/tests/integration/test_phase2_runtime_bootstrap.py apps/api/tests/unit/test_runtime_prompt_rendering.py` -> `34 passed`
- `./.venv/bin/pytest -q apps/api/tests/integration/test_db_reset_db.py apps/api/tests/integration/test_readyz_real_db.py` -> `2 passed`
- `./.venv/bin/ruff format apps/api/app/runtime/launch/projection.py` -> `1 file reformatted`
- `./.venv/bin/ruff format --check apps/api/app/runtime/launch/projection.py` -> `1 file already formatted`
- `./.venv/bin/ruff check apps/api/app/runtime/launch/projection.py` -> `All checks passed!`
- `./.venv/bin/mypy apps/api/app/runtime/launch/projection.py` -> `Success: no issues found in 1 source file`
- `find apps/api/tests/e2e -maxdepth 1 -type f -printf '%P\n' | sort` -> `.gitkeep`, `test_phase2_minimal_runtime_lane.py`, `test_phase3_normal_lane.py`
- `./.venv/bin/pytest -q apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py` -> `1 passed`
- `./.venv/bin/python scripts/docs/prompt_catalog_tools.py generate` -> completed
- `make pyright-api` -> `0 errors, 0 warnings, 0 informations`
- `./.venv/bin/python scripts/docs/prompt_catalog_tools.py validate` -> `Prompt catalog validation passed.`
- `./.venv/bin/ruff check scripts/docs` -> passed
- `./.venv/bin/mypy scripts/docs` -> passed
- `make test-api-db` -> `161 passed`

## Stale-logic search proof

- checked for stale Phase 2 authority signals inside the owned artifacts:
  - old prompt-bootstrap files remaining `summary-only: no`
  - old prompt-bootstrap files continuing to present themselves as the active
    closeout path
  - new closeout files omitting one of the five live Phase 2 closeout issues
- outcome:
  - the new closeout chain is the only `summary-only: no` Phase 2 closeout-path
    family in the owned surfaces
  - the old prompt-bootstrap chain now reads as historical support only

## Kill-list proof

- phase kill-list source: `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
- terms checked:
  - task compose as a runtime-derived kitchen sink
  - redesign docs treated as the shipped prompt source
  - prompt rules that rely on hidden transcript memory
  - filesystem-primary truth for generated roots
  - runtime persistence truth split across both Phase 2 and Phase 3
- outcome: the integrated Phase 2 proof and docs keep prompt-source ownership, raw delivery-state observability, and criteria-owner consumption aligned without reintroducing the phase kill-list terms as live behavior

## Docs answer-sourcing proof

- required execution canon read and applied:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs/execution/README.md`
  - `docs/execution/phases/overview.md`
  - `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
  - `docs/execution/maps/file-priority-map.md`
  - `docs/execution/maps/redesign-code-landing-map.md`
  - `docs/execution/gates/mandatory-review-gate.md`
  - `docs/execution/gates/reset-gate.md`
  - `docs/execution/gates/phase-done-gate.md`
- redesign owners and examples read for truthful wording:
  - `docs/redesign/prompt-layer/contract.md`
  - `docs/redesign/prompt-layer/source-and-sections.md`
  - `docs/redesign/prompt-layer/field-renderers.md`
  - `docs/redesign/prompt-layer/render-and-persistence.md`
  - `docs/redesign/prompt-layer/machine-contract.md`
  - `docs/redesign/prompt-layer/legality-and-coverage.md`
  - `docs/redesign/prompt-layer/README.md`
  - `docs/redesign/prompt-layer/INDEX.md`
  - `docs/redesign/prompt-layer/prompt-pack/README.md`
  - `docs/redesign/prompt-layer/prompt-pack/system-and-provider-block.md`
  - `docs/redesign/prompt-layer/prompt-pack/runtime-rule-blocks.md`
  - `docs/redesign/prompt-layer/prompt-pack/validation-and-reject-blocks.md`
  - `docs/redesign/prompt-layer/generated/README.md`
  - `docs/redesign/prompt-layer/generated/rendered-examples.md`
  - `docs/redesign/prompt-layer/generated/inventory.md`
  - `docs/redesign/architecture/manifest-contract.md`
  - `docs/redesign/architecture/worker-context-contract.md`
  - `docs/redesign/architecture/task-root-layout-and-generated-files.md`
  - `docs/redesign/architecture/artifact-ref-and-storage-contract.md`
  - `docs/redesign/architecture/runtime-records-and-lifecycle.md`
  - `docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md`
  - `docs/redesign/workflows/typed-dependency-selectors-and-produce-slots.md`
  - `docs/redesign/workflows/criteria-and-parent-verification.md`
- current-contrast reads used:
  - `docs/current/interfaces/prompt-layer-and-worker-delivery.md`
  - `docs/current/interfaces/current-openclaw-bridge-prompt-strings.md`
  - `docs/current/architecture/manifest-projection-and-acknowledgement.md`
  - `docs/current/architecture/task-roots-and-materialized-paths.md`
- canon gap or explicit `none`:
  - none

## Phase-bounded STYLE exceptions

- surface: `apps/api/app/runtime/launch/projection.py`
- exception: the file still exceeds the `>400` line split-review threshold at
  `529` lines, and `_build_manifest_projection` still exceeds the `>80`
  non-comment or non-blank line trigger at `88`
- phase-bounded reason: this closeout slice only removed duplicated
  prompt-family routing and refreshed the authoritative Phase 2 records;
  splitting the launch projection surface would widen into a broader
  bootstrap or manifest refactor outside the approved cleanup scope and would
  increase collision risk with adjacent runtime ownership
- owning follow-up: later bounded runtime projection split work, after the
  Phase 2 closeout slice, when the launch projection package can be refactored
  without crossing this cleanup scope

- surface: `apps/api/app/runtime/projection/state.py`
- exception: the file still exceeds the `>600` line no-growth threshold at
  `1098` lines
- phase-bounded reason: the integrated Phase 2 slice reopened current-child
  artifact surfacing in a file that still mixes manifest projection with
  broader runtime-state querying. Splitting it here would cross the Phase 2/3
  ownership hotspot.
- owning follow-up: later bounded runtime projection split work that separates
  manifest assembly from runtime-state loading

- surface: `apps/api/app/runtime/projection/materialize.py`
- exception: the file still exceeds the `>400` line split-review threshold at
  `472` lines
- phase-bounded reason: the integrated Phase 2 slice kept materialization
  behavior stable and did not widen into a broader projection split.
- owning follow-up: later bounded runtime materialization cleanup if the file
  reopens again

- surface: `apps/api/app/runtime/prompt/sections.py`
- exception: the file still exceeds the `>400` line split-review threshold at
  `426` lines
- phase-bounded reason: the integrated Phase 2 slice updated prompt wording and
  reread surfacing, but a larger section extraction would widen beyond this
  closeout scope.
- owning follow-up: later bounded prompt renderer split if the file reopens

- surface: `scripts/docs/prompt_catalog_tools.py`
- exception: the file still exceeds the `>600` line no-growth threshold at
  `1764` lines
- phase-bounded reason: the integrated Phase 2 slice updated exact-block
  ownership and generated prompt inventory truth, but splitting the validator
  tool would widen this closeout slice beyond the approved tooling cleanup.
- owning follow-up: later bounded prompt tooling refactor

- surface: `apps/api/tests/integration/test_phase2_runtime_bootstrap.py`
- exception: the file still exceeds the `>600` line no-growth threshold at
  `1428` lines
- phase-bounded reason: the integrated Phase 2 slice added regression coverage
  for prompt and manifest changes without repartitioning the broader bootstrap
  suite.
- owning follow-up: later bounded test-suite split for Phase 2 bootstrap

- surface: `apps/api/tests/unit/test_runtime_prompt_rendering.py`
- exception: the file still exceeds the `>600` line no-growth threshold at
  `943` lines
- phase-bounded reason: the integrated Phase 2 slice expanded prompt rendering
  coverage, but splitting the broader fixture-heavy render suite would widen
  beyond this closeout cleanup.
- owning follow-up: later bounded prompt-render test-suite split

- surface: `apps/api/app/runtime/projection/state.py`
- exception: the file still exceeds the `>600` line no-growth threshold at
  `1098` lines
- phase-bounded reason: the integrated Phase 2 slice reopened current-child
  artifact surfacing in a file that still mixes manifest projection with
  broader runtime-state querying. Splitting it here would cross the Phase 2/3
  ownership hotspot.
- owning follow-up: later bounded runtime projection split work that separates
  manifest assembly from runtime-state loading

- surface: `apps/api/app/runtime/projection/materialize.py`
- exception: the file still exceeds the `>400` line split-review threshold at
  `472` lines
- phase-bounded reason: the integrated Phase 2 slice left materialization
  behavior stable and did not widen into a broader projection split.
- owning follow-up: later bounded runtime materialization cleanup if the file
  reopens again

- surface: `apps/api/app/runtime/prompt/sections.py`
- exception: the file still exceeds the `>400` line split-review threshold at
  `426` lines
- phase-bounded reason: the integrated Phase 2 slice updated prompt wording and
  reread surfacing, but a larger section extraction would widen beyond this
  closeout scope.
- owning follow-up: later bounded prompt renderer split if the file reopens

- surface: `scripts/docs/prompt_catalog_tools.py`
- exception: the file still exceeds the `>600` line no-growth threshold at
  `1764` lines
- phase-bounded reason: the integrated Phase 2 slice updated exact-block
  ownership and generated prompt inventory truth, but splitting the validator
  tool would widen this closeout slice beyond the approved tooling cleanup.
- owning follow-up: later bounded prompt tooling refactor

- surface: `apps/api/tests/integration/test_phase2_runtime_bootstrap.py`
- exception: the file still exceeds the `>600` line no-growth threshold at
  `1428` lines
- phase-bounded reason: the integrated Phase 2 slice added regression coverage
  for prompt and manifest changes without repartitioning the broader bootstrap
  suite.
- owning follow-up: later bounded test-suite split for Phase 2 bootstrap

- surface: `apps/api/tests/unit/test_runtime_prompt_rendering.py`
- exception: the file still exceeds the `>600` line no-growth threshold at
  `943` lines
- phase-bounded reason: the integrated Phase 2 slice expanded prompt rendering
  coverage, but splitting the broader fixture-heavy render suite would widen
  beyond this closeout cleanup.
- owning follow-up: later bounded prompt-render test-suite split

## Reset-gate outcome

- applicable because the integrated Phase 2 slice changed task-root bootstrap
  and manifest or task-root projection behavior covered by the Phase 2 reset
  criteria
- satisfied by `./.venv/bin/pytest -q apps/api/tests/integration/test_db_reset_db.py apps/api/tests/integration/test_readyz_real_db.py` -> `2 passed`
- package reinstall was not triggered because no prompt-asset package-data or
  install-path change landed in the integrated Phase 2 slice
- Postgres or Docker reset proof was not required for this closeout refresh
  because the integrated Phase 2 slice did not change DB schema or
  controller-owned persistence truth

## Remaining exact blockers

- none

## Cross-links

- authoritative plan:
  `../plans/phase-2-closeout-prompt-legality-and-proof.md`
- authoritative evidence:
  `../evidence/phase-2-closeout-prompt-legality-and-proof.md`
- superseded historical summary:
  `./phase-2-prompt-bootstrap-contract-repair.md`
