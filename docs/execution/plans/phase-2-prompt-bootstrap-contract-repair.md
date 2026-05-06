# Phase 2 Prompt, Checkpoint, and Bootstrap Contract Repair

Status: Reference

## Slice identity

- selected phase: Phase 2
- work package or slice: prompt rendering, surfaced checkpoint handoff, transient-index, and truthful same-session proof
- owner: Codex
- date: 2026-05-05

## Delegated slices and return contract

- delegated slices:
  - phase-2 runtime code and tests
    - slice type: `edit`
    - selected phase: Phase 2
    - owned surfaces: `apps/api/app/runtime/contracts.py`, `apps/api/app/runtime/resources.py`, `apps/api/app/runtime/projection/state.py`, `apps/api/app/runtime/projection/materialize.py`, `apps/api/app/runtime/prompt/sections.py`, `apps/api/app/runtime/prompt/bundle.py`, `apps/api/app/runtime/launch/projection.py`, `apps/api/tests/integration/test_phase2_runtime_bootstrap.py`, `apps/api/tests/unit/test_runtime_prompt_rendering.py`
    - do-not-edit surfaces: docs, `scripts/docs/*`, execution artifacts, and Phase 3-owned runtime control/replan files
    - required reads: the full Phase 2 required read set plus the owned runtime/test files
    - expected outputs: task-root localization fix, `latest_relevant_checkpoint_path` split in code, deterministic checkpoint selection, and Phase 2-owned test coverage
    - required validators/tests: focused `ruff check` and Phase 2 unit/integration pytest lanes
    - dependencies: none
    - evidence to return: exact files changed, landed semantics, and command outcomes
    - parent-owned decisions: final docs wording and artifact refresh
    - stop conditions: stop and report if a needed change requires docs/scripts or live Phase 4A continuity behavior
  - phase-2 docs, examples, and prompt validation
    - slice type: `edit`
    - selected phase: Phase 2
    - owned surfaces: Phase 2-owned redesign prompt/manifest/task-root docs, generated prompt examples, `docs/current/interfaces/prompt-layer-and-worker-delivery.md`, and `scripts/docs/prompt_catalog_tools.py` only if needed
    - do-not-edit surfaces: runtime code/tests, `AGENTS.md`, execution artifacts, and non-Phase-2 docs
    - required reads: the full Phase 2 required read set plus prompt docs/examples/tooling
    - expected outputs: doc-teaching of the checkpoint split and localized surfaced files, regenerated examples, and cleared prompt-example drift
    - required validators/tests: `prompt_catalog_tools.py generate`, `prompt_catalog_tools.py validate`, and `ruff check scripts/docs` if scripts change
    - dependencies: phase-2 runtime code and tests slice for the final field names/semantics
    - evidence to return: exact docs/examples/tooling files changed and command outcomes
    - parent-owned decisions: final wording arbitration where docs overlap ambiguously
    - stop conditions: stop and report if a needed change would alter runtime code/tests
  - review-only Phase 2 artifact audit
    - slice type: `review-only`
    - selected phase: Phase 2
    - owned surfaces: none
    - do-not-edit surfaces: all files
    - required reads: the full Phase 2 required read set plus the authoritative Phase 2 plan/evidence/review artifacts
    - expected outputs: exact artifact deltas needed after the code/docs slices land, including reset-gate and Phase 0 blocker clearance evidence
    - required validators/tests: none
    - dependencies: sibling edit slices
    - evidence to return: exact file/line references, keep/fix checklist, and residual compliance gaps
    - parent-owned decisions: actual artifact edits and final verdict
    - stop conditions: review only; do not edit or revert anything
  - review-only Phase 2 correctness audit
    - slice type: `review-only`
    - selected phase: Phase 2
    - owned surfaces: none
    - do-not-edit surfaces: all files
    - required reads: the full Phase 2 required read set plus the owned runtime/test files
    - expected outputs: correctness audit for localization semantics, checkpoint split, deterministic precedence, prompt rendering, and phase-boundary drift
    - required validators/tests: none
    - dependencies: sibling edit slices
    - evidence to return: exact file/line references and an integration audit checklist
    - parent-owned decisions: final rendering/duplication rule and integration verdict
    - stop conditions: review only; do not edit or revert anything

## Goal

- make the Phase 2-owned prompt/render/materialization surfaces match canon on
  task-root-local surfaced resources, current-attempt-only `latest_checkpoint_path`,
  `latest_relevant_checkpoint_path` redispatch handoff, Task Memory, transient
  carryover, field-renderer shape, and proof story without widening into Phase 3
  or Phase 4A ownership

## Phase-local contract

- current phase page: `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
- implementation file lock map: `docs/execution/maps/file-priority-map.md`
- required reads completed: yes

## Locked surfaces

- owned surfaces: prompt/render/materialization services under `apps/api/app/runtime/*`, shipped prompt assets, prompt docs/generated examples, manifest/task-root/worker-context/artifact docs
- allowed collateral surfaces: generated prompt pages, `scripts/docs/*`, current prompt-layer contrast docs, narrow prompt/runtime tests
- do not edit or defer surfaces: runtime DB/currentness/control-state handshake, replacement-dispatch inactivity proof, full gateway/session continuity semantics

## Success criteria

- `Latest Checkpoint Context` resolves from surfaced checkpoint truth, including child/prior-attempt handoff
- surfaced external resources localize under `task_root/tmp/transfers/localized`
- `latest_checkpoint_path` remains current-attempt-only while `latest_relevant_checkpoint_path` carries parent/root redispatch handoff
- `Task Memory` includes assignment hints, surfaced curated refs, and checkpoint hints
- `transient-index.json` includes assignment-staged transient carryover before first checkpoint
- live renderer output matches canonical field-renderer shape
- generated examples and prompt validation cover representative runtime states
- prompt-generated examples clear the prior Phase 0 docs-freeze blocker
- same-session Phase 2 proof is truthful: renderer/persisted request behavior is proven, but live dispatch-opening selection is not overclaimed

## Deliverables and milestones

- deliverables:
  - landed checkpoint-handoff fix
  - landed task-root-local surfaced-resource localization fix
  - landed transient-index fix
  - landed Task Memory and renderer-shape fix
  - regenerated prompt examples and validator inputs
  - narrowed same-session proof story
  - Phase 2 plan/evidence/review artifacts
- milestones:
  - localization/checkpoint/transient repair landed
  - Task Memory/field-renderer parity landed
  - generated examples and validator green
  - prior Phase 0 docs-freeze blocker cleared
  - truthful same-session boundary documented

## Ordered work packages

- `P2-WP1`: task-root-local external surfaced resource localization
- `P2-WP2`: current-attempt-only `latest_checkpoint_path` plus `latest_relevant_checkpoint_path` split
- `P2-WP3`: deterministic parent/root redispatch checkpoint selection and prompt rendering
- `P2-WP4`: pre-checkpoint transient-index and Task Memory/field-renderer parity
- `P2-WP5`: prompt-catalog/generated-example regeneration and current-doc wording
- `P2-WP6`: Phase 2 evidence, review, and reset-gate recording

## Validation checkpoints

- prompt catalog generate/validate passes
- focused prompt-render unit lane passes
- focused bootstrap/materialization integration lane passes
- docs freeze passes and the prior prompt-example drift blocker is cleared
- reset-gate proof is recorded for the task-root/manifest truth change
- docs freeze passes after current-doc/example updates
- repo-native type/lint gates pass for touched Phase 2 Python surfaces

## Required tests and validators

- `./.venv/bin/ruff format --check apps/api/app/runtime/projection/materialize.py apps/api/app/runtime/projection/state.py apps/api/app/runtime/prompt/sections.py apps/api/tests/unit/test_runtime_prompt_rendering.py apps/api/tests/integration/test_phase2_runtime_bootstrap.py scripts/docs/prompt_catalog_tools.py`
- `./.venv/bin/ruff check apps/api/app/runtime/projection/materialize.py apps/api/app/runtime/projection/state.py apps/api/app/runtime/prompt/sections.py apps/api/tests/unit/test_runtime_prompt_rendering.py apps/api/tests/integration/test_phase2_runtime_bootstrap.py scripts/docs/prompt_catalog_tools.py`
- `./.venv/bin/mypy apps/api/app/runtime/projection/materialize.py apps/api/app/runtime/projection/state.py apps/api/app/runtime/prompt/sections.py apps/api/tests/unit/test_runtime_prompt_rendering.py apps/api/tests/integration/test_phase2_runtime_bootstrap.py scripts/docs/prompt_catalog_tools.py`
- `make pyright-api`
- `./.venv/bin/python scripts/docs/prompt_catalog_tools.py generate`
- `./.venv/bin/python scripts/docs/prompt_catalog_tools.py validate`
- `./.venv/bin/python scripts/docs/docs_freeze_validate.py`
- `./.venv/bin/pytest -q apps/api/tests/unit/test_runtime_prompt_rendering.py apps/api/tests/integration/test_phase2_runtime_bootstrap.py`
- reset-gate proof for the task-root/manifest truth change, recorded in evidence

## Required docs and examples

- prompt-layer owner docs and generated examples
- manifest docs
- worker-context docs
- task-root and artifact docs
- current prompt-layer contrast docs where same-session proof wording changed

## Exit evidence

- evidence artifact: `../evidence/phase-2-prompt-bootstrap-contract-repair.md`

## Rollback or stop conditions

- stop if a fix requires editing full runtime control/release semantics instead of Phase 2-owned prompt/materialization surfaces
- stop if live same-session dispatch opening would require gateway/session continuity state that belongs to Phase 4A
- stop if a separate minimal e2e lane becomes clearly viable only after Phase 3-owned runtime closure/control truth lands

## Cross-links

- evidence artifact: `../evidence/phase-2-prompt-bootstrap-contract-repair.md`
- review artifact: `../reviews/phase-2-prompt-bootstrap-contract-repair.md`
