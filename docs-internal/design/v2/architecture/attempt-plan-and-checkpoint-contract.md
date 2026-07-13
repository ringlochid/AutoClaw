# Attempt plan and checkpoint contract

Status: Target

This page owns the V2 distinction between a worker's current structured plan and the durable checkpoint records used for handoff, external waits, and terminal boundary evidence.

## Core rule

An `AttemptPlan` says what the current worker intends to do and which meaningful step is active. A checkpoint says what later controller work or another agent must durably know at a handoff or terminal boundary.

Plans are the ordinary visible progress surface. Checkpoints are not a command-by-command or plan-step diary.

## `AttemptPlan`

One current plan belongs to one attempt.

Required persisted shape:

```yaml
attempt_plan:
    attempt_id: string
    revision: integer
    steps_json:
        - step: string
          status: pending | in_progress | completed
    explanation: string | null
    updated_by_dispatch_id: string
    updated_at: timestamp
```

Rules:

- every worker calls `update_plan`, including a worker with one meaningful step
- a plan contains between 1 and 9 meaningful steps
- exactly one step is `in_progress` unless every step is `completed`
- a one-step worker starts with that step `in_progress`
- each call replaces the current plan snapshot for the attempt
- the first accepted plan has revision 1
- every changed accepted snapshot increments revision by one
- `updated_by_dispatch_id` records the dispatch that committed the revision
- `explanation` is optional for the first plan and required when replanning changes the intended step sequence or meaning materially
- step text describes outcomes, not shell commands or low-level tool calls
- workers update the plan after meaningful step transitions, not after every command

Parent and root nodes keep their existing orchestration behavior. V2 does not require them to create an `AttemptPlan` or mention the watchdog threshold in their prompt.

## `update_plan` acceptance

The node MCP `update_plan` operation validates:

- current task, node-session, dispatch, assignment, and attempt authority
- worker role
- step count and statuses
- exactly-one-active invariant
- revision currentness where the tool contract exposes it
- explanation requirement for material replanning

The server owns revision assignment and timestamps. The agent does not claim them as trusted values.

An identical snapshot is a successful no-op readback:

- no new revision
- no `plan_updated` task event
- no `last_progress_at` advancement
- `NodeMcpInvocation.advanced_progress = false`

A changed accepted snapshot commits the new plan, one bounded `plan_updated` task event, and the `last_progress_at` advancement in the same transaction.

## Plan lifecycle

Plan ownership follows attempt ownership:

- watchdog recovery opens a new dispatch on the same attempt and keeps the current plan
- human-request resolution opens a new dispatch on the same attempt and keeps the current plan
- command-run completion opens a new dispatch on the same attempt and keeps the current plan
- provider session fallback or replacement does not change the plan
- semantic `retry` closes the old attempt and creates a new attempt with no current plan until its worker calls `update_plan`
- a fresh child assignment and attempt receive their own plan

After recovery or external-wait continuation, `get_current_context` returns the current plan inline. The worker updates it before continuing when the prior active step or sequence is no longer accurate.

## Plan completion and terminal outcomes

For a terminal `green` result, every plan step must be `completed` before the terminal checkpoint and boundary are accepted.

For terminal `retry` or `blocked`, unfinished steps are allowed. The terminal checkpoint explains the reason, evidence collected, and the next lawful handoff.

Plan completion does not itself close an attempt or dispatch. Only the matching terminal checkpoint plus accepted `return_boundary` operation does that.

## Checkpoint purpose

The V1 checkpoint schema and artifact-validation rules remain the baseline with one explicit schema removal and the timing changes below. V2 removes `task_memory_search_hints` from both the `record_checkpoint` request and every checkpoint row, API read, and generated projection. No renamed memory-hint field replaces it.

V2 keeps two checkpoint kinds:

- `progress`
- `terminal`

Progress checkpoints are durable handoff records. Terminal checkpoints are the evidence required immediately before a terminal runtime boundary.

Checkpoint currentness remains controller-owned through the attempt's latest checkpoint pointer. Generated checkpoint files are projections only.

## Allowed progress checkpoints

A progress checkpoint is required only immediately before one of these actions:

- yielding to a child
- opening a human request
- starting a long command run

The checkpoint captures enough durable state for the next dispatch to resume without hidden provider memory. It should include:

- concise work completed so far
- important decisions or evidence
- produced artifacts or surfaced transient refs allowed by the assignment
- the exact next action after continuation
- unresolved risks relevant to the handoff

Rules:

- record the checkpoint before the action that closes the current dispatch
- a progress checkpoint has `outcome = null`
- an accepted progress checkpoint advances `last_progress_at`
- do not record a start checkpoint
- do not checkpoint after an ordinary plan step
- do not checkpoint per shell command, file edit, or provider tool call
- do not use checkpoints as a timer-renewal operation

`update_plan`, other meaningful node MCP-backed mutations, and these narrow checkpoint moments provide the visible semantic progress needed by the watchdog.

## Child yield

Before a legal parent/root `yield`:

1. the parent/root stages the child assignment under the existing boundary rules
2. the current node records a progress checkpoint for the handoff
3. the current node calls `return_boundary(yield)`
4. the controller validates and advances the explicit tree

`yield` remains a workflow boundary, not a checkpoint outcome. The progress checkpoint exists because the next agent execution needs durable handoff context.

## Human-request and command-run waits

Before opening either external wait, the worker records one progress checkpoint. After the wait-opening node MCP operation succeeds, the worker:

- stops its provider response immediately
- does not record a terminal checkpoint
- does not call `return_boundary`

The task, assignment, attempt, and plan remain current. The controller closes the dispatch with the corresponding external-wait reason. When the source row becomes terminal and continuation remains legal, the replacement dispatch receives the current plan plus `checkpoint_to_resume_from`.

## Terminal checkpoints

A terminal checkpoint is required immediately before one of these terminal outcomes:

- `green`
- `retry`
- `blocked`

Rules:

- `checkpoint_kind = terminal`
- `outcome` exactly matches the requested terminal boundary
- the checkpoint contains final evidence, artifact claims, criteria status, remaining risk, and the appropriate handoff
- the existing terminal preflight validates artifact and release legality
- the accepted checkpoint advances `last_progress_at`
- the boundary must follow while the same dispatch, assignment, attempt, and terminal checkpoint remain current
- a provider response ending without the boundary has no terminal meaning

The sequence is:

```text
finish or stop planned work
  -> make plan status truthful
  -> record terminal checkpoint
  -> call return_boundary(green | retry | blocked)
  -> stop the provider response
```

## Resume context

`get_current_context` exposes:

- current assignment and attempt
- current `AttemptPlan`, when one exists
- `checkpoint_to_resume_from`, when continuation requires a durable handoff
- normalized human-request or command-run continuation context
- current allowed actions and surfaced task paths

When `checkpoint_to_resume_from` exists, the worker reads that checkpoint before replanning or acting. The task-file MCP owner defines how the projected file is read. Provider conversation continuity may supplement this context but never replaces it.

## Progress relationship

The semantic progress rule is:

| Operation                                      | Advances `last_progress_at` |
| ---------------------------------------------- | --------------------------- |
| changed, accepted `update_plan`                | yes                         |
| identical `update_plan`                        | no                          |
| allowed accepted progress checkpoint           | yes                         |
| accepted terminal checkpoint                   | yes                         |
| successful structural/controller mutation     | yes                         |
| context or task-file read                      | no                          |
| failed, rejected, stale, or unauthorized call | no                          |
| provider event, output, or terminal frame      | no                          |

The invocation record and semantic mutation commit together where practical. There is no second activity timer.

## Non-goals

This contract does not add:

- plan-step tables
- percentages or estimated completion time
- more plan statuses
- a parent/root plan requirement
- a checkpoint for every plan transition
- a generic heartbeat or lease-renewal tool
- request replay or new client idempotency requirements

## Related contracts

- [Runtime lifecycle and watchdog](runtime-lifecycle-and-watchdog.md)
- [Runtime records and control state](runtime-records-and-control-state.md)
- [Controller contract and resumable execution](controller-contract-and-resumable-execution.md)
- [V1 checkpoint contract](../../v1/architecture/checkpoint-contract.md)
- [V1 assignment contract](../../v1/architecture/assignment-contract.md)
- [Node and operator MCP surface contract](../interfaces/node-and-operator-mcp-surface-contract.md)
- [Task root and file access](task-root-and-file-access.md)
