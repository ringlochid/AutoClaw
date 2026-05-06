# Phase 0 Canon and Current-Contrast Repair

Status: Reference

## Slice identity

- selected phase: Phase 0
- work package or slice: canon, current-contrast, validator, and closeout-summary repair
- owner: Codex
- date: 2026-05-05

## Subagents decision

- delegated slices:
  - execution canon and lock-map repair
  - current seed-authority doc repair
  - current runtime-control doc repair
  - docs validator hardening
  - aggregate closeout-summary normalization

## Goal

- make the docs, gates, execution-pack wording, current-contrast pages, and
  docs validator trustworthy enough that later Phase 1-3 work can be planned
  and closed against real canon

## Phase-local contract

- current phase page: `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- implementation file lock map: `docs/execution/maps/file-priority-map.md`
- required reads completed: yes

## Locked surfaces

- owned surfaces: `AGENTS.md`, `STYLE.md`, `docs/README.md`, `docs/execution/**`, `scripts/docs/*`
- allowed collateral surfaces: `docs/redesign/prompt-layer/*`, `README.md`
- do not edit or defer surfaces: repo code, registry/runtime/compiler implementation, and `docs/current/**` beyond the four explicit unlock pages

## Success criteria

- one selected phase per authoritative plan, evidence, and review artifact is explicit canon
- the four named current-contrast pages match shipped seed and cancel behavior
- `docs_freeze_validate.py` contains explicit assertions for those pages
- `phase-0-3-closeout*` is summary-only and no longer claims authoritative pass
- delegated-slice and per-wave evidence requirements are explicit

## Deliverables and milestones

- deliverables:
  - corrected execution-pack canon
  - corrected current-contrast pages
  - hardened docs validator
  - normalized aggregate closeout-summary artifacts
  - Phase 0-scoped plan, evidence, and review artifacts
- milestones:
  - execution canon aligned
  - current docs aligned
  - validator green
  - closeout summary demoted
  - Phase 0 review passed

## Ordered work packages

- `P0-WP1`: execution canon and lock-map repair
- `P0-WP2`: current seed-authority and cancel-behavior doc repair
- `P0-WP3`: explicit validator assertions for the named current docs and closeout summaries
- `P0-WP4`: aggregate closeout-summary normalization
- `P0-WP5`: Phase 0 evidence and mandatory review

## Validation checkpoints

- docs freeze validator passes with explicit current-doc assertions
- `ruff check scripts/docs` passes
- `mypy scripts/docs` passes
- aggregate closeout summaries no longer satisfy closure authority

## Required tests and validators

- `./.venv/bin/python scripts/docs/docs_freeze_validate.py`
- `./.venv/bin/ruff check scripts/docs`
- `./.venv/bin/mypy scripts/docs`

## Required docs and examples

- execution pack routers, gate pages, maps, and the Phase 0 page
- `docs/current/interfaces/definition-precedence-and-skill-version-defaults.md`
- `docs/current/interfaces/definitions-compiler-and-launch.md`
- `docs/current/interfaces/definition-registry-and-publish-lifecycle.md`
- `docs/current/architecture/runtime-control-plane.md`
- aggregate `phase-0-3-closeout*` artifacts

## Exit evidence

- evidence artifact: `../evidence/phase-0-canon-current-contrast-repair.md`

## Rollback or stop conditions

- stop if any additional `docs/current/**` page must change without canon unlock
- stop if a needed fix requires changing runtime/compiler/registry code to make docs true
- stop if prompt-layer wording would imply live runtime behavior changes instead of documentation repair

## Cross-links

- evidence artifact: `../evidence/phase-0-canon-current-contrast-repair.md`
- review artifact: `../reviews/phase-0-canon-current-contrast-repair.md`
