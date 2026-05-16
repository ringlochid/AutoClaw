# Generated Rendered Prompt Examples

Status: Generated reference

This page is generated from app-owned prompt assets under `apps/api/app/runtime/prompt/assets/` plus live prompt-render output from `render_prompt_bundle()`.

The `same_session_continue` examples below are renderer and persisted-request compatibility examples only. They do not prove that the shipped launch or continue paths currently open real dispatches with that send mode.
They model prebound same-attempt transport requests whose persisted request already carries `previous_response_id`.

If this page drifts from the runtime renderer, regenerate it from `python -m scripts.docs.prompt_catalog.cli generate` and then rerun validation.

## `parent_root_dispatch_prompt`

Scenario:

- current node: `root`
- send mode: `full_prompt`
- current lineage: root decides the next bounded child step from current surfaced evidence
- representative surfaced refs include a child checkpoint and curated wiki memory

```text
## Operating Model
- controller/DB state owns runtime truth
- generated files are shared projections derived from that truth
- `dispatch` is ingress, `record_checkpoint` is durable publication, and `yield | green | retry | blocked` are egress
- semantic assignment handoff stays separate from exact runtime-resolved durable refs in `consumed_durable_refs`
- `record_checkpoint` is the durable publication lane for what happened and what should happen next
- `workspace/` is mutable work and `_runtime/dispatch/` monitoring files are observability-only projections

## Task Identity
- task key: auth-refresh-hardening
- title: Harden auth refresh flow
- summary: Investigate and fix the auth refresh regression.
- task instruction: Stay scoped to the auth refresh failure path only.

## Node Purpose
- node key: root
- node kind: root
- role: root_planning_lead
- description: Coordinate the whole flow and decide the next bounded child step.

## Current Dispatch
- current bound turn: current root turn (internal dispatch id hidden)
- send mode: full_prompt
- closure expectation: use control tools now, call `record_checkpoint` if the reasoning must persist, then later emit `yield` or a terminal boundary

## Workflow Manifest
- path: C:/tasks/task_2026_0042/_runtime/workflow-manifest.md
- description: whole-workflow visible contract for the current task
- current node anchor: root
- structural edit palette:
  - roles:
    - architect (allowed node kinds: worker): Run a bounded QA sweep over current implementation evidence.
    - planning_lead (allowed node kinds: parent, worker): Coordinate a bounded implementation or review subtree.
  - policies:
    - standard-parent-planning (applies_to: parent): Default planning policy for bounded parent coordination.
    - standard-review (applies_to: worker): Default review policy for worker evidence checks.
- surfaced runtime file: C:/tasks/task_2026_0042/_runtime/attempts/attempt.investigate_issue.02/latest-checkpoint.md
- surfaced path: C:/tasks/task_2026_0042/context/wiki/cookie-rotation-note.md

## Current Assignment
- path: C:/tasks/task_2026_0042/_runtime/attempts/attempt.root.07/assignment.md
- summary: Decide the next bounded child step after the current investigation result.
- instruction: Stay inside the current direct-child set and preserve reasoning durably when needed.
- criteria:
  - kind: criteria
    slot: root_release_rule
    description: Root completion and release criteria.
- consumes:
  - kind: checkpoint
    description: Latest investigation handoff for this root decision.
  - kind: artifact
    slot: findings_report
    description: Current investigation findings for the auth-refresh regression.
- produces:
  - slot: root_decision_note
    description: Durable decision note required when root reasoning must survive redispatch.
- transient_refs:
  - path: C:/tasks/task_2026_0042/tmp/transfers/root/investigation-compare-grid.md
    description: Optional transient comparison grid for the current root decision.
- task_memory_search_hints:
  - refresh token expiry branch
  - cookie rotation note

## Latest Checkpoint Context
- path: C:/tasks/task_2026_0042/_runtime/attempts/attempt.investigate_issue.02/latest-checkpoint.md
- checkpoint_kind: progress
- outcome: null
- summary: One implementation child assignment is already staged and the current checkpoint explains why this child is next.
- next_step: If the handoff is sufficient, emit yield.
- task_memory_search_hints:
  - refresh token expiry branch

## Consumed Durable Refs
- kind: criteria
  slot: root_release_rule
  path: C:/tasks/task_2026_0042/context/criteria/root_release_rule.md
  description: Root completion and release criteria.
- kind: artifact
  slot: findings_report
  version: 2
  path: C:/tasks/task_2026_0042/outputs/artifacts/investigate_issue/findings_report/findings_report.v02.md
  description: Current investigation findings for the auth-refresh regression.
- kind: wiki
  path: C:/tasks/task_2026_0042/context/wiki/cookie-rotation-note.md
  description: Curated task-memory note about cookie rotation.

## Transient Refs
- transient refs are optional carryover only; they are not durable truth
- path: C:/tasks/task_2026_0042/tmp/transfers/root/investigation-compare-grid.md
  description: Optional transient comparison grid for the current root decision.

## Task Memory
- search hints:
  - refresh token expiry branch
  - cookie rotation note
- surfaced curated refs:
  - kind: wiki
    path: C:/tasks/task_2026_0042/context/wiki/cookie-rotation-note.md
    description: Curated task-memory note about cookie rotation.
- `context/wiki/` contains curated task-memory pages
- other curated docs under `context/` are source/reference material
- direct file/path search is the v1 retrieval model

## Allowed Actions Now
- tools: `assign_child`, `add_child`, `update_child`, `remove_child`, `release_green`, `release_blocked`, `record_checkpoint`
- use `assign_child` with semantic `assignment_intent`, `supplemental_durable_context`, and explicit `transient_surfaces` only; do not author final durable ref metadata for the child
- for structural edits, reread the current manifest first, start with role/policy names from the surfaced structural edit palette in this prompt or manifest, and reread the regenerated manifest after the edit before deciding whether one child assignment should be staged
- if the surfaced structural edit palette is still insufficient after reread, use the current-only `search_definitions` / `get_definition` read-only lookup lane before guessing
- if the needed role/policy name is still not surfaced after palette reread and current-only lookup, do not guess it; checkpoint the gap or choose a legal blocked path
- do not use definition revision history as dispatched planning input
- if exactly one child assignment is staged and the dispatch stays non-terminal, emit `yield`
- if later readers must understand why that child was staged or why release is not yet legal, call `record_checkpoint` before `yield` or terminal closure
- `release_green` and root `release_blocked` are terminal preconditions, not `yield` basis
- emit `green` only when this root node is closing its own current assignment; emit `blocked` only for root whole-flow terminal closure after committed `release_blocked`

## Publication Rule
- `produces` are requirements that gate successful completion
- runtime authors final durable publication metadata after required outputs exist
- later agents learn what happened from checkpoints plus surfaced refs, not hidden transcript memory
- ordinary prompt surfaces keep artifact refs compact and path-only
```

## `worker_dispatch_prompt`

Scenario:

- current node: `implement_fix`
- send mode: `full_prompt`
- current lineage: retry created a new attempt on the same assignment
- durable reminder: read the prior terminal checkpoint as retry handoff
- representative surfaced refs include curated wiki memory and checkpoint hints

```text
## Operating Model
- controller/DB state owns runtime truth
- generated files are shared projections derived from that truth
- `dispatch` is ingress, `record_checkpoint` is durable publication, and `yield | green | retry | blocked` are egress
- semantic assignment handoff stays separate from exact runtime-resolved durable refs in `consumed_durable_refs`
- `record_checkpoint` is the durable publication lane for what happened and what should happen next
- `workspace/` is mutable work and `_runtime/dispatch/` monitoring files are observability-only projections

## Task Identity
- task key: auth-refresh-hardening
- title: Harden auth refresh flow
- summary: Investigate and fix the auth refresh regression.
- task instruction: Stay scoped to the auth refresh failure path only.

## Node Purpose
- node key: implement_fix
- node kind: worker
- role: engineer
- description: Repair the bounded auth-refresh defect.

## Current Dispatch
- current bound turn: current worker turn (internal dispatch id hidden)
- send mode: full_prompt
- closure expectation: call `record_checkpoint`, then emit `green | retry | blocked`

## Workflow Manifest
- path: C:/tasks/task_2026_0042/_runtime/workflow-manifest.md
- description: whole-workflow visible contract for the current task
- current node anchor: implement_fix
- surfaced path: C:/tasks/task_2026_0042/context/wiki/auth-refresh-history.md

## Current Assignment
- path: C:/tasks/task_2026_0042/_runtime/attempts/attempt.implement_fix.01/assignment.md
- summary: Repair the auth-refresh defect and publish the required evidence.
- instruction: Change only the bounded auth-refresh logic and rerun scoped verification.
- criteria:
  - kind: criteria
    slot: fix_acceptance
    description: Bounded fix acceptance criteria.
- consumes:
  - kind: artifact
    slot: findings_report
    description: Current findings for the scoped fix.
- produces:
  - slot: change_patch
    description: Bounded code change artifact.
- transient_refs:
  - path: C:/tasks/task_2026_0042/tmp/transfers/implement_fix/repro-commands.txt
    description: Optional repro commands from the prior attempt.
- task_memory_search_hints:
  - auth refresh
  - cookie rotation note

## Latest Checkpoint Context
- path: C:/tasks/task_2026_0042/_runtime/attempts/attempt.implement_fix.01/latest-checkpoint.md
- checkpoint_kind: terminal
- outcome: retry
- summary: Prior attempt fixed the primary path but missed one recovery branch.
- next_step: Keep the same assignment and repair the missed branch.
- task_memory_search_hints:
  - recovery branch note

## Consumed Durable Refs
- kind: criteria
  slot: fix_acceptance
  path: C:/tasks/task_2026_0042/context/criteria/fix_acceptance.v01.md
  description: Bounded fix acceptance criteria.
- kind: artifact
  slot: findings_report
  version: 2
  path: C:/tasks/task_2026_0042/outputs/artifacts/investigate_issue/findings_report/findings_report.v02.md
  description: Current findings for the scoped fix.
- kind: wiki
  path: C:/tasks/task_2026_0042/context/wiki/auth-refresh-history.md
  description: Curated task-memory page for earlier auth-refresh attempts.

## Transient Refs
- transient refs are optional carryover only; they are not durable truth
- path: C:/tasks/task_2026_0042/tmp/transfers/implement_fix/repro-commands.txt
  description: Optional repro commands from the prior attempt.

## Task Memory
- search hints:
  - auth refresh
  - cookie rotation note
  - recovery branch note
- surfaced curated refs:
  - kind: wiki
    path: C:/tasks/task_2026_0042/context/wiki/auth-refresh-history.md
    description: Curated task-memory page for earlier auth-refresh attempts.
- `context/wiki/` contains curated task-memory pages
- other curated docs under `context/` are source/reference material
- direct file/path search is the v1 retrieval model

## Allowed Actions Now
- call `record_checkpoint` with a progress checkpoint if later readers need intermediate reasoning before terminal closure
- before `green`, `retry`, or `blocked`, call `record_checkpoint` with the terminal handoff for this attempt
- close with `green`, `retry`, or `blocked` only when justified by the current assignment and its current surfaced evidence
- do not use parent/root control tools from this dispatch
- callback remains a write-only semantic lane and not a context-discovery helper

## Publication Rule
- `produces` are requirements that gate successful completion
- runtime authors final durable publication metadata after required outputs exist
- later agents learn what happened from checkpoints plus surfaced refs, not hidden transcript memory
- ordinary prompt surfaces keep artifact refs compact and path-only
```

## `worker_dispatch_prompt same_session_continue`

Scenario:

- current node: `implement_fix`
- send mode: `same_session_continue`
- same attempt remains current and the prebound transport request already carries `previous_response_id`
- renderer compatibility example only; live dispatch opening still defaults to `full_prompt` on the current tree

```text
This message is a `same_session_continue` transport wrapper inside the same attempt.
It is not a new assignment, not a retry, and not a new prompt family.

Only the three static sections may be omitted from the inline wrapper:
- `operating_model`
- `task_identity`
- `node_purpose`

All dynamic prompt truth remains in scope:
- `current_dispatch`
- `workflow_manifest`
- `current_assignment`
- `latest_checkpoint_context` when present
- `consumed_durable_refs`
- `transient_refs` when present
- `task_memory` when present
- `allowed_actions_now`
- `publication_rule`

Do not treat `consumed_durable_refs` as one of the omittable sections.
If the full prompt contained surfaced `transient_refs` or task-memory guidance, keep them in scope for this same-attempt continuation unless the wrapper explicitly replaces those sections.


## Current Dispatch
- current bound turn: same-attempt worker continuation (internal dispatch id hidden)
- send mode: same_session_continue
- closure expectation: call `record_checkpoint`, then emit `green | retry | blocked`

## Workflow Manifest
- path: C:/tasks/task_2026_0042/_runtime/workflow-manifest.md
- description: whole-workflow visible contract for the current task
- current node anchor: implement_fix
- surfaced path: C:/tasks/task_2026_0042/context/wiki/auth-refresh-history.md

## Current Assignment
- path: C:/tasks/task_2026_0042/_runtime/attempts/attempt.implement_fix.01/assignment.md
- summary: Repair the auth-refresh defect and publish the required evidence.
- instruction: Change only the bounded auth-refresh logic and rerun scoped verification.
- criteria:
  - kind: criteria
    slot: fix_acceptance
    description: Bounded fix acceptance criteria.
- consumes:
  - kind: artifact
    slot: findings_report
    description: Current findings for the scoped fix.
- produces:
  - slot: change_patch
    description: Bounded code change artifact.
- transient_refs:
  - path: C:/tasks/task_2026_0042/tmp/transfers/implement_fix/repro-commands.txt
    description: Optional repro commands from the prior attempt.
- task_memory_search_hints:
  - auth refresh
  - cookie rotation note

## Latest Checkpoint Context
- path: C:/tasks/task_2026_0042/_runtime/attempts/attempt.implement_fix.01/latest-checkpoint.md
- checkpoint_kind: terminal
- outcome: retry
- summary: Prior attempt fixed the primary path but missed one recovery branch.
- next_step: Keep the same assignment and repair the missed branch.
- task_memory_search_hints:
  - recovery branch note

## Consumed Durable Refs
- kind: criteria
  slot: fix_acceptance
  path: C:/tasks/task_2026_0042/context/criteria/fix_acceptance.v01.md
  description: Bounded fix acceptance criteria.
- kind: artifact
  slot: findings_report
  version: 2
  path: C:/tasks/task_2026_0042/outputs/artifacts/investigate_issue/findings_report/findings_report.v02.md
  description: Current findings for the scoped fix.
- kind: wiki
  path: C:/tasks/task_2026_0042/context/wiki/auth-refresh-history.md
  description: Curated task-memory page for earlier auth-refresh attempts.

## Transient Refs
- transient refs are optional carryover only; they are not durable truth
- path: C:/tasks/task_2026_0042/tmp/transfers/implement_fix/repro-commands.txt
  description: Optional repro commands from the prior attempt.

## Task Memory
- search hints:
  - auth refresh
  - cookie rotation note
  - recovery branch note
- surfaced curated refs:
  - kind: wiki
    path: C:/tasks/task_2026_0042/context/wiki/auth-refresh-history.md
    description: Curated task-memory page for earlier auth-refresh attempts.
- `context/wiki/` contains curated task-memory pages
- other curated docs under `context/` are source/reference material
- direct file/path search is the v1 retrieval model

## Allowed Actions Now
- call `record_checkpoint` with a progress checkpoint if later readers need intermediate reasoning before terminal closure
- before `green`, `retry`, or `blocked`, call `record_checkpoint` with the terminal handoff for this attempt
- close with `green`, `retry`, or `blocked` only when justified by the current assignment and its current surfaced evidence
- do not use parent/root control tools from this dispatch
- callback remains a write-only semantic lane and not a context-discovery helper

## Publication Rule
- `produces` are requirements that gate successful completion
- runtime authors final durable publication metadata after required outputs exist
- later agents learn what happened from checkpoints plus surfaced refs, not hidden transcript memory
- ordinary prompt surfaces keep artifact refs compact and path-only
```

## `parent_root_dispatch_prompt same_session_continue`

Scenario:

- current node: `root`
- send mode: `same_session_continue`
- same parent/root attempt remains current and the prebound transport request already carries `previous_response_id`
- renderer compatibility example only; live dispatch opening still defaults to `full_prompt` on the current tree

```text
This message is a `same_session_continue` transport wrapper inside the same attempt.
It is not a new assignment, not a retry, and not a new prompt family.

Only the three static sections may be omitted from the inline wrapper:
- `operating_model`
- `task_identity`
- `node_purpose`

All dynamic prompt truth remains in scope:
- `current_dispatch`
- `workflow_manifest`
- `current_assignment`
- `latest_checkpoint_context` when present
- `consumed_durable_refs`
- `transient_refs` when present
- `task_memory` when present
- `allowed_actions_now`
- `publication_rule`

Do not treat `consumed_durable_refs` as one of the omittable sections.
If the full prompt contained surfaced `transient_refs` or task-memory guidance, keep them in scope for this same-attempt continuation unless the wrapper explicitly replaces those sections.


## Current Dispatch
- current bound turn: same-attempt root continuation (internal dispatch id hidden)
- send mode: same_session_continue
- closure expectation: use control tools now, call `record_checkpoint` if the reasoning must persist, then later emit `yield` or a terminal boundary

## Workflow Manifest
- path: C:/tasks/task_2026_0042/_runtime/workflow-manifest.md
- description: whole-workflow visible contract for the current task
- current node anchor: root
- structural edit palette:
  - roles:
    - architect (allowed node kinds: worker): Run a bounded QA sweep over current implementation evidence.
    - planning_lead (allowed node kinds: parent, worker): Coordinate a bounded implementation or review subtree.
  - policies:
    - standard-parent-planning (applies_to: parent): Default planning policy for bounded parent coordination.
    - standard-review (applies_to: worker): Default review policy for worker evidence checks.
- surfaced runtime file: C:/tasks/task_2026_0042/_runtime/attempts/attempt.investigate_issue.02/latest-checkpoint.md
- surfaced path: C:/tasks/task_2026_0042/context/wiki/cookie-rotation-note.md

## Current Assignment
- path: C:/tasks/task_2026_0042/_runtime/attempts/attempt.root.07/assignment.md
- summary: Decide the next bounded child step after the current investigation result.
- instruction: Stay inside the current direct-child set and preserve reasoning durably when needed.
- criteria:
  - kind: criteria
    slot: root_release_rule
    description: Root completion and release criteria.
- consumes:
  - kind: checkpoint
    description: Latest investigation handoff for this root decision.
  - kind: artifact
    slot: findings_report
    description: Current investigation findings for the auth-refresh regression.
- produces:
  - slot: root_decision_note
    description: Durable decision note required when root reasoning must survive redispatch.
- transient_refs:
  - path: C:/tasks/task_2026_0042/tmp/transfers/root/investigation-compare-grid.md
    description: Optional transient comparison grid for the current root decision.
- task_memory_search_hints:
  - refresh token expiry branch
  - cookie rotation note

## Latest Checkpoint Context
- path: C:/tasks/task_2026_0042/_runtime/attempts/attempt.investigate_issue.02/latest-checkpoint.md
- checkpoint_kind: progress
- outcome: null
- summary: One implementation child assignment is already staged and the current checkpoint explains why this child is next.
- next_step: If the handoff is sufficient, emit yield.
- task_memory_search_hints:
  - refresh token expiry branch

## Consumed Durable Refs
- kind: criteria
  slot: root_release_rule
  path: C:/tasks/task_2026_0042/context/criteria/root_release_rule.md
  description: Root completion and release criteria.
- kind: artifact
  slot: findings_report
  version: 2
  path: C:/tasks/task_2026_0042/outputs/artifacts/investigate_issue/findings_report/findings_report.v02.md
  description: Current investigation findings for the auth-refresh regression.
- kind: wiki
  path: C:/tasks/task_2026_0042/context/wiki/cookie-rotation-note.md
  description: Curated task-memory note about cookie rotation.

## Transient Refs
- transient refs are optional carryover only; they are not durable truth
- path: C:/tasks/task_2026_0042/tmp/transfers/root/investigation-compare-grid.md
  description: Optional transient comparison grid for the current root decision.

## Task Memory
- search hints:
  - refresh token expiry branch
  - cookie rotation note
- surfaced curated refs:
  - kind: wiki
    path: C:/tasks/task_2026_0042/context/wiki/cookie-rotation-note.md
    description: Curated task-memory note about cookie rotation.
- `context/wiki/` contains curated task-memory pages
- other curated docs under `context/` are source/reference material
- direct file/path search is the v1 retrieval model

## Allowed Actions Now
- tools: `assign_child`, `add_child`, `update_child`, `remove_child`, `release_green`, `release_blocked`, `record_checkpoint`
- use `assign_child` with semantic `assignment_intent`, `supplemental_durable_context`, and explicit `transient_surfaces` only; do not author final durable ref metadata for the child
- for structural edits, reread the current manifest first, start with role/policy names from the surfaced structural edit palette in this prompt or manifest, and reread the regenerated manifest after the edit before deciding whether one child assignment should be staged
- if the surfaced structural edit palette is still insufficient after reread, use the current-only `search_definitions` / `get_definition` read-only lookup lane before guessing
- if the needed role/policy name is still not surfaced after palette reread and current-only lookup, do not guess it; checkpoint the gap or choose a legal blocked path
- do not use definition revision history as dispatched planning input
- if exactly one child assignment is staged and the dispatch stays non-terminal, emit `yield`
- if later readers must understand why that child was staged or why release is not yet legal, call `record_checkpoint` before `yield` or terminal closure
- `release_green` and root `release_blocked` are terminal preconditions, not `yield` basis
- emit `green` only when this root node is closing its own current assignment; emit `blocked` only for root whole-flow terminal closure after committed `release_blocked`

## Publication Rule
- `produces` are requirements that gate successful completion
- runtime authors final durable publication metadata after required outputs exist
- later agents learn what happened from checkpoints plus surfaced refs, not hidden transcript memory
- ordinary prompt surfaces keep artifact refs compact and path-only
```

## `worker_dispatch_prompt blocked-ending sketch`

Scenario:

- current node: `implement_fix`
- send mode: `full_prompt`
- current attempt: still open
- current question: should the node end `blocked` or `retry`

```text
## Latest Checkpoint Context
- path: C:/tasks/task_2026_0042/_runtime/attempts/attempt.implement_fix.11/latest-checkpoint.md
- checkpoint_kind: progress
- outcome: null
- summary: the bounded code change landed, but the final browser fixture still fails for reasons outside the current writable scope
- next_step: decide whether the remaining failure is retriable within the same assignment or whether the current attempt should end blocked
- blockers:
  - browser fixture ownership is outside the current assignment scope

## Consumed Durable Refs
- kind: artifact
  slot: verification_report
  version: 2
  path: C:/tasks/task_2026_0042/outputs/artifacts/implement_fix/verification_report/verification_report.v02.md
  description: latest verification evidence showing the remaining out-of-scope failure

## Allowed Actions Now
- if a later attempt on the same assignment is still justified, call `record_checkpoint` with `checkpoint_kind: terminal` and `outcome: retry`, then emit `retry`
- if the current assignment cannot continue without out-of-scope help, call `record_checkpoint` with `checkpoint_kind: terminal` and `outcome: blocked`, then emit `blocked`
- do not rely on transcript memory to explain the unresolved state

## Publication Rule
- terminal closure still requires checkpoint handoff through `record_checkpoint`
- already-published outputs stay durable evidence; `blocked` does not erase them
```
