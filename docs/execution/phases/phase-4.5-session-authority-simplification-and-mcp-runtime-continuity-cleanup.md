# Phase 4.5 session-authority simplification and MCP/runtime continuity cleanup

Status: Target

This phase lands the session-rooted authority simplification, removes the
separate callback-binding authority model, unifies callback/node-MCP validation
on one trusted Gateway `sessionKey`, and implements parent/root-only
same-session redispatch with same `sessionKey`, fresh `idempotencyKey`, full
regenerated resend, and fresh returned `runId`.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary redesign pages

- [Runtime records and lifecycle](../../redesign/architecture/runtime-records-and-lifecycle.md)
- [Runtime boundary and controller loop contract](../../redesign/architecture/runtime-boundary-and-controller-loop-contract.md)
- [Runtime database and object contract](../../redesign/architecture/runtime-database-and-object-contract.md)
- [OpenClaw session lifecycle](../../redesign/architecture/openclaw-session-lifecycle.md)
- [OpenClaw continuity and send modes](../../redesign/architecture/openclaw-continuity-and-send-modes.md)
- [OpenClaw worker and gateway contract](../../redesign/architecture/openclaw-worker-and-gateway-contract.md)
- [MCP, plugin, and CLI boundary](../../redesign/interfaces/mcp-plugin-and-cli-boundary.md)
- [MCP tool reference](../../redesign/interfaces/plugin-tool-reference.md)
- [API surface and trust-lane map](../../redesign/interfaces/api-surface-and-trust-lane-map.md)

## Required supporting redesign reads

- [Provider, worker, and operator boundary](../../redesign/architecture/provider-worker-and-operator-boundary.md)
- [Watchdog and recovery contract](../../redesign/architecture/watchdog-and-recovery-contract.md)
- [Runtime observability and boundary log](../../redesign/architecture/runtime-observability-and-boundary-log.md)
- [Guarded registry and runtime writes](../../redesign/interfaces/guarded-registry-and-runtime-writes.md)
- [API schema appendix](../../redesign/interfaces/api-schema-appendix.md)

## Required current contrast reads

- [API trust lanes](../../current/interfaces/api-trust-lanes.md)
- [OpenClaw dispatch and session contract](../../current/architecture/openclaw-dispatch-and-session-contract.md)
- [Runtime control plane](../../current/architecture/runtime-control-plane.md)

## Required examples and diagrams

- the lifecycle and continuity diagrams in
  [Runtime records and lifecycle](../../redesign/architecture/runtime-records-and-lifecycle.md),
  [Runtime boundary and controller loop contract](../../redesign/architecture/runtime-boundary-and-controller-loop-contract.md),
  and [OpenClaw session lifecycle](../../redesign/architecture/openclaw-session-lifecycle.md)

## Implementation surfaces

- owned surfaces: runtime session-authority and redispatch implementation under
  `apps/api/app/runtime/*`, runtime DB/model and schema surfaces under
  `apps/api/app/db/*` and `apps/api/app/schemas/*`, the session-bound MCP
  wrapper and binding surfaces under `apps/api/autoclaw/openclaw/**`, and the
  redesign/execution owner docs named above
- allowed collateral surfaces: prompt-layer owner docs when same-session
  continuity wording must stay aligned with the locked `full_prompt` resend
  model, narrow observability docs when authority wording must stop teaching
  callback-binding truth, `apps/api/app/config.py` and
  `apps/api/app/main.py` when runtime-owned session/continuity wiring must
  change, and the selected Phase 4.5 plan/evidence/review artifacts under
  `docs/execution/plans/`, `docs/execution/evidence/`, and
  `docs/execution/reviews/`

## Do not edit / defer surfaces

- public ingest/API/CLI noun-family work that remains Phase 5A-owned
- packaging/release/install/reset surfaces that remain Phase 5B-owned
- support-state field-set freezing beyond narrow authority-wording repairs

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- subagents are useful here for runtime authority, MCP/binding cleanup, or redispatch continuity slices
- the parent agent owns the final authority-model interpretation and the parent/root continuity boundary decisions

## Wave integration loop

1. lock the current session-authority cleanup work package against the phase page and file lock map
2. decide `no subagents` or brief the bounded subagents slices
3. integrate the returned runtime, DB/model, MCP wrapper, and docs changes
4. run authority, redispatch, and MCP validation tests plus viable e2e lanes
5. review findings and patch before another wave

## Phase purpose

Make session-rooted authority, unified node/callback validation, and parent/root-only same-session redispatch explicit and implemented cleanly enough that the runtime no longer carries the redundant callback-binding authority split.

## Success criteria

- one presented Gateway `sessionKey` is the canonical node/callback authority input
- the same Gateway `sessionKey` is both continuity identity and node/callback caller identity on the canonical Gateway WS path
- provider/OpenResponses fields such as provider `session_key` and `previous_response_id` remain adapter-native transport detail only
- parent/root same-attempt redispatch keeps the same `sessionKey`, sends a fresh `idempotencyKey`, resends the full regenerated prompt package, and accepts a fresh returned `runId`
- worker retry, fresh child assignment, and new-attempt recovery remain fresh-session flows
- `NodeSessionModel` is the canonical authority row
- separate callback-binding authority and synthetic `NodeMcpBinding` no longer define the live target implementation model
- callback and node-MCP validation derive currentness from runtime truth rather than parallel authority rows

## Deliverables

- runtime/session-authority simplification
- callback/node-MCP validation simplification
- parent/root same-session redispatch implementation
- stale docs, tests, and migration cleanup for the removed redundancy

## Milestones

- session-authority model aligned
- node/callback validation aligned
- parent/root same-session redispatch aligned
- stale authority-model ballast removed

## Ordered work packages

### `P4.5-WP1`

- objective: align runtime and DB authority truth around `NodeSession`
- owned surfaces: runtime DB/models, runtime control, runtime owner docs
- dependencies: Phase 4A complete, Phase 4B complete
- test-first requirement: authority/currentness gap-revealing tests
- documentation update requirement: runtime authority docs remain exact
- subagent allowed: yes
- closeout evidence: separate callback-binding authority is no longer canonical

### `P4.5-WP2`

- objective: collapse callback/node-MCP validation and simplify session-bound MCP authority
- owned surfaces: node/callback validation code, OpenClaw MCP wrapper surfaces, MCP boundary docs
- dependencies: `P4.5-WP1`
- test-first requirement: callback/node-MCP validation tests
- documentation update requirement: MCP/session-bound authority wording updated in the same phase
- subagent allowed: yes
- closeout evidence: one server-side session-authority path governs callback and node MCP writes

### `P4.5-WP3`

- objective: implement parent/root-only same-session redispatch with same `sessionKey`, fresh `idempotencyKey`, full regenerated resend, and fresh returned `runId`
- owned surfaces: runtime redispatch/session services, OpenClaw session/continuity docs, related tests
- dependencies: `P4.5-WP1`, `P4.5-WP2`
- test-first requirement: same-session parent/root redispatch tests
- documentation update requirement: session/continuity docs updated in the same phase
- subagent allowed: yes
- closeout evidence: parent/root same-attempt redispatch no longer remints a fresh session by default

## Mandatory checklist

- [ ] one presented Gateway `sessionKey` is the canonical node/callback authority input
- [ ] parent/root same-attempt redispatch keeps the same `sessionKey`, sends a fresh `idempotencyKey`, resends the full regenerated prompt package, and accepts a fresh returned `runId`
- [ ] worker retry and new-attempt recovery remain fresh-session flows
- [ ] `NodeSessionModel` is the canonical authority row
- [ ] separate callback-binding authority no longer defines the live target implementation model
- [ ] callback and node-MCP validation are unified around runtime truth
- [ ] stale docs and tests no longer teach callback-binding authority as canonical
- [ ] any subagents slice stayed inside its authority, MCP, or redispatch ownership

## Required tests

- runtime authority and redispatch integration tests
- callback/node-MCP validation tests
- parent/root same-session redispatch tests
- viable minimal, normal, and maximal e2e lanes

## Required docs and examples

- runtime/session-authority docs
- OpenClaw session/continuity docs
- MCP boundary docs
- required examples and diagrams named above

## Candidate delegated slices

- runtime authority slice
- MCP/binding cleanup slice
- parent/root continuity slice

## Exit evidence

- session-authority, redispatch, and MCP docs match landed behavior
- callback/node validation simplification is explicit and test-backed
- parent/root same-session redispatch is explicit and test-backed
- the selected Phase 4.5 plan, evidence, and review artifacts remain the only closeout authority for this phase

## Reset criteria

- apply the reset gate if runtime persistence, session authority, or public readback contracts change in a breaking way

## Kill-list terms

- separate callback-binding authority as the target model
- fresh-session-per-dispatch as the universal redispatch rule
- mixed node and operator MCP sessions
- `same_session_continue` described as the canonical parent/root redispatch transport
- task-scoped path ids treated as primary node authority
