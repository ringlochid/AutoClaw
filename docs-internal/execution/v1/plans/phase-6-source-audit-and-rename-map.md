# Phase 6 Source-Only Audit And Owner Map Plan

Status: Reference

selected phase: Phase 6
current phase page: docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md
selected work packages: P6-WP0
summary-only: no
delegated slices: listed
slice id: phase6_wp0_review
slice type: review-only
owned surfaces: docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md, docs-internal/execution/v1/phases/phase-7-test-structure-and-proof-convergence.md, docs-internal/execution/v1/maps/file-priority-map.md, docs-internal/execution/v1/plans/phase-6-source-audit-and-rename-map.md, docs-internal/execution/v1/evidence/phase-6-source-audit-and-rename-map.md, docs-internal/execution/v1/reviews/phase-6-source-audit-and-rename-map.md, docs-internal/execution/v1/plans/phase-6-full-source-owner-convergence-and-package-migration.md, scripts/docs/docs_freeze/**, apps/api/tests/unit/test_docs_freeze.py, apps/api/app/cli/__init__.py, apps/api/app/cli/commands/server_config.py
touched surfaces: none

## Slice identity

- owner: Codex
- date: 2026-06-03
- work package or slice: `P6-WP0` source-only audit baseline and owner map

## Subagents decision

- one fresh `review-only` slice runs after the docs and validator proof is green and before staging
- no edit subagents

## Delegated slice brief

### phase6_wp0_review

- slice type: `review-only`
- selected phase and package scope: `Phase 6`, `P6-WP0`
- owned surfaces:
  - `docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md`
  - `docs-internal/execution/v1/phases/phase-7-test-structure-and-proof-convergence.md`
  - `docs-internal/execution/v1/maps/file-priority-map.md`
  - the `P6-WP0` plan, evidence, and review packet
  - the new full-source Phase 6 master plan
  - touched `scripts/docs/docs_freeze/**`
  - touched `apps/api/tests/unit/test_docs_freeze.py`
  - touched `apps/api/app/cli/__init__.py`
  - touched `apps/api/app/cli/commands/server_config.py`
- do-not-edit surfaces:
  - all repo files; findings only
- required reads:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md`
  - `docs-internal/execution/v1/phases/phase-7-test-structure-and-proof-convergence.md`
  - `docs-internal/execution/v1/maps/file-priority-map.md`
  - this `P6-WP0` plan plus the matching evidence and review artifact
- expected outputs:
  - prioritized findings only, or an explicit stage-readiness pass verdict
- required tests or validators:
  - the focused docs and validator proof chain recorded in the matching evidence artifact
- dependencies:
  - the parent must finish the docs-freeze and validator proof before the review starts
- evidence to return:
  - file-referenced findings or a stage-readiness verdict
- parent-owned decisions:
  - final doc edits, validator edits, packet wording, and staging
- stop conditions:
  - if a concern requires widening into non-Phase-6 docs cleanup or source-owner implementation, report it as out-of-scope instead of expanding the slice

## Goal

- freeze the Phase 6 source-only owner, naming, wrapper, and proof map before any broad source mutation begins

## Authoritative follow-on plan

- the live follow-on master plan after this baseline is `docs-internal/execution/v1/plans/phase-6-full-source-owner-convergence-and-package-migration.md`
- this `P6-WP0` packet remains authoritative for the audit baseline only; it does not authorize hotspot-only closure for later source-owner work

## Phase-local contract

- current phase page: `docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md`
- implementation file lock map: `docs-internal/execution/v1/maps/file-priority-map.md`
- required reads completed: `AGENTS.md`, `STYLE.md`, `docs-internal/execution/v1/README.md`, `docs-internal/execution/v1/phases/overview.md`, `docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md`, `docs-internal/execution/v1/maps/file-priority-map.md`, `docs-internal/design/v1/architecture/design-overview.md`, `docs-internal/design/v1/architecture/glossary-and-boundaries.md`, `docs-internal/design/v1/interfaces/cli-api-and-package-shape.md`, `docs-internal/design/v1/architecture/runtime-lifecycle-overview.md`, `docs-internal/design/v1/architecture/README.md`, `docs-internal/design/v1/interfaces/README.md`, `docs-internal/design/v1/architecture/provider-worker-and-operator-boundary.md`, `docs-internal/design/v1/interfaces/mcp-plugin-and-cli-boundary.md`, `docs-internal/design/v1/architecture/runtime-records-and-lifecycle.md`, `docs-internal/current/v1/architecture/current-architecture.md`, `docs-internal/current/v1/interfaces/api-surface-and-route-map.md`, `docs-internal/current/v1/interfaces/cli-surface-and-config-precedence.md`, `docs-internal/current/v1/architecture/openclaw-and-bridge-plugin.md`, `.agents/standards/structure/repo-layout.md`, `.agents/standards/structure/source-layout.md`, `.agents/standards/structure/integration-boundaries.md`, `.agents/standards/code/naming.md`, `.agents/standards/code/readability-refactor.md`, and `.agents/standards/structure/test-structure.md`

## Locked surfaces

- owned surfaces: `scripts/docs/style_audit/**`, `apps/api/tests/unit/test_style_audit.py`, and the Phase 6 packet under `docs-internal/execution/v1/plans/`, `docs-internal/execution/v1/evidence/`, and `docs-internal/execution/v1/reviews/`
- allowed collateral surfaces used in this package: `scripts/docs/docs_freeze/**`, `apps/api/tests/unit/test_docs_freeze.py`, the narrow Phase 6 execution docs that now name the source-only owner-family gates explicitly, and the opening gate-unblock collateral in `apps/api/app/cli/__init__.py` plus `apps/api/app/cli/commands/server_config.py`
- do not edit or defer surfaces: production source moves, production renames, broad test-tree relayout, grouped-runner cleanup, and any end-to-end or DB-lane widening beyond the focused proof named below

## Source-only baseline findings

These counts are live-worktree baseline measurements captured by the source-only audit commands above. This `P6-WP0` packet stages only the docs and validator rewrite; it does not stage source-owner edits itself.

### Audit summary

| Baseline finding | Count |
| --- | ---: |
| scanned source files | 291 |
| import-direction findings | 36 |
| module-shape findings | 321 |
| public naming findings | 21 |
| function-size threshold violations | 1 |
| file-size threshold violations | 0 |

### Source inventory

| Scope | Python files |
| --- | ---: |
| `apps/api/app/**` | 269 |
| `apps/api/autoclaw/**` | 22 |

### Representative backlog

| Concern | Current baseline |
| --- | --- |
| package authority drift | `apps/api/autoclaw/**` still imports `app.*` across bridge and MCP-facing families, and `src/autoclaw` does not yet exist as the public package root |
| transport owner split | API, CLI, `cli/terminal/**`, root startup shells, and public wrappers still encode parallel durable owners after this packet removed stale owner references to deleted `cli_commands/**` and `terminal/**` trees |
| root taxonomy drift | the target package still trends toward a mixed top-level `api/`, `cli/`, `compiler/`, `registry/`, `runtime/`, `db/`, `schemas/`, and `integrations/` root instead of one coherent `interfaces/`, `definitions/`, `runtime/`, `integrations/`, `persistence/`, and `platform/` taxonomy with domain-owned `definitions/contracts/**` and `runtime/contracts/**` lanes |
| platform and shared root drift | root modules and shared owners such as `config.py`, `paths.py`, `file_entrypoints.py`, `core/**`, `service_managers/**`, and `services/**` still need owner-family cleanup |
| runtime and OpenClaw readability debt | `apps/api/app/runtime/**` still carries broad module-shape debt, and runtime or OpenClaw closure cannot rely on hotspot-only cleanup |
| public naming debt | weak public verbs and non-fact-shaped booleans remain on shared or public surfaces such as `apps/api/app/main.py`, `apps/api/autoclaw/openclaw/common.py`, and `apps/api/autoclaw/openclaw/node_mcp/runtime_tools.py` |
| remaining size hotspot | `apps/api/autoclaw/openclaw/node_mcp/runtime_tools.py:register_node_runtime_tools` remains above the function-size threshold |

## Canonical package authority table

| Current source family | Current owner | Target owner | Temporary shim status | Owning future wave |
| --- | --- | --- | --- | --- |
| `apps/api/app/**` | legacy backend package and dominant source owner | `apps/api/src/autoclaw/**` domain-first canonical package | no new legacy-first growth; only explicit bridge surfaces may survive | Waves A, B, C, D, E, and F |
| `apps/api/autoclaw/**` | current public wrapper, entrypoint, and OpenClaw adapter lane | `apps/api/src/autoclaw/interfaces/**`, `apps/api/src/autoclaw/runtime/openclaw/**`, and `apps/api/src/autoclaw/integrations/openclaw/**` | approved re-export shims only | Waves A, B, E, and F |
| `apps/api/app/api/routes/**` | current transport route package | `apps/api/src/autoclaw/interfaces/http/routers/**` | temporary directory-wide wrapper allowance only | Waves B and F |
| `apps/api/src/autoclaw/**` | not yet created in repo truth | canonical backend package root | no wrapper status; this becomes the authority | Wave A |

## Wrapper disposition table

| Path | Current shape | Phase 6 status | Owning future wave |
| --- | --- | --- | --- |
| `legacy cli.py wrapper under apps/api/app/` | pure import-only wrapper to `app.cli.main` | active finding; do not allowlist | Wave A |
| stale `app/terminal/**` owner tree | no live source modules remain outside `__pycache__` | remove stale owner references from Phase 6 docs and keep no allowlist for this deleted tree | Wave B |
| `apps/api/app/runtime/contracts.py` | import-only export surface over `app.runtime.contract_models/**` | approved temporary shim | Wave D |
| `apps/api/app/runtime/ids.py` | substantive shared utility module, not a pure wrapper | keep as active shared source until naming cleanup | Wave E |
| `apps/api/autoclaw/cli.py` | import-only wrapper to `app.cli` plus CLI `__main__` surface | approved temporary shim | Wave F |
| `apps/api/autoclaw/main.py` | import-only wrapper to `app.main` | approved temporary shim | Wave F |
| `apps/api/autoclaw/openclaw/node_server.py` | import-only wrapper to `autoclaw.openclaw.node_mcp` exports | approved temporary shim | Wave F |
| `apps/api/autoclaw/openclaw/operator_server.py` | import-only wrapper to `autoclaw.openclaw.operator_mcp` exports | approved temporary shim | Wave F |

## Source-owner map by future Wave A-F

| Wave | Current path families | Target owner packages | Future `src/autoclaw` landing family |
| --- | --- | --- | --- |
| Wave A | `apps/api/src/autoclaw/**`, `apps/api/app/*.py`, `apps/api/autoclaw/*.py`, and `pyproject.toml` | package metadata, import shells, and bridge surfaces | `apps/api/src/autoclaw/**` package root and public-interface family |
| Wave B | `apps/api/app/api/**`, `apps/api/app/cli/**`, `apps/api/app/main.py`, `apps/api/app/cli_support.py`, and public wrapper or MCP-facing entrypoint shells under `apps/api/autoclaw/**` | public transport and wrapper shells | `apps/api/src/autoclaw/interfaces/http/**`, `apps/api/src/autoclaw/interfaces/cli/**`, and `apps/api/src/autoclaw/interfaces/mcp/**` |
| Wave C | `apps/api/app/config.py`, `apps/api/app/paths.py`, `apps/api/app/file_entrypoints.py`, `apps/api/app/core/**`, `apps/api/app/service_managers/**`, `apps/api/app/services/**`, `apps/api/app/resources/**` | platform and shared owners | `apps/api/src/autoclaw/platform/**` plus stable shared root modules |
| Wave D | `apps/api/app/compiler/**`, `apps/api/app/db/**`, `apps/api/app/registry/**`, `apps/api/app/schemas/**` | definition-domain, persistence, and contract owners | `apps/api/src/autoclaw/definitions/**` with `definitions/contracts/**`, `apps/api/src/autoclaw/persistence/**`, and `apps/api/src/autoclaw/runtime/contracts/**` |
| Wave E | `apps/api/app/runtime/**` and non-shim `apps/api/autoclaw/openclaw/**` | runtime and OpenClaw internals | `apps/api/src/autoclaw/runtime/**` and `apps/api/src/autoclaw/integrations/openclaw/**` |
| Wave F | `apps/api/src/autoclaw/**`, residual shims, final package metadata and exports | final canonical package move, root-taxonomy convergence, and shim removal | `apps/api/src/autoclaw/**` with `interfaces/**`, `definitions/**`, `runtime/**`, `integrations/**`, `persistence/**`, and `platform/**`, plus domain-owned `definitions/contracts/**` and `runtime/contracts/**` only |

## Focused proof selector matrix for P6-WP1 through P6-WP5

| Work package | Current focused selectors |
| --- | --- |
| `P6-WP1` | `apps/api/tests/unit/test_package_entrypoints.py`<br>`apps/api/tests/unit/cli/test_main.py`<br>`apps/api/tests/unit/test_cli.py` |
| `P6-WP2` | `apps/api/tests/unit/cli/test_main.py`<br>`apps/api/tests/unit/test_cli.py`<br>`apps/api/tests/integration/phase5a/test_root_cli_phase5a.py`<br>`apps/api/tests/integration/phase3/routes`<br>`apps/api/tests/integration/test_readyz_real_db.py`<br>`apps/api/tests/integration/test_startup_schema_guard.py` |
| `P6-WP3` | `apps/api/tests/unit/definition_schemas`<br>`apps/api/tests/unit/workflow_compiler`<br>`apps/api/tests/integration/definition_registry`<br>`apps/api/tests/integration/phase3/db`<br>`apps/api/tests/integration/runtime_schema_contract` |
| `P6-WP4` | `apps/api/tests/unit/runtime/openclaw/test_host_setup.py`<br>`apps/api/tests/unit/runtime/openclaw/test_mcp_operation_failures.py`<br>`apps/api/tests/unit/runtime_prompt_rendering`<br>`apps/api/tests/integration/phase3/control`<br>`apps/api/tests/integration/phase3/db`<br>`apps/api/tests/integration/phase3/routes`<br>`apps/api/tests/integration/phase4a/runtime_dispatch_gateway`<br>`apps/api/tests/integration/phase4b/watchdog`<br>`apps/api/tests/integration/phase4b/mcp`<br>`apps/api/tests/integration/runtime_schema_contract` |
| `P6-WP5` | `apps/api/tests/unit/test_package_entrypoints.py`<br>`apps/api/tests/unit/cli/test_main.py`<br>`apps/api/tests/unit/test_cli.py`<br>`apps/api/tests/integration/definition_registry`<br>`apps/api/tests/integration/phase5a/test_root_cli_phase5a.py`<br>`apps/api/tests/integration/phase5a/mcp/test_operator_server_phase5a.py`<br>`apps/api/tests/integration/runtime_schema_contract` |

## Validation checkpoints

- land the audit-tool unit coverage before changing the scanners
- keep the Phase 6 pre-pytest gate order explicit: touched-scope import and interface check first, then `make format-api`, then `make check-api`, then any pytest
- record the source-only baseline evidence before mutating the report order or execution packet
- close `P6-WP0` only when the new audits expose stale-shape backlog without flagging unresolved `WP0` tooling debt

## Required tests and validators

- Phase 6 future-wave pre-pytest gate order captured by this `WP0` packet:
  - touched-scope import and interface gate
  - `make format-api`
  - `make check-api`
  - focused pytest only after those three pass
- `make check-api`
- `./.venv/bin/python -m pytest apps/api/tests/unit/test_style_audit.py apps/api/tests/unit/test_docs_freeze.py -q`
- `./.venv/bin/ruff check scripts/docs apps/api/tests/unit/test_style_audit.py apps/api/tests/unit/test_docs_freeze.py`
- `./.venv/bin/mypy scripts/docs`
- `make pyright-api`
- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --scan-root apps/api/app --scan-root apps/api/autoclaw`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --scan-root apps/api/app --scan-root apps/api/autoclaw --fail-on-findings`

## Exit evidence

- evidence artifact: `../evidence/phase-6-source-audit-and-rename-map.md`
- review artifact: `../reviews/phase-6-source-audit-and-rename-map.md`
