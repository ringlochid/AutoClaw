# Diagrams and Mermaid

This file collects repo-local Mermaid diagrams for the current AutoClaw V2.1 design.

Use these as **communication aids**, not as the sole source of truth.
When a diagram and the architecture/ADR docs drift, update both.

## 1. System map

```mermaid
flowchart LR
    subgraph Source[Source definitions]
        RD[Role definitions]
        PD[Policy definitions]
        WD[Workflow definitions]
        SR[Skill refs to OpenClaw-managed skills]
    end

    REG[Registry / published versions]
    COMP[Deterministic compiler]
    CPL[Compiled plan revision]
    RT[Runtime instance]
    EVT[Checkpoints / approvals / plan revisions]
    UI[Operator console]

    RD --> REG
    PD --> REG
    WD --> REG
    SR --> REG
    REG --> COMP
    COMP --> CPL
    CPL --> RT
    RT --> EVT
    EVT --> RT
    RT --> UI
    EVT --> UI
```

## 2. Default end-to-end runtime path

```mermaid
sequenceDiagram
    participant User
    participant API as API / Controller
    participant Registry
    participant Compiler
    participant Runtime
    participant Parent as Parent Supervisor
    participant Child as Main Loop Child

    User->>API: Start task / run
    API->>Registry: Resolve published versions
    API->>Compiler: Compile normalized plan
    Compiler-->>API: Compiled plan revision
    API->>Runtime: Instantiate run / attempt / flow
    Runtime->>Parent: Start parent loop
    Parent->>Child: Dispatch child under current plan
    Child-->>Parent: Typed checkpoint
    Parent-->>Runtime: Continue / review / block / finish
    Runtime-->>API: Updated run state
    API-->>User: Current status
```

## 3. Control-plane storage layers

```mermaid
flowchart TD
    subgraph Registry[Definition registry]
        R1[role_definitions / role_versions]
        R2[policy_definitions / policy_versions]
        R3[workflow_definitions / workflow_versions]
        R4[skill_registry / skill_versions]
    end

    subgraph Compiled[Compiled plan]
        C1[compiled_plans]
        C2[compiled_plan_nodes]
        C3[compiled_plan_edges]
        C4[compiled_plan_bindings optional]
    end

    subgraph Runtime[Runtime state]
        T1[tasks]
        T2[runs]
        T3[attempts]
        T4[flow_nodes]
        T5[node_checkpoints]
        T6[approvals]
        T7[node_plan_revisions]
    end

    Registry --> Compiled
    Compiled --> Runtime
```

## 4. Plan patch and safe recompile

```mermaid
sequenceDiagram
    participant Child as Main Loop Child
    participant Parent as Parent Supervisor
    participant Controller
    participant Compiler
    participant Runtime

    Child-->>Parent: Checkpoint: repeated failure
    Parent->>Controller: Structured patch proposal
    Controller->>Compiler: Validate + partial recompile
    Compiler-->>Controller: New compiled plan revision
    Controller->>Runtime: Adopt revision at safe boundary
    Runtime->>Parent: Resume parent loop
    Parent->>Child: Dispatch next step under new plan
```

## 5. Operator console hierarchy

```mermaid
flowchart TD
    TASK[Task]
    RUN[Run]
    ATTEMPT[Attempt]
    FLOW[Flow]
    NODE[Node]
    CHECKPOINT[Latest checkpoint]
    APPROVAL[Approval / blocker state]

    TASK --> RUN
    RUN --> ATTEMPT
    ATTEMPT --> FLOW
    FLOW --> NODE
    NODE --> CHECKPOINT
    RUN --> APPROVAL
```

## 6. MVP builder workflow pack

```mermaid
flowchart TD
    ROOT[Root orchestrator]

    ROOT --> DISC[Discovery subtree]
    ROOT --> ARCH[Architecture subtree]
    ROOT --> BUILD[Build subtree]
    ROOT --> VALID[Validation subtree]
    ROOT --> LAUNCH[Launch / report subtree]

    DISC --> DISC1[Product design]
    DISC --> DISC2[Business research]

    ARCH --> ARCH1[PM loop]
    ARCH --> ARCH2[Architecture loop]

    BUILD --> BUILD1[Design main pages]
    BUILD --> BUILD2[Backend design / implementation]
    BUILD --> BUILD3[Design other pages]
    BUILD --> BUILD4[Frontend implementation]

    VALID --> VALID1[User test]
    VALID --> VALID2[Compliance]
    VALID --> VALID3[Security assurance]

    LAUNCH --> LAUNCH1[Marketing plan]
    LAUNCH --> LAUNCH2[Demo / report packaging]
```

## 7. Querying and scheduling split

```mermaid
flowchart LR
    DBQ[Recursive CTE in Postgres]
    SCHED[Python scheduler]
    TREE[Ownership tree queries]
    DAG[Runnable dependency slice]
    LOOP[Iteration records]

    DBQ --> TREE
    SCHED --> DAG
    SCHED --> LOOP
```

## Notes

- Ownership is primarily a **tree**.
- Dependency edges are optional and should stay secondary.
- Loops should be modeled as **iteration state**, not raw cyclic graph edges.
- The default homepage/view should show the **simple truth first**; the full graph is an inspect view.
