# Phase 1 Registry Reseed and Shipped-Path Proof Repair

Status: Reference

## Slice identity

- selected phase: Phase 1
- work package or slice: registry reseed semantics, shipped-path proof, and current-contrast parity
- owner: Codex
- date: 2026-05-05

## Subagents decision

- delegated slices:
  - registry reseed semantics and persistence tests
  - shipped-path init/upgrade/reset proof tests
  - current-contrast doc parity for registry/seed behavior
  - review-only Phase 1 gate audit

## Goal

- make shipped reseed create or reuse immutable revisions correctly, preserve
  controller-selected currentness, and prove shipped-path `init`, `db upgrade`,
  and `db reset` behavior explicitly

## Phase-local contract

- current phase page: `docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md`
- implementation file lock map: `docs/execution/maps/file-priority-map.md`
- required reads completed: yes

## Locked surfaces

- owned surfaces: `apps/api/app/registry/*`, internal registry persistence under `apps/api/app/db/*`, compiler-facing registry tests, shipped-path proof tests, and Phase 1 redesign owners where needed
- allowed collateral surfaces:
  - `apps/api/app/cli.py`
  - `apps/api/app/resources/definitions/**`
  - narrow `pyproject.toml` package-data entries if needed
  - the three named Phase 1 current-contrast definition pages as phase-bounded current-behavior parity updates after landed code truth
- do not edit or defer surfaces: runtime assignment/dispatch/replan persistence, public ingest routes, wider package/release surfaces

## Success criteria

- changed seed content appends a new immutable revision
- currentness stays on a newer controller-selected revision when reseed should not promote
- packaged seed provenance is stable across packaged extraction paths
- positive shipped-path `init`, `db upgrade`, and `db reset` proof exists
- current docs match landed shipped behavior

## Deliverables and milestones

- deliverables:
  - landed reseed semantics in registry service and seed path
  - positive shipped-path proof tests
  - aligned current-contrast registry docs
  - Phase 1-scoped plan/evidence/review artifacts
- milestones:
  - reseed semantics aligned
  - shipped-path proof aligned
  - current docs aligned
  - Postgres/Docker lane green

## Ordered work packages

- `P1-WP1`: stable seed-source identity and append-or-reuse reseed semantics
- `P1-WP2`: preserve newer controller-selected currentness when reseed should not promote
- `P1-WP3`: positive shipped-path `autoclaw db upgrade` proof
- `P1-WP4`: current-contrast doc parity for landed shipped behavior
- `P1-WP5`: Phase 1 evidence and review

## Validation checkpoints

- focused registry persistence lane passes
- focused CLI/reset/seed-authority lane passes
- `docs_freeze_validate.py` passes after current-doc updates
- `make pyright-api` passes
- Docker/Postgres strong verification passes

## Required tests and validators

- `./.venv/bin/ruff format --check apps/api/app/registry/seeds.py apps/api/app/registry/service.py apps/api/app/registry/support.py apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/unit/test_cli.py`
- `./.venv/bin/ruff check apps/api/app/registry/seeds.py apps/api/app/registry/service.py apps/api/app/registry/support.py apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/unit/test_cli.py`
- `./.venv/bin/mypy apps/api/app/registry/seeds.py apps/api/app/registry/service.py apps/api/app/registry/support.py apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/unit/test_cli.py`
- `make pyright-api`
- `./.venv/bin/pytest -q apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/integration/test_registry_seed_authority.py apps/api/tests/integration/test_db_reset_db.py apps/api/tests/unit/test_cli.py`
- `./.venv/bin/python scripts/docs/docs_freeze_validate.py`
- `make test-api-db`

## Required docs and examples

- `docs/current/interfaces/definition-precedence-and-skill-version-defaults.md`
- `docs/current/interfaces/definitions-compiler-and-launch.md`
- `docs/current/interfaces/definition-registry-and-publish-lifecycle.md`
- Phase 1 redesign owners and workflow appendix as read-only contract sources unless a fix requires updates

## Exit evidence

- evidence artifact: `../evidence/phase-1-registry-reseed-and-proof-repair.md`

## Rollback or stop conditions

- stop if fixing reseed semantics requires public ingest or broader CLI noun changes
- stop if a required current-doc repair extends beyond the three named Phase 1 current-contrast pages without a canon update
- stop if Docker/Postgres verification exposes schema/reset behavior that needs Phase 5B-owned package/install work

## Cross-links

- evidence artifact: `../evidence/phase-1-registry-reseed-and-proof-repair.md`
- review artifact: `../reviews/phase-1-registry-reseed-and-proof-repair.md`
