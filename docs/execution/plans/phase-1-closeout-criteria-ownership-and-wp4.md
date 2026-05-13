# Phase 1 Local-Tool-First Audit And Record Repair Plan

Status: Reference

selected phase: Phase 1
current phase page: docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md
selected work packages: P1-WP1, P1-WP2, P1-WP3, P1-WP4
summary-only: no
delegated slices: listed
slice id: phase1-current-doc-and-record-refresh
slice type: edit
owned surfaces: docs/execution/plans/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/evidence/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/reviews/phase-1-closeout-criteria-ownership-and-wp4.md
touched surfaces: docs/execution/plans/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/evidence/phase-1-closeout-criteria-ownership-and-wp4.md, docs/execution/reviews/phase-1-closeout-criteria-ownership-and-wp4.md
slice id: phase1-proof-revalidation
slice type: review-only
owned surfaces: apps/api/app/compiler/**, apps/api/app/registry/**, apps/api/app/schemas/definitions/**, apps/api/tests/unit/definition_schemas/**, apps/api/tests/unit/workflow_compiler/**, apps/api/tests/integration/definition_registry/**, apps/api/tests/unit/test_cli.py, apps/api/app/cli.py
touched surfaces: none

## Slice identity

- selected phase: Phase 1
- approved execution brief: authoritative Phase 1 local-tool-first audit,
  proof revalidation, and record repair for the full Phase 1 package set
- date: 2026-05-13
- execution mode: closure-artifact repair plus local-tool-first audit only; no
  new Phase 1 product code or current-doc edits

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`
- landing map rows used for answer-sourcing and proof routing:
  `internal definition identity, revision, and currentness truth`,
  `authored workflow schema and legality`, and
  `compiler launch normalization`

## Objective

- normalize the authoritative Phase 1 plan, evidence, and review so they
  satisfy the current execution-record grammar and remain repo-local
- keep the chain truthful to this slice:
  - only the three Phase 1 execution artifacts are edited
  - Phase 1 code and tests are revalidated, not reopened
  - existing SQLite reset proof and the Postgres strong lane are rerun instead
    of carried forward as inherited claims
- remove the stale out-of-scope ownership claim that this closeout repair also
  edits current Phase 1 contrast docs

## Scope and truth constraints

- owned edit surfaces for this slice:
  - `docs/execution/plans/phase-1-closeout-criteria-ownership-and-wp4.md`
  - `docs/execution/evidence/phase-1-closeout-criteria-ownership-and-wp4.md`
  - `docs/execution/reviews/phase-1-closeout-criteria-ownership-and-wp4.md`
- proof-only surfaces inspected and revalidated:
  - `apps/api/app/compiler/**`
  - `apps/api/app/registry/**`
  - `apps/api/app/schemas/definitions/**`
  - `apps/api/tests/unit/definition_schemas/**`
  - `apps/api/tests/unit/workflow_compiler/**`
  - `apps/api/tests/integration/definition_registry/**`
  - `apps/api/tests/unit/test_cli.py`
  - `apps/api/app/cli.py`
- do not claim:
  - a new schema, compiler, registry, CLI, or current-doc behavior change
  - a broader Phase 2 or Phase 3 repair
  - a repo-wide `docs_freeze` pass if remaining failures are outside Phase 1

## Delegated slice briefs

### phase1-current-doc-and-record-refresh

- do-not-edit surfaces:
  - all repo files outside the three owned Phase 1 execution artifacts
- required reads:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs/execution/README.md`
  - `docs/execution/maps/file-priority-map.md`
  - `docs/execution/maps/redesign-code-landing-map.md`
  - `docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md`
  - `docs/execution/gates/mandatory-review-gate.md`
  - `docs/execution/gates/reset-gate.md`
  - `docs/execution/gates/code-quality-gate.md`
  - the current Phase 1 plan, evidence, and review
  - the current `docs_freeze` failure output for missing delegated-slice body
    briefs and missing style/private-symbol proof language
- required tests/validators:
  - rerun `./.venv/bin/python -m scripts.docs.docs_freeze.cli validate` after
    the rewrite and confirm any remaining failures are outside Phase 1
- expected outputs:
  - validator-compliant delegated-slice body briefs in the plan
  - rewritten evidence and review text that only claims this closure-repair
    slice and the rerun proof lanes
  - removal of stale out-of-scope ownership claims from the Phase 1 chain
- dependencies:
  - fresh proof results from the review-only proof lane
- evidence to return:
  - updated plan/evidence/review artifacts
  - `docs_freeze` result showing no remaining Phase 1-specific validator error
- parent-owned decisions:
  - whether later-phase validator failures are treated as blockers for the full
    program rather than for this Phase 1 slice
- stop conditions:
  - stop if truthful repair would require edits outside the three owned Phase 1
    artifacts
  - stop if Phase 1 closure truth depends on reopening current docs or Phase 1
    code paths

### phase1-proof-revalidation

- do-not-edit surfaces:
  - all repo-tracked files; this is a review-only slice
- required reads:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs/execution/README.md`
  - `docs/execution/maps/file-priority-map.md`
  - `docs/execution/maps/redesign-code-landing-map.md`
  - `docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md`
  - `docs/execution/gates/mandatory-review-gate.md`
  - `docs/execution/gates/reset-gate.md`
  - `docs/execution/gates/code-quality-gate.md`
  - `docs/redesign/workflows/workflow-definition-schema.md`
  - `docs/redesign/workflows/task-compose-schema.md`
  - `docs/redesign/workflows/compiler-contract-and-launch-materialization.md`
  - `docs/redesign/interfaces/definition-registry-and-upload-contract.md`
  - `docs/redesign/interfaces/guarded-registry-and-runtime-writes.md`
  - `docs/redesign/workflows/workflow-schema-appendix.md`
  - `docs/redesign/interfaces/role-and-policy-definition-schema.md`
  - `docs/current/interfaces/definitions-compiler-and-launch.md`
  - `docs/current/interfaces/definition-precedence-and-skill-version-defaults.md`
  - `docs/current/interfaces/definition-registry-and-publish-lifecycle.md`
  - the live Phase 1 code and tests under the owned proof surfaces above
- required tests/validators:
  - `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
  - `make pyright-api`
  - `./.venv/bin/pytest -q apps/api/tests/unit/definition_schemas apps/api/tests/unit/workflow_compiler apps/api/tests/integration/definition_registry`
  - `./.venv/bin/pytest -q apps/api/tests/unit/test_cli.py -k 'packaged_seed_definitions_are_available or init_writes_minimal_config_and_db_file or db_reset_recreates_sqlite_database or db_upgrade_bootstraps_seeded_sqlite_database_on_shipped_path'`
  - `make test-api-db`
  - exact repo search for cross-module underscore-private imports across the
    Phase 1 code and proof paths
- expected outputs:
  - fresh Phase 1 proof results for style audit, typing, schema/compiler or
    registry tests, SQLite reset proof, and Postgres strong verification
  - explicit note on whether any Phase 1 product drift was discovered
- dependencies:
  - none
- evidence to return:
  - commands run with pass or fail outcomes
  - exact repo search result for private symbol or underscore-private imports
  - blocker note if SQLite reset proof or `make test-api-db` could not be rerun
- parent-owned decisions:
  - whether any failure indicates a true Phase 1 product regression or only a
    closure-artifact repair blocker
- stop conditions:
  - stop if the proof run reveals a real Phase 1 product defect that would
    require edits outside the three owned artifacts
  - stop if the strong DB or shipped-path SQLite lane is unavailable and must
    be triaged in an owning infrastructure slice

## Validation checkpoints

- delegated-slice body briefs exist for each listed slice and include every
  required field from the new validator
- the rewritten evidence and review include truthful `style_audit` proof and
  exact repo search or underscore-private proof language
- the rewritten evidence and review include rerun SQLite reset proof and
  `make test-api-db` strong-lane proof, not inherited summaries
- `docs_freeze` no longer reports Phase 1-specific execution-record errors

## Exit criteria

- the authoritative Phase 1 triplet remains the `summary-only: no` closure
  chain for the full Phase 1 package set
- the chain now describes only closure-artifact repair plus proof
  revalidation, not a broader code or current-doc change
- Phase 1 proof lanes are recorded with fresh results and Phase 1-specific
  validator complaints are cleared

## Stop conditions

- stop if truthful Phase 1 repair would require touching current docs, code,
  tests, or other phase artifacts outside the owned surfaces
- stop if rerun proof finds a real compiler, schema, registry, or shipped-path
  defect that belongs to a Phase 1 product work package instead of this
  closure-artifact rebuild

## Cross-links

- evidence artifact:
  `../evidence/phase-1-closeout-criteria-ownership-and-wp4.md`
- review artifact:
  `../reviews/phase-1-closeout-criteria-ownership-and-wp4.md`
