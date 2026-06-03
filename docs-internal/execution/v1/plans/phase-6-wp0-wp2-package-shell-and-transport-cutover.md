# Phase 6 WP0-WP2 Package Shell And Transport Cutover Plan

Status: Reference

selected phase: Phase 6
current phase page: docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md
selected work packages: P6-WP0, P6-WP1, P6-WP2
summary-only: no
delegated slices: none

## Slice identity

- owner: Codex
- date: 2026-06-03
- work package bundle: `P6-WP0` through `P6-WP2`

## Subagents decision

- no subagents
- reason: the user explicitly requested no subagents for the doc-heavy opening tranche

## Goal

- repair the live Phase 6 packet so the later `P6-WP3` through `P6-WP5` work is divided cleanly
- land the opening source tranche through `P6-WP2`: gate-unblock collateral, `src/autoclaw` package-shell authority, and public transport-shell cutover

## Phase-local contract

- current phase page: `docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md`
- implementation file lock map: `docs-internal/execution/v1/maps/file-priority-map.md`
- authoritative companion packets:
  - `docs-internal/execution/v1/plans/phase-6-source-audit-and-rename-map.md`
  - `docs-internal/execution/v1/plans/phase-6-full-source-owner-convergence-and-package-migration.md`

## Locked surfaces

- owned surfaces:
  - the Phase 6 execution docs touched by the `P6-WP0` reopen
  - `apps/api/src/autoclaw/**` public package shell
  - `apps/api/app/main.py`
  - `apps/api/app/cli/__init__.py`
  - `apps/api/app/cli/commands/server_config.py`
  - repo-native import shells under `Makefile`, `apps/api/Dockerfile`, `scripts/testing/run_api_pytest_groups.sh`, and `apps/api/tests/run_integration_groups.sh`
  - focused proof surfaces under `apps/api/tests/unit/**`
- allowed collateral surfaces used in this bundle:
  - `apps/api/tests/integration/phase5a/test_root_cli_phase5a.py`
  - `apps/api/tests/integration/phase3/routes/**`
  - `apps/api/tests/integration/test_readyz_real_db.py`
  - `apps/api/tests/integration/test_startup_schema_guard.py`
  - `scripts/docs/style_audit/**`
  - `apps/api/tests/unit/test_docs_freeze.py`

## Work package bundle

### `P6-WP0`

- repair the live Phase 6 docs chain so it matches current truth
- legalize the exact opening gate-unblock edits in `apps/api/app/cli/__init__.py` and `apps/api/app/cli/commands/server_config.py`
- remove stale live-owner references to deleted `cli_commands/**` and `terminal/**` trees
- record the bounded package sequence for later `P6-WP3` through `P6-WP5` work

### `P6-WP1`

- introduce `apps/api/src/autoclaw/**` as the repo-native public package shell
- make runner and subprocess import resolution prefer `apps/api/src` before `apps/api`
- keep legacy `apps/api/autoclaw/**` available only as temporary compatibility shells

### `P6-WP2`

- move the public API and CLI shells needed by the package entrypoints into `src/autoclaw`
- keep the deeper non-transport OpenClaw internals deferred to `P6-WP4`
- keep the legacy `app/**` transport entrypoints behavior-stable while the public shell cutover lands

## Validation loop

- `make format-api`
- `make check-api`
- touched-scope `./.venv/bin/python -m scripts.docs.style_audit.cli --scan-root ... --fail-on-findings`
- focused unit proof:
  - `apps/api/tests/unit/test_style_audit.py`
  - `apps/api/tests/unit/test_docs_freeze.py`
  - `apps/api/tests/unit/test_package_entrypoints.py`
  - `apps/api/tests/unit/cli/test_main.py`
  - `apps/api/tests/unit/test_cli.py`
- focused integration proof:
  - `apps/api/tests/integration/phase5a/test_root_cli_phase5a.py`
  - `apps/api/tests/integration/phase3/routes`
  - `apps/api/tests/integration/test_readyz_real_db.py`
  - `apps/api/tests/integration/test_startup_schema_guard.py`
- docs validators:
  - `ruff check scripts/docs apps/api/tests/unit/test_style_audit.py apps/api/tests/unit/test_docs_freeze.py`
  - `mypy scripts/docs`
  - `./.venv/bin/python -m scripts.docs.docs_freeze.cli`

## Exit evidence

- the Phase 6 packet names the bounded package sequence for `P6-WP3` through `P6-WP5`
- the repo-native public shell prefers `apps/api/src/autoclaw/**`
- `make check-api` is green
- the focused `WP0` to `WP2` proof selectors are green
- the expensive full backend matrix remains explicitly deferred
