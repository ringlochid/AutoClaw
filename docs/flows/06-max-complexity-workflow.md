# Flow 06 — Max-Complexity Supported Workflow (Compact)

Practical operator-facing summary.

The full target flow lives in `06b-max-complexity-workflow-full.md`.

## Intent

This is the phase-6 target for adaptive work:

- nested loop/subgraph owners
- explicit review/committee branches
- node-attempt execution history
- flow-revision replan history
- pinned workflow / role / policy / skill provenance

## Current state (reality check)

- the current codebase is still migrating off legacy `run` / top-level `attempt`
- this target is not fully implemented yet

## Fast path

```text
root
├─ root.discovery
├─ root.product
│  ├─ root.product.architecture
│  └─ root.product.product_plan
├─ root.implementation_loop
│  ├─ root.implementation_loop.cycle
│  └─ root.implementation_loop.bugfix
├─ root.validation
├─ root.review_and_governance
│  ├─ root.review_and_governance.security
│  └─ root.review_and_governance.risk
└─ root.sync
```

## Runtime semantics (compact)

- `flow` is the execution container
- `flow_revision` is the active executable graph revision
- `flow_nodes` own topology and state
- `node_attempts` record actual execution slices and retries
- `node_checkpoints` are the typed control boundary
- `flow_edges` handle joins and cross-branch constraints
- replan goes through proposal -> validate -> compile -> adopt
