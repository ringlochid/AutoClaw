## Parent/Root Runtime Opening Example

Current Dispatch:

- current bound turn: current root turn (internal dispatch id hidden)
- node kind: root
- send mode: full_prompt
- closure expectation: use control tools now, call `record_checkpoint` if the reasoning must persist, then later emit `yield` or a terminal boundary
- task_id for node tools: task_2026_0042
- session_key for node tools: sess_root_dispatch_07

Runtime Reminder:

1. Read `C:/tasks/task_2026_0042/_runtime/workflow-manifest.md` first for the whole-workflow picture.
2. Read `C:/tasks/task_2026_0042/_runtime/attempts/attempt.root.07/assignment.md` next for the semantic parent/root handoff.
3. Read surfaced child checkpoints and `consumed_durable_refs` before assigning, restructuring, or releasing.
4. Do bounded research only to prepare a tighter child brief; inspect the minimum additional workspace, context, or source files needed to choose the right refs and scope.
5. Use `assign_child` with semantic `assignment_intent`, `supplemental_durable_context`, and explicit `transient_surfaces` only; do not author final durable ref metadata for the child.
6. If you start solving the child task in place, step back and improve the child brief unless delegation is clearly the wrong tool.
7. After exactly one staged child assignment exists and the dispatch stays non-terminal, emit `yield`.
8. Immediately after a successful `yield`, stop the current outer assistant turn; do not continue with more tool calls or prose.
9. Structural CRUD alone does not justify `yield`.
10. After `release_green` or root `release_blocked`, close with the matching terminal boundary.
11. Immediately after a successful terminal boundary, stop the current outer assistant turn; do not continue with more tool calls or prose.
