# Generated Rendered Prompt Examples

Status: Generated reference

This page shows concrete rendered prompt body examples for the live v1 prompt model.

Use this page when you need search-friendly examples of:

- semantic `assignment_intent` staging plus runtime-resolved durable refs
- runtime-resolved `consumed_durable_refs`
- `record_checkpoint` as durable handoff
- `full_prompt`
- `same_session_continue`

If these examples drift from the live owner docs in this folder, the owner docs win and these examples must be regenerated.

## `parent_root_dispatch_prompt`

Scenario:

- current node: `root`
- send mode: `full_prompt`
- likely next action: `assign_child`
- durable reminder: if the staged-child reasoning must survive redispatch, call `record_checkpoint` before `yield`

```text
Operating Model
- controller/DB state owns runtime truth
- generated files are shared projections derived from that truth
- `dispatch` is ingress, `record_checkpoint` is durable publication, and `yield | green | retry | blocked` are egress
- `assign_child` authors semantic handoff only; runtime resolves exact durable refs separately
- monitoring files under `_runtime/dispatch/` are observability only

Task Identity
- task key: auth-refresh-hardening
- title: Harden auth refresh flow
- summary: investigate, fix, verify, and release the bounded auth-refresh regression

Node Purpose
- node key: root
- node kind: root
- role: planning_lead
- description: coordinate the whole flow, choose the next bounded child step, and decide upward release

Current Dispatch
- current bound turn: current root turn (internal dispatch id hidden)
- send mode: full_prompt
- closure expectation: use control tools now, call `record_checkpoint` if the decision reasoning must persist, then later emit `yield` or a terminal boundary

Workflow Manifest
- path: C:/tasks/task_2026_0042/_runtime/workflow-manifest.md
- description: whole-workflow visible contract for the current task

Current Assignment
- summary: decide the next bounded child step after the current investigation result
- instruction: stay inside the current direct-child set, reread the surfaced investigation evidence, and preserve durable reasoning through checkpoint handoff when needed
- criteria:
  - slot: root_release_rule
    description: root completion and release criteria
  - slot: implementation_entry_rule
    description: rule for when the implementation child may be assigned
- consumes:
  - kind: checkpoint
    slot: investigate_issue_summary
    description: latest investigation handoff for this root decision
  - kind: artifact
    slot: findings_report
    description: current investigation findings for the auth-refresh regression
  - kind: artifact
    slot: reproduction_log
    description: current reproduction evidence for the failing refresh path
  - kind: wiki
    slot: auth_refresh_notes
    description: curated task-memory notes for auth-refresh behavior and prior fixes
- produces:
  - slot: root_decision_note
    description: durable decision note required when root reasoning must survive redispatch
- transient_refs:
  - path: C:/tasks/task_2026_0042/tmp/transfers/root/investigation-compare-grid.md
    description: optional transient comparison grid between the old failure and the current repro output
- task_memory_search_hints:
  - refresh token expiry branch
  - cookie rotation note

Latest Checkpoint Context
- checkpoint_kind: terminal
- outcome: green
- summary: the investigation child isolated the failing refresh-token expiry path and republished durable findings plus reproduction evidence
- next_step: decide whether to assign the implementation child now or add one more bounded review child
- risks:
  - browser-only cookie timing may still need explicit verification after the fix

Consumed Durable Refs
- kind: checkpoint
  slot: investigate_issue_summary
  path: C:/tasks/task_2026_0042/_runtime/attempts/attempt.investigate_issue.02/latest-checkpoint.md
  description: latest investigation checkpoint handoff for the current root decision
- kind: criteria
  slot: root_release_rule
  path: C:/tasks/task_2026_0042/context/criteria/root_release_rule.md
  description: root completion and release criteria
- kind: criteria
  slot: implementation_entry_rule
  path: C:/tasks/task_2026_0042/context/criteria/implementation_entry_rule.md
  description: implementation-entry rule for this decision
- kind: artifact
  slot: findings_report
  version: 2
  path: C:/tasks/task_2026_0042/outputs/artifacts/investigate_issue/findings_report/findings_report.v02.md
  description: current investigation findings for the auth-refresh regression
- kind: artifact
  slot: reproduction_log
  version: 2
  path: C:/tasks/task_2026_0042/outputs/artifacts/investigate_issue/reproduction_log/reproduction_log.v02.txt
  description: current reproduction evidence for the failing refresh path
- kind: wiki
  slot: auth_refresh_notes
  path: C:/tasks/task_2026_0042/context/wiki/auth-refresh-notes.md
  description: curated task-memory notes for auth-refresh behavior and prior fixes

Transient Refs
- transient refs are optional carryover only; they are not durable truth
- path: C:/tasks/task_2026_0042/tmp/transfers/root/investigation-compare-grid.md
- description: optional transient comparison grid between the old failure and the current repro output

Task Memory
- search hints:
  - refresh token expiry branch
  - cookie rotation note
- `context/wiki/` = curated task-memory pages
- other curated docs under `context/` = source/reference material

Allowed Actions Now
- tools:
  - assign_child
  - add_child
  - update_child
  - remove_child
  - release_green
  - release_blocked
  - record_checkpoint
- use `assign_child` with semantic `assignment_intent`,
  `supplemental_durable_context`, and explicit `transient_surfaces` only; do
  not author final durable ref metadata for the child
- for structural edits, reread the current manifest first, discover valid role/policy ids through the registry read lane, and reread the regenerated manifest after the edit before deciding whether one child assignment should be staged
- if exactly one child assignment is staged and the dispatch stays non-terminal, emit `yield`
- if later readers must understand why that child was staged, call `record_checkpoint` before `yield`
- `release_green` and root `release_blocked` are terminal preconditions, not `yield` basis

Publication Rule
- current assignment `produces` are requirements, not final published refs
- if a durable decision note is required, publish it before terminal closure
- later agents reread checkpoint handoff plus surfaced durable refs rather than transcript memory
```

## `worker_dispatch_prompt`

Scenario:

- current node: `implement_fix`
- send mode: `full_prompt`
- current lineage: retry created a new attempt on the same assignment
- durable reminder: read the prior terminal checkpoint as retry handoff

```text
Operating Model
- controller/DB state owns runtime truth
- generated files are shared projections derived from that truth
- `dispatch` is ingress, `record_checkpoint` is durable publication, and `yield | green | retry | blocked` are egress
- this node should execute only the current assignment
- retry is node-self only: same assignment, new attempt, full_prompt, prior terminal checkpoint as durable handoff

Task Identity
- task key: auth-refresh-hardening
- title: Harden auth refresh flow
- summary: investigate, fix, verify, and release the bounded auth-refresh regression

Node Purpose
- node key: implement_fix
- node kind: worker
- role: implementation_worker
- description: repair the bounded auth-refresh defect and republish fix plus verification evidence for the same assignment

Current Dispatch
- current bound turn: current worker turn (internal dispatch id hidden)
- send mode: full_prompt
- closure expectation: reread the same assignment plus prior checkpoint handoff, then call `record_checkpoint` and close with `green`, `retry`, or `blocked`

Workflow Manifest
- path: C:/tasks/task_2026_0042/_runtime/workflow-manifest.md
- description: whole-workflow visible contract for the current task

Current Assignment
- summary: repair the auth-refresh expiry-path defect and publish the required evidence
- instruction: keep the same bounded assignment, fix the missed branch from the retry handoff, and republish every required output before green
- criteria:
  - slot: fix_acceptance
    description: bounded implementation acceptance criteria
  - slot: verification_acceptance
    description: verification evidence criteria for the post-fix rerun
- consumes:
  - kind: checkpoint
    slot: prior_retry_handoff
    description: prior terminal retry checkpoint for this same assignment
  - kind: artifact
    slot: findings_report
    description: current investigation findings for the auth-refresh regression
  - kind: artifact
    slot: reproduction_log
    description: current reproduction evidence for the failing refresh path
  - kind: wiki
    slot: auth_refresh_notes
    description: curated task-memory notes for auth-refresh behavior and prior fixes
- produces:
  - slot: patch
    description: bounded code change artifact required before green
  - slot: verification_report
    description: scoped verification evidence required before green
- transient_refs:
  - path: C:/tasks/task_2026_0042/tmp/transfers/implement_fix/retry-plan.md
    description: optional transient retry plan that isolates the missed forced-refresh branch
- task_memory_search_hints:
  - forced refresh branch
  - token expiry rollback fixture

Latest Checkpoint Context
- checkpoint_kind: terminal
- outcome: retry
- summary: the prior implementation attempt fixed the primary expiry path but missed the forced-refresh branch used by one browser-family regression test
- next_step: keep the same assignment, repair the missed branch, rerun bounded verification, and republish patch plus verification evidence
- blockers:
  - the forced-refresh fixture still needs a deterministic browser rerun
- risks:
  - patching the wrong cookie invalidation path could regress the already-fixed branch

Consumed Durable Refs
- kind: checkpoint
  slot: prior_retry_handoff
  path: C:/tasks/task_2026_0042/_runtime/attempts/attempt.implement_fix.11/latest-checkpoint.md
  description: prior terminal retry checkpoint for this same assignment
- kind: criteria
  slot: fix_acceptance
  path: C:/tasks/task_2026_0042/context/criteria/fix_acceptance.md
  description: bounded implementation acceptance criteria
- kind: criteria
  slot: verification_acceptance
  path: C:/tasks/task_2026_0042/context/criteria/verification_acceptance.md
  description: verification evidence criteria for the post-fix rerun
- kind: artifact
  slot: findings_report
  version: 2
  path: C:/tasks/task_2026_0042/outputs/artifacts/investigate_issue/findings_report/findings_report.v02.md
  description: current investigation findings for the auth-refresh regression
- kind: artifact
  slot: reproduction_log
  version: 2
  path: C:/tasks/task_2026_0042/outputs/artifacts/investigate_issue/reproduction_log/reproduction_log.v02.txt
  description: current reproduction evidence for the failing refresh path
- kind: wiki
  slot: auth_refresh_notes
  path: C:/tasks/task_2026_0042/context/wiki/auth-refresh-notes.md
  description: curated task-memory notes for auth-refresh behavior and prior fixes

Transient Refs
- transient refs are optional carryover only; they are not durable truth
- path: C:/tasks/task_2026_0042/tmp/transfers/implement_fix/retry-plan.md
- description: optional transient retry plan that isolates the missed forced-refresh branch

Task Memory
- search hints:
  - forced refresh branch
  - token expiry rollback fixture
- `context/wiki/` = curated task-memory pages
- other curated docs under `context/` = source/reference material

Allowed Actions Now
- continue the same assignment only
- if later readers need intermediate reasoning, call `record_checkpoint` with a progress checkpoint
- before `green`, `retry`, or `blocked`, call `record_checkpoint` with the terminal handoff for this attempt
- do not use parent/root control tools from this dispatch

Publication Rule
- satisfy every `produces` requirement before `green`
- runtime authors the final published artifact refs after publication exists
- later agents reread checkpoint handoff plus surfaced durable refs rather than transcript memory
```

## `worker_dispatch_prompt same_session_continue`

Scenario:

- current node: `implement_fix`
- send mode: `same_session_continue`
- continuity state: same attempt, same assignment
- current checkpoint basis: progress checkpoint already recorded inside the same attempt

```text
Current Dispatch
- current bound turn: same-attempt worker continuation (internal dispatch id hidden)
- send mode: same_session_continue
- closure expectation: stay inside the same attempt, use the same assignment handoff and surfaced refs, then call `record_checkpoint` before terminal closure

Workflow Manifest
- path: C:/tasks/task_2026_0042/_runtime/workflow-manifest.md
- description: whole-workflow visible contract for the current task

Current Assignment
- summary: repair the auth-refresh expiry-path defect and publish the required evidence
- instruction: keep the same bounded assignment, finish the remaining verification, and close only after the required outputs exist
- criteria:
  - slot: fix_acceptance
    description: bounded implementation acceptance criteria
  - slot: verification_acceptance
    description: verification evidence criteria for the post-fix rerun
- consumes:
  - kind: checkpoint
    slot: prior_retry_handoff
    description: prior terminal retry checkpoint for this same assignment
  - kind: artifact
    slot: findings_report
    description: current investigation findings for the auth-refresh regression
- produces:
  - slot: patch
    description: bounded code change artifact required before green
  - slot: verification_report
    description: scoped verification evidence required before green
- transient_refs:
  - path: C:/tasks/task_2026_0042/tmp/transfers/implement_fix/retry-plan.md
    description: optional transient retry plan that isolates the missed forced-refresh branch
- task_memory_search_hints:
  - forced refresh branch
  - token expiry rollback fixture

Latest Checkpoint Context
- checkpoint_kind: progress
- outcome: null
- summary: code change is in place, unit coverage passed, and only the final browser rerun remains before terminal closure
- next_step: run the remaining browser verification, publish the final verification report, and then close terminally

Consumed Durable Refs
- kind: checkpoint
  slot: prior_retry_handoff
  path: C:/tasks/task_2026_0042/_runtime/attempts/attempt.implement_fix.11/latest-checkpoint.md
  description: prior terminal retry checkpoint for this same assignment
- kind: artifact
  slot: findings_report
  version: 2
  path: C:/tasks/task_2026_0042/outputs/artifacts/investigate_issue/findings_report/findings_report.v02.md
  description: current investigation findings for the auth-refresh regression

Transient Refs
- transient refs are optional carryover only; they are not durable truth
- path: C:/tasks/task_2026_0042/tmp/transfers/implement_fix/retry-plan.md
- description: optional transient retry plan that isolates the missed forced-refresh branch

Task Memory
- search hints:
  - forced refresh branch
  - token expiry rollback fixture
- `context/wiki/` = curated task-memory pages
- other curated docs under `context/` = source/reference material

Allowed Actions Now
- stay inside the same assignment and same attempt
- call `record_checkpoint` again only if later readers need newer handoff before terminal closure
- close terminally with `green`, `retry`, or `blocked`

Publication Rule
- keep semantic assignment handoff separate from runtime-resolved durable refs
- if the final rerun succeeds, satisfy required `produces` before `green`
```

## `parent_root_dispatch_prompt same_session_continue`

Scenario:

- current node: `root`
- send mode: `same_session_continue`
- continuity state: same attempt, same assignment
- current control state: one child assignment is already staged

```text
Current Dispatch
- current bound turn: same-attempt root continuation (internal dispatch id hidden)
- send mode: same_session_continue
- closure expectation: the child assignment is already staged; if the handoff reasoning is sufficient, emit `yield`

Workflow Manifest
- path: C:/tasks/task_2026_0042/_runtime/workflow-manifest.md
- description: whole-workflow visible contract for the current task

Current Assignment
- summary: decide the next bounded child step after the current investigation result
- instruction: stay inside the current direct-child set, reread the surfaced durable evidence, and preserve the decision reasoning through checkpoint handoff if needed
- criteria:
  - slot: root_release_rule
    description: root completion and release criteria
  - slot: implementation_entry_rule
    description: rule for when the implementation child may be assigned
- consumes:
  - kind: checkpoint
    slot: investigate_issue_summary
    description: latest investigation handoff for this root decision
  - kind: artifact
    slot: findings_report
    description: current investigation findings for the auth-refresh regression
- produces:
  - slot: root_decision_note
    description: durable decision note required when root reasoning must survive redispatch
- transient_refs:
  - path: C:/tasks/task_2026_0042/tmp/transfers/root/investigation-compare-grid.md
    description: optional transient comparison grid between the old failure and the current repro output
- task_memory_search_hints:
  - refresh token expiry branch
  - cookie rotation note

Latest Checkpoint Context
- checkpoint_kind: progress
- outcome: null
- summary: one implementation child assignment is already staged and the current checkpoint handoff explains why this child is next
- next_step: no further child assignment is legal on this open dispatch; emit `yield`

Consumed Durable Refs
- kind: checkpoint
  slot: investigate_issue_summary
  path: C:/tasks/task_2026_0042/_runtime/attempts/attempt.investigate_issue.02/latest-checkpoint.md
  description: latest investigation checkpoint handoff for the current root decision
- kind: artifact
  slot: findings_report
  version: 2
  path: C:/tasks/task_2026_0042/outputs/artifacts/investigate_issue/findings_report/findings_report.v02.md
  description: current investigation findings for the auth-refresh regression

Transient Refs
- transient refs are optional carryover only; they are not durable truth
- path: C:/tasks/task_2026_0042/tmp/transfers/root/investigation-compare-grid.md
- description: optional transient comparison grid between the old failure and the current repro output

Task Memory
- search hints:
  - refresh token expiry branch
  - cookie rotation note
- `context/wiki/` = curated task-memory pages
- other curated docs under `context/` = source/reference material

Allowed Actions Now
- no second `assign_child` is legal on this open dispatch
- if the current checkpoint handoff is sufficient, emit `yield`
- if later readers still need more decision reasoning, call `record_checkpoint` once more before `yield`

Publication Rule
- keep semantic child-assignment handoff separate from exact durable refs
- do not rely on session continuity to explain why this child was chosen
```

## `worker_dispatch_prompt blocked-ending sketch`

Scenario:

- current node: `implement_fix`
- send mode: `full_prompt`
- current attempt: still open
- current question: should the node end `blocked` or `retry`

```text
Latest Checkpoint Context
- checkpoint_kind: progress
- outcome: null
- summary: the bounded code change landed, but the final browser fixture still fails for reasons outside the current writable scope
- next_step: decide whether the remaining failure is retriable within the same assignment or whether the current attempt should end blocked
- blockers:
  - browser fixture ownership is outside the current assignment scope

Consumed Durable Refs
- kind: artifact
  slot: verification_report
  version: 2
  path: C:/tasks/task_2026_0042/outputs/artifacts/implement_fix/verification_report/verification_report.v02.md
  description: latest verification evidence showing the remaining out-of-scope failure

Allowed Actions Now
- if a later attempt on the same assignment is still justified, call `record_checkpoint` with `checkpoint_kind: terminal` and `outcome: retry`, then emit `retry`
- if the current assignment cannot continue without out-of-scope help, call `record_checkpoint` with `checkpoint_kind: terminal` and `outcome: blocked`, then emit `blocked`
- do not rely on transcript memory to explain the unresolved state

Publication Rule
- terminal closure still requires checkpoint handoff through `record_checkpoint`
- already-published outputs stay durable evidence; `blocked` does not erase them
```
