# Phase 6 WP0-WP2 Package Shell And Transport Cutover Evidence

Status: Reference

selected phase: Phase 6
current phase page: docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md
selected work packages: P6-WP0, P6-WP1, P6-WP2
summary-only: yes
delegated slices: none

## Slice identity

- work package bundle: `P6-WP0` through `P6-WP2`
- date: 2026-06-03

## Authoritative replacements

- `docs-internal/execution/v1/evidence/phase-0-phase6-reopen-canon-reset.md`
- `docs-internal/execution/v1/plans/phase-6-full-source-owner-convergence-and-package-migration.md`

## Plan and review links

- tranche plan: `../plans/phase-6-wp0-wp2-package-shell-and-transport-cutover.md`
- `P6-WP0` baseline packet: `../plans/phase-6-source-audit-and-rename-map.md`
- later master plan: `../plans/phase-6-full-source-owner-convergence-and-package-migration.md`
- approved plan: `../plans/phase-6-wp0-wp2-package-shell-and-transport-cutover.md`
- mandatory review: `../reviews/phase-6-wp0-wp2-package-shell-and-transport-cutover.md`
- review artifact: `../reviews/phase-6-wp0-wp2-package-shell-and-transport-cutover.md`

## Commands run

- `make format-api`
- `make check-api`
- `PYTHONPATH=/home/ubuntu/leo/projects/autoclaw/apps/api/src:/home/ubuntu/leo/projects/autoclaw/apps/api ./.venv/bin/python -m pytest apps/api/tests/unit/test_style_audit.py apps/api/tests/unit/test_package_entrypoints.py apps/api/tests/unit/cli/test_main.py apps/api/tests/unit/test_cli.py -q`
- `PYTHONPATH=/home/ubuntu/leo/projects/autoclaw/apps/api/src:/home/ubuntu/leo/projects/autoclaw/apps/api ./.venv/bin/python -m pytest apps/api/tests/unit/test_docs_freeze.py -q`
- `PYTHONPATH=/home/ubuntu/leo/projects/autoclaw/apps/api/src:/home/ubuntu/leo/projects/autoclaw/apps/api ./.venv/bin/python -m pytest apps/api/tests/integration/phase5a/test_root_cli_phase5a.py apps/api/tests/integration/phase3/routes apps/api/tests/integration/test_readyz_real_db.py apps/api/tests/integration/test_startup_schema_guard.py -q`
- `PYTHONPATH=/home/ubuntu/leo/projects/autoclaw/apps/api/src:/home/ubuntu/leo/projects/autoclaw/apps/api ./.venv/bin/python -m scripts.docs.style_audit.cli --scan-root apps/api/src/autoclaw/__init__.py --scan-root apps/api/src/autoclaw/__main__.py --scan-root apps/api/src/autoclaw/main.py --scan-root apps/api/src/autoclaw/cli --scan-root apps/api/src/autoclaw/api --scan-root apps/api/autoclaw/__init__.py --scan-root apps/api/autoclaw/__main__.py --scan-root apps/api/src/autoclaw/interfaces/cli/main.py --scan-root apps/api/autoclaw/main.py --scan-root apps/api/src/autoclaw/interfaces/cli/__init__.py --scan-root apps/api/src/autoclaw/interfaces/cli/commands/server_config.py --fail-on-findings`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --scan-root apps/api/app --scan-root apps/api/autoclaw --scan-root apps/api/src/autoclaw`
- `./.venv/bin/ruff check scripts/docs apps/api/tests/unit/test_style_audit.py apps/api/tests/unit/test_docs_freeze.py`
- `./.venv/bin/mypy scripts/docs`
- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`

## Gate and validator summary

- `make check-api`: passed
- touched-scope Phase 6 style audit across the `src` shell and legacy top-level `autoclaw` shims: passed with `No findings`
- docs validator lane: passed
- repo-native import shells now prefer `apps/api/src` before `apps/api`
- report-only full Phase 6 audit over `apps/api/app`, `apps/api/autoclaw`, and `apps/api/src/autoclaw`: duplicate module-name ownership findings reduced to `0`; remaining import-direction, module-shape, naming, and function-size debt is the deferred `P6-WP3` through `P6-WP5` backlog

## Test lanes

- unit shell and package proof: `61 passed, 1 skipped`
- docs-freeze unit proof: `10 passed`
- integration: `48 passed`
- e2e: not run by design for this pre-closeout tranche
- SQLite: covered by the focused CLI and route selectors above
- Postgres or Docker: not run by design for this tranche

## Scope landed

- `P6-WP0`: the Phase 6 execution-doc packet now legalizes the opening gate-unblock edits, removes stale live-owner references to deleted `cli_commands/**` and `terminal/**` trees, and records the bounded package sequence for later `P6-WP3` through `P6-WP5` work
- `P6-WP1`: repo-native public-package resolution now prefers `apps/api/src` before `apps/api` in the dev shell, grouped test runner, Docker shell, and subprocess package-entrypoint proof; `src/autoclaw` extends its package path deliberately so the deferred legacy `apps/api/autoclaw/openclaw/**` subtree remains the sole substantive OpenClaw owner until `P6-WP4`
- `P6-WP2`: the public `autoclaw` package now exposes its package root, CLI package shell, API wrapper shell, and main app shell from `apps/api/src/autoclaw/**`; the copied `apps/api/src/autoclaw/openclaw/**` tree was removed so deeper non-transport OpenClaw internals remain deferred cleanly

## Artifacts changed

- `docs-internal/execution/v1/maps/file-priority-map.md`
- `docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md`
- `docs-internal/execution/v1/plans/phase-6-source-audit-and-rename-map.md`
- `docs-internal/execution/v1/plans/phase-6-full-source-owner-convergence-and-package-migration.md`
- `docs-internal/execution/v1/plans/phase-6-wp0-wp2-package-shell-and-transport-cutover.md`
- `apps/api/src/autoclaw/**`
- repo-native import shells under `Makefile`, `apps/api/Dockerfile`, `scripts/testing/run_api_pytest_groups.sh`, and `apps/api/tests/run_integration_groups.sh`
- focused proof surfaces under `apps/api/tests/unit/**`

## Remaining exact blockers

- none
