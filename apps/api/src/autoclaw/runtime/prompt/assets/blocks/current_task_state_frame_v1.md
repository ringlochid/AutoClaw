## Current Task State Frame

Current Task State must expose:

- the current `dispatch` boundary and current node identity
- the current workflow manifest path as the visible workflow contract
- the current assignment path as the semantic handoff for this node
- the latest relevant checkpoint path as the durable handoff surface from `record_checkpoint`
- the current assignment `summary` plus optional `instruction`
- reduced `criteria`, reduced `consumes`, and `produces` requirements from the semantic assignment
- exact surfaced `consumed_durable_refs` rendered separately from the semantic assignment
- optional `transient_refs`
- `task_memory_search_hints`, with the rule that they point first to `context/wiki/` and then to other curated files under `context/`
- a note that `_runtime/dispatch/...` monitoring files are observability only, not normal assignment truth
