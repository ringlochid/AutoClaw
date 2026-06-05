# Phase 2 Local-Tool-First Prompt And Task-Root Review

Status: Reference

selected phase: Phase 2
current phase page: docs-internal/execution/v1/phases/phase-2-prompt-manifest-artifact-bootstrap.md
selected work packages: P2-WP1, P2-WP2, P2-WP3
summary-only: no
delegated slices: listed
slice id: phase2-prompt-source-legality
slice type: edit
owned surfaces: apps/api/src/autoclaw/runtime/prompt/assets/**, narrow apps/api/src/autoclaw/runtime/prompt/** render surfaces, apps/api/tests/unit/runtime_prompt_rendering/**, docs-internal/design/v1/prompt-layer/**, docs-internal/design/v1/prompt-layer/generated/**, scripts/docs/prompt_catalog/**
touched surfaces: apps/api/src/autoclaw/runtime/prompt/assets/**, apps/api/src/autoclaw/runtime/prompt/sections/rendering.py, apps/api/tests/unit/runtime_prompt_rendering/**, docs-internal/design/v1/prompt-layer/**, docs-internal/design/v1/prompt-layer/generated/rendered-examples.md, scripts/docs/prompt_catalog/**
slice id: phase2-stable-manifest-parity
slice type: edit
owned surfaces: apps/api/src/autoclaw/runtime/projection/manifest/**, apps/api/src/autoclaw/runtime/projection/dispatch/** when needed for manifest parity, apps/api/src/autoclaw/runtime/task_root/**, narrow apps/api/src/autoclaw/runtime/launch/bootstrap/** helpers, apps/api/tests/integration/phase2/bootstrap/**, apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py
touched surfaces: apps/api/src/autoclaw/runtime/projection/manifest/**, apps/api/src/autoclaw/runtime/projection/runtime_state.py, apps/api/src/autoclaw/runtime/task_root/**, apps/api/tests/integration/phase2/bootstrap/**, apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py
slice id: phase2-structural-edit-palette
slice type: edit
owned surfaces: apps/api/src/autoclaw/runtime/contracts/__init__.py, apps/api/src/autoclaw/runtime/contracts/{launch,projection}.py, apps/api/src/autoclaw/runtime/launch/bootstrap/manifest.py, apps/api/src/autoclaw/runtime/projection/manifest/{structural_palette.py,tree.py}, apps/api/src/autoclaw/runtime/prompt/{bundle.py,instructions.py,sections/rendering.py,structural_edit_palette.py}, apps/api/tests/unit/runtime_prompt_rendering/**, apps/api/tests/integration/phase2/bootstrap/**, docs-internal/design/v1/prompt-layer/generated/rendered-examples.md, scripts/docs/prompt_catalog/**
touched surfaces: apps/api/src/autoclaw/runtime/contracts/__init__.py, apps/api/src/autoclaw/runtime/contracts/{launch,projection}.py, apps/api/src/autoclaw/runtime/launch/bootstrap/manifest.py, apps/api/src/autoclaw/runtime/projection/manifest/{structural_palette.py,tree.py}, apps/api/src/autoclaw/runtime/prompt/{bundle.py,instructions.py,sections/rendering.py,structural_edit_palette.py}, apps/api/tests/unit/runtime_prompt_rendering/**, apps/api/tests/integration/phase2/bootstrap/**, docs-internal/design/v1/prompt-layer/generated/rendered-examples.md, scripts/docs/prompt_catalog/**
slice id: phase2-current-doc-and-closeout-refresh
slice type: edit
owned surfaces: docs-internal/current/v1/interfaces/prompt-layer-and-worker-delivery.md, docs-internal/current/v1/interfaces/current-openclaw-bridge-prompt-strings.md, docs-internal/current/v1/architecture/manifest-projection-and-acknowledgement.md, docs-internal/current/v1/architecture/task-roots-and-materialized-paths.md, docs-internal/execution/v1/plans/phase-2-closeout-prompt-legality-and-proof.md, docs-internal/execution/v1/evidence/phase-2-closeout-prompt-legality-and-proof.md, docs-internal/execution/v1/reviews/phase-2-closeout-prompt-legality-and-proof.md
touched surfaces: docs-internal/current/v1/interfaces/prompt-layer-and-worker-delivery.md, docs-internal/current/v1/interfaces/current-openclaw-bridge-prompt-strings.md, docs-internal/current/v1/architecture/manifest-projection-and-acknowledgement.md, docs-internal/current/v1/architecture/task-roots-and-materialized-paths.md, docs-internal/execution/v1/plans/phase-2-closeout-prompt-legality-and-proof.md, docs-internal/execution/v1/evidence/phase-2-closeout-prompt-legality-and-proof.md, docs-internal/execution/v1/reviews/phase-2-closeout-prompt-legality-and-proof.md

## Slice identity

- selected phase: Phase 2
- reviewed plan: `../plans/phase-2-closeout-prompt-legality-and-proof.md`
- reviewed evidence: `../evidence/phase-2-closeout-prompt-legality-and-proof.md`
- date: 2026-05-13

## Phase-local contract

- current phase page: `docs-internal/execution/v1/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
- implementation file lock map: `docs-internal/execution/v1/maps/file-priority-map.md`

## Scope

- reviewed plan: `../plans/phase-2-closeout-prompt-legality-and-proof.md`
- reviewed evidence: `../evidence/phase-2-closeout-prompt-legality-and-proof.md`
- review focus:
  - validator-compliant authoritative Phase 2 records
  - truthful prompt-source and manifest/current-doc closeout narrative
  - fresh proof tokens for prompt-catalog, scripts/docs, `style_audit`, exact repo search, typing, and pytest
  - continued Phase 3 deferral for runtime-truth fixes

## Verdict

- pass/fail: pass
- summary: the authoritative Phase 2 chain is now truthful to the landed prompt-source and manifest/current-doc work, includes delegated-slice body briefs for all listed slices, records fresh `style_audit`, exact repo search, prompt_catalog generate/validate, `ruff check scripts/docs`, `mypy scripts/docs`, backend typing, and pytest proof, and keeps Phase 3 runtime-truth fixes explicitly deferred while making the local-tool-first synchronous task-root model explicit

## Findings

- the closeout chain now states one prompt contract across shipped prompt assets, rendered guidance, generated examples, and the prompt-catalog: structural edits are taught only through the surfaced compact `structural_edit_palette`, `yield` stays tied to one staged child assignment, and root-only `blocked` is preserved
- the closeout chain now states one manifest and current-doc contract around `manifest_version`, top-level `structural_edit_palette`, per-node `policy`, and dedicated checkpoint-handoff carriers instead of implying that checkpoint context may be inferred from surfaced checkpoint order
- the current-doc narrative is now truthful about what Phase 2 did not solve: the no-open-dispatch checkpoint fallback remains current behavior and is explicitly deferred to Phase 3 runtime work rather than silently claimed as fixed here
- the rewritten plan now includes delegated-slice body briefs for `phase2-prompt-source-legality`, `phase2-stable-manifest-parity`, `phase2-structural-edit-palette`, and `phase2-current-doc-and-closeout-refresh`, satisfying the new execution record grammar instead of relying only on header blocks
- the rewritten evidence and review now record fresh `style_audit` proof, exact repo search or underscore-private proof language, `prompt_catalog.cli generate`, `prompt_catalog.cli validate`, `ruff check scripts/docs`, `mypy scripts/docs`, `make pyright-api`, and the full Phase 2 pytest lane instead of inherited or incomplete summaries

## Delegated-slice compliance

- `phase2-prompt-source-legality`
  - slice type: `edit`
  - ownership result: stayed inside Phase 2 prompt assets, prompt render surfaces, prompt docs, generated examples, tests, and prompt-catalog tooling
  - do-not-edit compliance: did not claim Phase 3 runtime-currentness or route orchestration ownership
- `phase2-stable-manifest-parity`
  - slice type: `edit`
  - ownership result: stayed inside Phase 2 manifest, task-root, narrow bootstrap, and Phase 2 proof-test surfaces
  - do-not-edit compliance: did not take ownership of runtime control, release-precondition truth, or callback routing
- `phase2-structural-edit-palette`
  - slice type: `edit`
  - ownership result: stayed inside prompt/readback model, manifest helper, test, and prompt-catalog surfaces needed to surface the compact palette
  - do-not-edit compliance: did not claim Phase 3 legality or controller-truth cleanup
- `phase2-current-doc-and-closeout-refresh`
  - slice type: `edit`
  - ownership result: current-doc alignment and authoritative record repair stayed inside the allowed Phase 2 current docs and the selected triplet
  - do-not-edit compliance: this slice stayed inside its owned current-doc and execution-record surfaces
- wave integration proof:
  - proof lanes were gathered first, then the authoritative triplet was rewritten to reflect the landed Phase 2 work and the fresh results

## Proof lanes relied on

- `./.venv/bin/python -m scripts.docs.prompt_catalog.cli generate` -> passed with exit code `0`; no console output
- `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate` -> `Prompt catalog validation passed.`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings` -> passed with `No findings.`
- exact repo search:
  - `rg -n "from .* import _|import .*\\._" apps/api/src/autoclaw/runtime/prompt apps/api/src/autoclaw/runtime/projection apps/api/src/autoclaw/runtime/task_root apps/api/src/autoclaw/runtime/launch apps/api/tests/unit/runtime_prompt_rendering apps/api/tests/integration/phase2/bootstrap apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py scripts/docs/prompt_catalog docs-internal/design/v1/prompt-layer docs-internal/current/v1/interfaces/prompt-layer-and-worker-delivery.md docs-internal/current/v1/interfaces/current-openclaw-bridge-prompt-strings.md docs-internal/current/v1/architecture/manifest-projection-and-acknowledgement.md docs-internal/current/v1/architecture/task-roots-and-materialized-paths.md`
  - outcome: no matches; no cross-module private symbol or underscore-private import drift was found in the Phase 2 code, tests, docs tooling, design docs, or owned current docs
- `./.venv/bin/ruff check apps/api/src/autoclaw/runtime/prompt apps/api/src/autoclaw/runtime/projection apps/api/src/autoclaw/runtime/task_root apps/api/src/autoclaw/runtime/launch apps/api/tests/unit/runtime_prompt_rendering apps/api/tests/integration/phase2/bootstrap apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py scripts/docs/prompt_catalog` -> `All checks passed!`
- `./.venv/bin/ruff check scripts/docs` -> `All checks passed!`
- `./.venv/bin/mypy apps/api/src/autoclaw/runtime/prompt apps/api/src/autoclaw/runtime/projection apps/api/src/autoclaw/runtime/task_root apps/api/src/autoclaw/runtime/launch apps/api/tests/unit/runtime_prompt_rendering apps/api/tests/integration/phase2/bootstrap scripts/docs/prompt_catalog` -> `Success: no issues found in 80 source files`
- `./.venv/bin/mypy scripts/docs` -> `Success: no issues found in 54 source files`
- `make pyright-api` -> `0 errors, 0 warnings, 0 informations`
- `./.venv/bin/pytest -q apps/api/tests/unit/runtime_prompt_rendering apps/api/tests/integration/phase2/bootstrap apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py` -> `78 passed in 38.67s`

## Reset-gate note

- this closure-artifact rebuild did not land a new runtime schema change, package-install change, or task-root root-layout change inside the owned surfaces
- the landed prompt-source and manifest/current-doc work still required truthful proof for prompt-catalog generation and validation plus the Phase 2 bootstrap and minimal e2e lanes
- Phase 3 remains responsible for runtime persistence currentness, route-layer structural manifest orchestration, and any reset-gate work those changes require

## Stale-logic search proof

- searched the authoritative Phase 2 triplet for stale closeout wording that:
  - treated any role or policy name surfaced anywhere in the prompt or manifest as a legal structural-edit target
  - implied root `blocked` was a generic closure option
  - treated manifest payload fields or checkpoint-handoff carriers as implicit
  - claimed Phase 3 runtime-truth fixes had already landed
- outcome:
  - the rewritten chain removes those stale claims and keeps the remaining no-open-dispatch checkpoint fallback explicit as Phase 3 debt
- searched the Phase 2 code, tests, tooling, design docs, and owned current docs for private symbol and underscore-private cross-module import drift:
  - exact repo search found none

## Kill-list proof

- phase kill-list source:
  - `docs-internal/execution/v1/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
- terms checked in this slice:
  - design docs treated as the shipped prompt source
  - prompt rules that rely on hidden transcript memory
  - filesystem-primary truth for generated roots
  - runtime persistence truth split across both Phase 2 and Phase 3
- outcome:
  - the authoritative chain keeps app-owned prompt assets as the shipped prompt source, keeps prompt legality explicit instead of implied by hidden continuity, keeps generated roots controller-derived rather than filesystem-authoritative, and continues to defer runtime persistence truth cleanly to Phase 3

## Docs answer-sourcing proof

- execution canon read:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs-internal/execution/v1/README.md`
  - `docs-internal/execution/v1/maps/file-priority-map.md`
  - `docs-internal/execution/v1/maps/design-code-landing-map.md`
  - `docs-internal/execution/v1/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
  - `docs-internal/execution/v1/gates/mandatory-review-gate.md`
  - `docs-internal/execution/v1/gates/reset-gate.md`
  - `docs-internal/execution/v1/gates/code-quality-gate.md`
- design owners and supporting reads used:
  - `docs-internal/design/v1/prompt-layer/contract.md`
  - `docs-internal/design/v1/prompt-layer/source-and-sections.md`
  - `docs-internal/design/v1/prompt-layer/field-renderers.md`
  - `docs-internal/design/v1/prompt-layer/render-and-persistence.md`
  - `docs-internal/design/v1/prompt-layer/machine-contract.md`
  - `docs-internal/design/v1/prompt-layer/README.md`
  - `docs-internal/design/v1/prompt-layer/README.md`
  - `docs-internal/design/v1/prompt-layer/prompt-pack/README.md`
  - `docs-internal/design/v1/prompt-layer/prompt-pack/system-and-provider-block.md`
  - `docs-internal/design/v1/prompt-layer/prompt-pack/runtime-rule-blocks.md`
  - `docs-internal/design/v1/prompt-layer/prompt-pack/validation-and-reject-blocks.md`
  - `docs-internal/design/v1/prompt-layer/generated/README.md`
  - `docs-internal/design/v1/prompt-layer/generated/rendered-examples.md`
  - `docs-internal/design/v1/prompt-layer/generated/inventory.md`
  - `docs-internal/design/v1/prompt-layer/legality-and-coverage.md`
  - `docs-internal/design/v1/prompt-layer/prompt-catalog.yaml`
  - `docs-internal/design/v1/prompt-layer/prompt-resource-usage-appendix.md`
  - `docs-internal/design/v1/architecture/manifest-contract.md`
  - `docs-internal/design/v1/architecture/worker-context-contract.md`
  - `docs-internal/design/v1/architecture/task-root-layout-and-generated-files.md`
  - `docs-internal/design/v1/architecture/artifact-ref-and-storage-contract.md`
  - `docs-internal/design/v1/architecture/runtime-records-and-lifecycle.md`
  - `docs-internal/design/v1/architecture/runtime-boundary-and-controller-loop-contract.md`
- current-contrast reads used:
  - `docs-internal/current/v1/interfaces/prompt-layer-and-worker-delivery.md`
  - `docs-internal/current/v1/interfaces/current-openclaw-bridge-prompt-strings.md`
  - `docs-internal/current/v1/architecture/manifest-projection-and-acknowledgement.md`
  - `docs-internal/current/v1/architecture/task-roots-and-materialized-paths.md`
- repo-local prompt/readback sources used:
  - prompt assets, design docs, generated examples, and prompt-catalog surfaces covering structural-edit naming, root-only `blocked`, and `yield` wording
  - manifest, task-root, and current-doc surfaces covering `manifest_version`, `structural_edit_palette`, node `policy`, and the explicit Phase 3 debt note for the no-open-dispatch checkpoint fallback
- code and tests reviewed against those docs:
  - `apps/api/src/autoclaw/runtime/prompt/**`
  - `apps/api/src/autoclaw/runtime/projection/**`
  - `apps/api/src/autoclaw/runtime/task_root/**`
  - `apps/api/src/autoclaw/runtime/launch/bootstrap/**`
  - `apps/api/tests/unit/runtime_prompt_rendering/**`
  - `apps/api/tests/integration/phase2/bootstrap/**`
  - `apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`
- canon gap:
  - none

## Phase-bounded STYLE exceptions

- none

## Ownership compliance

- edited surfaces stayed inside:
  - `docs-internal/execution/v1/plans/phase-2-closeout-prompt-legality-and-proof.md`
  - `docs-internal/execution/v1/evidence/phase-2-closeout-prompt-legality-and-proof.md`
  - `docs-internal/execution/v1/reviews/phase-2-closeout-prompt-legality-and-proof.md`
- this slice did not edit Phase 2 code, prompt docs, generated docs, or current docs; it only repaired the authoritative execution-record chain
- the chain no longer claims Phase 3 ownership or fixes as Phase 2 closure

## Remaining exact blockers

- none

## Repo-level follow-on blockers outside this slice

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli validate` may still fail until the out-of-scope Phase 3 authoritative artifacts add their delegated slice body briefs and required proof tokens

## Cross-links

- authoritative plan: `../plans/phase-2-closeout-prompt-legality-and-proof.md`
- authoritative evidence: `../evidence/phase-2-closeout-prompt-legality-and-proof.md`
