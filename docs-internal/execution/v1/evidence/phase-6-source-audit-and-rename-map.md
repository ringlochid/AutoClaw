# Phase 6 Source-Only Audit And Owner Map Evidence

Status: Reference

selected phase: Phase 6
current phase page: docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md
selected work packages: P6-WP0
summary-only: yes
delegated slices: listed
slice id: phase6_wp0_review
slice type: review-only
owned surfaces: docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md, docs-internal/execution/v1/phases/phase-7-test-structure-and-proof-convergence.md, docs-internal/execution/v1/maps/file-priority-map.md, docs-internal/execution/v1/plans/phase-6-source-audit-and-rename-map.md, docs-internal/execution/v1/evidence/phase-6-source-audit-and-rename-map.md, docs-internal/execution/v1/reviews/phase-6-source-audit-and-rename-map.md, docs-internal/execution/v1/plans/phase-6-full-source-owner-convergence-and-package-migration.md, scripts/docs/docs_freeze/**, apps/api/tests/unit/test_docs_freeze.py, apps/api/src/autoclaw/interfaces/cli/__init__.py, apps/api/src/autoclaw/interfaces/cli/commands/server_config.py
touched surfaces: none

## Slice identity

- work package or slice: `P6-WP0`
- slice type: edit
- date: 2026-06-03

## Authoritative replacements

- `docs-internal/execution/v1/evidence/phase-0-phase6-reopen-canon-reset.md`
- `docs-internal/execution/v1/plans/phase-6-full-source-owner-convergence-and-package-migration.md`

## Plan and review links

- approved plan: `../plans/phase-6-source-audit-and-rename-map.md`
- mandatory review: `../reviews/phase-6-source-audit-and-rename-map.md`
- review artifact: `../reviews/phase-6-source-audit-and-rename-map.md`

## Commands run

- `./.venv/bin/python -m pytest apps/api/tests/unit/test_style_audit.py apps/api/tests/unit/test_docs_freeze.py -q`
- `./.venv/bin/ruff check scripts/docs apps/api/tests/unit/test_style_audit.py apps/api/tests/unit/test_docs_freeze.py`
- `./.venv/bin/mypy scripts/docs`
- `make check-api`
- `make pyright-api`
- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --scan-root apps/api/app --scan-root apps/api/autoclaw`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --scan-root apps/api/app --scan-root apps/api/autoclaw --fail-on-findings`

## Phase 6 wave gate-order truth

- the Phase 6 packet now records this future-wave pre-pytest order explicitly:
  1. touched-scope import and interface check
  2. `make format-api`
  3. `make check-api`
  4. only then pytest
- this `P6-WP0` packet records the opening `make check-api` gate-unblock collateral in `apps/api/src/autoclaw/interfaces/cli/__init__.py` and `apps/api/src/autoclaw/interfaces/cli/commands/server_config.py`, while broader owner-family mutations remain deferred to `P6-WP1` through `P6-WP5`

## Gate and validator summary

- docs validators: `scripts.docs.docs_freeze.cli` passed after the Phase 6 packet rewrite, stale owner-tree reference cleanup, and stale partial-packet removal
- audit-tool proof: `test_style_audit.py`, `test_docs_freeze.py`, `ruff check scripts/docs`, `mypy scripts/docs`, and `make pyright-api` passed
- repo-native source gate unblock: `make check-api` now passes after the bounded `__all__` ordering cleanup in `apps/api/src/autoclaw/interfaces/cli/__init__.py` and `apps/api/src/autoclaw/interfaces/cli/commands/server_config.py`
- Phase 6 gate-order truth: later source-owner waves must run the import/interface gate, then `make format-api`, then `make check-api`, before any pytest expansion
- source-only audit baseline: report-mode `style_audit` completed on `apps/api/app/**` plus `apps/api/autoclaw/**`
- expected backlog proof: source-only `style_audit --fail-on-findings` exited non-zero because `P6-WP1` through `P6-WP5` source-owner debt still remains by design at `WP0`

## Source-only baseline repo truth

These source counts and audit findings are live-worktree baseline measurements captured by the source-only audit commands above. The staged snapshot for this packet contains only the docs and validator rewrite, not source-owner edits.

### Source inventory

| Scope | Python files |
| --- | ---: |
| `apps/api/app/**` | 269 |
| `apps/api/autoclaw/**` | 22 |
| total shipped backend source | 291 |

### Style audit summary

| Finding family | Count |
| --- | ---: |
| import-direction findings | 36 |
| module-shape findings | 321 |
| public naming findings | 21 |
| function-size threshold violations | 1 |
| file-size threshold violations | 0 |

### Representative source-owner backlog

| Surface | Current backlog |
| --- | --- |
| package authority | `apps/api/autoclaw/**` still imports `app.*` across bridge and MCP-facing families |
| transport owners | API, CLI, `cli/terminal/**`, and public wrapper families still encode parallel durable owners after this packet removed stale owner references to deleted `cli_commands/**` and `terminal/**` trees |
| root taxonomy | the target package still trends toward a mixed top-level `api/`, `cli/`, `compiler/`, `registry/`, `runtime/`, `db/`, `schemas/`, and `integrations/` root instead of one coherent `interfaces/`, `definitions/`, `runtime/`, `integrations/`, `persistence/`, and `platform/` taxonomy with domain-owned `definitions/contracts/**` and `runtime/contracts/**` lanes |
| platform and shared owners | root modules and shared owner families such as `config.py`, `paths.py`, `file_entrypoints.py`, `core/**`, `service_managers/**`, `services/**`, and `resources/**` still need full-family cleanup |
| runtime and OpenClaw internals | `apps/api/src/autoclaw/runtime/**` still carries broad module-shape debt, and runtime closure cannot rely on hotspot-only cleanup |
| public naming | weak public verbs and non-fact-shaped booleans remain on shared and public surfaces such as `apps/api/src/autoclaw/main.py`, `apps/api/src/autoclaw/interfaces/mcp/transport.py`, and `apps/api/src/autoclaw/interfaces/mcp/node/runtime_tools.py` |
| size hotspot | `apps/api/src/autoclaw/interfaces/mcp/node/runtime_tools.py:register_node_runtime_tools` remains above the function-size threshold |

## Artifacts changed

- `docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md`
- `docs-internal/execution/v1/maps/file-priority-map.md`
- `docs-internal/execution/v1/plans/phase-6-source-audit-and-rename-map.md`
- `docs-internal/execution/v1/evidence/phase-6-source-audit-and-rename-map.md`
- `docs-internal/execution/v1/reviews/phase-6-source-audit-and-rename-map.md`
- `docs-internal/execution/v1/plans/phase-6-full-source-owner-convergence-and-package-migration.md`
- `docs-internal/execution/v1/phases/phase-7-test-structure-and-proof-convergence.md`
- `scripts/docs/docs_freeze/content/markers_execution.py`
- `scripts/docs/docs_freeze/validation/docs.py`
- `apps/api/tests/unit/test_docs_freeze.py`
- `apps/api/src/autoclaw/interfaces/cli/__init__.py`
- `apps/api/src/autoclaw/interfaces/cli/commands/server_config.py`
- stale partial Phase 6 hotspot packet chain removed from the live execution-doc set

## Residual blockers

- none for the `P6-WP0` reopen packet itself
- the non-zero source-only `style_audit --fail-on-findings` result is intentional backlog evidence for `P6-WP1` through `P6-WP5`, not a `P6-WP0` blocker
- broader source-owner backlog still remains under `P6-WP1` through `P6-WP5`; `P6-WP0` only cleared the two opening `make check-api` blockers rather than taking transport-wave closure authority
