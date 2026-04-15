# 07 — Phase 7: Controller-Driven Looping and Governance

## Goal

Remove accidental idle gaps from the runtime and make implementation-loop behavior explicit without inventing a second state model.

This phase hardens the control path on top of the flow-first runtime that phases 3–6 already established.

## Why this phase exists

The current runtime is now structurally correct and flow-first, but some important control behavior is still spread across several modules and still depends on a follow-up `continue` call to keep the flow moving.

Current gaps:

- `continue_flow()` is the real advancement engine, but safe transitions like approval resolution or a green checkpoint can still leave the flow waiting for another explicit advance call
- implementation-loop behavior exists implicitly across scheduler / runner / approval / watchdog code rather than as one explicit contract
- governance before `sync` is still more implicit than explicit
- observability is snapshot-first; important controller transitions do not yet have a minimum typed event surface

## Assumptions entering this phase

Before this phase starts, the codebase should already have:

- flow-first runtime ownership
- revision-safe graph materialization
- node-attempt history
- approval/watchdog/replan/context-bootstrap semantics
- validated phase-6 max-complexity execution
- no live `/runs` control surface

Do not use this phase to re-litigate the flow-first reset.

## In scope

### 1. Controller-side flow advancement

Add a thin controller helper such as `advance_flow_until_boundary(flow_id, cause)`.

It should run after safe control transitions and advance the flow until it hits a real external boundary.

Expected trigger points:

- explicit `continue`
- context manifest acknowledgement
- approval resolution (`approved` / `not_required`)
- `green` checkpoint
- `retry` checkpoint
- operator retry
- adopted revision / replan activation
- safe watchdog recovery path

### 2. Bounded implementation-loop semantics

Make loop-owner behavior explicit rather than leaving it spread across runtime branches.

That means defining:

- retry budget / loop budget
- retry vs replan boundary
- approval boundary
- explicit stop conditions
- explicit success conditions
- explicit `sync`/terminal-exit criteria

This is the useful concept to borrow from persistent coding loops: not “keep prompting forever”, but “keep moving until one of the declared loop boundaries is reached.”

### 3. Policy extraction for variable decisions

Move variable control decisions into policy when they can differ by workflow, node, or operator preference.

Good policy candidates:

- when approval is required
- which node/role scopes need approval
- what approval means (`resume same attempt` vs `retry` vs `fail`)
- retry budget and watchdog threshold
- scheduler preference when more than one node is runnable
- governance rules before `sync`

Keep invariants hardcoded in runtime:

- every retry creates a new `node_attempt`
- every adopted structural change creates a new `flow_revision`
- no execution before context acknowledgement
- auditability and relational control truth remain mandatory

### 4. Minimum typed runtime/operator events

Add a thin typed event surface for observability and console timelines.

Examples:

- `context_manifest_projected`
- `context_manifest_acked`
- `approval_requested`
- `approval_resolved`
- `checkpoint_recorded`
- `watchdog_blocked`
- `revision_adopted`
- `sync_ready`

These events are facts for auditability and UI. They should not become a second control system.

### 5. Session continuity without a second state model

Use existing `node_sessions` for continuity where appropriate, especially for persistent implementation-loop owners.

Do **not** add a parallel session-scoped active-state runtime.

## Explicit non-goals

- do not add a second mode/session state machine parallel to `flow` / `flow_node` / `node_attempt`
- do not import an oh-my-codex-style global active-state model
- do not import a Claude-style plugin/hook framework as the main runtime architecture
- do not make transcript text the control truth
- do not reintroduce `run`-style wrappers or top-level attempts
- do not solve liveness by blindly sending repeated “continue” prompts to delegated workers

## Allowed implementation shape

A shared internal transition helper is allowed **only** as a refactor over existing runtime records.

That helper must:

- reduce duplicated handoff logic across runtime modules
- stay internal to the controller/runtime layer
- avoid becoming a new user-visible ontology

If it does not delete real duplication from scheduler / runner / approval / watchdog logic, skip it.

## Runtime records exercised by this phase

Start with the existing flow-first records:

- `flows`
- `flow_revisions`
- `flow_nodes`
- `flow_edges`
- `node_attempts`
- `node_checkpoints`
- `approvals`
- `node_sessions`
- `node_plan_revisions`
- `context_manifests`

Do not add new durable tables up front unless the minimum typed event surface cannot be expressed sanely on top of existing records.

## Exit criteria

The phase is complete when all of the following are true:

- safe control transitions no longer leave the flow accidentally idle
- a loop-owner node has explicit bounded retry/replan/approval/governance semantics
- governance before `sync` is enforced by explicit evidence/gate rules rather than prompt convention
- important controller transitions are observable without transcript scraping
- no redundant parallel mode/session state model was added
