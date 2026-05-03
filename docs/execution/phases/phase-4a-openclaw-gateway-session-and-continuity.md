# Phase 4A OpenClaw gateway, session, and continuity

Status: Target

This phase lands the OpenClaw-first gateway, session lifecycle, continuity, and worker-lane integration contract.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary redesign pages

- [Provider, worker, and operator boundary](../../redesign/architecture/provider-worker-and-operator-boundary.md)
- [OpenClaw worker and gateway contract](../../redesign/architecture/openclaw-worker-and-gateway-contract.md)
- [OpenClaw session lifecycle](../../redesign/architecture/openclaw-session-lifecycle.md)
- [OpenClaw continuity and send modes](../../redesign/architecture/openclaw-continuity-and-send-modes.md)
- [Runtime database and object contract](../../redesign/architecture/runtime-database-and-object-contract.md)
- [Provider direction and provider-native capabilities](../../redesign/workflows/provider-direction-and-provider-native-capabilities.md)

## Exhaustive appendix owners

- [API schema appendix](../../redesign/interfaces/api-schema-appendix.md)
- [Prompt resource and usage appendix](../../redesign/prompt-layer/prompt-resource-usage-appendix.md)

## Implementation surfaces

- owned surfaces: `apps/api/app/integrations/openclaw.py`,
  `apps/api/app/services/openclaw_bridge.py`, worker-lane
  gateway/session/continuity services under `apps/api/app/runtime/`, and the
  OpenClaw gateway/session/continuity owner docs
- allowed collateral surfaces: runtime presenters or API appendix surfaces for session and dispatch readbacks, and the prompt resource appendix when worker delivery or continuation behavior depends on it

## Do not edit / defer surfaces

- watchdog, operator/plugin, and support-state readback freezing
- public ingest/API/CLI or packaging/release surfaces

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- subagents are useful here for gateway integration, session lifecycle, or continuity behavior slices
- the parent agent owns the final worker-lane contract, single-live-run invariant interpretation, and continuity boundary decisions

## Wave integration loop

1. lock the current gateway/session work package against the phase page and file lock map
2. decide `no subagents` or brief the bounded subagents slices
3. integrate the returned gateway, bridge, runtime, and docs changes
4. run session, continuity, and worker-lane integration tests plus viable minimal and normal lanes
5. review findings and patch before another wave

## Phase purpose

Make worker-lane dispatch, session continuity, and gateway boundaries explicit enough that watchdog and operator work can build on them without reinterpreting the worker contract.

## Success criteria

- worker-lane dispatch, session, run, wake, and continuity behavior match canon
- gateway and bridge normalization boundaries are explicit
- continuity behavior preserves the single-live-run invariant

## Deliverables

- gateway integration alignment
- session lifecycle alignment
- continuity and worker-lane alignment

## Milestones

- gateway dispatch model aligned
- session lifecycle aligned
- continuity path aligned

## Ordered work packages

### `P4A-WP1`

- objective: align gateway dispatch, bridge normalization, and worker-lane launch semantics
- owned surfaces: OpenClaw integration, bridge service, gateway owner docs
- dependencies: Phase 3 complete
- test-first requirement: worker-lane or dispatch gap-revealing tests
- docs/update requirement: gateway boundary docs remain exact
- subagent allowed: yes
- closeout evidence: gateway behavior matches canon

### `P4A-WP2`

- objective: align session lifecycle, run binding, and continuity semantics
- owned surfaces: runtime session services, session owner docs, continuity docs
- dependencies: `P4A-WP1`
- test-first requirement: session or continuity tests
- docs/update requirement: session and continuity docs update in the same phase
- subagent allowed: yes
- closeout evidence: session and continuity behavior are explicit and reproducible

## Mandatory checklist

- [ ] gateway, bridge, session, and continuity docs match the landed worker-lane behavior
- [ ] session lifecycle and wake or redispatch behavior are explicit rather than inferred
- [ ] worker-lane behavior stays distinct from operator or support-state concerns
- [ ] any subagents slice stayed inside its gateway, session, or continuity ownership

## Required tests

- unit or integration tests for gateway dispatch and bridge normalization
- session lifecycle and continuity tests
- viable minimal and normal e2e lanes

## Required docs/examples

- gateway contract docs
- session lifecycle docs
- continuity docs

## Candidate delegated slices

- gateway integration slice
- session lifecycle slice
- continuity slice

## Exit evidence

- gateway, session, and continuity docs match landed behavior
- worker-lane integration is explicit and test-backed
- no stale mixed worker/operator assumptions survive in the worker contract

## Reset criteria

- apply the reset gate if runtime persistence, session truth, or worker-lane public readbacks change in a breaking way

## Kill-list terms

- OpenClaw as generic runtime truth
- continuity inferred from provider behavior instead of controller rules
- mixed worker and operator lane assumptions
