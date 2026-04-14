# 03 — Phase 3: Runtime and OpenClaw Integration

## Goal

Execute compiled plans through a checkpoint-driven control kernel with OpenClaw delegation.

## In scope

- start flow from compiled plan
- dispatch leaves to OpenClaw sessions
- checkpoint ingestion
- basic approval/blocked handling

## Notable behavior

- Node role decides whether node can spawn or loop.
- Parent node is a loop/subgraph owner node.
- Child execution is performed by OpenClaw delegate via session binding.

## Explicit out-of-scope

- full max-complexity scheduling
- multi-committee orchestration
- global replan fan-out

## Next requirement

- explicit `flow_edges` and `node_state` tables for deterministic scheduling.
