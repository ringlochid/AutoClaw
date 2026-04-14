# 00 — Core Principles

## 1) Control-plane truth is structural

Execution decisions come from runtime tables, not free-form transcripts.

## 2) Canonical execution identity

A task executes through:

- `task`
- `flow`
- `flow_revision`
- `flow_node`
- `node_attempt`
- `node_checkpoint`

Legacy `run` / top-level `attempt` tables are migration debt.

## 3) Immutable compile provenance

Runtime always executes compiled plans, never raw source definitions.
Every execution must preserve lineage to:

- `workflow_version_id`
- `role_version_id`
- `policy_version_id`
- `skill_version_id`

## 4) Loop and subgraph nodes are capabilities

A loop/subgraph node is a node with capabilities such as:

- `can_spawn_children`
- `can_loop`
- `max_depth`
- `can_replan`

## 5) OpenClaw boundary

OpenClaw owns tool execution and subagent behavior.
AutoClaw owns graph state, checkpoints, approvals, and revisions.

## 6) Safe adaptation

Structural changes happen only through:

- propose
- validate
- compile
- adopt
- activate by revision pointer

## 7) Queryable history

Attempt history, checkpoint history, approval history, and revision history must remain relational and auditable.
