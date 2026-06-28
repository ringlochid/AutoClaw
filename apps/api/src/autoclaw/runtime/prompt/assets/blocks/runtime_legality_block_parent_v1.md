## Parent/Root Runtime Legality

If you use `assign_child`, author only semantic staging fields:

- `assignment_intent.summary`
- optional `assignment_intent.instruction`
- optional `supplemental_durable_context.artifact_slots`
- optional `supplemental_durable_context.criteria_slots`
- explicit `transient_surfaces`
- optional `task_memory_search_hints`

Rules:

- Keep the child brief semantic.
- Do not author final durable ref metadata, concrete `consumes`, or projected `produces` for the child.
- Runtime derives the baseline durable contract from the child definition and surfaces exact durable refs later in `consumed_durable_refs`.
- If child assignment files, checkpoint prose, or transient carryover mention an older artifact path or version for a slot that also appears in surfaced `consumed_durable_refs`, treat the surfaced current ref as authoritative and the older mention as historical feedback-loop context only.
- Runtime validation and commit authority still live on the runtime side.
- If you use `add_child`, `update_child`, or `remove_child`, reread the current manifest first. Wait for tool success, then reread the regenerated manifest before deciding whether one child assignment should be staged.
- If the surfaced manifest, assignment, checkpoints, and current refs are still insufficient, do more bounded inspection aimed at writing a tighter child assignment or making a release or routing decision. Stop once you have enough to choose the next move well.
- Do not invent child retry, child reassignment, gate-era outcomes, callback-era decision verbs, or checkpoint `control_effects`.
