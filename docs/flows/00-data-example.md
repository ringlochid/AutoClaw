# Flow 00 — Example: Data Model Snapshot

This example uses a task called `repair-bugfix`.

## Runtime tables in this snapshot

### flow

- `flow.id = flow_repair_bf_001`
- `task_id = task_repair_bf_001`
- `status = running`

### flow_nodes

- `node_root` (`node_kind = loop`, can spawn)
- `node_impl_loop` (`node_kind = loop`, can_loop = true)
- `node_discovery` (`node_kind = leaf`)
- `node_validation` (`node_kind = leaf`)

### node_sessions

- `node_impl_loop` -> `session_impl_openclaw_001`

### node_attempts

- `node_impl_loop` has attempt 1 and 2

### node_checkpoints

- attempt 1: `status=retry`
- attempt 2: `status=blocked` + `recommended_next_action=replan`

### flow_edges (sparse)

- `discovery -> impl_loop`
- `impl_loop -> validation`
- `validation -> sync`

## Replan behavior

When blocked and approved for replan:

1. proposal row created in `node_plan_revisions`
2. new compiled plan revision created
3. new `flow_nodes` / `flow_edges` inserted
4. old edges marked retired by revision
5. flow status remains running with updated revision pointer

## Checkpoint boundary rule

A checkpoint always triggers state transition logic, it does not directly mutate the graph.
