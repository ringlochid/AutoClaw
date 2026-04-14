# ADR-0005: Relational Runtime Model and Iteration Loops

## Status

Accepted

## Decision

Represent loop behavior and state relationally.

- no raw graph back-edge rewrite for loops
- loop state lives in `node_attempts` and node status
- ownership is from `parent_node_id`
- constraints from `flow_edges`

## Consequence

This gives queryability for retries, stalled loops, and completion confidence.
