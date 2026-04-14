# Current Roadmap Status

## Today

- **Phase 3 kernel is implemented** at a basic level (compile, flow start, checkpoint transitions, approvals).
- The current repo still has older `run/attempt` naming in parts of implementation.
- The runtime target has moved to **flow-centric, node-first control**.

## Near-term target

- `flow` = full execution graph for a task
- `flow_node` = immutable node identity in graph
- `flow_node_state` = current execution state
- `flow_edges` = sparse dependency constraints only
- `node_attempts` = per-node execution history
- `node_sessions` = OpenClaw context binding
- `node_plan_revisions` / `flow_revisions` = replan history

## Max-complexity status

The max-complexity workflow is the **Phase 6 target**, not fully in code yet.

- loop/subgraph orchestration: design target
- committee branches: design target
- revisioned replan + safe adoption: design target

## Where to read the exact target

- compact target summary: `docs/flows/06-max-complexity-workflow.md`
- exact target shape + delegation map: `docs/flows/06b-max-complexity-workflow-full.md`
