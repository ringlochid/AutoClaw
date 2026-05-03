# Phase 5B packaging, release, and docs cutover

Status: Target

This phase lands packaging, install/reset/release behavior, final docs cutover, and stale canonical-doc cleanup.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary redesign pages

- [Testing and release checklist](../../redesign/interfaces/testing-and-release-checklist.md)
- [Release and install strategy](../../redesign/interfaces/release-and-install-strategy.md)
- [CLI surface and operator workflows](../../redesign/interfaces/cli-surface-and-operator-workflows.md)

## Exhaustive appendix owners

- [API schema appendix](../../redesign/interfaces/api-schema-appendix.md) when package or reset behavior changes public examples

## Implementation surfaces

- owned surfaces: `pyproject.toml`, `Makefile`, `scripts/*`,
  install/release/onboarding docs, root/router docs that must point to the
  final canonical surfaces, and archive cleanup under `docs/archive/*`
- allowed collateral surfaces: CLI docs/examples when package or reset behavior changes their invocation story, and current/router pages when cutover must point them cleanly back to canon

## Do not edit / defer surfaces

- core runtime, compiler, gateway, watchdog, plugin, or public API semantics except doc corrections needed for cutover

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- subagents are useful here for package/install, release docs, or docs cutover and archive cleanup slices
- the parent agent owns final cutover decisions, package/reset interpretation, and canonical routing

## Wave integration loop

1. lock the current packaging/cutover work package against the phase page and file lock map
2. decide `no subagents` or brief the bounded subagents slices
3. integrate the returned packaging, docs, and archive changes
4. run package/install/reset smoke checks plus docs validators and link audits
5. review findings and patch before another wave

## Phase purpose

Finish the install/release story and cut the docs over so implementers can work from canonical surfaces only without relying on stale packs.

## Success criteria

- package/install/reset behavior is explicit and test-backed
- release and onboarding docs match the shipped package behavior
- stale guidance is removed or archived so canonical routing stays clean

## Deliverables

- package/install/reset alignment
- release and onboarding alignment
- final docs cutover and archive cleanup

## Milestones

- packaging and install behavior aligned
- release docs aligned
- docs cutover complete

## Ordered work packages

### `P5B-WP1`

- objective: align package, install, reset, and smoke-check behavior
- owned surfaces: package files, scripts, reset docs
- dependencies: `Phase 5A`
- test-first requirement: package/install/reset smoke checks
- docs/update requirement: install and reset docs update in the same phase
- subagent allowed: yes
- closeout evidence: package and reset behavior are explicit and reproducible

### `P5B-WP2`

- objective: align release, onboarding, and final canonical routing
- owned surfaces: release docs, onboarding docs, root/router pages
- dependencies: `P5B-WP1`
- test-first requirement: docs routing and link checks
- docs/update requirement: onboarding and release routes point only to canonical surfaces
- subagent allowed: yes
- closeout evidence: root and canonical docs point implementers to the final surfaces only

### `P5B-WP3`

- objective: archive stale guidance and complete docs cutover
- owned surfaces: `docs/archive/*` and stale canonical-doc references
- dependencies: `P5B-WP2`
- test-first requirement: docs consistency and validation checks
- docs/update requirement: old packs no longer teach target behavior as live canon
- subagent allowed: yes
- closeout evidence: no stale cutover gap remains in canonical routing

## Mandatory checklist

- [ ] package, install, reset, release, and onboarding docs match the landed behavior
- [ ] canonical routers point implementers to the final live surfaces only
- [ ] stale docs were archived or de-routed intentionally rather than left as shadow canon
- [ ] any subagents slice stayed inside its package/install, release-docs, or cutover ownership

## Required tests

- package, install, and reset smoke checks
- docs routing and validation checks
- all currently-viable minimal, normal, and maximal e2e lanes when packaging or reset changes can invalidate prior evidence

## Required docs/examples

- release/install docs
- onboarding examples
- archive routing and cutover docs

## Candidate delegated slices

- package/install slice
- release-docs slice
- docs cutover and archive cleanup slice

## Exit evidence

- packaging and release docs match install and reset behavior
- canonical docs route implementers to the final surfaces only
- stale guidance no longer survives as live canonical routing

## Reset criteria

- the reset gate is mandatory in this phase

## Kill-list terms

- package or install ambiguity
- docs cutover gaps that still force implementers into old packs
- stale archive or router surfaces teaching live target behavior
