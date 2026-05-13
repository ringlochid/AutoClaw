# Phase 2 Local-Tool-First Prompt And Task-Root Evidence

Status: Reference

selected phase: Phase 2
current phase page: docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md
selected work packages: P2-WP1, P2-WP2, P2-WP3
summary-only: no
delegated slices: listed
slice id: phase2-prompt-source-legality
slice type: edit
owned surfaces: apps/api/app/runtime/prompt/assets/**, narrow apps/api/app/runtime/prompt/** render surfaces, apps/api/tests/unit/runtime_prompt_rendering/**, docs/redesign/prompt-layer/**, docs/redesign/prompt-layer/generated/**, scripts/docs/prompt_catalog/**
touched surfaces: apps/api/app/runtime/prompt/assets/**, apps/api/app/runtime/prompt/sections/rendering.py, apps/api/tests/unit/runtime_prompt_rendering/**, docs/redesign/prompt-layer/**, docs/redesign/prompt-layer/generated/rendered-examples.md, scripts/docs/prompt_catalog/**
slice id: phase2-stable-manifest-parity
slice type: edit
owned surfaces: apps/api/app/runtime/projection/manifest/**, apps/api/app/runtime/projection/dispatch/** when needed for manifest parity, apps/api/app/runtime/task_root/**, narrow apps/api/app/runtime/launch/bootstrap/** helpers, apps/api/tests/integration/phase2/bootstrap/**, apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py
touched surfaces: apps/api/app/runtime/projection/manifest/**, apps/api/app/runtime/projection/runtime_state.py, apps/api/app/runtime/task_root/**, apps/api/tests/integration/phase2/bootstrap/**, apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py
slice id: phase2-structural-edit-palette
slice type: edit
owned surfaces: apps/api/app/runtime/contracts.py, apps/api/app/runtime/contract_models/{launch,projection}.py, apps/api/app/runtime/launch/bootstrap/manifest.py, apps/api/app/runtime/projection/manifest/{structural_palette.py,tree.py}, apps/api/app/runtime/prompt/{bundle.py,instructions.py,sections/rendering.py,structural_edit_palette.py}, apps/api/tests/unit/runtime_prompt_rendering/**, apps/api/tests/integration/phase2/bootstrap/**, docs/redesign/prompt-layer/generated/rendered-examples.md, scripts/docs/prompt_catalog/**
touched surfaces: apps/api/app/runtime/contracts.py, apps/api/app/runtime/contract_models/{launch,projection}.py, apps/api/app/runtime/launch/bootstrap/manifest.py, apps/api/app/runtime/projection/manifest/{structural_palette.py,tree.py}, apps/api/app/runtime/prompt/{bundle.py,instructions.py,sections/rendering.py,structural_edit_palette.py}, apps/api/tests/unit/runtime_prompt_rendering/**, apps/api/tests/integration/phase2/bootstrap/**, docs/redesign/prompt-layer/generated/rendered-examples.md, scripts/docs/prompt_catalog/**
slice id: phase2-current-doc-and-closeout-refresh
slice type: edit
owned surfaces: docs/current/interfaces/prompt-layer-and-worker-delivery.md, docs/current/interfaces/current-openclaw-bridge-prompt-strings.md, docs/current/architecture/manifest-projection-and-acknowledgement.md, docs/current/architecture/task-roots-and-materialized-paths.md, docs/execution/plans/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/evidence/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/reviews/phase-2-closeout-prompt-legality-and-proof.md
touched surfaces: docs/current/interfaces/prompt-layer-and-worker-delivery.md, docs/current/interfaces/current-openclaw-bridge-prompt-strings.md, docs/current/architecture/manifest-projection-and-acknowledgement.md, docs/current/architecture/task-roots-and-materialized-paths.md, docs/execution/plans/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/evidence/phase-2-closeout-prompt-legality-and-proof.md, docs/execution/reviews/phase-2-closeout-prompt-legality-and-proof.md

## Slice identity

- selected phase: Phase 2
- approved execution brief served by this evidence: authoritative Phase 2
  prompt/task-root normalization, proof refresh, and record repair for the
  full Phase 2 package set
- date: 2026-05-13
- owned surface:
  `docs/execution/evidence/phase-2-closeout-prompt-legality-and-proof.md`
- evidence source for this record:
  repo-local Phase 2 prompt, manifest, task-root, and current-doc surfaces
  plus the rerun proof commands listed below

## Plan and review links

- approved plan: `../plans/phase-2-closeout-prompt-legality-and-proof.md`
- mandatory review: `../reviews/phase-2-closeout-prompt-legality-and-proof.md`
- review artifact: `../reviews/phase-2-closeout-prompt-legality-and-proof.md`

## Authoritative evidence rule

- this file is the authoritative `summary-only: no` Phase 2 closeout evidence
  record
- it records fresh proof for the landed Phase 2 prompt, manifest, task-root,
  current-doc, and prompt-tooling work
- it does not claim that Phase 3 runtime-truth fixes, route-layer structural
  orchestration cleanup, or no-open-dispatch checkpoint selection repair have
  already landed

## Artifacts changed

- runtime prompt package:
  `apps/api/app/runtime/prompt/assets/**`,
  `apps/api/app/runtime/prompt/bundle.py`,
  `apps/api/app/runtime/prompt/instructions.py`,
  `apps/api/app/runtime/prompt/sections/`, and
  `apps/api/app/runtime/prompt/structural_edit_palette.py`
- runtime projection and task-root package:
  `apps/api/app/runtime/projection/manifest/**`,
  `apps/api/app/runtime/projection/dispatch/**`,
  `apps/api/app/runtime/projection/runtime_state.py`,
  `apps/api/app/runtime/task_root/**`, and
  narrow `apps/api/app/runtime/launch/bootstrap/**`
- prompt and bootstrap proof tests:
  `apps/api/tests/unit/runtime_prompt_rendering/**`,
  `apps/api/tests/integration/phase2/bootstrap/**`, and
  `apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`
- phase-scoped prompt-layer owner docs, generated prompt examples, and
  `scripts/docs/prompt_catalog/**`
- truthful current-contrast surfaces:
  `docs/current/interfaces/prompt-layer-and-worker-delivery.md`,
  `docs/current/interfaces/current-openclaw-bridge-prompt-strings.md`,
  `docs/current/architecture/manifest-projection-and-acknowledgement.md`, and
  `docs/current/architecture/task-roots-and-materialized-paths.md`

## Phase 2 changes captured by this evidence

- prompt-source alignment now teaches structural edits only through the surfaced
  compact `structural_edit_palette`, keeps parent/root `yield` wording tied to
  one staged child assignment, keeps root-only `blocked`, and regenerates the
  rendered prompt examples
- Phase 2-owned task-root and projection surfaces now teach the synchronous
  local-task-root contract for the stable reread path instead of a generic
  queued refresh model
- manifest and current-doc alignment now teaches `manifest_version`, top-level
  `structural_edit_palette`, per-node `policy`, and the dedicated
  `latest_relevant_checkpoint_path` carrier instead of inferring checkpoint
  context from surfaced checkpoint order
- current docs are explicit that the no-open-dispatch checkpoint fallback still
  exists as current behavior and remains a Phase 3 runtime debt rather than a
  closed Phase 2 contract

## Proof run for this rebuild

- `./.venv/bin/python -m scripts.docs.prompt_catalog.cli generate`
  - result: passed with exit code `0`; no console output
- `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate`
  - result: `Prompt catalog validation passed.`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
  - result: passed with `No findings.`
- exact repo search:
  - `rg -n "from .* import _|import .*\\._" apps/api/app/runtime/prompt apps/api/app/runtime/projection apps/api/app/runtime/task_root apps/api/app/runtime/launch apps/api/tests/unit/runtime_prompt_rendering apps/api/tests/integration/phase2/bootstrap apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py scripts/docs/prompt_catalog docs/redesign/prompt-layer docs/current/interfaces/prompt-layer-and-worker-delivery.md docs/current/interfaces/current-openclaw-bridge-prompt-strings.md docs/current/architecture/manifest-projection-and-acknowledgement.md docs/current/architecture/task-roots-and-materialized-paths.md`
  - result: no matches; no cross-module underscore-private imports found in the
    Phase 2 code, tests, docs tooling, redesign docs, or owned current docs
- `./.venv/bin/ruff check apps/api/app/runtime/prompt apps/api/app/runtime/projection apps/api/app/runtime/task_root apps/api/app/runtime/launch apps/api/tests/unit/runtime_prompt_rendering apps/api/tests/integration/phase2/bootstrap apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py scripts/docs/prompt_catalog`
  - result: `All checks passed!`
- `./.venv/bin/ruff check scripts/docs`
  - result: `All checks passed!`
- `./.venv/bin/mypy apps/api/app/runtime/prompt apps/api/app/runtime/projection apps/api/app/runtime/task_root apps/api/app/runtime/launch apps/api/tests/unit/runtime_prompt_rendering apps/api/tests/integration/phase2/bootstrap scripts/docs/prompt_catalog`
  - result: `Success: no issues found in 80 source files`
- `./.venv/bin/mypy scripts/docs`
  - result: `Success: no issues found in 54 source files`
- `make pyright-api`
  - result: `0 errors, 0 warnings, 0 informations`
- `./.venv/bin/pytest -q apps/api/tests/unit/runtime_prompt_rendering apps/api/tests/integration/phase2/bootstrap apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`
  - result: `78 passed in 38.67s`

## Docs-freeze follow-up

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli validate`
  - result before this rebuild: failed on missing Phase 2 delegated-slice body
    briefs and missing Phase 2 proof tokens, plus known Phase 3 artifact gaps
  - result after this rebuild: Phase 2 errors are expected to clear; any
    remaining failure belongs to the out-of-scope Phase 3 closeout artifacts

## Phase 3 deferrals kept truthful

- this evidence does not claim queued-effect currentness fixes, route-layer
  structural manifest orchestration cleanup, or typed runtime-failure
  normalization
- the current docs are now explicit where current behavior still depends on a
  later Phase 3 runtime cleanup
- Phase 2 closure remains limited to prompt/render, manifest/readback,
  task-root/bootstrap, and truthful current-doc repair

## Residual blockers

- none
