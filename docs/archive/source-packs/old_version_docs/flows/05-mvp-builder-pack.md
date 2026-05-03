# Flow 05 — MVP Builder Pack

## Scope

A practical starter graph for product-safe execution.

## Required nodes

- root loop node
- discovery loop node
- implementation loop node
- validation node
- sync node

## Constraint model

- subgraph is ownership-based
- dependency edges are only for cross-branch ordering

## Runtime note

This file describes the starter graph shape only.
Execution history still follows the canonical runtime model:

- `flow_revision` for adopted graph state
- `node_attempts` for per-node execution/retry history
- `node_checkpoints` for typed control boundaries
