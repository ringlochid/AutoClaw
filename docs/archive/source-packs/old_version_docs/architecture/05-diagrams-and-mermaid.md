# Diagrams and Mermaid

## 1) Canonical execution identity

```mermaid
flowchart TD
  task[Task] --> flow[Flow]
  flow --> rev[Active flow revision]
  rev --> root[root loop node]
  root --> child[leaf or subgraph node]
  child --> attempt[Node attempt]
  attempt --> checkpoint[Node checkpoint]
```

## 2) OpenClaw delegation boundary

```mermaid
sequenceDiagram
  autonumber
  participant API as AutoClaw API
  participant Ctrl as Runtime Controller
  participant OCL as OpenClaw

  API->>Ctrl: start flow
  Ctrl->>Ctrl: create node_attempt
  Ctrl->>OCL: dispatch delegated node with prompt + context
  OCL-->>Ctrl: checkpoint(green/retry/blocked)
  Ctrl->>Ctrl: update node_attempt + flow_node + flow state
```

## 3) Full target graph — max-complexity (exact reference)

```mermaid
flowchart TD
  ROOT[root] -->|owns| DISC[root.discovery]
  ROOT -->|owns| PROD[root.product]
  ROOT -->|owns| IMPL[root.implementation_loop]
  ROOT -->|owns| VAL[root.validation]
  ROOT -->|owns| SYNC[root.sync]
  PROD -->|owns| ARCH[root.product.architecture]
  PROD -->|owns| PMAT[root.product.product_plan]
  IMPL -->|owns| CYCLE[root.implementation_loop.cycle]
  IMPL -->|owns| BUGFIX[root.implementation_loop.bugfix]
  ROOT -->|owns| REV[root.review_and_governance]
  REV -->|owns| SEC[root.review_and_governance.security]
  REV -->|owns| RISK[root.review_and_governance.risk]

  DISC --> PROD
  DISC --> IMPL
  PROD --> IMPL
  IMPL --> VAL
  VAL --> REV
  REV -->|approved| SYNC
  REV -->|escalate| ROOT

  ROOT -->|dispatch| O_ROOT["OpenClaw session<br/>root"]
  DISC -->|dispatch| O_DISC["OpenClaw session<br/>root.discovery"]
  ARCH -->|dispatch| O_ARCH["OpenClaw session<br/>root.product.architecture"]
  PMAT -->|dispatch| O_PMAT["OpenClaw session<br/>root.product.product_plan"]
  CYCLE -->|dispatch| O_CYCLE["OpenClaw session<br/>root.implementation_loop.cycle"]
  BUGFIX -->|dispatch| O_BUGFIX["OpenClaw session<br/>root.implementation_loop.bugfix"]
  VAL -->|dispatch| O_VAL["OpenClaw session<br/>root.validation"]
  SYNC -->|dispatch| O_SYNC["OpenClaw session<br/>root.sync"]
  SEC -->|dispatch| O_SEC["OpenClaw session<br/>root.review_and_governance.security"]
  RISK -->|dispatch| O_RISK["OpenClaw session<br/>root.review_and_governance.risk"]

  classDef owner fill:#eef,stroke:#515,stroke-width:1px
  classDef ocl fill:#f4f4f4,stroke:#666,stroke-dasharray:3 3
  class ROOT,PROD,IMPL,ARCH,PMAT,CYCLE,BUGFIX,REV,SEC,RISK,VAL,SYNC,DISC owner
  class O_ROOT,O_DISC,O_ARCH,O_PMAT,O_CYCLE,O_BUGFIX,O_VAL,O_SYNC,O_SEC,O_RISK ocl
```

## 4) Legend

- **Solid `owns` edges** = ownership tree (`parent_flow_node_id`)
- **Solid direct edges** = runtime dependency/order constraints (`flow_edges`)
- **Dashed boxes** = delegated OpenClaw execution context for delegated nodes (not necessarily leaves)
- **Node attempt / checkpoint lifecycle** = execution history, not topology

## 5) Detailed target walk-through

For the full explicit step-by-step narrative, use:

- `../../../../flows/06b-max-complexity-workflow-full.md`
