# Flow 01 — Definition to Runtime

## What happens

1. publish workflow/policy/role versions
2. compile reusable definitions to an immutable plan
3. accept a task-compose-first start request
4. materialize internal `task` from task compose
5. persist `task_compose` as the launch-binding record
6. instantiate `flow` and initial `flow_revision`
7. materialize `flow_nodes` / `flow_edges`
8. runtime controller schedules runnable nodes and creates `node_attempts`

## Why this matters

Runtime should never execute arbitrary raw definition.
It should execute compiled plan structure and state only.
