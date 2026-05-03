# Phase 4B watchdog, operator, plugin, and support-state lanes

Status: Target

This phase lands watchdog recovery, operator or plugin lane behavior, and exact support-state readback shapes.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary redesign pages

- [Watchdog and recovery contract](../../redesign/architecture/watchdog-and-recovery-contract.md)
- [Runtime monitoring and watchdog automation](../../redesign/architecture/runtime-monitoring-and-watchdog-automation.md)
- [Runtime observability and boundary log](../../redesign/architecture/runtime-observability-and-boundary-log.md)
- [Plugin tool reference](../../redesign/interfaces/plugin-tool-reference.md)
- [Human and operator control surface](../../redesign/interfaces/human-and-operator-control-surface.md)
- [Runtime database and object contract](../../redesign/architecture/runtime-database-and-object-contract.md)

## Exhaustive appendix owners

- [API schema appendix](../../redesign/interfaces/api-schema-appendix.md)
- [Prompt resource and usage appendix](../../redesign/prompt-layer/prompt-resource-usage-appendix.md)

## Implementation surfaces

- owned surfaces: watchdog and monitor services under `autoclaw-main/apps/api/app/runtime/`, `autoclaw-bridge-plugin-main/src/*`, and the operator/plugin/support-state owner docs
- allowed collateral surfaces: runtime database or observability docs, API appendix pages, and narrow OpenClaw dispatch read models required for watchdog or operator evidence

## Do not edit / defer surfaces

- gateway/session core semantics except follow-on fixes discovered through watchdog work
- public ingest/API/CLI and packaging/release surfaces

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- subagents are useful here for watchdog logic, operator/plugin lane behavior, or support-state schema/example slices
- the parent agent owns final operator boundary interpretation, watchdog recovery semantics, and support-state freeze decisions

## Wave integration loop

1. lock the current watchdog/operator work package against the phase page and file lock map
2. decide `no subagents` or brief the bounded subagents slices
3. integrate the returned watchdog, plugin, operator, and docs changes
4. run watchdog/operator/plugin tests plus support-state schema or example verification
5. review findings and patch before another wave

## Phase purpose

Make watchdog recovery, operator tooling, and support-state observability explicit enough to preserve bounded operator scope and prevent support-state files from becoming implicit controller truth.

## Success criteria

- watchdog and recovery behavior match canon
- worker lane, operator lane, and support tooling stay distinct
- exact support-state readback shapes for `delivery-state.json`, `continuity-state.json`, and `watchdog-state.json` are frozen and clearly support-only

## Deliverables

- watchdog and recovery alignment
- operator/plugin lane alignment
- exact support-state readback contracts

## Milestones

- watchdog model aligned
- operator/plugin lane aligned
- support-state readback shapes frozen

## Ordered work packages

### `P4B-WP1`

- objective: align watchdog detection, wake, retry, and recovery semantics
- owned surfaces: watchdog services and recovery owner docs
- dependencies: Phase 4A complete
- test-first requirement: watchdog gap-revealing tests
- docs/update requirement: watchdog recovery rules remain exact
- subagent allowed: yes
- closeout evidence: watchdog behavior matches canon

### `P4B-WP2`

- objective: align operator/plugin lane scope and tool inventory
- owned surfaces: plugin source, plugin tool reference, operator control docs
- dependencies: `P4B-WP1`
- test-first requirement: operator/plugin integration tests
- docs/update requirement: operator/plugin scope remains explicit and bounded
- subagent allowed: yes
- closeout evidence: no stale worker/operator mixing remains

### `P4B-WP3`

- objective: freeze support-state readback shapes and examples
- owned surfaces: runtime observability docs, support-state docs, example payloads
- dependencies: `P4B-WP1`, `P4B-WP2`
- test-first requirement: schema or example-shape verification
- docs/update requirement: exact field sets, meanings, and example payloads remain explicit
- subagent allowed: yes
- closeout evidence: implementers no longer infer support-state readbacks from prose alone

## Mandatory checklist

- [ ] watchdog recovery rules are explicit and test-backed
- [ ] plugin and operator lane docs stay bounded and distinct from worker-lane behavior
- [ ] support-state files are frozen as support-only readbacks rather than implicit controller truth
- [ ] any subagents slice stayed inside its watchdog, operator/plugin, or support-state ownership

## Required tests

- watchdog and recovery integration tests
- operator/plugin integration tests
- support-state schema or example verification
- viable minimal, normal, and maximal e2e lanes

## Required docs/examples

- watchdog and recovery docs
- operator/plugin docs
- support-state readback examples

## Candidate delegated slices

- watchdog logic slice
- operator/plugin slice
- support-state schema/example slice

## Exit evidence

- watchdog, operator/plugin, and support-state docs match landed behavior
- exact support-state examples are frozen and explicitly support-only
- no stale raw transport state is treated as controller truth

## Reset criteria

- apply the reset gate if runtime persistence, support-state readback contracts, plugin capability surface, or public operator surface changes in a breaking way

## Kill-list terms

- raw transport state treated as controller truth
- mixed worker and operator lane assumptions
- support-state readbacks inferred from prose alone
