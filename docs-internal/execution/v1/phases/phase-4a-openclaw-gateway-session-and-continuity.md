# Phase 4A OpenClaw gateway, session, and continuity

Status: Reference

This phase lands the OpenClaw-first gateway, the dispatch-scoped Gateway RPC transport, the immediate controller-owned per-dispatch ingest write seam, session lifecycle, continuity, parent/root same-session redispatch semantics, and the worker-lane integration contract.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary design pages

- [Provider, worker, and operator boundary](../../../design/v1/architecture/provider-worker-and-operator-boundary.md)
- [OpenClaw Gateway RPC subset](../../../design/v1/architecture/openclaw-gateway-rpc-subset.md)
- [OpenClaw worker and gateway contract](../../../design/v1/architecture/openclaw-worker-and-gateway-contract.md)
- [MCP, plugin, and CLI boundary](../../../design/v1/interfaces/mcp-plugin-and-cli-boundary.md)
- [OpenClaw session lifecycle](../../../design/v1/architecture/openclaw-session-lifecycle.md)
- [OpenClaw continuity and send modes](../../../design/v1/architecture/openclaw-continuity-and-send-modes.md)
- [Runtime database and object contract](../../../design/v1/architecture/runtime-database-and-object-contract.md)
- [Provider direction and provider-native capabilities](../../../design/v1/workflows/provider-direction-and-provider-native-capabilities.md)

## Required supporting design reads

- [Runtime lane separation rationale](../../../design/v1/architecture/runtime-lane-separation-rationale.md)
- [Prompt legality and coverage](../../../design/v1/prompt-layer/legality-and-coverage.md)
- [Prompt-layer front door](../../../design/v1/prompt-layer/README.md)
- [Prompt-pack router and exact block ownership](../../../design/v1/prompt-layer/prompt-pack/README.md)
- [System and provider block](../../../design/v1/prompt-layer/prompt-pack/system-and-provider-block.md)
- [Runtime rule blocks](../../../design/v1/prompt-layer/prompt-pack/runtime-rule-blocks.md)
- [Validation and reject blocks](../../../design/v1/prompt-layer/prompt-pack/validation-and-reject-blocks.md)
- [Watchdog and provider recovery](../../../design/v1/architecture/watchdog-and-provider-recovery.md)
- [Guarded registry and runtime writes](../../../design/v1/interfaces/guarded-registry-and-runtime-writes.md)
- [ADR-0004 OpenClaw adapter normalization and worker transport boundary](../../../adr/ADR-0004-openclaw-adapter-normalization-and-worker-transport-boundary.md)
- [Recover a provider session](../../../design/v1/how-to/recover-a-provider-session.md)

## Required current contrast reads

- [OpenClaw dispatch and session contract](../../../current/v1/architecture/openclaw-dispatch-and-session-contract.md)
- [OpenClaw and bridge plugin](../../../current/v1/architecture/openclaw-and-bridge-plugin.md)
- [Current exact OpenClaw bridge prompt strings](../../../current/v1/interfaces/current-openclaw-bridge-prompt-strings.md)
- [API trust lanes](../../../current/v1/interfaces/api-trust-lanes.md)

## Exhaustive appendix owners

- [API schema appendix](../../../design/v1/interfaces/api-schema-appendix.md)
- [Prompt resource and usage appendix](../../../design/v1/prompt-layer/prompt-resource-usage-appendix.md)

## Required examples and diagrams

- the gateway and worker-lane diagrams in [OpenClaw worker and gateway contract](../../../design/v1/architecture/openclaw-worker-and-gateway-contract.md)
- the session-lifecycle and continuity diagrams in [OpenClaw session lifecycle](../../../design/v1/architecture/openclaw-session-lifecycle.md) and [OpenClaw continuity and send modes](../../../design/v1/architecture/openclaw-continuity-and-send-modes.md)
- [Generated prompt inventory](../../../design/v1/prompt-layer/generated/inventory.md)

## Implementation surfaces

- owned surfaces: OpenClaw gateway, bridge-normalization, dispatch-scoped ingest, session, parent/root same-session continuity, and worker-lane continuity services under `apps/api/src/autoclaw/runtime/`, and the OpenClaw gateway/session/continuity owner docs
- allowed collateral surfaces: runtime presenters or API appendix surfaces for session and dispatch readbacks; the prompt resource appendix when worker delivery or continuation behavior depends on it; `apps/api/src/autoclaw/config.py` and `apps/api/src/autoclaw/main.py` when runtime-owned Gateway config loading or lifespan startup wiring must land; narrow runtime DB/runtime-model surfaces when the immediate controller-owned ingest commit, session/run persistence, or parent/root same-session redispatch truth must land without widening into watchdog or MCP ownership; the currently viable Phase 2 minimal e2e lane plus the touched Phase 3 control-preservation tests when real Gateway/session lifecycle changes must preserve earlier-phase runtime behavior truth, specifically `apps/api/tests/e2e/workflows/minimal/test_minimal_runtime_lane.py`, `apps/api/tests/integration/runtime/control/test_abort_cases.py`, and `apps/api/tests/integration/runtime/control/test_boundary_transition_cases.py`; the selected Phase 4A plan, evidence, and review artifacts under `docs-internal/execution/v1/plans/`, `docs-internal/execution/v1/evidence/`, and `docs-internal/execution/v1/reviews/`; and the canonical local config owner page when runtime or OpenClaw tunables are introduced or renamed

## Do not edit / defer surfaces

- external operator MCP and node MCP surface exposure, package/profile separation proof, watchdog consumption of committed truth, and support-state readback freezing, including `delivery-state.json`, `continuity-state.json`, `watchdog-state.json`, and `provider-events.ndjson`
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

Make worker-lane dispatch, dispatch-scoped Gateway ingest, session continuity, parent/root same-session redispatch, and Gateway boundaries explicit enough that later watchdog and operator work can consume committed truth without reinterpreting the worker contract.

## Success criteria

- worker-lane dispatch, session, run, wake, and continuity behavior match canon
- the exact Gateway RPC subset is frozen and pinned tightly enough that the adapter does not guess payloads or compatibility behavior
- reconnect, auth, and policy-limit behavior follow official Gateway best practice instead of local guesswork
- gateway and bridge normalization boundaries are explicit
- each dispatch owns one runtime-scoped Gateway reader plus one immediate controller-owned ingest write seam that turns correlated provider progress into committed runtime truth
- continuity behavior preserves the single-live-run invariant
- parent/root same-attempt redispatch reuses the same `sessionKey` when continuity reuse remains lawful, otherwise falls back to a fresh `sessionKey`, always opens a fresh `runId`, and resends the full regenerated prompt package
- worker retry, fresh child assignment, and new-attempt recovery remain fresh-session flows
- watchdog classification, support-state freezing, and support-facing readbacks remain downstream consumers of the committed truth written here
- authority-model simplification and callback-binding removal remain Phase 4.5-owned rather than being folded into Phase 4A

## Deliverables

- gateway integration alignment
- dispatch-scoped Gateway ingest seam alignment
- exact Gateway RPC subset contract
- session lifecycle alignment
- continuity and worker-lane alignment

## Milestones

- gateway dispatch model aligned
- dispatch-scoped ingest seam aligned
- gateway subset contract aligned
- session lifecycle aligned
- continuity path aligned

## Ordered work packages

### `P4A-WP1`

- objective: align gateway dispatch, exact Gateway RPC subset, bridge normalization, the immediate controller-owned per-dispatch ingest write seam, and worker-lane launch semantics
- owned surfaces: OpenClaw integration, bridge service, gateway owner docs
- dependencies: Phase 3 complete
- test-first requirement: worker-lane or dispatch gap-revealing tests
- documentation update requirement: gateway boundary and Gateway-subset docs remain exact
- subagent allowed: yes
- closeout evidence: gateway and ingest behavior match canon

### `P4A-WP2`

- objective: align session lifecycle, run binding, and continuity semantics
- owned surfaces: runtime session services, session owner docs, continuity docs
- dependencies: `P4A-WP1`
- test-first requirement: session or continuity tests
- documentation update requirement: session and continuity docs update in the same phase
- subagent allowed: yes
- closeout evidence: session and continuity behavior are explicit and reproducible

## Mandatory checklist

- [ ] gateway, bridge, session, and continuity docs match the landed worker-lane behavior
- [ ] one exact Gateway subset page freezes the handshake, method subset,
      compatibility checks, and required proof artifacts
- [ ] session lifecycle and wake or redispatch behavior are explicit rather than inferred
- [ ] parent/root same-session redispatch semantics are explicit rather than
      left to transport guesswork
- [ ] the protocol pin, startup compatibility checks, and live handshake/run/abort proof requirements are explicit
- [ ] the Gateway adapter explicitly honors `hello-ok` policy fields,
      loopback token/password/no-auth support, blocked unsupported auth
      shapes, and fail-closed auth diagnostics
- [ ] the first controller-owned write after correlated Gateway receipt remains Phase 4A-owned and is documented as the immediate per-dispatch ingest seam rather than as a watchdog or support-state concern
- [ ] configurable OpenClaw and runtime knobs are routed to the canonical local
      `config.toml` owner page rather than left as inline literals in runtime
      or wrapper docs
- [ ] worker-lane behavior stays distinct from operator or support-state concerns
- [ ] authority-model simplification and callback-binding removal remain
      Phase 4.5-owned
- [ ] external node MCP surface exposure, package/profile attachment proof,
      and exact `delivery-state.json`, `continuity-state.json`,
      `watchdog-state.json`, and `provider-events.ndjson` freeze remain
      Phase 4B-owned
- [ ] any subagents slice stayed inside its gateway, session, or continuity ownership

## Required tests

- unit or integration tests for gateway dispatch, bridge normalization, and the immediate ingest seam
- session lifecycle and continuity tests
- golden handshake or method fixtures for `connect.challenge`, `connect`, `hello-ok`, `agent`, `agent.wait`, and `sessions.abort`
- startup compatibility checks for protocol version, required methods, and required scopes
- reconnect/auth tests for loopback token, loopback password, explicit loopback no-auth, blocked non-loopback, blocked trusted-proxy, missing secret input, ambiguous auth, and unresolved secret-reference cases
- transport-policy tests for `tickIntervalMs` validation or recording and for `maxPayload` / `maxBufferedBytes` enforcement
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
- the exact Gateway RPC subset, protocol pin, and startup compatibility checks are explicit and test-backed
- worker-lane integration and immediate committed-truth ingest ownership are explicit and test-backed
- the selected Phase 4A plan, evidence, and review artifacts remain the only closeout authority for this phase; there is no blended Phase 4 closure record
- no stale mixed worker/operator assumptions survive in the worker contract

## Reset criteria

- apply the reset gate if runtime persistence, session truth, or worker-lane public readbacks change in a breaking way

## Kill-list terms

- OpenClaw as generic runtime truth
- imagined Gateway response handling
- unpinned protocol or handwritten ad hoc Gateway payloads
- continuity inferred from provider behavior instead of controller rules
- mixed worker and operator lane assumptions
