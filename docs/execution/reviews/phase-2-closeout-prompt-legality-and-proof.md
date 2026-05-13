# Phase 2 Prompt, Manifest, and Structural Reread Repair Review

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

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`

## Scope

- reviewed plan: `../plans/phase-2-closeout-prompt-legality-and-proof.md`
- reviewed evidence: `../evidence/phase-2-closeout-prompt-legality-and-proof.md`
- reviewed owned current docs:
  `../../current/interfaces/prompt-layer-and-worker-delivery.md`,
  `../../current/interfaces/current-openclaw-bridge-prompt-strings.md`,
  `../../current/architecture/manifest-projection-and-acknowledgement.md`,
  and `../../current/architecture/task-roots-and-materialized-paths.md`

## Verdict

- pass/fail: pass
- summary: the merged Phase 2 code/docs wave repaired prompt-source legality,
  dispatch-aware stable manifest parity, structural-edit palette surfacing, and
  authoritative Phase 2 closeout routing; after parent integration, the
  owned proof lanes pass.

## Findings

- the current-contrast docs no longer point at obsolete flat prompt,
  projection, task-root, or top-level test surfaces from before the package
  split
- non-root parent prompt rendering no longer teaches root-only `release_blocked`
  or non-root `blocked` closure
- stable `_runtime/workflow-manifest.*` materialization is now current-open-dispatch-aware for controller-selected checkpoint handoff and staged release descendant refs
- the merged tree currently leaves the parent/root with an immediate stable
  manifest reread path after structural success, but the callback timing shell
  that makes that behavior synchronous is Phase 3-owned collateral and is not
  claimed here as Phase 2 closure authority
- parent/root prompt and manifest readback now surface a compact registry-backed structural edit palette instead of relying on guessed role/policy names
- the authoritative closeout chain now names the live split package boundaries:
  `apps/api/app/runtime/prompt/sections/`,
  `apps/api/app/runtime/projection/dispatch/`,
  `apps/api/app/runtime/projection/manifest/`,
  `apps/api/app/runtime/task_root/`,
  `apps/api/app/runtime/launch/bootstrap/`,
  `apps/api/tests/unit/runtime_prompt_rendering/`,
  `apps/api/tests/integration/phase2/bootstrap/`, and
  `apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`
- the obsolete `phase-2-prompt-bootstrap-contract-repair*` family no longer
  remains in the record homes to generate stale missing-path failures
- `docs_freeze` now passes on the merged tree

## Proof lanes relied on

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli validate` -> `passed`
- `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate` -> `passed`
- `./.venv/bin/pytest -q apps/api/tests/unit/runtime_prompt_rendering apps/api/tests/integration/phase2/bootstrap apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py` -> `78 passed in 39.76s`

## Delegated-slice compliance

- delegated slices stayed inside the merged Phase 2 owned or allowed-collateral surfaces after parent integration removed the stray out-of-scope edits

## Stale-logic search proof

- checked the owned artifacts for stale closeout references to deleted flat
  prompt, projection, task-root, and test surfaces
- outcome: those stale references were removed from the authoritative closeout
  chain and the obsolete repair family that still depended on them was deleted

## Kill-list proof

- phase kill-list source:
  `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
- outcome:
  the refreshed closeout chain still keeps prompt assets as the shipped prompt source, keeps `_runtime/dispatch/*` observability-only, keeps generated roots controller-derived rather than filesystem-authoritative, and continues to defer runtime persistence truth to Phase 3

## Docs answer-sourcing proof

- execution canon read:
  `AGENTS.md`,
  `STYLE.md`,
  `docs/execution/README.md`,
  `docs/execution/phases/overview.md`,
  `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`,
  `docs/execution/maps/file-priority-map.md`,
  `docs/execution/maps/redesign-code-landing-map.md`,
  `docs/execution/gates/mandatory-review-gate.md`,
  `docs/execution/gates/reset-gate.md`,
  and `docs/execution/gates/phase-done-gate.md`
- primary and supporting redesign reads used for truthful closeout wording:
  `docs/redesign/prompt-layer/contract.md`,
  `docs/redesign/prompt-layer/source-and-sections.md`,
  `docs/redesign/prompt-layer/field-renderers.md`,
  `docs/redesign/prompt-layer/render-and-persistence.md`,
  `docs/redesign/prompt-layer/machine-contract.md`,
  `docs/redesign/prompt-layer/README.md`,
  `docs/redesign/prompt-layer/INDEX.md`,
  `docs/redesign/prompt-layer/prompt-pack/README.md`,
  `docs/redesign/prompt-layer/prompt-pack/system-and-provider-block.md`,
  `docs/redesign/prompt-layer/prompt-pack/runtime-rule-blocks.md`,
  `docs/redesign/prompt-layer/prompt-pack/validation-and-reject-blocks.md`,
  `docs/redesign/prompt-layer/generated/README.md`,
  `docs/redesign/prompt-layer/generated/rendered-examples.md`,
  `docs/redesign/prompt-layer/generated/inventory.md`,
  `docs/redesign/prompt-layer/legality-and-coverage.md`,
  `docs/redesign/prompt-layer/prompt-catalog.yaml`,
  `docs/redesign/prompt-layer/prompt-resource-usage-appendix.md`,
  `docs/redesign/prompt-layer/composition-example.md`,
  `docs/redesign/architecture/manifest-contract.md`,
  `docs/redesign/architecture/worker-context-contract.md`,
  `docs/redesign/architecture/task-root-layout-and-generated-files.md`,
  `docs/redesign/architecture/artifact-ref-and-storage-contract.md`,
  `docs/redesign/architecture/runtime-records-and-lifecycle.md`,
  `docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md`,
  `docs/redesign/architecture/filesystem-layout-and-roots.md`,
  `docs/redesign/architecture/task-compose-root-binding-and-host-placement.md`,
  `docs/redesign/decisions/ADR-0005-task-owned-roots-and-runtime-generated-projections.md`,
  `docs/redesign/workflows/typed-dependency-selectors-and-produce-slots.md`,
  `docs/redesign/workflows/criteria-and-parent-verification.md`,
  and `docs/redesign/workflows/workflow-schema-appendix.md`
- current-contrast reads used:
  `docs/current/interfaces/prompt-layer-and-worker-delivery.md`,
  `docs/current/interfaces/current-openclaw-bridge-prompt-strings.md`,
  `docs/current/architecture/manifest-projection-and-acknowledgement.md`,
  and `docs/current/architecture/task-roots-and-materialized-paths.md`
- current live Phase 2 code and test surfaces reviewed:
  `apps/api/app/runtime/prompt/`,
  `apps/api/app/runtime/projection/dispatch/`,
  `apps/api/app/runtime/projection/manifest/`,
  `apps/api/app/runtime/task_root/`,
  `apps/api/app/runtime/launch/bootstrap/`,
  `apps/api/tests/unit/runtime_prompt_rendering/`,
  `apps/api/tests/integration/phase2/bootstrap/`,
  and `apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`
- canon gap or explicit `none`:
  none

## Phase-bounded STYLE exceptions

- none

## Reset-gate note

- this merged Phase 2 wave reopened prompt assets, prompt/readback models,
  manifest projection, current docs, and closeout records
- shipped prompt package-data, runtime schema install paths, and task-root
  layout roots remained unchanged; the rerun bootstrap and minimal e2e lanes
  are the recorded proof for the landed manifest-readback behavior

## Remaining exact blockers

- none

## Cross-links

- authoritative plan:
  `../plans/phase-2-closeout-prompt-legality-and-proof.md`
- authoritative evidence:
  `../evidence/phase-2-closeout-prompt-legality-and-proof.md`
