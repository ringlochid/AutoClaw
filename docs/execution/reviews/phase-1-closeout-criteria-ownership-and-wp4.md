# Phase 1 Closeout Criteria Ownership, WP4, and Proof Routing Review

Status: Reference

selected phase: Phase 1
current phase page: docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md
selected work packages: P1-WP1, P1-WP2, P1-WP3, P1-WP4
summary-only: no
delegated slices: listed
slice id: phase1-compiler-criteria-ownership
slice type: edit
owned surfaces: apps/api/app/compiler/contracts.py, apps/api/app/compiler/normalize.py, apps/api/tests/unit/test_workflow_compiler.py, docs/redesign/workflows/criteria-and-parent-verification.md, docs/redesign/workflows/compiler-contract-and-launch-materialization.md, docs/redesign/workflows/workflow-schema-appendix.md
touched surfaces: apps/api/app/compiler/contracts.py, apps/api/app/compiler/normalize.py, apps/api/tests/unit/test_workflow_compiler.py, docs/redesign/workflows/criteria-and-parent-verification.md, docs/redesign/workflows/compiler-contract-and-launch-materialization.md, docs/redesign/workflows/workflow-schema-appendix.md
slice id: phase1-examples-schema-proof
slice type: edit
owned surfaces: apps/api/tests/unit/test_definition_schemas.py, docs/redesign/workflows/workflow-definition-schema.md, docs/redesign/workflows/examples/minimal.md, docs/redesign/workflows/examples/normal.md, docs/redesign/workflows/examples/maximal.md, definitions/workflows/*.yaml, apps/api/app/resources/definitions/workflows/*.yaml
touched surfaces: apps/api/tests/unit/test_definition_schemas.py, docs/redesign/workflows/workflow-definition-schema.md
slice id: phase1-closeout-artifacts
slice type: edit
owned surfaces: docs/execution/plans/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/evidence/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/reviews/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/plans/phase-1-registry-reseed-and-proof-repair.md, docs/execution/evidence/phase-1-registry-reseed-and-proof-repair.md, docs/execution/reviews/phase-1-registry-reseed-and-proof-repair.md
touched surfaces: docs/execution/plans/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/evidence/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/reviews/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/plans/phase-1-registry-reseed-and-proof-repair.md, docs/execution/evidence/phase-1-registry-reseed-and-proof-repair.md, docs/execution/reviews/phase-1-registry-reseed-and-proof-repair.md
slice id: phase1-audit
slice type: review-only
owned surfaces: none
touched surfaces: none

## Slice identity

- selected phase: Phase 1
- work package or slice: authoritative closeout-path review for `P1-WP1`
  through `P1-WP4`
- date: 2026-05-06

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`

## Scope

- reviewed plan: `../plans/phase-1-closeout-criteria-ownership-and-wp4.md`
- reviewed evidence: `../evidence/phase-1-closeout-criteria-ownership-and-wp4.md`
- reviewed downstream authoritative Phase 2 closeout truth:
  `../evidence/phase-2-closeout-prompt-legality-and-proof.md`
  `../reviews/phase-2-closeout-prompt-legality-and-proof.md`
- reviewed superseded historical support:
  `../plans/phase-1-registry-reseed-and-proof-repair.md`
  `../evidence/phase-1-registry-reseed-and-proof-repair.md`
  `../reviews/phase-1-registry-reseed-and-proof-repair.md`

## Verdict

- pass/fail: pass
- summary: this rewrite restores one clear authority chain for the current
  Phase 1 closeout path. Authored criteria ownership, compiler proof, and
  `P1-WP4` closure are now explicit Phase 1 obligations, the shipped-path
  proof lanes remain required, and the older registry-reseed chain can no
  longer read as closure authority.

## Findings

- authored criteria ownership is now routed as Phase 1 truth: the durable
  baseline comes from node-local criteria declarations plus legal direct-parent
  `child_defaults` expansion, while runtime assignment criteria remain current
  projections rather than authored rewrites
- `P1-WP2` and `P1-WP3` now explicitly cover the compiler-owned criteria-owner
  contract instead of leaving that work implicit or deferred
- `P1-WP4` is now explicit in the authoritative closeout path, so examples,
  fixtures, and acceptance paths are no longer implicitly waived by the older
  `P1-WP1`..`P1-WP3` chain
- the Phase 1 shipped-path SQLite and Postgres or Docker proof requirements
  remain explicit phase-local obligations instead of being silently replaced by
  historical support
- no new command outcomes were invented; the new evidence chain truthfully
  records the exact parent-attached results for the selected proof lanes
- the older `phase-1-registry-reseed-and-proof-repair*` chain is now
  `summary-only: yes` across plan, evidence, and review, so it cannot remain
  the apparent mandatory-review or phase-done authority
- the authoritative downstream Phase 2 closeout chain now records the
  criteria-owner consumption handoff as satisfied, so the earlier Phase 2
  blocker wording is no longer truthful Phase 1 closeout status

## Delegated-slice compliance

- the phase used four bounded slices: compiler criteria ownership, examples or
  schema proof, closeout artifacts, and one review-only audit
- the review verified that each edit slice stayed inside its owned surfaces and
  that the review-only slice returned no edits

## Proof lanes relied on

- `./.venv/bin/pytest -q apps/api/tests/unit/test_workflow_compiler.py apps/api/tests/unit/test_definition_schemas.py` -> `49 passed`
- `./.venv/bin/pytest -q apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/integration/test_registry_seed_authority.py apps/api/tests/integration/test_db_reset_db.py apps/api/tests/unit/test_cli.py` -> `17 passed`
- `./.venv/bin/ruff format --check apps/api/app/compiler/contracts.py apps/api/app/compiler/normalize.py apps/api/tests/unit/test_definition_schemas.py apps/api/tests/unit/test_workflow_compiler.py` -> passed
- `./.venv/bin/ruff check apps/api/app/compiler/contracts.py apps/api/app/compiler/normalize.py apps/api/tests/unit/test_definition_schemas.py apps/api/tests/unit/test_workflow_compiler.py` -> passed
- `./.venv/bin/mypy apps/api/app/compiler/contracts.py apps/api/app/compiler/normalize.py apps/api/tests/unit/test_definition_schemas.py apps/api/tests/unit/test_workflow_compiler.py` -> passed
- `make pyright-api` -> `0 errors, 0 warnings, 0 informations`
- `make test-api-db` -> `153 passed`

## 2026-05-07 follow-up review

- pass/fail: pass
- scope:
  - registry-owned workflow launch identity
  - referenced-only role/policy lookup narrowing
  - optional-selector semantics proof
  - same-key workflow update/no-op concurrency
- findings:
  - launch snapshot now rejects stored workflow body `id` drift instead of trusting the authored body over the registry key
  - launch snapshot compilation and guarded workflow validation now load only referenced current role/policy rows, so unrelated corrupt current policy rows no longer block compile
  - `required=false` remains a real normalized/runtime-facing flag without weakening compile-time selector-target existence rules
  - identical concurrent same-key workflow updates now collapse to one new immutable revision instead of failing with a duplicate workflow revision number on SQLite
- proof lanes:
  - `./.venv/bin/pytest -q apps/api/tests/unit/test_workflow_compiler.py apps/api/tests/unit/test_definition_schemas.py apps/api/tests/integration/test_definition_registry_db.py` -> `61 passed`
  - `./.venv/bin/ruff format --check apps/api/app/registry/lookup.py apps/api/app/registry/service.py apps/api/tests/unit/test_workflow_compiler.py apps/api/tests/unit/test_definition_schemas.py apps/api/tests/integration/test_definition_registry_db.py` -> `5 files already formatted`
  - `./.venv/bin/ruff check apps/api/app/registry/lookup.py apps/api/app/registry/service.py apps/api/tests/unit/test_workflow_compiler.py apps/api/tests/unit/test_definition_schemas.py apps/api/tests/integration/test_definition_registry_db.py` -> passed
  - `./.venv/bin/mypy apps/api/app/registry/lookup.py apps/api/app/registry/service.py apps/api/tests/unit/test_workflow_compiler.py apps/api/tests/unit/test_definition_schemas.py apps/api/tests/integration/test_definition_registry_db.py` -> `Success: no issues found in 5 source files`
  - `make pyright-api` -> failed outside owned surfaces with pre-existing errors in `apps/api/app/runtime/control/assign_child.py` and `apps/api/app/runtime/control/boundary.py`
  - `cd apps/api && npx --yes pyright app/registry/lookup.py app/registry/service.py tests/unit/test_workflow_compiler.py tests/unit/test_definition_schemas.py tests/integration/test_definition_registry_db.py` -> `0 errors, 0 warnings, 0 informations`

## Stale-logic search proof

- checked for stale Phase 1 authority signals inside the owned artifacts:
  - old registry-reseed files remaining `summary-only: no`
  - old registry-reseed files continuing to present themselves as the active
    closeout path
  - new closeout files missing `P1-WP4` or criteria-ownership routing
- outcome:
  - the new closeout chain is the only `summary-only: no` Phase 1 closeout-path
    family in the owned surfaces
  - the old registry-reseed chain now reads as historical support only

## Kill-list proof

- phase kill-list source: `docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md`
- terms checked:
  - authored `edges` as canonical workflow authoring
  - dotted-id parent inference as core semantics
  - generic authored `skill_refs` as target schema
  - obsolete flat flagship workflow teaching model
- outcome: no touched Phase 1 artifact or proof lane reintroduced the phase kill-list terms as live target behavior

## Docs answer-sourcing proof

- required execution canon read and applied:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs/execution/README.md`
  - `docs/execution/phases/overview.md`
  - `docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md`
  - `docs/execution/maps/file-priority-map.md`
  - `docs/execution/maps/redesign-code-landing-map.md`
  - `docs/execution/gates/mandatory-review-gate.md`
  - `docs/execution/gates/reset-gate.md`
  - `docs/execution/gates/phase-done-gate.md`
- redesign owners and examples read for truthful wording:
  - `docs/redesign/workflows/workflow-definition-schema.md`
  - `docs/redesign/workflows/task-compose-schema.md`
  - `docs/redesign/workflows/typed-dependency-selectors-and-produce-slots.md`
  - `docs/redesign/workflows/mode-contract-and-legality-matrix.md`
  - `docs/redesign/workflows/criteria-and-parent-verification.md`
  - `docs/redesign/workflows/criteria-projection-and-consumption-example.md`
  - `docs/redesign/workflows/compiler-contract-and-launch-materialization.md`
  - `docs/redesign/workflows/provider-direction-and-provider-native-capabilities.md`
  - `docs/redesign/workflows/role-and-policy-example-definitions.md`
  - `docs/redesign/workflows/workflow-schema-appendix.md`
  - `docs/redesign/workflows/examples/minimal.md`
  - `docs/redesign/workflows/examples/normal.md`
  - `docs/redesign/workflows/examples/maximal.md`
  - `docs/redesign/interfaces/definition-registry-and-upload-contract.md`
  - `docs/redesign/interfaces/guarded-registry-and-runtime-writes.md`
  - `docs/redesign/workflows/README.md`
  - `docs/redesign/architecture/glossary-and-boundaries.md`
  - `docs/redesign/decisions/ADR-0002-deterministic-compiler-and-immutable-compiled-plans.md`
  - `docs/redesign/decisions/ADR-0003-parent-owned-execution-tree-and-boundary-advancement.md`
  - `docs/redesign/how-to/write-a-nested-workflow.md`
  - `docs/redesign/tutorials/create-a-definition-and-run-a-task.md`
- current-contrast reads used:
  - `docs/current/interfaces/definition-and-task-compose-yaml-contract.md`
  - `docs/current/interfaces/definition-precedence-and-skill-version-defaults.md`
  - `docs/current/interfaces/definition-registry-and-publish-lifecycle.md`
  - `docs/current/interfaces/definitions-compiler-and-launch.md`
- read-only downstream runtime cross-check used to retire stale earlier findings:
  - `apps/api/app/runtime/launch/projection.py`
  - `apps/api/app/runtime/projection/state.py`
  - `apps/api/tests/integration/test_phase2_runtime_bootstrap.py`
- downstream closeout cross-check used:
  - `docs/execution/evidence/phase-2-closeout-prompt-legality-and-proof.md`
  - `docs/execution/reviews/phase-2-closeout-prompt-legality-and-proof.md`
- canon gap or explicit `none`:
  - none

## Phase-bounded STYLE exceptions

- `apps/api/tests/unit/test_definition_schemas.py` remains 611 lines after the
  landed Phase 1 schema-proof slice. This exceeds the `STYLE.md` 600-line
  file-growth threshold, but this artifact-only closeout slice cannot safely
  split schema-regression coverage without broadening scope beyond the owned
  surfaces. Follow-up owner: a separate bounded Phase 1 test-organization
  cleanup slice before any future growth in this file.
- `apps/api/tests/unit/test_workflow_compiler.py` is now 707 lines after the
  landed optional-selector proof additions. This exceeds the `STYLE.md`
  600-line file-growth threshold, but this bounded Phase 1 slice cannot safely
  split compiler-legality coverage without widening beyond the owned surfaces.
  Follow-up owner: a separate bounded Phase 1 test-organization cleanup slice.
- `apps/api/tests/integration/test_definition_registry_db.py` is now 940 lines
  after the landed registry identity and concurrency proof additions. This
  exceeds the `STYLE.md` 600-line file-growth threshold, but this bounded
  Phase 1 slice cannot safely split registry proof lanes without widening
  beyond the owned surfaces. Follow-up owner: a separate bounded Phase 1
  integration-test organization cleanup slice.

## Reset-gate outcome

- satisfied by the authoritative Phase 1 evidence already attached
- shipped-path SQLite proof is recorded in
  `../evidence/phase-1-closeout-criteria-ownership-and-wp4.md` via
  `./.venv/bin/pytest -q apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/integration/test_registry_seed_authority.py apps/api/tests/integration/test_db_reset_db.py apps/api/tests/unit/test_cli.py`
  -> `17 passed`
- Postgres + Docker strong verification is recorded in
  `../evidence/phase-1-closeout-criteria-ownership-and-wp4.md` via
  `make test-api-db` -> `153 passed`

## Remaining exact blockers

- none inside the authoritative Phase 1 closeout chain
- downstream cross-check: the authoritative Phase 2 closeout chain records the
  criteria-owner consumption handoff as satisfied and reports no remaining
  exact blockers

## Cross-links

- authoritative plan:
  `../plans/phase-1-closeout-criteria-ownership-and-wp4.md`
- authoritative evidence:
  `../evidence/phase-1-closeout-criteria-ownership-and-wp4.md`
- superseded historical summary:
  `./phase-1-registry-reseed-and-proof-repair.md`
