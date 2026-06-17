# Human request and approval contract

Status: Target

This page defines the Vnext human-in-the-loop contract.

## Core rule

Human-in-the-loop is a typed pending controller request.

It is not:

- generic chat with the operator
- ordinary `continue_task`
- free-form transcript recovery

## Request kinds

Vnext supports these canonical pending human request kinds:

- `approval`
- `selection`
- `form`

Rules:

- `approval` is a binary or explicitly enumerated allow/deny decision over a concrete proposed action
- `selection` is a bounded choice over controller-provided options
- `form` is structured input validated against controller-owned schema

Free-form operator notes may accompany a resolution, but they are supporting audit detail only. They do not replace the typed response payload.

## Pending request shape

The controller-owned pending request record must include:

```yaml
pending_human_request:
  request_id: string
  task_id: string
  node_key: string
  request_kind: approval | selection | form
  title: string
  prompt: string
  policy_basis: string
  response_schema: object | null
  choices:
    - id: string
      title: string
      description: string | optional
  due_at: timestamp | null
  opened_at: timestamp
  status: open | resolved | timed_out | cancelled | superseded
```

Rules:

- `response_schema` is required for `form`, optional for `selection`, and null for simple `approval`
- `choices` is required for `selection` and must be absent for simple `form`
- one current node execution may own at most one open pending human request at a time
- opening a request moves the task lineage into controller waiting cause `waiting_for_human_request`

## Capability gate

The current node may open a pending human request only when its effective capability set allows `human_request`.

Capability values are:

- `none`
- `approval_only`
- `structured_input`
- `approval_or_structured_input`

Rules:

- `approval_only` may open `approval` requests only
- `structured_input` may open `selection` or `form` requests only
- `approval_or_structured_input` may open any canonical request kind

## Resolution shape

Every resolution must be persisted as a controller-owned record:

```yaml
human_request_resolution:
  request_id: string
  task_id: string
  resolution_kind: approved | rejected | submitted | timed_out | cancelled
  response_payload: object | null
  resolved_at: timestamp
  resolved_by_subject: string | null
  note: string | null
```

Rules:

- `approved` and `rejected` are legal only for `approval`
- `submitted` is legal only for `selection` and `form`
- `response_payload` must validate against `response_schema` when present
- timeout and cancellation are first-class terminal resolutions and must be persisted even when no human answered

## Wake semantics

Resolving a pending human request must:

1. persist the terminal resolution
2. emit the matching operator event
3. create a `resume_trigger_record` with cause `human_request_resolved`
4. wake the same task lineage when the task is still current

The wake path must not create a second generic chat turn or a second controller truth lane.

## Non-goals

This contract does not define:

- free-form operator conversation threads
- arbitrary operator-authored instructions as runtime truth
- ordinary workflow continuation through `continue_task`

## Related contracts

- [Controller contract and resumable execution](../architecture/controller-contract-and-resumable-execution.md)
- [Capability, security, and audit](capability-security-and-audit.md)
- [Operator UI API and event stream](operator-ui-api-and-event-stream.md)
