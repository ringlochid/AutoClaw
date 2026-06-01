# Phase 0 Local-Tool-First Canon Fix

Status: Reference

selected phase: Phase 0
current phase page: docs-internal/execution/v1/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP1, P0-WP2
summary-only: no
delegated slices: none

## Slice identity

- owner: Codex
- date: 2026-05-13
- work package or slice: Phase 0 local-tool-first canon fix for root and execution routing

## Subagents decision

- `no subagents`

## Wave integration rule

- parent no-edit during wave: not applicable; no subagents
- full-wave wait rule: not applicable; no subagents
- ownership-boundary and slice-type review: keep edits inside `P0-WP1` root canon and `P0-WP2` execution-router surfaces
- revert rule for out-of-scope or review-only edits: revert any drift into execution maps, docs tooling, `docs-internal/current/v1/**`, or repo code
- validation and review before next wave: run the single allowed docs validator after edits, then rewrite evidence and review

## Goal

- harden root and execution canon so Phase 0-3 are explicitly one-process local-tool-first
- demote MQ or distributed-safe wording to non-goal notes instead of active design pressure
- route exact inline-versus-after-return timing, case-sequence behavior, and sync/async ownership into the owning Phase 2 or Phase 3 pages

## Phase-local contract

- current phase page: `docs-internal/execution/v1/phases/phase-0-docs-contract-freeze-and-setup.md`
- implementation file lock map: `docs-internal/execution/v1/maps/file-priority-map.md`
- required reads completed: `AGENTS.md`, `STYLE.md`, `docs-internal/execution/v1/README.md`, `docs-internal/execution/v1/phases/overview.md`, `docs-internal/execution/v1/phases/phase-0-docs-contract-freeze-and-setup.md`, `docs-internal/execution/v1/maps/file-priority-map.md`, `docs-internal/execution/v1/maps/design-code-landing-map.md`, the Phase 0 primary design pages, the named supporting design reads, the named current-contrast reads, and the named prompt examples

## Locked surfaces

- owned surfaces:
  - `AGENTS.md`
  - `docs-internal/execution/v1/README.md`
  - `docs-internal/execution/v1/phases/overview.md`
  - `docs-internal/execution/v1/how-to/use-this-pack-for-implementation.md`
  - `docs-internal/execution/v1/gates/phase-implementation-prompts.md`
  - `docs-internal/execution/v1/phases/phase-0-docs-contract-freeze-and-setup.md`
  - `docs-internal/execution/v1/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
  - `docs-internal/execution/v1/phases/phase-3-runtime-parent-review-and-replan.md`
  - `docs-internal/execution/v1/plans/phase-0-canon-validator-and-authority-repair.md`
  - `docs-internal/execution/v1/evidence/phase-0-canon-validator-and-authority-repair.md`
  - `docs-internal/execution/v1/reviews/phase-0-canon-validator-and-authority-repair.md`
- allowed collateral surfaces: none planned
- do not edit or defer surfaces:
  - `apps/**`
  - `docs-internal/current/v1/**`
  - `docs-internal/execution/v1/maps/*`
  - `scripts/docs/**`
  - root `README.md`
  - `docs/README.md`

## Success criteria

- root canon states that Phase 0-3 optimize for a one-process local tool
- MQ or distributed-safe language remains only as a non-goal note
- execution router pages direct exact timing and sync/async questions into Phase 2 or Phase 3 owner docs
- Phase 2 and Phase 3 pages state their own local-tool-first timing ownership explicitly
- the authoritative Phase 0 triplet matches this slice and uses `selected work packages: P0-WP1, P0-WP2`

## Deliverables and milestones

- deliverables:
  - root canon update in `AGENTS.md`
  - execution router updates under `docs-internal/execution/v1/`
  - refreshed Phase 0 plan, evidence, and review triplet
- milestones:
  - Phase 0 root/execution stance aligned
  - Phase 2 or Phase 3 timing ownership aligned
  - validator outcome recorded

## Ordered work packages

- `P0-WP1`: update `AGENTS.md` so root canon states the Phase 0-3 local-tool-first stance and removes queue-first pressure
- `P0-WP2`: update execution router, how-to, prompt, and owning phase pages so timing or sync/async questions route into Phase 2 or Phase 3

## Validation checkpoints

- confirm no edit is needed in execution maps or `docs-internal/current/v1/**`
- rewrite the authoritative Phase 0 triplet after the doc edits settle
- run `./.venv/bin/python -m scripts.docs.docs_freeze.cli validate` once after the edits

## Required tests and validators

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli validate`

## Required docs and examples

- `AGENTS.md`
- `docs-internal/execution/v1/README.md`
- `docs-internal/execution/v1/phases/overview.md`
- `docs-internal/execution/v1/how-to/use-this-pack-for-implementation.md`
- `docs-internal/execution/v1/gates/phase-implementation-prompts.md`
- `docs-internal/execution/v1/phases/phase-0-docs-contract-freeze-and-setup.md`
- `docs-internal/execution/v1/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
- `docs-internal/execution/v1/phases/phase-3-runtime-parent-review-and-replan.md`
- `docs-internal/design/v1/prompt-layer/composition-example.md`
- `docs-internal/design/v1/prompt-layer/generated/rendered-examples.md`

## Exit evidence

- evidence expected under `../evidence/`:
  - exact changed-file list for the local-tool-first canon fix
  - exact validator command and outcome
  - note of any residual wording conflicts or blocked follow-up

## Rollback or stop conditions

- stop if the local-tool-first canon fix requires `docs-internal/current/v1/**` edits
- stop if the local-tool-first routing cannot land without reopening `P0-WP3` execution maps
- stop if the docs validator requires `scripts/docs/**` changes

## Cross-links

- evidence artifact: `../evidence/phase-0-canon-validator-and-authority-repair.md`
- review artifact: `../reviews/phase-0-canon-validator-and-authority-repair.md`
