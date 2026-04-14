# Flow 06 — Max-Complexity Supported Workflow (Compact)

Practical operator-facing summary.

The full target graph lives in `06b-max-complexity-workflow-full.md`.

## Intent

This is the **phase-6 target** for adaptive work:

- nested loop/subgraph nodes,
- explicit review/committee branches,
- checkpoint-driven state transitions,
- safe revision-based replanning.

## Current state (reality check)

- Default kernel is in place.
- This flow target is not fully implemented yet.

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

- `root`, `product`, and `implementation_loop` are loop/subgraph nodes.
- leaf nodes are dispatched to OpenClaw and return typed checkpoints.
- cross-branch ordering and wait/join behavior uses `flow_edges`.
- rework/replan goes through proposal -> validate -> compile -> adopt.

## Quick transition rules

- `discovery` -> `product`
- `product` -> `implementation_loop`
- `implementation_loop` -> `validation`
- `validation` -> `review_and_governance`
- `review_and_governance` -> `sync` (approved)
- `review_and_governance` -> `root` (blocked/high-risk escalation)

## If you want the full graph

- `docs/flows/06b-max-complexity-workflow-full.md` (full target shape with ownership + OpenClaw dispatch annotation)
