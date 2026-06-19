# Capability, security, and audit

Status: Target

This page defines the Vnext capability, security, and audit contract.

## Core rule

Capability, human-request permission, and audit are Vnext core runtime concerns, not optional UX polish.

Human requests, async jobs, control-plane UI/API actions, and adapter integrations all depend on one controller-owned capability and audit model.

## Effective capability model

The controller must compute an effective capability set per current node execution.

That effective capability set may draw from:

- the current role and policy definitions
- controller-owned task or control policy
- deployment-time runtime profile selection
- adapter-specific constraints that are mapped into controller truth

The controller-owned effective capability set is the only authority for whether the current node may:

- open each kind of human request
- start an async job
- access specific node-tool families
- surface specific control-plane actions

Adapter permissions, local tool permissions, and UI affordances may restrict further, but they must not silently widen the controller-owned capability set.

The controller may serialize that effective set in a shape such as:

```yaml
effective_capability_set:
  execution_scope: dispatch | capability_denied | human_request_open | async_job_start
  human_request:
    direction: allow | deny
    approval: allow | deny
    input: allow | deny
    review: allow | deny
  async_job: allow | deny
  node_tool_allowlist:
    mode: inherited | explicit
    tool_families:
      - checkpoint
      - boundary
      - parent_structural_edit
      - definition_lookup
      - human_request
      - async_job
  control_action_visibility:
    - inspect_runtime
    - pause
    - continue
    - cancel
    - resolve_human_request
    - cancel_async_job
```

Rules:

- effective `human_request` capability resolves per request kind, not as one vague yes or no bit
- omitted or denied `human_request` kinds resolve to `deny` in the effective capability set
- one dispatch should use one stable evaluated capability snapshot for prompt and readback surfaces
- later dispatches may recompute the set from fresher controller truth without treating old prompt text as authority

## Non-detector rule

The capability layer is not a provider tool detector.

It does not watch arbitrary model/provider tool calls and decide whether the user should approve them. AutoClaw's default automation posture remains explicit orchestration: a node requests human help when its instructions, workflow state, or model judgment say the task needs human direction, input, review, or approval.

Provider-specific approval or permission mechanisms may exist underneath particular adapters, but they are not capability-layer concepts.

## Minimum Vnext capability families

Vnext must model these capability families explicitly:

- `human_request`
- `async_job`
- `node_tool_allowlist`
- `control_action_visibility`

Rules:

- `human_request` uses explicit deny/allow policy and governs whether the current node may open a typed pending human request
- `async_job` governs whether the current node may start controller-managed long-running work
- `node_tool_allowlist` governs the current node's effective write-capable or side-effectful tool set
- `control_action_visibility` governs which control actions the control UI or API may present as legal for the current task state
- explicit deny is authoritative even when stale allow-list fields are present on the same authored policy object

## Policy explanation rule

Every denied or gated capability decision that reaches the control UI/API surface must carry a stable explanation string.

That explanation must name:

- the denied capability family
- the current source of the deny or restriction
- the next legal action when one exists

These explanation strings are control-plane controller outputs. They must not be reconstructed from prompt text or inferred from hidden policy grammar.

Stable controller outputs may use a structure such as:

```yaml
capability_explanation:
  capability: human_request.review
  decision: deny
  source_basis: policy.standard_worker
  explanation: current worker policy does not allow review requests from this node
  next_legal_action: record_checkpoint_or_choose_another_allowed_boundary
  note: string | optional
```

Denied node attempts should also be represented in task events when they reach controller evaluation, using a stable family such as `capability_denied`.

## Capability snapshot and projection rule

The controller may materialize dispatch-local capability readbacks such as `_runtime/dispatch/<dispatch_id>/capabilities.json` or `_runtime/dispatch/<dispatch_id>/capabilities.md`.

Rules:

- those files are read models over controller-owned effective capability truth
- prompt sections may read from the same evaluated capability snapshot, but prompt text is not the source of truth
- if a materialized capability file lags, disappears, or disagrees with controller truth, controller truth and task events win

## Human request provenance

Every resolved human request must persist controller-owned provenance.

Minimum provenance fields are:

```yaml
human_request_provenance:
  request_id: string
  task_id: string
  resolved_by_actor_ref: string
  resolved_by_surface: control_api | control_ui | operator_mcp
  resolution_kind: answered | timed_out | cancelled
  resolved_at: timestamp
  policy_basis: string
  note: string | optional
```

Rules:

- the controller persists provenance even when the final result is rejection, timeout, or cancellation
- `resolved_by_actor_ref` is the controller's stable actor/principal reference for who or what resolved the request
- provenance is auditable fact, not prompt context by default
- future UI surfaces may display provenance, but they must not edit it

## Event-log integrity

Controller-owned task events, human-request state changes, and async-job state changes must be append-only and tamper-evident.

Minimum integrity rule:

- each persisted event record carries `event_id`
- each persisted event record carries `event_hash`
- each persisted event record carries `prev_event_hash | null`
- the hash is computed over the controller's canonical serialized event payload plus the prior hash

The exact hash algorithm may evolve, but the design contract requires a verifiable append-only chain.

## Per-task auth rule

Control-plane reads and writes must be authorized per task.

Rules:

- operator identity remains external authority, not runtime DB truth
- task-scoped access is evaluated against controller-owned authorization inputs
- adapter-local auth success does not automatically authorize controller writes
- controller writes from adapter callbacks or adapter-normalized human requests must still pass task-lineage and capability checks

## Redaction rule

Raw secrets, tokens, and irreversible credentials must never be persisted in:

- task event records
- pending human requests
- async-job summaries
- prompt previews
- UI event payloads

Allowed alternatives are:

- redacted placeholders
- stable secret refs or ids
- correlation ids
- machine-local deployment-binding references outside controller truth

## Related contracts

- [Controller contract and resumable execution](../architecture/controller-contract-and-resumable-execution.md)
- [Human request and approval contract](human-request-and-approval-contract.md)
- [Async job and long-running boundary](../architecture/async-job-and-long-running-boundary.md)
- [Control API and task event stream](control-api-and-task-event-stream.md)
- [Deployment binding and runtime profile map](deployment-binding-and-runtime-profile-map.md)
