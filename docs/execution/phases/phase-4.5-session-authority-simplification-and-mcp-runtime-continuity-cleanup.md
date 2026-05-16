# Phase 4.5 session-authority simplification and MCP/runtime continuity cleanup

Status: Target

This phase lands the deletion-heavy server-side simplification under the explicit-arg v1 interface: it removes the separate callback-binding authority model, unifies callback and node-MCP validation on one trusted Gateway `sessionKey`, preserves parent and root same-attempt redispatch with the same `sessionKey`, fresh `idempotencyKey`, full regenerated resend, and a fresh returned `runId`, and deletes non-behavioral support-state, readback, prompt-compatibility, schema, and test ballast once it stops driving behavior.

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
- [Prompt contract](../../redesign/prompt-layer/contract.md)
- [Prompt source and sections](../../redesign/prompt-layer/source-and-sections.md)
- [Render and persistence](../../redesign/prompt-layer/render-and-persistence.md)

## Required adjacent phase reads

- [Phase 4A](phase-4a-openclaw-gateway-session-and-continuity.md)
- [Phase 4B](phase-4b-watchdog-operator-plugin-and-support-state.md)

## Required current contrast reads

- [API trust lanes](../../current/interfaces/api-trust-lanes.md)
- [OpenClaw dispatch and session contract](../../current/architecture/openclaw-dispatch-and-session-contract.md)
- [Runtime control plane](../../current/architecture/runtime-control-plane.md)

## Required examples and diagrams

- the lifecycle and continuity diagrams in [Runtime records and lifecycle](../../redesign/architecture/runtime-records-and-lifecycle.md), [Runtime boundary and controller loop contract](../../redesign/architecture/runtime-boundary-and-controller-loop-contract.md), and [OpenClaw session lifecycle](../../redesign/architecture/openclaw-session-lifecycle.md)
- same-session and node-tool examples in [Prompt contract](../../redesign/prompt-layer/contract.md), [Prompt source and sections](../../redesign/prompt-layer/source-and-sections.md), and the Phase 4A continuity owners listed above

## Implementation surfaces

- owned surfaces: runtime authority, redispatch, prompt, projection, and watchdog implementation under `apps/api/app/runtime/*`; runtime DB/model and schema surfaces under `apps/api/app/db/*` and `apps/api/app/schemas/*`; the static v1 node-MCP wrapper surfaces under `apps/api/autoclaw/openclaw/**`; regression, schema-contract, prompt, and e2e proof surfaces under `apps/api/tests/integration/phase3/**`, `apps/api/tests/integration/phase4a/**`, `apps/api/tests/integration/phase4b/**`, `apps/api/tests/integration/runtime_schema_contract/**`, `apps/api/tests/e2e/**`, and `apps/api/tests/unit/runtime_prompt_rendering/**`; and the redesign and execution owner docs named above
- allowed collateral surfaces: prompt-layer owner docs plus generated prompt docs and prompt-catalog inputs when `full_prompt`-only truth or dispatch-local `task_id` and `session_key` tool context must stay aligned; the exact current-contrast pages named above when deleted readback or prompt-compatibility debt must remain truthful as shipped contrast only; narrow observability and readback docs when support-state wording must stop teaching callback-binding or fresh-session target truth; `apps/api/app/config.py` and `apps/api/app/main.py` when runtime-owned session or continuity wiring must change; and the selected Phase 4.5 plan, evidence, and review artifacts under `docs/execution/plans/`, `docs/execution/evidence/`, and `docs/execution/reviews/`
- strict review artifact allowance: the final closeout review may be written only by an edit slice that owns `docs/execution/reviews/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md` and no other repo-tracked file

## Do not edit / defer surfaces

- public ingest/API/CLI noun-family work that remains Phase 5A-owned
- packaging/release/install/reset surfaces that remain Phase 5B-owned
- unrelated registry, frontend, or plugin work that does not participate in the Phase 4.5 proof lanes
- support-state field-set freezing beyond fields that still drive or directly explain behavior; non-behavioral support-state, readback, prompt-compatibility, schema, and test debt is Phase 4.5 deletion material, not protected ballast

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- docs-first canon repair may run as a bounded edit slice before the code-bearing waves
- separate edit slices are useful for authority/runtime DB work, node-MCP and callback parity, watchdog and observability cleanup, and prompt/runtime asset cleanup
- one review-only QA slice may inspect the integrated repo before final closeout
- the final authoritative Phase 4.5 review may be written only by the strict closeout edit slice that owns the review artifact and nothing else
- the parent agent owns the final authority-model interpretation, wave integration order, expensive proof lanes, and the pass/fail decision when the strict closeout reviewer returns findings

## Wave integration loop

1. land the Phase 0 addendum docs-first truth repair before deletion-heavy code work starts
2. run the first code wave only after the docs-first slice, then wait for the full wave before editing repo-tracked files again
3. integrate the returned authority, node-MCP, watchdog, and docs changes in `P4.5-WP1` through `P4.5-WP5` order even when slices ran in parallel
4. run targeted validators, targeted tests, and targeted coverage once after interface-stable integration before starting the prompt-runtime asset wave or QA review wave
5. run the final expensive proof lanes once at code freeze, then hand the final evidence pack to the strict closeout review slice
6. patch only from returned review findings before claiming completion

## Phase purpose

Make session-rooted authority, unified node and callback validation, and parent and root same-session redispatch explicit and implemented cleanly enough that the runtime no longer carries the redundant callback-binding authority split, while keeping the external v1 node-MCP interface stable as explicit `session_key` plus `task_id` tool arguments, narrowing watchdog to lineage-preserving stability recovery only, and deleting stale continuity, support-state, readback, prompt-compatibility, schema, and hidden-binding ballast from the live target contract whenever it no longer drives behavior.

## Success criteria

- one presented Gateway `sessionKey` is the canonical node/callback authority input
- `NodeSessionModel` is the canonical authority row
- callback HTTP and node MCP resolve authority through one shared runtime truth path rooted in `NodeSession.session_key` plus task and currentness truth
- the same Gateway `sessionKey` is both continuity identity and the backend authority value validated behind explicit v1 node tool arguments
- provider/OpenResponses fields such as provider `session_key` and `previous_response_id` remain adapter-native transport detail only
- parent/root same-attempt redispatch keeps the same `sessionKey`, sends a fresh `idempotencyKey`, resends the full regenerated prompt package, and accepts a fresh returned `runId`
- live parent/root redispatch emits `full_prompt` only and no longer depends on `same_session_continue`
- worker retry, fresh child assignment, and semantic new-attempt recovery remain fresh-session flows
- separate callback-binding authority and synthetic `NodeMcpBinding` no longer define the live target implementation model
- callback and node-MCP validation derive currentness from runtime truth rather than parallel authority rows
- the external v1 node-MCP interface remains explicit `session_key` + `task_id` tool arguments rather than a hidden-binding contract
- watchdog preserves runtime lineage and may only `redispatch_same_attempt` or `escalate`
- watchdog automatic recovery does not mint a new attempt and does not consume authored retry budget
- controller-owned same-attempt watchdog redispatch caps and watchdog timing live under `[runtime]` config rather than authored policy grammar
- non-behavioral persisted, support-state, readback, prompt-compatibility, schema, and test surfaces are deleted rather than preserved for compatibility theater
- stale field families such as dispatch `phase`, target-facing `send_mode`, dispatch `status`, `staged_continuation_kind`, `controller_observation_state`, broad continuity-state catalogs, `previous_response_id`, and callback-binding authority rows are removed from live canon or explicitly demoted to current and debt observability only when they still explain behavior
- minimal, normal, and maximal e2e lanes plus the real OpenClaw host proof lane pass before closeout

## Deliverables

- docs-first truth repair and Phase 0 addendum handoff
- runtime/session-authority simplification
- explicit-arg node MCP rewrite and callback parity rewrite
- parent/root same-session redispatch implementation
- prompt-layer contract alignment for dispatch-local node tool context and full-prompt-only live behavior
- watchdog recovery narrowing and continuity/send-mode cleanup
- redundant state, schema, support-state, and test deletion for the removed hidden-binding model
- coverage raise, full proof-lane execution, and strict independent closeout review

## Milestones

- Phase 0 addendum green
- Phase 4.5 docs-first sync green
- session-authority model aligned
- authority path unified
- node and callback parity aligned
- parent/root same-session redispatch aligned
- prompt and dispatch-state cleanup aligned
- watchdog lineage-preserving recovery aligned
- redundant state removed
- repo tests green
- real OpenClaw proof green
- strict closeout review green

## Ordered work packages

### `P4.5-WP1`

- objective: replace callback-binding authority with one shared resolver keyed by presented `session_key` plus `task_id`, backed by `NodeSession`, current dispatch, current assignment, current attempt, current node, and running-flow truth
- owned surfaces: runtime DB/models, runtime control, runtime schemas, runtime owner docs, and authority regression tests
- dependencies: Phase 4A complete, Phase 4B complete
- test-first requirement: authority/currentness gap-revealing tests
- documentation update requirement: runtime authority docs remain exact
- subagent allowed: yes
- closeout evidence: separate callback-binding authority is no longer live runtime truth

### `P4.5-WP2`

- objective: rewrite node MCP so every node tool takes explicit `session_key` plus `task_id`, remove `NodeMcpBinding`, remove the hidden `x-session-key` canonical path, and move callback HTTP and node MCP onto the same semantic node-operation service
- owned surfaces: node/callback validation code, OpenClaw MCP wrapper surfaces, callback route surfaces, MCP boundary docs, and MCP regression tests
- dependencies: `P4.5-WP1`
- test-first requirement: callback/node-MCP validation tests
- documentation update requirement: MCP/session-rooted explicit-arg authority wording updated in the same phase
- subagent allowed: yes
- closeout evidence: one server-side session-authority path governs callback and node MCP writes

### `P4.5-WP3`

- objective: land real parent/root `redispatch_same_attempt` behavior with the same Gateway `sessionKey`, a fresh `runId`, a fresh `idempotencyKey`, and a full regenerated `full_prompt` resend while keeping worker retry and semantic new-attempt flows fresh-session
- owned surfaces: runtime redispatch, session, continuity, and related tests plus the session and continuity owner docs
- dependencies: `P4.5-WP1`, `P4.5-WP2`
- test-first requirement: same-session parent/root redispatch tests
- documentation update requirement: session/continuity docs updated in the same phase
- subagent allowed: yes
- closeout evidence: parent/root same-attempt redispatch no longer remints a fresh session by default

### `P4.5-WP4`

- objective: rewrite prompt models, prompt assets, generated docs, prompt tests, and dispatch prompt projection to full-prompt-only live behavior and add dispatch-local node tool context for `task_id` and `session_key` with the exact non-echo and non-persist rule
- owned surfaces: prompt and task-root runtime surfaces, prompt owner docs, generated prompt docs, prompt-catalog inputs, and prompt regression tests
- dependencies: `P4.5-WP3`
- test-first requirement: prompt rendering and dispatch-local node tool context tests
- documentation update requirement: prompt-layer owner and generated docs updated in the same phase
- subagent allowed: yes
- closeout evidence: prompt/runtime no longer preserves `same_session_continue` artifacts as live behavior

### `P4.5-WP5`

- objective: remove watchdog `create_new_attempt`, narrow automatic recovery to `redispatch_same_attempt | escalate`, add controller-owned same-attempt redispatch caps under `[runtime]`, and delete redundant support-state and readback fields in behavior-safe order
- owned surfaces: watchdog, observability, projection, support-state docs, readback and runtime-schema tests, and e2e helpers tied to recovery or removed fields
- dependencies: `P4.5-WP3`, `P4.5-WP4`
- test-first requirement: watchdog, support-state omission, and runtime-schema contract tests
- documentation update requirement: watchdog, observability, and current-contrast docs updated in the same phase
- subagent allowed: yes
- closeout evidence: removed field families no longer drive behavior or target readback truth

### `P4.5-WP6`

- objective: rewrite stale tests and helpers, raise coverage, create the maximal e2e lane, and run the full repo, DB, reset, and host OpenClaw proof lanes at code freeze
- owned surfaces: touched Phase 4.5 regression and e2e tests, final evidence and review artifacts, and any narrow proof-harness support needed by the selected phase
- dependencies: `P4.5-WP1`, `P4.5-WP2`, `P4.5-WP3`, `P4.5-WP4`, `P4.5-WP5`
- test-first requirement: missing-coverage and stale-fixture gap review before final expensive runs
- documentation update requirement: execution evidence and review artifacts stay exact
- subagent allowed: yes
- closeout evidence: the final Phase 4.5 evidence artifact records the full pass matrix and the final review passes

## Mandatory checklist

- [ ] the Phase 0 addendum landed before Phase 4.5 deletes support-state, readback, prompt-compatibility, schema, or test ballast
- [ ] one presented Gateway `sessionKey` is the canonical node/callback authority input
- [ ] `NodeSessionModel` is the canonical authority row
- [ ] separate callback-binding authority no longer defines the live target implementation model
- [ ] callback HTTP and node MCP share one semantic node-operation path rooted in runtime truth
- [ ] explicit-arg node MCP uses `session_key` + `task_id` and no hidden `x-session-key` authority contract
- [ ] parent/root same-attempt redispatch keeps the same `sessionKey`, gets a fresh `runId`, sends a fresh `idempotencyKey`, resends the full regenerated prompt package, and accepts a fresh returned `runId`
- [ ] worker retry and new-attempt recovery remain fresh-session flows
- [ ] live prompt/runtime behavior emits `full_prompt` only and no longer preserves `same_session_continue` as a live feature term
- [ ] dispatch-local prompt context teaches explicit `task_id` + `session_key` tool calls without promoting them into stable runtime truth
- [ ] watchdog automatic recovery preserves runtime lineage and no longer auto-mints a new attempt
- [ ] watchdog automatic recovery does not consume authored retry budget
- [ ] stale field families such as `DispatchTurn.phase`, `DispatchTurn.status`, `DispatchTurn.staged_continuation_kind`, `DispatchDeliveryState.send_mode`, `DispatchDeliveryState.controller_observation_state`, `DispatchContinuityState.previous_response_id`, broad `continuity_state` transport catalogs, and callback-binding authority rows are removed from live target canon or explicitly demoted to current/debt observability only
- [ ] stale prompt-compatibility, schema, test, and support-state surfaces no longer freeze the hidden callback-binding authority model as target truth
- [ ] non-behavioral support-state and readback ballast is deleted rather than kept solely for compatibility
- [ ] stale docs and tests no longer teach callback-binding authority as canonical
- [ ] the maximal e2e lane and real OpenClaw host proof lane are green before closeout
- [ ] the final strict closeout review slice owns only the authoritative Phase 4.5 review artifact
- [ ] every touched markdown file is cleaned of broken line wraps inside sentences and bullets
- [ ] any subagents slice stayed inside its owned surfaces and wave role

## Required tests

- unified authority rejection tests for stale, revoked, mismatched, or non-current session cases
- task mismatch and lineage mismatch tests
- explicit-arg node MCP schema and mounted-tool tests with no baked hidden `x-session-key` contract
- callback and node parity tests
- parent/root same-session redispatch tests asserting the same Gateway `sessionKey`, a fresh `runId`, and a fresh `idempotencyKey`
- worker retry fresh-session regression tests
- watchdog `redispatch_same_attempt | escalate` tests and no-authored-budget-consumption tests
- prompt hygiene tests for dispatch-local `task_id` / `session_key`
- support/readback omission tests for removed fields
- runtime schema contract tests after field or table deletion
- prompt unit tests
- viable minimal, normal, and maximal e2e lanes
- shipped-path SQLite smoke/reset proof when runtime or persistence truth changes
- Postgres + Docker strong verification when runtime or persistence truth changes
- real OpenClaw host proof with correct effective tool inventories and one real node-tool call before closeout

## Required docs and examples

- Phase 0 addendum docs and the Phase 4.5 execution artifacts
- runtime/session-authority docs
- OpenClaw session/continuity docs
- MCP boundary docs
- prompt-layer owner docs plus generated prompt inventory/examples
- watchdog recovery and observability docs
- touched current-contrast docs and the API schema appendix when shapes change
- required examples and diagrams named above
- every touched markdown file must be cleaned of broken line wraps inside sentences or bullets

## Candidate delegated slices

- `phase45-docs-execution`
- `phase45-authority-runtime-db`
- `phase45-node-mcp-callback`
- `phase45-watchdog-observability`
- `phase45-prompt-runtime-assets`
- `phase45-qa-gate-review`
- `phase45-strict-closeout-review`

## Exit evidence

- session-authority, redispatch, prompt, watchdog, and MCP docs match landed behavior
- callback/node validation simplification is explicit and test-backed
- parent/root same-session redispatch is explicit and test-backed
- watchdog lineage-preserving recovery is explicit and test-backed
- the final Phase 4.5 evidence artifact records the pass matrix for targeted lanes, expensive lanes, and any valid no-rerun decisions
- the real OpenClaw host proof result and stale-logic search proof are explicit
- the selected Phase 4.5 plan, evidence, and review artifacts remain the only closeout authority for this phase; the master-program records stay `summary-only: yes`

## Reset criteria

- apply the reset gate if runtime persistence, session authority, removed field families, or public readback contracts change in a breaking way
- shipped-path SQLite proof and Postgres + Docker strong verification are required when the selected work packages change runtime or persistence truth

## Kill-list terms

- separate callback-binding authority as the target model
- fresh-session-per-dispatch as the universal redispatch rule
- mixed node and operator MCP sessions
- `same_session_continue` described as the canonical parent/root redispatch transport
- automatic watchdog `create_new_attempt`
- task-scoped path ids treated as primary node authority
- removed support-state or readback ballast kept alive without a behavior reason
