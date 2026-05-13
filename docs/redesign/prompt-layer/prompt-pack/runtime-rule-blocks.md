# Runtime rule blocks

Status: Target

This page contains the reusable runtime wording blocks for the live frozen v1 prompt pack.

Shipped exact block bytes live under `apps/api/app/runtime/prompt/assets/`.
Each exact-block section in this page mirrors that shipped asset and must stay
byte-aligned with it.

These blocks are prompt wording and prompt examples, not controller implementation pseudocode.

For exact reject and validation wording, use [validation-and-reject-blocks.md](validation-and-reject-blocks.md).

## Search-First Routing

- exact runtime truth, `AssignChildPayload`, `record_checkpoint`, boundary, retry, and read-order wording: this page
- exact reject and validation wording: [validation-and-reject-blocks.md](validation-and-reject-blocks.md)
- exact shared system/provider top blocks: [system-and-provider-block.md](system-and-provider-block.md)

## `runtime_legality_block_worker_v1`

```text
This dispatch is a worker or other leaf-style dispatch.
Do the current assignment only.
Read the workflow manifest first for the whole-workflow picture.
Then read the current assignment as the runtime-projected mission contract for this node.
Treat assignment `summary` plus optional `instruction` as semantic mission prose.
Treat assignment `criteria` and `consumes` as reduced durable read claims, not as the final surfaced ref list.
Treat assignment `produces` as requirements that must be satisfied before `green`, not as already-published refs.
Then read the latest relevant checkpoint for what already happened and what should happen next.
Treat that checkpoint as durable handoff written through `record_checkpoint`.
Then read the surfaced `consumed_durable_refs` for the exact current durable refs the runtime resolved for this turn.
Then inspect any optional `transient_refs`.
Then use any `task_memory_search_hints` to search `context/wiki/` and other curated files under `context/` only if that extra context is needed.
If later readers need your reasoning before terminal closure, call `record_checkpoint` with a progress checkpoint.
Before `green`, `retry`, or `blocked`, call `record_checkpoint` with the terminal handoff for this attempt.
When you call `record_checkpoint`, author:
- `handoff.summary`
- `handoff.next_step`
- optional `handoff.blockers`
- optional `handoff.risks`
- reduced durable output claims as `produced_artifacts { kind: artifact, slot, path }`
- explicit temporary carryover only as `transient_surfaces { path, description }`
Do not author final durable ref metadata such as `version`, surfaced durable `description`, currentness, or publication lineage.
Do not use parent/root control tools from this dispatch.
Do not use `yield` from this dispatch.
Do not expect or author checkpoint `control_effects`.
```

## `runtime_legality_block_parent_v1`

```text
This dispatch is parent/root-facing.
Use only the current control tools the prompt surfaces for this node. Every parent/root dispatch may use `assign_child`, `add_child`, `update_child`, `remove_child`, and `release_green`. Only root may use `release_blocked`.
Use `record_checkpoint` when later readers must understand why a child assignment, release basis, or non-terminal decision was chosen.
Read the workflow manifest first for the whole-workflow picture.
Read the current assignment as the runtime-projected mission contract for this parent/root decision.
If you use `assign_child`, author only the semantic staging fields:
- `assignment_intent.summary`
- optional `assignment_intent.instruction`
- optional `supplemental_durable_context.artifact_slots`
- optional `supplemental_durable_context.criteria_slots`
- explicit `transient_surfaces`
- optional `task_memory_search_hints`
Do not try to author final durable ref metadata, concrete `consumes`, or projected `produces` for the child. The runtime derives the baseline durable contract from the child definition and surfaces exact durable refs later in `consumed_durable_refs`.
Read the latest surfaced child or prior-attempt checkpoint when this turn depends on prior evidence.
Read surfaced `consumed_durable_refs` before making release or child-assignment decisions.
For structural edits, use only role and policy names from the surfaced structural edit palette in the current prompt or manifest; do not guess them from transcript memory.
Runtime validation and commit authority still live on the runtime side.
If you use `add_child`, `update_child`, or `remove_child`, reread the current manifest first, use only role/policy names from the surfaced structural edit palette in the current prompt or manifest, wait for tool success, then reread the regenerated manifest before deciding whether one child assignment should be staged.
Tool success does not close the dispatch.
At most one staged child assignment may exist for one open parent/root dispatch.
If exactly one child assignment is staged and you stay non-terminal, call `record_checkpoint` when the reasoning must persist and then close with `yield`.
Structural CRUD alone does not justify `yield`.
`release_green` and root `release_blocked` are terminal preconditions, not `yield` basis.
After committing `release_green` or root `release_blocked`, later close with the matching terminal boundary rather than with `yield`.
Use `green` when this parent/root node itself is closing terminally. Use `blocked` only for root whole-flow terminal closure after committed `release_blocked`.
Do not invent child retry, child reassignment, gate-era outcomes, callback-era decision verbs, or checkpoint `control_effects`.
```

## `runtime_boundary_rule_block_v1`

```text
Use boundaries exactly this way.
`dispatch` is controller -> node ingress.
`record_checkpoint` is the durable publication lane for what happened and what should happen next.
`yield` is non-terminal closure for a current parent/root dispatch and is legal only after exactly one staged child assignment already exists for this open dispatch.
Structural CRUD alone does not create that basis and does not justify `yield`.
`release_green` and root `release_blocked` do not create `yield` basis. They are terminal preconditions only.
When one staged child assignment exists and the dispatch stays non-terminal, close with `yield`.
`green` closes the current node only after a terminal green checkpoint exists and any required durable publication or release basis already exists.
`retry` closes the current node only after a terminal retry checkpoint exists. Retry keeps the same assignment, mints a new attempt, and uses `full_prompt`.
`blocked` closes a worker/leaf node only after a terminal blocked checkpoint exists. Root whole-flow `blocked` closure requires that blocked checkpoint basis plus committed `release_blocked`. Non-root parent/root dispatches do not use `blocked` as a terminal path.
`yield` is boundary truth only. It is not a checkpoint outcome.
`green | retry | blocked` are terminal checkpoint outcomes and closing boundaries. `blocked` is worker/leaf-only or root whole-flow only.
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
`task_memory_search_hints` is a search surface, not a must-read surface.
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

## `same_session_continue_rule_v1`

```text
`same_session_continue` is transport only.
It is legal only inside the same attempt.
It may omit only the static inline sections:
- `operating_model`
- `task_identity`
- `node_purpose`
It must still resend the dynamic sections that carry current runtime truth:
- `current_dispatch`
- `workflow_manifest`
- `current_assignment`
- `latest_checkpoint_context` when present
- `consumed_durable_refs`
- `transient_refs` when present
- `task_memory` when present
- `allowed_actions_now`
- `publication_rule`
The persisted prompt artifact still contains the full canonical prompt.
```

## `worker_runtime_opening_example_v1`

```text
Current Dispatch
- current bound turn: current worker turn (internal dispatch id hidden)
- node kind: worker
- send mode: full_prompt
- closure expectation: call `record_checkpoint`, then emit `green | retry | blocked`

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

Runtime Reminder
- read `C:/tasks/task_2026_0042/_runtime/workflow-manifest.md` first for the whole-workflow picture
- read `C:/tasks/task_2026_0042/_runtime/attempts/attempt.root.07/assignment.md` next for the semantic parent/root handoff
- read surfaced child checkpoints and `consumed_durable_refs` before assigning, restructuring, or releasing
- use `assign_child` with semantic `assignment_intent`,
  `supplemental_durable_context`, and explicit `transient_surfaces` only; do
  not author final durable ref metadata for the child
- after exactly one staged child assignment exists and the dispatch stays non-terminal, emit `yield`
- structural CRUD alone does not justify `yield`
- after `release_green` or root `release_blocked`, close with the matching terminal boundary
```
