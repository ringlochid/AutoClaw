# Controller contract and resumable execution

Status: Target

This page defines V2 controller truth, currentness, workflow advancement, and resumable execution across dispatch replacement and controller-owned external waits.

## Core rule

Controller-owned persisted state is the only runtime truth owner.

For agent-originated work, controller truth changes through validated node MCP operations. Provider streams, callbacks, prompt artifacts, support files, task events, UI caches, and local deployment bindings may project or explain that truth, but none of them replace it.

## Controller truth families

The controller owns:

- task and immutable compose identity
- active flow structure and explicit parent/child ownership
- current assignment per current runtime node
- current attempt per current assignment
- one current dispatch slot per task lineage
- current `AttemptPlan` per worker attempt
- latest checkpoint per attempt
- staged parent/root continuation outcomes
- accepted runtime boundaries
- human-request and command-run source rows
- one current waiting cause or none
- durable artifact publications and current pointers
- capability decisions
- task events as authoritative chronology, but not source-row currentness

The exact local runtime records are defined in [Runtime records and control state](runtime-records-and-control-state.md).

## Truth precedence

When surfaces disagree, use this order:

1. task, flow, structural revision, assignment, attempt, dispatch, plan, checkpoint, boundary, and active-wait source rows
2. durable artifact publication and current-pointer rows
3. capability and policy decisions
4. task events for event chronology
5. controller-generated API, prompt, CLI, and file read models
6. adapter-private or provider-native detail

Chronology does not become currentness. A newer task event, file timestamp, or provider message never supersedes a current pointer or validated source row.

## Controller mutation law

Every runtime mutation follows one sequence:

1. validate the inbound schema and trusted node or operator authority
2. reread current controller truth under the owning lock
3. derive the candidate state without mutating current rows in place
4. validate currentness, capability, dependency, boundary, and budget legality
5. atomically commit source rows and explicit currentness changes
6. close stale authority where the transition requires it
7. reread committed truth
8. produce task events and read models from that commit

Provider I/O happens after desired controller state commits. Provider output is never replayed into controller truth as an alternative mutation path.

## Currentness model

The controller maintains:

- one active structural revision per flow
- one current assignment per current runtime node
- one current attempt per current assignment
- one latest checkpoint pointer per attempt
- zero or one current plan per attempt
- at most one current dispatch whose status is `starting`, `open`, or `closing` per task lineage
- one current durable artifact pointer per owner and slot
- one active external waiting cause or none per task lineage

Stale writes fail before commit. An earlier dispatch, closed node session, superseded attempt, resolved external wait, or non-current structural basis cannot reopen or mutate current work.

## Assignment, attempt, dispatch, and session

These identities remain distinct:

- an assignment is one forward-looking mission contract
- an attempt is one semantic try of that assignment
- a dispatch is one controller-to-agent execution turn within the attempt
- a node session is the existing task/node-recognition authority for one dispatch
- a provider session hint is optional opaque conversation continuity

Consequences:

- watchdog recovery creates a new dispatch on the same assignment and attempt
- external-wait resolution creates a new dispatch on the same assignment and attempt
- semantic `retry` alone creates a new attempt
- provider session reuse never establishes currentness or authorizes node MCP
- a provider may return a replacement session hint without changing controller lineage
- a provider session hint is reused only with the provider that created it

## Dispatch lifecycle

The generic dispatch lifecycle is:

```text
starting -> open -> closed
starting -> closing -> closed
open -> closing -> closed
```

The only statuses are:

- `starting`
- `open`
- `closing`
- `closed`

The only close reasons are:

- `boundary`
- `human_request_wait`
- `command_run_wait`
- `cancelled`
- `superseded`
- `control_failed`

The controller commits the dispatch, complete prompt transport request, and node-session authority before provider launch. Successful provider start handoff records `adapter_started_at` and opens the dispatch. It does not prove agent progress.

The precommitted node session closes the launch-handoff race: a current `starting` dispatch may accept node MCP work, but start success may move only a still-current `starting` dispatch to `open`. It never reopens a dispatch that an early legal MCP wait or boundary already closed.

Initial provider-control exhaustion closes the dispatch as `control_failed` and pauses the task with `runtime_recovery_exhausted`; ordinary continue may prepare a new same-attempt dispatch after repair.

Meaningful accepted node MCP-backed commits advance `last_progress_at`. Provider acceptance, output, events, native tools, disconnect, and terminal state advance nothing.

The full lifecycle and retry policy belong to [Runtime lifecycle and watchdog](runtime-lifecycle-and-watchdog.md).

## Workflow advancement

V2 preserves the explicit tree and boundary model:

- ingress is `dispatch`
- egress uses `return_boundary(yield | green | retry | blocked)`
- terminal worker outcomes are `green | retry | blocked`
- parent/root child handoff remains explicit `yield`
- parent/root continuation outcomes are staged by explicit controller tools
- provider terminal success is never a runtime boundary

Boundary acceptance requires current controller authority and the checkpoint rules owned by [Attempt plan and checkpoint contract](attempt-plan-and-checkpoint-contract.md).

Normal accepted boundary progression is internal controller work. It is not an operator waiting cause and does not use provider stop. The provider response ends naturally after the agent's boundary call.

## Plans and checkpoints

Every worker attempt creates and maintains one structured `AttemptPlan`. Changed plan updates are the normal visible progress surface.

Checkpoints are narrow durable handoffs:

- progress before child yield
- progress before opening a human request
- progress before starting a long command run
- terminal immediately before `green | retry | blocked`

There is no start checkpoint and no checkpoint after an ordinary plan step. Parent/root plan behavior remains unchanged.

## Resumable execution

Resumption means reconstructing a legal dispatch from current controller truth. It does not mean resuming a provider response or generic chat transcript.

The controller persists enough truth to continue the same task lineage after:

- typed human-request answer, timeout, or cancellation
- command-run success, failure, timeout, or cancellation
- operator pause and later operator resume
- watchdog replacement of a stale dispatch
- provider session-continuity failure that falls back to fresh context

Every continuation:

1. reads the source row or pause state that authorizes consideration
2. rereads task, structure, assignment, attempt, dispatch, plan, and checkpoint currentness
3. recomputes capability and boundary legality
4. closes any stale node-session authority
5. commits a new dispatch and prompt from current truth when legal
6. optionally passes the prior provider session hint

The adapter may reuse conversation context, start a fresh session, or return a new hint. None of those choices change the controller transition.

## Canonical waiting causes

The controller may expose exactly these current waiting causes:

- `paused_by_operator`
- `waiting_for_human_request`
- `waiting_for_command_run`

Rules:

- only one waiting cause may be active for one current task lineage
- historical waits remain queryable, but do not compete with currentness
- ordinary workflow advancement is not a waiting cause
- watchdog recovery is active controller work, not a waiting cause
- exhausted runtime recovery pauses the task with `pause_reason = runtime_recovery_exhausted`; it does not add another waiting cause
- `continue_task` remains operator pause-resume and repaired-runtime resume; it is not the mechanism that resolves a human request or command run

The former adapter-reconnect and internal-fencing waiting causes are removed. Provider connectivity is handled inside provider-control retry, and watchdog recovery is handled by the runtime supervisor.

## Human-request continuation

A human request is opened by a legal node MCP operation after its required progress checkpoint.

Opening it:

- commits the request source row
- sets `waiting_for_human_request`
- closes current node-session authority
- closes the dispatch with `human_request_wait`
- keeps task, assignment, attempt, and plan non-terminal
- does not call provider stop
- does not record a terminal checkpoint or boundary

Answer, timeout, or cancellation makes the request record terminal according to the human-request owner. That source transition clears the matching waiting cause and may open a new dispatch on the same attempt after currentness and legality are recomputed.

The exact request types and resolution policy belong to [Human request and approval contract](../interfaces/human-request-and-approval-contract.md).

## Command-run continuation

A long command run follows the same controller shape:

- progress checkpoint first
- command source row commits
- `waiting_for_command_run` becomes current
- current node-session authority and dispatch close
- the provider response ends naturally
- the command runner owns execution, logs, timeout, and cancellation
- a terminal command row authorizes controller reconsideration
- a legal replacement dispatch opens on the same attempt and plan

The exact command states and process mechanics belong to [Command run and external wait](command-run-and-external-wait.md).

## Watchdog continuation

The watchdog evaluates only the current open dispatch. Its stale anchor is `last_progress_at ?? adapter_started_at`, and its default deadline is 900 seconds.

Recovery:

- closes old node-session authority
- retries provider stop through the central manager
- closes the stale dispatch as `superseded`
- opens a replacement dispatch on the same assignment, attempt, and plan
- retries provider start through the same manager

After two restart cycles by default, or after provider-control exhaustion, the controller closes the affected dispatch as `control_failed` and pauses the task with `runtime_recovery_exhausted`.

There is no provider-terminal progression path. A provider response that ends without a controller boundary is indistinguishable from any other execution that stops making semantic progress; the watchdog handles it after the same deadline.

## Semantic retry

Worker `retry` remains different from runtime recovery.

Semantic retry:

- requires a terminal retry checkpoint
- closes the old attempt
- keeps the assignment
- creates a new current attempt
- starts that attempt with no current plan
- prepares a new dispatch from controller truth
- may pass provider continuity only as an optional adapter hint

The old attempt's plan and checkpoints remain audit history. They do not become the new attempt's current plan.

## Operator pause, continue, and cancel

### Pause

Pause commits controller intent and closes current node-session authority. Pausing an open dispatch explicitly cancels that dispatch through the one central stop lane and closes it with `closed_reason = cancelled`; the task itself remains paused rather than cancelled. The task carries `paused_by_operator`.

### Continue

Continue is legal for an operator-paused task and for a task paused with `runtime_recovery_exhausted` after the provider is repaired. It rereads current controller truth and opens a new same-attempt dispatch when legal.

Continue does not answer human requests, finish command runs, or infer a provider reconnect.

### Cancel

Cancel commits terminal controller intent, closes node-session authority, routes stop through the same manager, and closes the dispatch as `cancelled`. Provider stop success does not replace the controller cancellation commit.

## Task events and read models

`task_events` are authoritative for append-only chronology and cursor replay. They are not authority for currentness or legality.

Events are emitted from committed source-row changes, including plan revisions, checkpoint creation, dispatch control readback, external-wait transitions, and boundaries. Replaying events must never re-execute provider control or semantic mutations.

Support panels, CLI status, and SSE consumers derive their state from source rows plus events. No removed provider-event or dispatch-monitor file family is required for runtime correctness.

## Effective capability truth

The effective capability set for one dispatch is controller-owned even when it is computed from other controller records.

Rules:

- resolve from current role, policy, task, `resolved_provider`, local runtime configuration, and adapter constraints before launch
- keep one stable capability decision for the dispatch
- prompts, task events, and API read models project that decision
- provider-native permission prompts must not become hidden interactive waits
- denied provider-native operations fail or route through the explicit AutoClaw human-request lane according to the capability owner

The exact capability vocabulary belongs to [Capability, security, and audit](../interfaces/capability-security-and-audit.md).

## Required invariants

- controller source rows outrank provider and projection detail
- one task lineage has at most one current executable dispatch
- provider fallback resolves before dispatch commit
- provider choice is fixed for one dispatch
- node-session authority exists before provider launch
- provider start retry does not consume semantic work time
- only meaningful accepted node MCP-backed commits advance semantic progress
- external waits own closed dispatches, not suspended provider turns
- external-wait and watchdog continuation preserve the current attempt
- only semantic retry creates a new attempt
- provider session continuity is optional and opaque
- provider terminal state never closes an assignment, attempt, or boundary

## Related contracts

- [Runtime lifecycle and watchdog](runtime-lifecycle-and-watchdog.md)
- [Runtime records and control state](runtime-records-and-control-state.md)
- [Attempt plan and checkpoint contract](attempt-plan-and-checkpoint-contract.md)
- [Adapter contract](adapter-contract.md)
- [Human request and approval contract](../interfaces/human-request-and-approval-contract.md)
- [Control API](../interfaces/control-api.md)
- [Task event stream](../interfaces/task-event-stream.md)
- [Capability, security, and audit](../interfaces/capability-security-and-audit.md)
- [V1 runtime boundary and controller loop](../../v1/architecture/runtime-boundary-and-controller-loop-contract.md)
- [Command run and external wait](command-run-and-external-wait.md)
