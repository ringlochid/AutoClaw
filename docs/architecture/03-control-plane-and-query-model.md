# Control Plane and Query Model

## Storage layers

Keep storage in three layers:

1. **definition registry**
   - role definitions / versions
   - policy definitions / versions
   - workflow definitions / versions
   - skill registry / versions

2. **compiled plan**
   - compiled plans
   - compiled plan nodes
   - compiled plan edges
   - optional compiled bindings table

3. **runtime state**
   - tasks / runs / attempts
   - flow nodes
   - checkpoints
   - approvals
   - plan revisions
   - watchdog / progress signals

## Database truth

Database truth beats transcript truth.
Sessions help continuity, but they must not become the canonical source of workflow state.

## ID stack

Use a small stable hierarchy:

- `task_id` — user/business job
- `run_id` — one top-level execution
- `attempt_id` — one retry/fresh try inside a run
- `flow_id` — one instantiated runtime graph/tree for an attempt
- `lineage_id` — optional grouping across related attempts/branches
- `node_id` — one runtime node

## Ownership tree vs dependency graph

Use two different ideas on purpose:

- **ownership tree** for supervision and UI structure
- **dependency edges** only when tree ownership is not enough to express execution ordering

Avoid making the whole runtime a free-form cyclic graph.

## Loops

Loops should be modeled as iteration state, not as raw graph back-edges.

Good:
- loop node
- iteration counter
- iteration records

Bad:
- giant cyclic graph blob

## Relational first, JSONB second

Store these relationally:
- ownership links
- state / mode
- timestamps
- counters
- pinned version refs

Store these in JSONB only when needed:
- checkpoint payload bodies
- plan patch payloads
- prompt overlay payloads
- flexible rule bodies
- extracted skill manifest metadata

## Query and scheduling split

Use the right tool for each job:

- **Postgres recursive CTE** for ancestry / subtree / dashboard tree queries
- **Python topo sort** for execution planning over the current runnable dependency slice

That keeps the DB good at structure and the runtime good at scheduling.
