# Phase 0 Design Truth And Current Drift Canon-Fix Review

Status: Reference

selected phase: Phase 0
current phase page: docs-internal/execution/v1/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP1, P0-WP2, P0-WP3
summary-only: no
delegated slices: none

## Slice identity

- work package or slice: design-truth authority lock plus current-drift doc repair
- date: 2026-05-21

## Phase-local contract

- current phase page: `docs-internal/execution/v1/phases/phase-0-docs-contract-freeze-and-setup.md`
- implementation file lock map: `docs-internal/execution/v1/maps/file-priority-map.md`

## Scope

- reviewed plan: `../plans/phase-0-design-truth-and-current-drift-canon-fix.md`
- reviewed evidence: `../evidence/phase-0-design-truth-and-current-drift-canon-fix.md`

## Verdict

- pass/fail: pass
- summary: the slice now teaches design-first authority in root canon and front-door routing, rewrites routed current docs so they stop teaching live dispatch `bootstrap | execution` and manifest-ack behaviour as canonical truth, truthfully records the shipped `POST /tasks/start` route, and captures the still-open runtime config mismatch as a later Phase 4B code follow-up rather than a lost docs note.

## Findings

- root canon needs one explicit design-first source-of-truth rule rather than relying on read order alone
- routed current docs were teaching legacy dispatch `bootstrap | execution`, manifest-ack vocabulary, and one stale launch-route claim as if they were live truth
- the docs-freeze validator exposed a genuine Phase 0 unlock gap for routed current-doc repairs, so this slice also patched the Phase 0 page and docs-freeze rule file to allow the exact current-doc surfaces needed for truthful stale-wording cleanup
- follow-up debt: the known runtime config mismatch on `watchdog_bootstrap_first_progress_timeout_seconds` remains later Phase 4B code work in `apps/api/app/config.py`; this slice records the drift but does not treat it as a Phase 0 implementation task

## Delegated-slice compliance

- `no subagents`
- owned-surface compliance: pass
- review-only compliance: not applicable
- wave integration proof: parent-only docs slice
- authoritative proof link: `../evidence/phase-0-design-truth-and-current-drift-canon-fix.md`

## Proof lanes relied on

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- `./.venv/bin/ruff check scripts/docs`
- `./.venv/bin/mypy scripts/docs`
- focused repo searches over the stale drift terms
- direct config-load repro for the design watchdog knob mismatch

## Stale-logic search proof

- commands or search terms: `bootstrap shape`, `execution shape`, `manifest to acknowledge`, `ack their manifest`, `not a public HTTP route`, `wait_for_response=true`, `Init and local bootstrap`
- outcome: all targeted stale markers were removed from the routed current surfaces; the only remaining match from the focused search is `docs-internal/current/v1/architecture/watchdog-and-runtime-monitoring.md:17` because the generic heading `## Current execution shape` still contains the words `execution shape` without teaching a dispatch-phase contract

## Kill-list proof

- phase kill-list source: `docs-internal/execution/v1/phases/phase-0-docs-contract-freeze-and-setup.md`
- terms checked: split authority, stale-path cleanup outside the Phase 0 unlock, and overlapping ownership
- outcome: satisfied; the slice stayed inside Phase 0-owned or allowed-collateral surfaces, and the validator unlock repair was landed in the owning Phase 0 page plus docs-freeze rules instead of being left as an undocumented exception

## Docs answer-sourcing proof

- design owners relied on:
  - `docs-internal/design/v1/architecture/runtime-boundary-and-controller-loop-contract.md`
  - `docs-internal/design/v1/architecture/manifest-contract.md`
  - `docs-internal/design/v1/architecture/openclaw-session-lifecycle.md`
  - `docs-internal/design/v1/architecture/openclaw-continuity-and-send-modes.md`
  - `docs-internal/design/v1/workflows/compiler-contract-and-launch-materialization.md`
  - `docs-internal/design/v1/how-to/install-and-onboard.md`
- supporting design reads or appendix owners relied on:
  - `docs-internal/design/v1/README.md`
  - `docs-internal/design/v1/architecture/runtime-records-and-lifecycle.md`
  - `docs-internal/design/v1/architecture/runtime-database-and-object-contract.md`
- current-contrast pages relied on:
  - the named routed current pages patched in this slice
- code or tests inspected:
  - `apps/api/app/api/routes/tasks.py`
  - `apps/api/app/registry/task_start.py`
  - `apps/api/app/runtime/launch/service.py`
  - `apps/api/app/config.py`
- canon gap or explicit `none`: none

## Phase-bounded STYLE exceptions

- none

## Reset-gate outcome

- not applicable

## Remaining exact blockers

- none

## Cross-links

- aggregate historical summary, if any: none
- companion exceptions page, if any: none
