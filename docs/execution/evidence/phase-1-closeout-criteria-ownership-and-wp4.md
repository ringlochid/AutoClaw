# Phase 1 Closeout Criteria Ownership, WP4, and Proof Routing Evidence

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
- work package or slice: authoritative evidence routing for `P1-WP1` through
  `P1-WP4`
- date: 2026-05-06
- owned surface:
  `docs/execution/evidence/phase-1-closeout-criteria-ownership-and-wp4.md`
- execution mode for this refresh: artifact rewrite only
- commands run in this refresh: none
- validation run in this refresh: read-only sanity on the owned execution
  artifacts only

## Plan and review links

- approved plan: `../plans/phase-1-closeout-criteria-ownership-and-wp4.md`
- mandatory review: `../reviews/phase-1-closeout-criteria-ownership-and-wp4.md`
- review artifact: `../reviews/phase-1-closeout-criteria-ownership-and-wp4.md`

## Authoritative evidence rule

- this file is the authoritative Phase 1 closeout-path evidence record inside
  the owned surfaces
- the older registry-reseed evidence chain is historical support only after
  this chain lands:
  `../evidence/phase-1-registry-reseed-and-proof-repair.md`

## Commands run

- `./.venv/bin/pytest -q apps/api/tests/unit/test_workflow_compiler.py apps/api/tests/unit/test_definition_schemas.py`
  - result: `49 passed`
  - phase mapping: `P1-WP2`, `P1-WP3`, `P1-WP4`
- `./.venv/bin/pytest -q apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/integration/test_registry_seed_authority.py apps/api/tests/integration/test_db_reset_db.py apps/api/tests/unit/test_cli.py`
  - result: `17 passed`
  - phase mapping: `P1-WP1`
- `./.venv/bin/ruff format --check apps/api/app/compiler/contracts.py apps/api/app/compiler/normalize.py apps/api/tests/unit/test_definition_schemas.py apps/api/tests/unit/test_workflow_compiler.py`
  - result: passed
- `./.venv/bin/ruff check apps/api/app/compiler/contracts.py apps/api/app/compiler/normalize.py apps/api/tests/unit/test_definition_schemas.py apps/api/tests/unit/test_workflow_compiler.py`
  - result: passed
- `./.venv/bin/mypy apps/api/app/compiler/contracts.py apps/api/app/compiler/normalize.py apps/api/tests/unit/test_definition_schemas.py apps/api/tests/unit/test_workflow_compiler.py`
  - result: passed
- `make pyright-api`
  - result: `0 errors, 0 warnings, 0 informations`
- `make test-api-db`
  - result: `153 passed`
  - phase mapping: `P1-WP1`

## Phase-local proof obligations

- proof lane:
  - focused compiler criteria-ownership proof
  - result: satisfied by `49 passed`
  - phase mapping: `P1-WP2`, `P1-WP3`
- proof lane:
  - example or fixture validation for minimal, normal, and maximal workflow
    YAML and aligned packaged mirrors
  - result: satisfied by `49 passed`
  - phase mapping: `P1-WP4`
- proof lane:
  - acceptance or regression proof that removed generic authored `skill_refs`
    semantics stay rejected or intentionally isolated
  - result: satisfied by `49 passed`
  - phase mapping: `P1-WP4`
- proof lane:
  - shipped-path SQLite `autoclaw init`, `autoclaw db upgrade`, and
    `autoclaw db reset`
  - result: satisfied by `17 passed`
  - phase mapping: `P1-WP1`
- proof lane:
  - Postgres + Docker strong verification when viable
  - result: satisfied by `153 passed`
  - phase mapping: `P1-WP1`

## 2026-05-07 follow-up refresh

- slice scope:
  - registry-owned workflow identity at launch snapshot time
  - referenced-only role and policy current-revision lookup for workflow compile
  - required-selector semantics proof
  - same-key update/no-op concurrency proof on the workflow path
- commands run:
  - `./.venv/bin/pytest -q apps/api/tests/unit/test_workflow_compiler.py apps/api/tests/unit/test_definition_schemas.py apps/api/tests/integration/test_definition_registry_db.py`
    - result: `61 passed`
  - `./.venv/bin/ruff format --check apps/api/app/registry/lookup.py apps/api/app/registry/service.py apps/api/tests/unit/test_workflow_compiler.py apps/api/tests/unit/test_definition_schemas.py apps/api/tests/integration/test_definition_registry_db.py`
    - result: `5 files already formatted`
  - `./.venv/bin/ruff check apps/api/app/registry/lookup.py apps/api/app/registry/service.py apps/api/tests/unit/test_workflow_compiler.py apps/api/tests/unit/test_definition_schemas.py apps/api/tests/integration/test_definition_registry_db.py`
    - result: passed
  - `./.venv/bin/mypy apps/api/app/registry/lookup.py apps/api/app/registry/service.py apps/api/tests/unit/test_workflow_compiler.py apps/api/tests/unit/test_definition_schemas.py apps/api/tests/integration/test_definition_registry_db.py`
    - result: `Success: no issues found in 5 source files`
  - `make pyright-api`
    - result: failed outside owned surfaces with pre-existing errors in `apps/api/app/runtime/control/assign_child.py` and `apps/api/app/runtime/control/boundary.py`
  - `cd apps/api && npx --yes pyright app/registry/lookup.py app/registry/service.py tests/unit/test_workflow_compiler.py tests/unit/test_definition_schemas.py tests/integration/test_definition_registry_db.py`
    - result: `0 errors, 0 warnings, 0 informations`
- landed proof:
  - `compile_current_workflow_launch_snapshot()` now compiles against the registry workflow key and rejects a corrupt stored workflow body `id`
  - launch snapshot compilation and guarded workflow validation now load only referenced current role/policy rows, so an unrelated corrupt current policy row no longer blocks workflow compile
  - authored consume-selector target existence still rejects even when `required=false`
  - normalized consume selectors still preserve `required=false` for later runtime surfaces
  - identical concurrent same-key workflow updates now reconcile to one new immutable revision on the workflow path instead of surfacing a duplicate-revision uniqueness failure

## Criteria ownership routing captured by this refresh

- authored criteria ownership stays with the declaring node plus any legal
  direct-parent `child_defaults.criteria` expansion
- runtime assignment surfaces may carry current exact criteria refs for one
  attempt, but they do not rewrite the authored baseline contract
- `P1-WP4` closure therefore depends on examples, fixtures, and acceptance
  paths teaching that authored ownership split correctly

## Historical support retained

- superseded historical plan:
  `../plans/phase-1-registry-reseed-and-proof-repair.md`
- superseded historical evidence:
  `../evidence/phase-1-registry-reseed-and-proof-repair.md`
- superseded historical review:
  `../reviews/phase-1-registry-reseed-and-proof-repair.md`
- scope note:
  - those files retain earlier `P1-WP1`..`P1-WP3` context only
  - they are not the final closeout evidence authority once this chain exists

## Validation for this refresh

- read-only sanity:
  - verified the exact parseable labels remain at line start
  - verified the superseded registry-reseed chain is referenced as historical
    support only

## Review link

- review artifact:
  `../reviews/phase-1-closeout-criteria-ownership-and-wp4.md`
