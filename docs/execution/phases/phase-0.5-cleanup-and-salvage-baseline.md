# Phase 0.5 cleanup and salvage baseline

Status: Target

This phase establishes the cleanup baseline before redesign implementation continues into Phase 1.

It explicitly commits the project to:

- fresh-baseline DB/schema reset
- one new redesign baseline migration replacing current authoritative history
- plugin near-greenfield rebuild from a target-only skeleton

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary redesign pages

- [API surface and trust-lane map](../../redesign/interfaces/api-surface-and-trust-lane-map.md)
- [API schema appendix](../../redesign/interfaces/api-schema-appendix.md)
- [Plugin tool reference](../../redesign/interfaces/plugin-tool-reference.md)
- [Workflow schema appendix](../../redesign/workflows/workflow-schema-appendix.md)
- [Prompt resource and usage appendix](../../redesign/prompt-layer/prompt-resource-usage-appendix.md)
- [Current schema, route, and plugin migration appendix](../maps/current-schema-route-and-plugin-migration-appendix.md)

## Exhaustive appendix owners

- [API schema appendix](../../redesign/interfaces/api-schema-appendix.md)
- [Workflow schema appendix](../../redesign/workflows/workflow-schema-appendix.md)
- [Prompt resource and usage appendix](../../redesign/prompt-layer/prompt-resource-usage-appendix.md)
- [Repo salvage matrix](../maps/repo-salvage-matrix.md)

## Implementation surfaces

- owned surfaces: salvage matrix, cleanup checklist, reset and cleanup how-to pages, migration appendix references, and test or plugin inventory docs
- allowed collateral surfaces: execution routers and root/router pages that must reflect the cleanup baseline

## Do not edit / defer surfaces

- target implementation rewrites beyond narrow reset, reseed, bootstrap, or plugin-skeleton smoke fixes
- redesign owner pages unless cleanup canon is genuinely incomplete

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- in this phase, subagents are optional and should stay limited to subsystem inventory, stale-test inventory, or plugin-boundary inventory
- the parent agent owns keep/rewrite/delete/quarantine decisions, reset authority, and final salvage dispositions

## Wave integration loop

1. classify the current inventory slice against canon
2. decide `no subagents` or brief bounded subagents inventory slices
3. integrate the returned classifications into the salvage matrix or checklist
4. verify that no ambiguous bucket remains and that reset or plugin consequences are explicit
5. rerun the relevant docs validation and smoke evidence checks before another wave

## Phase purpose

Freeze what is kept, rewritten, deleted, or quarantined before the rewrite begins, and make reset/plugin/test strategy explicit instead of incidental.

## Success criteria

- every major subsystem has an intentional salvage disposition
- reset/reseed/bootstrap expectations are explicit
- stale contract tests are classified intentionally
- plugin rebuild is bounded as target-only and near-greenfield

## Deliverables

- completed salvage matrix
- completed cleanup checklist
- explicit reset baseline and plugin boundary
- explicit stale-test routing

## Milestones

- subsystem classification complete
- stale-test classification complete
- reset baseline complete
- plugin boundary complete

## Ordered work packages

### `P0.5-WP1`

- objective: classify every major subsystem into keep, rewrite in place, delete, quarantine support-only, or plugin rebuild
- owned surfaces: salvage matrix and cleanup checklist
- dependencies: none
- test-first requirement: none
- docs/update requirement: disposition and owning later phase must be recorded
- subagent allowed: yes
- closeout evidence: no ambiguous subsystem bucket remains

### `P0.5-WP2`

- objective: freeze the fresh-baseline reset and reseed strategy
- owned surfaces: phase page, checklist, reset how-to, migration appendix references
- dependencies: `P0.5-WP1`
- test-first requirement: reset/reseed smoke evidence path named
- docs/update requirement: DB reset, reseed, and rerun validation procedures
- subagent allowed: yes
- closeout evidence: one redesign baseline migration strategy is explicit

### `P0.5-WP3`

- objective: classify stale tests into keep, small edit, rewrite, or delete
- owned surfaces: tests inventory docs and related execution guidance
- dependencies: `P0.5-WP1`
- test-first requirement: retained infra tests must still prove useful behavior
- docs/update requirement: stale task-start, flows/operator, registry/skill/approval, and plugin tests explicitly called out
- subagent allowed: yes
- closeout evidence: no stale-contract family remains unclassified

### `P0.5-WP4`

- objective: freeze the plugin rebuild boundary
- owned surfaces: plugin boundary docs and salvage matrix
- dependencies: `P0.5-WP1`
- test-first requirement: target tool inventory defined from canon first
- docs/update requirement: reusable plugin utilities are explicitly kept or removed
- subagent allowed: yes
- closeout evidence: no ambiguous plugin cleanup-in-place path remains

## Mandatory checklist

- [Cleanup and salvage checklist](../gates/cleanup-and-salvage-checklist.md)
- [ ] the implementation file lock map and the phase page agree on cleanup ownership
- [ ] no subsystem, test family, or plugin surface remains in a vague bucket
- [ ] reset, reseed, bootstrap, and plugin-boundary consequences are explicit enough for later phases

## Required tests

- keep and rerun redesign-agnostic infra tests for config, package entrypoints, install/bootstrap, and health where still applicable
- rewrite or delete old contract tests for old task-start/task-upload, old `/flows/*`, old registry/skill/approval behavior, and old plugin tool families
- add smoke coverage that the new baseline migration, reset, reseed, and plugin skeleton are viable enough for later phases

## Required docs/examples

- salvage matrix
- cleanup checklist
- reset, reseed, and plugin-boundary guidance

## Candidate delegated slices

- subsystem classification only
- stale-test inventory only
- plugin boundary inventory only

## Exit evidence

- completed cleanup checklist
- named keep/rewrite/delete/quarantine/plugin-rebuild decisions
- explicit reset and reseed evidence requirements

## Reset criteria

- the reset gate is mandatory in this phase
- DB reset, reseed/bootstrap, and rerun validation are required outputs of this phase rather than deferred release work

## Kill-list terms

- compatibility-minded migration of redesign-incompatible target schema
- keeping old target-facing tables alive for convenience
- preserving stale contract tests for convenience
- plugin cleanup-in-place that keeps old approval/skill/raw-slice tool families alive
- vague keep/delete decisions with no owning later phase
