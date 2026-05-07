# Phase 2 Closeout Prompt Legality and Proof Routing

Status: Reference

selected phase: Phase 2
current phase page: docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md
selected work packages: P2-WP1, P2-WP2, P2-WP3
summary-only: no
delegated slices: listed
slice id: phase2-controller-context
slice type: edit
owned surfaces: apps/api/app/runtime/projection/state.py, apps/api/app/runtime/projection/materialize.py, apps/api/tests/integration/test_phase2_runtime_bootstrap.py, docs/redesign/architecture/manifest-contract.md, docs/redesign/architecture/worker-context-contract.md, docs/redesign/prompt-layer/source-and-sections.md, docs/current/architecture/manifest-projection-and-acknowledgement.md, docs/current/architecture/task-roots-and-materialized-paths.md
touched surfaces: apps/api/app/runtime/projection/state.py, apps/api/app/runtime/projection/materialize.py, apps/api/tests/integration/test_phase2_runtime_bootstrap.py, docs/redesign/architecture/manifest-contract.md, docs/redesign/architecture/worker-context-contract.md, docs/redesign/prompt-layer/source-and-sections.md, docs/current/architecture/manifest-projection-and-acknowledgement.md, docs/current/architecture/task-roots-and-materialized-paths.md
slice id: phase2-prompt-assets
slice type: edit
owned surfaces: apps/api/app/runtime/prompt/asset_catalog.py, scripts/docs/prompt_catalog_tools.py, apps/api/tests/unit/test_runtime_prompt_assets.py, docs/redesign/prompt-layer/contract.md, docs/redesign/prompt-layer/generated/README.md, docs/redesign/prompt-layer/generated/rendered-examples.md, docs/redesign/prompt-layer/prompt-pack/README.md, docs/redesign/prompt-layer/prompt-pack/system-and-provider-block.md, docs/current/interfaces/prompt-layer-and-worker-delivery.md
touched surfaces: apps/api/app/runtime/prompt/asset_catalog.py, scripts/docs/prompt_catalog_tools.py, apps/api/tests/unit/test_runtime_prompt_assets.py, docs/redesign/prompt-layer/contract.md, docs/redesign/prompt-layer/generated/README.md, docs/redesign/prompt-layer/generated/rendered-examples.md, docs/redesign/prompt-layer/prompt-pack/README.md, docs/redesign/prompt-layer/prompt-pack/system-and-provider-block.md, docs/current/interfaces/prompt-layer-and-worker-delivery.md
slice id: phase2-docs-tooling
slice type: edit
owned surfaces: docs/redesign/prompt-layer/render-and-persistence.md, docs/redesign/prompt-layer/prompt-catalog.yaml, docs/redesign/prompt-layer/prompt-resource-usage-appendix.md, docs/redesign/prompt-layer/generated/inventory.md
touched surfaces: docs/redesign/prompt-layer/render-and-persistence.md, docs/redesign/prompt-layer/prompt-resource-usage-appendix.md
slice id: phase2-closeout-artifacts
slice type: edit
owned surfaces: docs/execution/plans/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/evidence/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/reviews/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/plans/phase-2-prompt-bootstrap-contract-repair.md, docs/execution/evidence/phase-2-prompt-bootstrap-contract-repair.md, docs/execution/reviews/phase-2-prompt-bootstrap-contract-repair.md
touched surfaces: docs/execution/plans/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/evidence/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/reviews/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/plans/phase-2-prompt-bootstrap-contract-repair.md, docs/execution/evidence/phase-2-prompt-bootstrap-contract-repair.md, docs/execution/reviews/phase-2-prompt-bootstrap-contract-repair.md
slice id: phase2-audit
slice type: review-only
owned surfaces: none
touched surfaces: none
slice id: phase2-minimal-e2e
slice type: edit
owned surfaces: apps/api/tests/e2e/*
touched surfaces: apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py

## Slice identity

- selected phase: Phase 2
- work package or slice: authoritative closeout-path prep for live prompt
  legality, criteria-owner consumption, raw delivery-state truth,
  package-install proof, reset-gate applicability, minimal-e2e viability
  routing, and prompt-family cleanup across `P2-WP1` through `P2-WP3`
- owner: Codex
- date: 2026-05-07
- execution mode: owned closeout-artifact refresh plus local prompt-source and
  projection cleanup

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`

## Closeout focus

- make this chain the only `summary-only: no` Phase 2 closeout-path record in
  the owned surfaces
- scope authority to the live Phase 2 closeout issues only:
  - prompt legality
  - criteria-owner consumption
  - raw delivery-state truth
  - package-install proof
  - reset-gate applicability and outcome
  - minimal-e2e viability status
- attach the reset-gate decision explicitly:
  - applicable because the integrated Phase 2 slice changed task-root
    bootstrap and manifest or task-root projection behavior named by the Phase
    2 reset criteria
  - package reinstall remains not triggered unless prompt-asset package-data
    changed
- inspect the shared worktree before finalizing minimal-e2e wording instead of
  repeating the earlier placeholder claim
- record any reopened Phase 2 STYLE exceptions on touched oversized surfaces
  that remain unsplit after this cleanup
- demote the older `phase-2-prompt-bootstrap-contract-repair*` chain to
  historical support only
- keep final proof outcomes parent-attached in the new evidence artifact after
  integration instead of inventing them here
- the live Phase 2 closeout surfaces for this refresh are
  `apps/api/app/runtime/prompt/asset_catalog.py`,
  `scripts/docs/prompt_catalog_tools.py`,
  `apps/api/app/runtime/projection/state.py`,
  `apps/api/app/runtime/projection/materialize.py`,
  `apps/api/tests/unit/test_runtime_prompt_assets.py`,
  `apps/api/tests/integration/test_phase2_runtime_bootstrap.py`,
  `docs/redesign/prompt-layer/contract.md`,
  `docs/redesign/prompt-layer/generated/README.md`,
  `docs/redesign/prompt-layer/generated/rendered-examples.md`,
  `docs/redesign/prompt-layer/prompt-pack/README.md`,
  `docs/redesign/prompt-layer/prompt-pack/system-and-provider-block.md`,
  `docs/redesign/prompt-layer/source-and-sections.md`,
  `docs/redesign/architecture/manifest-contract.md`,
  `docs/redesign/architecture/worker-context-contract.md`,
  `docs/current/architecture/manifest-projection-and-acknowledgement.md`,
  `docs/current/architecture/task-roots-and-materialized-paths.md`, and
  `docs/current/interfaces/prompt-layer-and-worker-delivery.md`

## Scope mapping

- `P2-WP1`: route prompt legality, prompt-family and node-kind legality,
  `same_session_continue` transport-only truth, and prompt-catalog alignment as
  explicit closure obligations
- `P2-WP2`: route Phase 1 criteria-owner consumption into manifest, assignment,
  worker-context, and prompt-read surfaces without rewriting durable criteria
  ownership or turning observability-only delivery-state files into ordinary
  worker context
- `P2-WP3`: route bootstrap and materialization closeout proof so package
  install, shipped prompt-asset delivery, and minimal-e2e viability are stated
  explicitly rather than inferred from earlier bootstrap summaries

## Truths to encode

- the only authoritative Phase 2 work-package ids in this chain are
  `P2-WP1`, `P2-WP2`, and `P2-WP3`
- prompt legality is a live Phase 2 closeout obligation:
  - prompts must stay inside the two canonical prompt families
  - `full_prompt` and `same_session_continue` remain the only canonical send
    modes
  - `same_session_continue` stays transport-only and must not change prompt
    truth
  - exact shipped prompt blocks load byte-for-byte from packaged assets, and
    prompt-pack mirrors plus generated examples must match those bytes
- Phase 2 must consume the Phase 1 criteria-owner contract truthfully:
  - declaring-node ownership remains the durable criteria truth
  - assignment or manifest or prompt surfaces still expose exact current
    criteria refs rather than widening ordinary criteria carriers into
    controller-only ownership payloads
  - parent/root reread uses controller-selected relevant-checkpoint truth when
    the controller staged it, rather than recomputing that choice from a
    generic surfaced-ref heuristic
  - release-turn descendant evidence may surface from explicit controller
    staging instead of only direct-child auto discovery
- raw `delivery-state.json`, `continuity-state.json`, `watchdog-state.json`,
  and `provider-events.ndjson` remain observability-only support projections:
  - they are not ordinary `current_relevant_paths`
  - they are not ordinary worker context
  - they are not substitute proof that criteria were satisfied
- package-install proof is required only when the integrated Phase 2 slice
  changed narrow prompt-asset package-data truth; the final evidence must say
  either:
  - exact shipped-path proof passed
  - package-install proof was not triggered because no such package-data delta
    landed
- reset-gate applicability must be explicit in the final evidence and review:
  - Phase 2 closeout cannot leave the gate as `not decided`
  - if task-root or manifest or bootstrap truth changed, the evidence must
    attach the shipped-path reset or readiness proof command and outcome
- minimal e2e remains required only when viable; the final evidence must say
  either:
  - exact minimal-lane proof passed
  - the lane is not yet viable and the blocker is named exactly from the
    current shared worktree state
- the older `phase-2-prompt-bootstrap-contract-repair*` chain becomes
  historical support only after this chain lands and may not remain apparent
  Phase 2 closure authority

## Required proof before closeout

- focused prompt-render or prompt-catalog proof for prompt legality and
  send-mode legality
- focused proof that Phase 2 consumes compiler-owned criteria ownership without
  rewriting the durable owner to the consumer node
- focused proof that raw delivery-state and related dispatch projections stay
  observability-only and out of ordinary worker-visible runtime context
- package-install verification when narrow prompt-asset package-data changed
- shipped-path reset or readiness proof when the integrated Phase 2 task-root
  or manifest or bootstrap changes make the reset gate applicable
- minimal e2e lane proof when viable, otherwise an exact blocker record

## Evidence routing

- this artifact does not claim final proof outcomes
- the parent will attach exact command results in
  `../evidence/phase-2-closeout-prompt-legality-and-proof.md` after
  integration
- the superseded prompt-bootstrap chain remains supporting history only:
  `../evidence/phase-2-prompt-bootstrap-contract-repair.md`

## Validation checkpoints

- the top-level parseable label block stays exact
- this new chain is the only `summary-only: no` Phase 2 closeout-path artifact
  family in the owned surfaces
- the old prompt-bootstrap chain is marked `summary-only: yes`
- if the shared worktree lands a runnable Phase 2 minimal lane before
  finalization, the evidence records that exact command result instead of
  preserving the earlier placeholder blocker wording
- the final review records any reopened `STYLE.md` oversize exception on
  touched unsplit Phase 2 surfaces
- no proof result is claimed here unless the new evidence artifact records the
  exact command outcome or exact non-viability blocker

## Stop conditions

- stop if truthful routing would require edits outside the owned Phase 2
  execution artifacts
- stop if closure would require changing Phase 0-owned gates, maps, or phase
  pages instead of recording the obligation here

## Cross-links

- evidence artifact:
  `../evidence/phase-2-closeout-prompt-legality-and-proof.md`
- review artifact:
  `../reviews/phase-2-closeout-prompt-legality-and-proof.md`
- superseded historical support:
  `../plans/phase-2-prompt-bootstrap-contract-repair.md`
  `../evidence/phase-2-prompt-bootstrap-contract-repair.md`
  `../reviews/phase-2-prompt-bootstrap-contract-repair.md`
