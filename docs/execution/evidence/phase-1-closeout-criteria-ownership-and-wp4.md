# Phase 1 Closeout Criteria Ownership, WP4, and Proof Routing Evidence

Status: Reference

selected phase: Phase 1
current phase page: docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md
selected work packages: P1-WP1, P1-WP2, P1-WP3, P1-WP4
summary-only: no
delegated slices: listed
slice id: phase1-compiler-criteria-ownership
slice type: edit
owned surfaces: apps/api/app/registry/service.py, apps/api/app/registry/revision_upsert.py, apps/api/app/registry/lookup.py, apps/api/tests/unit/test_workflow_compiler.py, apps/api/tests/unit/test_workflow_compiler_*.py, apps/api/tests/integration/test_definition_registry_db.py, apps/api/tests/integration/test_definition_registry_db_*.py, docs/redesign/workflows/criteria-and-parent-verification.md, docs/redesign/workflows/compiler-contract-and-launch-materialization.md, docs/redesign/workflows/workflow-schema-appendix.md
touched surfaces: apps/api/app/registry/service.py, apps/api/app/registry/revision_upsert.py, apps/api/app/registry/lookup.py, apps/api/tests/unit/test_workflow_compiler.py, apps/api/tests/unit/test_workflow_compiler_*.py, apps/api/tests/integration/test_definition_registry_db.py, apps/api/tests/integration/test_definition_registry_db_*.py, docs/redesign/workflows/criteria-and-parent-verification.md, docs/redesign/workflows/compiler-contract-and-launch-materialization.md, docs/redesign/workflows/workflow-schema-appendix.md
slice id: phase1-examples-schema-proof
slice type: edit
owned surfaces: apps/api/tests/unit/test_definition_schemas.py, apps/api/tests/unit/test_definition_schemas_*.py, apps/api/tests/unit/definition_schema_test_support.py, docs/redesign/workflows/workflow-definition-schema.md, docs/redesign/workflows/examples/minimal.md, docs/redesign/workflows/examples/normal.md, docs/redesign/workflows/examples/maximal.md, definitions/workflows/*.yaml, apps/api/app/resources/definitions/workflows/*.yaml
touched surfaces: apps/api/tests/unit/test_definition_schemas.py, apps/api/tests/unit/test_definition_schemas_*.py, apps/api/tests/unit/definition_schema_test_support.py, docs/redesign/workflows/workflow-definition-schema.md, docs/redesign/workflows/examples/minimal.md, docs/redesign/workflows/examples/normal.md, docs/redesign/workflows/examples/maximal.md, definitions/workflows/*.yaml, apps/api/app/resources/definitions/workflows/*.yaml
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
  `P1-WP4` after the landed registry-service split, the split schema and
  compiler test suites, and the generalized same-key identical-update
  concurrency proof
- date: 2026-05-12
- owned surface:
  `docs/execution/evidence/phase-1-closeout-criteria-ownership-and-wp4.md`
- execution mode for this refresh: artifact rewrite only
- commands run in this refresh:
  - reran the unique Phase 1 split-suite `pytest` command recorded below
  - reran `make pyright-api`
  - aligned broader proof totals with the current-tree parent-validated
    full-suite and DB evidence recorded in the live Phase 0 closeout chain
- validation run in this refresh: read-only sanity on the owned execution
  artifacts, landed-surface alignment review, and current-tree proof alignment

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

## Parent-validated proof recorded by this refresh

- `./.venv/bin/ruff check apps/api/app/registry apps/api/tests/unit apps/api/tests/integration`
  - result: passed
- `./.venv/bin/mypy apps/api/app/registry apps/api/tests/unit/test_definition_schemas.py apps/api/tests/unit/test_definition_schemas_catalog.py apps/api/tests/unit/test_definition_schemas_examples.py apps/api/tests/unit/test_definition_schemas_role_policy.py apps/api/tests/unit/test_definition_schemas_workflow.py apps/api/tests/unit/definition_schema_test_support.py apps/api/tests/unit/test_workflow_compiler.py apps/api/tests/unit/test_workflow_compiler_lookup.py apps/api/tests/unit/test_workflow_compiler_semantics.py apps/api/tests/unit/test_workflow_compiler_structure.py apps/api/tests/unit/test_workflow_compiler_support.py apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/integration/test_definition_registry_db_launch_snapshot.py apps/api/tests/integration/test_definition_registry_db_concurrency.py apps/api/tests/integration/definition_registry_db_concurrency_support.py`
  - result: passed
- `cd apps/api && npx --yes pyright app/registry/service.py app/registry/revision_upsert.py app/registry/lookup.py tests/unit/test_definition_schemas.py tests/unit/test_definition_schemas_catalog.py tests/unit/test_definition_schemas_examples.py tests/unit/test_definition_schemas_role_policy.py tests/unit/test_definition_schemas_workflow.py tests/unit/definition_schema_test_support.py tests/unit/test_workflow_compiler.py tests/unit/test_workflow_compiler_lookup.py tests/unit/test_workflow_compiler_semantics.py tests/unit/test_workflow_compiler_structure.py tests/unit/test_workflow_compiler_support.py tests/integration/test_definition_registry_db.py tests/integration/test_definition_registry_db_launch_snapshot.py tests/integration/test_definition_registry_db_concurrency.py tests/integration/definition_registry_db_concurrency_support.py`
  - result: passed
- `./.venv/bin/pytest -q apps/api/tests/unit/test_definition_schemas.py apps/api/tests/unit/test_definition_schemas_catalog.py apps/api/tests/unit/test_definition_schemas_examples.py apps/api/tests/unit/test_definition_schemas_role_policy.py apps/api/tests/unit/test_definition_schemas_workflow.py apps/api/tests/unit/test_workflow_compiler.py apps/api/tests/unit/test_workflow_compiler_lookup.py apps/api/tests/unit/test_workflow_compiler_semantics.py apps/api/tests/unit/test_workflow_compiler_structure.py apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/integration/test_definition_registry_db_launch_snapshot.py apps/api/tests/integration/test_definition_registry_db_concurrency.py`
  - result: `64 passed`
- `make pyright-api`
  - result: passed
- `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest -q tests`
  - result: `238 passed in 947.69s (0:15:47)`
- `make test-api-db`
  - result: `236 passed in 751.09s (0:12:31)`

## Phase-local proof obligations

- split schema validation, compiler normalization, example alignment, and
  launch-snapshot or concurrency regression coverage
  - result: satisfied by the unique split-suite `pytest` lane above with
    `64 passed`
  - phase mapping: `P1-WP2`, `P1-WP3`, `P1-WP4`
- controller-owned definition identity, revision, and currentness proof on the
  shipped and strong-verification lanes
  - result: satisfied by the unique split-suite `pytest` lane above and
    `make test-api-db` -> `236 passed in 751.09s (0:12:31)`
  - phase mapping: `P1-WP1`
- repo-native Python static validation on the landed registry and test split
  surfaces
  - result: satisfied by `ruff check`, `mypy`, path-scoped `pyright`, and
    `make pyright-api`
  - phase mapping: `P1-WP1`, `P1-WP2`, `P1-WP3`, `P1-WP4`

## Landed surface alignment captured by this refresh

- registry write and lookup proof now follows the landed split across
  `apps/api/app/registry/service.py`,
  `apps/api/app/registry/revision_upsert.py`, and
  `apps/api/app/registry/lookup.py`
- definition-schema proof now follows the split suite:
  `test_definition_schemas.py`,
  `test_definition_schemas_catalog.py`,
  `test_definition_schemas_examples.py`,
  `test_definition_schemas_role_policy.py`,
  `test_definition_schemas_workflow.py`, and
  `definition_schema_test_support.py`
- compiler proof now follows the split suite:
  `test_workflow_compiler.py`,
  `test_workflow_compiler_lookup.py`,
  `test_workflow_compiler_semantics.py`,
  `test_workflow_compiler_structure.py`, and
  `test_workflow_compiler_support.py`
- registry integration proof now follows the split suite:
  `test_definition_registry_db.py`,
  `definition_registry_db_concurrency_support.py`,
  `test_definition_registry_db_launch_snapshot.py`, and
  `test_definition_registry_db_concurrency.py`

## Landed behavior proved by the refreshed lanes

- `compile_current_workflow_launch_snapshot()` compiles against the registry
  workflow key and rejects stored workflow-body `id` drift before
  materialization
- launch snapshot and guarded workflow validation load only the current role and
  explicit policy rows referenced by the selected workflow revision; unrelated
  corrupt current policy rows stay out of the compile path
- authored consume selectors still reject missing targets even when
  `required=false`, while normalized selector output still preserves the
  `required=false` flag for later runtime surfaces
- concurrent same-key identical updates now prove the same no-op or
  single-revision reuse law across role, policy, and workflow definitions:
  both writers reconcile to one new immutable revision instead of surfacing a
  duplicate-revision failure

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
  - verified the refreshed proof and surface inventory now match the landed
    registry split and split test-suite layout
  - verified the broader current-tree proof totals now match the live Phase 0
    closeout chain: full suite `238 passed` and DB lane `236 passed`
