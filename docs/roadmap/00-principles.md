# 00 — Core Principles

## 1) Runtime truth is relational

Execution decisions come from explicit runtime records, not from free-form transcripts.
Files, blobs, and folders can back payloads, but they are not the authoritative control plane.

## 2) Canonical execution identity

The target execution chain is:

- `task`
- `flow`
- `flow_revision`
- `flow_node`
- `node_attempt`
- `node_checkpoint`

Legacy `runs` / top-level `attempts` are migration debt, not target architecture.

## 3) Compile/runtime separation is strict

Runtime executes immutable compiled output, never mutable source definitions directly.
Published definitions feed the compiler; the compiler emits `compiled_plans`, `compiled_plan_nodes`, and `compiled_plan_edges`; runtime materializes flow state from compiled output.

## 4) Ownership and delegation are orthogonal

- ownership tree = `flow_nodes.parent_flow_node_id`
- delegated execution = `node_sessions`
- a node may own children and still delegate planner/synthesis-heavy work to OpenClaw

Do not collapse “owner node” and “leaf node” into the same concept.

## 5) Shared context is published, not implied

Shared context must be explicit and queryable:

- `context_items` = typed published context metadata
- `context_manifests` = projected context slices for one node attempt

Delegated execution should begin only after manifest projection + acknowledgement.
Do not rely on “please read this first” prompt wording alone.

## 6) Safe adaptation is revision-based

Structural changes happen only through:

- propose
- validate
- compile
- adopt
- activate by revision pointer

Do not mutate graph topology in place during execution.

## 7) Roadmap honesty matters

- phase docs should state target work and removals clearly
- `current.md` should describe the real shipped state
- `backlog.md` should contain deferred work only
- do not blur “target contract” and “already implemented code”
