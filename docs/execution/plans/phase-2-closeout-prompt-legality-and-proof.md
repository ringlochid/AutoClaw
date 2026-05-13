# Phase 2 Local-Tool-First Prompt And Task-Root Plan

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
- approved execution brief: authoritative Phase 2 prompt/task-root
  normalization, proof refresh, and record repair for the full Phase 2
  package set
- date: 2026-05-13
- execution mode: record repair and proof refresh only; no new Phase 2 code,
  prompt, generated-doc, or current-doc edit is performed in this slice
  beyond recording the landed local-tool-first sync task-root contract
  truthfully

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`
- landing map rows used for answer-sourcing and proof routing:
  `prompt contract and rendered delivery`,
  `manifest, worker context, task-root, and artifact materialization`, and
  `explicit split from runtime persistence truth`

## Objective

- normalize the authoritative Phase 2 plan, evidence, and review into
  validator-compliant repo-local execution records
- keep the chain truthful to the landed Phase 2 work:
  - the prompt-source slice aligned structural-edit naming to the surfaced
    compact `structural_edit_palette`, tightened parent/root `yield` wording,
    kept root-only `blocked`, and regenerated prompt examples
  - the manifest/current-doc slice aligned `manifest_version`,
    top-level `structural_edit_palette`, per-node `policy`, and current-doc
    wording around checkpoint-handoff carriers while explicitly keeping the
    no-open-dispatch checkpoint fallback as Phase 3 runtime debt
  - the closeout chain must not claim that Phase 3 runtime-truth fixes, route
    orchestration cleanup, or controller-currentness repair already landed
- record fresh proof for prompt-catalog generation and validation, prompt/docs
  tooling lint and typing, style audit, private-symbol search, backend typing,
  and the Phase 2 prompt/bootstrap pytest lanes

## Scope and truth constraints

- owned edit surfaces for this slice:
  - `docs/execution/plans/phase-2-closeout-prompt-legality-and-proof.md`
  - `docs/execution/evidence/phase-2-closeout-prompt-legality-and-proof.md`
  - `docs/execution/reviews/phase-2-closeout-prompt-legality-and-proof.md`
- landed Phase 2 surfaces that this chain must describe truthfully:
  - app-owned prompt assets and render surfaces under
    `apps/api/app/runtime/prompt/**`
  - manifest, dispatch, task-root, and narrow launch-bootstrap Phase 2
    surfaces under `apps/api/app/runtime/projection/**`,
    `apps/api/app/runtime/task_root/**`, and
    `apps/api/app/runtime/launch/bootstrap/**`
  - prompt unit, Phase 2 bootstrap integration, and minimal e2e proof under
    `apps/api/tests/unit/runtime_prompt_rendering/**`,
    `apps/api/tests/integration/phase2/bootstrap/**`, and
    `apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`
  - prompt-layer owner/generated docs, manifest/task-root/current docs, and
    `scripts/docs/prompt_catalog/**`
- do not claim:
  - Phase 3 runtime-truth fixes for queued-effect currentness, structural route
    timing ownership, or no-open-dispatch checkpoint selection
  - a new Phase 2 code or doc landing performed by this artifact-only slice
  - a repo-wide `docs_freeze` pass if remaining failures are outside Phase 2

## Delegated slice briefs

### phase2-prompt-source-legality

- do-not-edit surfaces:
  - runtime persistence and control surfaces under `apps/api/app/runtime/control/**`
  - current docs under `docs/current/**`
  - execution artifacts outside the selected Phase 2 triplet
- required reads:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs/execution/README.md`
  - `docs/execution/maps/file-priority-map.md`
  - `docs/execution/maps/redesign-code-landing-map.md`
  - `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
  - `docs/execution/gates/mandatory-review-gate.md`
  - `docs/execution/gates/reset-gate.md`
  - `docs/execution/gates/code-quality-gate.md`
  - `docs/redesign/prompt-layer/contract.md`
  - `docs/redesign/prompt-layer/source-and-sections.md`
  - `docs/redesign/prompt-layer/field-renderers.md`
  - `docs/redesign/prompt-layer/machine-contract.md`
  - `docs/redesign/prompt-layer/prompt-catalog.yaml`
  - `docs/redesign/prompt-layer/prompt-pack/system-and-provider-block.md`
  - `docs/redesign/prompt-layer/prompt-pack/runtime-rule-blocks.md`
  - `docs/redesign/prompt-layer/generated/rendered-examples.md`
  - the repo-local prompt assets, redesign docs, generated examples, and
    prompt-catalog surfaces listed in this Phase 2 plan
- required tests/validators:
  - `./.venv/bin/python -m scripts.docs.prompt_catalog.cli generate`
  - `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate`
  - `./.venv/bin/ruff check apps/api/app/runtime/prompt apps/api/tests/unit/runtime_prompt_rendering scripts/docs/prompt_catalog`
  - `./.venv/bin/mypy apps/api/app/runtime/prompt scripts/docs/prompt_catalog`
  - `./.venv/bin/pytest -q apps/api/tests/unit/runtime_prompt_rendering`
- expected outputs:
  - shipped prompt assets, prompt docs, prompt-catalog, and generated examples
    teach the same structural-edit and boundary wording
  - generated prompt examples are regenerated after prompt-source changes
- dependencies:
  - Phase 1 complete
- evidence to return:
  - changed prompt assets/docs/example inventory
  - prompt-catalog and prompt-render proof results
- parent-owned decisions:
  - whether any remaining prompt wording dispute is truly Phase 2-owned or is a
    Phase 3 runtime legality issue
- stop conditions:
  - stop if the truthful fix requires editing runtime control, closure, or
    currentness surfaces that the Phase 2 page defers to Phase 3

### phase2-stable-manifest-parity

- do-not-edit surfaces:
  - runtime control and checkpoint-currentness ownership under
    `apps/api/app/runtime/control/**`
  - API route orchestration under `apps/api/app/api/routes/**`
  - later-phase execution artifacts
- required reads:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs/execution/README.md`
  - `docs/execution/maps/file-priority-map.md`
  - `docs/execution/maps/redesign-code-landing-map.md`
  - `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
  - `docs/redesign/architecture/manifest-contract.md`
  - `docs/redesign/architecture/worker-context-contract.md`
  - `docs/redesign/architecture/task-root-layout-and-generated-files.md`
  - `docs/redesign/architecture/artifact-ref-and-storage-contract.md`
  - `docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md`
  - `docs/current/architecture/manifest-projection-and-acknowledgement.md`
  - `docs/current/architecture/task-roots-and-materialized-paths.md`
  - the current Phase 2 triplet
- required tests/validators:
  - `./.venv/bin/ruff check apps/api/app/runtime/projection apps/api/app/runtime/task_root apps/api/app/runtime/launch apps/api/tests/integration/phase2/bootstrap apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`
  - `./.venv/bin/mypy apps/api/app/runtime/projection apps/api/app/runtime/task_root apps/api/app/runtime/launch apps/api/tests/integration/phase2/bootstrap`
  - `./.venv/bin/pytest -q apps/api/tests/integration/phase2/bootstrap apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`
- expected outputs:
  - manifest/task-root/current docs and proof tests reflect the landed Phase 2
    stable-manifest behavior
  - Phase 2 closeout wording stays explicit that no-open-dispatch checkpoint
    fallback remains Phase 3 debt
- dependencies:
  - `P2-WP1`
- evidence to return:
  - manifest/task-root/current-doc surface inventory
  - bootstrap integration and minimal e2e results
- parent-owned decisions:
  - whether a remaining checkpoint-handoff gap belongs to Phase 2 readback
    truth or Phase 3 controller-owned currentness truth
- stop conditions:
  - stop if a required fix would need runtime assignment, attempt, checkpoint,
    or release truth edits outside the Phase 2-owned readback surfaces

### phase2-structural-edit-palette

- do-not-edit surfaces:
  - runtime control, assignment, release, and callback-route ownership
  - Phase 3 current docs or execution artifacts
- required reads:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs/execution/README.md`
  - `docs/execution/maps/file-priority-map.md`
  - `docs/execution/maps/redesign-code-landing-map.md`
  - `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
  - `docs/redesign/prompt-layer/contract.md`
  - `docs/redesign/prompt-layer/source-and-sections.md`
  - `docs/redesign/prompt-layer/field-renderers.md`
  - `docs/redesign/prompt-layer/machine-contract.md`
  - `docs/redesign/architecture/manifest-contract.md`
  - `docs/redesign/architecture/worker-context-contract.md`
  - the current Phase 2 triplet
- required tests/validators:
  - `./.venv/bin/python -m scripts.docs.prompt_catalog.cli generate`
  - `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate`
  - `./.venv/bin/ruff check apps/api/app/runtime/prompt apps/api/app/runtime/projection apps/api/app/runtime/launch apps/api/tests/unit/runtime_prompt_rendering apps/api/tests/integration/phase2/bootstrap scripts/docs/prompt_catalog`
  - `./.venv/bin/mypy apps/api/app/runtime/prompt apps/api/app/runtime/projection apps/api/app/runtime/launch apps/api/tests/unit/runtime_prompt_rendering apps/api/tests/integration/phase2/bootstrap scripts/docs/prompt_catalog`
  - `./.venv/bin/pytest -q apps/api/tests/unit/runtime_prompt_rendering apps/api/tests/integration/phase2/bootstrap`
- expected outputs:
  - prompt and manifest readback surface a compact registry-backed
    `structural_edit_palette`
  - prompt-catalog and generated examples remain synchronized with the shipped
    prompt source
- dependencies:
  - `P2-WP1`, `P2-WP2`
- evidence to return:
  - changed prompt/readback model inventory
  - regenerated prompt examples and prompt-catalog proof
- parent-owned decisions:
  - whether a remaining legality mismatch is Phase 2 prompt/readback scope or
    Phase 3 continuation legality scope
- stop conditions:
  - stop if the truthful fix requires runtime controller-truth or route-layer
    timing changes outside the Phase 2 lock

### phase2-current-doc-and-closeout-refresh

- do-not-edit surfaces:
  - all repo files outside the four Phase 2 current docs and the selected
    Phase 2 plan, evidence, and review artifacts
- required reads:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs/execution/README.md`
  - `docs/execution/maps/file-priority-map.md`
  - `docs/execution/maps/redesign-code-landing-map.md`
  - `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
  - `docs/execution/gates/mandatory-review-gate.md`
  - `docs/execution/gates/reset-gate.md`
  - `docs/execution/gates/code-quality-gate.md`
  - the current Phase 2 plan, evidence, and review
  - the current `docs_freeze` failure output for missing delegated-slice body
    briefs and missing Phase 2 proof tokens
  - the repo-local Phase 2 prompt, manifest, task-root, and current-doc
    surfaces listed in this plan and the matching evidence/review artifacts
- required tests/validators:
  - `./.venv/bin/python -m scripts.docs.docs_freeze.cli validate`
- expected outputs:
  - validator-compliant delegated-slice body briefs for all listed Phase 2
    slices
  - rewritten evidence and review text that record fresh `style_audit`,
    prompt-catalog generate/validate, scripts/docs lint/typing, exact repo
    search, backend typing, and pytest proof
  - truthful current-doc and closeout wording that keeps Phase 3 runtime-truth
    work deferred
- dependencies:
  - fresh proof results from the rerun validators and tests
  - landed prompt-source and manifest/current-doc slice summaries
- evidence to return:
  - updated plan/evidence/review artifacts
  - `docs_freeze` result showing no remaining Phase 2-specific validator error
- parent-owned decisions:
  - whether remaining repo-level `docs_freeze` failures are treated as the next
    Phase 3 slice instead of a blocker for Phase 2 closure repair
- stop conditions:
  - stop if truthful repair would require editing code, prompt docs, generated
    docs, or current docs outside the owned surfaces listed above

## Validation checkpoints

- delegated-slice body briefs exist for all four listed Phase 2 slices and
  include every required field from the new validator
- the rewritten evidence and review include truthful `style_audit` proof,
  exact repo search or underscore-private proof language, and the exact
  `prompt_catalog generate`, `ruff check scripts/docs`, and
  `mypy scripts/docs` tokens the validator expects
- the rewritten evidence and review describe the landed prompt-source and
  manifest/current-doc changes without claiming Phase 3 runtime-truth fixes
- `docs_freeze` no longer reports any Phase 2-specific execution-record error

## Exit criteria

- the authoritative Phase 2 triplet remains the `summary-only: no` closure
  chain for the full Phase 2 package set
- the chain now records the landed prompt-source and manifest/current-doc work
  truthfully, keeps stable-manifest and structural-edit-palette wording aligned
  with the live tree, and keeps Phase 3 runtime-truth fixes deferred
- fresh proof lanes are recorded for prompt-catalog generate/validate,
  `style_audit`, exact repo search, scripts/docs lint/typing, backend typing,
  and the Phase 2 prompt/bootstrap pytest lanes

## Stop conditions

- stop if truthful Phase 2 repair would require touching any code, prompt docs,
  current docs, generated docs, or later-phase execution artifacts outside the
  three owned surfaces of this slice
- stop if rerun proof reveals a real Phase 2 product defect that belongs to a
  new code or doc landing slice instead of this closure-artifact rebuild

## Cross-links

- evidence artifact:
  `../evidence/phase-2-closeout-prompt-legality-and-proof.md`
- review artifact:
  `../reviews/phase-2-closeout-prompt-legality-and-proof.md`
