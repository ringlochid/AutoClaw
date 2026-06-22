# Runtime rule blocks

Status: Target

This page contains the reusable runtime wording blocks for the live frozen v1 prompt pack.

Shipped exact block bytes live under `apps/api/src/autoclaw/runtime/prompt/assets/`. Each exact-block section in this page mirrors that shipped asset and must stay byte-aligned with it.

These blocks are prompt wording and prompt examples, not controller implementation pseudocode.

For exact reject and validation wording, use [Validation And Reject Blocks](validation-and-reject-blocks.md).

## Search-First Routing

- exact runtime truth, `AssignChildPayload`, `record_checkpoint`, boundary, retry, and read-order wording: this page
- exact parent/root assignment packaging guidance and checkpoint-authoring guidance: this page
- exact reject and validation wording: [Validation And Reject Blocks](validation-and-reject-blocks.md)
- exact shared system/provider top blocks: [System And Provider Block](system-and-provider-block.md)

## `checkpoint_authoring_guide_v1`

```text
Treat every checkpoint as a durable handoff, not a diary entry or polished status report.
Write only the decision-relevant delta that the next reader should not have to rediscover.
Use `handoff.summary` for what changed, what was learned, or what failed in a way that materially affects the next move.
Use `handoff.next_step` for one concrete next action, not a vague continuation note.
Use `handoff.blockers` or `handoff.risks` only when they actually change execution.
Use `produced_artifacts` only for exact durable claims you are making now: one `artifact` claim per produced slot plus the produced file path.
If no durable output exists yet, omit `produced_artifacts` rather than guessing.
Use `transient_surfaces` only for temporary carryover that genuinely helps the next turn start faster.
Use `task_memory_search_hints` as semantic retrieval prompts for this exact defect, rejection, root cause, or artifact thread. Do not use generic hints like `retry`, `fix`, or `bug`.
If prose mentions an older artifact path or prior version for a slot that also appears in surfaced current refs later, that older mention is history only, not current truth.
Bad checkpoint example:
- `handoff.summary`: Made progress, still checking.
- `handoff.next_step`: Continue.
- `task_memory_search_hints`: `fix`, `retry`
Better checkpoint example:
- `handoff.summary`: Reproduced Task Start header overflow at `390px`. No source patch yet. The failure comes from CTA min-width plus nav wrap.
- `handoff.next_step`: Reduce the CTA min-width in Task Start only, rerender desktop and mobile, then checkpoint with the new artifact paths.
- `task_memory_search_hints`: `task start header overflow 390px cta min-width`, `task start nav wrap rejection`
```

## `runtime_legality_block_worker_v1`

```text
If later readers need your reasoning before terminal closure, call `record_checkpoint` with a progress checkpoint.
Before `green`, `retry`, or `blocked`, call `record_checkpoint` with the terminal handoff for this attempt.
When you call `record_checkpoint`, author:
- `handoff.summary`
- `handoff.next_step`
- optional `handoff.blockers`
- optional `handoff.risks`
- reduced durable output claims as `produced_artifacts { kind: artifact, slot, path }`
- explicit temporary carryover only as `transient_surfaces { path, description }`
- optional `task_memory_search_hints`
If no durable output exists yet, omit `produced_artifacts` rather than guessing.
Do not author final durable ref metadata such as `version`, surfaced durable `description`, currentness, or publication lineage.
Do not expect or author checkpoint `control_effects`.
```

## `parent_root_assignment_guide_v1`

```text
When you prepare a child assignment, do bounded research first.
Start from the current workflow manifest, current assignment, latest relevant checkpoint, and surfaced `consumed_durable_refs`.
Inspect additional workspace, context, or source files only until you can answer:
- what exact problem or question the child owns
- which surfaced durable refs and constraints the child should trust first
- what evidence or outputs the child must return
- what scope boundaries or untouched areas protect the rest of the task
Use `assignment_intent.summary` for one crisp owned objective or question.
Use `assignment_intent.instruction` to tell the child how to acquire truth before acting: what to read first, what to compare, what evidence to return, and any required sequencing or acceptance nuance.
Use `supplemental_durable_context.artifact_slots` for durable artifact slots the child should trust or compare against.
Use `supplemental_durable_context.criteria_slots` for the acceptance or guardrail criteria that must govern the child's decisions.
Use `transient_surfaces` only for short-lived carryover that will help now and would be noisy as durable context.
Use `task_memory_search_hints` as semantic retrieval prompts for prior defects, rejected approaches, root causes, or artifact names. Do not use generic hints like `ui`, `bug`, or `page`.
Write the child brief as an acquisition plan, not just a work order.
Bad child brief example:
- `summary`: Check the page and fix issues.
- `instruction`: null
- `task_memory_search_hints`: `task start`, `bug`
Better child brief example:
- `summary`: Verify Task Start CTA state and nav behavior on the current page.
- `instruction`: Read the latest review checkpoint and surfaced page artifacts first. Compare desktop and mobile output before changing source. If you patch, keep the change scoped to Task Start only and return exact artifact paths plus the next blocker if the page still fails.
- `artifact_slots`: `page_html`, `page_review_report`
- `criteria_slots`: `page_review_acceptance`
- `task_memory_search_hints`: `task start prior CTA rejection state`, `task start nav artifact leak guardrail`
```

## `runtime_legality_block_parent_v1`

```text
If you use `assign_child`, author only the semantic staging fields:
- `assignment_intent.summary`
- optional `assignment_intent.instruction`
- optional `supplemental_durable_context.artifact_slots`
- optional `supplemental_durable_context.criteria_slots`
- explicit `transient_surfaces`
- optional `task_memory_search_hints`
Keep the child brief semantic. Do not try to author final durable ref metadata, concrete `consumes`, or projected `produces` for the child. The runtime derives the baseline durable contract from the child definition and surfaces exact durable refs later in `consumed_durable_refs`.
If child assignment files, checkpoint prose, or transient carryover mention an older artifact path or version for a slot that also appears in surfaced `consumed_durable_refs`, treat the surfaced current ref as authoritative and the older mention as historical feedback-loop context only.
Runtime validation and commit authority still live on the runtime side.
If you use `add_child`, `update_child`, or `remove_child`, reread the current manifest first. Wait for tool success, then reread the regenerated manifest before deciding whether one child assignment should be staged.
If the surfaced manifest, assignment, checkpoints, and current refs are still insufficient, do more bounded inspection aimed at writing a tighter child assignment or making a release or routing decision. Stop once you have enough to choose the next move well.
Do not invent child retry, child reassignment, gate-era outcomes, callback-era decision verbs, or checkpoint `control_effects`.
```

Interpretation note for parent/root structural edits:

- the compact structural edit palette in the prompt or manifest remains the default surfaced discovery lane
- current-only `search_definitions` / `get_definition` reads are the legal read-only escalation path after palette reread and before guessing
- definition revision history remains operator/audit-only rather than normal dispatched planning input
- parent/root should use that escalation path when repeated loops or review findings imply the current role/policy shape is weak

## `runtime_boundary_rule_block_v1`

```text
Use boundaries exactly this way.
`dispatch` is controller -> node ingress.
`record_checkpoint` is the durable publication lane for what happened and what should happen next.
`yield` is non-terminal closure for a current parent/root dispatch and is legal only after exactly one staged child assignment already exists for this open dispatch.
Structural CRUD alone does not create that basis and does not justify `yield`.
`release_green` and root `release_blocked` do not create `yield` basis. They are terminal preconditions only.
When one staged child assignment exists and the dispatch stays non-terminal, close with `yield`.
After a successful `yield`, stop the current outer assistant turn immediately. Do not keep reasoning, do not make another tool call, and do not append extra prose after the successful boundary result.
`green` closes the current node only after a terminal green checkpoint exists and any required durable publication or release basis already exists.
`retry` closes the current node only after a terminal retry checkpoint exists. Retry keeps the same assignment, mints a new attempt, and uses `full_prompt`.
`blocked` closes a worker/leaf node only after a terminal blocked checkpoint exists. Root whole-flow `blocked` closure requires that blocked checkpoint basis plus committed `release_blocked`. Non-root parent/root dispatches do not use `blocked` as a terminal path.
`yield` is boundary truth only. It is not a checkpoint outcome.
`green | retry | blocked` are terminal checkpoint outcomes and closing boundaries. `blocked` is worker/leaf-only or root whole-flow only.
After a successful `green`, `retry`, or `blocked`, stop the current outer assistant turn immediately. Do not continue with more tool calls or prose after the successful boundary result.
```

## `retry_handover_rule_v1`

```text
Retry is node-self only.
Retry keeps the same assignment.
Retry creates a new attempt.
Retry always uses `full_prompt`.
Retry durable handover comes from:
- the same assignment
- the prior terminal checkpoint written through `record_checkpoint`
- current surfaced `consumed_durable_refs`
- any optional `transient_refs`
- any relevant `task_memory_search_hints`
Do not treat same-session continuation as retry.
Do not depend on prior live session memory for retry.
```

## `runtime_read_order_rule_v1`

```text
Read runtime surfaces in this order unless the current prompt says otherwise:
1. `_runtime/workflow-manifest.*`
2. current `_runtime/attempts/<attempt_id>/assignment.*`
3. current relevant `_runtime/attempts/<attempt_id>/latest-checkpoint.*`
4. surfaced `consumed_durable_refs`
5. optional `transient_refs`
6. `task_memory_search_hints`, then search `context/wiki/` and other curated docs under `context/` if needed
Do not recover current truth from transcript memory, folder scans, or raw provider transport state.
```

## `current_task_state_frame_v1`

```text
Current Task State must expose:

- the current `dispatch` boundary and current node identity
- the current workflow manifest path as the visible workflow contract
- the current assignment path as the semantic handoff for this node
- the latest relevant checkpoint path as the durable handoff surface from `record_checkpoint`
- the current assignment `summary` plus optional `instruction`
- reduced `criteria`, reduced `consumes`, and `produces` requirements from the semantic assignment
- exact surfaced `consumed_durable_refs` rendered separately from the semantic assignment
- any optional `transient_refs`
- any `task_memory_search_hints`, with the rule that they point first to `context/wiki/` and then to other curated files under `context/`
- a note that `_runtime/dispatch/...` monitoring files are observability only, not normal assignment truth
```

## `artifact_render_rule_v1`

```text
When you cite a durable artifact ref in the prompt, render it compactly:

- `slot`
- `version`
- `path`
- `description`

Use this exact shape only for runtime-resolved durable refs such as `consumed_durable_refs` and checkpoint artifact lists.
Do not inline controller-only pointer fields such as currentness history, assignment lineage, or attempt lineage.
Do not ask the node to infer meaning from filenames like `latest.md` or from directory scans.
Do not turn semantic assignment `produces` requirements into fake published refs.
```

## `task_memory_rule_v1`

```text
`task_memory_search_hints` is a retrieval surface, not a must-read surface.
Write hints as semantic search prompts for prior defects, rejected approaches, root causes, or artifact names.
Prefer phrases that can recover the right prior context later, not generic labels or tags.
Use the hints to search `context/wiki/` first and then other curated files under `context/` when the current assignment needs that extra context.
Do not silently promote all task-memory files into current `consumes`.
```

## `monitoring_not_task_truth_v1`

```text
Files under `_runtime/dispatch/<dispatch_id>/` are monitoring and incident-debug projections only.
They are not ordinary assignment truth.
Read them only when the current failure, surfaced ref, or incident flow explicitly sends you there.
If a monitoring projection disagrees with current manifest, assignment, or checkpoint context, controller/DB truth wins.
```

## `worker_runtime_opening_example_v1`

```text
Current Dispatch
- current bound turn: current worker turn (internal dispatch id hidden)
- node kind: worker
- send mode: full_prompt
- closure expectation: call `record_checkpoint`, then emit `green | retry | blocked`
- task_id for node tools: task_2026_0042
- session_key for node tools: sess_worker_dispatch_01

Runtime Reminder
- read `C:/tasks/task_2026_0042/_runtime/workflow-manifest.md` first for the whole-workflow picture
- read `C:/tasks/task_2026_0042/_runtime/attempts/attempt.implement_fix.11/assignment.md` next for the semantic handoff you own now
- reread `C:/tasks/task_2026_0042/_runtime/attempts/attempt.implement_fix.10/latest-checkpoint.md` because this retry handoff explains what failed and what must change
- read `consumed_durable_refs` for the exact current durable refs the runtime resolved for this attempt
- satisfy every `produces` requirement before `green`
```

## `parent_root_runtime_opening_example_v1`

```text
Current Dispatch
- current bound turn: current root turn (internal dispatch id hidden)
- node kind: root
- send mode: full_prompt
- closure expectation: use control tools now, call `record_checkpoint` if the reasoning must persist, then later emit `yield` or a terminal boundary
- task_id for node tools: task_2026_0042
- session_key for node tools: sess_root_dispatch_07

Runtime Reminder
- read `C:/tasks/task_2026_0042/_runtime/workflow-manifest.md` first for the whole-workflow picture
- read `C:/tasks/task_2026_0042/_runtime/attempts/attempt.root.07/assignment.md` next for the semantic parent/root handoff
- read surfaced child checkpoints and `consumed_durable_refs` before assigning, restructuring, or releasing
- do bounded research only to prepare a tighter child brief; inspect the minimum additional workspace, context, or source files needed to choose the right refs and scope
- use `assign_child` with semantic `assignment_intent`,
  `supplemental_durable_context`, and explicit `transient_surfaces` only; do
  not author final durable ref metadata for the child
- if you start solving the child task in place, step back and improve the child brief unless delegation is clearly the wrong tool
- after exactly one staged child assignment exists and the dispatch stays non-terminal, emit `yield`
- immediately after a successful `yield`, stop the current outer assistant turn; do not continue with more tool calls or prose
- structural CRUD alone does not justify `yield`
- after `release_green` or root `release_blocked`, close with the matching terminal boundary
- immediately after a successful terminal boundary, stop the current outer assistant turn; do not continue with more tool calls or prose
```
