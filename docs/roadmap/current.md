# Current Roadmap Status

Status: current backend/runtime completion record
Last verified: 2026-04-20

This file tracks completed backend/runtime work using checked boxes.
Use `next.md` for active unfinished backend-only work.
UI/editor/authoring work is intentionally excluded from this file.

## Verified baseline

- [x] `make format-api` passes
- [x] `make check-api` passes
- [x] `make test-api` passes
- [x] `make test-api-db` passes

## Completed by phase

### Phase 1 to 4 — foundations

- [x] Published definitions compile into immutable plans
- [x] The flow-first runtime model is live: `task -> flow -> flow_revision -> flow_node -> node_attempt -> node_checkpoint`
- [x] Control truth remains relational rather than transcript-derived
- [x] Operator read surfaces exist for inspect, audit, runtime slice, and timeline slice

### Phase 5 — replan, watchdog, approval, recovery semantics

- [x] Checkpoint statuses (`green`, `retry`, `blocked`, `needs_approval`) are runtime control facts
- [x] Approval lifecycle is explicit and auditable
- [x] Watchdog can block stale attempts and record watchdog checkpoints
- [x] Structural replans are auditable through `node_plan_revisions` and `flow_revisions`

### Phase 7 — controller-driven looping and governance baseline

- [x] Safe control edges auto-advance through the controller path
- [x] Approval resolution and context acknowledgement resume through controller advancement
- [x] A shared flow-boundary snapshot now reduces duplicated boundary classification in the runner path
- [x] The runtime no longer depends on manual `continue` calls for the key safe mutation edges that were stabilized in this pass

### Phase 8 — bridge and callback baseline

- [x] Real AutoClaw to OpenClaw dispatch works through the Responses gateway path
- [x] Callback-bound writes use session/manifest/ack lineage validation
- [x] Session continuity is carried through `node_sessions.provider_session_key`
- [x] Worker-bundle, runtime-slice, timeline-slice, and audit reads exist and are test-backed

### Phase 9 — local-first packaging and runtime packaging baseline

- [x] Package-first CLI/service substrate exists
- [x] Packaged definitions are the default bootstrap source with explicit filesystem override precedence
- [x] Task-owned materialization roots are used under the AutoClaw data directory
- [x] Task-compose-first start exists as the public launch surface

### Phase 10 — compiler semantics baseline

- [x] Effective-node merge semantics are test-defined
- [x] Compiled node payloads carry effective task defaults and node-local resource intent
- [x] Runtime/replan no longer depends on compiler-private `_merge_*` helpers

### Phase 13 — runtime stabilization and carry-forward cleanup landed

- [x] Task compose launch truth survives upload refresh and remint paths
- [x] Partial root selections for compose start are now handled correctly
- [x] Upload writes enforce resolved root containment and reject symlink/root escapes
- [x] Callback binding extraction and attempt-binding validation are centralized enough to be reused across checkpoints, approvals, replan, manifest ack, and worker-bundle access
- [x] Worker-bundle and start-route readback use runtime read-model snapshots instead of hand-assembled route queries
- [x] Registry bootstrap tests are less brittle and now include idempotence coverage
- [x] Unsupported `workflow.entrypoint` is rejected explicitly instead of being ignored silently
- [x] Front-door docs and contract docs were truth-synced to the current repo state

## Current state summary

- [x] The OpenClaw bridge is materially working
- [x] The runtime-stabilization pass is closed
- [x] The remaining work is follow-on backend cleanup, not foundational bring-up
- [x] The current repo should be described as a stabilized baseline with follow-on cleanup remaining

## Read next

- `next.md` — unchecked backend-only work still remaining
- `backlog.md` — deferred work only
- `00-principles.md` — invariants
- `../architecture/README.md` — reference contracts
