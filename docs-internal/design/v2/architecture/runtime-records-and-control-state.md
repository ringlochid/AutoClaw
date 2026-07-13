# Runtime records and control state

Status: Target

This page owns the V2 persisted records and relations required by the local runtime, semantic MCP progress, minimal provider control, same-attempt watchdog recovery, and the reset-only physical schema delta.

The semantic shapes below are provider-neutral. The physical table, column, constraint, index, stale-schema, and reset rules in this page are the implementation contract; no separate persistence appendix owns them.

## Core rule

Persist controller facts that are necessary to reconstruct legality and local runtime intent. Do not persist a provider-shaped parallel account of agent execution.

V2 keeps assignment, attempt, checkpoint, boundary, external-wait, and task event truth. It uses one generic dispatch family, one existing node-session authority family, one attempt plan, one minimal node MCP invocation family, and small provider-control readback.

## Record families

### Retained controller truth

V2 retains these existing semantic families unless another V2 owner changes their exact schema:

- task, compose, flow, structural revision, node, and edge
- assignment and attempt
- checkpoint and terminal boundary
- staged parent/root continuation outcomes
- durable artifact publication and current pointers
- human request and command run source rows
- task events
- role, policy, and capability decisions
- root and workspace bindings that survive the V2 task-root simplification

These rows keep their existing authority roles. This page does not move workflow semantics into dispatch or provider-control state.

### Added or reshaped runtime truth

V2 adds or reshapes:

- `Dispatch`
- persisted `PromptTransportRequest`
- existing `NodeSession`, created before provider launch
- `AttemptPlan`
- `NodeMcpInvocation`
- attempt watchdog restart count
- generic provider start/stop readback

## `Dispatch`

`Dispatch` represents one controller-to-agent execution turn. It is not a provider run and does not require a provider-native run identifier.

Required semantic fields:

```yaml
dispatch:
    dispatch_id: string
    task_id: string
    flow_id: string
    flow_node_id: string
    assignment_id: string
    attempt_id: string
    previous_dispatch_id: string | null
    requested_provider: string
    resolved_provider: string
    provider_session_hint: string | null
    status: starting | open | closing | closed
    closed_reason: >-
      boundary | human_request_wait | command_run_wait | cancelled |
      superseded | control_failed | null
    adapter_started_at: timestamp | null
    last_progress_at: timestamp | null
    created_at: timestamp
    closed_at: timestamp | null
```

Rules:

- `requested_provider` records the lawful operator/task preference at dispatch preparation time
- `resolved_provider` records the provider selected after fallback and before dispatch commit
- one dispatch never changes `resolved_provider`
- `provider_session_hint` is optional opaque continuity context
- the session hint is never parsed by generic runtime code and never authorizes node MCP
- the session hint is scoped to `resolved_provider` and is not passed across provider changes
- `adapter_started_at` commits only after provider start hands off successfully
- `last_progress_at` is nullable until the first meaningful accepted node MCP semantic commit
- `closed_reason` is null until status is `closed`
- one task lineage has at most one current dispatch whose status is `starting`, `open`, or `closing`
- historical dispatch rows are immutable except for their bounded lifecycle, progress, control-readback, and closure fields

The generic dispatch record has no OpenClaw Gateway session or run column and no provider-terminal status.

## Persisted `PromptTransportRequest`

The complete prompt transport request is committed before launch and belongs to one dispatch.

Required semantic fields:

```yaml
prompt_transport_request:
    dispatch_id: string
    instructions_text: string
    input_text: string
    created_at: timestamp
```

Rules:

- `instructions_text` and `input_text` remain separate when an adapter supports that split
- one-message adapters may flatten them only at their private transport edge
- retries of one dispatch use the same committed prompt request
- replacement dispatches regenerate a new request from current controller truth
- a support/readback Markdown rendering is optional and never authoritative

The prompt owner may add hashes or derived readback fields. Such additions do not become runtime currentness.

## `NodeSession`

V2 keeps the existing task/node-recognition model. It does not introduce an execution grant, generation, or provider-specific MCP credential.

Required semantic fields remain:

```yaml
node_session:
    flow_node_id: string
    dispatch_id: string
    attempt_id: string
    assignment_id: string
    session_key: string
    session_status: open | closed
    opened_at: timestamp
    closed_at: timestamp | null
```

Rules:

- create the node session in the same commit as the `starting` dispatch and prompt request
- `session_key` plus task scope resolves the current node, assignment, attempt, and dispatch server-side
- provider session identifiers never replace or authorize this row
- close authority before a dispatch closes, opens an external wait, enters watchdog replacement, or is cancelled
- stale, closed, superseded, or non-current session writes fail before commit

## Attempt restart state

The current attempt owns its watchdog restart budget because watchdog recovery preserves the attempt.

Required semantic field:

```yaml
attempt:
    watchdog_restart_count: integer
```

Rules:

- initialize to zero for a new semantic attempt
- increment once for each watchdog replacement cycle that reaches replacement preparation
- preserve it across external waits and same-attempt continuation
- do not increment it for provider start retries within one dispatch
- do not increment it for semantic `retry`; that creates a new attempt whose count starts at zero

## Generic provider-control readback

Persist only enough start/stop state for support visibility and lifespan reconciliation.

Required semantic fields stored directly on `dispatch_turns`:

```yaml
provider_control_readback:
    dispatch_id: string
    control_operation: start | stop | null
    control_state: queued | attempting | retry_scheduled | succeeded | failed | null
    control_attempt: integer | null
    control_max_attempts: integer | null
    control_next_retry_at: timestamp | null
    control_last_error_summary: string | null
    control_updated_at: timestamp | null
```

Rules:

- `control_attempt` is the current provider-control call number, not `Attempt.attempt_id`
- `control_state` is controller-owned provider-control readback, not a provider lifecycle state
- errors are sanitized summaries, not raw provider payload archives
- successful completion clears delayed-retry fields
- on API restart, dispatch lifecycle status plus this bounded readback is enough for the supervisor to resubmit unresolved local control work
- no durable queue or outbox is required for the local-first runtime
- no provider output, tool event, or token stream is stored here

The task-event owner emits a bounded `dispatch_control_updated` event when material readback changes. Events are read models over this controller state and do not drive retries.

## `AttemptPlan`

The exact plan contract belongs to [Attempt plan and checkpoint contract](attempt-plan-and-checkpoint-contract.md). Its persisted shape is:

```yaml
attempt_plan:
    attempt_id: string
    revision: integer
    steps_json: json
    explanation: string | null
    updated_by_dispatch_id: string
    updated_at: timestamp
```

One current plan exists per attempt after the worker's first accepted `update_plan`. Plan currentness follows `attempt_id`; it does not follow a provider session or dispatch.

## `NodeMcpInvocation`

`NodeMcpInvocation` is the minimal audit and progress-timing record around one node MCP tool call.

Its fields are exactly:

```yaml
node_mcp_invocation:
    invocation_id: string
    dispatch_id: string
    tool_name: string
    status: started | completed | failed
    started_at: timestamp
    finished_at: timestamp | null
    advanced_progress: boolean
    failure_code: string | null
```

Rules:

- create or mark `started` only after task, node-session, dispatch, assignment, and attempt authority validates
- mark `completed` or `failed` after tool handling finishes
- set `advanced_progress = true` only when the call committed meaningful semantic progress
- update `Dispatch.last_progress_at` in the same transaction as the semantic commit and successful invocation completion
- read-only calls may complete with `advanced_progress = false`
- failed, rejected, stale, and no-op calls never advance progress
- record a stable normalized `failure_code`; do not archive stack traces or raw provider messages in this row

This record deliberately has no:

- request or response payload archive
- replay result
- client idempotency key
- execution generation
- provider identity
- new MCP credential

The controller does not emit one main task-timeline event per invocation. The owning semantic mutation emits its normal bounded event when that event family requires one.

FastMCP and provider SDKs continue to own low-level request transport. Existing validators continue to own mutation legality.

## Physical V2 schema delta

Retained V1 semantic tables keep their existing physical ownership except for the exact changes below. SQLAlchemy may map timestamps and JSON to the native SQLite or Postgres representation, but the table names, column names, nullability, relationships, checks, and index purposes are canonical.

### `dispatch_turns`

`dispatch_turns` is rewritten to carry the exact `Dispatch` fields above plus the provider-control columns named in `provider_control_readback`. It no longer carries delivery, Gateway, provider-terminal, foreground-fence, or provider-event columns.

Required constraints and indexes:

- `ck_dispatch_turns_status` permits only `starting | open | closing | closed`
- `ck_dispatch_turns_closed_reason` permits only the six documented reasons or null
- `ck_dispatch_turns_closure_consistency` requires a non-null close reason and `closed_at` only for `closed`, and requires both to be null otherwise
- `ck_dispatch_turns_provider_control_operation` permits only `start | stop` or null
- `ck_dispatch_turns_provider_control_state` permits only the five documented control states or null
- `ck_dispatch_turns_provider_control_attempts` requires positive attempt values, `control_attempt <= control_max_attempts`, and both values to be present or absent together
- `uq_dispatch_turns_one_active_flow` is a partial unique index on `flow_id` for rows whose status is `starting`, `open`, or `closing`
- `ix_dispatch_turns_attempt_created_at` indexes `(attempt_id, created_at)` for same-attempt chronology

The existing primary key remains `dispatch_id`. Task, flow, node, assignment, attempt, and previous-dispatch identifiers remain foreign keys to their owning rows.

### `dispatch_prompt_requests`

`dispatch_prompt_requests` is the one-to-one persisted `PromptTransportRequest`:

- `dispatch_id` is both primary key and foreign key to `dispatch_turns.dispatch_id`
- `instructions_text` and `input_text` are required text columns
- `created_at` is a required timezone-aware timestamp

No prompt row may outlive or belong to more than one dispatch.

### `attempts` and `attempt_plans`

`attempts` adds required integer `watchdog_restart_count` with default zero and `ck_attempts_watchdog_restart_count_nonnegative`.

`attempt_plans` stores the exact `AttemptPlan` shape:

- `attempt_id` is both primary key and foreign key to `attempts.attempt_id`
- `revision` is required and positive
- `steps_json` is required JSON
- `explanation` is nullable text
- `updated_by_dispatch_id` is a required foreign key to `dispatch_turns.dispatch_id`
- `updated_at` is a required timezone-aware timestamp
- `ck_attempt_plans_revision_positive` enforces revision at least one

One attempt therefore has at most one current plan row. Revision history remains in persisted `plan_updated` task events rather than additional plan-revision rows.

### `node_mcp_invocations`

`node_mcp_invocations` stores the exact invocation shape above:

- `invocation_id` is the primary key
- `dispatch_id` is a required foreign key to `dispatch_turns.dispatch_id`
- `tool_name`, `status`, `started_at`, and `advanced_progress` are required
- `finished_at` and `failure_code` are nullable
- `ck_node_mcp_invocations_status` permits only `started | completed | failed`
- `ck_node_mcp_invocations_finish_consistency` requires `finished_at` for completed or failed rows and null for started rows
- `ck_node_mcp_invocations_failure_consistency` permits `failure_code` only for failed rows
- `ix_node_mcp_invocations_dispatch_started_at` indexes `(dispatch_id, started_at)`

### `node_sessions`

`node_sessions` keeps the documented recognition fields. `dispatch_id` is required and unique, so one dispatch has exactly one NodeSession row; `session_key` remains indexed for recognition. Provider session hints never appear in this table.

### Removed columns on retained tables

The physical V2 delta also removes these currently shipped columns without replacements:

- `assignments.task_memory_search_hints_json`
- `attempt_checkpoints.task_memory_search_hints_json`
- `task_composes.context_root_path`
- `dispatch_turns.gateway_session_key`
- `dispatch_turns.gateway_run_id`

## Relations and currentness

The runtime must enforce these relationships:

- one immutable task compose per task run
- one current assignment per current runtime node
- one current attempt per current assignment
- one latest checkpoint pointer per attempt
- zero or one current `AttemptPlan` per attempt
- at most one current `starting`, `open`, or `closing` dispatch per task lineage
- one prompt transport request per dispatch
- one node session per current dispatch
- many node MCP invocations per dispatch
- one active external waiting cause or none per task lineage

Currentness never comes from newest timestamps, lexical file names, provider history, prompt memory, or task-event order.

## Removed record families

V2 removes these provider-shaped generic runtime families:

- provider event records
- dispatch delivery-state records
- dispatch continuity-state records
- dispatch watchdog-state records

V2 also removes the unused context and task-memory persistence family:

- `ContextSpaceModel`
- `ContextItemModel`
- context-root and context/wiki manifest fields, including `context_root_path`
- task-memory search-hint fields, including `task_memory_search_hints`

It also removes these identifiers from generic runtime records:

- `gateway_run_id`
- `gateway_session_key`
- `last_provider_signal_at`
- `provider_signal_seen`
- `provider_completed`
- `provider_failed`

Provider-specific adapters may keep private active handles in the lifespan-owned manager while work is local and live. Those handles are not a generic persisted record family. Optional opaque continuity persists only as `provider_session_hint`.

## Removed file families

V2 removes the four dispatch-monitor projections:

```text
_runtime/dispatch/<dispatch_id>/delivery-state.json
_runtime/dispatch/<dispatch_id>/continuity-state.json
_runtime/dispatch/<dispatch_id>/watchdog-state.json
_runtime/dispatch/<dispatch_id>/provider-events.ndjson
```

No compatibility writer, ignored readback field, or alternate filename keeps these families live. Runtime support consumes controller records and task events instead.

The remaining task-root and projected-file contract belongs to [Task root and file access](task-root-and-file-access.md).

## Removed monitor ownership

The target source tree removes four overlapping monitor owners:

- foreground provider lifecycle manager
- provider event-ingest manager
- dispatch lifecycle reconciler
- standalone watchdog manager

One `LocalRuntimeSupervisor` replaces their scheduling ownership. Domain services still validate and commit their own rows; the supervisor does not become a semantic god object.

## Reset-only schema policy

This simplification is an intentional reset boundary, not an in-place data migration.

Rules:

- startup compares the configured AutoClaw schema against current ORM metadata using exact application table and column sets, not only missing-table checks
- backend-owned system tables are excluded, but an extra or missing AutoClaw table or column is a stale-schema mismatch
- named foreign-key, check-constraint, unique-index, and ordinary-index signatures for the V2 delta above must also match
- a database containing removed provider-event, delivery, continuity, watchdog, Gateway-ID, task-memory-hint, or context-root schema therefore fails startup with diagnostic code `runtime_schema_reset_required`
- the diagnostic tells the operator to run `autoclaw db reset`
- startup does not silently retain, reinterpret, or partially migrate removed fields
- reset recreates only the current V2 schema and task-root shape
- reset may delete AutoClaw-owned local runtime data after normal confirmation
- reset and upgrade code must never recursively delete an externally bound context path or any other user-owned external directory

The known removed fingerprint must receive explicit coverage even when the general equality check already detects it:

```yaml
removed_tables:
  - context_spaces
  - context_items
  - dispatch_delivery_states
  - dispatch_continuity_states
  - dispatch_watchdog_states
  - provider_event_records
removed_columns:
  assignments:
    - task_memory_search_hints_json
  dispatch_turns:
    - gateway_session_key
    - gateway_run_id
  attempt_checkpoints:
    - task_memory_search_hints_json
  task_composes:
    - context_root_path
```

Reset mechanics are exact:

- SQLite reset replaces only the configured AutoClaw database after normal confirmation, recreates current metadata, and reruns required seeds
- Postgres reset drops and recreates AutoClaw-owned tables in the configured schema after normal confirmation, preserves unrelated schemas, recreates current metadata, and reruns required seeds
- neither reset traverses or deletes task workspace bindings, an old external context path, or another user-owned directory
- `db upgrade` does not attempt an in-place V1-to-V2 runtime data migration; it returns the same reset guidance for this epoch break

Required schema proof covers fresh and reset SQLite, fresh and reset Postgres, and stale SQLite/Postgres fixtures containing every removed table or column family above. Each fresh/reset schema must match current table, column, foreign-key, check, unique-index, and index signatures. Each stale fixture must fail before runtime startup with `runtime_schema_reset_required` and the `autoclaw db reset` remediation.

## Projection and readback rule

Controller records remain authoritative. Task events, API carriers, CLI status, and any remaining generated files are read models.

If a read model disagrees with the controller database:

1. use controller source rows for currentness and legality
2. repair or regenerate the read model
3. never rewrite controller truth from the projection

## Related contracts

- [Runtime lifecycle and watchdog](runtime-lifecycle-and-watchdog.md)
- [Controller contract and resumable execution](controller-contract-and-resumable-execution.md)
- [Attempt plan and checkpoint contract](attempt-plan-and-checkpoint-contract.md)
- [Node and operator MCP surface contract](../interfaces/node-and-operator-mcp-surface-contract.md)
- [V1 runtime database and object contract](../../v1/architecture/runtime-database-and-object-contract.md)
- [Task root and file access](task-root-and-file-access.md)
