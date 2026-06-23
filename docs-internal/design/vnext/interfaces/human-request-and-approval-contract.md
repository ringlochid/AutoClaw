# Human request contract

Status: Target

This page defines the Vnext human request contract.

## Core rule

A human request is an explicit, typed pending controller request opened by the current node when the controller-owned `human_request` capability allows it.

It is not:

- generic chat with the operator
- ordinary `continue_task`
- free-form transcript recovery
- provider tool-use detection
- a deterministic destructive-command scanner

## Request kinds

Vnext supports these canonical pending human request kinds:

- `direction`
- `approval`
- `input`
- `review`

Rules:

- `direction` asks the human to resolve a gap in purpose, priority, scope, technique, or tradeoff
- `approval` asks the human to allow, reject, or constrain a proposed action that the requester judges sensitive or risky
- `input` asks the human for missing structured information
- `review` asks the human to inspect a plan, diff, summary, result, or evidence set and choose the next step

Free-form operator notes and extra instructions may accompany a resolution, but they are supporting guidance and audit detail only. They do not replace the typed response payload or bypass controller legality.

## Non-detector rule

AutoClaw core does not detect arbitrary provider tool use and does not infer destructive intent from raw command text as the Vnext contract.

The normal path is:

1. the prompt, role, policy, workflow, or node instruction teaches the model when a human request is appropriate
2. the current node deliberately opens a typed human request through the node tool
3. the controller checks capability and task currentness
4. the operator, UI, or trusted automation resolves the request through the control lane
5. the controller continues the same task lineage when legal

Provider-specific approval or permission mechanisms may exist underneath particular adapters. They are adapter implementation details, not AutoClaw human-request concepts.

## Pending request shape

The controller-owned pending request record must include:

```yaml
pending_human_request:
  request_id: string
  task_id: string
  title: string
  summary: string
  kind: direction | approval | input | review
  requester_node: string
  items:
    - item_id: string
      prompt: string
      options:
        - id: string
          title: string
          description: string | optional
      recommended_option: string | null
      input_payload_schema: object | null
  timeout:
    due_at: timestamp | null
    default_behavior: string | null
  evidence_refs:
    - string
  suggested_human_instruction: string
  opened_at: timestamp
  status: open | resolved | timed_out | cancelled
```

Rules:

- `items` is required and must be non-empty
- each item names one scoped prompt the human must answer
- `options` is required for `direction`, `approval`, and `review` items
- `recommended_option` must match one of an item's `options` when present
- every human response uses the same per-item envelope: selected option, freeform answer, extra notes, and optional structured input payload
- `input_payload_schema` is required for `input` items and null for simple option-only items
- `evidence_refs` should point to controller-readable or operator-readable evidence, not raw secret material
- `suggested_human_instruction` tells the human what to inspect or do first before answering
- one current node execution may own at most one open pending human request at a time
- opening a request moves the task lineage into controller waiting cause `waiting_for_human_request`
- pending requests stay lean: the human should be able to answer from the title, summary, items, timeout/default behavior, evidence refs, and suggested human instruction without separate risk or expected-effect metadata

## Human-request gate

The current node may open a pending human request only when the controller-owned effective `human_request` capability allows the target request kind.

The effective capability resolves each canonical request kind independently:

- `direction: allow | deny`
- `approval: allow | deny`
- `input: allow | deny`
- `review: allow | deny`

Rules:

- the target request kind must resolve to `allow`
- omitted or denied request kinds resolve to `deny`
- authored `human_request.mode: deny` or omitted human-request policy resolves every request kind to `deny`
- authored `human_request.mode: deny` ignores `allowed_kinds` and must not leak accidental permission through stale list values
- denied request attempts return a structured rejection error, do not create `pending_human_request`, and do not enter `waiting_for_human_request`

## Resolution shape

Every resolution must be persisted as a controller-owned record:

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
```

Rules:

- `answered` means the human or operator submitted a response that satisfies the request kind
- `item_responses` is required for `answered` and omitted or empty for terminal non-answer outcomes
- every answered item response must match one request item by `item_id`
- `selected_option` must match an available option for the target item when options exist
- `freeform_answer` lets the human decline the listed options for one item and answer casually with another direction, constraint, or instruction
- answered responses for option-based items must include exactly one of `selected_option` or `freeform_answer`
- `extra_notes` is the standard place for item-scoped comments, caveats, or follow-up instructions
- `response_payload` must validate against the target item's `input_payload_schema` when present
- `freeform_answer`, `extra_notes`, and `response_payload` are validated guidance and data for the continued task; they are not direct controller truth
- `resolved_by_actor_ref` identifies who or what closed the request when the controller knows it, for example a human user, an operator agent, or trusted automation
- timeout and cancellation are first-class terminal resolutions and must be persisted even when no human answered

## Terminal boundary semantics

Terminating a pending human request must:

1. persist the terminal resolution
2. emit the matching task event
3. update the waiting-cause state when the terminal resolution clears the active human wait
4. leave the task lineage in database state that the controller loop can evaluate
5. allow redispatch with a full regenerated canonical prompt only when the task is still current and no replacement request keeps it waiting

The terminal boundary path must not create a second generic chat turn or a second controller truth lane.

Timeout is also a terminal resolution. When a request times out, the controller persists `resolution_kind: timed_out`, applies the request's `timeout.default_behavior`, emits the terminal task event, updates the waiting-cause state, and may redispatch the same controller lineage with the timeout/default behavior in the prompt when currentness and legality still hold. A timeout is failure to get a human response, not failure of the task itself unless policy or default behavior says so.

Provider session continuation may be reused for the redispatch when lawful, but controller lineage continuation is the required behavior.

## Operator handling

Operators are allowed to inspect and resolve pending human requests through control surfaces when task authorization allows it.

Operator handling may include:

- listing pending human requests
- reading request context, item prompts, item options, item recommendations, and evidence refs
- summarizing the request for the human
- asking the human through another approved communication surface
- submitting the typed resolution with item-scoped selected options or freeform answers, item-scoped extra notes, and any validated input payloads

Rules:

- operator handling uses the dedicated human-request resolution surface, not `continue_task`
- operator-authored summaries are not controller truth unless persisted as resolution extra notes or validated response payload
- an operator such as Orin may help the human understand and resolve the request, but must not silently choose for the human unless explicitly authorized by policy and task context

## UI handling

The control UI should treat pending human requests as first-class interactive work items.

Expected UI behavior includes:

- realtime `human_request_opened` delivery through the task event stream
- browser notification when the user has granted notification permission
- popup, modal, or drawer for the active pending request
- structured controls for request items, item options, approval, review, or input payloads
- item navigation when a request has multiple items, for example previous and next controls plus current item position
- item-scoped extra-notes fields as part of the standard response schema
- visible suggested human instruction, timeout/default behavior, item-level recommendations, and evidence refs
- display of resolved, cancelled, and timed-out states

The UI must submit resolution through the control human-request API and must not mutate controller state locally.

## Non-goals

This contract does not define:

- free-form operator conversation threads
- arbitrary operator-authored instructions as runtime truth
- ordinary workflow continuation through `continue_task`
- provider-level tool-use detection or approval interception

## Related contracts

- [Controller contract and resumable execution](../architecture/controller-contract-and-resumable-execution.md)
- [Capability, security, and audit](capability-security-and-audit.md)
- [Control API and task event stream](control-api-and-task-event-stream.md)
