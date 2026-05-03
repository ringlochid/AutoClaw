# ADR-0005: Relational Runtime Model and Iteration Loops

## Status

Accepted

## Decision

Represent loop behavior and execution history relationally.

- the whole execution container is `flow`
- retries/iterations live in `node_attempts`
- topology lives in `flow_nodes` plus `flow_edges`
- ownership is from `parent_flow_node_id`
- checkpoints are attached to one `node_attempt`

## Consequence

This gives queryability for:

- per-node retry history
- approval/watchdog recovery
- revision-aware execution lineage
- effective workflow / role / policy / skill provenance
