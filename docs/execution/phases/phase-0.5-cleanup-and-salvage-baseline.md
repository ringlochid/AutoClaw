# Phase 0.5 total code hard reset baseline

Status: Target

This phase succeeds only if it TOTALLY resets the code before redesign
implementation continues into Phase 1.

It exists to delete or reset the current implementation so later phases rebuild
from a hard gate instead of inheriting partially trusted code.

This is not for docs change.

Don't change the docs.

It explicitly commits the project to:

- total code-level reset of the current baseline inside the Phase 0.5 boundary
- remove any current-code surface that is ambiguous, suspicious, stale, or only
  incidentally useful to keep
- no current-code surface in the phase boundary survives unchanged on trust
- fresh-baseline DB/state reset
- no carried migration history or reset-only schema survives as redesign authority
- stale-contract test deletion, with rewrite allowed only for the minimum reset
  proof that later phases need
- plugin near-greenfield rebuild from a target-only skeleton

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Current workspace note

- this checkout exposes backend, console, definitions, packaging, and scripts at repo-root paths such as `apps/api`, `apps/console`, `definitions`, `scripts`, `pyproject.toml`, and `Makefile`
- some execution surfaces still use historical `autoclaw-main/...` labels; Phase 0.5 owned docs must normalize those references to the repo-root layout without widening into a Phase 0 file-lock rewrite
- no `autoclaw-bridge-plugin-main/...` source tree is present in this checkout; plugin cleanup inventory is docs-driven and Phase 4B begins from a target-only rebuild boundary

## Primary redesign pages

- [API surface and trust-lane map](../../redesign/interfaces/api-surface-and-trust-lane-map.md)
- [Plugin tool reference](../../redesign/interfaces/plugin-tool-reference.md)
- [Human and operator control surface](../../redesign/interfaces/human-and-operator-control-surface.md)
- [Workflow definition schema](../../redesign/workflows/workflow-definition-schema.md)

## Supporting execution maps

- [Current schema, route, and plugin migration appendix](../maps/current-schema-route-and-plugin-migration-appendix.md)
- [Repo salvage matrix](../maps/repo-salvage-matrix.md)

## Exhaustive appendix owners

- [API schema appendix](../../redesign/interfaces/api-schema-appendix.md)
- [Workflow schema appendix](../../redesign/workflows/workflow-schema-appendix.md)
- [Prompt resource and usage appendix](../../redesign/prompt-layer/prompt-resource-usage-appendix.md)

## Implementation surfaces

- owned work is destructive reset of code, schema, DB state, and
  test surfaces needed to establish the new baseline
- docs are out of scope for implementation in this phase
- this is not for docs change
- don't change the docs
- if docs work seems necessary, stop and route that work to Phase 0 instead of
  broadening Phase 0.5
- allowed collateral surfaces: none as implementation deliverables; execution
  docs are reference inputs, not the work product

## Hard gate

- default action: remove or reset current code inside the phase boundary
- no surface survives because it looks useful, familiar, or high quality
- any survivor must be fully reset; nothing current survives unchanged
- if a surface is ambiguous, suspicious, or target-incompatible, delete it

## Do not edit / defer surfaces

- docs-only cleanup or wording churn that is not required to land the code reset
- any docs change treated as Phase 0.5 implementation progress
- target implementation rewrites beyond bounded reset or
  plugin-skeleton smoke fixes
- soft-salvage decisions that keep current code around pending later judgment
- redesign owner pages unless cleanup canon is genuinely incomplete

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- in this phase, subagents are optional and should stay limited to subsystem inventory, stale-test inventory, or plugin-boundary inventory
- the parent agent owns hard-reset decisions, removal authority, and the narrow
  allowlist for any surviving infra shell

## Wave integration loop

1. inspect the current code or test slice against canon
2. decide `no subagents` or brief bounded subagents inventory slices
3. remove or reset the slice by default; no current surface survives unchanged
4. if the slice appears to require docs work, stop and route that blocker to
   Phase 0
5. verify that no ambiguous or suspicious survivor remains and that reset,
   test, or plugin consequences are explicit
6. rerun the relevant validation and smoke evidence checks before another wave

## Phase purpose

Totally reset the current repo for future implementation by deleting or
resetting stale code paths, reset history, test families, and plugin survivors
before the rewrite begins.

## Success criteria

- all current code in the phase boundary is deleted or reset
- no current-code survivor remains unchanged in the phase boundary
- reset expectations are explicit
- stale contract tests are deleted or minimally replaced intentionally
- plugin rebuild is bounded as target-only and near-greenfield
- Phase 0.5 completion does not depend on docs edits

## Deliverables

- totally reset current-repo code baseline
- explicit reset baseline and plugin boundary
- explicit stale-test routing

## Milestones

- current-repo hard-reset sweep complete
- stale-test classification complete
- empty DB baseline complete
- plugin boundary complete

## Ordered work packages

### `P0.5-WP1`

- objective: inspect every major current-repo code family and hard-reset it by
  default so later implementation inherits a clean baseline instead of a
  salvage decision tree
- owned surfaces: the affected code families
- dependencies: none
- test-first requirement: none
- docs/update requirement: none; if docs changes appear necessary, route that
  blocker to Phase 0
- subagent allowed: yes
- closeout evidence: no current-code survivor remains unchanged

### `P0.5-WP2`

- objective: freeze the fresh-baseline DB reset strategy for the reset
  current-repo baseline without carried schema history or reset-only tables
- owned surfaces: DB/reset code paths
- dependencies: `P0.5-WP1`
- test-first requirement: DB reset smoke evidence path named
- docs/update requirement: none; if docs changes appear necessary, route that
  blocker to Phase 0
- subagent allowed: yes
- closeout evidence: reset path is explicit and leaves no carried schema history

### `P0.5-WP3`

- objective: delete stale tests by default and rewrite only the minimum infra
  smoke coverage needed so future implementation does not inherit misleading
  coverage
- owned surfaces: the affected test suites
- dependencies: `P0.5-WP1`
- test-first requirement: retained infra tests must still prove useful behavior
- docs/update requirement: none; if docs changes appear necessary, route that
  blocker to Phase 0
- subagent allowed: yes
- closeout evidence: no stale-contract family survives by convenience

### `P0.5-WP4`

- objective: freeze the plugin rebuild boundary as part of the reset
  current-repo baseline
- owned surfaces: any surviving plugin-facing code or harness surfaces
- dependencies: `P0.5-WP1`
- test-first requirement: target tool inventory defined from canon first
- docs/update requirement: none; if docs changes appear necessary, route that
  blocker to Phase 0
- subagent allowed: yes
- closeout evidence: no plugin survivor remains without explicit hard-reset
  justification

## Mandatory checklist

- [Cleanup and salvage checklist](../gates/cleanup-and-salvage-checklist.md)
- [ ] code reset, not docs cleanup, is the implementation center of gravity
- [ ] the hard gate removed or reset every ambiguous or suspicious survivor
- [ ] no subsystem, test family, or plugin surface survives on apparent quality
      alone
- [ ] success means total code reset, not partial salvage plus docs alignment
- [ ] reset and plugin-boundary consequences are explicit enough for later phases

## Required tests

- keep and rerun redesign-agnostic infra tests for config, package entrypoints, install, and health where still applicable
- rewrite or delete old contract tests for old task-start/task-upload, old `/flows/*`, old registry/skill/approval behavior, and old plugin tool families
- add smoke coverage that the DB reset path and plugin skeleton boundary are viable enough for later phases

## Required docs/examples

- none; docs changes belong to Phase 0, not Phase 0.5

## Candidate delegated slices

- subsystem classification only
- stale-test inventory only
- plugin boundary inventory only

## Exit evidence

- completed cleanup checklist
- explicit removed-or-reset surfaces
- proof that no current-code surface in the phase boundary survived unchanged
- explicit reset evidence requirements

## Reset criteria

- the reset gate is mandatory in this phase
- DB reset and rerun validation are required outputs of this phase rather than
  deferred release work
- Phase 0.5 must not leave any carried migration history, packaged migration
  mirror, or reset-only schema table acting as redesign authority

## Kill-list terms

- compatibility-minded migration of redesign-incompatible target schema
- keeping old target-facing tables alive for convenience
- keeping current code because it looks good, clean, or maybe reusable later
- leaving current code partially reset and trying to close the phase with docs
- preserving stale contract tests for convenience
- plugin cleanup-in-place that keeps old approval/skill/raw-slice tool families alive
- treating Phase 0.5 as a docs-only cleanup pass
- vague keep/delete decisions with no owning later phase
