# Phase 2 Closeout Prompt Legality and Proof Routing Evidence

Status: Reference

selected phase: Phase 2
current phase page: docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md
selected work packages: P2-WP1, P2-WP2, P2-WP3
summary-only: no
delegated slices: none

## Slice identity

- selected phase: Phase 2
- approved continuation slice: `P2-WP3-B` artifact refresh serving authoritative closeout for `P2-WP1` through `P2-WP3`
- date: 2026-05-12
- owned surface:
  `docs/execution/evidence/phase-2-closeout-prompt-legality-and-proof.md`
- evidence source for this refresh: focused Phase 2 proof from the final wrapper-cleanup slices, broader suite and DB totals available from the parent tree, and local read-only closeout audits for split-surface and stale-exception cleanup

## Plan and review links

- approved plan: `../plans/phase-2-closeout-prompt-legality-and-proof.md`
- mandatory review: `../reviews/phase-2-closeout-prompt-legality-and-proof.md`
- review artifact: `../reviews/phase-2-closeout-prompt-legality-and-proof.md`

## Authoritative evidence rule

- this file is the authoritative Phase 2 closeout-path evidence record in the owned surfaces
- the older `phase-2-prompt-bootstrap-contract-repair*` chain remains supporting history only and is not final closure authority

## Landed Phase 2 surfaces reflected by this evidence

- runtime launch package under `apps/api/app/runtime/launch/*.py`, with the public package boundary now in `apps/api/app/runtime/launch/__init__.py` and no remaining `launch/projection.py` wrapper
- runtime projection package under `apps/api/app/runtime/projection/*.py`, with the public package boundary now in `apps/api/app/runtime/projection/__init__.py` and no remaining `state.py` or `materialize.py` facades
- runtime prompt package under `apps/api/app/runtime/prompt/*.py` plus the real `apps/api/app/runtime/prompt/sections/*.py` subpackage; the flat boundaries `section_context.py`, `section_primitives.py`, and `sections.py` are gone
- stable task-root path boundary `apps/api/app/runtime/resources.py`, which remains a true public boundary because runtime projection, control, replan, and post-commit callers still import it
- split prompt-render unit suites `apps/api/tests/unit/test_runtime_prompt_rendering*.py`, including `test_runtime_prompt_rendering_support.py`
- split bootstrap integration suites `apps/api/tests/integration/test_phase2_runtime_bootstrap*.py`, including `test_phase2_runtime_bootstrap_fixtures.py`
- minimal Phase 2 e2e lane `apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py`

## Parent-validated proof recorded here

### Prompt catalog and typed/lint gates

- `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate`
  - result: `passed`
- `./.venv/bin/ruff check apps/api/app/runtime/launch apps/api/app/runtime/projection apps/api/app/runtime/prompt apps/api/app/runtime/resources.py apps/api/tests/unit/test_runtime_prompt_rendering*.py apps/api/tests/integration/test_phase2_runtime_bootstrap*.py apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py`
  - result: `passed`
- `./.venv/bin/mypy apps/api/app/runtime/launch apps/api/app/runtime/projection apps/api/app/runtime/prompt apps/api/app/runtime/resources.py apps/api/tests/unit/test_runtime_prompt_rendering*.py apps/api/tests/integration/test_phase2_runtime_bootstrap*.py apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py`
  - result: `passed`
- `cd apps/api && npx --yes pyright app/runtime/launch app/runtime/projection app/runtime/prompt app/runtime/resources.py tests/unit/test_runtime_prompt_rendering*.py tests/integration/test_phase2_runtime_bootstrap*.py tests/e2e/test_phase2_minimal_runtime_lane.py`
  - result: `passed`

### Focused Phase 2 proof lanes and broader parent-tree totals

- `./.venv/bin/pytest -q apps/api/tests/unit/test_runtime_prompt_rendering.py apps/api/tests/unit/test_runtime_prompt_rendering*.py apps/api/tests/integration/test_phase2_runtime_bootstrap.py apps/api/tests/integration/test_phase2_runtime_bootstrap*.py apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py`
  - result: `43 passed`
- `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest -q tests`
  - result: `238 passed`
- `make test-api-db`
  - result: `236 passed`

## Local split-surface and stale-exception audit for this refresh

- `find apps/api/app/runtime/launch apps/api/app/runtime/projection apps/api/app/runtime/prompt -maxdepth 1 -type f -name '*.py' -print0 | xargs -0 wc -l | sort -nr`
  - result: largest reviewed runtime file is `apps/api/app/runtime/launch/bootstrap_result.py` at `380` lines; no reviewed runtime file exceeds the `>400` split-review threshold
- `find apps/api/tests/unit -maxdepth 1 -type f \\( -name 'test_runtime_prompt_rendering*.py' \\) -print0 | xargs -0 wc -l | sort -nr`
  - result: largest reviewed unit shard is `apps/api/tests/unit/test_runtime_prompt_rendering_samples.py` at `345` lines
- `find apps/api/tests/integration -maxdepth 1 -type f \\( -name 'test_phase2_runtime_bootstrap*.py' \\) -print0 | xargs -0 wc -l | sort -nr`
  - result: largest reviewed integration shard is `apps/api/tests/integration/test_phase2_runtime_bootstrap_fixtures.py` at `317` lines
- `./.venv/bin/python - <<'PY' ... PY`
  - result: `NO_FINDINGS` for functions over the `>80` non-comment, non-blank threshold across the reviewed Phase 2 scope
- `rg -n "from .* import _|import .*\\._|\\b_[A-Za-z0-9]+\\(" apps/api/app/runtime/launch apps/api/app/runtime/projection apps/api/app/runtime/prompt apps/api/tests/unit/test_runtime_prompt_rendering*.py apps/api/tests/integration/test_phase2_runtime_bootstrap*.py`
  - result: only module-local `_now()` usage in `apps/api/app/runtime/launch/workspace_leases.py`; no cross-module underscore-private helper import remained in the reviewed scope

## Collateral doc touch decision

- reviewed allowed collateral surfaces:
  `docs/current/interfaces/prompt-layer-and-worker-delivery.md`,
  `docs/current/architecture/manifest-projection-and-acknowledgement.md`,
  `docs/current/architecture/task-roots-and-materialized-paths.md`,
  `docs/redesign/prompt-layer/generated/README.md`,
  and `docs/redesign/prompt-layer/generated/rendered-examples.md`
- result: no wording change was required for truthful Phase 2 closeout wording, so those files were left untouched

## Owned files edited in this refresh

- `docs/execution/plans/phase-2-closeout-prompt-legality-and-proof.md`
- `docs/execution/evidence/phase-2-closeout-prompt-legality-and-proof.md`
- `docs/execution/reviews/phase-2-closeout-prompt-legality-and-proof.md`

## Historical support retained

- historical plan:
  `../plans/phase-2-prompt-bootstrap-contract-repair.md`
- historical evidence:
  `../evidence/phase-2-prompt-bootstrap-contract-repair.md`
- historical review:
  `../reviews/phase-2-prompt-bootstrap-contract-repair.md`

## Remaining exact blockers

- none
