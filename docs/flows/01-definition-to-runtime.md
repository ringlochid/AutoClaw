# Flow 01 — Definition to Runtime

## What happens

1. create task definition package
2. publish workflow/policy/role versions
3. compile to immutable plan
4. instantiate `flow` and initial `flow_revision`
5. materialize `flow_nodes` / `flow_edges`
6. runtime controller schedules runnable nodes and creates `node_attempts`

## Why this matters

Runtime should never execute arbitrary raw definition.
It should execute compiled plan structure and state only.
