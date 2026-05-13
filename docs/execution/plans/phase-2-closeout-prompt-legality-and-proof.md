# Phase 2 Prompt, Manifest, and Structural Reread Repair

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
- owner: Codex
- date: 2026-05-12
- execution mode: merged Phase 2 code/docs repair with delegated slices

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`

## Closeout focus

- capture the final merged Phase 2 wave: prompt legality repair, dispatch-aware
  stable-manifest parity, surfaced structural-edit palette, and truthful
  current-doc / closeout routing
- keep route-level structural-tool timing out of this authoritative Phase 2
  chain; the callback compatibility shell that makes current structural success
  synchronously rereadable remains Phase 3-owned collateral
- rewrite the four Phase 2 current-contrast pages so they point at the live
  package-split prompt, manifest, task-root, bootstrap, and current structural
  reread behavior
- rewrite the authoritative Phase 2 plan/evidence/review chain so it names the
  live package and test layout instead of deleted flat modules or stale
  docs-only wording
- prune the obsolete `phase-2-prompt-bootstrap-contract-repair*` family because
  it no longer adds routing value and now preserves only stale missing-path
  references
- keep non-Phase-2 current docs untouched in this slice

## Live landed Phase 2 surfaces reflected here

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
  `apps/api/app/runtime/task_root/__init__.py`,
  `apps/api/app/runtime/task_root/paths.py`,
  `apps/api/app/runtime/task_root/reads.py`,
  `apps/api/app/runtime/task_root/writes.py`,
  and `apps/api/app/runtime/task_root/localization.py`
- narrow launch-bootstrap helpers:
  `apps/api/app/runtime/launch/bootstrap/`
- prompt/readback helper and contract surfaces:
  `apps/api/app/runtime/contracts.py`,
  `apps/api/app/runtime/contract_models/projection.py`,
  `apps/api/app/runtime/contract_models/launch.py`,
  and `apps/api/app/runtime/prompt/structural_edit_palette.py`
- split Phase 2 tests:
  `apps/api/tests/unit/runtime_prompt_rendering/`,
  `apps/api/tests/integration/phase2/bootstrap/`,
  and `apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`

## Proof to record in the evidence artifact

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli validate`
- `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate`
- `./.venv/bin/ruff check apps/api/app/runtime/prompt apps/api/app/runtime/projection apps/api/app/runtime/task_root apps/api/app/runtime/launch apps/api/tests/unit/runtime_prompt_rendering apps/api/tests/integration/phase2/bootstrap apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`
- `./.venv/bin/mypy apps/api/app/runtime/prompt apps/api/app/runtime/projection apps/api/app/runtime/task_root apps/api/app/runtime/launch apps/api/tests/unit/runtime_prompt_rendering apps/api/tests/integration/phase2/bootstrap`
- `make pyright-api`
- `./.venv/bin/pytest -q apps/api/tests/unit/runtime_prompt_rendering apps/api/tests/integration/phase2/bootstrap apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`

## Collateral doc touch decision

- touched Phase 2 current-contrast pages:
  `docs/current/interfaces/prompt-layer-and-worker-delivery.md`,
  `docs/current/interfaces/current-openclaw-bridge-prompt-strings.md`,
  `docs/current/architecture/manifest-projection-and-acknowledgement.md`,
  and `docs/current/architecture/task-roots-and-materialized-paths.md`
- result: these pages required current-layout repair because they still pointed
  at obsolete flat prompt, projection, task-root, and top-level test surfaces

## Routing cleanup

- remove stale closeout references to obsolete flat prompt, projection,
  task-root, and top-level test surfaces from before the package split
- replace those references with the live split package and test boundaries
- delete the obsolete `phase-2-prompt-bootstrap-contract-repair*` family once
  the authoritative triplet no longer depends on it

## Authoritative routing rule

- this closeout chain remains the only authoritative `summary-only: no` Phase 2
  closeout path in the owned surfaces
- no separate historical Phase 2 repair family remains once the obsolete
  `phase-2-prompt-bootstrap-contract-repair*` files are removed

## Stop conditions

- stop if truthful Phase 2 wording requires edits outside the owned execution artifacts or the explicitly allowed collateral docs
- stop if one of the reviewed current, redesign, or generated collateral pages needs change and the truthful fix would widen beyond the allowed collateral surface list

## Cross-links

- evidence artifact:
  `../evidence/phase-2-closeout-prompt-legality-and-proof.md`
- review artifact:
  `../reviews/phase-2-closeout-prompt-legality-and-proof.md`
