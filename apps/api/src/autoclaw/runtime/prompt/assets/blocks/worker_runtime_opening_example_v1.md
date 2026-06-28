## Worker Runtime Opening Example

Current Dispatch:

- current bound turn: current worker turn (internal dispatch id hidden)
- node kind: worker
- send mode: full_prompt
- closure expectation: call `record_checkpoint`, then emit `green | retry | blocked`
- task_id for node tools: task_2026_0042
- session_key for node tools: sess_worker_dispatch_01

Runtime Reminder:

1. Read `C:/tasks/task_2026_0042/_runtime/workflow-manifest.md` first for the whole-workflow picture.
2. Read `C:/tasks/task_2026_0042/_runtime/attempts/attempt.implement_fix.11/assignment.md` next for the semantic handoff you own now.
3. Reread `C:/tasks/task_2026_0042/_runtime/attempts/attempt.implement_fix.10/latest-checkpoint.md` because this retry handoff explains what failed and what must change.
4. Read `consumed_durable_refs` for the exact current durable refs the runtime resolved for this attempt.
5. Satisfy every `produces` requirement before `green`.
