# Phase 2 Prompt, Manifest, Artifact, and Bootstrap Contract Repair

Status: Reference

selected phase: Phase 2
current phase page: docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md
selected work packages: P2-WP1, P2-WP2, P2-WP3
summary-only: no
delegated slices: listed
slice id: phase-2-runtime-code-and-tests
slice type: edit
owned surfaces: apps/api/app/runtime/contracts.py, apps/api/app/runtime/resources.py, apps/api/app/runtime/projection/state.py, apps/api/app/runtime/projection/materialize.py, apps/api/app/runtime/prompt/bundle.py, apps/api/app/runtime/prompt/instructions.py, apps/api/app/runtime/prompt/sections.py, apps/api/app/runtime/launch/projection.py, apps/api/tests/unit/test_runtime_prompt_rendering.py, apps/api/tests/integration/test_phase2_runtime_bootstrap.py
touched surfaces: apps/api/app/runtime/contracts.py, apps/api/app/runtime/resources.py, apps/api/app/runtime/projection/state.py, apps/api/app/runtime/projection/materialize.py, apps/api/app/runtime/prompt/bundle.py, apps/api/app/runtime/prompt/instructions.py, apps/api/app/runtime/prompt/sections.py, apps/api/app/runtime/launch/projection.py, apps/api/tests/unit/test_runtime_prompt_rendering.py, apps/api/tests/integration/test_phase2_runtime_bootstrap.py
slice id: phase-2-docs-examples-and-prompt-validation
slice type: edit
owned surfaces: docs/redesign/prompt-layer/source-and-sections.md, docs/redesign/prompt-layer/field-renderers.md, docs/redesign/prompt-layer/prompt-resource-usage-appendix.md, docs/redesign/prompt-layer/composition-example.md, docs/redesign/prompt-layer/generated/rendered-examples.md, docs/redesign/prompt-layer/prompt-catalog.yaml, docs/current/interfaces/prompt-layer-and-worker-delivery.md, scripts/docs/prompt_catalog_tools.py
touched surfaces: docs/redesign/prompt-layer/source-and-sections.md, docs/redesign/prompt-layer/field-renderers.md, docs/redesign/prompt-layer/prompt-resource-usage-appendix.md, docs/redesign/prompt-layer/composition-example.md, docs/redesign/prompt-layer/generated/rendered-examples.md, docs/redesign/prompt-layer/prompt-catalog.yaml, docs/current/interfaces/prompt-layer-and-worker-delivery.md, scripts/docs/prompt_catalog_tools.py
slice id: phase-2-artifact-audit
slice type: review-only
owned surfaces: none
touched surfaces: none
slice id: phase-2-correctness-audit
slice type: review-only
owned surfaces: none
touched surfaces: none

## Slice identity

- selected phase: Phase 2
- work package or slice: authoritative artifact refresh for `P2-WP1`, `P2-WP2`, and `P2-WP3`

## Phase-local contract

- current phase page: `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
- implementation file lock map: `docs/execution/maps/file-priority-map.md`

## Bounded Slice

This document now serves the Phase 2 authoritative artifact refresh only. No additional Phase 2 work-package ids exist beyond `P2-WP1`, `P2-WP2`, and `P2-WP3`.

The refresh edits only these owned execution artifacts:

- `docs/execution/plans/phase-2-prompt-bootstrap-contract-repair.md`
- `docs/execution/evidence/phase-2-prompt-bootstrap-contract-repair.md`
- `docs/execution/reviews/phase-2-prompt-bootstrap-contract-repair.md`

## Goal

Refresh the authoritative Phase 2 plan, evidence, and review so they match the current Phase 2 lane truth without widening into code, docs tooling, prompt docs, or later-phase surfaces.

## Scope Mapping

- `P2-WP1`: record the prompt/render hardening truth, including prompt-family versus node-kind legality checks, `same_session_continue` transport rules, prompt-block drift closure by canon reconciliation, and the semantic `prompt_catalog_tools.py validate` audit.
- `P2-WP2`: record that surfaced-resource localization is on the live production path and that Phase 2 task-root or manifest truth remains controller-owned and Phase 2-scoped.
- `P2-WP3`: record bootstrap and artifact handoff truth, including `artifact-index.json` publications carrying `owner_node_key` and the focused prompt/bootstrap test lane proof.

## Truths To Encode

- The authoritative Phase 2 work-package ids are only `P2-WP1`, `P2-WP2`, and `P2-WP3`.
- Prompt-block drift is closed by the landed prompt catalog, prompt docs, and generated-example reconciliation.
- Live surfaced-resource localization is on the production path.
- `artifact-index.json` publications now include `owner_node_key`.
- `prompt_catalog_tools.py validate` now semantically audits prompt-family versus node-kind mapping in addition to generated-example parity.
- The focused Phase 2 prompt/bootstrap lane is recorded as `26 passed`.
- Prompt catalog validation passed in the current lane.
- `docs_freeze_validate.py` is not claimed in this bounded refresh; the parent will rerun docs-freeze proof after all artifact refreshes land.
- Reset proof remains required for the task-root or manifest truth changed in Phase 2; this refresh must not relabel that requirement as `not applicable`.

## Validation

- Read-only sanity on the three owned execution artifacts only.

## Stop Conditions

- Stop if truthful repair would require edits under `scripts/docs/*`, prompt docs or generated examples, app code or tests, or Phase 1 or Phase 3 execution artifacts.
- Stop if the current tree state no longer supports the locked truths above.

## Cross-Links

- Evidence artifact: `../evidence/phase-2-prompt-bootstrap-contract-repair.md`
- Review artifact: `../reviews/phase-2-prompt-bootstrap-contract-repair.md`
