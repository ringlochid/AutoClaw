# 00 — Core Principles

## 1) Control-plane truth is structural

Execution decisions are made from runtime tables, not from free-form transcripts.

## 2) One flow per task execution

A flow is the full graph for one top-level execution of a task.

- `flow_nodes` stores tree ownership (`parent_node_id`)
- `flow_edges` stores only additional execution constraints
- node checkpoint boundaries trigger state transitions

## 3) Loop and subgraph nodes are capabilities, not separate entity types

A loop/subgraph node is a node with role capabilities such as:

- `can_spawn_children`
- `can_loop`
- `max_depth`
- `can_replan`

Leaf nodes may not own children.

## 4) OpenClaw boundary

OpenClaw owns subagent behavior and tool execution.
AutoClaw owns node intent, session binding, checkpoints, and orchestration.

## 5) Safe adaptation

Shape changes happen only through revision workflow:

- propose
- validate
- compile
- adopt
- update live graph by insert/retire

## 6) Reliable query model

Keep JSONB for flexible payloads only.
Keep control and history relationals in standard columns with indexes.
