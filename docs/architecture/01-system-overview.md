# System Overview

AutoClaw is a controller + compiler for long-running adaptive workflows.
It is not a single-agent engine; it is a graph-based supervisor with deterministic plan control.

## Canonical execution identity

The target runtime model is:

- `task` — business job / operator-visible unit of work
- `flow` — one concrete execution graph for a task
- `flow_revision` — one adopted executable revision of that flow
- `flow_node` — a node in the graph
- `node_attempt` — one concrete execution attempt of a specific node
- `node_checkpoint` — a typed boundary/result emitted by a node attempt

## Version provenance

AutoClaw should always be able to answer:

- which `workflow_version` produced this flow revision
- which `role_version` and `policy_version` applied to this node
- which `skill_version_id` values were bound for this node

The provenance chain is:

- `flow_revision.compiled_plan_id`
- `compiled_plans.workflow_version_id`
- `flow_nodes.source_compiled_plan_node_id`
- `compiled_plan_nodes.role_version_id`
- `compiled_plan_nodes.policy_version_id`
- `compiled_plan_nodes.skill_bindings[*].skill_version_id`
- `task_composes.compiled_plan_id` for the task-scoped launch binding that selected this workflow meaning

## Execution boundaries

- AutoClaw controls graph state, checkpoints, revisions, approvals, and orchestration.
- OpenClaw performs delegated tool execution.
- Runtime truth is relational and revision-safe.

Boundary summary:

- workflow = reusable orchestration definition (roles, skills, policies, graph/defaults)
- task compose = small task-scoped start surface and launch record
- task = internal runtime/control-plane record materialized from task compose start
- runtime = live execution facts (flows, revisions, attempts, sessions, approvals, manifests, replans)

## Default vs max complexity

- default: single-path, tree-owned flow with simple retries
- max-complexity: nested subgraphs, join edges, review branches, staged replans

## Design safety

- no hidden graph mutation from transcript
- checkpoints are the control boundary
- large JSON payloads are supplemental, not workflow truth
- structural change happens by revision adoption, not direct hot mutation

## Runtime implementation note

The runtime is now flow-first: `task -> flow -> flow_revision -> flow_node -> node_attempt`.
Legacy `runs` and top-level `attempts` are no longer part of the live schema or API surface.
