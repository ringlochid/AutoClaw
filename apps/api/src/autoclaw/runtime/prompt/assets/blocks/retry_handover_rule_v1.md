## Retry Handover

Retry is node-self only.

Rules:

- Retry keeps the same assignment.
- Retry creates a new attempt.
- Retry always uses `full_prompt`.
- Do not treat same-session continuation as retry.
- Do not depend on prior live session memory for retry.

Retry durable handover comes from:

- the same assignment
- the prior terminal checkpoint written through `record_checkpoint`
- current surfaced `consumed_durable_refs`
- optional `transient_refs`
- relevant `task_memory_search_hints`
