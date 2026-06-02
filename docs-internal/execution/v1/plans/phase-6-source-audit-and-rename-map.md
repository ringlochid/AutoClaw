# Phase 6 Source Audit And Rename Map Plan

Status: Reference

selected phase: Phase 6
current phase page: docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md
selected work packages: P6-WP0
summary-only: no
delegated slices: none

## Slice identity

- owner: Codex
- date: 2026-06-02
- work package or slice: `P6-WP0` authoritative source audit, rename map, and audit expansion

## Subagents decision

- no subagents

## Goal

- freeze the Phase 6 source-owner, naming, wrapper, and proof map before any broad source mutation begins

## Phase-local contract

- current phase page: `docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md`
- implementation file lock map: `docs-internal/execution/v1/maps/file-priority-map.md`
- required reads completed: `AGENTS.md`, `STYLE.md`, `docs-internal/execution/v1/README.md`, `docs-internal/execution/v1/phases/overview.md`, `docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md`, `docs-internal/execution/v1/maps/file-priority-map.md`, `docs-internal/design/v1/architecture/design-overview.md`, `docs-internal/design/v1/architecture/glossary-and-boundaries.md`, `docs-internal/design/v1/interfaces/cli-api-and-package-shape.md`, `docs-internal/design/v1/architecture/runtime-lifecycle-overview.md`, `docs-internal/design/v1/architecture/README.md`, `docs-internal/design/v1/interfaces/README.md`, `docs-internal/design/v1/architecture/provider-worker-and-operator-boundary.md`, `docs-internal/design/v1/interfaces/mcp-plugin-and-cli-boundary.md`, `docs-internal/design/v1/architecture/runtime-records-and-lifecycle.md`, `docs-internal/current/v1/architecture/current-architecture.md`, `docs-internal/current/v1/interfaces/api-surface-and-route-map.md`, `docs-internal/current/v1/interfaces/cli-surface-and-config-precedence.md`, `docs-internal/current/v1/architecture/openclaw-and-bridge-plugin.md`, `.agents/standards/structure/repo-layout.md`, `.agents/standards/structure/source-layout.md`, `.agents/standards/structure/integration-boundaries.md`, `.agents/standards/code/naming.md`, `.agents/standards/code/readability-refactor.md`, and `.agents/standards/structure/test-structure.md`

## Locked surfaces

- owned surfaces: `scripts/docs/style_audit/**`, `apps/api/tests/unit/test_style_audit.py`, and the Phase 6 packet under `docs-internal/execution/v1/plans/`, `docs-internal/execution/v1/evidence/`, and `docs-internal/execution/v1/reviews/`
- allowed collateral surfaces used in this package: `scripts/docs/docs_freeze/record_rules.py`, `apps/api/tests/unit/test_docs_freeze.py`, and the narrow Phase 6 execution docs that now name the touched-scope `--scan-root` gate explicitly
- do not edit or defer surfaces: production source moves, production renames, broad test-tree relayout, grouped-runner cleanup, and any end-to-end or DB-lane widening beyond the focused proof named below

## Baseline findings table

### Audit summary

| Baseline finding | Count |
| --- | ---: |
| sibling-prefix layout families | 1 |
| import-only wrapper modules | 2 |
| phase-numbered test directories | 8 |
| cross-lane test imports | 8 |
| cross-module private-helper imports | 2 |
| cross-module private access findings | 2 |
| zero-reference private module helpers | 1 |
| import-direction findings | 36 |
| duplicate module-name ownership findings | 1 |
| module-shape findings | 425 |
| public naming findings | 58 |
| file-size threshold violations | 6 |
| function-size threshold violations | 15 |

### Import counts

These counts use `rg -n '^(from|import) app(\\.|\\b)' ...` and the matching `autoclaw` command on Python files.

| Scope | `app` import lines | `autoclaw` import lines |
| --- | ---: | ---: |
| `apps/api` + `scripts/docs` | 1310 | 54 |
| `apps/api/app/**` | 888 | 2 |
| `apps/api/autoclaw/**` | 38 | 27 |

### Major source hotspots

| Path family | Python files | Total lines |
| --- | ---: | ---: |
| `apps/api/app/runtime/**` | 146 | 22,385 |
| `apps/api/app/cli_commands/**` | 10 | 3,000 |
| `apps/api/autoclaw/**` | 22 | 2,125 |

### Largest files

| Path | Lines |
| --- | ---: |
| `apps/api/tests/integration/phase5a/test_root_cli_phase5a.py` | 1,749 |
| `apps/api/tests/unit/test_style_audit.py` | 1137 |
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

## Canonical package authority table

| Current source family | Current owner | Target owner | Temporary shim status | Owning future wave |
| --- | --- | --- | --- | --- |
| `apps/api/app/**` | legacy backend package and dominant runtime owner | `apps/api/src/autoclaw/**` domain-first canonical package | no new legacy-first growth; only explicit bridge surfaces may survive | Waves B, C, D, and E |
| `apps/api/autoclaw/**` | current public wrapper, entrypoint, and OpenClaw adapter lane | `apps/api/src/autoclaw/cli/**` and `apps/api/src/autoclaw/openclaw/**` | approved re-export shims only | Waves A, D, and E |
| `apps/api/app/api/routes/**` | current transport route package | `apps/api/src/autoclaw/api/routes/**` | temporary directory-wide wrapper allowance only | Waves C and E |
| `apps/api/src/autoclaw/**` | not yet created in repo truth | canonical backend package root | no wrapper status; this becomes the authority | Wave E |

## Wrapper disposition table

| Path | Current shape | Phase 6 status | Owning future wave |
| --- | --- | --- | --- |
| `apps/api/app/cli.py` | pure import-only wrapper to `app.cli.main` | active finding; do not allowlist | Wave A |
| `apps/api/app/terminal/output.py` | pure import-only wrapper to `app.terminal.theme` | active finding; do not allowlist | Wave B |
| `apps/api/app/runtime/contracts.py` | import-only export surface over `app.runtime.contract_models/**` | approved temporary shim | Wave D |
| `apps/api/app/runtime/ids.py` | substantive shared utility module, not a pure wrapper | keep as active shared source until naming cleanup | Wave D |
| `apps/api/autoclaw/cli.py` | import-only wrapper to `app.cli` plus CLI `__main__` surface | approved temporary shim | Wave E |
| `apps/api/autoclaw/main.py` | import-only wrapper to `app.main` | approved temporary shim | Wave E |
| `apps/api/autoclaw/openclaw/node_server.py` | import-only wrapper to `autoclaw.openclaw.node_mcp` exports | approved temporary shim | Wave E |
| `apps/api/autoclaw/openclaw/operator_server.py` | import-only wrapper to `autoclaw.openclaw.operator_mcp` exports | approved temporary shim | Wave E |

## Source-owner map by future Wave A-E

| Wave | Current path families | Target owner packages | Future `src/autoclaw` landing family |
| --- | --- | --- | --- |
| Wave A | `apps/api/app/*.py`, `apps/api/autoclaw/*.py`, `pyproject.toml` | package metadata and entrypoint surfaces | `apps/api/src/autoclaw/**` entrypoint and CLI family |
| Wave B | `apps/api/app/cli/**`, `apps/api/app/cli_commands/**`, `apps/api/app/terminal/**` | CLI parsing, command orchestration, and terminal rendering | `apps/api/src/autoclaw/cli/**` |
| Wave C | `apps/api/app/runtime/**`, `apps/api/app/db/**`, adjacent `apps/api/app/api/**` where route thinness depends on the move | runtime, persistence, and thin API transports | `apps/api/src/autoclaw/runtime/**`, `apps/api/src/autoclaw/db/**`, `apps/api/src/autoclaw/api/**` |
| Wave D | `apps/api/app/schemas/**`, `apps/api/app/registry/**`, `apps/api/autoclaw/openclaw/**` | contracts, schemas, registry, and OpenClaw adapter surfaces | `apps/api/src/autoclaw/schemas/**`, `apps/api/src/autoclaw/registry/**`, `apps/api/src/autoclaw/openclaw/**` |
| Wave E | `apps/api/src/autoclaw/**`, residual shims, final package metadata and exports | final canonical package move and shim removal | `apps/api/src/autoclaw/**` only |

## Canonical naming glossary

| Canonical term | Banned or legacy synonyms | Known current offenders | Future wave owner |
| --- | --- | --- | --- |
| `autoclaw` as the canonical backend package | long-lived `app` as a parallel first-class backend owner | 38 `app.*` import lines still originate from `apps/api/autoclaw/**`; 888 `app.*` lines remain inside `apps/api/app/**` | Wave E |
| `tool` for MCP/runtime callable surfaces | `plugin`, `bundle` as interchangeable runtime nouns | `apps/api/autoclaw/openclaw/node_mcp/**` and `operator_mcp/**` still sit under mixed `tool` / `plugin` wording across docs and helper names | Wave D |
| `definition import` / `task compose start` public nouns | `bootstrap` and older upload-centric public wording | `apps/api/app/cli_commands/bootstrap.py` and adjacent docs still carry `bootstrap` in steady-state path names | Wave B |
| effect-bearing verbs such as `build_*`, `read_*`, `persist_*`, `reconcile_*` | weak verbs `handle`, `process`, `run`, `do`, `apply`, `check` | 12 current public-naming findings, including `run_read_operation`, `run_runtime_write_operation`, and `apply_server_config_overrides` | Wave B and Wave D |
| fact-shaped booleans such as `is_*`, `has_*`, `should_*`, `can_*` | bag- or status-shaped public booleans | no current module-level offenders in the Phase 6 scan scope; keep the rule active before Wave D renames | Wave D |

## Docs and test reference coverage table

These counts were captured before creating the new `P6-WP0` packet, so they describe the pre-packet baseline that later waves must update together.

| Surface | Baseline file count | Representative pages or files | Alignment note |
| --- | ---: | --- | --- |
| `docs-internal/design/v1/**` | 22 | `docs-internal/design/v1/how-to/install-and-onboard.md`, `docs-internal/design/v1/workflows/examples/normal.md`, `docs-internal/design/v1/workflows/workflow-definition-schema.md` | later source-owner renames must update design teaching and examples together |
| `docs-internal/current/v1/**` | 29 | `docs-internal/current/v1/architecture/openclaw-and-bridge-plugin.md`, `docs-internal/current/v1/architecture/system-baseline.md`, `docs-internal/current/v1/interfaces/cli-surface-and-config-precedence.md` | current-contrast pages still name legacy package and path families |
| `docs-internal/execution/v1/**` | 40 | `docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md`, `docs-internal/execution/v1/maps/file-priority-map.md`, earlier phase evidence and review records | execution routing and historical evidence will need coordinated path-term refreshes as each wave lands |
| `apps/api/tests/**` | 131 | `apps/api/tests/conftest.py`, `apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`, `apps/api/tests/e2e/phase4/maximal_lane/flow.py` | test selectors and helper imports still reflect legacy package and phase-tree naming |

## Focused proof selector matrix for P6-WP1 through P6-WP5

| Work package | Current focused selectors |
| --- | --- |
| `P6-WP1` | `apps/api/tests/unit/test_package_entrypoints.py`<br>`apps/api/tests/unit/cli/test_main.py`<br>`apps/api/tests/unit/test_cli.py` |
| `P6-WP2` | `apps/api/tests/unit/cli/test_main.py`<br>`apps/api/tests/unit/test_cli.py`<br>`apps/api/tests/integration/phase5a/test_root_cli_phase5a.py` |
| `P6-WP3` | `apps/api/tests/unit/runtime/openclaw/test_host_setup.py`<br>`apps/api/tests/unit/runtime/openclaw/test_mcp_operation_failures.py`<br>`apps/api/tests/unit/runtime_prompt_rendering`<br>`apps/api/tests/integration/phase3/control`<br>`apps/api/tests/integration/phase3/db`<br>`apps/api/tests/integration/phase4a/runtime_dispatch_gateway`<br>`apps/api/tests/integration/phase4b/watchdog`<br>`apps/api/tests/integration/phase4b/mcp`<br>`apps/api/tests/integration/runtime_schema_contract` |
| `P6-WP4` | `apps/api/tests/unit/definition_schemas`<br>`apps/api/tests/unit/test_phase5a_schema_contract.py`<br>`apps/api/tests/integration/definition_registry`<br>`apps/api/tests/integration/runtime_schema_contract`<br>`apps/api/tests/integration/phase5a/mcp/test_operator_server_phase5a.py` |
| `P6-WP5` | `apps/api/tests/unit/test_package_entrypoints.py`<br>`apps/api/tests/unit/cli/test_main.py`<br>`apps/api/tests/unit/test_cli.py`<br>`apps/api/tests/integration/phase5a/test_root_cli_phase5a.py` |

## Approved Phase 6 exceptions list

| Surface | Exception type | Why it survives past `WP0` | Exact removal wave |
| --- | --- | --- | --- |
| `apps/api/app/runtime/contracts.py` | approved import-only wrapper | keeps the current contract export surface stable while contract owners move | Wave D |
| `apps/api/autoclaw/cli.py` | approved import-only wrapper | preserves the shipped console entrypoint while package authority freezes | Wave E |
| `apps/api/autoclaw/main.py` | approved import-only wrapper | preserves the shipped ASGI/package import surface while package authority converges | Wave E |
| `apps/api/autoclaw/openclaw/node_server.py` | approved import-only wrapper | preserves the current OpenClaw node-MCP server export surface during adapter relayout | Wave E |
| `apps/api/autoclaw/openclaw/operator_server.py` | approved import-only wrapper | preserves the current OpenClaw operator-MCP server export surface during adapter relayout | Wave E |
| `apps/api/app/api/routes/**` | approved wrapper directory | keeps the existing route module family flat while runtime/API owner moves are sequenced | Wave E |
| `apps/api/app/main.py` | approved mixed-owner import-direction exception | current `app` entrypoint still bridges into the future canonical package direction | Wave A |

## Validation checkpoints

- land the audit-tool unit coverage before changing the scanners
- keep the Phase 6 import-first gate explicit through `--scan-root <path>` plus `--fail-on-findings`
- record the baseline evidence before mutating the report order or execution packet
- close `P6-WP0` only when the new audits expose stale-shape backlog without flagging unresolved `WP0` tooling debt

## Required tests and validators

- `./.venv/bin/python -m pytest apps/api/tests/unit/test_style_audit.py`
- `./.venv/bin/python -m pytest apps/api/tests/unit/test_docs_freeze.py`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --scan-root scripts/docs/style_audit --scan-root apps/api/tests/unit/test_style_audit.py --scan-root apps/api/tests/unit/test_docs_freeze.py --gate import-interface --fail-on-findings`
- `./.venv/bin/ruff check scripts/docs/style_audit apps/api/tests/unit/test_style_audit.py apps/api/tests/unit/test_docs_freeze.py`
- `./.venv/bin/mypy scripts/docs/style_audit scripts/docs/docs_freeze`
- `make pyright-api`
- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- `./.venv/bin/python -m scripts.docs.style_audit.cli`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`

## Exit evidence

- evidence artifact: `../evidence/phase-6-source-audit-and-rename-map.md`
- review artifact: `../reviews/phase-6-source-audit-and-rename-map.md`

## Cross-links

- evidence artifact: `../evidence/phase-6-source-audit-and-rename-map.md`
- review artifact: `../reviews/phase-6-source-audit-and-rename-map.md`
