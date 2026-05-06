# Phase 1 Registry Reseed and Shipped-Path Proof Repair Evidence

Status: Reference

selected phase: Phase 1
current phase page: docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md
selected work packages: P1-WP1, P1-WP2, P1-WP3
summary-only: no
delegated slices: none

## Slice identity

- selected phase: Phase 1
- work package or slice: authoritative evidence refresh for `P1-WP1`, `P1-WP2`, and `P1-WP3`
- approved final slice: authoritative evidence refresh only
- date: 2026-05-06
- owned surface: `docs/execution/evidence/phase-1-registry-reseed-and-proof-repair.md`
- execution mode for this refresh: artifact rewrite only
- commands run in this refresh: none
- validation run in this refresh: read-only sanity on the owned file only

## Plan and review links

- approved plan: `../plans/phase-1-registry-reseed-and-proof-repair.md`
- mandatory review: `../reviews/phase-1-registry-reseed-and-proof-repair.md`

## Proof provenance

- direct Phase 1 authority: record the locked final rerun values for schema,
  compiler, and registry or seed or reset or CLI proof on 2026-05-06
- broader shared proof only: `make test-api-db` and `make pyright-api` are
  recorded here as supporting shared proof and must not be treated as pure
  Phase 1-only authority

## Locked proof results

- proof lane:
  - `./.venv/bin/pytest -q apps/api/tests/unit/test_definition_schemas.py`
  - result: `38 passed`
  - phase mapping: `P1-WP2`
- proof lane:
  - `./.venv/bin/pytest -q apps/api/tests/unit/test_workflow_compiler.py`
  - result: `10 passed`
  - phase mapping: `P1-WP3`
- proof lane:
  - `./.venv/bin/pytest -q apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/integration/test_registry_seed_authority.py apps/api/tests/integration/test_db_reset_db.py apps/api/tests/unit/test_cli.py`
  - result: `17 passed`
  - phase mapping: `P1-WP1`, `P1-WP2`
- broader shared proof:
  - `make test-api-db`
  - result: `152 passed`
  - scope note: broader shared shipped-path and integration proof; do not
    treat it as pure Phase 1-only authority
- broader shared proof:
  - `make pyright-api`
  - result: `0 errors`
  - scope note: broader shared typing proof; do not treat it as pure Phase
    1-only authority

## Phase 1 closeout mapping

- `P1-WP1`: registry currentness and shipped-path seed or reset proof is
  represented by the `17 passed` registry or seed or reset or CLI lane
- `P1-WP2`: schema validation proof is represented by
  `test_definition_schemas.py -> 38 passed` plus the registry-backed
  validation coverage inside the `17 passed` aggregate
- `P1-WP3`: compiler dotted-id opacity and legality proof is represented by
  `test_workflow_compiler.py -> 10 passed`

## Scope limits

- this evidence refresh is a documentation repair only and does not claim a
  fresh rerun in this shell session
- `make test-api-db` and `make pyright-api` remain supporting shared proof
  rather than Phase 1-exclusive authority
- `P1-WP4` examples and fixtures are not claimed by this artifact

## Validation for this refresh

- read-only sanity:
  - verified the owned file keeps the exact parseable labels at line start
  - verified the recorded proof values are `38 passed`, `10 passed`,
    `17 passed`, `152 passed`, and `0 errors`

## Review link

- review artifact: `../reviews/phase-1-registry-reseed-and-proof-repair.md`
