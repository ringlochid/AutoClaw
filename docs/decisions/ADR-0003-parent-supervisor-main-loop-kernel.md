# ADR-0003: Parent Supervisor + Main Loop Child Kernel (Reframed)

## Status

Accepted

## Decision

A loop/subgraph node is a *role capability* within `flow_nodes`.

- parent node is any node with `can_spawn_children=true`
- child execution is delegated to OpenClaw via `node_sessions`
- OpenClaw manages tool-level runtime
- AutoClaw manages graph and checkpoint transitions

Thus there is no separate long-lived child-node entity in AutoClaw; the relationship is delegation-based.
