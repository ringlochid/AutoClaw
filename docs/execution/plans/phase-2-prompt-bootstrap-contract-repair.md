# Phase 2 Prompt, Checkpoint, and Bootstrap Contract Repair

Status: Reference

## Slice identity

- selected phase: Phase 2
- work package or slice: prompt rendering, surfaced checkpoint handoff, transient-index, and truthful same-session proof
- owner: Codex
- date: 2026-05-05

## Subagents decision

- delegated slices:
  - surfaced checkpoint handoff and transient-index materialization
  - Task Memory and field-renderer alignment
  - prompt catalog/generated examples and truthful same-session proof story
  - review-only Phase 2 audit

## Goal

- make the Phase 2-owned prompt/render/materialization surfaces match canon on
  surfaced checkpoint handoff, Task Memory, transient carryover, field-renderer
  shape, and proof story without widening into Phase 3 or Phase 4A ownership

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
- `Task Memory` includes assignment hints, surfaced curated refs, and checkpoint hints
- `transient-index.json` includes assignment-staged transient carryover before first checkpoint
- live renderer output matches canonical field-renderer shape
- generated examples and prompt validation cover representative runtime states
- same-session Phase 2 proof is truthful: renderer/persisted request behavior is proven, but live dispatch-opening selection is not overclaimed

## Deliverables and milestones

- deliverables:
  - landed checkpoint-handoff fix
  - landed transient-index fix
  - landed Task Memory and renderer-shape fix
  - regenerated prompt examples and validator inputs
  - narrowed same-session proof story
  - Phase 2 plan/evidence/review artifacts
- milestones:
  - checkpoint/transient repair landed
  - Task Memory/field-renderer parity landed
  - generated examples and validator green
  - truthful same-session boundary documented

## Ordered work packages

- `P2-WP1`: surfaced checkpoint handoff repair
- `P2-WP2`: pre-checkpoint transient-index repair
- `P2-WP3`: Task Memory and field-renderer alignment
- `P2-WP4`: prompt-catalog/generated-example realism
- `P2-WP5`: truthful same-session proof and current-doc wording
- `P2-WP6`: Phase 2 evidence and review

## Validation checkpoints

- prompt catalog generate/validate passes
- focused prompt-render unit lane passes
- focused bootstrap/materialization integration lane passes
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
