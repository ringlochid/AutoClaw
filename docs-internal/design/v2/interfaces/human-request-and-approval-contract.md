# Human request and approval contract

Status: Target

This page owns the V2 typed human-request source record, its external-wait transition, and its resolution policy.

## Core rule

A human request is the only interactive wait lane available to a managed agent. The current worker opens it deliberately through node MCP when controller-owned capability allows the request kind.

Opening a human request ends the current provider response and closes the current dispatch. It does not terminate the task, assignment, attempt, or plan, and it is not a `return_boundary` outcome.

Provider-native questions, approvals, and permission prompts must never become hidden interactive waits. Adapters resolve those mechanisms noninteractively by allowing, denying, or failing according to machine policy. When human direction is intentionally required, the worker uses this AutoClaw MCP lane.

## Request kinds

The request kinds are exactly:

- `direction` for a missing decision about purpose, priority, scope, technique, or trade-off
- `approval` for permission to take a proposed sensitive or consequential action
- `input` for missing structured information
- `review` for a human disposition on a plan, diff, summary, or result

Free-form notes may supplement an answer. They do not replace the typed item response or bypass controller legality.

## Request contract

The node-facing open request is:

```yaml
human_request_open_request:
    kind: direction | approval | input | review
    title: string
    summary: string
    items:
        - item_id: string
          prompt: string
          options:
              - id: string
                title: string
                description: string | null
          recommended_option: string | null
          input_payload_schema: object | null
    timeout:
        due_at: timestamp | null
        default_behavior: string | null
    suggested_human_instruction: string
```

Validation rules:

- `items` contains at least one item and item identifiers are unique inside the request
- `direction`, `approval`, and `review` items contain at least one option
- `input` items contain `input_payload_schema` and do not require options
- `input_payload_schema` is null for the three option-based kinds
- `recommended_option`, when present, names an option on the same item
- `due_at`, when present, is later than the controller commit time
- `suggested_human_instruction` tells the human what to inspect or do before answering

The controller response is:

```yaml
human_request_open_response:
    request_id: string
    task_id: string
    status: open
```

Success means the source row and external-wait transition committed. The response must also instruct the worker to stop its response immediately without recording a terminal checkpoint or calling `return_boundary`.

## Source record

The controller-owned source row is:

```yaml
pending_human_request:
    request_id: string
    task_id: string
    flow_id: string
    flow_revision_id: string
    flow_node_id: string
    assignment_id: string
    attempt_id: string
    dispatch_id: string
    requester_node: string
    kind: direction | approval | input | review
    title: string
    summary: string
    items: human_request_item[]
    timeout:
        due_at: timestamp | null
        default_behavior: string | null
    suggested_human_instruction: string
    opened_at: timestamp
    status: open | resolved | timed_out | cancelled
```

`HumanRequestRead` is the API and Node MCP read projection of this complete source shape. It does not omit the original items, timeout policy, or suggested human instruction.

`resolved` is the persisted status for an answered request. The separate resolution record identifies the terminal resolution kind as `answered`.

Only one open human request may own one current task lineage. Historical source rows remain readable but cannot compete with the current wait.

## Open legality

Opening is legal only when all of these are true:

- task, node session, dispatch, assignment, and attempt are current
- the current worker already recorded the required progress checkpoint
- no current human-request or command-run source wait owns the lineage
- effective `human_request.<kind>` capability is `allow`
- the request validates against the bounded contract above

Omitted request kinds resolve to `deny`. A rejected call returns the shared structured `capability_rejected`, validation, or currentness failure. It creates no source row, waiting cause, dispatch closure, or standalone task event and does not advance `last_progress_at`.

## Atomic external-wait transition

One shared controller operation closes a dispatch for either external-wait family. For a human request it commits, atomically:

1. the new `pending_human_request` source row
2. waiting cause `waiting_for_human_request` pointing to `request_id`
3. closure of the current `NodeSession`
4. dispatch status `closed` with `closed_reason = human_request_wait`
5. the semantic invocation completion and `last_progress_at`
6. bounded `human_request_opened` chronology

The operation does not:

- record a terminal checkpoint
- call `return_boundary`
- call adapter `stop`
- synthesize provider completion or failure
- suspend or retain an open dispatch
- wait for provider reconnect or provider output

The provider response ends naturally after MCP returns success. Task, assignment, attempt, and `AttemptPlan` remain current. With no open dispatch, the ordinary execution watchdog has nothing to inspect during the wait.

The command-run owner uses the same conceptual close-for-external-wait operation with its own source row, waiting cause, and close reason. Runtime code must not duplicate these closure rules in two service-specific helpers.

## Resolution contract

The terminal resolution is:

```yaml
human_request_resolution:
    request_id: string
    task_id: string
    resolution_kind: answered | timed_out | cancelled
    item_responses:
        - item_id: string
          selected_option: string | null
          freeform_answer: string | null
          extra_notes: string | null
          response_payload: object | null
    resolved_at: timestamp
    resolved_by_actor_ref: string | null
    resolved_by_surface: control_api | control_ui | operator_mcp | controller
    resolution_policy_basis: string
    resolution_note: string | null
```

`HumanRequestResolutionRead` is the read projection of this complete typed resolution shape. Continuation context always carries both `HumanRequestRead` and `HumanRequestResolutionRead`; a terminal status without its resolution is not sufficient continuation input.

Rules for `answered`:

- every request item has exactly one matching response
- option-based responses set exactly one of `selected_option` or `freeform_answer`
- `selected_option`, when set, names an option on the target item
- `response_payload`, when required, validates against that item's input schema
- `item_responses` is non-empty

Rules for `timed_out` and `cancelled`:

- `item_responses` is empty
- timeout and cancellation are controller-owned terminal results, not values a caller submits to the ordinary answer route
- the persisted request status becomes `timed_out` or `cancelled`

An answered request sets source status `resolved` and resolution kind `answered`. Provenance is immutable audit truth and is not editable prompt context.

## Currentness and policy

The ordinary resolve route may answer only the current open request that owns `waiting_for_human_request` for the task.

Resolution is rejected when the request is missing, already terminal, historical, superseded, or no longer owns the current wait. The caller does not need to provide `expected_active_flow_revision_id`; request identity plus source wait currentness provides the conflict boundary.

Pause does not terminate an open request. Task cancellation may cancel it.

When `due_at` expires, the human-request owner records `timed_out`, records the configured `default_behavior` as the policy basis or continuation guidance, and emits the matching terminal event. Timeout is not task failure by itself.

## Continuation

An `answered`, `timed_out`, or `cancelled` source row is terminal only for the human request. It is not terminal for the task lineage.

After the terminal result commits, the controller:

1. confirms the request still owns the matching wait
2. clears `waiting_for_human_request`
3. rereads task, structure, assignment, attempt, plan, checkpoint, and capability currentness
4. regenerates the complete prompt from controller truth
5. opens a new dispatch on the same assignment, attempt, and plan when legal

The continuation context includes the original request, its typed resolution, timeout/default behavior when relevant, and current plan and checkpoint context. Reusing a provider session hint is optional. Correctness never depends on provider conversation memory.

Operator `continue` does not answer or clear a human request.

## Read and audit surfaces

Control surfaces may list every request and expose the complete typed source and resolution records. The main task timeline keeps `human_request_*` payloads bounded and does not inline full answer bodies or structured response payloads.

The minimum event family is:

- `human_request_opened`
- `human_request_resolved`
- `human_request_timed_out`
- `human_request_cancelled`

Each event comes from the committed source-row transition. Provider events and provider-native approval UI are never audit truth.

## Required invariants

- AutoClaw MCP human requests are the only managed-agent interactive wait lane
- a successful open owns no live dispatch or node-session authority
- the open mutation and dispatch closure commit together
- request terminal state does not terminate task, assignment, attempt, or plan
- only the current source wait may authorize continuation
- one terminal source transition can prepare at most one continuation dispatch
- provider stop, provider completion, and `return_boundary` are absent from the external-wait path

## Related contracts

- [Controller contract and resumable execution](../architecture/controller-contract-and-resumable-execution.md)
- [Runtime lifecycle and watchdog](../architecture/runtime-lifecycle-and-watchdog.md)
- [Attempt plan and checkpoint contract](../architecture/attempt-plan-and-checkpoint-contract.md)
- [Capability, security, and audit](capability-security-and-audit.md)
- [Control API](control-api.md)
- [Task event stream](task-event-stream.md)
