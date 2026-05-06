# Prompt Composition Example

Status: Reference

This page shows how the live v1 prompt layer is assembled into the persisted
transport request and how prompt-layer validation should fail when generated
examples drift from the live owner docs.

Use this page when you want:

- exact persisted request keys for `prompt-request.json`
- the live `instructions_text` versus `input_text` split
- current-node-anchor, checkpoint, and `consumed_durable_refs` examples that
  match the landed renderer shape
- the exact `same_session_continue` wrapper behavior
- prompt-layer validation messages for stale or malformed generated prompts

For the fully rendered prompt body examples, use
[generated/rendered-examples.md](generated/rendered-examples.md).

## Search-first routing

- exact rendered prompt body examples:
  [generated/rendered-examples.md](generated/rendered-examples.md)
- exact section order and section owners:
  [source-and-sections.md](source-and-sections.md)
- exact compact ref rendering:
  [field-renderers.md](field-renderers.md)
- exact persistence and send-mode rules:
  [render-and-persistence.md](render-and-persistence.md)
- exact reusable system/provider wording:
  [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md)
- exact reusable legality wording:
  [prompt-pack/runtime-rule-blocks.md](prompt-pack/runtime-rule-blocks.md)

## Stable composition stack

The live v1 composition stack is:

1. static provider-side `instructions_text` on `full_prompt`
2. regenerated dynamic `input_text` body in canonical section order
3. persisted full prompt artifact at `_runtime/dispatch/<dispatch_id>/prompt.md`
4. persisted request artifact at `_runtime/dispatch/<dispatch_id>/prompt-request.json`
5. optional `same_session_continue` inline wrapper for the next same-attempt
   dispatch

Rules:

- `instructions_text` is present only for `full_prompt`
- `input_text` is always present and carries the node-facing prompt body for the
  current send mode
- persisted `prompt.md` always keeps the full canonical prompt, even when
  `input_text` is wrapped for `same_session_continue`
- `same_session_continue` may omit only `Operating Model`, `Task Identity`, and
  `Node Purpose` from inline transport
- every non-static section that exists in the full prompt stays in scope for
  `same_session_continue`

## Exact `full_prompt` request shape: `worker_dispatch_prompt`

The persisted request keys below are exact. The long prompt strings are
excerpted here; use [generated/rendered-examples.md](generated/rendered-examples.md)
plus the prompt-pack owner docs when you need every rendered line or reusable
block byte.

```yaml
prompt_request_json:
  dispatch_id: dispatch.implement_fix.01
  node_key: implement_fix
  attempt_id: attempt.implement_fix.01
  assignment_key: implement_fix.assign-01
  prompt_name: worker_dispatch_prompt
  send_mode: full_prompt
  previous_response_id: null
  instructions_text: |
    You are AutoClaw, a delegated node inside a controller-first runtime.
    ...
    Current node-kind, role, and policy guidance for this dispatch:
    - node kind: worker
    - node key: implement_fix
    - node description: Repair the bounded auth-refresh defect.
    - role: engineer
    - role description: Worker for one bounded engineering assignment.
    - role instruction: Complete only the current assignment.
    - policy: standard-worker
    - policy description: Default worker behavior for bounded work.
  input_text: |
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
  content_hash: sha256:...
  transport_request_hash: sha256:...
  rendered_at: 2026-05-05T12:40:11+00:00
```

## Exact `full_prompt` request shape: `parent_root_dispatch_prompt`

The surfaced checkpoint path appears once in `Latest Checkpoint Context`.
`Consumed Durable Refs` keeps the other exact current durable refs for the turn
and does not repeat that same checkpoint path.

```yaml
prompt_request_json:
  dispatch_id: dispatch.root.07
  node_key: root
  attempt_id: attempt.root.07
  assignment_key: root.assign-07
  prompt_name: parent_root_dispatch_prompt
  send_mode: full_prompt
  previous_response_id: null
  instructions_text: |
    You are AutoClaw, a delegated node inside a controller-first runtime.
    ...
    Current node-kind, role, and policy guidance for this dispatch:
    - node kind: root
    - node key: root
    - node description: Coordinate the whole flow and decide the next bounded child step.
    - role: root_planning_lead
    - role description: Root coordinator for the whole task.
    - role instruction: Choose the next bounded child step and close only when release is legal.
    - policy: standard-root-planning
    - policy description: Default root planning and closure behavior.
  input_text: |
    ## Workflow Manifest
    - path: C:/tasks/task_2026_0042/_runtime/workflow-manifest.md
    - description: whole-workflow visible contract for the current task
    - current node anchor: root
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
  content_hash: sha256:...
  transport_request_hash: sha256:...
  rendered_at: 2026-05-05T12:41:03+00:00
```

## Checkpoint publication excerpt

When a checkpoint surfaces durable output claims, the rendered field names are
`produced_artifacts`, `transient_refs`, and `task_memory_search_hints`.

```text
## Latest Checkpoint Context
- path: C:/tasks/task_2026_0042/_runtime/attempts/attempt.implement_fix.02/latest-checkpoint.md
- checkpoint_kind: terminal
- outcome: green
- summary: the bounded fix and verification completed and the current outputs are ready for parent/root review
- next_step: parent/root may consume the published outputs and decide whether release or further review is now legal
- produced_artifacts:
  - kind: artifact
    slot: change_patch
    version: 2
    path: C:/tasks/task_2026_0042/outputs/artifacts/implement_fix/change_patch/change_patch.v02.diff
    description: bounded code change artifact for the current assignment
  - kind: artifact
    slot: verification_report
    version: 3
    path: C:/tasks/task_2026_0042/outputs/artifacts/implement_fix/verification_report/verification_report.v03.md
    description: scoped verification evidence for the current assignment
- transient_refs:
  - path: C:/tasks/task_2026_0042/tmp/transfers/implement_fix/browser-rerun-notes.md
    description: optional transient browser rerun notes that do not become durable truth
- task_memory_search_hints:
  - browser rerun follow-up
```

## Exact assembly: `worker_dispatch_prompt` `same_session_continue`

This is the persisted transport-request shape for renderer-verified same-attempt
continuation. `instructions_text` is `null`, the inline wrapper stays at the
top of `input_text`, and every non-static section remains present.

```yaml
prompt_request_json:
  dispatch_id: dispatch.implement_fix.01
  node_key: implement_fix
  attempt_id: attempt.implement_fix.01
  assignment_key: implement_fix.assign-01
  prompt_name: worker_dispatch_prompt
  send_mode: same_session_continue
  previous_response_id: resp_impl_fix_01
  instructions_text: null
  input_text: |
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
  content_hash: sha256:...
  transport_request_hash: sha256:...
  rendered_at: 2026-05-05T12:42:14+00:00
```

## Exact assembly: `parent_root_dispatch_prompt` `same_session_continue`

The same transport rule applies to parent/root continuation. The inline wrapper
keeps the current surfaced checkpoint, current node anchor, and other dynamic
context in scope for the same attempt.

```yaml
prompt_request_json:
  dispatch_id: dispatch.root.07
  node_key: root
  attempt_id: attempt.root.07
  assignment_key: root.assign-07
  prompt_name: parent_root_dispatch_prompt
  send_mode: same_session_continue
  previous_response_id: resp_root_07
  instructions_text: null
  input_text: |
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
    - for structural edits, reread the current manifest first, discover valid role/policy ids through the registry read lane, and reread the regenerated manifest after the edit before deciding whether one child assignment should be staged
    - if exactly one child assignment is staged and the dispatch stays non-terminal, emit `yield`
    - if later readers must understand why that child was staged or why release is not yet legal, call `record_checkpoint` before `yield` or terminal closure
    - `release_green` and root `release_blocked` are terminal preconditions, not `yield` basis
    - emit `green | blocked` only when this root node is closing its own current assignment

    ## Publication Rule
    - `produces` are requirements that gate successful completion
    - runtime authors final durable publication metadata after required outputs exist
    - later agents learn what happened from checkpoints plus surfaced refs, not hidden transcript memory
    - ordinary prompt surfaces keep artifact refs compact and path-only
  content_hash: sha256:...
  transport_request_hash: sha256:...
  rendered_at: 2026-05-05T12:42:49+00:00
```

## Exact prompt-layer validation messages

These are the kinds of exact validation failures the prompt layer should emit
when generated examples drift from the live owner docs.

### Reject: `same_session_continue` omitted a required non-static section

```text
Prompt generation reject
- prompt_name: worker_dispatch_prompt
- send_mode: same_session_continue
- summary: The persisted `input_text` includes `task_memory` in the full prompt truth, but the same-session wrapper omitted that non-static section.
- required fix: Resend every non-static section present in the full prompt body: `current_dispatch`, `workflow_manifest`, `current_assignment`, `latest_checkpoint_context`, `consumed_durable_refs`, `transient_refs`, `task_memory`, `allowed_actions_now`, and `publication_rule`.
```

### Reject: progress checkpoint rendered with terminal outcome

```text
Prompt generation reject
- prompt_name: parent_root_dispatch_prompt
- section: latest_checkpoint_context
- summary: `checkpoint_kind: progress` must render with `outcome: null`. A progress checkpoint may not teach `green`, `retry`, or `blocked` as its outcome.
- required fix: Regenerate `latest_checkpoint_context` from the canonical checkpoint projection and keep terminal outcomes only for `checkpoint_kind: terminal`.
```

### Reject: compact artifact ref drifted into current-pointer internals

```text
Prompt generation reject
- prompt_name: worker_dispatch_prompt
- section: consumed_durable_refs
- summary: Ordinary prompt rendering may surface only compact artifact refs: `slot`, `version`, `path`, and `description`. The rendered example leaked controller-only pointer fields such as `assignment_key`, `attempt_id`, or `supersedes_path`.
- required fix: Replace the leaked pointer fields with the compact artifact ref shape.
```

### Reject: worker prompt omitted `consumed_durable_refs`

```text
Prompt generation reject
- prompt_name: worker_dispatch_prompt
- summary: Worker prompts must include `consumed_durable_refs` because the current assignment requires bounded must-read durable refs.
- required fix: Regenerate the prompt with surfaced criteria, artifact, and explicit doc/wiki refs rendered in the `consumed_durable_refs` section, without re-listing the checkpoint already rendered in `latest_checkpoint_context`.
```

### Reject: parent/root prompt reintroduced removed control wording

```text
Prompt generation reject
- prompt_name: parent_root_dispatch_prompt
- section: allowed_actions_now
- summary: The rendered prompt reintroduced removed live-model wording such as `run_child(...)`, child retry control, or reassignment control.
- required fix: Use only the canonical parent/root tools `assign_child`, `add_child`, `update_child`, `remove_child`, `release_green`, and `release_blocked`.
```

## Exact review checklist for these examples

Before accepting a new rendered prompt example, verify:

1. the persisted request uses `instructions_text` only for `full_prompt` and
   `null` for `same_session_continue`
2. the prompt family is `worker_dispatch_prompt` or `parent_root_dispatch_prompt`
3. static sections are omitted only for `same_session_continue`
4. `workflow_manifest` renders the current node anchor
5. every `Current Assignment` and `Latest Checkpoint Context` example renders a
   `- path:` line
6. `produced_artifacts`, `transient_refs`, and
   `task_memory_search_hints` use the live checkpoint field names when present
7. `Consumed Durable Refs` de-duplicates the checkpoint already rendered in
   `Latest Checkpoint Context`
8. `path` and `version` do not leak into current-assignment `criteria`,
   `consumes`, or `produces`
9. same-session examples do not overclaim that live dispatch opening currently
   auto-selects `same_session_continue`
10. monitoring files are not treated as normal assignment truth

## Related live owners

- [contract.md](contract.md)
- [source-and-sections.md](source-and-sections.md)
- [field-renderers.md](field-renderers.md)
- [render-and-persistence.md](render-and-persistence.md)
- [machine-contract.md](machine-contract.md)
