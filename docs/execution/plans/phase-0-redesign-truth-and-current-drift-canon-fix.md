# Phase 0 Redesign Truth And Current Drift Canon-Fix Plan

Status: Reference

selected phase: Phase 0
current phase page: docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP1, P0-WP2, P0-WP3
summary-only: no
delegated slices: none

## Slice identity

- owner: parent agent only
- date: 2026-05-21
- work package or slice: redesign-truth authority lock plus current-drift doc repair

## Subagents decision

- `no subagents`

## Wave integration rule

- parent no-edit during wave: not applicable
- full-wave wait rule: not applicable
- ownership-boundary and slice-type review: the slice stays inside `AGENTS.md`, root/front-door routers, named `docs/current/**` repairs, and one new Phase 0 execution triplet
- revert rule for out-of-scope or review-only edits: stop and patch scope before landing out-of-scope doc or code changes
- validation and review before next wave: run docs-freeze, focused stale-term searches, and the config-mismatch repro before final review

## Goal

- make redesign-first authority explicit
- stop routed current docs from teaching dispatch, manifest, and CLI drift as live truth
- record the known non-doc follow-up debt so later execution cannot lose it

## Phase-local contract

- current phase page: `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- implementation file lock map: `docs/execution/maps/file-priority-map.md`
- required reads completed:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs/execution/README.md`
  - `docs/execution/phases/overview.md`
  - `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
  - `docs/execution/maps/file-priority-map.md`
  - routed redesign owner pages for dispatch, manifest, session lifecycle, launch materialization, and install/onboarding
  - named current-contrast pages being repaired in this slice

## Locked surfaces

- owned surfaces:
  - `AGENTS.md`
  - `docs/README.md`
  - `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
  - `docs/current/README.md`
  - `docs/current/architecture/README.md`
  - `docs/current/architecture/openclaw-dispatch-and-session-contract.md`
  - `docs/current/interfaces/definitions-compiler-and-launch.md`
  - `docs/current/architecture/runtime-control-plane.md`
  - `docs/current/architecture/manifest-projection-and-acknowledgement.md`
  - `docs/current/operations/inspect-approvals-and-watchdog.md`
  - `docs/current/interfaces/cli-surface-and-config-precedence.md`
  - `docs/current/architecture/openclaw-and-bridge-plugin.md`
  - `docs/current/interfaces/current-definition-bootstrap-and-task-upload.md`
  - `docs/current/architecture/runtime-read-models-and-operator-surfaces.md`
  - `scripts/docs/docs_freeze/phase_records/rules.py`
  - this plan plus the matching evidence and review artifacts
- allowed collateral surfaces:
  - none beyond the named routed current-doc repairs and root/front-door routing surfaces
- do not edit or defer surfaces:
  - runtime code
  - config loader code
  - redesign owner docs beyond reinforcing already-locked authority wording in root/router surfaces
  - existing summary-only execution chains

## Success criteria

- `AGENTS.md` explicitly teaches `docs/redesign/**` as the target source of truth
- `docs/README.md` teaches redesign-first routing and keeps `current/` contrast-only
- routed current docs no longer teach live dispatch `bootstrap | execution`
- routed current docs no longer teach manifest acknowledgement as a live runtime step
- current launch docs say `POST /tasks/start` exists today
- current docs do not promise an unsupported `wait_for_response=true` dispatch mode
- operator-facing current CLI docs no longer teach `bootstrap` as the primary local noun
- the known config-knob mismatch is recorded as a later Phase 4B code follow-up, not lost in a docs-only slice

## Deliverables and milestones

- deliverables:
  - redesign-first authority wording in root canon and docs front-door routers
  - current-doc drift cleanup across dispatch, manifest, launch, watchdog, CLI, and OpenClaw boundary pages
  - one authoritative Phase 0 plan/evidence/review triplet for this slice
- milestones:
  - authority wording aligned
  - routed current pages repaired
  - execution record added

## Ordered work packages

- `P0-WP1`: tighten repo-wide authority teaching in `AGENTS.md` and `docs/README.md`
- `P0-WP2`: rewrite routed current docs so they stop teaching redesign-removed dispatch and manifest concepts as live truth
- `P0-WP3`: record the slice and the known future-cleanup debt in one authoritative Phase 0 triplet

## Validation checkpoints

- confirm the routed current-doc set still matches the Phase 0 allowed-current unlock
- confirm filenames for stale current pages remain stable
- confirm no new summary-only master artifact is created
- confirm the config mismatch is recorded as later Phase 4B work rather than patched in this slice

## Required tests and validators

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- `./.venv/bin/ruff check scripts/docs`
- `./.venv/bin/mypy scripts/docs`
- `rg -n "bootstrap shape|execution shape|manifest to acknowledge|ack their manifest|not a public HTTP route|wait_for_response=true|Init and local bootstrap" docs/current docs/README.md AGENTS.md`
- `PYTHONPATH=apps/api ./.venv/bin/python - <<'PY' ...` config-load repro for `runtime.watchdog_bootstrap_first_progress_timeout_seconds`

## Required docs and examples

- root authority docs
- current front-door routers
- current dispatch/manifest/watchdog/launch/CLI contrast pages
- the canonical local config owner page as follow-up routing evidence only

## Exit evidence

- evidence expected under `../evidence/phase-0-redesign-truth-and-current-drift-canon-fix.md`
- review expected under `../reviews/phase-0-redesign-truth-and-current-drift-canon-fix.md`

## Rollback or stop conditions

- stop if truthful repair requires runtime-code edits rather than doc changes
- stop if redesign owner docs would need reinterpretation rather than authority reinforcement
- stop if a required current-doc repair falls outside the Phase 0 current-doc unlock

## Cross-links

- evidence artifact: `../evidence/phase-0-redesign-truth-and-current-drift-canon-fix.md`
- review artifact: `../reviews/phase-0-redesign-truth-and-current-drift-canon-fix.md`
