# System Overview

AutoClaw is a controller + compiler for long-running adaptive workflows.
It is not a single agent engine; it is a graph-based supervisor with deterministic plan control.

## Core execution units

- `flow`: full graph instance for a task execution
- `flow_node`: one node in that graph
- `flow_edges`: optional dependency constraints
- `flow_node_state`: current state per node
- `node_attempt`: per-node execution iteration/history

## Execution boundaries

- AutoClaw controls graph/state/checkpoints.
- OpenClaw performs delegated tool execution.

## Default vs max complexity

- default: single loop-path flow with bounded subtree behavior
- max-complexity: committee branches, multi-path joins, deeper subgraphs, staged replans

## Design safety

- no hidden graph mutation from transcript
- no full runtime state in one JSONB blob
- revisioned changes only for shape updates
