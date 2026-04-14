# Flow 01 — Definition to Runtime

## What happens

1. create task definition package
2. publish workflow/policy/role versions
3. compile to immutable plan
4. instantiate `flow` and initial `flow_nodes`
5. runtime controller schedules runnable leaf nodes

## Why this matters

Runtime should never execute arbitrary raw definition.
It should execute compiled plan structure and state only.
