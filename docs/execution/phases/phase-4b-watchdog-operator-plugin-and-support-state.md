# Phase 4B watchdog, operator MCP, node MCP, and support-state lanes

Status: Target

This phase lands watchdog recovery, external operator MCP and node MCP surface
exposure, OpenClaw package/profile attachment proof, and exact support-state
readback shapes.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary redesign pages

- [Watchdog and recovery contract](../../redesign/architecture/watchdog-and-recovery-contract.md)
- [Runtime observability and boundary log](../../redesign/architecture/runtime-observability-and-boundary-log.md)
- [MCP, plugin, and CLI boundary](../../redesign/interfaces/mcp-plugin-and-cli-boundary.md)
- [MCP tool reference](../../redesign/interfaces/plugin-tool-reference.md)
- [Human and operator control surface](../../redesign/interfaces/human-and-operator-control-surface.md)
- [Runtime database and object contract](../../redesign/architecture/runtime-database-and-object-contract.md)

## Exhaustive appendix owners

- [API schema appendix](../../redesign/interfaces/api-schema-appendix.md)
- [Prompt resource and usage appendix](../../redesign/prompt-layer/prompt-resource-usage-appendix.md)

## Supporting routing pages

- [Runtime monitoring and watchdog automation](../../redesign/architecture/runtime-monitoring-and-watchdog-automation.md)

## Required supporting redesign reads

- [Runtime lane separation rationale](../../redesign/architecture/runtime-lane-separation-rationale.md)
- [Provider, worker, and operator boundary](../../redesign/architecture/provider-worker-and-operator-boundary.md)
- [Watchdog and provider recovery](../../redesign/architecture/watchdog-and-provider-recovery.md)
- [Operator definition and role boundary](../../redesign/interfaces/operator-definition-and-role-boundary.md)
- [Guarded registry and runtime writes](../../redesign/interfaces/guarded-registry-and-runtime-writes.md)
- [ADR-0004 OpenClaw adapter normalization and worker transport boundary](../../redesign/decisions/ADR-0004-openclaw-adapter-normalization-and-worker-transport-boundary.md)
- [Debug a stalled node](../../redesign/how-to/debug-a-stalled-node.md)
- [Recover a provider session](../../redesign/how-to/recover-a-provider-session.md)

## Required current contrast reads

- [Watchdog and runtime monitoring](../../current/architecture/watchdog-and-runtime-monitoring.md)
- [Watchdog and OpenClaw bridge](../../current/architecture/watchdog-and-openclaw-bridge.md)
- [Use the current OpenClaw bridge plugin](../../current/operations/use-the-openclaw-bridge-plugin.md)
- [API surface and route map](../../current/interfaces/api-surface-and-route-map.md)
- [API trust lanes](../../current/interfaces/api-trust-lanes.md)

## Implementation surfaces

- owned surfaces: watchdog and monitor services under `apps/api/app/runtime/`,
  the repo-local OpenClaw package or parity-wrapper tree under
  `apps/api/autoclaw/openclaw/**` created during Phase 4B from a target-only
  rebuild boundary, and the operator MCP/node MCP/support-state owner docs
  including the Phase 4B MCP boundary front door
- allowed collateral surfaces: runtime database or observability docs, API
  appendix pages, narrow OpenClaw dispatch read models required for watchdog or
  operator evidence, `apps/api/app/config.py` and `apps/api/app/main.py` when
  watchdog or MCP wrapper wiring needs canonical runtime config loading or
  lifespan startup wiring, narrow package metadata surfaces when the
  repo-local wrapper needs one explicit MCP-server dependency, the canonical
  local config owner page when watchdog or OpenClaw tunables are introduced or
  renamed, the already-legalized shared Phase 3 node-operation and
  runtime-write seam under `apps/api/app/runtime/control/node_operations.py`
  and `apps/api/app/runtime/effects/writes.py` when Phase 4B must reuse the
  same callback authority and commit/effect boundary instead of duplicating
  them, the selected Phase 4B plan, evidence, and review artifacts under
  `docs/execution/plans/`, `docs/execution/evidence/`, and
  `docs/execution/reviews/`, and the route-map or architecture owners that
  must align the new MCP boundary wording without widening into Phase 5 public
  noun ownership

## Do not edit / defer surfaces

- gateway/session core semantics except follow-on fixes discovered through watchdog work
- public ingest/API/CLI and packaging/release surfaces

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- subagents are useful here for watchdog logic, operator MCP/node MCP
  behavior, or support-state schema/example slices
- the parent agent owns final MCP boundary interpretation, watchdog recovery
  semantics, and support-state freeze decisions

## Wave integration loop

1. lock the current watchdog/operator work package against the phase page and file lock map
2. decide `no subagents` or brief the bounded subagents slices
3. integrate the returned watchdog, MCP wrapper, operator, and docs changes
4. run watchdog/operator MCP/node MCP tests plus support-state schema or
   example verification
5. review findings and patch before another wave

## Phase purpose

Make watchdog recovery, external operator MCP and node MCP surface exposure,
OpenClaw package/profile attachment, and support-state observability explicit
enough to preserve bounded operator scope and prevent support-state files from
becoming implicit controller truth.

## Success criteria

- watchdog and recovery behavior match canon
- worker lane, operator lane, and support tooling stay distinct
- `operator MCP` and `node MCP` inventories, forbidden overlaps, and
  OpenClaw-profile separation proof are explicit
- OpenClaw profile config follows fail-closed allowlist practice instead of
  broad inherited tool profiles
- exact support-state readback shapes for `delivery-state.json`,
  `continuity-state.json`, `watchdog-state.json`, and
  `provider-events.ndjson` are frozen and clearly support-only
- Phase 4B closes on the runtime, operator, and support subset only; the
  definition-registry and task-start extensions to `operator MCP` remain
  Phase 5A-owned

## Deliverables

- watchdog and recovery alignment
- operator MCP/node MCP lane alignment
- OpenClaw package/profile attachment and separation proof
- exact support-state readback contracts

## Milestones

- watchdog model aligned
- operator MCP/node MCP lane aligned
- package/profile attachment proof aligned
- support-state readback shapes frozen

## Ordered work packages

### `P4B-WP1`

- objective: align watchdog detection, wake, retry, and recovery semantics
- owned surfaces: watchdog services and recovery owner docs
- dependencies: Phase 4A complete
- test-first requirement: watchdog gap-revealing tests
- documentation update requirement: watchdog recovery rules remain exact
- subagent allowed: yes
- closeout evidence: watchdog behavior matches canon

### `P4B-WP2`

- objective: align operator MCP/node MCP scope, tool inventory, forbidden
  overlaps, and OpenClaw package/profile attachment proof without widening
  into Phase 5A definition-registry or task-start ownership
- owned surfaces: OpenClaw package or parity-wrapper source, plugin tool
  reference, the MCP boundary front door, and operator control docs
- dependencies: `P4B-WP1`
- test-first requirement: operator MCP/node MCP integration tests
- documentation update requirement: MCP scope, transport, and runtime-effective separation proof remain explicit and bounded
- documentation update requirement: exact allowlist and deny-list profile
  practice remains explicit and bounded
- subagent allowed: yes
- closeout evidence: no stale worker/operator or mixed-MCP assumptions remain

### `P4B-WP3`

- objective: freeze support-state readback shapes and examples
- owned surfaces: runtime observability docs, support-state docs, example payloads
- dependencies: `P4B-WP1`, `P4B-WP2`
- test-first requirement: schema or example-shape verification
- documentation update requirement: exact field sets, meanings, and example
  payloads remain explicit for `delivery-state.json`,
  `continuity-state.json`, `watchdog-state.json`, and
  `provider-events.ndjson`
- subagent allowed: yes
- closeout evidence: implementers no longer infer support-state readbacks from prose alone

## Mandatory checklist

- [ ] watchdog recovery rules are explicit and test-backed
- [ ] operator MCP and node MCP docs stay bounded and distinct from worker-lane
      behavior
- [ ] package/profile attachment rules and runtime-effective separation proof
      are explicit; config writes alone are not treated as success
- [ ] when a repo-local OpenClaw profile tree lands, that profile wiring uses fail-closed `tools.allow` practice, and any profile that must not see MCP tools denies `bundle-mcp` explicitly; otherwise the landed wrapper path still proves separation through an equivalent live runtime inventory read
- [ ] configurable watchdog or OpenClaw wrapper/runtime knobs are routed to the
      canonical local `config.toml` owner page rather than copied as free
      inline config blocks
- [ ] definition discovery, guarded upload, and task-start parity on
      `operator MCP` remain Phase 5A-owned and are not Phase 4B exit
      requirements
- [ ] `delivery-state.json`, `continuity-state.json`,
      `watchdog-state.json`, and `provider-events.ndjson` are frozen as
      support-only readbacks rather than implicit controller truth
- [ ] any subagents slice stayed inside its watchdog, MCP, or support-state
      ownership

## Required tests

- watchdog and recovery integration tests
- operator MCP/node MCP integration tests
- OpenClaw profile or session verification proof, such as `tools.effective` or
  the equivalent runtime inventory read, showing no mixed MCP catalog
- OpenClaw security posture proof, such as `openclaw security audit --deep`,
  when the repo-local package/profile tree lands or changes; environment-scoped findings must stay separated from repo-code blockers
- support-state schema or example verification for `delivery-state.json`,
  `continuity-state.json`, `watchdog-state.json`, and
  `provider-events.ndjson`
- currently viable minimal, normal, and maximal e2e lanes

## Required examples and diagrams

- watchdog and observability diagrams in
  [Runtime monitoring and watchdog automation](../../redesign/architecture/runtime-monitoring-and-watchdog-automation.md),
  [Runtime observability and boundary log](../../redesign/architecture/runtime-observability-and-boundary-log.md),
  and [Watchdog and recovery contract](../../redesign/architecture/watchdog-and-recovery-contract.md)
- operator control examples in
  [Human and operator control surface](../../redesign/interfaces/human-and-operator-control-surface.md)
- MCP tool inventory examples in
  [MCP tool reference](../../redesign/interfaces/plugin-tool-reference.md)
- support-state readback examples frozen in the phase-owned observability docs

## Required docs and examples

- watchdog and recovery docs
- operator MCP/node MCP docs
- support-state readback examples
- required examples and diagrams named above

## Candidate delegated slices

- watchdog logic slice
- operator MCP/node MCP slice
- support-state schema/example slice

## Exit evidence

- watchdog, operator MCP/node MCP, and support-state docs match landed
  behavior
- operator and node MCP separation is proven through live runtime evidence, not
  config-only bootstrap output
- exact `delivery-state.json`, `continuity-state.json`,
  `watchdog-state.json`, and `provider-events.ndjson` examples are frozen and
  explicitly support-only
- the selected Phase 4B plan, evidence, and review artifacts remain the only
  closeout authority for this phase; there is no blended Phase 4 closure record
- no stale raw transport state or mixed shared MCP assumptions are treated as
  controller truth

## Reset criteria

- apply the reset gate if runtime persistence, support-state readback
  contracts, OpenClaw package or parity-wrapper capability surface, or public
  operator surface changes in a breaking way

## Kill-list terms

- raw transport state treated as controller truth
- mixed worker and operator lane assumptions
- mixed node and operator MCP sessions
- config-only “success” without live compatibility proof
- plugin-first truth ownership
- support-state readbacks inferred from prose alone
