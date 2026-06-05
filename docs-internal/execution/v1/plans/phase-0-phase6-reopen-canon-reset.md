# Phase 0 Phase 6 Reopen Canon Reset Plan

Status: Reference

selected phase: Phase 0
current phase page: docs-internal/execution/v1/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP2, P0-WP3
summary-only: no
delegated slices: none

## Slice identity

- owner: Codex
- date: 2026-06-04
- work package bundle: `P0-CF0` reopen canon reset before live Phase 6 code work

## Goal

- reset the live execution canon so reopened Phase 6 work starts from the current `apps/api/src/autoclaw/**` tree and the refined steady-state taxonomy, not from removed `apps/api/app/**` or legacy `apps/api/autoclaw/**` owners

## Scope

- rewrite the live Phase 6 phase page, Phase 6 lock-map section, and the authoritative Phase 6 master plan to current-tree truth
- patch long-form standards so `interfaces/http/contracts/**` is an explicit allowed transport-contract lane
- reclassify `phase-6-source-audit-and-rename-map.*` and `phase-6-wp0-wp2-package-shell-and-transport-cutover.*` as `summary-only: yes` historical artifacts with truthful replacement links

## Locked surfaces

- owned surfaces:
  - `AGENTS.md`
  - `.agents/standards/code/naming.md`
  - `.agents/standards/structure/source-layout.md`
  - `.agents/standards/structure/repo-layout.md`
  - `.agents/standards/structure/integration-boundaries.md`
  - `docs-internal/execution/v1/maps/file-priority-map.md`
  - `docs-internal/execution/v1/phases/phase-6-source-structure-boundaries-and-naming-convergence.md`
  - `docs-internal/execution/v1/plans/phase-6-full-source-owner-convergence-and-package-migration.md`
  - `docs-internal/execution/v1/plans/phase-6-source-audit-and-rename-map.md`
  - `docs-internal/execution/v1/evidence/phase-6-source-audit-and-rename-map.md`
  - `docs-internal/execution/v1/reviews/phase-6-source-audit-and-rename-map.md`
  - `docs-internal/execution/v1/plans/phase-6-wp0-wp2-package-shell-and-transport-cutover.md`
  - `docs-internal/execution/v1/evidence/phase-6-wp0-wp2-package-shell-and-transport-cutover.md`
  - `docs-internal/execution/v1/reviews/phase-6-wp0-wp2-package-shell-and-transport-cutover.md`
  - `docs-internal/execution/v1/plans/phase-0-phase6-reopen-canon-reset.md`
  - `docs-internal/execution/v1/evidence/phase-0-phase6-reopen-canon-reset.md`
  - `docs-internal/execution/v1/reviews/phase-0-phase6-reopen-canon-reset.md`
  - `scripts/docs/docs_freeze/**`
  - `scripts/docs/docs_freeze/repo_refs.py`
- allowed collateral surfaces:
  - `scripts/docs/prompt_catalog/load.py`

## Required proof

- `ruff check scripts/docs`
- `mypy scripts/docs`
- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`

## Exit evidence

- the live Phase 6 contract no longer names removed `app/**` or legacy `autoclaw/**` trees as owned execution surfaces
- the authoritative Phase 6 plan now starts from the current `src/autoclaw/**` tree and the refined taxonomy
- the older Phase 6 artifacts are explicitly summary-only historical material
