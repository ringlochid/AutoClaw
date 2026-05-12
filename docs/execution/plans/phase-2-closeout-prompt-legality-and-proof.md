# Phase 2 Closeout Prompt Legality and Proof Routing

Status: Reference

selected phase: Phase 2
current phase page: docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md
selected work packages: P2-WP1, P2-WP2, P2-WP3
summary-only: no
delegated slices: none

## Slice identity

- selected phase: Phase 2
- approved continuation slice: `P2-WP3-B` artifact refresh serving authoritative closeout for `P2-WP1` through `P2-WP3`
- owner: Codex
- date: 2026-05-12
- execution mode: owned closeout-artifact refresh only; no subagents

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`

## Closeout focus

- refresh the authoritative Phase 2 closeout chain so it matches the landed split launch, projection, prompt, and test surfaces in the current tree
- replace stale proof routing that still points at pre-split or deleted monolith-era surfaces, old proof counts, or stale `STYLE.md` exceptions
- keep current, redesign, and generated collateral docs untouched unless the closeout wording cannot otherwise stay truthful
- keep `phase-2-prompt-bootstrap-contract-repair*` as historical support only

## Live landed Phase 2 surfaces reflected here

- runtime launch package:
  `apps/api/app/runtime/launch/attempt_persistence.py`,
  `bootstrap_context.py`,
  `bootstrap_persistence.py`,
  `bootstrap_result.py`,
  `criteria_staging.py`,
  `flow_persistence_builders.py`,
  `manifest_projection.py`,
  `persistence.py`,
  `pinned_revisions.py`,
  `service.py`,
  `workspace_leases.py`,
  and the package boundary in `launch/__init__.py`; the thin wrapper `launch/projection.py` is gone
- runtime projection package:
  `apps/api/app/runtime/projection/attempt_materialization.py`,
  `checkpoint_handoff.py`,
  `current_context_queries.py`,
  `dispatch_materialization.py`,
  `dispatch_prompt.py`,
  `manifest_current_context.py`,
  `manifest_materialization.py`,
  `manifest_projection.py`,
  `manifest_tree.py`,
  `projection_mappers.py`,
  `runtime_state.py`,
  `task_roots.py`,
  and the package boundary in `projection/__init__.py`; the thin facades `state.py` and `materialize.py` are gone
- runtime prompt package:
  `apps/api/app/runtime/prompt/asset_catalog.py`,
  `bundle.py`,
  `instructions.py`,
  and the `sections/` package with `context.py`, `primitives.py`, and `rendering.py`; the flat boundaries `section_context.py`, `section_primitives.py`, and `sections.py` are gone
- stable task-root path boundary:
  `apps/api/app/runtime/resources.py`, which remains a true public boundary because non-Phase-2 runtime callers still import it
- split prompt-render unit suites:
  `apps/api/tests/unit/test_runtime_prompt_rendering.py`,
  `test_runtime_prompt_rendering_support.py`,
  `test_runtime_prompt_rendering_context.py`,
  `test_runtime_prompt_rendering_dispatch.py`,
  `test_runtime_prompt_rendering_memory_checkpoint.py`,
  and `test_runtime_prompt_rendering_samples.py`; `test_runtime_prompt_rendering.py` is now a real smoke-proof boundary rather than a large collector
- split bootstrap integration suites:
  `apps/api/tests/integration/test_phase2_runtime_bootstrap.py`,
  `test_phase2_runtime_bootstrap_fixtures.py`,
  `test_phase2_runtime_bootstrap_attempt_files.py`,
  `test_phase2_runtime_bootstrap_bootstrap.py`,
  `test_phase2_runtime_bootstrap_controller_truth.py`,
  `test_phase2_runtime_bootstrap_dispatch.py`,
  and `test_phase2_runtime_bootstrap_manifest.py`; `test_phase2_runtime_bootstrap.py` now remains only as a minimal boundary plus smoke proof
- minimal Phase 2 e2e lane:
  `apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py`

## Proof to record in the evidence artifact

Attach the current focused Phase 2 proof and the broader parent-tree totals exactly as follows:

- `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate` -> `passed`
- `./.venv/bin/ruff check apps/api/app/runtime/launch apps/api/app/runtime/projection apps/api/app/runtime/prompt apps/api/app/runtime/resources.py apps/api/tests/unit/test_runtime_prompt_rendering*.py apps/api/tests/integration/test_phase2_runtime_bootstrap*.py apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py` -> `passed`
- `./.venv/bin/mypy apps/api/app/runtime/launch apps/api/app/runtime/projection apps/api/app/runtime/prompt apps/api/app/runtime/resources.py apps/api/tests/unit/test_runtime_prompt_rendering*.py apps/api/tests/integration/test_phase2_runtime_bootstrap*.py apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py` -> `passed`
- `cd apps/api && npx --yes pyright app/runtime/launch app/runtime/projection app/runtime/prompt app/runtime/resources.py tests/unit/test_runtime_prompt_rendering*.py tests/integration/test_phase2_runtime_bootstrap*.py tests/e2e/test_phase2_minimal_runtime_lane.py` -> `passed`
- `./.venv/bin/pytest -q apps/api/tests/unit/test_runtime_prompt_rendering.py apps/api/tests/unit/test_runtime_prompt_rendering*.py apps/api/tests/integration/test_phase2_runtime_bootstrap.py apps/api/tests/integration/test_phase2_runtime_bootstrap*.py apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py` -> `43 passed`
- `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest -q tests` -> `238 passed`
- `make test-api-db` -> `236 passed`

## Collateral doc touch decision

- reviewed allowed collateral surfaces:
  `docs/current/interfaces/prompt-layer-and-worker-delivery.md`,
  `docs/current/architecture/manifest-projection-and-acknowledgement.md`,
  `docs/current/architecture/task-roots-and-materialized-paths.md`,
  `docs/redesign/prompt-layer/generated/README.md`,
  and `docs/redesign/prompt-layer/generated/rendered-examples.md`
- result: no current, redesign, or generated wording change was required for truthful Phase 2 closeout wording, so those files stay untouched

## STYLE and stale-logic routing

- clear the stale monolith-era `STYLE.md` exceptions only if the refreshed review can support `none` from the current split-surface inventory
- remove stale closeout references to deleted or pre-split proof surfaces such as `apps/api/tests/unit/test_runtime_prompt_assets.py`
- remove stale proof totals such as `71 passed`, `161 passed`, and the older targeted docs-tooling proof set
- remove stale closeout references that still treat `apps/api/app/runtime/projection/state.py`, `apps/api/app/runtime/projection/materialize.py`, `apps/api/app/runtime/launch/projection.py`, or `apps/api/app/runtime/prompt/sections.py` as live Phase 2 boundaries
- keep the `apps/api/app/runtime/resources.py` public-boundary note only while that import surface remains live outside Phase 2 ownership

## Historical support handling

- `docs/execution/plans/phase-2-prompt-bootstrap-contract-repair.md`,
  `docs/execution/evidence/phase-2-prompt-bootstrap-contract-repair.md`,
  and `docs/execution/reviews/phase-2-prompt-bootstrap-contract-repair.md`
  remain `summary-only: yes`
- this closeout chain remains the only authoritative `summary-only: no` Phase 2 closeout path in the owned surfaces

## Stop conditions

- stop if truthful Phase 2 wording requires edits outside the owned execution artifacts or the explicitly allowed collateral docs
- stop if one of the reviewed current, redesign, or generated collateral pages needs change and the truthful fix would widen beyond the allowed collateral surface list

## Cross-links

- evidence artifact:
  `../evidence/phase-2-closeout-prompt-legality-and-proof.md`
- review artifact:
  `../reviews/phase-2-closeout-prompt-legality-and-proof.md`
- historical support:
  `../plans/phase-2-prompt-bootstrap-contract-repair.md`
  `../evidence/phase-2-prompt-bootstrap-contract-repair.md`
  `../reviews/phase-2-prompt-bootstrap-contract-repair.md`
