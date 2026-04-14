# Control Plane and Query Model

## Core tables (target)

### `flows`

- `id`, `task_id`, `status`, `active_plan_revision_id`, `root_node_id`

### `flow_nodes`

- `id`, `flow_id`, `parent_node_id`, `node_key`, `node_path`, `role_version_id`, `policy_version_id`
- static capabilities: `can_spawn_children`, `can_loop`, `max_depth`

### `flow_node_state`

- `flow_node_id`, `state`, `active_attempt_id`, `active_session_id`, `last_checkpoint_id`, `finish_confidence`

### `node_attempts`

- per-node execution history
- attempt number, status, failure signature, outcome

### `node_sessions`

- OpenClaw session/thread binding

### `node_checkpoints`

- typed result boundary: `status`, `summary`, `failure_signature`, `recommended_next_action`

### `flow_edges`

- sparse dependency rules only
- not ownership edges

### `node_plan_revisions` and `flow_revisions`

- patch proposal and adoption history

## Query model split

- Current state: relational queries on `flow_node_state`, `flows`, `node_sessions`
- Timeline/history: `node_attempts`, `node_checkpoints`, `node_plan_revisions`
- Structural snapshot: `flow_nodes` + `flow_edges`

## Sourcing a subtree

Use `parent_node_id` + recursion to materialize a node-rooted subgraph.

## Why no single giant JSONB

Reliability needs indexed joins, constraints, and history tracking.
JSONB remains only for flexible payloads.
