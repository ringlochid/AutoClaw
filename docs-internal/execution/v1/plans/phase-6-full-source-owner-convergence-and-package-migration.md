# Phase 6 Full Source Owner Convergence And Package Migration Plan

Status: Reference

selected phase: Phase 6
current phase page: docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md
selected work packages: P6-WP3, P6-WP4, P6-WP5
summary-only: no
delegated slices: none

## Slice identity

- owner: Codex
- date: 2026-06-04
- work package bundle: `P6-WP3` through `P6-WP5`

## Goal

- complete reopened Phase 6 against the current `apps/api/src/autoclaw/**` tree, not against removed `app/**` or legacy `autoclaw/**` trees

## Planning reset

- this plan replaces the earlier shell-first Phase 6 execution packet as the authoritative follow-on plan for live code work
- historical `phase-6-source-audit-and-rename-map.*` and `phase-6-wp0-wp2-package-shell-and-transport-cutover.*` artifacts remain summary-only background only
- the next unfinished execution package under this plan is `P6-WP3A`

## Phase-local contract

- current phase page: `docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md`
- implementation file lock map: `docs-internal/execution/v1/maps/file-priority-map.md`
- required reads completed: `AGENTS.md`, `STYLE.md`, `docs-internal/execution/v1/README.md`, `docs-internal/execution/v1/phases/overview.md`, `docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md`, `docs-internal/execution/v1/maps/file-priority-map.md`, `docs-internal/design/v1/architecture/design-overview.md`, `docs-internal/design/v1/architecture/glossary-and-boundaries.md`, `docs-internal/design/v1/interfaces/cli-api-and-package-shape.md`, `docs-internal/design/v1/architecture/runtime-lifecycle-overview.md`, `docs-internal/design/v1/architecture/README.md`, `docs-internal/design/v1/interfaces/README.md`, `docs-internal/design/v1/architecture/provider-worker-and-operator-boundary.md`, `docs-internal/design/v1/interfaces/mcp-plugin-and-cli-boundary.md`, `docs-internal/design/v1/architecture/runtime-records-and-lifecycle.md`, `docs-internal/current/v1/architecture/current-architecture.md`, `docs-internal/current/v1/interfaces/api-surface-and-route-map.md`, `docs-internal/current/v1/interfaces/cli-surface-and-config-precedence.md`, `docs-internal/current/v1/architecture/openclaw-and-bridge-plugin.md`, `.agents/standards/structure/repo-layout.md`, `.agents/standards/structure/source-layout.md`, `.agents/standards/structure/integration-boundaries.md`, `.agents/standards/code/naming.md`, and `.agents/standards/code/readability-refactor.md`

## Locked surfaces

- owned surfaces:
  - shipped backend source under `apps/api/src/autoclaw/**`
  - package and entrypoint surfaces such as `pyproject.toml`, `apps/api/src/autoclaw/main.py`, `apps/api/src/autoclaw/__main__.py`, and the canonical CLI entrypoint
  - repo-native audit tooling under `scripts/docs/style_audit/**`
  - the audit-tool proof surface `apps/api/tests/unit/test_style_audit.py`
  - design, current, and execution docs needed to keep source-owner routing, gate order, and package-migration truth exact
- allowed collateral surfaces used in this bundle:
  - targeted proof tests under `apps/api/tests/**` when source movement, package migration, or function extraction needs adjacent proof repair without taking ownership of the test tree
  - `Makefile`, `apps/api/Dockerfile`, `apps/api/pyrightconfig.json`, and narrow `scripts/**` surfaces when package or import-path changes require command-truth alignment without reopening broader release ownership
  - `docs/**`, `docs-internal/current/**`, and `scripts/docs/docs_freeze/**` when package-owner or path-owner changes require path-validation truth and live public/current reference owner paths to stay aligned
- do not edit or defer surfaces:
  - broad test-tree ownership convergence, grouped-runner relayout, proof-lane cleanup, and helper or fixture convergence, which remain Phase 7-owned
  - intentional public-behavior, runtime-contract, or API-contract changes that are not required to preserve behavior during the structural refactor

## Baseline summary

- latest source-only audit scope: `apps/api/src/autoclaw/**`
- source-only source inventory:
  - `317` scanned source files under `apps/api/src/autoclaw/**`
- latest source-only audit findings:
  - `0` import-direction findings
  - `0` duplicate module-name ownership findings
  - `0` module-shape findings
  - `0` public-naming findings
  - `0` function-size threshold violations
  - `0` file-size threshold violations
- representative backlog that this plan must clear:
  - `apps/api/src/autoclaw/**` still uses the pre-convergence top-level taxonomy `api|cli|compiler|db|registry|schemas|openclaw`
  - the runtime tree still exposes top-level mechanism buckets such as `runtime/control/**`, `runtime/effects/**`, and `runtime/openclaw/**`
  - shipped compatibility assertions and test-only `app.*` lanes still survive under `apps/api/tests/**`
  - `autoclaw.openclaw/**` still exists as a top-level package even though the refined taxonomy requires `interfaces/mcp/**` plus `integrations/openclaw/**`

## Execution rules

- this bundle is source-only; tests are proof consumers and narrow repair collateral only
- each work package closes by completed owner-family scope, not by touched hotspot scope
- a completed owner-family wave must pass this pre-pytest and source-quality gate stack:
  - import and interface gate
  - `make format-api`
  - `make check-api`
  - full touched-family `style_audit --scan-root <path> --fail-on-findings`
- no completed owner family may retain unresolved module-shape, public-naming, import-direction, wrapper-budget, or compatibility debt without an exact Phase 6 review exception
- no test-tree relayout, lane migration, helper convergence, or grouped-runner cleanup belongs in this bundle
- the final `src/autoclaw` root must converge to one coherent taxonomy with grouped `interfaces/**`, `definitions/**`, `runtime/**`, `integrations/**`, `persistence/**`, and `platform/**` owners, plus domain-owned contract lanes under `definitions/contracts/**` and `runtime/contracts/**`
- no shipped compatibility shells, lazy import bridges, or test-only compat lanes may remain at closeout

## Owner-family wave map

- `P6-WP3`: interfaces, definitions, persistence, contracts, platform, and root owners
  - `apps/api/src/autoclaw/api/**`
  - `apps/api/src/autoclaw/cli/**`
  - `apps/api/src/autoclaw/compiler/**`
  - `apps/api/src/autoclaw/db/**`
  - `apps/api/src/autoclaw/registry/**`
  - `apps/api/src/autoclaw/schemas/**`
  - `apps/api/src/autoclaw/platform/**`
  - root package modules under `apps/api/src/autoclaw/*.py`
- `P6-WP4`: runtime and reusable OpenClaw substrate boundaries
  - `apps/api/src/autoclaw/runtime/**`
  - adjacent `apps/api/src/autoclaw/integrations/openclaw/**`
- `P6-WP5`: final naming convergence, root-taxonomy convergence, and canonical package finalization
  - `apps/api/src/autoclaw/**`
  - package metadata and entrypoint cleanup
  - compatibility-test and import-smoke cleanup

## Ordered work packages

### `P6-WP3`

- objective: converge interfaces, definition-domain owners, persistence, contracts, platform, and root package owners around the current `src/autoclaw/**` tree before runtime closeout begins
- owned surfaces: `apps/api/src/autoclaw/{api,cli,compiler,db,registry,schemas,platform}/**`, root package modules, matching proof tests, and matching source-owner docs
- dependencies: Phase 0 canon reset
- test-first requirement: focused proof selectors for each completed platform, compiler, persistence, or contract family
- documentation update requirement: touched docs reflect the landed owner paths and dominant responsibilities
- closeout evidence: completed non-runtime source families pass their full touched-family source-quality gates, public HTTP, CLI, and MCP owners converge under `interfaces/**`, definition owners converge under `definitions/**` with `definitions/contracts/**`, persistence converges under `persistence/**`, runtime contracts converge under `runtime/contracts/**`, and no avoidable shared-owner or compatibility ambiguity remains
- required bounded package sequence:
  - package `P6-WP3A`: HTTP interface convergence
  - package `P6-WP3B`: CLI and MCP interface convergence
  - package `P6-WP3C`: definitions, persistence, and contract convergence
  - package `P6-WP3D`: platform, root, and non-runtime debt cleanup

### `P6-WP4`

- objective: converge the full runtime around direct domain owners, remove mechanism-first top-level buckets, and delete the standalone `runtime/openclaw/**` usage owner
- owned surfaces: `apps/api/src/autoclaw/runtime/**` and adjacent `apps/api/src/autoclaw/integrations/openclaw/**`
- dependencies: `P6-WP3`
- test-first requirement: focused proof selectors around each completed runtime or OpenClaw owner family
- documentation update requirement: touched docs reflect the landed owner paths and dominant responsibilities
- closeout evidence: runtime and OpenClaw source-owner families pass their full touched-family source-quality gates, reusable provider substrate converges under `integrations/openclaw/**`, runtime-owned contracts stay under `runtime/contracts/**`, and mechanism-first roots `runtime/effects/**`, `runtime/control/**`, and standalone `runtime/openclaw/**` no longer survive as top-level owner buckets
- required bounded package sequence:
  - package `P6-WP4A`: runtime foundations
  - package `P6-WP4B`: runtime domain-owner convergence
  - package `P6-WP4C`: dispatch, watchdog, replan, and OpenClaw runtime usage

### `P6-WP5`

- objective: finalize package authority, delete remaining compatibility ballast, and prove one self-contained canonical package rooted in `apps/api/src/autoclaw/**`
- owned surfaces: `apps/api/src/autoclaw/**`, package exports, entrypoints, package metadata, final audit-tool allowlists, remaining compatibility tests, and final Phase 6 docs
- dependencies: `P6-WP3`, `P6-WP4`
- test-first requirement: focused package-entrypoint and import-path smoke coverage for the final move plus focused proof for renamed public or shared surfaces
- documentation update requirement: compatibility-debt status and remaining migration exceptions are written explicitly
- closeout evidence: the canonical backend package move is complete, source-owner families are naming-clean, the final root taxonomy is coherent, no shipped compatibility shells or test-only compat lanes remain, and only product-canonical wrapper concepts survive
- required bounded package sequence:
  - package `P6-WP5A`: package authority and metadata finalization
  - package `P6-WP5B`: final debt purge and phase closeout

## Focused proof selector defaults

- `P6-WP3`
  - `apps/api/tests/unit/definition_schemas`
  - `apps/api/tests/unit/workflow_compiler`
  - `apps/api/tests/unit/test_package_entrypoints.py`
  - `apps/api/tests/unit/cli/test_main.py`
  - `apps/api/tests/unit/test_cli.py`
  - `apps/api/tests/integration/definition_registry`
  - `apps/api/tests/integration/phase3/routes`
  - `apps/api/tests/integration/runtime_schema_contract`
- `P6-WP4`
  - `apps/api/tests/unit/runtime/openclaw/test_host_setup.py`
  - `apps/api/tests/unit/runtime/openclaw/test_mcp_operation_failures.py`
  - `apps/api/tests/unit/runtime_prompt_rendering`
  - `apps/api/tests/integration/phase3/control`
  - `apps/api/tests/integration/phase3/db`
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
  2. `make format-api`
  3. `make check-api`
  4. full touched-family `style_audit --scan-root <path> --fail-on-findings`
  5. focused pytest selection for the affected family
  6. only the narrowest broader proof forced by the touched surface
- end-of-phase closeout only once:
  - `ruff format`
  - `ruff check`
  - `mypy`
  - `make format-api`
  - `make check-api`
  - `make pyright-api`
  - `./.venv/bin/python -m scripts.docs.style_audit.cli --scan-root apps/api/src/autoclaw --fail-on-findings`
  - `ruff check scripts/docs` and `mypy scripts/docs` when `scripts/docs/style_audit/**` changed
  - `./.venv/bin/python -m scripts.docs.docs_freeze.cli` when `docs-internal/execution/v1/**`, `docs-internal/current/v1/**`, `docs/reference/**`, or `scripts/docs/docs_freeze/**` changed as Phase 6 collateral
  - the full applicable backend test matrix for touched source surfaces
  - all viable e2e lanes required by the touched shipped surfaces

## Exit evidence

- each owner-family execution packet must record its exact source-owner scope and proof lanes
- historical `P6-WP0` through `P6-WP2` artifacts are summary-only background only
- Phase 6 closes only after the canonical backend package move is complete and the full source-only quality gates pass
