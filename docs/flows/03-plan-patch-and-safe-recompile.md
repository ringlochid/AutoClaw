# Flow 03 — Plan Patch and Safe Recompile

## Replan principle

- repeated failure does not mutate graph in place
- patch is proposed with target insertion/removal
- compile validates the patch
- adopt replaces active revision only

## Data trail

- write `node_plan_revisions`
- set `adopted` only after compile validation
- update `flow_nodes` and `flow_edges` via insert/retire
- keep old rows for traceability
