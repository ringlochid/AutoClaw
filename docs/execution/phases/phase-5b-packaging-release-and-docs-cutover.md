# Phase 5B packaging, release, and docs cutover

Status: Target

This phase lands packaging, install/reset/release behavior, final docs cutover, and stale canonical-doc cleanup.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary redesign pages

- [Testing and release checklist](../../redesign/interfaces/testing-and-release-checklist.md)
- [Release and install strategy](../../redesign/interfaces/release-and-install-strategy.md)
- [CLI surface and operator workflows](../../redesign/interfaces/cli-surface-and-operator-workflows.md)

## Required supporting redesign reads

- [Interfaces front door](../../redesign/interfaces/README.md)
- [MCP, plugin, and CLI boundary](../../redesign/interfaces/mcp-plugin-and-cli-boundary.md)
- [CLI, API, and package shape](../../redesign/interfaces/cli-api-and-package-shape.md)
- [How-to guides](../../redesign/how-to/README.md)
- [Install and onboard](../../redesign/how-to/install-and-onboard.md)
- [Publish a release](../../redesign/how-to/publish-a-release.md)
- [Tutorials](../../redesign/tutorials/README.md)
- [Onboard locally](../../redesign/tutorials/onboard-locally.md)
- [End-to-end redesign walkthrough](../../redesign/tutorials/end-to-end-redesign-walkthrough.md)

## Required current contrast reads

- [CLI surface and config precedence](../../current/interfaces/cli-surface-and-config-precedence.md)
- [Packaging CLI and install](../../current/interfaces/packaging-cli-and-install.md)
- [Install and start local](../../current/operations/install-and-start-local.md)
- [Verify current install and runtime](../../current/operations/verify-current-install-and-runtime.md)
- [Run the current Docker and Postgres verification lane](../../current/operations/run-docker-postgres-verification.md)

## Required examples and diagrams

- [Distribution and database support matrix](../../redesign/interfaces/distribution-and-database-support-matrix.md)
- the release architecture mermaid diagram in [Release and install strategy](../../redesign/interfaces/release-and-install-strategy.md)
- [Use Postgres in the redesign target](../../redesign/how-to/use-postgres.md)
- [Run the redesign target on local SQLite](../../redesign/how-to/run-local-sqlite.md)

## Exhaustive appendix owners

- [API schema appendix](../../redesign/interfaces/api-schema-appendix.md) when package or reset behavior changes public examples

## Implementation surfaces

- owned surfaces: `pyproject.toml`, `Makefile`, `scripts/*`, install/release/onboarding docs, root/router docs that must point to the final canonical surfaces, and archive cleanup under `docs/archive/*`
- allowed collateral surfaces: CLI docs and examples when package or reset behavior changes their invocation story, and current/router pages when cutover must point them cleanly back to canon

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

Finish the install or release story and cut the docs over so implementers can work from canonical surfaces only without relying on stale packs, with the OpenClaw lifecycle, tool-surface vocabulary, and CLI output rules frozen in the install or onboarding docs.

## Success criteria

- package/install/reset behavior is explicit and test-backed
- release and onboarding docs match the shipped package behavior
- install and onboarding docs teach the minimal path, direct setup path, and subset re-entry path without using `bootstrap` as the primary public noun
- onboarding docs keep `check`, `setup`, `onboard`, `configure`, and `doctor` in their approved roles and preserve the warning-first OpenClaw tone
- CLI docs keep `--json` as output-shape only, `--non-interactive` as the automation switch, rich styling as TTY-only, and the copied OpenClaw lobster-palette, section-and-panel visual grammar
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
- documentation update requirement: install and reset docs update in the same phase
- subagent allowed: yes
- closeout evidence: package and reset behavior are explicit and reproducible

### `P5B-WP2`

- objective: align release, onboarding, and final canonical routing, including the minimal path and subset re-entry docs lock
- owned surfaces: release docs, onboarding docs, root/router pages
- dependencies: `P5B-WP1`
- test-first requirement: docs routing and link checks
- documentation update requirement: onboarding and release routes point only to canonical surfaces
- subagent allowed: yes
- closeout evidence: root and canonical docs point implementers to the final surfaces only and teach the approved lifecycle nouns and output rules

### `P5B-WP3`

- objective: archive stale guidance and complete docs cutover
- owned surfaces: `docs/archive/*` and stale canonical-doc references
- dependencies: `P5B-WP2`
- test-first requirement: docs consistency and validation checks
- documentation update requirement: old packs no longer teach target behavior as live canon
- subagent allowed: yes
- closeout evidence: no stale cutover gap remains in canonical routing

## Mandatory checklist

- [ ] package, install, reset, release, and onboarding docs match the landed behavior
- [ ] install and onboarding docs teach both the minimal path and subset re-entry path with the approved OpenClaw command roles
- [ ] `bootstrap` is not taught as the primary public onboarding noun and `plugin` stays adapter or wrapper terminology only
- [ ] CLI output rules stay locked at a high level: `--json`, `--non-interactive`, TTY-only styling, and `--plain` or `--no-color` or `NO_COLOR`
- [ ] CLI and onboarding docs lock the copied OpenClaw visual grammar: high-contrast terminal presentation, accent section headings, framed warning/status panels, and dense aligned diagnostics
- [ ] canonical routers point implementers to the final live surfaces only
- [ ] stale docs were archived or de-routed intentionally rather than left as shadow canon
- [ ] any subagents slice stayed inside its package/install, release-docs, or cutover ownership

## Required tests

- package, install, and reset smoke checks
- docs routing and validation checks
- all currently-viable minimal, normal, and maximal e2e lanes when packaging or reset changes can invalidate prior evidence
- SQLite local smoke verification
- Postgres + Docker strong verification

## Required docs and examples

- release/install docs
- onboarding examples
- archive routing and cutover docs
- required examples and diagrams named above

## Candidate delegated slices

- package/install slice
- release-docs slice
- docs cutover and archive cleanup slice

## Exit evidence

- packaging and release docs match install and reset behavior
- canonical docs route implementers to the final surfaces only
- install and onboarding docs teach the approved OpenClaw lifecycle and CLI output and visual rules
- stale guidance no longer survives as live canonical routing
- SQLite and Postgres package lanes are proven or explicitly blocked with an exact phase-bounded reason

## Reset criteria

- the reset gate is mandatory in this phase

## Kill-list terms

- package or install ambiguity
- docs cutover gaps that still force implementers into old packs
- `bootstrap` taught as the primary public onboarding noun
- install or onboarding docs that blur `setup`, `onboard`, `configure`, and `doctor`
- stale archive or router surfaces teaching live target behavior
