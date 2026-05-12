# Phase 2 Closeout Prompt Legality and Proof Routing Review

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

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`

## Scope

- reviewed plan: `../plans/phase-2-closeout-prompt-legality-and-proof.md`
- reviewed evidence: `../evidence/phase-2-closeout-prompt-legality-and-proof.md`
- reviewed historical support:
  `../plans/phase-2-prompt-bootstrap-contract-repair.md`
  `../evidence/phase-2-prompt-bootstrap-contract-repair.md`
  `../reviews/phase-2-prompt-bootstrap-contract-repair.md`

## Verdict

- pass/fail: pass
- summary: the authoritative Phase 2 closeout chain now matches the landed launch, projection, prompt, and test package boundaries after the final wrapper cleanup; records the current focused Phase 2 proof and broader parent-tree totals; preserves the truthful `resources.py` boundary note; removes stale monolith-era `STYLE.md` exceptions; and leaves the reviewed collateral docs untouched because their current wording already stays truthful.

## Findings

- the authoritative closeout chain no longer points at pre-split or deleted proof surfaces such as `apps/api/tests/unit/test_runtime_prompt_assets.py`
- the authoritative proof set now matches the current parent-validated commands and outcomes:
  `prompt_catalog_tools.py validate`,
  exact-scope `ruff check`,
  exact-scope `mypy`,
  exact-scope `pyright`,
  focused Phase 2 `pytest` at `43 passed`,
  full `apps/api` tests at `238 passed`,
  and `make test-api-db` at `236 passed`
- the authoritative closeout chain no longer treats `apps/api/app/runtime/projection/state.py`, `apps/api/app/runtime/projection/materialize.py`, `apps/api/app/runtime/launch/projection.py`, or `apps/api/app/runtime/prompt/sections.py` as live Phase 2 boundaries; those wrappers are gone and the surviving boundaries are the `projection/__init__.py`, `launch/__init__.py`, and `prompt/sections/*.py` package surfaces
- `apps/api/app/runtime/resources.py` still remains a truthful public boundary note because non-Phase-2 runtime callers continue to import it
- the split prompt-render and bootstrap suites are now reflected by the current test shards:
  `test_runtime_prompt_rendering*.py`,
  `test_phase2_runtime_bootstrap*.py`,
  and `test_phase2_minimal_runtime_lane.py`
- the reviewed allowed collateral docs remained truthful, so this refresh correctly left them untouched instead of widening into unnecessary current or redesign doc edits
- the older `phase-2-prompt-bootstrap-contract-repair*` chain remains `summary-only: yes` and no longer reads as closeout authority

## Proof lanes relied on

- `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate` -> `passed`
- `./.venv/bin/ruff check apps/api/app/runtime/launch apps/api/app/runtime/projection apps/api/app/runtime/prompt apps/api/app/runtime/resources.py apps/api/tests/unit/test_runtime_prompt_rendering*.py apps/api/tests/integration/test_phase2_runtime_bootstrap*.py apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py` -> `passed`
- `./.venv/bin/mypy apps/api/app/runtime/launch apps/api/app/runtime/projection apps/api/app/runtime/prompt apps/api/app/runtime/resources.py apps/api/tests/unit/test_runtime_prompt_rendering*.py apps/api/tests/integration/test_phase2_runtime_bootstrap*.py apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py` -> `passed`
- `cd apps/api && npx --yes pyright app/runtime/launch app/runtime/projection app/runtime/prompt app/runtime/resources.py tests/unit/test_runtime_prompt_rendering*.py tests/integration/test_phase2_runtime_bootstrap*.py tests/e2e/test_phase2_minimal_runtime_lane.py` -> `passed`
- `./.venv/bin/pytest -q apps/api/tests/unit/test_runtime_prompt_rendering.py apps/api/tests/unit/test_runtime_prompt_rendering*.py apps/api/tests/integration/test_phase2_runtime_bootstrap.py apps/api/tests/integration/test_phase2_runtime_bootstrap*.py apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py` -> `43 passed`
- `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest -q tests` -> `238 passed`
- `make test-api-db` -> `236 passed`
- `find apps/api/app/runtime/launch apps/api/app/runtime/projection apps/api/app/runtime/prompt -maxdepth 1 -type f -name '*.py' -print0 | xargs -0 wc -l | sort -nr` -> no reviewed runtime file over `400` lines
- `find apps/api/tests/unit -maxdepth 1 -type f \\( -name 'test_runtime_prompt_rendering*.py' \\) -print0 | xargs -0 wc -l | sort -nr` -> largest reviewed unit shard `345` lines
- `find apps/api/tests/integration -maxdepth 1 -type f \\( -name 'test_phase2_runtime_bootstrap*.py' \\) -print0 | xargs -0 wc -l | sort -nr` -> largest reviewed integration shard `317` lines in `test_phase2_runtime_bootstrap_fixtures.py`
- `./.venv/bin/python - <<'PY' ... PY` -> `NO_FINDINGS` for functions over `80` non-comment, non-blank lines across the reviewed Phase 2 scope
- `rg -n "from .* import _|import .*\\._|\\b_[A-Za-z0-9]+\\(" apps/api/app/runtime/launch apps/api/app/runtime/projection apps/api/app/runtime/prompt apps/api/tests/unit/test_runtime_prompt_rendering*.py apps/api/tests/integration/test_phase2_runtime_bootstrap*.py` -> no cross-module underscore-private helper import remained in the reviewed scope

## Delegated-slice compliance

- `delegated slices: none` is truthful for this closeout-artifact refresh

## Stale-logic search proof

- checked the owned artifacts for stale closeout references to:
  `apps/api/tests/unit/test_runtime_prompt_assets.py`,
  monolith-era ownership claims for `projection/state.py`, `projection/materialize.py`, `launch/projection.py`, and `prompt/sections.py`,
  old proof totals such as `71 passed` and `161 passed`,
  and stale monolith-era `STYLE.md` exceptions
- outcome:
  those stale references were removed from the authoritative closeout chain

## Kill-list proof

- phase kill-list source:
  `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
- outcome:
  the refreshed closeout chain still keeps prompt assets as the shipped prompt source, keeps `_runtime/dispatch/*` observability-only, keeps generated roots controller-derived rather than filesystem-authoritative, and continues to defer runtime persistence truth to Phase 3

## Docs answer-sourcing proof

- execution canon read:
  `AGENTS.md`,
  `STYLE.md`,
  `docs/execution/README.md`,
  `docs/execution/phases/overview.md`,
  `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`,
  `docs/execution/maps/file-priority-map.md`,
  `docs/execution/maps/redesign-code-landing-map.md`,
  `docs/execution/gates/mandatory-review-gate.md`,
  `docs/execution/gates/reset-gate.md`,
  and `docs/execution/gates/phase-done-gate.md`
- primary and supporting redesign reads used for truthful closeout wording:
  `docs/redesign/prompt-layer/contract.md`,
  `docs/redesign/prompt-layer/source-and-sections.md`,
  `docs/redesign/prompt-layer/field-renderers.md`,
  `docs/redesign/prompt-layer/render-and-persistence.md`,
  `docs/redesign/prompt-layer/machine-contract.md`,
  `docs/redesign/prompt-layer/README.md`,
  `docs/redesign/prompt-layer/INDEX.md`,
  `docs/redesign/prompt-layer/prompt-pack/README.md`,
  `docs/redesign/prompt-layer/prompt-pack/system-and-provider-block.md`,
  `docs/redesign/prompt-layer/prompt-pack/runtime-rule-blocks.md`,
  `docs/redesign/prompt-layer/prompt-pack/validation-and-reject-blocks.md`,
  `docs/redesign/prompt-layer/generated/README.md`,
  `docs/redesign/prompt-layer/generated/rendered-examples.md`,
  `docs/redesign/prompt-layer/generated/inventory.md`,
  `docs/redesign/prompt-layer/legality-and-coverage.md`,
  `docs/redesign/prompt-layer/prompt-catalog.yaml`,
  `docs/redesign/prompt-layer/prompt-resource-usage-appendix.md`,
  `docs/redesign/prompt-layer/composition-example.md`,
  `docs/redesign/architecture/manifest-contract.md`,
  `docs/redesign/architecture/worker-context-contract.md`,
  `docs/redesign/architecture/task-root-layout-and-generated-files.md`,
  `docs/redesign/architecture/artifact-ref-and-storage-contract.md`,
  `docs/redesign/architecture/runtime-records-and-lifecycle.md`,
  `docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md`,
  `docs/redesign/architecture/filesystem-layout-and-roots.md`,
  `docs/redesign/architecture/task-compose-root-binding-and-host-placement.md`,
  `docs/redesign/decisions/ADR-0005-task-owned-roots-and-runtime-generated-projections.md`,
  `docs/redesign/workflows/typed-dependency-selectors-and-produce-slots.md`,
  `docs/redesign/workflows/criteria-and-parent-verification.md`,
  and `docs/redesign/workflows/workflow-schema-appendix.md`
- current-contrast reads used:
  `docs/current/interfaces/prompt-layer-and-worker-delivery.md`,
  `docs/current/interfaces/current-openclaw-bridge-prompt-strings.md`,
  `docs/current/architecture/manifest-projection-and-acknowledgement.md`,
  and `docs/current/architecture/task-roots-and-materialized-paths.md`
- current live Phase 2 code and test surfaces reviewed:
  `apps/api/app/runtime/launch/*.py` plus `launch/__init__.py`,
  `apps/api/app/runtime/projection/*.py` plus `projection/__init__.py`,
  `apps/api/app/runtime/prompt/*.py` plus `prompt/sections/*.py`,
  `apps/api/app/runtime/resources.py`,
  `apps/api/tests/unit/test_runtime_prompt_rendering*.py`,
  `apps/api/tests/integration/test_phase2_runtime_bootstrap*.py`,
  and `apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py`
- canon gap or explicit `none`:
  none

## Phase-bounded STYLE exceptions

- none

## Reset-gate note

- the earlier authoritative closeout chain no longer relies on the old targeted reset/readiness pair
- this refresh records the current parent-validated broader DB proof lanes instead:
  `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest -q tests` -> `238 passed`
  and `make test-api-db` -> `236 passed`
- no prompt-asset package-data or install-path delta was reopened by the landed split surfaces reviewed in this refresh

## Remaining exact blockers

- none

## Cross-links

- authoritative plan:
  `../plans/phase-2-closeout-prompt-legality-and-proof.md`
- authoritative evidence:
  `../evidence/phase-2-closeout-prompt-legality-and-proof.md`
- historical support:
  `./phase-2-prompt-bootstrap-contract-repair.md`
