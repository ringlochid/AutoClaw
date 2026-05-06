# Phase 2 Closeout Prompt Legality and Proof Routing

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

## Slice identity

- selected phase: Phase 2
- work package or slice: authoritative closeout-path prep for live prompt
  legality, criteria-owner consumption, raw delivery-state truth,
  package-install proof, and minimal-e2e viability routing across `P2-WP1`
  through `P2-WP3`
- owner: Codex
- date: 2026-05-06
- execution mode: owned execution-artifact rewrite only

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
  - minimal-e2e viability status
- demote the older `phase-2-prompt-bootstrap-contract-repair*` chain to
  historical support only
- keep final proof outcomes parent-attached in the new evidence artifact after
  integration instead of inventing them here

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
- Phase 2 must consume the Phase 1 criteria-owner contract truthfully:
  - declaring-node ownership remains the durable criteria truth
  - assignment or manifest or prompt surfaces still expose exact current
    criteria refs rather than widening ordinary criteria carriers into
    controller-only ownership payloads
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
- minimal e2e remains required only when viable; the final evidence must say
  either:
  - exact minimal-lane proof passed
  - the lane is not yet viable and the blocker is named exactly
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
