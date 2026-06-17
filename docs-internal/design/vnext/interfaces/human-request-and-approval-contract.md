# Human request contract

Status: Target

This page defines the Vnext human request contract.

## Core rule

A human request is an explicit, typed pending controller request opened by the current node when policy allows it.

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
  risk_level: none | low | medium | high | destructive | external_write | privileged
  options:
    - id: string
      title: string
      description: string | optional
      expected_effect: string | optional
  recommended_option: string | null
  expected_effect: string | null
  timeout:
    due_at: timestamp | null
    default_behavior: string | null
  input_payload_schema: object | null
  evidence_refs:
    - string
  suggested_human_instruction: string
  opened_at: timestamp
  status: open | resolved | timed_out | cancelled | superseded
  superseded_by_request_id: string | null
```

Rules:

- `options` is required for `direction`, `approval`, and `review`
- `recommended_option` must match one of `options` when present
- `expected_effect` summarizes what the requester expects after the human answers; option-specific effects may live on individual options when useful
- every human response uses the same envelope: selected option, extra notes, and optional structured input payload
- `input_payload_schema` is required for `input` and null for simple option-only requests
- `risk_level` is requester-declared controller metadata, not a deterministic parser result
- `evidence_refs` should point to controller-readable or operator-readable evidence, not raw secret material
- `suggested_human_instruction` tells the human what to inspect or do first before answering
- one current node execution may own at most one open pending human request at a time
- opening a request moves the task lineage into controller waiting cause `waiting_for_human_request`
- `superseded_by_request_id` is null unless the controller closes this request because a newer controller-owned request replaces it

## Capability gate

The current node may open a pending human request only when its effective capability set allows `human_request`.

The effective capability names the request kinds the node may open:

- `none`
- `direction`
- `approval`
- `input`
- `review`
- `any`

Rules:

- `none` may not open a human request
- `any` may open any canonical request kind
- otherwise the request kind must appear in the node's allowed human-request capability set

## Resolution shape

Every resolution must be persisted as a controller-owned record:

```yaml
human_request_resolution:
  request_id: string
  task_id: string
  resolution_kind: answered | timed_out | cancelled | superseded
  selected_option: string | null
  freeform_answer: string | null
  extra_notes: string | null
  response_payload: object | null
  resolved_at: timestamp
  resolved_by_subject: string | null
  superseded_by_request_id: string | null
```

Rules:

- `answered` means the human or operator submitted a response that satisfies the request kind
- `selected_option` must match an available option for `direction`, `approval`, and `review`
- `freeform_answer` lets the human decline the listed options and answer casually with another direction, constraint, or instruction
- answered responses for option-based request kinds must include exactly one of `selected_option` or `freeform_answer`
- `extra_notes` is the standard place for human comments, caveats, or follow-up instructions
- `response_payload` must validate against `input_payload_schema` when present
- `freeform_answer`, `extra_notes`, and `response_payload` are validated guidance and data for the continued task; they are not direct controller truth
- timeout, cancellation, and supersession are first-class terminal resolutions and must be persisted even when no human answered
- `superseded` is controller-initiated and must name the replacement request when one exists

## Terminal boundary semantics

Terminating a pending human request must:

1. persist the terminal resolution
2. emit the matching task event
3. update the waiting-cause state when the terminal resolution clears the active human wait
4. leave the task lineage in database state that the controller loop can evaluate
5. allow redispatch with a full regenerated canonical prompt only when the task is still current and no replacement request keeps it waiting

The terminal boundary path must not create a second generic chat turn or a second controller truth lane.

If one request is superseded by a replacement request, the supersession event closes the old request but does not by itself open the next ordinary node dispatch. The replacement request owns the active `waiting_for_human_request` wait until it reaches a terminal resolution.

Timeout is also a terminal resolution. When a request times out, the controller persists `resolution_kind: timed_out`, applies the request's `timeout.default_behavior`, emits the terminal task event, updates the waiting-cause state, and may redispatch the same controller lineage with the timeout/default behavior in the prompt when currentness and legality still hold. A timeout is failure to get a human response, not failure of the task itself unless policy or default behavior says so.

Provider session continuation may be reused for the redispatch when lawful, but controller lineage continuation is the required behavior.

## Operator handling

Operators are allowed to inspect and resolve pending human requests through control surfaces when task authorization allows it.

Operator handling may include:

- listing pending human requests
- reading request context, options, recommended option, and evidence refs
- summarizing the request for the human
- asking the human through another approved communication surface
- submitting the typed resolution with selected option or freeform answer, extra notes, and any validated input payload

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
- structured controls for options, approval, review, or input payloads
- extra-notes field as part of the standard response schema
- visible risk level, recommended option, suggested human instruction, timeout/default behavior, expected effect, and evidence refs
- display of resolved, cancelled, timed-out, and superseded states

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
