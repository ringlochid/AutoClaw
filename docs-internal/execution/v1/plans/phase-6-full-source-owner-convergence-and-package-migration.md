# Phase 6 Full Source Owner Convergence And Package Migration Plan

Status: Reference

selected phase: Phase 6
current phase page: docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md
selected work packages: P6-WP1, P6-WP2, P6-WP3, P6-WP4, P6-WP5
summary-only: no
delegated slices: none

## Slice identity

- owner: Codex
- date: 2026-06-03
- work package bundle: `P6-WP1` through `P6-WP5`

## Subagents decision

- no edit subagents
- any later review wave must use a fresh `review-only` slice with bounded owner-family scope and no file edits

## Goal

- complete Phase 6 as a full source-only standards refactor across shipped backend source, not as a hotspot or partial-family cleanup bundle

## Planning reset

- this plan replaces the earlier partial `WP1` through `WP3` hotspot packet as the authoritative follow-on plan for Phase 6
- the prior hotspot packet is removed from the live execution-doc set because it was not sufficient closure authority for a source-only full-family refactor phase
- `P6-WP0` remains the authoritative baseline audit packet; this plan picks up from that baseline and governs the remaining source-owner work

## Phase-local contract

- current phase page: `docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md`
- implementation file lock map: `docs-internal/execution/v1/maps/file-priority-map.md`
- required reads completed: `AGENTS.md`, `STYLE.md`, `docs-internal/execution/v1/README.md`, `docs-internal/execution/v1/phases/overview.md`, `docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md`, `docs-internal/execution/v1/maps/file-priority-map.md`, `docs-internal/design/v1/architecture/design-overview.md`, `docs-internal/design/v1/architecture/glossary-and-boundaries.md`, `docs-internal/design/v1/interfaces/cli-api-and-package-shape.md`, `docs-internal/design/v1/architecture/runtime-lifecycle-overview.md`, `docs-internal/design/v1/architecture/README.md`, `docs-internal/design/v1/interfaces/README.md`, `docs-internal/design/v1/architecture/provider-worker-and-operator-boundary.md`, `docs-internal/design/v1/interfaces/mcp-plugin-and-cli-boundary.md`, `docs-internal/design/v1/architecture/runtime-records-and-lifecycle.md`, `docs-internal/current/v1/architecture/current-architecture.md`, `docs-internal/current/v1/interfaces/api-surface-and-route-map.md`, `docs-internal/current/v1/interfaces/cli-surface-and-config-precedence.md`, `docs-internal/current/v1/architecture/openclaw-and-bridge-plugin.md`, `.agents/standards/structure/repo-layout.md`, `.agents/standards/structure/source-layout.md`, `.agents/standards/structure/integration-boundaries.md`, `.agents/standards/code/naming.md`, and `.agents/standards/code/readability-refactor.md`

## Locked surfaces

- owned surfaces:
  - shipped backend source under `apps/api/app/**`
  - shipped backend wrapper and public package surfaces under `apps/api/autoclaw/**`
  - the target source root `apps/api/src/autoclaw/**` as it is introduced by the phase
  - package and entrypoint surfaces such as `pyproject.toml`, `apps/api/app/*.py`, and `apps/api/autoclaw/*.py`
  - repo-native audit tooling under `scripts/docs/style_audit/**`
  - the audit-tool proof surface `apps/api/tests/unit/test_style_audit.py`
  - design, current, and execution docs needed to keep source-owner routing, gate order, and package-migration truth exact
- allowed collateral surfaces used in this bundle:
  - targeted proof tests under `apps/api/tests/**` when source movement, package migration, or function extraction needs adjacent proof repair without taking ownership of the test tree
  - `Makefile` and narrow `scripts/**` surfaces when package or import-path changes require command-truth alignment without reopening broader release ownership
  - `scripts/docs/docs_freeze/**` and `docs/reference/**` when package-owner or path-owner changes require path-validation truth and public reference owner paths to stay aligned
- do not edit or defer surfaces:
  - broad test-tree ownership convergence, grouped-runner relayout, proof-lane cleanup, and helper or fixture convergence, which remain Phase 7-owned
  - intentional public-behavior, runtime-contract, or API-contract changes that are not required to preserve behavior during the structural refactor

## Baseline summary

- latest source-only audit scope: `apps/api/app/**` plus `apps/api/autoclaw/**`
- source-only source inventory:
  - `269` Python files under `apps/api/app/**`
  - `22` Python files under `apps/api/autoclaw/**`
  - `291` shipped backend source files in total
- latest source-only audit findings:
  - `36` import-direction findings
  - `321` module-shape findings
  - `21` public-naming findings
  - `1` function-size threshold violation
  - `0` file-size threshold violations
- representative backlog that this plan must clear:
  - `apps/api/autoclaw/**` still imports `app.*` in bridge and MCP families
  - top-level source families still split durable ownership across `api/**`, `cli/**`, `cli_commands/**`, `terminal/**`, and mixed root modules
  - runtime and OpenClaw families still carry broad module-order debt and mechanism-first path sprawl
  - public weak-verb helpers still exist in `apps/api/autoclaw/openclaw/common.py` and `apps/api/autoclaw/openclaw/node_mcp/runtime_tools.py`
  - the last remaining source-only function-size violation is `apps/api/autoclaw/openclaw/node_mcp/runtime_tools.py:register_node_runtime_tools`

## Execution rules

- this bundle is source-only; tests are proof consumers and narrow repair collateral only
- each work package closes by completed owner-family scope, not by touched hotspot scope
- a completed owner-family wave must pass both:
  - import and interface gate
  - full touched-family `style_audit --scan-root <path> --fail-on-findings`
- no completed owner family may retain unresolved module-shape, public-naming, import-direction, or wrapper-budget debt without an exact Phase 6 review exception
- no test-tree relayout, lane migration, helper convergence, or grouped-runner cleanup belongs in this bundle
- the `apps/api/src/autoclaw/**` move is mandatory Phase 6 closeout work, not optional follow-on cleanup

## Owner-family wave map

- `P6-WP1`: package authority and bridge surfaces
  - `apps/api/app/*.py`
  - `apps/api/autoclaw/*.py`
  - `pyproject.toml`
- `P6-WP2`: transport and public-surface owners
  - `apps/api/app/api/**`
  - `apps/api/app/cli/**`
  - `apps/api/app/cli_commands/**`
  - `apps/api/app/terminal/**`
  - public wrapper and MCP-facing source under `apps/api/autoclaw/**`
- `P6-WP3`: platform, compiler, persistence, contracts, and shared owners
  - `apps/api/app/config.py`
  - `apps/api/app/paths.py`
  - `apps/api/app/file_entrypoints.py`
  - `apps/api/app/core/**`
  - `apps/api/app/service_managers/**`
  - `apps/api/app/services/**`
  - `apps/api/app/resources/**`
  - `apps/api/app/compiler/**`
  - `apps/api/app/db/**`
  - `apps/api/app/registry/**`
  - `apps/api/app/schemas/**`
- `P6-WP4`: runtime and OpenClaw internals
  - `apps/api/app/runtime/**`
  - non-shim `apps/api/autoclaw/openclaw/**`
  - adjacent `apps/api/app/api/**` only where transport thinness or ownership depends on the move
- `P6-WP5`: final naming convergence and canonical package move
  - `apps/api/src/autoclaw/**`
  - residual shims
  - final package metadata and entrypoint cleanup

## Ordered work packages

### `P6-WP1`

- objective: freeze canonical package authority, remove all non-approved bridge wrappers, and stop new `app`-owner growth before deeper owner moves begin
- owned surfaces: package metadata, entrypoints, import wrappers, package-routing docs
- dependencies: `P6-WP0`
- test-first requirement: package-entrypoint and import-path smoke coverage
- documentation update requirement: package authority and shim status stay explicit
- closeout evidence: one canonical package direction is explicit and the remaining bridge surfaces are exact and deliberate

### `P6-WP2`

- objective: converge transport and public-surface owners so API, CLI, and public wrapper families each live under one obvious owner path and carry their readability or naming cleanup with the move
- owned surfaces: `apps/api/app/api/**`, `apps/api/app/cli/**`, `apps/api/app/cli_commands/**`, `apps/api/app/terminal/**`, public wrapper and MCP-facing source under `apps/api/autoclaw/**`, and matching source-owner docs
- dependencies: `P6-WP1`
- test-first requirement: focused proof selectors for each moved transport or public-surface family
- documentation update requirement: file and directory ownership stays obvious in touched docs
- closeout evidence: completed transport and public-surface families pass their full touched-family source-quality gates and no longer rely on parallel flat owner trees

### `P6-WP3`

- objective: converge platform, compiler, persistence, registry, schema, and shared-owner families so those non-runtime source lanes are structurally clean before runtime closeout begins
- owned surfaces: `apps/api/app/config.py`, `apps/api/app/paths.py`, `apps/api/app/file_entrypoints.py`, `apps/api/app/core/**`, `apps/api/app/service_managers/**`, `apps/api/app/services/**`, `apps/api/app/resources/**`, `apps/api/app/compiler/**`, `apps/api/app/db/**`, `apps/api/app/registry/**`, `apps/api/app/schemas/**`, and matching source-owner docs
- dependencies: `P6-WP1`
- test-first requirement: focused proof selectors for each completed platform, compiler, persistence, or contract family
- documentation update requirement: touched docs reflect the landed owner paths and dominant responsibilities
- closeout evidence: completed non-runtime source families pass their full touched-family source-quality gates and no longer carry avoidable shared-owner ambiguity

### `P6-WP4`

- objective: converge the full runtime and OpenClaw source owners until those families meet the same structure, readability, and naming bar as the earlier waves
- owned surfaces: `apps/api/app/runtime/**`, non-shim `apps/api/autoclaw/openclaw/**`, and adjacent `apps/api/app/api/**` only where transport thinness or ownership depends on the move
- dependencies: `P6-WP2`, `P6-WP3`
- test-first requirement: focused proof selectors around each completed runtime or OpenClaw owner family
- documentation update requirement: touched docs reflect the landed owner paths and dominant responsibilities
- closeout evidence: runtime and OpenClaw source-owner families pass their full touched-family source-quality gates and no longer rely on hotspot-only cleanup as closure authority

### `P6-WP5`

- objective: complete naming convergence, finish the `apps/api/src/autoclaw/**` move, and reduce remaining shims to the narrow minimum so Phase 6 closes on one canonical backend package
- owned surfaces: `apps/api/src/autoclaw/**`, remaining shims, package exports, entrypoints, package metadata, and final Phase 6 docs
- dependencies: `P6-WP1`, `P6-WP2`, `P6-WP3`, `P6-WP4`
- test-first requirement: focused package-entrypoint and import-path smoke coverage for the final move plus focused proof for renamed public or shared surfaces
- documentation update requirement: shim status and remaining migration exceptions are written explicitly
- closeout evidence: the canonical backend package move is complete, source-owner families are naming-clean, and only deliberate temporary shims remain

## Focused proof selector defaults

- `P6-WP1`
  - `apps/api/tests/unit/test_package_entrypoints.py`
  - `apps/api/tests/unit/cli/test_main.py`
  - `apps/api/tests/unit/test_cli.py`
- `P6-WP2`
  - `apps/api/tests/unit/cli/test_main.py`
  - `apps/api/tests/unit/test_cli.py`
  - `apps/api/tests/integration/phase5a/test_root_cli_phase5a.py`
  - `apps/api/tests/integration/phase3/routes`
  - `apps/api/tests/integration/test_readyz_real_db.py`
  - `apps/api/tests/integration/test_startup_schema_guard.py`
- `P6-WP3`
  - `apps/api/tests/unit/definition_schemas`
  - `apps/api/tests/unit/workflow_compiler`
  - `apps/api/tests/integration/definition_registry`
  - `apps/api/tests/integration/phase3/db`
  - `apps/api/tests/integration/runtime_schema_contract`
- `P6-WP4`
  - `apps/api/tests/unit/runtime/openclaw/test_host_setup.py`
  - `apps/api/tests/unit/runtime/openclaw/test_mcp_operation_failures.py`
  - `apps/api/tests/unit/runtime_prompt_rendering`
  - `apps/api/tests/integration/phase3/control`
  - `apps/api/tests/integration/phase3/db`
  - `apps/api/tests/integration/phase3/routes`
  - `apps/api/tests/integration/phase4a/runtime_dispatch_gateway`
  - `apps/api/tests/integration/phase4b/watchdog`
  - `apps/api/tests/integration/phase4b/mcp`
  - `apps/api/tests/integration/runtime_schema_contract`
- `P6-WP5`
  - `apps/api/tests/unit/test_package_entrypoints.py`
  - `apps/api/tests/unit/cli/test_main.py`
  - `apps/api/tests/unit/test_cli.py`
  - `apps/api/tests/integration/definition_registry`
  - `apps/api/tests/integration/phase5a/test_root_cli_phase5a.py`
  - `apps/api/tests/integration/phase5a/mcp/test_operator_server_phase5a.py`
  - `apps/api/tests/integration/runtime_schema_contract`

## Required tests and validators

- gate order for every owner-family wave:
  1. import and interface gate
  2. full touched-family `style_audit --scan-root <path> --fail-on-findings`
  3. focused pytest selection for the affected family
  4. only the narrowest broader proof forced by the touched surface
- end-of-phase closeout only once:
  - `ruff format`
  - `ruff check`
  - `mypy`
  - `make pyright-api`
  - `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
  - `ruff check scripts/docs` and `mypy scripts/docs` when `scripts/docs/style_audit/**` changed
  - `./.venv/bin/python -m scripts.docs.docs_freeze.cli` when `docs-internal/execution/v1/**`, `docs-internal/current/v1/**`, `docs/reference/**`, or `scripts/docs/docs_freeze/**` changed as Phase 6 collateral
  - the full applicable backend test matrix for touched source surfaces
  - all viable e2e lanes required by the touched shipped surfaces

## Exit evidence

- `P6-WP0` remains the authoritative baseline audit packet
- each later owner-family execution packet must record its exact source-owner scope and proof lanes
- Phase 6 closes only after the canonical backend package move is complete and the full source-only quality gates pass
