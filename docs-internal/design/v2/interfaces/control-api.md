# Control API

Status: Target

This page owns V2 task runtime reads, operator controls, human-request and command-run routes, snapshots, and traces. Event listing and streaming belong to the [task event stream](task-event-stream.md).

## Core rule

The Control API reads controller source rows and commits explicit controller intent. It never reconstructs currentness from provider output, task events, support files, or opaque provider session state.

All routes are task-authorized. Mutations record the stable actor reference when the caller identity is known.

## Route families

The target routes are:

```text
GET  /control/tasks/{task_id}
GET  /control/tasks/{task_id}/snapshot
GET  /control/tasks/{task_id}/trace
GET  /control/tasks/{task_id}/events
GET  /control/tasks/{task_id}/events/stream

GET  /control/tasks/{task_id}/human-requests
POST /control/tasks/{task_id}/human-requests/{request_id}/resolve

GET  /control/tasks/{task_id}/command-runs
GET  /control/tasks/{task_id}/command-runs/{run_id}
GET  /control/tasks/{task_id}/command-runs/{run_id}/log
POST /control/tasks/{task_id}/command-runs/{run_id}/cancel

POST /control/tasks/{task_id}/pause
POST /control/tasks/{task_id}/continue
POST /control/tasks/{task_id}/cancel
```

The event routes are listed here for public route cohesion; their exact carrier, cursor, and replay contract lives only in the task-event owner.

No route exposes provider credentials, raw authentication state, provider payloads, or `provider_session_hint`.

## Task runtime read

`GET /control/tasks/{task_id}` extends the shipped compact flow read with the current V2 runtime fields:

```yaml
RuntimeFlowRead:
    task_id: string
    task_title: string
    task_summary: string
    workflow_key: string | null
    status: pending | running | blocked | paused | succeeded | cancelled
    active_flow_revision_id: string
    workflow_manifest_ref: ref
    current_node_key: string | null
    active_attempt_id: string | null
    waiting_cause: >-
      paused_by_operator | waiting_for_human_request |
      waiting_for_command_run | null
    pause_reason: paused_by_operator | runtime_recovery_exhausted | null
    current_dispatch: dispatch_runtime_read | null
    current_plan: attempt_plan_read | null
    watchdog_restart_count: integer | null
    current_human_request: human_request_summary | null
    current_command_run: command_run_summary | null
    updated_at: timestamp
```

The nested reads are:

```yaml
dispatch_runtime_read:
    dispatch_id: string
    previous_dispatch_id: string | null
    status: starting | open | closing | closed
    closed_reason: >-
      boundary | human_request_wait | command_run_wait | cancelled |
      superseded | control_failed | null
    requested_provider: openclaw | codex | claude
    resolved_provider: openclaw | codex | claude
    adapter_started_at: timestamp | null
    last_progress_at: timestamp | null
    provider_control: provider_control_readback | null

attempt_plan_read:
    attempt_id: string
    revision: integer
    explanation: string | null
    steps:
        - step: string
          status: pending | in_progress | completed
    updated_by_dispatch_id: string
    updated_at: timestamp
```

`current_dispatch` is the current or most recently closed dispatch for the active attempt when one exists. `current_plan` is null only before the worker's first accepted `update_plan` or when there is no active worker attempt.

Provider provenance is exactly the requested and resolved provider selected by controller resolution for that dispatch. Detailed fallback diagnostics may remain in authorized support readback. Session hints and credentials never appear.

The provider-control readback is:

```yaml
provider_control_readback:
    operation: start | stop | null
    state: queued | attempting | retry_scheduled | succeeded | failed | null
    attempt: integer | null
    max_attempts: integer | null
    next_retry_at: timestamp | null
    last_error_summary: string | null
    updated_at: timestamp | null
```

This is controller-owned status for AutoClaw's operation. It is not provider lifecycle. `attempt` is the provider-control call number, not the semantic attempt identifier.

Human-request and command-run summaries identify the current source wait and its source state. Their complete records remain on the dedicated routes.

## Snapshot

`GET /control/tasks/{task_id}/snapshot` returns the runtime flow read plus the smallest operator-ready summary:

```yaml
OperatorFlowSnapshotResponse:
    flow: RuntimeFlowRead
    top_actionable_items:
        - summary: string
          node_key: string | null
          current_paths: ref[]
          suggested_action: string | null
    current_paths: ref[]
    stream_head_event_id: string | null
```

`stream_head_event_id` is a bootstrap anchor only. The snapshot remains a source row read; its event-stream anchor does not make the event log currentness authority.

Actionable items may point to current plan work, an open human request, a command run, provider-control retry, operator pause, or exhausted recovery. They must not infer actions from provider terminal output.

## Trace

`GET /control/tasks/{task_id}/trace` accepts `OperatorFlowTraceQuery`:

```yaml
OperatorFlowTraceQuery:
    scope: current | whole
    q: string | null
    cursor: string | null
    limit: 1..200
    sort: occurred_at_desc | occurred_at_asc
```

The response is:

```yaml
OperatorFlowTraceResponse:
    task_id: string
    scope: current | whole
    graph_nodes: task_graph_node[]
    dependency_edges: task_graph_dependency[]
    dispatch_history:
        - dispatch_id: string
          attempt_id: string
          assignment_key: string | null
          assignment_summary: string | null
          node_key: string
          status: starting | open | closing | closed
          closed_reason: string | null
          requested_provider: string
          resolved_provider: string
          adapter_started_at: timestamp | null
          last_progress_at: timestamp | null
          created_at: timestamp
          closed_at: timestamp | null
    checkpoint_history: checkpoint_history_entry[]
    boundary_history: boundary_history_entry[]
    current_paths: ref[]
    next_cursor: string | null
```

Trace history uses generic dispatch lifecycle and semantic checkpoints. It has no delivery status, provider terminal result, provider run identifier, provider session hint, or reopen-after-inactivity field.

Plan currentness is read from `current_plan`; plan chronology is carried by `plan_updated` events. Individual `NodeMcpInvocation` rows remain internal and do not expand the ordinary trace.

## Operator task controls

Pause, continue, and cancel accept the current structural guard as typed query parameters:

```yaml
RuntimeFlowControlQuery:
    expected_active_flow_revision_id: string

RuntimeFlowPauseResponse:
    flow: RuntimeFlowRead
```

Pause returns `RuntimeFlowPauseResponse`. Continue and cancel return `RuntimeFlowRead` directly.

### Pause

Pause commits operator intent. If a current dispatch is starting, open, or closing, the controller closes NodeSession authority and routes stop through the single `AgentControlManager` lane before closing the dispatch as `cancelled`.

An existing human-request or command-run source wait stays source-owned. Pause does not fabricate a provider dispatch or resolve the source. If that source becomes terminal while the task is operator-paused, continuation remains held until ordinary operator continue.

While the source remains open, `waiting_cause` continues to name that source and `pause_reason` records `paused_by_operator`. After the source becomes terminal, the task remains paused and `waiting_cause` may return to `paused_by_operator` until continue succeeds.

### Continue

Continue is legal for:

- an operator-paused task
- a task paused with `pause_reason = runtime_recovery_exhausted` after provider repair

Continue recomputes task, structure, attempt, plan, capability, wait, and provider legality before preparing a new same-attempt dispatch.

Continue does not answer a human request, complete a command run, infer provider reconnect, or resume a provider response. Current source waits must reach their own terminal state through their owning routes or managers.

### Cancel

Cancel commits terminal task intent. It closes node authority, routes any live dispatch through the same centralized stop lane, and closes the dispatch as `cancelled`.

Task cancellation also closes or cancels current external-wait sources according to their owners. Later source callbacks or provider output cannot reopen the cancelled task.

## Human-request routes

`GET /control/tasks/{task_id}/human-requests` returns chronological typed source records with their terminal resolution when present:

```yaml
human_request_list_response:
    task_id: string
    items:
        - request: pending_human_request
          resolution: human_request_resolution | null
```

`POST /control/tasks/{task_id}/human-requests/{request_id}/resolve` accepts:

```yaml
human_request_resolve_request:
    item_responses:
        - item_id: string
          selected_option: string | null
          freeform_answer: string | null
          extra_notes: string | null
          response_payload: object | null
```

It may answer only the current open request that owns `waiting_for_human_request`. Timeout and cancellation are controller-owned terminal paths and are not caller-selected answer kinds.

The response contains the committed typed resolution. A successful resolution may cause the controller to prepare a new same-attempt dispatch after legality recomputation; the HTTP handler does not directly resume a provider turn.

```yaml
human_request_resolve_response:
    task_id: string
    resolution: human_request_resolution
```

## Command-run routes

`GET /control/tasks/{task_id}/command-runs` returns bounded chronological items with cursor pagination:

```yaml
command_run_list_response:
    task_id: string
    items:
        - run_id: string
          state: >-
            pending_start | running | cancellation_requested | succeeded |
            failed | timed_out | cancelled
          command: string
          description: string | null
          workdir: string | null
          created_at: timestamp
          started_at: timestamp | null
          ended_at: timestamp | null
          timeout_seconds: integer | null
          summary: string | null
          exit_code: integer | null
          signal: string | null
          log_ref: string | null
    next_cursor: string | null
```

`GET /control/tasks/{task_id}/command-runs/{run_id}` returns the complete normalized controller record, including cancellation and terminal provenance.

```yaml
command_run_record:
    run_id: string
    task_id: string
    dispatch_id: string
    attempt_id: string
    command: string
    description: string
    workdir: string | null
    state: >-
      pending_start | running | cancellation_requested | succeeded | failed |
      timed_out | cancelled
    created_at: timestamp
    started_at: timestamp | null
    ended_at: timestamp | null
    timeout_seconds: integer | null
    latest_update: string | null
    latest_log_ref: string | null
    cancellation_requested_at: timestamp | null
    cancellation_requested_by_actor_ref: string | null
    terminal_result: command_run_terminal_result | null
    terminal_event_source: controller | control_api | operator_mcp | null
    terminal_actor_ref: string | null
```

`GET /control/tasks/{task_id}/command-runs/{run_id}/log` returns the authorized append-only retained log:

```yaml
command_run_log_response:
    task_id: string
    run_id: string
    log_ref: string
    content: string
```

`POST /control/tasks/{task_id}/command-runs/{run_id}/cancel` targets one current non-terminal run. Accepted intent may return `cancellation_requested`; that state remains non-terminal and does not clear the source wait.

```yaml
command_run_cancel_response:
    task_id: string
    run: command_run_list_item
```

## Failure contract

All mutation failures use the shared structured runtime failure shape:

```yaml
operation_failure:
    code: string
    summary: string
    is_retryable: boolean
    suggested_next_step: string | null
```

Currentness, stale source, invalid transition, capability, authorization, path, and request-shape errors are distinct normalized codes. Raw provider exceptions, credentials, process environment, and stack traces are not response payloads.

Control writes commit source state before asynchronous provider or runner work. The API response reports committed controller truth, not a guessed final provider result.

## Read-model and control invariants

- current task reads expose plan revision, semantic progress, provider resolution, provider-control retry, restart count, pause/recovery, and source waits
- source rows remain authoritative when an event consumer is delayed
- source waits are resolved through their owning lanes, never `continue`
- provider-control status describes AutoClaw operations, not provider runtime state
- session hints, credentials, provider events, and raw provider errors are absent from public contracts
- API restart can reconstruct unresolved local control work from dispatch and bounded provider-control state without replaying task events

## Validation scenarios

The Control API contract must prove:

- a running dispatch is readable without any provider stream
- a changed plan appears with its new revision, while an identical update does not change plan or semantic progress
- provider retry readback exposes call count and next retry time
- exhausted initial or watchdog control pauses with `runtime_recovery_exhausted`
- a human or command terminal source can continue the same attempt without operator `continue`
- operator pause holds an otherwise terminal source continuation
- no provider-native hidden prompt is required to operate any control route

## Related contracts

- [Task event stream](task-event-stream.md)
- [Controller contract and resumable execution](../architecture/controller-contract-and-resumable-execution.md)
- [Runtime records and control state](../architecture/runtime-records-and-control-state.md)
- [Runtime lifecycle and watchdog](../architecture/runtime-lifecycle-and-watchdog.md)
- [Attempt plan and checkpoint contract](../architecture/attempt-plan-and-checkpoint-contract.md)
- [Human request and approval contract](human-request-and-approval-contract.md)
- [Command run and external wait](../architecture/command-run-and-external-wait.md)
- [Capability, security, and audit](capability-security-and-audit.md)
