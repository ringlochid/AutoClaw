# Phase 2 Prompt, Checkpoint, and Bootstrap Contract Repair Evidence

Status: Reference

## Slice identity

- selected phase: Phase 2
- work package or slice: prompt rendering, surfaced checkpoint handoff, transient-index, and truthful same-session proof
- date: 2026-05-05

## Plan link

- approved plan: `../plans/phase-2-prompt-bootstrap-contract-repair.md`

## Delegated slice return log

- wave 3 delegated slices:
  - phase-2 runtime code and tests
    - slice type: `edit`
    - owned surfaces: `apps/api/app/runtime/contracts.py`, `apps/api/app/runtime/resources.py`, `apps/api/app/runtime/projection/state.py`, `apps/api/app/runtime/projection/materialize.py`, `apps/api/app/runtime/prompt/sections.py`, `apps/api/app/runtime/prompt/bundle.py`, `apps/api/app/runtime/launch/projection.py`, `apps/api/tests/integration/test_phase2_runtime_bootstrap.py`, `apps/api/tests/unit/test_runtime_prompt_rendering.py`
    - required reads: the full Phase 2 required read set plus the owned runtime/test files
    - expected outputs: task-root localization fix, checkpoint-field split in code, deterministic redispatch handoff, and Phase 2-owned tests
    - required validators/tests: focused `ruff check` and Phase 2 unit/integration pytest lanes
    - dependencies: none
    - evidence requested: exact files changed, landed semantics, and command outcomes
    - returned evidence: external surfaced resources now localize under `task_root/tmp/transfers/localized`; `latest_checkpoint_path` stays current-attempt-only; `latest_relevant_checkpoint_path` drives redispatch handoff; focused `ruff check` passed; `pytest -q apps/api/tests/unit/test_runtime_prompt_rendering.py apps/api/tests/integration/test_phase2_runtime_bootstrap.py` -> `21 passed`
    - parent ownership-boundary check result: passed
  - phase-2 docs, examples, and prompt validation
    - slice type: `edit`
    - owned surfaces: Phase 2-owned redesign prompt/manifest/task-root docs, generated prompt examples, `docs/current/interfaces/prompt-layer-and-worker-delivery.md`, and `scripts/docs/prompt_catalog_tools.py` only if needed
    - required reads: the full Phase 2 required read set plus prompt docs/examples/tooling
    - expected outputs: doc-teaching of the checkpoint split and localized surfaced files, regenerated examples, and cleared prompt-example drift
    - required validators/tests: `prompt_catalog_tools.py generate`, `prompt_catalog_tools.py validate`, and `ruff check scripts/docs` if scripts change
    - dependencies: phase-2 runtime code and tests slice
    - evidence requested: exact docs/examples/tooling files changed and command outcomes
    - returned evidence: redesign and current prompt-layer docs now teach `latest_relevant_checkpoint_path` and `tmp/transfers/localized`; generated prompt examples were regenerated; `prompt_catalog_tools.py generate` passed; `prompt_catalog_tools.py validate` passed; `ruff check scripts/docs` passed
    - parent ownership-boundary check result: passed
  - review-only Phase 2 artifact audit
    - slice type: `review-only`
    - owned surfaces: none
    - required reads: the full Phase 2 required read set plus the authoritative Phase 2 artifacts
    - expected outputs: exact artifact deltas needed after the code/docs slices land, including reset-gate and Phase 0 blocker clearance evidence
    - required validators/tests: none
    - dependencies: sibling edit slices
    - evidence requested: exact file/line references, keep/fix checklist, and residual compliance gaps
    - returned evidence: Phase 2 artifacts must explicitly record localization, checkpoint-field split, prompt-example drift clearance, and reset-gate proof
    - parent ownership-boundary check result: passed; no file edits returned
  - review-only Phase 2 correctness audit
    - slice type: `review-only`
    - owned surfaces: none
    - required reads: the full Phase 2 required read set plus the owned runtime/test files
    - expected outputs: correctness audit for localization semantics, checkpoint split, deterministic precedence, prompt rendering, and phase-boundary drift
    - required validators/tests: none
    - dependencies: sibling edit slices
    - evidence requested: exact file/line references and an integration audit checklist
    - returned evidence: code-level semantics are correct; the main remaining integration risk was docs/test drift, now addressed in this wave
    - parent ownership-boundary check result: passed; no file edits returned

## Parent integration and validation log

- wave 3 integration result:
  - parent waited for the full delegated wave before integrating
  - parent reviewed every returned diff against owned surfaces and slice type
  - no out-of-scope edits or review-only edits required revert in this wave
  - parent integrated the materialization/state/resource changes
  - parent integrated the renderer/test/docs/generated-example changes
  - parent kept same-session proof narrowed to renderer/persisted request behavior and did not claim live dispatch-opening selection

## Commands run

- `./.venv/bin/ruff format --check apps/api/app/runtime/projection/materialize.py apps/api/app/runtime/projection/state.py apps/api/app/runtime/prompt/sections.py apps/api/tests/unit/test_runtime_prompt_rendering.py apps/api/tests/integration/test_phase2_runtime_bootstrap.py scripts/docs/prompt_catalog_tools.py`
  - outcome: passed
- `./.venv/bin/ruff check apps/api/app/runtime/projection/materialize.py apps/api/app/runtime/projection/state.py apps/api/app/runtime/prompt/sections.py apps/api/tests/unit/test_runtime_prompt_rendering.py apps/api/tests/integration/test_phase2_runtime_bootstrap.py scripts/docs/prompt_catalog_tools.py`
  - outcome: passed
- `./.venv/bin/mypy apps/api/app/runtime/projection/materialize.py apps/api/app/runtime/projection/state.py apps/api/app/runtime/prompt/sections.py apps/api/tests/unit/test_runtime_prompt_rendering.py apps/api/tests/integration/test_phase2_runtime_bootstrap.py scripts/docs/prompt_catalog_tools.py`
  - outcome: passed
- `make pyright-api`
  - outcome: passed
- `./.venv/bin/python scripts/docs/prompt_catalog_tools.py generate`
  - outcome: passed and regenerated `docs/redesign/prompt-layer/generated/rendered-examples.md`
- `./.venv/bin/python scripts/docs/prompt_catalog_tools.py validate`
  - outcome: passed and cleared the earlier generated-example drift for `parent_root_dispatch_prompt` and `parent_root_dispatch_prompt same_session_continue`
- `./.venv/bin/python scripts/docs/docs_freeze_validate.py`
  - outcome: passed and the prior Phase 0 docs-freeze blocker is cleared now that the generated prompt examples match live renderer output
- `./.venv/bin/pytest -q apps/api/tests/unit/test_runtime_prompt_rendering.py apps/api/tests/integration/test_phase2_runtime_bootstrap.py`
  - outcome: `21 passed`
- `python3 -m venv <temp-venv> && <temp-venv>/bin/pip install -e . && <temp-venv>/bin/python -c "<prompt asset smoke>"`
  - outcome: passed

## Gate and validator summary

- docs or prompt validators: prompt catalog generate/validate and docs freeze passed
- language gates: `ruff`, `mypy`, and `pyright` passed
- reset or package checks: prompt package-install smoke passed on a fresh temporary venv; reset-gate proof for the task-root/manifest truth change passed through the owned Phase 2 unit/integration and docs-freeze lanes without test-only setup

## Test lanes

- unit: passed
- integration: passed
- e2e: no separate minimal-e2e command is recorded in this slice because full runtime closure/control flow remains Phase 3-owned
- SQLite: not required in this slice
- Postgres or Docker: not required in this slice

## Artifacts

- `docs/execution/plans/phase-2-prompt-bootstrap-contract-repair.md`
- `docs/execution/reviews/phase-2-prompt-bootstrap-contract-repair.md`
- the earlier Phase 0 docs-freeze blocker is now cleared by the regenerated prompt examples in this slice

## Blockers

- none for this Phase 2-owned slice
- live same-session dispatch opening remains outside this slice and is not claimed as Phase 2 closure proof

## Review link

- review artifact: `../reviews/phase-2-prompt-bootstrap-contract-repair.md`
