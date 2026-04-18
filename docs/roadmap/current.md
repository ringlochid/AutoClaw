# Current Roadmap Status

## Status summary

The runtime reset has landed.
The codebase and target docs still align on the flow-first runtime model.

The OpenClaw bridge is now **materially working**, not just contractual:

- real AutoClaw → OpenClaw dispatch over Gateway `POST /v1/responses`
- stable delegated session routing through `node_sessions.provider_session_key`
- SSE idle-timeout hardening plus terminal-event enforcement
- live approval and replan callback paths passing
- manifest-ack UUID normalization for the observed malformed-but-recoverable callback shape
- a fresh max-complexity flow reaching terminal success

Do **not** overclaim the current state:

- one review/governance node still needed an operator nudge because downstream evidence propagation is still thin
- watchdog recovery now has a controller-owned same-session wake path, but safe-retry semantics and broader operator policy are still incomplete
- broader shared/untrusted-worker trust hardening is not finished yet

That means AutoClaw is good enough to start **Phase 9 local-first packaging work now**, while still carrying a small Phase 7/8 closeout list.

## Live contract

The current implementation treats this as authoritative:

- `task`
- `flow`
- `flow_revision`
- `flow_node`
- `node_attempt`
- `node_checkpoint`
- `node_sessions`
- `context_items`
- `context_manifests`

## Legacy status

These legacy structures are now historical, not live implementation:

- `runs`
- top-level `attempts`
- `flows.attempt_id`
- `approvals.run_id`
- `approvals.attempt_id`
- run-scoped routes / services
- `flow_nodes.iteration_index`-style execution-history modeling

## Current focus

- finish Phase 8 closeout honestly instead of leaving stale blocker text in docs
- start Phase 9 packaging / local-first productization in parallel
- freeze explicit local-first conventions for task root materialization, definition discovery, and typed node handoff instead of leaving them as repo lore
- define a logical task/runtime packaging layer before backend tables, mounts, and side effects sprawl through the core runtime
- finish the Phase 7 follow-up semantics that still affect autonomy:
  - watchdog recovery
  - governance/evidence propagation
  - explicit loop/governance policy extraction
- queue Phase 10 before rich authoring/editor work
- queue Phase 11 for graph/operator/definition-authoring surfaces after the semantic contract is explicit
- queue a later post-core phase for broader OpenClaw-side AutoClaw inspect/operator/plugin surfaces only after AutoClaw itself is stable and working end-to-end
- allow bounded reliability-oriented worker/query plugin surfaces earlier when they improve deterministic replan/review behavior without shifting control ownership
- avoid reintroducing compatibility surfaces that blur `flow` vs `run`

## Verified bridge/runtime state

What is already real in code/tests/live validation:

- real AutoClaw → OpenClaw dispatch via Gateway `POST /v1/responses`
- plugin-backed callback path with no per-request client tool definitions
- controller-side bridge selection/build logic in `app/services/openclaw_bridge.py`
- stable session continuity via `node_sessions.provider_session_key`
- bootstrap/execution phase split in the bridge
- SSE hardening in `app/integrations/openclaw.py`
- live approval path passing
- live replan path passing
- manifest-ack route hardened against the observed extra-hyphen UUID callback shape
- a fresh max-complexity flow succeeding end-to-end on the host-native API path

## Phase 7 follow-up still open

Phase 7 is no longer blocked on the basic controller-advancement cutover, but a few semantics are still thinner than the target contract:

- implementation/governance loop policy is still more implicit than ideal
- watchdog now supports a controller-owned bounded same-session wake + explicit escalation path, but not the full auto wake/retry/escalate loop yet
- downstream review/governance nodes do not automatically get rich enough flow-local evidence for normal fully hands-off execution
- the minimum typed runtime/operator event surface exists, but graph/timeline ergonomics remain thin

## Phase 8 closeout — what is still not fully green

Before Phase 8 should be called **fully closed**, finish these closeout items:

- truth-sync docs so roadmap/E2E docs stop describing the bridge as still fundamentally blocked
- finish truth-sync so docs describe the now-implemented runtime recovery behavior accurately:
  - `response.failed` is treated as terminal bridge failure
  - ambiguous execution/wake timeouts require inspect-before-retry operator guidance
  - watchdog wake dispatch failure returns the node to safe blocked state
  - watchdog wake timeout is treated as ambiguous delivery: keep the attempt/session resumable and require inspect-before-retry guidance
  - wake budget is tracked per node attempt
- improve evidence propagation so review/governance nodes do not need manual nudges on healthy successful flows
- tighten callback trust boundaries before broader shared/untrusted-worker claims:
  - hash/session/capability validation where appropriate

Important nuance:

- the last item is **not** a blocker for local-first/single-user Phase 9
- it **is** a blocker for stronger claims about shared or less-trusted worker environments

## Ordered plan from the current issues

### 1. Truth-sync the docs now

Update the docs so they match the real state:

- the bridge works
- Phase 9 can start
- there are still residual caveats around watchdog recovery, governance evidence, and broader trust hardening

### 2. Harden bridge trust and callback identity next

The next reliability work should make callbacks and resumes bind to the real delegated execution identity, not just broad flow/node references.
Define, test, and truth-sync:

- `record_checkpoint` reliability and failure handling
- hash/session/capability validation where appropriate
- binding checks around `provider_session_key`, `manifest_hash`, attempt identity, and checkpoint acknowledgement state
- explicit use of `ack_checkpoint_id` or equivalent acknowledgement state so resume/retry semantics are deterministic

### 3. Freeze runtime recovery rules and typed handoff semantics

Do not leave liveness/recovery semantics as scattered implementation behavior.
Define, test, and truth-sync:

- execution timeout handling
- `response.failed` handling
- watchdog same-session wake / operator retry / escalation rules
- explicit operator guidance for ambiguous timeout states ("inspect flow state before blind retry")

This is also the main autonomy gap exposed by the latest successful run.
Make review/governance nodes consume richer first-class flow-local evidence rather than relying on prompt luck or operator nudges.

That follow-through should explicitly freeze the node handoff model:

- do not rely on private prompt-to-prompt whispering between workers
- use typed checkpoint/context-item publication plus task workspace/context artifacts as the default handoff path
- add a first-class typed handoff publication tool only if the current checkpoint-only channel proves too thin

### 4. Freeze local-first defaults immediately

Phase 9 can proceed now because packaging/local-first installability does not require the runtime to already be perfectly hands-off.
But do **not** smuggle major authoring/editor rewrites into Phase 9.

Land the productized defaults explicitly:

- packaged definitions are the default bootstrap/discovery source
- configured filesystem definitions roots are the explicit override path
- definition identity remains stable (`key == filename stem == YAML id`)
- task-local filesystem materialization defaults under `<data_dir>/tasks/<full-task-id>/{workspace,context,manifests}` while DB keys and logical URIs stay canonical

### 5. Add the logical task/runtime packaging layer

Phase 9 should also freeze the logical packaging/runtime boundary:

- `TaskImage` = immutable reusable seed/template for task environment defaults
- `TaskCompose` = live task environment topology for one task
- `RuntimeImage` = immutable node execution contract
- `RuntimeContainer` = live node execution instance

This should be a backend-agnostic control-plane abstraction, not a Docker-first rewrite.
The first backend can still be an OpenClaw session plus task-owned filesystem/object-storage roots.

### 6. Add a bounded but semantics-thick OpenClaw plugin query surface

For reliability, do not force replan/review work to reconstruct truth from prompts or many tiny calls.

Near-term plugin/query surface should be:

- rich on deterministic read/query semantics
- able to assemble stable bundles across definitions, resources, runtime state, manifests, checkpoints, approvals, and recent events/log slices
- bounded in authority so it does not own scheduling, approval resolution, or replan adoption

This is earlier than the full later-stage operator/plugin phase because it improves execution reliability rather than broadening operator automation.

### 7. Finish Phase 10 before rich authoring UI

Add explicit effective-node semantics first:

- role / workflow / node / replan precedence
- first-class node description semantics
- node-local effective skill bindings
- merged semantic validation

### 8. Then build the richer graph/operator/authoring surface in Phase 11

Only after packaging is real and compiler semantics are explicit should the console grow into:

- a graph-native operator surface
- richer definition authoring
- n8n-style workflow editing
- better skill reference UX

### 9. Only after that, consider the broader OpenClaw-side AutoClaw operator/plugin surface

This is explicitly **later** than making core AutoClaw solid.
If pursued, it should let OpenClaw inspect AutoClaw definitions/runtime and perform broader scoped authoring/operator actions through AutoClaw APIs, but only after the core product/runtime semantics are already stable and trustworthy.

## Current phase mix

### Phase 8 — bridge closeout

Phase 8 is no longer “bridge might work someday.”
It is now “bridge works, but closeout honesty and recovery semantics still need to be finished.”

See:

- `08-phase-8-production-openclaw-bridge-and-native-plugin-adapter.md`
- `../e2e/phase8-happy-path.md`

### Phase 9 — local-first packaging and distribution

Phase 9 can start now:

- package install becomes the primary user path
- bundled console/assets/definitions become product resources
- SQLite becomes the supported local path
- Postgres remains the production-strength path
- local task workspace/context/manifest materialization should default under the platform data dir with full task ids, while DB keys and logical URIs stay canonical
- definition bootstrap/discovery should make packaged resources the default source and keep stable key rules explicit (`key == filename stem == YAML id`)
- the runtime/package contract should grow a logical `TaskImage` / `TaskCompose` / `RuntimeImage` / `RuntimeContainer` layer so backend-specific mounts, services, and logs do not leak everywhere
- current code already carries task-owned bindings plus manifest projection for `workspace`, `context`, `image`, `compose`, and `container`, but the explicit `task_images` / `task_composes` / `runtime_images` / `runtime_containers` lifecycle is still a target abstraction, not live schema/runtime code yet

See:

- `09-phase-9-local-first-packaging-and-distribution.md`

### Phase 10 — effective-node compiler semantics and authoring safety

Phase 10 remains the prerequisite for safe rich authoring.
It should define explicit merge precedence and effective-node meaning before AutoClaw grows a more ambitious editor surface.

That includes the remaining skill-reference and task-resource follow-through:

- parse/index `SKILL.md` frontmatter into the AutoClaw pin/provenance layer
- carry `runtime_name`, manifest summary, and artifact metadata in node-local compiled skill bindings
- define first-class workspace/context binding semantics and compile them into node-local effective payloads
- add explicit resource binding modes such as `use_existing`, `ensure_task_primary`, `ensure_task_root`, `clone_from`, and `seed_from`
- make dispatch fail closed when a node marks a skill or task resource as `required` but the delegated session cannot materialize or verify it
- make compiled effective-node meaning strong enough to drive a stable `RuntimeImage` spec without re-reading raw authoring defaults at dispatch time

See:

- `10-phase-10-effective-node-compiler-semantics-and-authoring-safety.md`

### Phase 11 — graph/operator surfaces and definition authoring

Queue this only after Phase 10 semantics are explicit.
This is where graph-native operator views, node descriptions, safe console authoring, TaskSpec/task-resource UX, skill reference UX, and task/runtime packaging inspection should land.
Manifest artifact files should remain materialized exports or audit copies; `context_manifests` rows remain the execution/audit truth.

See:

- `11-phase-11-graph-operator-surfaces-and-definition-authoring.md`

### Phase 12 — OpenClaw operator/plugin surfaces for AutoClaw

This is a later-stage expansion, not a prerequisite for the core product.
Only queue this after AutoClaw itself is operationally solid.

Target direction:

- deep OpenClaw-side inspection of AutoClaw definitions, compiled plans, tasks, flows, manifests, approvals, and runtime state
- semantics-thick but authority-thin query/bundle surfaces, with deterministic joins and stable snapshot semantics rather than transcript reconstruction
- OpenClaw should consume typed task-image/task-compose/runtime-image/runtime-container surfaces rather than inventing a second runtime abstraction
- scoped draft/create/validate/publish flows for AutoClaw definitions through AutoClaw APIs
- scoped runtime operator actions through AutoClaw APIs
- strict separation between read surfaces, draft/publish surfaces, and live runtime/operator control

See:

- `12-phase-12-openclaw-operator-plugin-and-definition-automation.md`

## Explicitly not next stage

- no n8n-style graph editor before compiler semantics are explicit
- no raw skill-package hosting/upload as the default AutoClaw contract
- no transcript-derived control truth
- no separate session-scoped active-state model parallel to `flow` / `flow_node` / `node_attempt`
- no “keep pinging continue” liveness workaround as runtime design
- no powerful OpenClaw-side AutoClaw authoring/operator plugin before the core AutoClaw product/runtime is already working and trustworthy

## Implementation baseline

- fresh Alembic history starts at `apps/api/alembic/versions/20260414_0001_fresh_initial_schema.py`
- runtime API surface is split into:
  - public/operator routes under `/flows` and approval resolution under `/approvals`
  - internal audit/control routes under `/internal/...`
  - public health under `/healthz` and `/readyz`
- `AUTOCLAW_INTERNAL_API_KEY` is a superset credential today: it can call `/internal/...` and the public/operator routes; the console should still use the operator key by default
- `/flows/{flow_id}/operator` is the compact operator summary
- `/internal/flows/{flow_id}/audit` is the full audit/debug view
- raw checkpoint/context-manifest/watchdog/compiler/bootstrap/internal approval-create routes are intentionally internal-only
- `continue_flow()` is now a thin poll/invoke boundary for manual wakeups; safe transitions on major mutation paths auto-advance when possible
- database verification should use the Docker-backed repo flow from `docs/roadmap/suggestion.md`

## Reading note

This roadmap mixes current implementation baseline, accepted target semantics, and queued follow-through work.
For exact ownership/editability/runtime-truth rules, prefer the architecture docs and ADRs over shorthand roadmap bullets.

## Why this reset matters

This gives a cleaner model where:

- `flow` is the whole execution container
- `flow_revision` owns executable graph snapshots
- `node_attempt` is the execution container for one specific node
- history and provenance are queryable without transcript inspection
- shared context is published and projected through explicit runtime metadata, not hidden prompt residue
