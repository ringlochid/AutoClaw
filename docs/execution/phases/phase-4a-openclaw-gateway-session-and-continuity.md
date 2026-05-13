# Phase 4A OpenClaw gateway, session, and continuity

Status: Target

This phase lands the OpenClaw-first gateway, session lifecycle, continuity, and worker-lane integration contract.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary redesign pages

- [Provider, worker, and operator boundary](../../redesign/architecture/provider-worker-and-operator-boundary.md)
- [OpenClaw Gateway RPC subset](../../redesign/architecture/openclaw-gateway-rpc-subset.md)
- [OpenClaw worker and gateway contract](../../redesign/architecture/openclaw-worker-and-gateway-contract.md)
- [MCP, plugin, and CLI boundary](../../redesign/interfaces/mcp-plugin-and-cli-boundary.md)
- [OpenClaw session lifecycle](../../redesign/architecture/openclaw-session-lifecycle.md)
- [OpenClaw continuity and send modes](../../redesign/architecture/openclaw-continuity-and-send-modes.md)
- [Runtime database and object contract](../../redesign/architecture/runtime-database-and-object-contract.md)
- [Provider direction and provider-native capabilities](../../redesign/workflows/provider-direction-and-provider-native-capabilities.md)

## Required supporting redesign reads

- [Runtime lane separation rationale](../../redesign/architecture/runtime-lane-separation-rationale.md)
- [Prompt legality and coverage](../../redesign/prompt-layer/legality-and-coverage.md)
- [Prompt-layer index](../../redesign/prompt-layer/INDEX.md)
- [Prompt-pack router and exact block ownership](../../redesign/prompt-layer/prompt-pack/README.md)
- [System and provider block](../../redesign/prompt-layer/prompt-pack/system-and-provider-block.md)
- [Runtime rule blocks](../../redesign/prompt-layer/prompt-pack/runtime-rule-blocks.md)
- [Validation and reject blocks](../../redesign/prompt-layer/prompt-pack/validation-and-reject-blocks.md)
- [Watchdog and provider recovery](../../redesign/architecture/watchdog-and-provider-recovery.md)
- [Guarded registry and runtime writes](../../redesign/interfaces/guarded-registry-and-runtime-writes.md)
- [ADR-0004 OpenClaw adapter normalization and worker transport boundary](../../redesign/decisions/ADR-0004-openclaw-adapter-normalization-and-worker-transport-boundary.md)
- [Recover a provider session](../../redesign/how-to/recover-a-provider-session.md)

## Required current contrast reads

- [OpenClaw dispatch and session contract](../../current/architecture/openclaw-dispatch-and-session-contract.md)
- [OpenClaw and bridge plugin](../../current/architecture/openclaw-and-bridge-plugin.md)
- [Current exact OpenClaw bridge prompt strings](../../current/interfaces/current-openclaw-bridge-prompt-strings.md)
- [API trust lanes](../../current/interfaces/api-trust-lanes.md)

## Exhaustive appendix owners

- [API schema appendix](../../redesign/interfaces/api-schema-appendix.md)
- [Prompt resource and usage appendix](../../redesign/prompt-layer/prompt-resource-usage-appendix.md)

## Required examples and diagrams

- the gateway and worker-lane diagrams in
  [OpenClaw worker and gateway contract](../../redesign/architecture/openclaw-worker-and-gateway-contract.md)
- the session-lifecycle and continuity diagrams in
  [OpenClaw session lifecycle](../../redesign/architecture/openclaw-session-lifecycle.md)
  and
  [OpenClaw continuity and send modes](../../redesign/architecture/openclaw-continuity-and-send-modes.md)
- the retained `same_session_continue` examples in
  [Runtime prompt, state, and transport examples](../../redesign/prompt-layer/generated/rendered-examples.md)
  and [System contract layer example](../../redesign/prompt-layer/composition-example.md)
- [Generated prompt inventory](../../redesign/prompt-layer/generated/inventory.md)

## Implementation surfaces

- owned surfaces: OpenClaw gateway, bridge-normalization, session, continuity,
  and private node-MCP attachment services under `apps/api/app/runtime/`, and
  the OpenClaw gateway/session/continuity owner docs
- allowed collateral surfaces: runtime presenters or API appendix surfaces for
  session and dispatch readbacks, the prompt resource appendix when worker
  delivery or continuation behavior depends on it, and the canonical local
  config owner page when runtime or OpenClaw tunables are introduced or renamed

## Do not edit / defer surfaces

- operator-MCP and node-MCP inventory freezing, package/profile separation
  proof, watchdog, and support-state readback freezing
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

Make worker-lane dispatch, session continuity, private node-MCP attachment, and
Gateway boundaries explicit enough that watchdog and operator work can build on
them without reinterpreting the worker contract.

## Success criteria

- worker-lane dispatch, session, run, wake, and continuity behavior match canon
- the exact Gateway RPC subset is frozen and pinned tightly enough that the
  adapter does not guess payloads or compatibility behavior
- reconnect, auth, and policy-limit behavior follow official Gateway best
  practice instead of local guesswork
- gateway and bridge normalization boundaries are explicit
- continuity behavior preserves the single-live-run invariant

## Deliverables

- gateway integration alignment
- exact Gateway RPC subset contract
- session lifecycle alignment
- continuity and worker-lane alignment

## Milestones

- gateway dispatch model aligned
- gateway subset contract aligned
- session lifecycle aligned
- continuity path aligned

## Ordered work packages

### `P4A-WP1`

- objective: align gateway dispatch, exact Gateway RPC subset, bridge normalization, and worker-lane launch semantics
- owned surfaces: OpenClaw integration, bridge service, gateway owner docs
- dependencies: Phase 3 complete
- test-first requirement: worker-lane or dispatch gap-revealing tests
- documentation update requirement: gateway boundary and Gateway-subset docs remain exact
- subagent allowed: yes
- closeout evidence: gateway behavior matches canon

### `P4A-WP2`

- objective: align session lifecycle, run binding, and continuity semantics
- owned surfaces: runtime session services, session owner docs, continuity docs
- dependencies: `P4A-WP1`
- test-first requirement: session or continuity tests
- documentation update requirement: session, node-attachment, and continuity docs update in the same phase
- subagent allowed: yes
- closeout evidence: session and continuity behavior are explicit and reproducible

## Mandatory checklist

- [ ] gateway, bridge, session, and continuity docs match the landed worker-lane behavior
- [ ] one exact Gateway subset page freezes the handshake, method subset,
      compatibility checks, and required proof artifacts
- [ ] session lifecycle and wake or redispatch behavior are explicit rather than inferred
- [ ] private node-MCP attachment and callback authority are explicit rather
      than left to transport guesswork
- [ ] the protocol pin, startup compatibility checks, and live handshake/run/abort proof requirements are explicit
- [ ] the Gateway adapter explicitly honors `hello-ok` policy fields,
      persisted device-token reconnect rules, and one bounded
      `AUTH_TOKEN_MISMATCH` retry
- [ ] configurable OpenClaw and runtime knobs are routed to the canonical local
      `config.toml` owner page rather than left as inline literals in runtime
      or wrapper docs
- [ ] worker-lane behavior stays distinct from operator or support-state concerns
- [ ] any subagents slice stayed inside its gateway, session, or continuity ownership

## Required tests

- unit or integration tests for gateway dispatch and bridge normalization
- session lifecycle and continuity tests
- golden handshake or method fixtures for `connect.challenge`, `connect`,
  `hello-ok`, `agent`, `agent.wait`, and `sessions.abort`
- startup compatibility checks for protocol version, required methods, and
  required scopes
- reconnect/auth tests for persisted device tokens, stored approved scopes, and
  one bounded `AUTH_TOKEN_MISMATCH` retry
- transport-policy tests for `tickIntervalMs`, `maxPayload`, and
  `maxBufferedBytes`
- live compatibility tests against a real OpenClaw Gateway lane
- viable minimal and normal e2e lanes

## Required docs and examples

- gateway contract docs
- session lifecycle docs
- continuity docs
- required examples and diagrams named above

## Candidate delegated slices

- gateway integration slice
- session lifecycle slice
- continuity slice

## Exit evidence

- gateway, session, and continuity docs match landed behavior
- the exact Gateway RPC subset, protocol pin, and startup compatibility checks
  are explicit and test-backed
- worker-lane integration is explicit and test-backed
- no stale mixed worker/operator or mixed operator/node MCP assumptions survive
  in the worker contract

## Reset criteria

- apply the reset gate if runtime persistence, session truth, or worker-lane public readbacks change in a breaking way

## Kill-list terms

- OpenClaw as generic runtime truth
- imagined Gateway response handling
- unpinned protocol or handwritten ad hoc Gateway payloads
- continuity inferred from provider behavior instead of controller rules
- mixed worker and operator lane assumptions
