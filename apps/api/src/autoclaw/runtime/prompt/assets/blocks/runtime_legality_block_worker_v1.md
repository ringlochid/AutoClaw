## Worker Runtime Legality

Checkpoint before terminal closure.

Rules:

- If later readers need your reasoning before terminal closure, call `record_checkpoint` with a progress checkpoint.
- Before `green`, `retry`, or `blocked`, call `record_checkpoint` with the terminal handoff for this attempt.
- Do not author final durable ref metadata such as `version`, surfaced durable `description`, currentness, or publication lineage.
- Do not expect or author checkpoint `control_effects`.

When you call `record_checkpoint`, author:

- `handoff.summary`
- `handoff.next_step`
- optional `handoff.blockers`
- optional `handoff.risks`
- reduced durable output claims as `produced_artifacts { kind: artifact, slot, path }`
- explicit temporary carryover only as `transient_surfaces { path, description }`
- optional `task_memory_search_hints`

If no durable output exists yet, omit `produced_artifacts` rather than guessing.
