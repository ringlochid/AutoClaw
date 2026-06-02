# Phase 6 Source Audit And Rename Map Evidence

Status: Reference

selected phase: Phase 6
current phase page: docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md
selected work packages: P6-WP0
summary-only: no
delegated slices: none

## Slice identity

- work package or slice: `P6-WP0`
- slice type: edit
- date: 2026-06-02

## Plan and review links

- approved plan: `../plans/phase-6-source-audit-and-rename-map.md`
- mandatory review: `../reviews/phase-6-source-audit-and-rename-map.md`
- review artifact: `../reviews/phase-6-source-audit-and-rename-map.md`

## Commands run

- `./.venv/bin/python -m pytest apps/api/tests/unit/test_style_audit.py apps/api/tests/unit/test_docs_freeze.py -q` -> `41 passed`
- `./.venv/bin/ruff check scripts/docs apps/api/tests/unit/test_style_audit.py apps/api/tests/unit/test_docs_freeze.py` -> passed
- `./.venv/bin/mypy scripts/docs` -> passed
- `./.venv/bin/python -m scripts.docs.docs_freeze.cli` -> passed
- `./.venv/bin/python -m scripts.docs.style_audit.cli` -> report mode passed
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings` -> exited `1` as expected because `P6-WP1` through `P6-WP5` backlog remains

## Gate and validator summary

- docs or prompt validators: `scripts.docs.docs_freeze.cli` passed after adding `Phase 5.5`, `Phase 6`, and `Phase 7` to the execution-record phase registry
- language gates: focused `ruff check` and `mypy` passed on the touched `scripts/docs/**` and focused test surfaces
- reset or package checks: not applicable for `P6-WP0`

## Test lanes

- unit: focused `test_style_audit.py` plus `test_docs_freeze.py` because the phase packet required docs-freeze collateral to validate new Phase 6 execution records
- integration: none
- e2e: none
- SQLite: none
- Postgres or Docker: none

## Baseline repo-truth capture

### Style audit summary

| Finding family | Count |
| --- | ---: |
| scanned python files | 494 |
| import-direction findings | 36 |
| duplicate module-name ownership findings | 1 |
| import-only wrapper modules | 2 |
| sibling-prefix layout families | 1 |
| phase-numbered test directories | 8 |
| cross-lane test imports | 8 |
| module-shape findings | 425 |
| cross-module private-helper imports | 2 |
| cross-module private access findings | 2 |
| zero-reference private module helpers | 1 |
| public naming findings | 58 |
| file-size threshold violations | 6 |
| function-size threshold violations | 15 |

### Import count commands

| Command | Result |
| --- | ---: |
| `rg -g '*.py' -n '^(from|import) app(\\.|\\b)' apps/api scripts/docs | wc -l` | 1310 |
| `rg -g '*.py' -n '^(from|import) autoclaw(\\.|\\b)' apps/api scripts/docs | wc -l` | 54 |
| `rg -g '*.py' -n '^(from|import) app(\\.|\\b)' apps/api/app | wc -l` | 888 |
| `rg -g '*.py' -n '^(from|import) autoclaw(\\.|\\b)' apps/api/app | wc -l` | 2 |
| `rg -g '*.py' -n '^(from|import) app(\\.|\\b)' apps/api/autoclaw | wc -l` | 38 |
| `rg -g '*.py' -n '^(from|import) autoclaw(\\.|\\b)' apps/api/autoclaw | wc -l` | 27 |

### Major directory totals

| Command family | Result |
| --- | --- |
| `find apps/api/app/runtime -name '*.py' | wc -l` | `146` |
| `find apps/api/app/runtime -name '*.py' -print0 | xargs -0 wc -l | tail -n 1` | `22385 total` |
| `find apps/api/app/cli_commands -name '*.py' | wc -l` | `10` |
| `find apps/api/app/cli_commands -name '*.py' -print0 | xargs -0 wc -l | tail -n 1` | `3000 total` |
| `find apps/api/autoclaw -name '*.py' | wc -l` | `22` |
| `find apps/api/autoclaw -name '*.py' -print0 | xargs -0 wc -l | tail -n 1` | `2125 total` |

### Wrapper, drift, and private-helper backlog

| Surface | Current backlog |
| --- | --- |
| import-only wrapper findings | `apps/api/app/cli.py`, `apps/api/app/terminal/output.py` |
| approved wrapper modules | `apps/api/app/runtime/contracts.py`, `apps/api/app/runtime/ids.py`, `apps/api/autoclaw/cli.py`, `apps/api/autoclaw/main.py`, `apps/api/autoclaw/openclaw/node_server.py`, `apps/api/autoclaw/openclaw/operator_server.py` |
| approved wrapper directories | `apps/api/app/api/routes/**` |
| phase-numbered test directories | `apps/api/tests/e2e/phase2`, `phase3`, `phase4`; `apps/api/tests/integration/phase2`, `phase3`, `phase4a`, `phase4b`, `phase5a` |
| cross-lane test imports | 8 findings; all current consumers are `e2e -> integration` except `apps/api/tests/unit/test_cli.py -> tests.integration.phase5a.test_root_cli_phase5a` |
| duplicate module-name ownership findings | `app.cli` resolves to both `apps/api/app/cli.py` and `apps/api/app/cli/__init__.py` |
| cross-module private-helper imports | `apps/api/app/runtime/openclaw/connection.py:_connect_and_handshake` into `apps/api/tests/unit/test_cli.py`; `apps/api/tests/integration/phase5a/test_root_cli_phase5a.py:_write_fake_openclaw_cli` into `apps/api/tests/unit/test_cli.py` |
| zero-reference private helper | `apps/api/app/cli_commands/openclaw_wrapper.py:_preferred_agent_id` |

### Largest files

| Path | Lines |
| --- | ---: |
| `apps/api/tests/integration/phase5a/test_root_cli_phase5a.py` | 1,749 |
| `apps/api/tests/unit/test_style_audit.py` | 1026 |
| `apps/api/app/cli_commands/openclaw_wrapper.py` | 933 |
| `apps/api/tests/unit/test_cli.py` | 810 |
| `apps/api/app/cli_commands/operator.py` | 742 |
| `apps/api/app/cli_commands/bootstrap.py` | 626 |

### Largest functions

| Path | Function | Non-comment lines |
| --- | --- | ---: |
| `apps/api/app/cli_commands/operator.py` | `cmd_onboard` | 203 |
| `apps/api/autoclaw/openclaw/node_mcp/runtime_tools.py` | `register_node_runtime_tools` | 162 |
| `apps/api/app/cli_commands/operator.py` | `cmd_doctor` | 132 |
| `apps/api/tests/integration/phase5a/test_root_cli_phase5a.py` | `test_phase5a_root_cli_openclaw_setup_patches_selected_profiles_tool_slice_only` | 109 |
| `apps/api/tests/integration/phase5a/test_root_cli_phase5a.py` | `test_phase5a_root_cli_onboard_writes_wrapper_state` | 108 |
| `apps/api/app/runtime/openclaw/discovery.py` | `discover_openclaw_host_state` | 98 |
| `apps/api/app/cli_commands/operator.py` | `cmd_configure` | 97 |
| `apps/api/tests/integration/phase5a/test_root_cli_phase5a.py` | `_write_fake_openclaw_cli` | 93 |
| `apps/api/app/runtime/effects/task_reconcile.py` | `reconcile_current_dispatch` | 87 |
| `apps/api/tests/integration/phase5a/test_root_cli_phase5a.py` | `test_phase5a_root_cli_onboard_interactive_defaults_to_bootstrap_dedicated_agents` | 87 |
| `apps/api/tests/unit/test_cli.py` | `test_service_install_and_status_use_systemd_user_surface` | 86 |
| `apps/api/app/cli_commands/openclaw_wrapper.py` | `_resolve_openclaw_agent_selection` | 85 |
| `apps/api/tests/integration/phase5a/test_root_cli_phase5a.py` | `test_phase5a_root_cli_onboard_interactive_existing_worker_bootstrap_operator` | 85 |
| `apps/api/app/runtime/control/observability.py` | `operator_trace` | 84 |
| `apps/api/app/runtime/control/flow/service.py` | `cancel_runtime_flow` | 82 |

### Docs and test reference coverage capture

These counts were captured before creating the new `P6-WP0` packet so later waves can compare against the pre-packet baseline.

| Command | Result |
| --- | ---: |
| `rg -l 'apps/api/app|apps/api/autoclaw|\\bapp\\.|\\bautoclaw\\.' docs-internal/design/v1 | wc -l` | 22 |
| `rg -l 'apps/api/app|apps/api/autoclaw|\\bapp\\.|\\bautoclaw\\.' docs-internal/current/v1 | wc -l` | 29 |
| `rg -l 'apps/api/app|apps/api/autoclaw|\\bapp\\.|\\bautoclaw\\.' docs-internal/execution/v1 | wc -l` | 40 |
| `rg -l 'apps/api/app|apps/api/autoclaw|\\bapp\\.|\\bautoclaw\\.' apps/api/tests | wc -l` | 131 |

Representative path hits from those raw searches:

- design: `docs-internal/design/v1/how-to/install-and-onboard.md`, `docs-internal/design/v1/workflows/examples/normal.md`, `docs-internal/design/v1/workflows/workflow-definition-schema.md`
- current: `docs-internal/current/v1/architecture/openclaw-and-bridge-plugin.md`, `docs-internal/current/v1/architecture/system-baseline.md`, `docs-internal/current/v1/interfaces/cli-surface-and-config-precedence.md`
- execution: `docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md`, `docs-internal/execution/v1/maps/file-priority-map.md`, earlier phase evidence and review records
- tests: `apps/api/tests/conftest.py`, `apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`, `apps/api/tests/e2e/phase4/maximal_lane/flow.py`

## Artifacts changed

- `scripts/docs/style_audit/cli.py`
- `scripts/docs/style_audit/config.py`
- `scripts/docs/style_audit/import_direction_scan.py`
- `scripts/docs/style_audit/layout_scan.py`
- `scripts/docs/style_audit/models.py`
- `scripts/docs/style_audit/module_loader.py`
- `scripts/docs/style_audit/module_shape_scan.py`
- `scripts/docs/style_audit/private_helpers.py`
- `scripts/docs/style_audit/public_naming_scan.py`
- `scripts/docs/style_audit/report.py`
- `scripts/docs/style_audit/report_sections.py`
- `scripts/docs/style_audit/scan.py`
- `scripts/docs/docs_freeze/record_rules.py`
- `apps/api/tests/unit/test_docs_freeze.py`
- `apps/api/tests/unit/test_style_audit.py`
- `docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md`
- `docs-internal/execution/v1/maps/file-priority-map.md`
- `docs-internal/execution/v1/plans/phase-6-source-audit-and-rename-map.md`
- `docs-internal/execution/v1/evidence/phase-6-source-audit-and-rename-map.md`
- `docs-internal/execution/v1/reviews/phase-6-source-audit-and-rename-map.md`

## Residual blockers

- none; the intentional non-zero `style_audit --fail-on-findings` result is backlog evidence for `P6-WP1` through `P6-WP5`, not a `P6-WP0` blocker
