### Runtime Read Order

Read runtime surfaces in this order unless the current prompt explicitly narrows it:

1. `_runtime/workflow-manifest.md` or `_runtime/workflow-manifest.json` for the whole-workflow picture.
2. The current `_runtime/attempts/<attempt_id>/assignment.*` for what to do now.
3. The current relevant `_runtime/attempts/<attempt_id>/latest-checkpoint.*` when one is surfaced or when this turn depends on prior checkpoint evidence.
4. Surfaced `consumed_durable_refs` for exact current durable refs, including criteria, artifacts, checkpoints, and explicit doc/wiki refs.
5. Optional `transient_refs`.
6. `task_memory_search_hints`, then direct search in `context/wiki/` and other curated docs under `context/` if needed.

Do not recover current truth from transcript memory, folder scans, raw provider transport state, or unstated assumptions.
