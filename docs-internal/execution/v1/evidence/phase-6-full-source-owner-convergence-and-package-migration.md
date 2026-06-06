# Phase 6 Full Source Owner Convergence And Package Migration Evidence

Status: Reference

selected phase: Phase 6
current phase page: docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md
selected work packages: P6-WP3, P6-WP4, P6-WP5
summary-only: yes
delegated slices: listed
slice id: p6_wp3_worker
slice type: edit
owned surfaces: apps/api/src/autoclaw/{api,cli,compiler,db,registry,schemas,platform}/**, root package modules, matching proof tests
touched surfaces: apps/api/src/autoclaw/interfaces/**, apps/api/src/autoclaw/definitions/**, apps/api/src/autoclaw/persistence/**, apps/api/src/autoclaw/runtime/contracts/**, apps/api/tests/**
slice id: p6_wp4_worker
slice type: edit
owned surfaces: apps/api/src/autoclaw/runtime/**, adjacent integrations/openclaw gateway/runtime-io surfaces, matching proof tests
touched surfaces: apps/api/src/autoclaw/runtime/**, apps/api/src/autoclaw/integrations/openclaw/**, apps/api/tests/**
slice id: p6_wp5_worker
slice type: edit
owned surfaces: pyproject.toml, Makefile, docker-compose.yml, apps/api/Dockerfile, apps/api/pyrightconfig.json, scripts/testing/run_api_pytest_groups.sh, remaining package/test compatibility debt
touched surfaces: pyproject.toml, Makefile, docker-compose.yml, apps/api/Dockerfile, apps/api/pyrightconfig.json, scripts/testing/run_api_pytest_groups.sh, apps/api/tests/**

## Slice identity

- work package bundle: `P6-WP3` through `P6-WP5`
- date: 2026-06-05

## Authoritative replacements

- `../plans/phase-6-full-source-owner-convergence-and-package-migration.md`
- `../evidence/phase-6-overflow-source-owner-and-runtime-convergence.md`
- `../reviews/phase-6-overflow-source-owner-and-runtime-convergence.md`
- `../plans/phase-7-proof-pattern-and-leak-cleanup.md`
- `../evidence/phase-7-proof-pattern-and-leak-cleanup.md`
- `../reviews/phase-7-proof-pattern-and-leak-cleanup.md`

## Plan and review links

- approved plan: `../plans/phase-6-full-source-owner-convergence-and-package-migration.md`
- mandatory review: `../reviews/phase-6-full-source-owner-convergence-and-package-migration.md`
- review artifact: `../reviews/phase-6-full-source-owner-convergence-and-package-migration.md`

## Commands run

- `make format-api`
- `make check-api`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --scan-root apps/api/src/autoclaw --fail-on-findings`
- `./.venv/bin/ruff check scripts/docs`
- `./.venv/bin/mypy scripts/docs`
- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- `make api-install`
- `./.venv/bin/autoclaw --help`
- `make test-api`
- `make test-api-integration-local`
- `make test-api-db`
- `make test-api-e2e-minimal`
- `make test-api-e2e-normal`
- `make test-api-e2e-maximal`

## Gate and validator summary

- historical snapshot only: this packet preserves the originally recorded command bundle, but the merged reopen findings and the live reopened Phase 6 / Phase 7 plans mean it is no longer truthful closure authority
- package, lint, mypy, and pyright gates are green after the package-authority flip and final compatibility purge
- source-only Phase 6 style audit over `apps/api/src/autoclaw` is green with `0` findings
- docs tooling proof is green: `ruff check scripts/docs`, `mypy scripts/docs`, and `scripts.docs.docs_freeze.cli`
- local install truth is green: `make api-install` reinstalls the canonical package and `./.venv/bin/autoclaw --help` works
- full backend proof matrix is green:
  - `make test-api`
  - `make test-api-integration-local`
  - `make test-api-db`
  - `make test-api-e2e-minimal`
  - `make test-api-e2e-normal`
  - `make test-api-e2e-maximal`

## Scope landed

- `P6-WP3`: public HTTP, CLI, MCP, definitions, persistence, and contract owners now live under the converged `interfaces/**`, `definitions/**`, `persistence/**`, and `runtime/contracts/**` families
- `P6-WP4`: runtime owners now live under direct domain families plus `runtime/post_commit/**`, `runtime/dispatch/**`, and `integrations/openclaw/{gateway,runtime_io}.py`; mechanism-first `runtime/control/**`, `runtime/effects/**`, and `runtime/openclaw/**` compatibility dependencies were removed from live code
- `P6-WP5`: package metadata, install path, local runner truth, Docker/compose truth, and final code-side compatibility debt now match the converged package root

## Artifacts changed

- `AGENTS.md`
- `.agents/standards/code/naming.md`
- `.agents/standards/structure/integration-boundaries.md`
- `.agents/standards/structure/repo-layout.md`
- `.agents/standards/structure/source-layout.md`
- `Makefile`
- `docker-compose.yml`
- `apps/api/Dockerfile`
- `apps/api/pyrightconfig.json`
- `apps/api/src/autoclaw/**`
- `apps/api/tests/**`
- `scripts/docs/docs_freeze/**`
- `scripts/docs/prompt_catalog/load.py`
- `scripts/docs/style_audit/**`
- `docs/**`
- `docs-internal/current/**`
- `docs-internal/execution/v1/**`

## Residual blockers

- merged reopen findings reopened live Phase 6 and Phase 7 work after this snapshot; use the authoritative replacements above instead of this historical summary for current closure truth
