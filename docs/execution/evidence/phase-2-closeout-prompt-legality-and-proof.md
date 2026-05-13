# Phase 2 Prompt, Manifest, and Structural Reread Repair Evidence

Status: Reference

selected phase: Phase 2
current phase page: docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md
selected work packages: P2-WP1, P2-WP2, P2-WP3
summary-only: no
delegated slices: listed
slice id: phase2-prompt-source-legality
slice type: edit
owned surfaces: shipped prompt assets under apps/api/app/runtime/prompt/assets/** and directly mirrored prompt-pack/generated redesign docs
touched surfaces: apps/api/app/runtime/prompt/assets/blocks/autoclaw_parent_worker_split_v1.txt, apps/api/app/runtime/prompt/assets/blocks/autoclaw_system_block_v1.txt, apps/api/app/runtime/prompt/assets/blocks/runtime_boundary_rule_block_v1.txt, apps/api/app/runtime/prompt/assets/blocks/runtime_legality_block_parent_v1.txt, docs/redesign/prompt-layer/README.md, docs/redesign/prompt-layer/composition-example.md, docs/redesign/prompt-layer/contract.md, docs/redesign/prompt-layer/field-renderers.md, docs/redesign/prompt-layer/legality-and-coverage.md, docs/redesign/prompt-layer/prompt-pack/runtime-rule-blocks.md, docs/redesign/prompt-layer/prompt-pack/system-and-provider-block.md, docs/redesign/prompt-layer/source-and-sections.md
slice id: phase2-stable-manifest-parity
slice type: edit
owned surfaces: apps/api/app/runtime/projection/manifest/**, apps/api/app/runtime/projection/dispatch/** when needed for parity, apps/api/app/runtime/task_root/**, narrow apps/api/app/runtime/launch/bootstrap/** helpers, apps/api/tests/integration/phase2/bootstrap/**, and apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py
touched surfaces: apps/api/app/runtime/projection/manifest/projection.py, apps/api/app/runtime/projection/runtime_state.py, apps/api/app/runtime/task_root/reads.py, apps/api/tests/integration/phase2/bootstrap/test_manifest.py, apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py
slice id: phase2-structural-edit-palette
slice type: edit
owned surfaces: prompt/render readback models and helpers needed to surface a registry-backed structural edit palette in prompt/manifest/readback context
touched surfaces: apps/api/app/runtime/contract_models/launch.py, apps/api/app/runtime/contract_models/projection.py, apps/api/app/runtime/contracts.py, apps/api/app/runtime/launch/bootstrap/manifest.py, apps/api/app/runtime/projection/manifest/structural_palette.py, apps/api/app/runtime/projection/manifest/tree.py, apps/api/app/runtime/prompt/bundle.py, apps/api/app/runtime/prompt/instructions.py, apps/api/app/runtime/prompt/sections/rendering.py, apps/api/app/runtime/prompt/structural_edit_palette.py, apps/api/tests/integration/phase2/bootstrap/fixtures.py, apps/api/tests/integration/phase2/bootstrap/test_bootstrap.py, apps/api/tests/unit/runtime_prompt_rendering/manifest_samples.py, apps/api/tests/unit/runtime_prompt_rendering/planning_samples.py, apps/api/tests/unit/runtime_prompt_rendering/samples.py, apps/api/tests/unit/runtime_prompt_rendering/support.py, apps/api/tests/unit/runtime_prompt_rendering/test_assets.py, apps/api/tests/unit/runtime_prompt_rendering/test_dispatch.py, apps/api/tests/unit/runtime_prompt_rendering/test_smoke.py, docs/redesign/prompt-layer/generated/rendered-examples.md, scripts/docs/prompt_catalog/examples.py, scripts/docs/prompt_catalog/load.py, scripts/docs/prompt_catalog/sample_palette.py
slice id: phase2-current-doc-and-closeout-refresh
slice type: edit
owned surfaces: the four Phase 2 current-contrast docs plus the authoritative Phase 2 plan/evidence/review chain and obsolete Phase 2 repair records
touched surfaces: docs/current/interfaces/prompt-layer-and-worker-delivery.md, docs/current/interfaces/current-openclaw-bridge-prompt-strings.md, docs/current/architecture/manifest-projection-and-acknowledgement.md, docs/current/architecture/task-roots-and-materialized-paths.md, docs/execution/plans/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/evidence/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/reviews/phase-2-closeout-prompt-legality-and-proof.md

## Slice identity

- selected phase: Phase 2
- approved continuation slice: merged Phase 2 prompt legality, manifest parity,
  structural-edit palette, and closeout-authority repair wave
- date: 2026-05-12
- owned surface: `docs/execution/evidence/phase-2-closeout-prompt-legality-and-proof.md`
- evidence source for this merged wave: live Phase 2 code/doc inspection,
  prompt-source repair, manifest parity repair, structural-edit palette surfacing,
  current-doc repair, closeout-record repair, obsolete-artifact pruning, and
  the rerun validators and tests listed below

## Plan and review links

- approved plan: `../plans/phase-2-closeout-prompt-legality-and-proof.md`
- mandatory review: `../reviews/phase-2-closeout-prompt-legality-and-proof.md`
- review artifact: `../reviews/phase-2-closeout-prompt-legality-and-proof.md`

## Authoritative evidence rule

- this file is the authoritative Phase 2 closeout-path evidence record in the owned surfaces
- the obsolete `phase-2-prompt-bootstrap-contract-repair*` chain was removed in
  this slice because it no longer added routing value and preserved only stale
  missing-path references

## Landed Phase 2 surfaces reflected by this evidence

- runtime prompt package:
  `apps/api/app/runtime/prompt/assets/**`,
  `apps/api/app/runtime/prompt/asset_catalog.py`,
  `apps/api/app/runtime/prompt/bundle.py`,
  `apps/api/app/runtime/prompt/instructions.py`,
  and `apps/api/app/runtime/prompt/sections/`
- runtime projection package:
  `apps/api/app/runtime/projection/dispatch/`,
  `apps/api/app/runtime/projection/manifest/`,
  `apps/api/app/runtime/projection/attempt_materialization.py`,
  `apps/api/app/runtime/projection/projection_mappers.py`,
  and `apps/api/app/runtime/projection/runtime_state.py`
- stable task-root package:
  `apps/api/app/runtime/task_root/`
- narrow launch-bootstrap helpers:
  `apps/api/app/runtime/launch/bootstrap/`
- split Phase 2 tests:
  `apps/api/tests/unit/runtime_prompt_rendering/`,
  `apps/api/tests/integration/phase2/bootstrap/`,
  and `apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`
- Phase 2-owned reread scope:
  the stable manifest path is current-open-dispatch-aware and the Phase 2 e2e
  lane rereads `_runtime/workflow-manifest.md` successfully in the merged tree,
  but the callback-route timing shell that keeps structural tool success
  synchronous is Phase 3-owned and is recorded in the Phase 3 closeout chain

## Proof run for this repair

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli validate`
  - result: `passed`
- `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate`
  - result: `passed`
- `./.venv/bin/ruff check apps/api/app/runtime/prompt apps/api/app/runtime/projection apps/api/app/runtime/task_root apps/api/app/runtime/launch apps/api/tests/unit/runtime_prompt_rendering apps/api/tests/integration/phase2/bootstrap apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`
  - result: `passed`
- `./.venv/bin/mypy apps/api/app/runtime/prompt apps/api/app/runtime/projection apps/api/app/runtime/task_root apps/api/app/runtime/launch apps/api/tests/unit/runtime_prompt_rendering apps/api/tests/integration/phase2/bootstrap`
  - result: `passed`
- `make pyright-api`
  - result: `passed`
- `./.venv/bin/pytest -q apps/api/tests/unit/runtime_prompt_rendering apps/api/tests/integration/phase2/bootstrap apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`
  - result: `78 passed in 52.44s`

## Owned current-doc and record repair landed here

- `docs/current/interfaces/prompt-layer-and-worker-delivery.md`
- `docs/current/interfaces/current-openclaw-bridge-prompt-strings.md`
- `docs/current/architecture/manifest-projection-and-acknowledgement.md`
- `docs/current/architecture/task-roots-and-materialized-paths.md`
- `docs/execution/plans/phase-2-closeout-prompt-legality-and-proof.md`
- `docs/execution/evidence/phase-2-closeout-prompt-legality-and-proof.md`
- `docs/execution/reviews/phase-2-closeout-prompt-legality-and-proof.md`
- `apps/api/app/runtime/prompt/assets/blocks/autoclaw_parent_worker_split_v1.txt`
- `apps/api/app/runtime/prompt/assets/blocks/autoclaw_system_block_v1.txt`
- `apps/api/app/runtime/prompt/assets/blocks/runtime_boundary_rule_block_v1.txt`
- `apps/api/app/runtime/prompt/assets/blocks/runtime_legality_block_parent_v1.txt`
- `apps/api/app/runtime/contract_models/launch.py`
- `apps/api/app/runtime/contract_models/projection.py`
- `apps/api/app/runtime/contracts.py`
- `apps/api/app/runtime/launch/bootstrap/manifest.py`
- `apps/api/app/runtime/projection/manifest/projection.py`
- `apps/api/app/runtime/projection/manifest/structural_palette.py`
- `apps/api/app/runtime/projection/manifest/tree.py`
- `apps/api/app/runtime/prompt/bundle.py`
- `apps/api/app/runtime/prompt/instructions.py`
- `apps/api/app/runtime/prompt/sections/rendering.py`
- `apps/api/app/runtime/prompt/structural_edit_palette.py`
- `apps/api/tests/integration/phase2/bootstrap/fixtures.py`
- `apps/api/tests/integration/phase2/bootstrap/test_bootstrap.py`
- `apps/api/tests/integration/phase2/bootstrap/test_manifest.py`
- `apps/api/tests/unit/runtime_prompt_rendering/manifest_samples.py`
- `apps/api/tests/unit/runtime_prompt_rendering/planning_samples.py`
- `apps/api/tests/unit/runtime_prompt_rendering/samples.py`
- `apps/api/tests/unit/runtime_prompt_rendering/support.py`
- `apps/api/tests/unit/runtime_prompt_rendering/test_assets.py`
- `apps/api/tests/unit/runtime_prompt_rendering/test_dispatch.py`
- `apps/api/tests/unit/runtime_prompt_rendering/test_smoke.py`
- `docs/redesign/prompt-layer/README.md`
- `docs/redesign/prompt-layer/composition-example.md`
- `docs/redesign/prompt-layer/contract.md`
- `docs/redesign/prompt-layer/field-renderers.md`
- `docs/redesign/prompt-layer/generated/rendered-examples.md`
- `docs/redesign/prompt-layer/legality-and-coverage.md`
- `docs/redesign/prompt-layer/prompt-pack/runtime-rule-blocks.md`
- `docs/redesign/prompt-layer/prompt-pack/system-and-provider-block.md`
- `docs/redesign/prompt-layer/source-and-sections.md`
- `scripts/docs/prompt_catalog/examples.py`
- `scripts/docs/prompt_catalog/load.py`
- `scripts/docs/prompt_catalog/sample_palette.py`

## Obsolete artifact pruning

- deleted the obsolete summary-only Phase 2 repair triplet that no longer added
  routing value

## Remaining exact blockers outside this slice

- none
